"""Mercado: inventário, saldo e anúncio são confirmados na mesma transação."""
from __future__ import annotations
import copy
import logging
import re
import uuid
from datetime import datetime, timezone
from bson import ObjectId
from pymongo import ReturnDocument
from pymongo.read_concern import ReadConcern
from pymongo.write_concern import WriteConcern
from modules.player import core
from modules.game_data.items import ITEMS_DATA
from modules.game_data.items_evolution import EVOLUTION_ITEMS_DATA

log = logging.getLogger(__name__)
# Todas as coleções usam o MESMO cliente; sessões não atravessam clientes Mongo.
users_col = core.users_collection
db = users_col.database if users_col is not None else None
market_col = db['market_listings'] if db is not None else None
counters_col = db['counters'] if db is not None else None

class MarketError(Exception): pass
class ListingNotFound(MarketError): pass
class ListingInactive(MarketError): pass
class InvalidListing(MarketError): pass
class PermissionDenied(MarketError): pass
class InsufficientQuantity(MarketError): pass
class InvalidPurchase(MarketError): pass


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


def _positive(value, label):
    if isinstance(value, bool) or not re.fullmatch(r'[0-9]+', str(value)):
        raise InvalidListing(f'{label} deve ser um número inteiro positivo.')
    value = int(value)
    if value <= 0 or value > 2**53 - 1:
        raise InvalidListing(f'{label} fora do limite permitido.')
    return value


def _player_id(value):
    if isinstance(value, ObjectId): return value
    if ObjectId.is_valid(str(value)): return ObjectId(str(value))
    if str(value).isdigit(): return int(value)
    raise PermissionDenied('Identificação de jogador inválida.')


def _listing_query(value):
    if isinstance(value, ObjectId) or ObjectId.is_valid(str(value)):
        return {'_id': ObjectId(str(value))}
    return {'id': _positive(value, 'Anúncio')}


def _transaction(callback):
    if market_col is None: raise MarketError('Mercado indisponível.')
    # Sem fallback não transacional: em servidor incompatível, falha sem mover bens.
    with db.client.start_session() as session:
        return session.with_transaction(callback, read_concern=ReadConcern('snapshot'),
                                        write_concern=WriteConcern('majority'))


def _invalidate(*ids):
    for uid in ids:
        core._player_cache.pop(str(uid), None)
        core._player_cache_time.pop(str(uid), None)


def _player(uid, session):
    doc = users_col.find_one({'_id': _player_id(uid)}, session=session)
    if not doc: raise MarketError('Jogador não encontrado.')
    return doc


def _save_inventory(doc, session, delta=None):
    update = {'$set': {'inventory': doc.get('inventory', {})}}
    if delta: update['$inc'] = delta
    result = users_col.update_one({'_id': doc['_id']}, update, session=session)
    if result.matched_count != 1: raise MarketError('Jogador indisponível.')


def _quantity(item):
    return int(item.get('quantity', item.get('qty', item.get('qtd', 1))) if isinstance(item, dict) else item)


def _set_quantity(item, value):
    item['quantity'] = value
    item.pop('qty', None)
    item.pop('qtd', None)


def _payload(listing):
    payload = copy.deepcopy(listing.get('item') or {})
    if isinstance(payload, str): return {'type': 'stack', 'base_id': payload, 'qty': 1}
    if not payload.get('type'):
        if 'durability' in payload or 'upgrade_level' in payload:
            return {'type': 'unique', 'base_id': payload.get('base_id'), 'item': payload}
        payload.update(type='stack', qty=1)
    return payload


