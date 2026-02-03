# registries/onboarding.py
from telegram.ext import CallbackQueryHandler, MessageHandler, filters
from handlers.tutorial.dora_intro import dora_intro_callback, dora_name_message
from handlers.tutorial.dora_profession import dora_profession_callback
from handlers.tutorial.dora_gathering import dora_gathering_callback
from handlers.tutorial.dora_hunting import dora_hunting_callback

def register_onboarding_handlers(application):
    application.add_handler(CallbackQueryHandler(dora_intro_callback, pattern=r"^dora_name_"))
    application.add_handler(CallbackQueryHandler(dora_profession_callback, pattern=r"^dora_prof_"))
    application.add_handler(CallbackQueryHandler(dora_gathering_callback, pattern=r"^dora_gath_"))
    
    application.add_handler(CallbackQueryHandler(dora_hunting_callback, pattern=r"^dora_hunt_"))

    # ✅ MUITO IMPORTANTE: group=-1 (roda antes dos outros handlers)
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, dora_name_message, block=False),
        group=-100
)

