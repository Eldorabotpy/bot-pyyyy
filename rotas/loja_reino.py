# rotas/loja_reino.py
from flask_socketio import emit
from flask import request
from bson.objectid import ObjectId

def registrar_loja_reino(socketio, db, jogadores_online):
    
    @socketio.on('comprar_item_gema')
    def handle_comprar_item_gema(dados):
        player_sid = request.sid
        if player_sid not in jogadores_online: 
            return

        char_id = str(jogadores_online[player_sid]['char_id'])
        item_desejado = dados.get('item')

        # Catálogo Premium (Gemas)
        loja_premium = {
            'pocao_xp_boost': {'nome': 'Pergaminho de XP (2x)', 'preco': 15},
            'bau_lendario': {'nome': 'Baú de Equipamentos Lendários', 'preco': 50}
        }

        if item_desejado not in loja_premium:
            emit('respostaCompraGema', {'sucesso': False, 'mensagem': 'Artigo não encontrado no tesouro do reino.'})
            return

        produto = loja_premium[item_desejado]
        preco = produto['preco']

        # Busca o jogador (Garante que a coleção se chama 'jogadores' no seu banco)
        jogador = db.jogadores.find_one({"_id": ObjectId(char_id)})
        gemas_atuais = int(jogador.get("gemas", 0)) # ATENÇÃO: Verifique se o campo no seu DB é 'gemas' ou 'diamantes'

        if gemas_atuais < preco:
            emit('respostaCompraGema', {'sucesso': False, 'mensagem': f"Gemas insuficientes! Custa {preco} 💎."})
            return

        # Desconta as Gemas e joga na mochila
        db.jogadores.update_one(
            {"_id": ObjectId(char_id)},
            {
                "$inc": {"gemas": -preco}, 
                "$push": {"inventario": item_desejado} 
            }
        )

        emit('respostaCompraGema', {'sucesso': True, 'mensagem': f"Compra Real Realizada: {produto['nome']}!"})