# Compras da Flora usam a mesma coleção e inventário do personagem.
from flask_socketio import emit
from flask import request
from bson.objectid import ObjectId

CATALOGO_FLORA = {
    "incubadora_pet": {"nome": "Incubadora · 1 uso", "preco": 25},
    "pocao_xp_boost": {"nome": "Poção de XP P", "preco": 15},
    "pocao_xp_boost_g": {"nome": "Poção de XP G", "preco": 60},
    "ticket_coliseu_pvp": {"nome": "Ticket de Entrada do Coliseu", "preco": 5},
    "chave_masmorra": {"nome": "Chave de Masmorra", "preco": 20},
}

def registrar_loja_reino(socketio, db, jogadores_online):
    @socketio.on('comprar_item_gema')
    def handle_comprar_item_gema(dados):
        from modules.player.core import users_collection
        jogador_online = jogadores_online.get(request.sid)
        if not jogador_online:
            emit('respostaCompraGema', {'sucesso': False, 'mensagem': 'Reconecte ao reino para comprar.'})
            return
        item = dados.get('item') if isinstance(dados, dict) else None
        produto = CATALOGO_FLORA.get(item) if isinstance(item, str) else None
        if not produto:
            emit('respostaCompraGema', {'sucesso': False, 'mensagem': 'Artigo indisponível.'})
            return
        char_id = str(jogador_online.get('char_id', ''))
        if not ObjectId.is_valid(char_id):
            return
        oid = ObjectId(char_id)
        if item == 'incubadora_pet':
            # Cobrança e recibo de entrega na mesma atualização atômica.
            receipt = {'id': str(ObjectId()), 'quantity': 1}
            result = users_collection.update_one(
                {'_id': oid, 'gems': {'$gte': produto['preco']}},
                {'$inc': {'gems': -produto['preco']}, '$push': {'companion_incubator_grants': receipt}})
            if result.modified_count:
                emit('respostaCompraGema', {'sucesso': True, 'mensagem': 'Incubadora comprada! Abra Bestiário → Companheiros para usar.'})
            else:
                emit('respostaCompraGema', {'sucesso': False, 'mensagem': 'Gemas insuficientes! Custa 25 💎.'})
            return
        if item == 'ticket_coliseu_pvp':
            # O saldo de tickets e as gemas são alterados juntos, sem risco de cobrança parcial.
            resultado = users_collection.update_one(
                {'_id': oid, 'gems': {'$gte': produto['preco']}},
                {'$inc': {'gems': -produto['preco'], 'coliseu_pvp_entry_tickets': 1}},
            )
            if resultado.modified_count:
                emit('respostaCompraGema', {
                    'sucesso': True,
                    'mensagem': 'Ticket adicionado à sua conta. Ele será usado automaticamente depois das 10 entradas gratuitas diárias.',
                })
            else:
                emit('respostaCompraGema', {
                    'sucesso': False,
                    'mensagem': f"Gemas insuficientes! O Ticket de Entrada do Coliseu custa {produto['preco']} 💎.",
                })
            return
        mensagem_sucesso = f"{produto['nome']} entregue na mochila. Use para ativar o XP dobrado!"
        if item == 'chave_masmorra':
            mensagem_sucesso = (
                'Chave de Masmorra adicionada à mochila. '
                'Ela será consumida ao iniciar uma nova expedição.'
            )
        # Comparação do inventário evita sobrescrever compras/consumos concorrentes.
        for _ in range(3):
            jogador = users_collection.find_one({'_id': oid})
            if not jogador or int(jogador.get('gems', 0)) < produto['preco']:
                emit('respostaCompraGema', {'sucesso': False, 'mensagem': f"Gemas insuficientes! Custa {produto['preco']} 💎."})
                return
            anterior = jogador.get('inventory', {})
            if not isinstance(anterior, dict):
                break
            inventario = dict(anterior)
            atual = inventario.get(item, 0)
            if isinstance(atual, dict):
                inventario[item] = {**atual, 'quantity': int(atual.get('quantity', 0)) + 1}
            else:
                inventario[item] = int(atual) + 1
            resultado = users_collection.update_one(
                {'_id': oid, 'gems': {'$gte': produto['preco']},
                 'inventory': anterior if 'inventory' in jogador else {'$exists': False}},
                {'$inc': {'gems': -produto['preco']}, '$set': {'inventory': inventario}})
            if resultado.modified_count:
                emit('respostaCompraGema', {'sucesso': True, 'mensagem': mensagem_sucesso})
                return
        emit('respostaCompraGema', {'sucesso': False, 'mensagem': 'O inventário mudou. Tente novamente.'})
