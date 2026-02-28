# modules/game_data/equipment.py

SLOT_EMOJI = {
    "elmo": "🪖",
    "armadura": "👕",
    "calca": "👖",
    "luvas": "🧤",
    "botas": "🥾",
    "colar": "📿",
    "anel": "💍",
    "brinco": "🧿",
    "arma": "⚔️",
    "tool": "🛠️",
}

# Ordem canônica usada nos handlers/menus
SLOT_ORDER = ["tool", "arma", "elmo", "armadura", "calca", "luvas", "botas", "colar", "anel", "brinco"]

# Regras por slot (stats primários)
# - "class_attribute": usa o atributo primário da CLASSE (vide CLASS_PRIMARY_ATTRIBUTE em classes.py)
# - "primary_stat": usa um atributo fixo para o slot, independente da classe
ITEM_SLOTS = {
    "arma": {"primary_stat_type": "class_attribute"},
    "anel": {"primary_stat_type": "class_attribute"},
    "brinco": {"primary_stat_type": "class_attribute"},

    "elmo": {"primary_stat": "vida"},
    "armadura": {"primary_stat": "vida"},
    "calca": {"primary_stat": "vida"},
    "colar": {"primary_stat": "vida"},
    "botas": {"primary_stat": "agilidade"},
    "luvas": {"primary_stat": "sorte"},
}

SLOT_LABELS = {
    "tool": "Ferramenta"
}

# ============================================================================
# SISTEMA DE CONJUNTOS (SET BONUSES) - CATACUMBAS
# ============================================================================
SETS_DATABASE = {
    "set_heranca_real": {
        "nome": "Herança do Rei Caído",
        "pecas_necessarias": 6, 
        "buffs": {
            "max_hp_mult": 0.25, # +25% de Vida Máxima
        },
        "descricao": "A aura do antigo rei envolve o portador. (Bónus: +25% Vida, +20 Defesa)"
    }
}
# ============================================================================
# BANCO DE DADOS MESTRE DE ITENS EQUIPÁVEIS (NOVOS)
# ============================================================================

