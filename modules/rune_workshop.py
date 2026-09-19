"""Operações puras de runas; persistência usa comparação do documento original."""
import copy
import unicodedata
from modules.game_data.runes_data import RUNES_DB
from modules.game_data.rune_rules import SOCKETS_BY_RARITY, EXTRACTION_GOLD, EVOLUTION_COSTS, DUST_YIELD


def rarity(value):
    return ''.join(c for c in unicodedata.normalize('NFD', str(value).lower()) if unicodedata.category(c) != 'Mn')


def equipment_item(item, info):
    return isinstance(item, dict) and not info.get('stackable', False) and info.get('type') not in ('runa', 'material', 'material_runico', 'consumable') and any(k in item for k in ('durability', 'attributes', 'enchantments', 'sockets', 'upgrade_level'))


def sockets(item):
    current = list(item.get('sockets') or [])
    capacity = SOCKETS_BY_RARITY.get(rarity(item.get('rarity', 'comum')), 0)
    # Nunca apaga encaixes antigos, inclusive de raridades legadas.
    return current + [None] * max(0, capacity - len(current))


def item_view(item):
    slots = sockets(item)
    return {'sockets': slots, 'rune_slots': [dict(RUNES_DB[r], id=r) if r in RUNES_DB else ({'id':r,'name':str(r),'desc':'Runa antiga — pode ser extraída'} if r else None) for r in slots]}


def quantity(inv, base):
    return sum(int(v.get('quantity',v.get('qty',v.get('qtd',1)))) if isinstance(v,dict) else int(v) for k,v in inv.items() if (v.get('base_id',k) if isinstance(v,dict) else k)==base)


def consume(inv, base, amount):
    if quantity(inv,base) < amount:
        raise ValueError(f'Material insuficiente: {base}.')
    for key in list(inv):
        value=inv[key]
        if (value.get('base_id',key) if isinstance(value,dict) else key)!=base: continue
        field=next((f for f in ('quantity','qty','qtd') if isinstance(value,dict) and f in value),'quantity')
        count=int(value.get(field,1)) if isinstance(value,dict) else int(value)
        used=min(amount,count);amount-=used
        if count==used: del inv[key]
        elif isinstance(value,dict): value[field]=count-used
        else: inv[key]=count-used
        if amount==0: break


def grant(inv, base, amount):
    value=inv.get(base,0)
    if isinstance(value,dict):
        field=next((f for f in ('quantity','qty','qtd') if f in value),'quantity')
        value[field]=int(value.get(field,1))+amount
    else: inv[base]=int(value)+amount


def state_view(player, items):
    inv=player.get('inventory') or {}
    equipped=set(str(x) for x in (player.get('equipment') or {}).values())
    gear=[]
    for uid,item in inv.items():
        info=items.get(item.get('base_id',uid),{}) if isinstance(item,dict) else {}
        if not equipment_item(item,info): continue
        gear.append({'id':uid,'base_id':item.get('base_id',uid),'nome':info.get('display_name',item.get('base_id',uid)),'raridade':item.get('rarity','comum'),'equipado':str(uid) in equipped,**item_view(item)})
    return {'gold':int(player.get('gold',0)), 'revision':int(player.get('rune_revision',0)), 'equipamentos':gear,
        'runas':[dict(r,id=rid,qtd=quantity(inv,rid)) for rid,r in RUNES_DB.items()],
        'materiais':{k:quantity(inv,k) for k in ('po_runico','fragmento_runa_ancestral')},
        'extracao_ouro':EXTRACTION_GOLD,'custos_evolucao':EVOLUTION_COSTS,'po_por_nivel':DUST_YIELD}


def apply_operation(player, data, items):
    if (player.get('player_state') or {}).get('action') not in (None,'','idle'):
        raise ValueError('Finalize sua atividade antes de alterar runas.')
    inv=copy.deepcopy(player.get('inventory') or {})
    gold=int(player.get('gold',0));cost=0
    action=data.get('action');rid=data.get('rune_id');rune=RUNES_DB.get(rid)
    if action in ('encaixar','extrair'):
        uid=data.get('item_id');item=inv.get(uid)
        info=items.get(item.get('base_id',uid),{}) if isinstance(item,dict) else {}
        if not equipment_item(item,info): raise ValueError('Selecione um equipamento válido da sua mochila.')
        slots=sockets(item)
        index=data.get('slot')
        if not isinstance(index,int) or isinstance(index,bool) or not 0<=index<len(slots): raise ValueError('Espaço rúnico inválido.')
        if action=='encaixar':
            if not rune: raise ValueError('Runa desconhecida.')
            if index>=SOCKETS_BY_RARITY.get(rarity(item.get('rarity','comum')),0): raise ValueError('Espaço não permitido para esta raridade.')
            if slots[index]: raise ValueError('Extraia a runa atual antes de encaixar outra.')
            if any(RUNES_DB.get(r,{}).get('family')==rune['family'] for r in slots if r): raise ValueError('Este equipamento já possui uma runa desta família.')
            consume(inv,rid,1);slots[index]=rid
        else:
            if not slots[index]: raise ValueError('Este espaço já está vazio.')
            cost=EXTRACTION_GOLD;grant(inv,slots[index],1);slots[index]=None
        item['sockets']=slots
    elif action=='evoluir':
        if not rune or not rune['next_id']: raise ValueError('Esta runa não possui outra evolução.')
        recipe=EVOLUTION_COSTS[rune['tier']];cost=recipe['gold']
        consume(inv,rid,3)
        for material,count in recipe.items():
            if material!='gold': consume(inv,material,count)
        grant(inv,rune['next_id'],1)
    elif action=='dissolver':
        if not rune: raise ValueError('Runa desconhecida.')
        consume(inv,rid,1);grant(inv,'po_runico',DUST_YIELD[rune['tier']])
    else: raise ValueError('Operação rúnica inválida.')
    if gold<cost: raise ValueError(f'Ouro insuficiente. Custo: {cost}.')
    return inv,gold-cost


def save_operation(collection, player, data, items):
    if int(data.get('revision',-1))!=int(player.get('rune_revision',0)): raise ValueError('A mochila mudou. Atualize a janela e tente novamente.')
    inv,gold=apply_operation(player,data,items)
    query={'_id':player['_id']}
    for key in ('inventory','gold','equipment','player_state','rune_revision','rune_hunt_active'):
        query[key]=player[key] if key in player else {'$exists':False}
    result=collection.update_one(query,{'$set':{'inventory':inv,'gold':gold},'$inc':{'rune_revision':1}})
    if result.modified_count!=1: raise ValueError('A mochila mudou durante a operação. Atualize antes de tentar novamente.')
