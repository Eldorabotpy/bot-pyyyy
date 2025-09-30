# modules/game_data/class_evolution.py
from __future__ import annotations
from typing import Dict, Any, List

"""
EVOLUTIONS:
- Mapa de evolução por classe-base -> opções de evolução T2 e T3.
- Cada entrada define: nível mínimo, itens necessários, descrição e preview de bônus.
- "to": nome da classe-alvo (deve existir nas suas classes ou você pode exibir como "classe nova").
- "media_key": chave para buscar mídia (video/foto) em assets/file_ids.json via modules.file_ids
"""

EVOLUTIONS: Dict[str, Dict[str, Any]] = {
    # =========================
    # GUERREIRO
    # =========================
    "guerreiro": {
        "tier2": [
            {
                "to": "cavaleiro",
                "min_level": 25,
                "required_items": {"emblema_guerreiro": 25, "essencia_guardia": 25}, 
                "desc": "Defesa elevada e proteção de aliados.",
                "preview_mods": {"hp": "+25%", "defense": "+22%", "attack": "+15%"},
                "media_key": "evo_guerreiro_to_cavaleiro_video",
            },
            {
                "to": "gladiador",
                "min_level": 35,
                "required_items": {"emblema_guerreiro": 35, "essencia_furia": 35},
                "desc": "Ofensiva agressiva e golpes em área.",
                "preview_mods": {"attack": "+24%", "hp": "+20%", "initiative": "+16%"},
                "media_key": "evo_guerreiro_to_gladiador_video",
            },
        ],
        "tier3": [
            {
                "from_any_of": ["cavaleiro", "gladiador"],
                "to": "templario",
                "min_level": 60,
                "required_items": {"selo_sagrado": 50, "essencia_luz": 50},
                "desc": "Paladino sagrado: defesa + suporte.",
                "preview_mods": {"defense": "+32%", "hp": "+20%", "luck": "+12%"},
                "media_key": "evo_guerreiro_to_templario_video",
            },
        ],
    },

    # =========================
    # BERSERKER
    # =========================
    "berserker": {
        "tier2": [
            {
                "to": "barbaro",
                "min_level": 25,
                "required_items": {"emblema_berserker": 25, "essencia_furia": 25},
                "desc": "Dano bruto e resistência à quebra de controle.",
                "preview_mods": {"attack": "+26%", "hp": "+16%"},
                "media_key": "evo_berserker_to_barbaro_video",
            },
            {
                "to": "juggernaut",
                "min_level": 35,
                "required_items": {"emblema_berserker": 35, "essencia_guardia": 35},
                "desc": "Avanços imparáveis e mitigação.",
                "preview_mods": {"hp": "+24%", "defense": "+15%", "attack": "+36%"},
                "media_key": "evo_berserker_to_juggernaut_video",
            },
        ],
        "tier3": [
            {
                "from_any_of": ["barbaro", "juggernaut"],
                "to": "ira_primordial",
                "min_level": 60,
                "required_items": {"totem_ancestral": 50, "essencia_furia": 50},
                "desc": "Forma ancestral que amplifica dano conforme a vida cai.",
                "preview_mods": {"attack": "+38%", "initiative": "+18%"},
                "media_key": "evo_berserker_to_ira_primordial_video",
            }
        ],
    },

    # =========================
    # CACADOR
    # =========================
    "cacador": {
        "tier2": [
            {
                "to": "arqueiro_sombrio",
                "min_level": 25,
                "required_items": {"emblema_cacador": 25, "essencia_sombra": 25},
                "desc": "DPS à distância e debuffs de escuridão.",
                "preview_mods": {"initiative": "+20%", "attack": "+25%", "luck": "+16%"},
                "media_key": "evo_cacador_to_arqueiro_sombrio_video",
            },
            {
                "to": "sniper",
                "min_level": 35,
                "required_items": {"emblema_cacador": 35, "essencia_precisao": 35},
                "desc": "Críticos elevados contra alvos isolados.",
                "preview_mods": {"attack": "+25%", "luck": "+16%"},
                "media_key": "evo_cacador_to_sniper_video",
            },
        ],
        "tier3": [
            {
                "from_any_of": ["arqueiro_sombrio", "sniper"],
                "to": "mestre_caçador",
                "min_level": 60,
                "required_items": {"marca_predador": 50, "essencia_fera": 50},
                "desc": "Controle de feras e bônus contra monstros raros.",
                "preview_mods": {"initiative": "+25%", "attack": "+32%"},
                "media_key": "evo_cacador_to_mestre_cacador_video",
            }
        ],
    },

    # =========================
    # MONGE
    # =========================
    "monge": {
        "tier2": [
            {
                "to": "guardiao",
                "min_level": 25,
                "required_items": {"emblema_monge": 25, "essencia_guardia": 25},
                "desc": "Escudos de ki e contra-ataques.",
                "preview_mods": {"defense": "+35%", "hp": "+25%"},
                "media_key": "evo_monge_to_guardiao_video",
            },
            {
                "to": "mestre_do_ki",
                "min_level": 35,
                "required_items": {"emblema_monge": 35, "essencia_ki": 35},
                "desc": "Canalização de ki para dano e cura.",
                "preview_mods": {"attack": "+30%", "initiative": "+38%", "luck": "+35%"},
                "media_key": "evo_monge_to_mestre_do_ki_video",
            },
        ],
        "tier3": [
            {
                "from_any_of": ["guardiao", "mestre_do_ki"],
                "to": "santo_asceta",
                "min_level": 60,
                "required_items": {"reliquia_mistica": 50, "essencia_luz": 50, "essencia_ki": 50},
                "desc": "Mitigação em equipe e cura periódica.",
                "preview_mods": {"defense": "+40%", "hp": "+32%"},
                "media_key": "evo_monge_to_santo_asceta_video",
            }
        ],
    },

    # =========================
    # MAGO
    # =========================
    "mago": {
        "tier2": [
            {
                "to": "feiticeiro",
                "min_level": 25,
                "required_items": {"emblema_mago": 25, "essencia_arcana": 25},
                "desc": "Controle + dano contínuo (DoT).",
                "preview_mods": {"attack": "+24%", "luck": "+16%"},
                "media_key": "evo_mago_to_feiticeiro_video",
            },
            {
                "to": "elementalista",
                "min_level": 35,
                "required_items": {"emblema_mago": 35, "essencia_elemental": 35},
                "desc": "Explosões elementais (fogo, gelo, raio).",
                "preview_mods": {"attack": "+22%", "initiative": "+18%"},
                "media_key": "evo_mago_to_elementalista_video",
            },
        ],
        "tier3": [
            {
                "from_any_of": ["feiticeiro", "elementalista"],
                "to": "arquimago",
                "min_level": 60,
                "required_items": {"grimorio_arcano": 50, "essencia_arcana": 50},
                "desc": "Amplificação de dano mágico e redução do custo.",
                "preview_mods": {"attack": "+28%", "luck": "+18%"},
                "media_key": "evo_mago_to_arquimago_video",
            }
        ],
    },

    # =========================
    # BARDO
    # =========================
    "bardo": {
        "tier2": [
            {
                "to": "menestrel",
                "min_level": 25,
                "required_items": {"emblema_bardo": 25, "essencia_harmonia": 25},
                "desc": "Buffs de grupo e amplificação de cura.",
                "preview_mods": {"luck": "+22%", "initiative": "+16%"},
                "media_key": "evo_bardo_to_menestrel_video",
            },
            {
                "to": "encantador",
                "min_level": 35,
                "required_items": {"emblema_bardo": 35, "essencia_encanto": 35},
                "desc": "Controle mental e debuffs rítmicos.",
                "preview_mods": {"luck": "+25%", "attack": "+18%"},
                "media_key": "evo_bardo_to_encantador_video",
            },
        ],
        "tier3": [
            {
                "from_any_of": ["menestrel", "encantador"],
                "to": "maestro",
                "min_level": 60,
                "required_items": {"batuta_maestria": 50, "essencia_harmonia": 50},
                "desc": "Orquestra sinérgica que encadeia buffs.",
                "preview_mods": {"luck": "+34%", "initiative": "+28%"},
                "media_key": "evo_bardo_to_maestro_video",
            }
        ],
    },

    # =========================
    # ASSASSINO
    # =========================
    "assassino": {
        "tier2": [
            {
                "to": "ninja",
                "min_level": 25,
                "required_items": {"emblema_assassino": 25, "essencia_sombra": 25},
                "desc": "Furtividade e múltiplos acertos rápidos.",
                "preview_mods": {"initiative": "+22%", "luck": "+18%"},
                "media_key": "evo_assassino_to_ninja_video",
            },
            {
                "to": "duelista",
                "min_level": 35,
                "required_items": {"emblema_assassino": 35, "essencia_letal": 35},
                "desc": "Foco em 1x1 e contra-golpes.",
                "preview_mods": {"attack": "+25%", "initiative": "+16%"},
                "media_key": "evo_assassino_to_duelista_video",
            },
        ],
        "tier3": [
            {
                "from_any_of": ["ninja", "duelista"],
                "to": "sombra_inexoravel",
                "min_level": 60,
                "required_items": {"manto_eterno": 50, "essencia_sombra": 50},
                "desc": "Velocidade máxima e críticos ampliados.",
                "preview_mods": {"initiative": "+36%", "luck": "+30%"},
                "media_key": "evo_assassino_to_sombra_inexoravel_video",
            }
        ],
    },

    # =========================
    # SAMURAI
    # =========================
    "samurai": {
        "tier2": [
            {
                "to": "ronin",
                "min_level": 25,
                "required_items": {"emblema_samurai": 25, "essencia_corte": 25},
                "desc": "Golpes independentes com foco em autonomia.",
                "preview_mods": {"attack": "+32%", "defense": "+16%"},
                "media_key": "evo_samurai_to_ronin_video",
            },
            {
                "to": "kensei",
                "min_level": 35,
                "required_items": {"emblema_samurai": 35, "essencia_disciplina": 35},
                "desc": "Precisão técnica e janelas de contra-ataque.",
                "preview_mods": {"attack": "+30%", "initiative": "+28%"},
                "media_key": "evo_samurai_to_kensei_video",
            },
        ],
        "tier3": [
            {
                "from_any_of": ["ronin", "kensei"],
                "to": "iaijutsu",
                "min_level": 60,
                "required_items": {"lamina_sagrada": 50, "essencia_disciplina": 50},
                "desc": "Execuções instantâneas e rupturas de postura.",
                "preview_mods": {"attack": "+36%", "initiative": "+30%"},
                "media_key": "evo_samurai_to_iaijutsu_video",
            }
        ],
    },
}


def get_evolution_options(
    current_class: str,
    current_level: int,
    show_locked: bool = True,
) -> List[dict]:
    """
    Retorna as opções de evolução da classe atual.

    - show_locked=True (padrão): retorna também as opções abaixo do nível mínimo,
      para que a UI possa exibir os requisitos (nível/itens) mesmo que ainda não
      estejam atendidos.
    - show_locked=False: retorna apenas as opções liberadas pelo nível.
    """
    curr_key = (current_class or "").lower()
    data = EVOLUTIONS.get(curr_key)
    if not data:
        return []

    options: List[dict] = []
    for tier in ("tier2", "tier3"):
        for opt in data.get(tier, []):
            # Valida 'from_any_of' de forma case-insensitive (se existir)
            req_from = opt.get("from_any_of")
            if isinstance(req_from, list):
                allowed = {str(x).lower() for x in req_from}
                if curr_key not in allowed:
                    continue  # este ramo não pode evoluir para esta opção

            # Checa nível mínimo
            min_lvl = int(opt.get("min_level", 0))
            if show_locked or current_level >= min_lvl:
                options.append({"tier": tier, **opt})
    return options
