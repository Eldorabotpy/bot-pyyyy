# Arquivo: limpar_webhook.py
import asyncio
from telegram import Bot

# IMPORTANTE: Coloca o token do teu bot aqui
TOKEN = "8381079451:AAEOVskOCbExxGoOkBSfWmO93DTw9jWGkzQ"

async def main():
    """Função que se conecta ao bot e apaga qualquer webhook existente."""
    bot = Bot(token=TOKEN)
    print("A tentar limpar o webhook...")

    # Pega informações do webhook atual (opcional, mas bom para debug)
    webhook_info = await bot.get_webhook_info()
    if webhook_info.url:
        print(f"Encontrado um webhook ativo: {webhook_info.url}")
    else:
        print("Nenhum webhook ativo encontrado.")

    # Apaga o webhook
    success = await bot.delete_webhook()

    if success:
        print("\n✅ Webhook limpo com sucesso!")
        print("Agora podes iniciar o teu bot principal com 'polling'.")
    else:
        print("\n❌ Falha ao limpar o webhook.")

if __name__ == "__main__":
    asyncio.run(main())