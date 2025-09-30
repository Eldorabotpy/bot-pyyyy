# =========================
# main.py — Mundo de Eldora (Modo Polling)
# =========================

from __future__ import annotations
import os
import logging
import asyncio
from datetime import datetime, timezone, time
from zoneinfo import ZoneInfo
from modules import player_manager

from telegram import Update
from telegram.ext import (
    Application, ApplicationBuilder, CallbackQueryHandler, CommandHandler,
    ContextTypes, filters, MessageHandler, ConversationHandler
)

# Jobs e Handlers Gerais
from handlers.jobs import regenerate_energy_job, daily_crystal_grant_job
from handlers.daily_jobs import daily_pvp_entry_reset_job
from handlers.chat_handler import chat_interaction_handler
from handlers.job_handler import finish_collection_job, job_handler
from handlers.admin_handler import delete_player_handler

# Módulos Opcionais com Tratamento de Erro
try:
    from modules.recipes import register_all as register_all_recipes
    register_all_recipes()
    logging.info("[RECIPES] Pacotes de receitas registrados com sucesso.")
except ImportError as e:
    logging.warning(f"[RECIPES] Registro de receitas não disponível: {e}")

try:
    from handlers.forge_handler import finish_craft_notification_job as finish_crafting_job, forge_handler
except ImportError:
    finish_crafting_job, forge_handler = None, None

try:
    from handlers.refining_handler import (
        finish_refine_job as finish_refining_job, ref_confirm_handler, ref_select_handler,
        refining_main_callback, refining_main_handler, dismantle_list_handler,
        dismantle_preview_handler, dismantle_confirm_handler, finish_dismantle_job
    )
except ImportError:
    finish_refine_job, ref_confirm_handler, ref_select_handler, refining_main_callback, \
    refining_main_handler, dismantle_list_handler, dismantle_preview_handler, \
    dismantle_confirm_handler, finish_dismantle_job = (None,) * 9

try:
    from modules.dungeons.runtime import dungeon_open_handler, dungeon_pick_handler
except ImportError:
    dungeon_open_handler, dungeon_pick_handler = None, None

try:
    from handlers.events.party_handler import invite_conversation_handler, party_callback_handler
except ImportError:
    invite_conversation_handler, party_callback_handler = None, None

try:
    from handlers.menu.region import (
        region_handler as region_callback_handler, travel_handler as travel_callback_handler,
        restore_durability_menu_handler, restore_durability_fix_handler,
        collect_handler as collect_callback_handler, finish_travel_job, open_region_handler
    )
except ImportError:
    region_callback_handler, travel_callback_handler, restore_durability_menu_handler, \
    restore_durability_fix_handler, collect_callback_handler, finish_travel_job, open_region_handler = (None,) * 7

try:
    from modules.game_data.market import validate_market_items
except ImportError:
    validate_market_items = None

# Handlers Essenciais (sem try/except pois o bot depende deles)
from handlers.admin.item_grant_conv import item_grant_conversation_handler
from handlers.admin_handler import admin_callback_handler, admin_command_handler, clear_cache_conv_handler
from handlers.admin.file_id_conv import file_id_conv_handler
from handlers.admin.premium_panel import premium_panel_handler, premium_command_handler
from handlers.admin.reset_panel import reset_panel_conversation_handler
from handlers.admin.force_daily import force_daily_handler
from handlers.start_handler import character_creation_handler, start_command_handler, name_command_handler
from handlers.menu_handler import continue_after_action_handler, kingdom_menu_handler, travel_handler
from handlers.menu.kingdom import show_kingdom_menu
from pvp.pvp_handler import pvp_handlers
from handlers.profile_handler import profile_handler
from handlers.status_handler import close_status_handler, status_callback_handler, status_command_handler, status_open_handler
from handlers.inventory_handler import inventory_handler, noop_inventory_handler
from handlers.hunt_handler import hunt_handler
from handlers.combat_handler import combat_handler
from handlers.class_selection_handler import class_selection_handler
from handlers.equipment_handler import equip_pick_handler, equip_slot_handler, equip_unequip_handler, equipment_menu_handler
from handlers.crafting_handler import craft_open_handler
from handlers.enhance_handler import enhance_action_handler, enhance_menu_handler, enhance_select_handler
from handlers.profession_handler import job_menu_handler, job_pick_handler
from handlers.market_handler import *
from handlers.gem_shop import *
from handlers.guild_handler import *
from handlers.class_evolution_handler import *
from modules.player_manager import is_player_premium, iter_players, save_player_data

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)


TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID")) if os.getenv("ADMIN_ID") else None