def _deliver(doc, payload, quantity):
    inv = doc.setdefault('inventory', {})
    if payload.get('type') == 'unique':
        item = payload.get('item')
        if not isinstance(item, dict) or not item: raise InvalidPurchase('Equipamento inválido.')
        for _ in range(quantity): inv[str(uuid.uuid4())] = copy.deepcopy(item)
        return
    if payload.get('type') != 'stack': raise InvalidPurchase('Tipo de item inválido.')
    base = payload.get('base_id')
    if not isinstance(base, str) or not base: raise InvalidPurchase('Item sem identificação.')
    base = re.sub(r'_[a-fA-F0-9]{8}$', '', base)
    amount = quantity * _positive(payload.get('qty', 1), 'Tamanho do lote')
    for key, value in inv.items():
        if (isinstance(value, dict) and value.get('base_id', key) == base) or (not isinstance(value, dict) and key == base):
            if isinstance(value, dict): _set_quantity(value, _quantity(value) + amount)
            else: inv[key] = _quantity(value) + amount
            return
    inv[base] = {'base_id': base, 'quantity': amount}


def create_listing(*, seller_id, item_id, total_price, quantity=1, currency='ouro'):
    price = _positive(total_price, 'Preço')
    quantity = _positive(quantity, 'Quantidade')
    currency = {'gema': 'gemas', 'gemas': 'gemas', 'ouro': 'ouro'}.get(currency)
    if not currency: raise InvalidListing('Moeda inválida.')
    if not isinstance(item_id, str) or not item_id: raise InvalidListing('Selecione um item.')

    def commit(session):
        seller = _player(seller_id, session)
        inv = seller.get('inventory', {})
        original = inv.get(item_id)
        if original is None: raise InvalidListing('Item não encontrado na mochila.')
        amount = _quantity(original)
        if quantity > amount: raise InsufficientQuantity(f'Você possui apenas {amount} unidades.')
        item = copy.deepcopy(original) if isinstance(original, dict) else {'base_id': item_id}
        base = re.sub(r'_[a-fA-F0-9]{8}$', '', item.get('base_id', item_id))
        info = ITEMS_DATA.get(base)
        if not info: raise InvalidListing('Item não cadastrado no catálogo.')
        if info.get('tradable') is False or item.get('tradable') is False or base in {'gems', 'sigilo_protecao', 'ticket_arena', 'chave_da_catacumba', 'cristal_de_abertura'}:
            raise InvalidListing('Este item não pode ser comercializado.')
        if base in EVOLUTION_ITEMS_DATA:
            raise InvalidListing('Venda itens de evolução no Comércio de Relíquias.')
        item['base_id'] = base
        unique = info.get('stackable') is False or info.get('type') in {'weapon','armor','helmet','boots','ring','necklace','earring','tool'} or (info.get('stackable') is not True and bool(item.get('durability') or item.get('upgrade_level') or item.get('enchantments')))
        if unique:
            if quantity != 1 or amount != 1: raise InvalidListing('Anuncie um equipamento por vez.')
            payload = {'type': 'unique', 'base_id': base, 'item': item}
        else: payload = {'type': 'stack', 'base_id': base, 'qty': 1}
        if quantity == amount: del inv[item_id]
        elif isinstance(original, dict): _set_quantity(inv[item_id], amount - quantity)
        else: inv[item_id] = amount - quantity
        seq = counters_col.find_one_and_update({'_id':'market_id'}, {'$inc':{'seq':1}}, upsert=True, return_document=ReturnDocument.AFTER, session=session)['seq']
        listing = {'id':seq, 'seller_id':str(seller['_id']), 'seller_name':seller.get('character_name','Aventureiro'),
                   'item':payload, 'quantity':quantity, 'unit_price':price // quantity, 'total_price':price,
                   'currency':currency, 'created_at':_now_iso(), 'active':True, 'target_buyer_id':None}
        _save_inventory(seller, session)
        market_col.insert_one(listing, session=session)
        return listing
    result = _transaction(commit)
    _invalidate(seller_id)
    return result


def get_listing(listing_id):
    return market_col.find_one(_listing_query(listing_id)) if market_col is not None else None


def _active(listing_id, session):
    listing = market_col.find_one(_listing_query(listing_id), session=session)
    if not listing: raise ListingNotFound('Anúncio não encontrado.')
    if not listing.get('active') or int(listing.get('quantity',0)) <= 0:
        raise ListingInactive('Anúncio já comprado ou cancelado.')
    return listing


