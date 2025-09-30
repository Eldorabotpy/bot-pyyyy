# run_daily_cristal_now.py
import asyncio
from types import SimpleNamespace
from handlers.jobs import daily_crystal_grant_job

# Contexto "fake" com bot mudo (pra não enviar DM)
ctx = SimpleNamespace(bot=SimpleNamespace(send_message=lambda **kw: None))

if __name__ == "__main__":
    asyncio.run(daily_crystal_grant_job(ctx))
    print("OK: job diário executado agora.")