if not TELEGRAM_TOKEN: raise ValueError("A variável de ambiente TELEGRAM_TOKEN não foi definida!")

try:
    admin_id_str = os.getenv("ADMIN_ID")
    if admin_id_str:
        ADMIN_ID = int(admin_id_str)
except (ValueError, TypeError):
    logging.warning("ADMIN_ID inválido ou não definido.")

if not TELEGRAM_TOKEN:
    raise ValueError("A variável de ambiente TELEGRAM_TOKEN não foi definida!")

ACTION_RESTORERS = {}

def build_action_restorers():
    """Constrói o dicionário de funções para restaurar ações em andamento."""
    global ACTION_RESTORERS
    if finish_collection_job: ACTION_RESTORERS["collecting"] = {"fn": finish_collection_job, "data_builder": lambda st: (st.get("details") or {})}
    if finish_crafting_job: ACTION_RESTORERS["crafting"] = {"fn": finish_crafting_job, "data_builder": lambda st: (st.get("details") or {})}
    if finish_refining_job: ACTION_RESTORERS["refining"] = {"fn": finish_refining_job, "data_builder": lambda st: (st.get("details") or {})}
    if finish_dismantle_job: ACTION_RESTORERS["dismantling"] = {"fn": finish_dismantle_job, "data_builder": lambda st: (st.get("details") or {})}
    if finish_travel_job: ACTION_RESTORERS["travel"] = {"fn": finish_travel_job, "data_builder": lambda st: {"dest": (st.get("details") or {}).get("destination")}}
    logging.info(f"Ações restauráveis carregadas: {list(ACTION_RESTORERS.keys())}")

async def restore_scheduled_jobs(app: Application):
    build_action_restorers()
    if not (job_queue := app.job_queue): return
    now = datetime.now(timezone.utc)
    restored_count = 0
    for user_id, pdata in player_manager.iter_players():
        st = pdata.get("player_state") or {}
        action, finish_iso = st.get("action"), st.get("finish_time")
        if not (action and finish_iso and action in ACTION_RESTORERS): continue
        try:
            finish_time = datetime.fromisoformat(finish_iso).replace(tzinfo=timezone.utc)
            delay = max(0, (finish_time - now).total_seconds())
            restorer, job_data = ACTION_RESTORERS[action], restorer["data_builder"](st)
            chat_id = pdata.get("last_chat_id", user_id)
            job_queue.run_once(restorer["fn"], delay, chat_id=chat_id, user_id=user_id, data=job_data, name=f"{action}:{user_id}")
            restored_count += 1
        except (ValueError, TypeError):
            logging.warning(f"Tempo de finalização inválido para {user_id}. Resetando estado.")
            pdata["player_state"] = {"action": "idle"}
            player_manager.save_player_data(user_id, pdata)
    logging.info(f"[RESTORE] Jobs re-agendados: {restored_count}")

