# modules/game_data/class_evolution.py (VERSÃO ATUALIZADA COM "unlocks_skills")

from __future__ import annotations
from typing import Dict, Any, List
import logging
logger = logging.getLogger(__name__)

EVOLUTIONS: Dict[str, Dict[str, Any]] = {
    # ========================= # GUERREIRO # =========================
    "guerreiro": {
        "tier2": [
            {
                "to": "cavaleiro", "min_level": 25,
                "required_items": {"emblema_guerreiro": 25, "essencia_guardia": 25}, 
                "desc": "Defesa elevada e proteção de aliados.",
                # --- MUDANÇA ---
                "unlocks_skills": ["passive_bulwark"], 
                "trial_monster_id": "guardian_of_the_aegis",
            },
            {
                "to": "gladiador", "min_level": 35,
                "required_items": {"emblema_guerreiro": 35, "essencia_furia": 35},
                "desc": "Ofensiva agressiva e golpes em área.",
                # --- MUDANÇA ---
                "unlocks_skills": ["active_whirlwind"], 
                "trial_monster_id": "phantom_of_the_arena",
            },
        ],
        "tier3": [
            {
                "from_any_of": ["cavaleiro", "gladiador"], "to": "templario", "min_level": 60,
                "required_items": {"selo_sagrado": 50, "essencia_luz": 50},
                "desc": "Paladino sagrado que combina defesa com suporte divino.",
                # --- MUDANÇA ---
                # (Ganha a skill que sobrou do pacote de "Guerreiro")
                "unlocks_skills": ["active_holy_blessing"], 
                "trial_monster_id": "aspect_of_the_divine",
            },
        ],
    },

    # ========================= # BERSERKER # =========================
    "berserker": {
        "tier2": [
            {
                "to": "barbaro", "min_level": 25,
                "required_items": {"emblema_berserker": 25, "essencia_furia": 25},
                "desc": "Dano bruto e resistência a controlo.",
                # --- MUDANÇA ---
                "unlocks_skills": ["passive_unstoppable"], 
                "trial_monster_id": "primal_spirit_of_rage",
            },
            {
                "to": "juggernaut", "min_level": 35,
                "required_items": {"emblema_berserker": 35, "essencia_guardia": 35},
                "desc": "Avanços imparáveis e mitigação de dano.",
                # --- MUDANÇA ---
                "unlocks_skills": ["active_unbreakable_charge"], 
                "trial_monster_id": "guardian_of_the_mountain",
            },
        ],
        "tier3": [
            {
                "from_any_of": ["barbaro", "juggernaut"], "to": "ira_primordial", "min_level": 60,
                "required_items": {"totem_ancestral": 50, "essencia_furia": 50},
                "desc": "Forma ancestral que amplifica dano conforme a vida cai.",
                # --- MUDANÇA ---
                "unlocks_skills": ["passive_last_stand"],
                "trial_monster_id": "avatar_of_primal_wrath",
            }
        ],
    },

    # ========================= # CAÇADOR # =========================
    "cacador": {
        "tier2": [
            {
                "to": "patrulheiro", "min_level": 25,
                "required_items": {"emblema_cacador": 25, "essencia_fera": 25},
                "desc": "Mestre da sobrevivência que luta ao lado de um companheiro animal.",
                # --- MUDANÇA ---
                "unlocks_skills": ["passive_animal_companion"], 
                "trial_monster_id": "spirit_of_the_alpha_wolf",
            },
            {
                "to": "franco_atirador", "min_level": 35,
                "required_items": {"emblema_cacador": 35, "essencia_precisao": 35},
                "desc": "Especialista em tiros à distância com dano crítico devastador.",
                # --- MUDANÇA ---
                "unlocks_skills": ["active_deadeye_shot"], 
                "trial_monster_id": "phantom_of_the_watchtower",
            },
        ],
        "tier3": [
            {
                "from_any_of": ["patrulheiro", "franco_atirador"], "to": "mestre_da_selva", "min_level": 60,
                "required_items": {"marca_predador": 50, "essencia_fera": 50},
                "desc": "O predador alfa, capaz de domar as feras mais selvagens.",
                # --- MUDANÇA ---
                "unlocks_skills": ["passive_apex_predator"], 
                "trial_monster_id": "aspect_of_the_world_tree",
            }
        ],
    },

    # ========================= # MONGE # =========================
    "monge": {
        "tier2": [
            {
                "to": "guardiao_do_templo", "min_level": 25,
                "required_items": {"emblema_monge": 25, "essencia_guardia": 25},
                "desc": "Mestre da defesa que usa o Ki para criar barreiras e contra-atacar.",
                # --- MUDANÇA ---
                "unlocks_skills": ["active_iron_skin"], 
                "trial_monster_id": "statue_of_the_serene_fist",
            },
            {
                "to": "punho_elemental", "min_level": 35,
                "required_items": {"emblema_monge": 35, "essencia_ki": 35},
                "desc": "Lutador que canaliza a fúria dos elementos nos seus punhos.",
                # --- MUDANÇA ---
                "unlocks_skills": ["passive_elemental_strikes"], 
                "trial_monster_id": "avatar_of_the_four_elements",
            },
        ],
        "tier3": [
            {
                "from_any_of": ["guardiao_do_templo", "punho_elemental"], "to": "ascendente", "min_level": 60,
                "required_items": {"reliquia_mistica": 50, "essencia_ki": 50},
                "desc": "Atingiu a transcendência, movendo-se como o vento e golpeando como o trovão.",
                # --- MUDANÇA ---
                "unlocks_skills": ["active_transcendence"], 
                "trial_monster_id": "echo_of_the_grandmaster",
            }
        ],
    },

    # ========================= # MAGO # =========================
    "mago": {
        "tier2": [
            {
                "to": "feiticeiro", "min_level": 25,
                "required_items": {"emblema_mago": 25, "essencia_arcana": 25},
                "desc": "Mestre das maldições e do dano contínuo (DoT).",
                # --- MUDANÇA ---
                "unlocks_skills": ["active_curse_of_weakness"], 
                "trial_monster_id": "shade_of_the_forbidden_library",
            },
            {
                "to": "elementalista", "min_level": 35,
                "required_items": {"emblema_mago": 35, "essencia_elemental": 35},
                "desc": "Especialista em dano elemental massivo e em área.",
                # --- MUDANÇA ---
                "unlocks_skills": ["passive_elemental_attunement"], 
                "trial_monster_id": "raging_elemental_vortex",
            },
        ],
        "tier3": [
            {
                "from_any_of": ["feiticeiro", "elementalista"], "to": "arquimago", "min_level": 60,
                "required_items": {"grimorio_arcano": 50, "essencia_arcana": 50},
                "desc": "Um canal de poder arcano puro, capaz de alterar a realidade.",
                # --- MUDANÇA ---
                "unlocks_skills": ["active_meteor_swarm"], 
                "trial_monster_id": "essence_of_pure_magic",
            }
        ],
    },
    
    # ... (Bardo, Assassino, Samurai - o mesmo padrão) ...
    
    # ========================= # BARDO # =========================
    "bardo": {
        "tier2": [
            {
                "to": "menestrel", "min_level": 25,
                "required_items": {"emblema_bardo": 25, "essencia_harmonia": 25},
                "desc": "Focado em canções que curam e fortalecem os aliados.",
                # --- MUDANÇA ---
                "unlocks_skills": ["active_song_of_valor"], 
                "trial_monster_id": "echo_of_the_first_ballad",
            },
            {
                "to": "encantador", "min_level": 35,
                "required_items": {"emblema_bardo": 35, "essencia_encanto": 35},
                "desc": "Usa melodias para confundir e debilitar os inimigos.",
                # --- MUDANÇA ---
                "unlocks_skills": ["active_dissonant_melody"], 
                "trial_monster_id": "siren_of_the_lost_stage",
            },
        ],
        "tier3": [
            {
                "from_any_of": ["menestrel", "encantador"], "to": "maestro", "min_level": 60,
                "required_items": {"batuta_maestria": 50, "essencia_harmonia": 50},
                "desc": "Rege o campo de batalha com sinfonias de poder.",
                # --- MUDANÇA ---
                "unlocks_skills": ["passive_symphony_of_power"], 
                "trial_monster_id": "avatar_of_the_grand_orchestra",
            }
        ],
    },

    # ========================= # ASSASSINO # =========================
    "assassino": {
        "tier2": [
            {
                "to": "sombra", "min_level": 25,
                "required_items": {"emblema_assassino": 25, "essencia_sombra": 25},
                "desc": "Mestre da furtividade e de ataques surpresa devastadores.",
                # --- MUDANÇA ---
                "unlocks_skills": ["active_shadow_strike"], 
                "trial_monster_id": "doppelganger_of_the_throne",
            },
            {
                "to": "venefico", "min_level": 35,
                "required_items": {"emblema_assassino": 35, "essencia_letal": 35},
                "desc": "Especialista em venenos e toxinas que causam dano ao longo do tempo.",
                # --- MUDANÇA ---
                "unlocks_skills": ["passive_potent_toxins"], 
                "trial_monster_id": "spirit_of_the_swamp_adder",
            },
        ],
        "tier3": [
            {
                "from_any_of": ["sombra", "venefico"], "to": "mestre_das_laminas", "min_level": 60,
                "required_items": {"manto_eterno": 50, "essencia_sombra": 50},
                "desc": "Um vulto letal cuja velocidade é inigualável.",
                # --- MUDANÇA ---
                "unlocks_skills": ["active_dance_of_a_thousand_cuts"], 
                "trial_monster_id": "specter_of_the_silent_kill",
            }
        ],
    },

    # ========================= # SAMURAI # =========================
    "samurai": {
        "tier2": [
            {
                "to": "kensei", "min_level": 25,
                "required_items": {"emblema_samurai": 25, "essencia_corte": 25},
                "desc": "O Santo da Espada, focado na perfeição técnica de cada golpe.",
                # --- MUDANÇA ---
                "unlocks_skills": ["passive_iai_stance"], 
                "trial_monster_id": "phantom_of_the_dojo",
            },
            {
                "to": "ronin", "min_level": 35,
                "required_items": {"emblema_samurai": 35, "essencia_disciplina": 35},
                "desc": "Um guerreiro solitário, mestre do contra-ataque e da sobrevivência.",
                # --- MUDANÇA ---
                "unlocks_skills": ["active_parry_and_riposte"], 
                "trial_monster_id": "spirit_of_the_wandering_warrior",
            },
        ],
        "tier3": [
            {
                "from_any_of": ["kensei", "ronin"], "to": "shogun", "min_level": 60,
                "required_items": {"lamina_sagrada": 50, "essencia_disciplina": 50},
                "desc": "Um líder no campo de batalha, cujas ordens inspiram os aliados.",
                # --- MUDANÇA ---
                "unlocks_skills": ["active_banner_of_command"], 
                "trial_monster_id": "avatar_of_the_first_emperor",
            }
        ],
    },
}