def listing_total(listing):
    return int(listing.get('total_price', int(listing.get('unit_price',0)) * int(listing.get('quantity',0))))


async def purchase_listing(*, buyer_id, listing_id, quantity=None, context=None):
    def commit(session):
        listing = _active(listing_id, session)
        if str(listing['seller_id']) == str(buyer_id): raise InvalidPurchase('Você não pode comprar seu próprio anúncio.')
        target = listing.get('target_buyer_id')
        if target is not None and str(target) != str(buyer_id): raise PermissionDenied('Anúncio reservado para outro jogador.')
        available = int(listing['quantity'])
        qty = available if quantity is None else _positive(quantity, 'Quantidade')
        if qty > available: raise InsufficientQuantity('Estoque insuficiente.')
        total = _positive(listing_total(listing), 'Preço do anúncio')
        # Partes recebem o resto inteiro; comprar o lote inteiro preserva o preço exato.
        price = total if qty == available else max(1, total * qty // available)
        if qty < available and price >= total: raise InvalidPurchase('Este anúncio deve ser comprado inteiro.')
        currency = listing.get('currency', 'ouro')
        if currency not in {'ouro','gema','gemas'}: raise InvalidPurchase('Moeda inválida no anúncio.')
        field = 'gold' if currency == 'ouro' else 'gems'
        buyer = _player(buyer_id, session)
        seller = _player(listing['seller_id'], session)
        if int(buyer.get(field,0) or 0) < price: raise InvalidPurchase('Saldo insuficiente.')
        _deliver(buyer, _payload(listing), qty)
        _save_inventory(buyer, session, {field:-price})
        tax = price // 10
        result = users_col.update_one({'_id':seller['_id']}, {'$inc':{field:price-tax}}, session=session)
        if result.matched_count != 1: raise MarketError('Falha ao creditar o vendedor.')
        remaining = available - qty
        changes = {'quantity':remaining, 'total_price':total-price, 'active':remaining > 0}
        if not remaining: changes['sold_at'] = _now_iso()
        market_col.update_one({'_id':listing['_id']}, {'$set':changes}, session=session)
        listing.update(changes, tax=tax, seller_amount=price-tax)
        return listing, price
    result = _transaction(commit)
    _invalidate(buyer_id, result[0]['seller_id'])
    return result


async def cancel_listing(listing_id, *, seller_id):
    def commit(session):
        listing = _active(listing_id, session)
        if str(listing['seller_id']) != str(seller_id): raise PermissionDenied('Você não pode cancelar o anúncio de outro jogador.')
        seller = _player(seller_id, session)
        _deliver(seller, _payload(listing), int(listing['quantity']))
        _save_inventory(seller, session)
        market_col.update_one({'_id':listing['_id']}, {'$set':{'active':False,'cancelled_at':_now_iso()}}, session=session)
        return listing
    result = _transaction(commit)
    _invalidate(seller_id)
    return result


def list_active(*, region_key=None, base_id=None, sort_by='created_at', ascending=False,
                page=1, page_size=20, price_per_unit=False, viewer_id=None):
    if market_col is None: return []
    query = {'active':True, 'quantity':{'$gt':0}}
    if region_key: query['region_key'] = region_key
    if base_id: query['item.base_id'] = base_id
    query['target_buyer_id'] = None
    if viewer_id:
        variants = [str(viewer_id), _player_id(viewer_id)]
        query.pop('target_buyer_id')
        query['$or'] = [{'target_buyer_id':None}, {'target_buyer_id':{'$in':variants}}, {'seller_id':{'$in':variants}}]
    return list(market_col.find(query).sort('unit_price' if sort_by == 'price' else 'created_at', 1 if ascending else -1).skip((max(1,page)-1)*page_size).limit(page_size))


def list_by_seller(seller_id):
    if market_col is None: return []
    return list(market_col.find({'active':True,'seller_id':{'$in':[str(seller_id),_player_id(seller_id)]}}))