async def check_premium_expirations(context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Verifica periodicamente todos os jogadores para ver se a assinatura premium expirou.
    """
    logging.info("[SCHEDULER] Verificando expiração de contas premium...")
    now = datetime.now(timezone.utc)
    expired_count = 0

    # 1. Itera por todos os jogadores do banco de dados
    for user_id, pdata in player_manager.iter_players():
        try:
            expires_iso = pdata.get("premium_expires_at")

            # 2. Se o jogador não tem data de expiração, pula para o próximo
            if not expires_iso:
                continue

            # 3. Compara a data de expiração com a data/hora atual
            expires_dt = datetime.fromisoformat(expires_iso).replace(tzinfo=timezone.utc)
            
            if now >= expires_dt:
                # 4. Se expirou, limpa os dados premium do jogador
                logging.info(f"Premium do jogador {user_id} expirou. Limpando...")
                pdata["premium_tier"] = None
                pdata["premium_expires_at"] = None
                player_manager.save_player_data(user_id, pdata)
                expired_count += 1

                # 5. Tenta notificar o jogador no privado
                try:
                    await context.bot.send_message(
                        chat_id=user_id,
                        text="Sua assinatura premium expirou! Agradecemos por seu apoio ao Mundo de Eldora."
                    )
                except Exception as e:
                    logging.warning(f"Falha ao notificar jogador {user_id} sobre expiração de premium: {e}")
        
        except Exception as e:
            # Erro ao processar um jogador específico (não para o job inteiro)
            logging.error(f"[PREMIUM] Erro ao verificar premium para o jogador {user_id}: {e}")

    if expired_count > 0:
        logging.info(f"[SCHEDULER] Total de {expired_count} contas premium expiradas foram processadas.")

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logging.error("Exceção ao processar um update:", exc_info=context.error)

def add_if(app, handler, group=None):
    if handler:
        app.add_handler(handler, group=group)

async def send_startup_message(application: Application) -> None:
    if not ADMIN_ID: return
    try:
        msg = "🤖 𝑭𝒂𝒍𝒂 𝑨𝒗𝒆𝒏𝒕𝒖𝒓𝒆𝒊𝒓𝒐 𝒐 👾\n 𝑴𝒖𝒏𝒅𝒐 𝒅𝒆 𝑬𝒍𝒅𝒐𝒓𝒂 𝒂𝒄𝒂𝒃𝒂 𝒅𝒆 𝒓𝒆𝒕𝒐𝒓𝒏𝒂𝒓 𝒅𝒆 𝒔𝒖𝒂 𝑨𝒕𝒖𝒂𝒍𝒊𝒛𝒂𝒄̧𝒂̃𝒐 👾"
        await application.bot.send_message(chat_id=ADMIN_ID, text=msg, parse_mode="Markdown", disable_notification=True)
        logging.info(f"Mensagem de inicialização enviada para ADMIN_ID {ADMIN_ID}")
    except Exception as e:
        logging.warning(f"Não foi possível enviar mensagem de inicialização: {e}")

async def post_initialization(app: Application) -> None:
    """Roda uma vez logo após o bot se conectar."""
    logging.info("Limpando configurações de webhook antigas...")
    await app.bot.delete_webhook()
    
    await restore_scheduled_jobs(app)
    await send_startup_message(app)
    logging.info("Bot conectado e pronto para receber mensagens.")

# ---------------------------------------------------------------------------
# 5. SETUP DOS HANDLERS
# ---------------------------------------------------------------------------
def setup_bot_handlers(application: Application):
    application.bot_data["ADMIN_ID"] = ADMIN_ID
    
    G0_CONVERSATIONS   = 0    
    G2_CALLBACKS_PRIM  = 2   
    G3_COMMANDS        = 3   
    G5_SECONDARY       = 5  
    G9_PARTY           = 9   
    G15_CHAT_LISTENER  = 15 

    # Conversas
    add_if(application, clear_cache_conv_handler, G0_CONVERSATIONS)
    add_if(application, file_id_conv_handler, G0_CONVERSATIONS)
    add_if(application, premium_panel_handler, G0_CONVERSATIONS)
    add_if(application, invite_conversation_handler, G0_CONVERSATIONS)
    add_if(application, reset_panel_conversation_handler, G0_CONVERSATIONS)
    add_if(application, item_grant_conversation_handler, G0_CONVERSATIONS)
    add_if(application, clan_creation_conv_handler, G0_CONVERSATIONS)
    add_if(application, clan_transfer_leader_conv_handler, G0_CONVERSATIONS)
    add_if(application, clan_logo_conv_handler, G0_CONVERSATIONS)
    add_if(application, clan_search_conv_handler,   G0_CONVERSATIONS)
    add_if(application, clan_deposit_conv_handler, G0_CONVERSATIONS)
    add_if(application, clan_withdraw_conv_handler, G0_CONVERSATIONS)

    # Comandos
    add_if(application, admin_command_handler, G3_COMMANDS)
    add_if(application, delete_player_handler, G3_COMMANDS)
    add_if(application, premium_command_handler, G3_COMMANDS)
    add_if(application, force_daily_handler, G3_COMMANDS)
    add_if(application, start_command_handler, G3_COMMANDS)
    add_if(application, gem_shop_command_handler, G3_COMMANDS)
    add_if(application, name_command_handler, G3_COMMANDS)
    add_if(application, evolution_command_handler, G3_COMMANDS)
    add_if(application, status_command_handler,G3_COMMANDS)
    if show_kingdom_menu:
        application.add_handler(CommandHandler("menu", show_kingdom_menu), G3_COMMANDS)
    if show_kingdom_menu:
        application.add_handler(CommandHandler("menu", show_kingdom_menu), G3_COMMANDS)
    if show_kingdom_menu:
        application.add_handler(CommandHandler("menu", show_kingdom_menu), G3_COMMANDS)

    # Callbacks (Botões)
    add_if(application, admin_callback_handler, G2_CALLBACKS_PRIM)
    add_if(application, gem_shop_open_handler, G2_CALLBACKS_PRIM)
    add_if(application, gem_pick_handler, G2_CALLBACKS_PRIM)
    add_if(application, gem_qty_minus_handler, G2_CALLBACKS_PRIM)
    add_if(application, gem_qty_plus_handler, G2_CALLBACKS_PRIM)
    add_if(application, gem_buy_handler, G2_CALLBACKS_PRIM)
    application.bot_data["ADMIN_ID"] = int(ADMIN_ID) if ADMIN_ID else None
    add_if(application, kingdom_menu_handler, G2_CALLBACKS_PRIM)
    add_if(application, kingdom_menu_handler, G2_CALLBACKS_PRIM) 
    add_if(application, travel_handler, G2_CALLBACKS_PRIM)
    add_if(application, profile_handler,               G2_CALLBACKS_PRIM)
    add_if(application, status_open_handler,           G2_CALLBACKS_PRIM)
    add_if(application, status_callback_handler,       G2_CALLBACKS_PRIM)
    add_if(application, close_status_handler,          G2_CALLBACKS_PRIM)
    add_if(application, status_evolution_open_handler, G2_CALLBACKS_PRIM)
    
    add_if(application, open_region_handler,           G2_CALLBACKS_PRIM)
    add_if(application, dismantle_list_handler,      G2_CALLBACKS_PRIM)
    add_if(application, dismantle_preview_handler,   G2_CALLBACKS_PRIM)
    add_if(application, dismantle_confirm_handler,   G2_CALLBACKS_PRIM)
    add_if(application, equipment_menu_handler,        G2_CALLBACKS_PRIM)
    add_if(application, equip_slot_handler,            G2_CALLBACKS_PRIM)
    add_if(application, equip_pick_handler,            G2_CALLBACKS_PRIM)
    add_if(application, equip_unequip_handler,         G2_CALLBACKS_PRIM)

    add_if(application, inventory_handler,             G2_CALLBACKS_PRIM)
    add_if(application, noop_inventory_handler,        G2_CALLBACKS_PRIM)
    add_if(application, hunt_handler,                  G2_CALLBACKS_PRIM)
    add_if(application, combat_handler,                G2_CALLBACKS_PRIM)
    add_if(application, class_selection_handler,       G2_CALLBACKS_PRIM)
    application.add_handlers(pvp_handlers(), group=G2_CALLBACKS_PRIM)
    add_if(application, guild_menu_handler, G2_CALLBACKS_PRIM)
    add_if(application, clan_menu_handler, G2_CALLBACKS_PRIM)
    add_if(application, clan_upgrade_menu_handler, G2_CALLBACKS_PRIM)
    add_if(application, clan_apply_handler, G2_CALLBACKS_PRIM)
    add_if(application, clan_manage_apps_handler, G2_CALLBACKS_PRIM)
    add_if(application, clan_app_accept_handler, G2_CALLBACKS_PRIM)
    add_if(application, clan_app_decline_handler, G2_CALLBACKS_PRIM)
    add_if(application, noop_handler, G2_CALLBACKS_PRIM)
    
    add_if(application, clan_upgrade_confirm_handler, G2_CALLBACKS_PRIM)
    add_if(application, clan_leave_confirm_handler, G2_CALLBACKS_PRIM)
    add_if(application, clan_leave_do_handler, G2_CALLBACKS_PRIM)
    add_if(application, clan_manage_menu_handler, G2_CALLBACKS_PRIM)
    add_if(application, clan_kick_menu_handler, G2_CALLBACKS_PRIM)
    add_if(application, clan_kick_confirm_handler, G2_CALLBACKS_PRIM)
    add_if(application, clan_kick_do_handler, G2_CALLBACKS_PRIM)
    add_if(application, missions_menu_handler, G2_CALLBACKS_PRIM)
    add_if(application, mission_claim_handler, G2_CALLBACKS_PRIM)
    add_if(application, mission_reroll_handler, G2_CALLBACKS_PRIM)
    add_if(application, clan_bank_menu_handler, G2_CALLBACKS_PRIM)
   
    add_if(application, clan_board_purchase_handler, G2_CALLBACKS_PRIM)
    add_if(application, clan_mission_start_handler, G2_CALLBACKS_PRIM)
    add_if(application, clan_mission_confirm_handler, G2_CALLBACKS_PRIM)
    add_if(application, clan_guild_mission_details_handler, G2_CALLBACKS_PRIM)
    add_if(application, forge_handler,                 G2_CALLBACKS_PRIM)
    add_if(application, job_handler,                   G2_CALLBACKS_PRIM)

    add_if(application, craft_open_handler,            G2_CALLBACKS_PRIM)
    add_if(application, enhance_menu_handler,          G2_CALLBACKS_PRIM)
    add_if(application, enhance_select_handler,        G2_CALLBACKS_PRIM)
    add_if(application, enhance_action_handler,        G2_CALLBACKS_PRIM)

    add_if(application, job_menu_handler,              G2_CALLBACKS_PRIM)
    add_if(application, job_pick_handler,              G2_CALLBACKS_PRIM)

    add_if(application, market_open_handler,           G2_CALLBACKS_PRIM)
    add_if(application, market_adventurer_handler,     G2_CALLBACKS_PRIM)
    add_if(application, market_kingdom_handler,        G2_CALLBACKS_PRIM)
    add_if(application, kingdom_set_item_handler,      G2_CALLBACKS_PRIM)
    add_if(application, kingdom_qty_minus_handler,     G2_CALLBACKS_PRIM)
    add_if(application, kingdom_qty_plus_handler,      G2_CALLBACKS_PRIM)
    add_if(application, market_kingdom_buy_handler,    G2_CALLBACKS_PRIM)
    add_if(application, market_kingdom_buy_legacy_handler, G2_CALLBACKS_PRIM)
    add_if(application, market_list_handler,           G2_CALLBACKS_PRIM)
    add_if(application, market_my_handler,             G2_CALLBACKS_PRIM)
    add_if(application, market_sell_handler,           G2_CALLBACKS_PRIM)
    add_if(application, market_buy_handler,            G2_CALLBACKS_PRIM)
    add_if(application, market_cancel_handler,         G2_CALLBACKS_PRIM)
    add_if(application, market_pick_unique_handler,    G2_CALLBACKS_PRIM)
    add_if(application, market_pick_stack_handler,     G2_CALLBACKS_PRIM)
    add_if(application, market_qty_handler,            G2_CALLBACKS_PRIM)
    add_if(application, market_price_spin_handler,     G2_CALLBACKS_PRIM)
    add_if(application, market_price_confirm_handler,  G2_CALLBACKS_PRIM)
    add_if(application, market_cancel_new_handler,     G2_CALLBACKS_PRIM)
    add_if(application, region_callback_handler,       G2_CALLBACKS_PRIM)
    add_if(application, restore_durability_menu_handler, G2_CALLBACKS_PRIM)
    add_if(application, restore_durability_fix_handler,  G2_CALLBACKS_PRIM)
    add_if(application, collect_callback_handler,      G2_CALLBACKS_PRIM)
    add_if(application, continue_after_action_handler, G2_CALLBACKS_PRIM) # <-- NOVO
    add_if(application, kingdom_menu_handler, G2_CALLBACKS_PRIM)          # <-- NOVO

    add_if(application, refining_main_handler,         G2_CALLBACKS_PRIM)
    add_if(application, ref_select_handler,            G2_CALLBACKS_PRIM)
    add_if(application, ref_confirm_handler,           G2_CALLBACKS_PRIM)

    if refining_main_callback:
        application.add_handler(
            CallbackQueryHandler(
                refining_main_callback,
                pattern=r"^(ref_menu|refining_main|menu_refino|refino_main|open_refino)$",
            ),
            G2_CALLBACKS_PRIM,
        )

    # 🏰 Calabouço (runtime)
    add_if(application, dungeon_open_handler,          G2_CALLBACKS_PRIM)
    add_if(application, dungeon_pick_handler,          G2_CALLBACKS_PRIM)



    # Handlers de Fundo e Erro
    add_if(application, character_creation_handler,    G5_SECONDARY)

    
    # Party callbacks (baixíssima prioridade comparada às conversas)
    add_if(application, party_callback_handler,        G9_PARTY)
    add_if(application, chat_interaction_handler,      G15_CHAT_LISTENER)
    application.add_error_handler(error_handler)
    
    logging.info("Handlers do bot configurados.")

# ---------------------------------------------------------------------------
# 7. EXECUÇÃO PRINCIPAL
# ---------------------------------------------------------------------------

def main() -> None:
    """Função principal que constrói e roda o bot."""
    
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).post_init(post_initialization).build()

    setup_bot_handlers(app)

    if jq := app.job_queue:
        jq.run_repeating(regenerate_energy_job, interval=300)
        jq.run_repeating(check_premium_expirations, interval=21600)
        
        tz_fortaleza = ZoneInfo("America/Fortaleza")
        jq.run_daily(daily_crystal_grant_job, time=time(hour=0, minute=5, tzinfo=tz_fortaleza))
        jq.run_daily(daily_pvp_entry_reset_job, time=time(hour=0, minute=10, tzinfo=tz_fortaleza))

    logging.info("Iniciando bot em modo Polling...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()