# --- MUDANÇA: A função get_evolution_options foi removida daqui ---
# (Ela estava no teu ficheiro, mas o teu 'class_evolution_handler.py'
# importa-a de 'modules.game_data.class_evolution', então está correto.)
# Se ela só existir aqui, mantemos. Se não, removemos.
# Vou assumir que ela fica aqui, como no teu ficheiro original.

def get_evolution_options(
    current_class: str,
    current_level: int,
    show_locked: bool = True,
) -> List[dict]:
    """
    Retorna as opções de evolução da classe atual.
    (Esta função já não funciona para T3, precisa ser corrigida,
     mas está igual ao ficheiro que enviaste)
    """
    curr_key = (current_class or "").lower()
    data = EVOLUTIONS.get(curr_key)
    if not data:
        return []

    options: List[dict] = []
    for tier in ("tier2", "tier3"):
        for opt in data.get(tier, []):
            req_from = opt.get("from_any_of")
            if isinstance(req_from, list):
                allowed = {str(x).lower() for x in req_from}
                if curr_key not in allowed:
                    continue 

            min_lvl = int(opt.get("min_level", 0))
            if show_locked or current_level >= min_lvl:
                options.append({"tier": tier, **opt})
    return options

# Em: modules/game_data/class_evolution.py
# (COLE ESTE CÓDIGO NO FINAL DO FICHEIRO)