ITEM_DATABASE = {
    # --------------------------------------------------------------
    # Conjunto dungeon (ajustado para 'armadura')
    # --------------------------------------------------------------
    "peitoral_coracao_umbrio": {"slot": "armadura", "nome_exibicao": "Peitoral Coração Umbrio"},
    "tunica_coracao_umbrio":   {"slot": "armadura", "nome_exibicao": "Túnica Coração Umbrio"},

    # --------------------------------------------------------------------
    # TIER 1 / TIER 2: GUERREIRO
    # --------------------------------------------------------------------
    "espada_ferro_guerreiro":     {"slot": "arma",     "nome_exibicao": "Espada de Ferro do Guerreiro"},
    "elmo_ferro_guerreiro":       {"slot": "elmo",     "nome_exibicao": "Elmo de Ferro do Guerreiro"},
    "peitoral_ferro_guerreiro":   {"slot": "armadura", "nome_exibicao": "Peitoral de Ferro do Guerreiro"},
    "calcas_ferro_guerreiro":     {"slot": "calca",    "nome_exibicao": "Calças de Ferro do Guerreiro"},
    "botas_ferro_guerreiro":      {"slot": "botas",    "nome_exibicao": "Botas de Ferro do Guerreiro"},
    "luvas_ferro_guerreiro":      {"slot": "luvas",    "nome_exibicao": "Luvas de Ferro do Guerreiro"},
    "anel_ferro_guerreiro":       {"slot": "anel",     "nome_exibicao": "Anel de Ferro do Guerreiro"},
    "colar_ferro_guerreiro":      {"slot": "colar",    "nome_exibicao": "Colar de Ferro do Guerreiro"},
    "brinco_ferro_guerreiro":     {"slot": "brinco",   "nome_exibicao": "Brinco de Ferro do Guerreiro"},

    "espada_aco_guerreiro":       {"slot": "arma",     "nome_exibicao": "Espada de Aço do Guerreiro"},
    "elmo_aco_guerreiro":         {"slot": "elmo",     "nome_exibicao": "Elmo de Aço do Guerreiro"},
    "peitoral_aco_guerreiro":     {"slot": "armadura", "nome_exibicao": "Peitoral de Aço do Guerreiro"},
    "calcas_aco_guerreiro":       {"slot": "calca",    "nome_exibicao": "Calças de Aço do Guerreiro"},
    "botas_aco_guerreiro":        {"slot": "botas",    "nome_exibicao": "Botas de Aço do Guerreiro"},
    "luvas_aco_guerreiro":        {"slot": "luvas",    "nome_exibicao": "Luvas de Aço do Guerreiro"},
    "anel_aco_guerreiro":         {"slot": "anel",     "nome_exibicao": "Anel de Aço do Guerreiro"},
    "colar_aco_guerreiro":        {"slot": "colar",    "nome_exibicao": "Colar de Aço do Guerreiro"},
    "brinco_aco_guerreiro":       {"slot": "brinco",   "nome_exibicao": "Brinco de Aço do Guerreiro"},

    # =====================================================================
    # MAGO — T1/T2
    # =====================================================================
    "cajado_aprendiz_mago":   {"slot": "arma",     "nome_exibicao": "Cajado de Aprendiz"},
    "chapeu_seda_mago":       {"slot": "elmo",     "nome_exibicao": "Chapéu de Seda do Mago"},
    "tunica_seda_mago":       {"slot": "armadura", "nome_exibicao": "Túnica de Seda do Mago"},
    "calcas_seda_mago":       {"slot": "calca",    "nome_exibicao": "Calças de Seda do Mago"},
    "botas_seda_mago":        {"slot": "botas",    "nome_exibicao": "Botas de Seda do Mago"},
    "luvas_seda_mago":        {"slot": "luvas",    "nome_exibicao": "Luvas de Seda do Mago"},
    "anel_gema_mago":         {"slot": "anel",     "nome_exibicao": "Anel de Gema do Mago"},
    "colar_gema_mago":        {"slot": "colar",    "nome_exibicao": "Colar de Gema do Mago"},
    "brinco_gema_mago":       {"slot": "brinco",   "nome_exibicao": "Brinco de Gema do Mago"},

    "cajado_arcano_mago":     {"slot": "arma",     "nome_exibicao": "Cajado Arcano"},
    "chapeu_veludo_mago":     {"slot": "elmo",     "nome_exibicao": "Chapéu de Veludo do Mago"},
    "tunica_veludo_mago":     {"slot": "armadura", "nome_exibicao": "Túnica de Veludo do Mago"},
    "calcas_veludo_mago":     {"slot": "calca",    "nome_exibicao": "Calças de Veludo do Mago"},
    "botas_veludo_mago":      {"slot": "botas",    "nome_exibicao": "Botas de Veludo do Mago"},
    "luvas_veludo_mago":      {"slot": "luvas",    "nome_exibicao": "Luvas de Veludo do Mago"},
    "anel_runico_mago":       {"slot": "anel",     "nome_exibicao": "Anel Rúnico do Mago"},
    "colar_runico_mago":      {"slot": "colar",    "nome_exibicao": "Colar Rúnico do Mago"},
    "brinco_runico_mago":     {"slot": "brinco",   "nome_exibicao": "Brinco Rúnico do Mago"},

    # =====================================================================
    # BERSERKER — T1/T2
    # =====================================================================
    "machado_rustico_berserker":   {"slot": "arma",     "nome_exibicao": "Machado Rústico do Berserker"},
    "elmo_chifres_berserker":      {"slot": "elmo",     "nome_exibicao": "Elmo de Chifres do Berserker"},
    "peitoral_placas_berserker":   {"slot": "armadura", "nome_exibicao": "Peitoral de Placas do Berserker"},
    "calcas_placas_berserker":     {"slot": "calca",    "nome_exibicao": "Calças de Placas do Berserker"},
    "botas_couro_berserker":       {"slot": "botas",    "nome_exibicao": "Botas de Couro do Berserker"},
    "luvas_couro_berserker":       {"slot": "luvas",    "nome_exibicao": "Luvas de Couro do Berserker"},
    "anel_osso_berserker":         {"slot": "anel",     "nome_exibicao": "Anel de Osso do Berserker"},
    "colar_presas_berserker":      {"slot": "colar",    "nome_exibicao": "Colar de Presas do Berserker"},
    "brinco_osso_berserker":       {"slot": "brinco",   "nome_exibicao": "Brinco de Osso do Berserker"},

    "machado_aco_berserker":       {"slot": "arma",     "nome_exibicao": "Machado de Aço do Berserker"},
    "elmo_troll_berserker":        {"slot": "elmo",     "nome_exibicao": "Elmo de Pele de Troll"},
    "peitoral_troll_berserker":    {"slot": "armadura", "nome_exibicao": "Peitoral de Pele de Troll"},
    "calcas_troll_berserker":      {"slot": "calca",    "nome_exibicao": "Calças de Pele de Troll"},
    "botas_troll_berserker":       {"slot": "botas",    "nome_exibicao": "Botas de Pele de Troll"},
    "luvas_troll_berserker":       {"slot": "luvas",    "nome_exibicao": "Luvas de Pele de Troll"},
    "anel_troll_berserker":        {"slot": "anel",     "nome_exibicao": "Anel de Garra de Troll"},
    "colar_troll_berserker":       {"slot": "colar",    "nome_exibicao": "Colar de Garra de Troll"},
    "brinco_troll_berserker":      {"slot": "brinco",   "nome_exibicao": "Brinco de Garra de Troll"},

    # =====================================================================
    # CAÇADOR — T1/T2
    # =====================================================================
    "arco_batedor_cacador":        {"slot": "arma",     "nome_exibicao": "Arco de Batedor"},
    "capuz_batedor_cacador":       {"slot": "elmo",     "nome_exibicao": "Capuz de Batedor"},
    "peitoral_batedor_cacador":    {"slot": "armadura", "nome_exibicao": "Peitoral de Batedor"},
    "calcas_batedor_cacador":      {"slot": "calca",    "nome_exibicao": "Calças de Batedor"},
    "botas_batedor_cacador":       {"slot": "botas",    "nome_exibicao": "Botas de Batedor"},
    "luvas_batedor_cacador":       {"slot": "luvas",    "nome_exibicao": "Luvas de Batedor"},
    "anel_batedor_cacador":        {"slot": "anel",     "nome_exibicao": "Anel de Batedor"},
    "colar_batedor_cacador":       {"slot": "colar",    "nome_exibicao": "Colar de Batedor"},
    "brinco_batedor_cacador":      {"slot": "brinco",   "nome_exibicao": "Brinco de Batedor"},

    "arco_patrulheiro_cacador":    {"slot": "arma",     "nome_exibicao": "Arco de Patrulheiro"},
    "capuz_patrulheiro_cacador":   {"slot": "elmo",     "nome_exibicao": "Capuz de Patrulheiro"},
    "peitoral_patrulheiro_cacador":{"slot": "armadura", "nome_exibicao": "Peitoral de Patrulheiro"},
    "calcas_patrulheiro_cacador":  {"slot": "calca",    "nome_exibicao": "Calças de Patrulheiro"},
    "botas_patrulheiro_cacador":   {"slot": "botas",    "nome_exibicao": "Botas de Patrulheiro"},
    "luvas_patrulheiro_cacador":   {"slot": "luvas",    "nome_exibicao": "Luvas de Patrulheiro"},
    "anel_patrulheiro_cacador":    {"slot": "anel",     "nome_exibicao": "Anel de Patrulheiro"},
    "colar_patrulheiro_cacador":   {"slot": "colar",    "nome_exibicao": "Colar de Patrulheiro"},
    "brinco_patrulheiro_cacador":  {"slot": "brinco",   "nome_exibicao": "Brinco de Patrulheiro"},

    # =====================================================================
    # ASSASSINO — T1/T2
    # =====================================================================
    "adaga_sorrateira_assassino":  {"slot": "arma",     "nome_exibicao": "Adaga Sorrateira"},
    "mascara_sorrateira_assassino":{"slot": "elmo",     "nome_exibicao": "Máscara Sorrateira"},
    "couraça_sorrateira_assassino":{"slot": "armadura", "nome_exibicao": "Couraça Sorrateira"},
    "calcas_sorrateiras_assassino":{"slot": "calca",    "nome_exibicao": "Calças Sorrateiras"},
    "botas_sorrateiras_assassino": {"slot": "botas",    "nome_exibicao": "Botas Sorrateiras"},
    "luvas_sorrateiras_assassino": {"slot": "luvas",    "nome_exibicao": "Luvas Sorrateiras"},
    "anel_sorrateiro_assassino":   {"slot": "anel",     "nome_exibicao": "Anel Sorrateiro"},
    "colar_sorrateiro_assassino":  {"slot": "colar",    "nome_exibicao": "Colar Sorrateiro"},
    "brinco_sorrateiro_assassino": {"slot": "brinco",   "nome_exibicao": "Brinco Sorrateiro"},

    "adaga_sombra_assassino":      {"slot": "arma",     "nome_exibicao": "Adaga da Sombra"},
    "mascara_sombra_assassino":    {"slot": "elmo",     "nome_exibicao": "Máscara da Sombra"},
    "couraça_sombra_assassino":    {"slot": "armadura", "nome_exibicao": "Couraça da Sombra"},
    "calcas_sombra_assassino":     {"slot": "calca",    "nome_exibicao": "Calças da Sombra"},
    "botas_sombra_assassino":      {"slot": "botas",    "nome_exibicao": "Botas da Sombra"},
    "luvas_sombra_assassino":      {"slot": "luvas",    "nome_exibicao": "Luvas da Sombra"},
    "anel_sombra_assassino":       {"slot": "anel",     "nome_exibicao": "Anel da Sombra"},
    "colar_sombra_assassino":      {"slot": "colar",    "nome_exibicao": "Colar da Sombra"},
    "brinco_sombra_assassino":     {"slot": "brinco",   "nome_exibicao": "Brinco da Sombra"},

    # =====================================================================
    # BARDO — T1/T2
    # =====================================================================
    "alaude_simples_bardo":        {"slot": "arma",     "nome_exibicao": "Alaúde Simples do Bardo"},
    "chapeu_elegante_bardo":       {"slot": "elmo",     "nome_exibicao": "Chapéu Elegante do Bardo"},
    "colete_viajante_bardo":       {"slot": "armadura", "nome_exibicao": "Colete de Viajante do Bardo"},
    "calcas_linho_bardo":          {"slot": "calca",    "nome_exibicao": "Calças de Linho do Bardo"},
    "botas_macias_bardo":          {"slot": "botas",    "nome_exibicao": "Botas Macias do Bardo"},
    "luvas_sem_dedos_bardo":       {"slot": "luvas",    "nome_exibicao": "Luvas sem Dedos do Bardo"},
    "anel_melodico_bardo":         {"slot": "anel",     "nome_exibicao": "Anel Melódico do Bardo"},
    "colar_melodico_bardo":        {"slot": "colar",    "nome_exibicao": "Colar Melódico do Bardo"},
    "brinco_melodico_bardo":       {"slot": "brinco",   "nome_exibicao": "Brinco Melódico do Bardo"},

    "alaude_ornamentado_bardo":    {"slot": "arma",     "nome_exibicao": "Alaúde Ornamentado do Bardo"},
    "chapeu_emplumado_bardo":      {"slot": "elmo",     "nome_exibicao": "Chapéu Emplumado do Bardo"},
    "casaco_veludo_bardo":         {"slot": "armadura", "nome_exibicao": "Casaco de Veludo do Bardo"},
    "calcas_veludo_bardo":         {"slot": "calca",    "nome_exibicao": "Calças de Veludo do Bardo"},
    "botas_veludo_bardo":          {"slot": "botas",    "nome_exibicao": "Botas de Veludo do Bardo"},
    "luvas_veludo_bardo":          {"slot": "luvas",    "nome_exibicao": "Luvas de Veludo do Bardo"},
    "anel_prata_bardo":            {"slot": "anel",     "nome_exibicao": "Anel de Prata do Bardo"},
    "colar_prata_bardo":           {"slot": "colar",    "nome_exibicao": "Colar de Prata do Bardo"},
    "brinco_prata_bardo":          {"slot": "brinco",   "nome_exibicao": "Brinco de Prata do Bardo"},

    # =====================================================================
    # MONGE — T1/T2
    # =====================================================================
    "manoplas_iniciado_monge":     {"slot": "arma",     "nome_exibicao": "Manoplas de Iniciado"},
    "bandana_iniciado_monge":      {"slot": "elmo",     "nome_exibicao": "Bandana de Iniciado"},
    "gi_iniciado_monge":           {"slot": "armadura", "nome_exibicao": "Gi de Iniciado"},
    "calcas_iniciado_monge":       {"slot": "calca",    "nome_exibicao": "Calças de Iniciado"},
    "sandalias_iniciado_monge":    {"slot": "botas",    "nome_exibicao": "Sandálias de Iniciado"},
    "faixas_iniciado_monge":       {"slot": "luvas",    "nome_exibicao": "Faixas de Mão de Iniciado"},
    "anel_iniciado_monge":         {"slot": "anel",     "nome_exibicao": "Anel de Iniciado"},
    "colar_iniciado_monge":        {"slot": "colar",    "nome_exibicao": "Colar de Iniciado"},
    "brinco_iniciado_monge":       {"slot": "brinco",   "nome_exibicao": "Brinco de Iniciado"},

    "manoplas_mestre_monge":       {"slot": "arma",     "nome_exibicao": "Manoplas de Mestre"},
    "bandana_mestre_monge":        {"slot": "elmo",     "nome_exibicao": "Bandana de Mestre"},
    "gi_mestre_monge":             {"slot": "armadura", "nome_exibicao": "Gi de Mestre"},
    "calcas_mestre_monge":         {"slot": "calca",    "nome_exibicao": "Calças de Mestre"},
    "sandalias_mestre_monge":      {"slot": "botas",    "nome_exibicao": "Sandálias de Mestre"},
    "faixas_mestre_monge":         {"slot": "luvas",    "nome_exibicao": "Faixas de Mão de Mestre"},
    "anel_mestre_monge":           {"slot": "anel",     "nome_exibicao": "Anel de Mestre"},
    "colar_mestre_monge":          {"slot": "colar",    "nome_exibicao": "Colar de Mestre"},
    "brinco_mestre_monge":         {"slot": "brinco",   "nome_exibicao": "Brinco de Mestre"},

    # =====================================================================
    # SAMURAI — T1/T2
    # =====================================================================
    "katana_laminada_samurai":     {"slot": "arma",     "nome_exibicao": "Katana Laminada"},
    "kabuto_laminado_samurai":     {"slot": "elmo",     "nome_exibicao": "Kabuto Laminado"},
    "do_laminado_samurai":         {"slot": "armadura", "nome_exibicao": "Do Laminado"},
    "haidate_laminado_samurai":    {"slot": "calca",    "nome_exibicao": "Haidate Laminado"},
    "suneate_laminado_samurai":    {"slot": "botas",    "nome_exibicao": "Suneate Laminado"},
    "kote_laminado_samurai":       {"slot": "luvas",    "nome_exibicao": "Kote Laminado"},
    "anel_laminado_samurai":       {"slot": "anel",     "nome_exibicao": "Anel Laminado"},
    "colar_laminado_samurai":      {"slot": "colar",    "nome_exibicao": "Colar Laminado"},
    "brinco_laminado_samurai":     {"slot": "brinco",   "nome_exibicao": "Brinco Laminado"},

    "katana_damasco_samurai":      {"slot": "arma",     "nome_exibicao": "Katana de Aço Damasco"},
    "kabuto_damasco_samurai":      {"slot": "elmo",     "nome_exibicao": "Kabuto de Aço Damasco"},
    "do_damasco_samurai":          {"slot": "armadura", "nome_exibicao": "Do de Aço Damasco"},
    "haidate_damasco_samurai":     {"slot": "calca",    "nome_exibicao": "Haidate de Aço Damasco"},
    "suneate_damasco_samurai":     {"slot": "botas",    "nome_exibicao": "Suneate de Aço Damasco"},
    "kote_damasco_samurai":        {"slot": "luvas",    "nome_exibicao": "Kote de Aço Damasco"},
    "anel_damasco_samurai":        {"slot": "anel",     "nome_exibicao": "Anel de Aço Damasco"},
    "colar_damasco_samurai":       {"slot": "colar",    "nome_exibicao": "Colar de Aço Damasco"},
    "brinco_damasco_samurai":      {"slot": "brinco",   "nome_exibicao": "Brinco de Aço Damasco"},

    # =====================================================================
    # 👑 SETS EXCLUSIVOS DAS CATACUMBAS (HERANÇA DO REI CAÍDO)
    # =====================================================================

    # --- GUERREIRO ---
    "espada_real_guerreiro":   {"slot": "arma",     "nome_exibicao": "Espada do Rei Caído", "set_id": "set_heranca_real", "class_req": ["guerreiro", "cavaleiro", "gladiador", "templario"]},
    "elmo_real_guerreiro":     {"slot": "elmo",     "nome_exibicao": "Coroa de Ferro do Rei", "set_id": "set_heranca_real", "class_req": ["guerreiro", "cavaleiro", "gladiador", "templario"]},
    "armadura_real_guerreiro": {"slot": "armadura", "nome_exibicao": "Égide do Rei Caído",  "set_id": "set_heranca_real", "class_req": ["guerreiro", "cavaleiro", "gladiador", "templario"]},
    "calca_real_guerreiro":    {"slot": "calca",    "nome_exibicao": "Grevas Reais Corrompidas", "set_id": "set_heranca_real", "class_req": ["guerreiro", "cavaleiro", "gladiador", "templario"]},
    "botas_real_guerreiro":    {"slot": "botas",    "nome_exibicao": "Sabatões do Rei Caído", "set_id": "set_heranca_real", "class_req": ["guerreiro", "cavaleiro", "gladiador", "templario"]},
    "luvas_real_guerreiro":    {"slot": "luvas",    "nome_exibicao": "Manoplas Reais Corrompidas", "set_id": "set_heranca_real", "class_req": ["guerreiro", "cavaleiro", "gladiador", "templario"]},

    # --- BERSERKER ---
    "machado_real_berserker":  {"slot": "arma",     "nome_exibicao": "Machado da Fúria Real", "set_id": "set_heranca_real", "class_req": ["berserker", "barbaro", "juggernaut", "ira_primordial"]},
    "elmo_real_berserker":     {"slot": "elmo",     "nome_exibicao": "Elmo de Ossos Reais", "set_id": "set_heranca_real", "class_req": ["berserker", "barbaro", "juggernaut", "ira_primordial"]},
    "armadura_real_berserker": {"slot": "armadura", "nome_exibicao": "Peitoral da Fúria Real", "set_id": "set_heranca_real", "class_req": ["berserker", "barbaro", "juggernaut", "ira_primordial"]},
    "calca_real_berserker":    {"slot": "calca",    "nome_exibicao": "Calças da Fúria Real", "set_id": "set_heranca_real", "class_req": ["berserker", "barbaro", "juggernaut", "ira_primordial"]},
    "botas_real_berserker":    {"slot": "botas",    "nome_exibicao": "Botas da Fúria Real", "set_id": "set_heranca_real", "class_req": ["berserker", "barbaro", "juggernaut", "ira_primordial"]},
    "luvas_real_berserker":    {"slot": "luvas",    "nome_exibicao": "Luvas da Fúria Real", "set_id": "set_heranca_real", "class_req": ["berserker", "barbaro", "juggernaut", "ira_primordial"]},

    # --- ASSASSINO ---
    "adaga_real_assassino":    {"slot": "arma",     "nome_exibicao": "Adaga Sombria do Rei", "set_id": "set_heranca_real", "class_req": ["assassino", "ladrao_de_sombras", "ninja", "mestre_das_laminas"]},
    "elmo_real_assassino":     {"slot": "elmo",     "nome_exibicao": "Máscara Sombria do Rei", "set_id": "set_heranca_real", "class_req": ["assassino", "ladrao_de_sombras", "ninja", "mestre_das_laminas"]},
    "armadura_real_assassino": {"slot": "armadura", "nome_exibicao": "Couraça Sombria do Rei", "set_id": "set_heranca_real", "class_req": ["assassino", "ladrao_de_sombras", "ninja", "mestre_das_laminas"]},
    "calca_real_assassino":    {"slot": "calca",    "nome_exibicao": "Calças Sombrias do Rei", "set_id": "set_heranca_real", "class_req": ["assassino", "ladrao_de_sombras", "ninja", "mestre_das_laminas"]},
    "botas_real_assassino":    {"slot": "botas",    "nome_exibicao": "Botas Sombrias do Rei", "set_id": "set_heranca_real", "class_req": ["assassino", "ladrao_de_sombras", "ninja", "mestre_das_laminas"]},
    "luvas_real_assassino":    {"slot": "luvas",    "nome_exibicao": "Luvas Sombrias do Rei", "set_id": "set_heranca_real", "class_req": ["assassino", "ladrao_de_sombras", "ninja", "mestre_das_laminas"]},

    # --- SAMURAI ---
    "katana_real_samurai":     {"slot": "arma",     "nome_exibicao": "Katana do Shogun Caído", "set_id": "set_heranca_real", "class_req": ["samurai", "kensei", "ronin", "shogun"]},
    "elmo_real_samurai":       {"slot": "elmo",     "nome_exibicao": "Kabuto do Shogun Caído", "set_id": "set_heranca_real", "class_req": ["samurai", "kensei", "ronin", "shogun"]},
    "armadura_real_samurai":   {"slot": "armadura", "nome_exibicao": "Do do Shogun Caído", "set_id": "set_heranca_real", "class_req": ["samurai", "kensei", "ronin", "shogun"]},
    "calca_real_samurai":      {"slot": "calca",    "nome_exibicao": "Haidate do Shogun Caído", "set_id": "set_heranca_real", "class_req": ["samurai", "kensei", "ronin", "shogun"]},
    "botas_real_samurai":      {"slot": "botas",    "nome_exibicao": "Suneate do Shogun Caído", "set_id": "set_heranca_real", "class_req": ["samurai", "kensei", "ronin", "shogun"]},
    "luvas_real_samurai":      {"slot": "luvas",    "nome_exibicao": "Kote do Shogun Caído", "set_id": "set_heranca_real", "class_req": ["samurai", "kensei", "ronin", "shogun"]},

    # --- MONGE ---
    "arma_real_monge":         {"slot": "arma",     "nome_exibicao": "Manoplas do Templo Caído", "set_id": "set_heranca_real", "class_req": ["monge", "guardiao_do_templo", "punho_elemental", "ascendente"]},
    "elmo_real_monge":         {"slot": "elmo",     "nome_exibicao": "Bandana do Templo Caído", "set_id": "set_heranca_real", "class_req": ["monge", "guardiao_do_templo", "punho_elemental", "ascendente"]},
    "armadura_real_monge":     {"slot": "armadura", "nome_exibicao": "Gi do Templo Caído", "set_id": "set_heranca_real", "class_req": ["monge", "guardiao_do_templo", "punho_elemental", "ascendente"]},
    "calca_real_monge":        {"slot": "calca",    "nome_exibicao": "Calças do Templo Caído", "set_id": "set_heranca_real", "class_req": ["monge", "guardiao_do_templo", "punho_elemental", "ascendente"]},
    "botas_real_monge":        {"slot": "botas",    "nome_exibicao": "Sandálias do Templo Caído", "set_id": "set_heranca_real", "class_req": ["monge", "guardiao_do_templo", "punho_elemental", "ascendente"]},
    "luvas_real_monge":        {"slot": "luvas",    "nome_exibicao": "Faixas do Templo Caído", "set_id": "set_heranca_real", "class_req": ["monge", "guardiao_do_templo", "punho_elemental", "ascendente"]},

    # --- MAGO ---
    "cajado_real_mago":        {"slot": "arma",     "nome_exibicao": "Cajado Arcano do Rei", "set_id": "set_heranca_real", "class_req": ["mago", "feiticeiro", "elementalista", "arquimago"]},
    "elmo_real_mago":          {"slot": "elmo",     "nome_exibicao": "Coroa Arcana do Rei", "set_id": "set_heranca_real", "class_req": ["mago", "feiticeiro", "elementalista", "arquimago"]},
    "armadura_real_mago":      {"slot": "armadura", "nome_exibicao": "Túnica Arcana do Rei", "set_id": "set_heranca_real", "class_req": ["mago", "feiticeiro", "elementalista", "arquimago"]},
    "calca_real_mago":         {"slot": "calca",    "nome_exibicao": "Calças Arcanas do Rei", "set_id": "set_heranca_real", "class_req": ["mago", "feiticeiro", "elementalista", "arquimago"]},
    "botas_real_mago":         {"slot": "botas",    "nome_exibicao": "Botas Arcanas do Rei", "set_id": "set_heranca_real", "class_req": ["mago", "feiticeiro", "elementalista", "arquimago"]},
    "luvas_real_mago":         {"slot": "luvas",    "nome_exibicao": "Luvas Arcanas do Rei", "set_id": "set_heranca_real", "class_req": ["mago", "feiticeiro", "elementalista", "arquimago"]},

    # --- BARDO ---
    "arma_real_bardo":         {"slot": "arma",     "nome_exibicao": "Alaúde do Réquiem Real", "set_id": "set_heranca_real", "class_req": ["bardo", "menestrel", "encantador", "maestro"]},
    "elmo_real_bardo":         {"slot": "elmo",     "nome_exibicao": "Chapéu do Réquiem Real", "set_id": "set_heranca_real", "class_req": ["bardo", "menestrel", "encantador", "maestro"]},
    "armadura_real_bardo":     {"slot": "armadura", "nome_exibicao": "Casaco do Réquiem Real", "set_id": "set_heranca_real", "class_req": ["bardo", "menestrel", "encantador", "maestro"]},
    "calca_real_bardo":        {"slot": "calca",    "nome_exibicao": "Calças do Réquiem Real", "set_id": "set_heranca_real", "class_req": ["bardo", "menestrel", "encantador", "maestro"]},
    "botas_real_bardo":        {"slot": "botas",    "nome_exibicao": "Botas do Réquiem Real", "set_id": "set_heranca_real", "class_req": ["bardo", "menestrel", "encantador", "maestro"]},
    "luvas_real_bardo":        {"slot": "luvas",    "nome_exibicao": "Luvas do Réquiem Real", "set_id": "set_heranca_real", "class_req": ["bardo", "menestrel", "encantador", "maestro"]},

    # --- CAÇADOR ---
    "arma_real_cacador":       {"slot": "arma",     "nome_exibicao": "Arco do Caçador Real", "set_id": "set_heranca_real", "class_req": ["cacador", "patrulheiro", "franco_atirador", "mestre_da_selva"]},
    "elmo_real_cacador":       {"slot": "elmo",     "nome_exibicao": "Capuz do Caçador Real", "set_id": "set_heranca_real", "class_req": ["cacador", "patrulheiro", "franco_atirador", "mestre_da_selva"]},
    "armadura_real_cacador":   {"slot": "armadura", "nome_exibicao": "Peitoral do Caçador Real", "set_id": "set_heranca_real", "class_req": ["cacador", "patrulheiro", "franco_atirador", "mestre_da_selva"]},
    "calca_real_cacador":      {"slot": "calca",    "nome_exibicao": "Calças do Caçador Real", "set_id": "set_heranca_real", "class_req": ["cacador", "patrulheiro", "franco_atirador", "mestre_da_selva"]},
    "botas_real_cacador":      {"slot": "botas",    "nome_exibicao": "Botas do Caçador Real", "set_id": "set_heranca_real", "class_req": ["cacador", "patrulheiro", "franco_atirador", "mestre_da_selva"]},
    "luvas_real_cacador":      {"slot": "luvas",    "nome_exibicao": "Luvas do Caçador Real", "set_id": "set_heranca_real", "class_req": ["cacador", "patrulheiro", "franco_atirador", "mestre_da_selva"]},

    # --- CURANDEIRO ---
    "arma_real_curandeiro":    {"slot": "arma",     "nome_exibicao": "Cajado do Milagre Real", "set_id": "set_heranca_real", "class_req": ["curandeiro", "clerigo", "druida", "sacerdote"]},
    "elmo_real_curandeiro":    {"slot": "elmo",     "nome_exibicao": "Capuz do Milagre Real", "set_id": "set_heranca_real", "class_req": ["curandeiro", "clerigo", "druida", "sacerdote"]},
    "armadura_real_curandeiro":{"slot": "armadura", "nome_exibicao": "Veste do Milagre Real", "set_id": "set_heranca_real", "class_req": ["curandeiro", "clerigo", "druida", "sacerdote"]},
    "calca_real_curandeiro":   {"slot": "calca",    "nome_exibicao": "Calças do Milagre Real", "set_id": "set_heranca_real", "class_req": ["curandeiro", "clerigo", "druida", "sacerdote"]},
    "botas_real_curandeiro":   {"slot": "botas",    "nome_exibicao": "Sandálias do Milagre Real", "set_id": "set_heranca_real", "class_req": ["curandeiro", "clerigo", "druida", "sacerdote"]},
    "luvas_real_curandeiro":   {"slot": "luvas",    "nome_exibicao": "Luvas do Milagre Real", "set_id": "set_heranca_real", "class_req": ["curandeiro", "clerigo", "druida", "sacerdote"]},
}

def get_item_info(base_id: str) -> dict:
    """Retorna metadados estáticos do item base."""
    return ITEM_DATABASE.get(base_id, {})