# --- INÍCIO DO NOVO CÓDIGO (CORREÇÃO DO BUG DE SKILL) ---

# Cache para guardar o mapa de classes base (Ex: "arquimago" -> "mago")
_EVOLUTION_BASE_CLASS_MAP: Dict[str, str] = {}

def _get_base_class(class_key: str) -> str:
    """
    Função auxiliar interna para encontrar a classe base de qualquer classe.
    Usa o _EVOLUTION_BASE_CLASS_MAP como cache.
    """
    if not class_key: 
        return class_key
        
    # 1. Se já está no cache, retorna imediatamente
    if class_key in _EVOLUTION_BASE_CLASS_MAP:
        return _EVOLUTION_BASE_CLASS_MAP[class_key]
    
    # 2. Se o cache está vazio, constrói-o
    if not _EVOLUTION_BASE_CLASS_MAP:
        logger.info("[ClassEvolution] Construindo mapa de classes base...")
        for base_class, tiers in EVOLUTIONS.items():
            # A classe base (ex: "mago") aponta para si mesma
            _EVOLUTION_BASE_CLASS_MAP[base_class] = base_class
            
            # Itera T2, T3... e mapeia todas evoluções para a classe base
            for tier_name, tier_list in tiers.items():
                if isinstance(tier_list, list):
                    for evo in tier_list:
                        evo_to_key = evo.get("to")
                        if evo_to_key:
                            # Ex: _EVOLUTION_BASE_CLASS_MAP["arquimago"] = "mago"
                            _EVOLUTION_BASE_CLASS_MAP[evo_to_key] = base_class

    # 3. Retorna o resultado (seja a classe base ou a própria classe, se não for uma evolução)
    base_class_result = _EVOLUTION_BASE_CLASS_MAP.get(class_key, class_key)
    
    # 4. Guarda no cache para a próxima vez
    _EVOLUTION_BASE_CLASS_MAP[class_key] = base_class_result
    return base_class_result

def can_player_use_skill(player_class_key: str, allowed_classes: List[str]) -> bool:
    """
    Verifica se um jogador pode usar uma skill, checando a sua classe 
    ATUAL e a sua classe BASE.
    """
    if not allowed_classes:
        return True # Skill universal (lista de permissão vazia)
    
    allowed_set = set(allowed_classes)
    
    # 1. Verifica a classe atual (ex: "arcanista" está em ["arcanista"])
    if player_class_key in allowed_set:
        return True
    
    # 2. Verifica a classe BASE (ex: "mago" (base de "arcanista") está em ["mago"])
    base_class = _get_base_class(player_class_key)
    if base_class in allowed_set:
        return True
    
    # Se nenhum passou, o jogador não pode usar
    return False

# --- FIM DO NOVO CÓDIGO ---