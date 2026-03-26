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
    "peitoral_coracao_umbrio": {"slot": "armadura", "nome_exibicao": "Peitoral Coração Umbrio","image_url": "https://github.com/sua-imagem-da-mascara.png"},
    "tunica_coracao_umbrio":   {"slot": "armadura", "nome_exibicao": "Túnica Coração Umbrio","image_url": "https://github.com/sua-imagem-da-mascara.png"},

    # --------------------------------------------------------------------
    # TIER 1 / TIER 2: GUERREIRO
    # --------------------------------------------------------------------
    "espada_ferro_guerreiro":     {"slot": "arma",     "nome_exibicao": "Espada de Ferro do Guerreiro","image_url": "https://github.com/sua-imagem-da-mascara.png"},
    "elmo_ferro_guerreiro":       {"slot": "elmo",     "nome_exibicao": "Elmo de Ferro do Guerreiro","image_url": "https://github.com/sua-imagem-da-mascara.png"},
    "peitoral_ferro_guerreiro":   {"slot": "armadura", "nome_exibicao": "Peitoral de Ferro do Guerreiro","image_url": "https://github.com/sua-imagem-da-mascara.png"},
    "calcas_ferro_guerreiro":     {"slot": "calca",    "nome_exibicao": "Calças de Ferro do Guerreiro","image_url": "https://github.com/sua-imagem-da-mascara.png"},
    "botas_ferro_guerreiro":      {"slot": "botas",    "nome_exibicao": "Botas de Ferro do Guerreiro","image_url": "https://github.com/sua-imagem-da-mascara.png"},
    "luvas_ferro_guerreiro":      {"slot": "luvas",    "nome_exibicao": "Luvas de Ferro do Guerreiro","image_url": "https://github.com/sua-imagem-da-mascara.png"},
    "anel_ferro_guerreiro":       {"slot": "anel",     "nome_exibicao": "Anel de Ferro do Guerreiro","image_url": "https://github.com/sua-imagem-da-mascara.png"},
    "colar_ferro_guerreiro":      {"slot": "colar",    "nome_exibicao": "Colar de Ferro do Guerreiro","image_url": "https://github.com/sua-imagem-da-mascara.png"},
    "brinco_ferro_guerreiro":     {"slot": "brinco",   "nome_exibicao": "Brinco de Ferro do Guerreiro","image_url": "https://github.com/sua-imagem-da-mascara.png"},

    "espada_aco_guerreiro":       {"slot": "arma",     "nome_exibicao": "Espada de Aço do Guerreiro","image_url": "https://github.com/sua-imagem-da-mascara.png"},
    "elmo_aco_guerreiro":         {"slot": "elmo",     "nome_exibicao": "Elmo de Aço do Guerreiro","image_url": "https://github.com/sua-imagem-da-mascara.png"},
    "peitoral_aco_guerreiro":     {"slot": "armadura", "nome_exibicao": "Peitoral de Aço do Guerreiro","image_url": "https://github.com/sua-imagem-da-mascara.png"},
    "calcas_aco_guerreiro":       {"slot": "calca",    "nome_exibicao": "Calças de Aço do Guerreiro","image_url": "https://github.com/sua-imagem-da-mascara.png"},
    "botas_aco_guerreiro":        {"slot": "botas",    "nome_exibicao": "Botas de Aço do Guerreiro","image_url": "https://github.com/sua-imagem-da-mascara.png"},
    "luvas_aco_guerreiro":        {"slot": "luvas",    "nome_exibicao": "Luvas de Aço do Guerreiro","image_url": "https://github.com/sua-imagem-da-mascara.png"},
    "anel_aco_guerreiro":         {"slot": "anel",     "nome_exibicao": "Anel de Aço do Guerreiro","image_url": "https://github.com/sua-imagem-da-mascara.png"},
    "colar_aco_guerreiro":        {"slot": "colar",    "nome_exibicao": "Colar de Aço do Guerreiro","image_url": "https://github.com/sua-imagem-da-mascara.png"},
    "brinco_aco_guerreiro":       {"slot": "brinco",   "nome_exibicao": "Brinco de Aço do Guerreiro","image_url": "https://github.com/sua-imagem-da-mascara.png"},

    # =====================================================================
    # MAGO — T1/T2
    # =====================================================================
    "cajado_aprendiz_mago":   {"slot": "arma",     "nome_exibicao": "Cajado de Aprendiz","image_url": "https://github.com/sua-imagem-da-mascara.png"},
    "chapeu_seda_mago":       {"slot": "elmo",     "nome_exibicao": "Chapéu de Seda do Mago","image_url": "https://github.com/sua-imagem-da-mascara.png"},
    "tunica_seda_mago":       {"slot": "armadura", "nome_exibicao": "Túnica de Seda do Mago","image_url": "https://github.com/sua-imagem-da-mascara.png"},
    "calcas_seda_mago":       {"slot": "calca",    "nome_exibicao": "Calças de Seda do Mago","image_url": "https://github.com/sua-imagem-da-mascara.png"},
    "botas_seda_mago":        {"slot": "botas",    "nome_exibicao": "Botas de Seda do Mago","image_url": "https://github.com/sua-imagem-da-mascara.png"},
    "luvas_seda_mago":        {"slot": "luvas",    "nome_exibicao": "Luvas de Seda do Mago"},
    "anel_gema_mago":         {"slot": "anel",     "nome_exibicao": "Anel de Gema do Mago","image_url": "https://github.com/sua-imagem-da-mascara.png"},
    "colar_gema_mago":        {"slot": "colar",    "nome_exibicao": "Colar de Gema do Mago","image_url": "https://github.com/sua-imagem-da-mascara.png"},
    "brinco_gema_mago":       {"slot": "brinco",   "nome_exibicao": "Brinco de Gema do Mago","image_url": "https://github.com/sua-imagem-da-mascara.png"},

    "cajado_arcano_mago":     {"slot": "arma",     "nome_exibicao": "Cajado Arcano","image_url": "https://github.com/sua-imagem-da-mascara.png"},
    "chapeu_veludo_mago":     {"slot": "elmo",     "nome_exibicao": "Chapéu de Veludo do Mago","image_url": "https://github.com/sua-imagem-da-mascara.png"},
    "tunica_veludo_mago":     {"slot": "armadura", "nome_exibicao": "Túnica de Veludo do Mago","image_url": "https://github.com/sua-imagem-da-mascara.png"},
    "calcas_veludo_mago":     {"slot": "calca",    "nome_exibicao": "Calças de Veludo do Mago","image_url": "https://github.com/sua-imagem-da-mascara.png"},
    "botas_veludo_mago":      {"slot": "botas",    "nome_exibicao": "Botas de Veludo do Mago","image_url": "https://github.com/sua-imagem-da-mascara.png"},
    "luvas_veludo_mago":      {"slot": "luvas",    "nome_exibicao": "Luvas de Veludo do Mago","image_url": "https://github.com/sua-imagem-da-mascara.png"},
    "anel_runico_mago":       {"slot": "anel",     "nome_exibicao": "Anel Rúnico do Mago","image_url": "https://github.com/sua-imagem-da-mascara.png"},
    "colar_runico_mago":      {"slot": "colar",    "nome_exibicao": "Colar Rúnico do Mago","image_url": "https://github.com/sua-imagem-da-mascara.png"},
    "brinco_runico_mago":     {"slot": "brinco",   "nome_exibicao": "Brinco Rúnico do Mago","image_url": "https://github.com/sua-imagem-da-mascara.png"},

    # =====================================================================
    # BERSERKER — T1/T2
    # =====================================================================
    "machado_rustico_berserker":   {"slot": "arma",     "nome_exibicao": "Machado Rústico do Berserker","image_url": "https://github.com/sua-imagem-da-mascara.png"},
    "elmo_chifres_berserker":      {"slot": "elmo",     "nome_exibicao": "Elmo de Chifres do Berserker","image_url": "https://github.com/sua-imagem-da-mascara.png"},
    "peitoral_placas_berserker":   {"slot": "armadura", "nome_exibicao": "Peitoral de Placas do Berserker","image_url": "https://github.com/sua-imagem-da-mascara.png"},
    "calcas_placas_berserker":     {"slot": "calca",    "nome_exibicao": "Calças de Placas do Berserker","image_url": "https://github.com/sua-imagem-da-mascara.png"},
    "botas_couro_berserker":       {"slot": "botas",    "nome_exibicao": "Botas de Couro do Berserker","image_url": "https://github.com/sua-imagem-da-mascara.png"},
    "luvas_couro_berserker":       {"slot": "luvas",    "nome_exibicao": "Luvas de Couro do Berserker","image_url": "https://github.com/sua-imagem-da-mascara.png"},
    "anel_osso_berserker":         {"slot": "anel",     "nome_exibicao": "Anel de Osso do Berserker","image_url": "https://github.com/sua-imagem-da-mascara.png"},
    "colar_presas_berserker":      {"slot": "colar",    "nome_exibicao": "Colar de Presas do Berserker","image_url": "https://github.com/sua-imagem-da-mascara.png"},
    "brinco_osso_berserker":       {"slot": "brinco",   "nome_exibicao": "Brinco de Osso do Berserker","image_url": "https://github.com/sua-imagem-da-mascara.png"},

    "machado_aco_berserker":       {"slot": "arma",     "nome_exibicao": "Machado de Aço do Berserker","image_url": "https://github.com/sua-imagem-da-mascara.png"},
    "elmo_troll_berserker":        {"slot": "elmo",     "nome_exibicao": "Elmo de Pele de Troll","image_url": "https://github.com/sua-imagem-da-mascara.png"},
    "peitoral_troll_berserker":    {"slot": "armadura", "nome_exibicao": "Peitoral de Pele de Troll","image_url": "https://github.com/sua-imagem-da-mascara.png"},
    "calcas_troll_berserker":      {"slot": "calca",    "nome_exibicao": "Calças de Pele de Troll","image_url": "https://github.com/sua-imagem-da-mascara.png"},
    "botas_troll_berserker":       {"slot": "botas",    "nome_exibicao": "Botas de Pele de Troll","image_url": "https://github.com/sua-imagem-da-mascara.png"},
    "luvas_troll_berserker":       {"slot": "luvas",    "nome_exibicao": "Luvas de Pele de Troll","image_url": "https://github.com/sua-imagem-da-mascara.png"},
    "anel_troll_berserker":        {"slot": "anel",     "nome_exibicao": "Anel de Garra de Troll","image_url": "https://github.com/sua-imagem-da-mascara.png"},
    "colar_troll_berserker":       {"slot": "colar",    "nome_exibicao": "Colar de Garra de Troll","image_url": "https://github.com/sua-imagem-da-mascara.png"},
    "brinco_troll_berserker":      {"slot": "brinco",   "nome_exibicao": "Brinco de Garra de Troll","image_url": "https://github.com/sua-imagem-da-mascara.png"},

    # =====================================================================
    # CAÇADOR — T1/T2
    # =====================================================================
    "arco_batedor_cacador":        {"slot": "arma",     "nome_exibicao": "Arco de Batedor","image_url": "https://github.com/sua-imagem-da-mascara.png"},
    "capuz_batedor_cacador":       {"slot": "elmo",     "nome_exibicao": "Capuz de Batedor","image_url": "https://github.com/sua-imagem-da-mascara.png"},
    "peitoral_batedor_cacador":    {"slot": "armadura", "nome_exibicao": "Peitoral de Batedor","image_url": "https://github.com/sua-imagem-da-mascara.png"},
    "calcas_batedor_cacador":      {"slot": "calca",    "nome_exibicao": "Calças de Batedor","image_url": "https://github.com/sua-imagem-da-mascara.png"},
    "botas_batedor_cacador":       {"slot": "botas",    "nome_exibicao": "Botas de Batedor","image_url": "https://github.com/sua-imagem-da-mascara.png"},
    "luvas_batedor_cacador":       {"slot": "luvas",    "nome_exibicao": "Luvas de Batedor","image_url": "https://github.com/sua-imagem-da-mascara.png"},
    "anel_batedor_cacador":        {"slot": "anel",     "nome_exibicao": "Anel de Batedor","image_url": "https://github.com/sua-imagem-da-mascara.png"},
    "colar_batedor_cacador":       {"slot": "colar",    "nome_exibicao": "Colar de Batedor","image_url": "https://github.com/sua-imagem-da-mascara.png"},
    "brinco_batedor_cacador":      {"slot": "brinco",   "nome_exibicao": "Brinco de Batedor","image_url": "https://github.com/sua-imagem-da-mascara.png"},

    "arco_patrulheiro_cacador":    {"slot": "arma",     "nome_exibicao": "Arco de Patrulheiro","image_url": "https://github.com/sua-imagem-da-mascara.png"},
    "capuz_patrulheiro_cacador":   {"slot": "elmo",     "nome_exibicao": "Capuz de Patrulheiro","image_url": "https://github.com/sua-imagem-da-mascara.png"},
    "peitoral_patrulheiro_cacador":{"slot": "armadura", "nome_exibicao": "Peitoral de Patrulheiro","image_url": "https://github.com/sua-imagem-da-mascara.png"},
    "calcas_patrulheiro_cacador":  {"slot": "calca",    "nome_exibicao": "Calças de Patrulheiro","image_url": "https://github.com/sua-imagem-da-mascara.png"},
    "botas_patrulheiro_cacador":   {"slot": "botas",    "nome_exibicao": "Botas de Patrulheiro","image_url": "https://github.com/sua-imagem-da-mascara.png"},
    "luvas_patrulheiro_cacador":   {"slot": "luvas",    "nome_exibicao": "Luvas de Patrulheiro","image_url": "https://github.com/sua-imagem-da-mascara.png"},
    "anel_patrulheiro_cacador":    {"slot": "anel",     "nome_exibicao": "Anel de Patrulheiro","image_url": "https://github.com/sua-imagem-da-mascara.png"},
    "colar_patrulheiro_cacador":   {"slot": "colar",    "nome_exibicao": "Colar de Patrulheiro","image_url": "https://github.com/sua-imagem-da-mascara.png"},
    "brinco_patrulheiro_cacador":  {"slot": "brinco",   "nome_exibicao": "Brinco de Patrulheiro","image_url": "https://github.com/sua-imagem-da-mascara.png"},

    # =====================================================================
    # ASSASSINO — T1/T2
    # =====================================================================
    "adaga_sorrateira_assassino":  {"slot": "arma",     "nome_exibicao": "Adaga Sorrateira","image_url": "https://github.com/sua-imagem-da-mascara.png"},
    "mascara_sorrateira_assassino":{"slot": "elmo",     "nome_exibicao": "Máscara Sorrateira","image_url": "https://github.com/sua-imagem-da-mascara.png"},
    "couraça_sorrateira_assassino":{"slot": "armadura", "nome_exibicao": "Couraça Sorrateira","image_url": "https://github.com/sua-imagem-da-mascara.png"},
    "calcas_sorrateiras_assassino":{"slot": "calca",    "nome_exibicao": "Calças Sorrateiras","image_url": "https://github.com/sua-imagem-da-mascara.png"},
    "botas_sorrateiras_assassino": {"slot": "botas",    "nome_exibicao": "Botas Sorrateiras","image_url": "https://github.com/sua-imagem-da-mascara.png"},
    "luvas_sorrateiras_assassino": {"slot": "luvas",    "nome_exibicao": "Luvas Sorrateiras","image_url": "https://github.com/sua-imagem-da-mascara.png"},
    "anel_sorrateiro_assassino":   {"slot": "anel",     "nome_exibicao": "Anel Sorrateiro","image_url": "https://github.com/sua-imagem-da-mascara.png"},
    "colar_sorrateiro_assassino":  {"slot": "colar",    "nome_exibicao": "Colar Sorrateiro","image_url": "https://github.com/sua-imagem-da-mascara.png"},
    "brinco_sorrateiro_assassino": {"slot": "brinco",   "nome_exibicao": "Brinco Sorrateiro","image_url": "https://github.com/sua-imagem-da-mascara.png"},

    "adaga_sombra_assassino":      {"slot": "arma",     "nome_exibicao": "Adaga da Sombra","image_url": "https://github.com/sua-imagem-da-mascara.png"},
    "mascara_sombra_assassino":    {"slot": "elmo",     "nome_exibicao": "Máscara da Sombra","image_url": "https://github.com/sua-imagem-da-mascara.png"},
    "couraça_sombra_assassino":    {"slot": "armadura", "nome_exibicao": "Couraça da Sombra","image_url": "https://github.com/sua-imagem-da-mascara.png"},
    "calcas_sombra_assassino":     {"slot": "calca",    "nome_exibicao": "Calças da Sombra","image_url": "https://github.com/sua-imagem-da-mascara.png"},
    "botas_sombra_assassino":      {"slot": "botas",    "nome_exibicao": "Botas da Sombra","image_url": "https://github.com/sua-imagem-da-mascara.png"},
    "luvas_sombra_assassino":      {"slot": "luvas",    "nome_exibicao": "Luvas da Sombra","image_url": "https://github.com/sua-imagem-da-mascara.png"},
    "anel_sombra_assassino":       {"slot": "anel",     "nome_exibicao": "Anel da Sombra","image_url": "https://github.com/sua-imagem-da-mascara.png"},
    "colar_sombra_assassino":      {"slot": "colar",    "nome_exibicao": "Colar da Sombra","image_url": "https://github.com/sua-imagem-da-mascara.png"},
    "brinco_sombra_assassino":     {"slot": "brinco",   "nome_exibicao": "Brinco da Sombra","image_url": "https://github.com/sua-imagem-da-mascara.png"},

    # =====================================================================
    # BARDO — T1/T2
    # =====================================================================
    "alaude_simples_bardo":        {"slot": "arma",     "nome_exibicao": "Alaúde Simples do Bardo","image_url": "https://github.com/sua-imagem-da-mascara.png"},
    "chapeu_elegante_bardo":       {"slot": "elmo",     "nome_exibicao": "Chapéu Elegante do Bardo","image_url": "https://github.com/sua-imagem-da-mascara.png"},
    "colete_viajante_bardo":       {"slot": "armadura", "nome_exibicao": "Colete de Viajante do Bardo","image_url": "https://github.com/sua-imagem-da-mascara.png"},
    "calcas_linho_bardo":          {"slot": "calca",    "nome_exibicao": "Calças de Linho do Bardo","image_url": "https://github.com/sua-imagem-da-mascara.png"},
    "botas_macias_bardo":          {"slot": "botas",    "nome_exibicao": "Botas Macias do Bardo","image_url": "https://github.com/sua-imagem-da-mascara.png"},
    "luvas_sem_dedos_bardo":       {"slot": "luvas",    "nome_exibicao": "Luvas sem Dedos do Bardo","image_url": "https://github.com/sua-imagem-da-mascara.png"},
    "anel_melodico_bardo":         {"slot": "anel",     "nome_exibicao": "Anel Melódico do Bardo","image_url": "https://github.com/sua-imagem-da-mascara.png"},
    "colar_melodico_bardo":        {"slot": "colar",    "nome_exibicao": "Colar Melódico do Bardo","image_url": "https://github.com/sua-imagem-da-mascara.png"},
    "brinco_melodico_bardo":       {"slot": "brinco",   "nome_exibicao": "Brinco Melódico do Bardo","image_url": "https://github.com/sua-imagem-da-mascara.png"},

    "alaude_ornamentado_bardo":    {"slot": "arma",     "nome_exibicao": "Alaúde Ornamentado do Bardo","image_url": "https://github.com/sua-imagem-da-mascara.png"},
    "chapeu_emplumado_bardo":      {"slot": "elmo",     "nome_exibicao": "Chapéu Emplumado do Bardo","image_url": "https://github.com/sua-imagem-da-mascara.png"},
    "casaco_veludo_bardo":         {"slot": "armadura", "nome_exibicao": "Casaco de Veludo do Bardo","image_url": "https://github.com/sua-imagem-da-mascara.png"},
    "calcas_veludo_bardo":         {"slot": "calca",    "nome_exibicao": "Calças de Veludo do Bardo","image_url": "https://github.com/sua-imagem-da-mascara.png"},
    "botas_veludo_bardo":          {"slot": "botas",    "nome_exibicao": "Botas de Veludo do Bardo","image_url": "https://github.com/sua-imagem-da-mascara.png"},
    "luvas_veludo_bardo":          {"slot": "luvas",    "nome_exibicao": "Luvas de Veludo do Bardo","image_url": "https://github.com/sua-imagem-da-mascara.png"},
    "anel_prata_bardo":            {"slot": "anel",     "nome_exibicao": "Anel de Prata do Bardo","image_url": "https://github.com/sua-imagem-da-mascara.png"},
    "colar_prata_bardo":           {"slot": "colar",    "nome_exibicao": "Colar de Prata do Bardo","image_url": "https://github.com/sua-imagem-da-mascara.png"},
    "brinco_prata_bardo":          {"slot": "brinco",   "nome_exibicao": "Brinco de Prata do Bardo","image_url": "https://github.com/sua-imagem-da-mascara.png"},

    # =====================================================================
    # MONGE — T1/T2
    # =====================================================================
    "manoplas_iniciado_monge":     {"slot": "arma",     "nome_exibicao": "Manoplas de Iniciado","image_url": "https://github.com/sua-imagem-da-mascara.png"},
    "bandana_iniciado_monge":      {"slot": "elmo",     "nome_exibicao": "Bandana de Iniciado","image_url": "https://github.com/sua-imagem-da-mascara.png"},
    "gi_iniciado_monge":           {"slot": "armadura", "nome_exibicao": "Gi de Iniciado","image_url": "https://github.com/sua-imagem-da-mascara.png"},
    "calcas_iniciado_monge":       {"slot": "calca",    "nome_exibicao": "Calças de Iniciado","image_url": "https://github.com/sua-imagem-da-mascara.png"},
    "sandalias_iniciado_monge":    {"slot": "botas",    "nome_exibicao": "Sandálias de Iniciado","image_url": "https://github.com/sua-imagem-da-mascara.png"},
    "faixas_iniciado_monge":       {"slot": "luvas",    "nome_exibicao": "Faixas de Mão de Iniciado","image_url": "https://github.com/sua-imagem-da-mascara.png"},
    "anel_iniciado_monge":         {"slot": "anel",     "nome_exibicao": "Anel de Iniciado","image_url": "https://github.com/sua-imagem-da-mascara.png"},
    "colar_iniciado_monge":        {"slot": "colar",    "nome_exibicao": "Colar de Iniciado","image_url": "https://github.com/sua-imagem-da-mascara.png"},
    "brinco_iniciado_monge":       {"slot": "brinco",   "nome_exibicao": "Brinco de Iniciado","image_url": "https://github.com/sua-imagem-da-mascara.png"},

    "manoplas_mestre_monge":       {"slot": "arma",     "nome_exibicao": "Manoplas de Mestre","image_url": "https://github.com/sua-imagem-da-mascara.png"},
    "bandana_mestre_monge":        {"slot": "elmo",     "nome_exibicao": "Bandana de Mestre","image_url": "https://github.com/sua-imagem-da-mascara.png"},
    "gi_mestre_monge":             {"slot": "armadura", "nome_exibicao": "Gi de Mestre","image_url": "https://github.com/sua-imagem-da-mascara.png"},
    "calcas_mestre_monge":         {"slot": "calca",    "nome_exibicao": "Calças de Mestre","image_url": "https://github.com/sua-imagem-da-mascara.png"},
    "sandalias_mestre_monge":      {"slot": "botas",    "nome_exibicao": "Sandálias de Mestre","image_url": "https://github.com/sua-imagem-da-mascara.png"},
    "faixas_mestre_monge":         {"slot": "luvas",    "nome_exibicao": "Faixas de Mão de Mestre","image_url": "https://github.com/sua-imagem-da-mascara.png"},
    "anel_mestre_monge":           {"slot": "anel",     "nome_exibicao": "Anel de Mestre","image_url": "https://github.com/sua-imagem-da-mascara.png"},
    "colar_mestre_monge":          {"slot": "colar",    "nome_exibicao": "Colar de Mestre","image_url": "https://github.com/sua-imagem-da-mascara.png"},
    "brinco_mestre_monge":         {"slot": "brinco",   "nome_exibicao": "Brinco de Mestre","image_url": "https://github.com/sua-imagem-da-mascara.png"},

    # =====================================================================
    # SAMURAI — T1/T2
    # =====================================================================
    "katana_laminada_samurai":     {"slot": "arma",     "nome_exibicao": "Katana Laminada","image_url": "https://github.com/sua-imagem-da-mascara.png"},
    "kabuto_laminado_samurai":     {"slot": "elmo",     "nome_exibicao": "Kabuto Laminado","image_url": "https://github.com/sua-imagem-da-mascara.png"},
    "do_laminado_samurai":         {"slot": "armadura", "nome_exibicao": "Do Laminado","image_url": "https://github.com/sua-imagem-da-mascara.png"},
    "haidate_laminado_samurai":    {"slot": "calca",    "nome_exibicao": "Haidate Laminado","image_url": "https://github.com/sua-imagem-da-mascara.png"},
    "suneate_laminado_samurai":    {"slot": "botas",    "nome_exibicao": "Suneate Laminado","image_url": "https://github.com/sua-imagem-da-mascara.png"},
    "kote_laminado_samurai":       {"slot": "luvas",    "nome_exibicao": "Kote Laminado","image_url": "https://github.com/sua-imagem-da-mascara.png"},
    "anel_laminado_samurai":       {"slot": "anel",     "nome_exibicao": "Anel Laminado","image_url": "https://github.com/sua-imagem-da-mascara.png"},
    "colar_laminado_samurai":      {"slot": "colar",    "nome_exibicao": "Colar Laminado","image_url": "https://github.com/sua-imagem-da-mascara.png"},
    "brinco_laminado_samurai":     {"slot": "brinco",   "nome_exibicao": "Brinco Laminado","image_url": "https://github.com/sua-imagem-da-mascara.png"},

    "katana_damasco_samurai":      {"slot": "arma",     "nome_exibicao": "Katana de Aço Damasco","image_url": "https://github.com/sua-imagem-da-mascara.png"},
    "kabuto_damasco_samurai":      {"slot": "elmo",     "nome_exibicao": "Kabuto de Aço Damasco","image_url": "https://github.com/sua-imagem-da-mascara.png"},
    "do_damasco_samurai":          {"slot": "armadura", "nome_exibicao": "Do de Aço Damasco","image_url": "https://github.com/sua-imagem-da-mascara.png"},
    "haidate_damasco_samurai":     {"slot": "calca",    "nome_exibicao": "Haidate de Aço Damasco","image_url": "https://github.com/sua-imagem-da-mascara.png"},
    "suneate_damasco_samurai":     {"slot": "botas",    "nome_exibicao": "Suneate de Aço Damasco","image_url": "https://github.com/sua-imagem-da-mascara.png"},
    "kote_damasco_samurai":        {"slot": "luvas",    "nome_exibicao": "Kote de Aço Damasco","image_url": "https://github.com/sua-imagem-da-mascara.png"},
    "anel_damasco_samurai":        {"slot": "anel",     "nome_exibicao": "Anel de Aço Damasco","image_url": "https://github.com/sua-imagem-da-mascara.png"},
    "colar_damasco_samurai":       {"slot": "colar",    "nome_exibicao": "Colar de Aço Damasco","image_url": "https://github.com/sua-imagem-da-mascara.png"},
    "brinco_damasco_samurai":      {"slot": "brinco",   "nome_exibicao": "Brinco de Aço Damasco","image_url": "https://github.com/sua-imagem-da-mascara.png"},

    # =====================================================================
    # 👑 SETS EXCLUSIVOS DAS CATACUMBAS (HERANÇA DO REI CAÍDO)
    # =====================================================================

    # --- GUERREIRO ---
    "espada_real_guerreiro":   {"slot": "arma",     "nome_exibicao": "Espada do Rei Caído", "set_id": "set_heranca_real", "class_req": ["guerreiro", "cavaleiro", "gladiador", "templario"],"image_url": "https://github.com/sua-imagem-da-mascara.png"},
    "elmo_real_guerreiro":     {"slot": "elmo",     "nome_exibicao": "Coroa de Ferro do Rei", "set_id": "set_heranca_real", "class_req": ["guerreiro", "cavaleiro", "gladiador", "templario"],"image_url": "https://github.com/sua-imagem-da-mascara.png"},
    "armadura_real_guerreiro": {"slot": "armadura", "nome_exibicao": "Égide do Rei Caído",  "set_id": "set_heranca_real", "class_req": ["guerreiro", "cavaleiro", "gladiador", "templario"],"image_url": "https://github.com/sua-imagem-da-mascara.png"},
    "calca_real_guerreiro":    {"slot": "calca",    "nome_exibicao": "Grevas Reais Corrompidas", "set_id": "set_heranca_real", "class_req": ["guerreiro", "cavaleiro", "gladiador", "templario"],"image_url": "https://github.com/sua-imagem-da-mascara.png"},
    "botas_real_guerreiro":    {"slot": "botas",    "nome_exibicao": "Sabatões do Rei Caído", "set_id": "set_heranca_real", "class_req": ["guerreiro", "cavaleiro", "gladiador", "templario"],"image_url": "https://github.com/sua-imagem-da-mascara.png"},
    "luvas_real_guerreiro":    {"slot": "luvas",    "nome_exibicao": "Manoplas Reais Corrompidas", "set_id": "set_heranca_real", "class_req": ["guerreiro", "cavaleiro", "gladiador", "templario"],"image_url": "https://github.com/sua-imagem-da-mascara.png"},

    # --- BERSERKER ---
    "machado_real_berserker":  {"slot": "arma",     "nome_exibicao": "Machado da Fúria Real", "set_id": "set_heranca_real", "class_req": ["berserker", "barbaro", "juggernaut", "ira_primordial"],"image_url": "https://github.com/sua-imagem-da-mascara.png"},
    "elmo_real_berserker":     {"slot": "elmo",     "nome_exibicao": "Elmo de Ossos Reais", "set_id": "set_heranca_real", "class_req": ["berserker", "barbaro", "juggernaut", "ira_primordial"],"image_url": "https://github.com/sua-imagem-da-mascara.png"},
    "armadura_real_berserker": {"slot": "armadura", "nome_exibicao": "Peitoral da Fúria Real", "set_id": "set_heranca_real", "class_req": ["berserker", "barbaro", "juggernaut", "ira_primordial"],"image_url": "https://github.com/sua-imagem-da-mascara.png"},
    "calca_real_berserker":    {"slot": "calca",    "nome_exibicao": "Calças da Fúria Real", "set_id": "set_heranca_real", "class_req": ["berserker", "barbaro", "juggernaut", "ira_primordial"],"image_url": "https://github.com/sua-imagem-da-mascara.png"},
    "botas_real_berserker":    {"slot": "botas",    "nome_exibicao": "Botas da Fúria Real", "set_id": "set_heranca_real", "class_req": ["berserker", "barbaro", "juggernaut", "ira_primordial"],"image_url": "https://github.com/sua-imagem-da-mascara.png"},
    "luvas_real_berserker":    {"slot": "luvas",    "nome_exibicao": "Luvas da Fúria Real", "set_id": "set_heranca_real", "class_req": ["berserker", "barbaro", "juggernaut", "ira_primordial"],"image_url": "https://github.com/sua-imagem-da-mascara.png"},

    # --- ASSASSINO ---
    "adaga_real_assassino":    {"slot": "arma",     "nome_exibicao": "Adaga Sombria do Rei", "set_id": "set_heranca_real", "class_req": ["assassino", "ladrao_de_sombras", "ninja", "mestre_das_laminas"],"image_url": "https://github.com/sua-imagem-da-mascara.png"},
    "elmo_real_assassino":     {"slot": "elmo",     "nome_exibicao": "Máscara Sombria do Rei", "set_id": "set_heranca_real", "class_req": ["assassino", "ladrao_de_sombras", "ninja", "mestre_das_laminas"],"image_url": "https://github.com/sua-imagem-da-mascara.png"},
    "armadura_real_assassino": {"slot": "armadura", "nome_exibicao": "Couraça Sombria do Rei", "set_id": "set_heranca_real", "class_req": ["assassino", "ladrao_de_sombras", "ninja", "mestre_das_laminas"],"image_url": "https://github.com/sua-imagem-da-mascara.png"},
    "calca_real_assassino":    {"slot": "calca",    "nome_exibicao": "Calças Sombrias do Rei", "set_id": "set_heranca_real", "class_req": ["assassino", "ladrao_de_sombras", "ninja", "mestre_das_laminas"],"image_url": "https://github.com/sua-imagem-da-mascara.png"},
    "botas_real_assassino":    {"slot": "botas",    "nome_exibicao": "Botas Sombrias do Rei", "set_id": "set_heranca_real", "class_req": ["assassino", "ladrao_de_sombras", "ninja", "mestre_das_laminas"],"image_url": "https://github.com/sua-imagem-da-mascara.png"},
    "luvas_real_assassino":    {"slot": "luvas",    "nome_exibicao": "Luvas Sombrias do Rei", "set_id": "set_heranca_real", "class_req": ["assassino", "ladrao_de_sombras", "ninja", "mestre_das_laminas"],"image_url": "https://github.com/sua-imagem-da-mascara.png"},

    # --- SAMURAI ---
    "katana_real_samurai":     {"slot": "arma",     "nome_exibicao": "Katana do Shogun Caído", "set_id": "set_heranca_real", "class_req": ["samurai", "kensei", "ronin", "shogun"],"image_url": "https://github.com/sua-imagem-da-mascara.png"},
    "elmo_real_samurai":       {"slot": "elmo",     "nome_exibicao": "Kabuto do Shogun Caído", "set_id": "set_heranca_real", "class_req": ["samurai", "kensei", "ronin", "shogun"],"image_url": "https://github.com/sua-imagem-da-mascara.png"},
    "armadura_real_samurai":   {"slot": "armadura", "nome_exibicao": "Do do Shogun Caído", "set_id": "set_heranca_real", "class_req": ["samurai", "kensei", "ronin", "shogun"],"image_url": "https://github.com/sua-imagem-da-mascara.png"},
    "calca_real_samurai":      {"slot": "calca",    "nome_exibicao": "Haidate do Shogun Caído", "set_id": "set_heranca_real", "class_req": ["samurai", "kensei", "ronin", "shogun"],"image_url": "https://github.com/sua-imagem-da-mascara.png"},
    "botas_real_samurai":      {"slot": "botas",    "nome_exibicao": "Suneate do Shogun Caído", "set_id": "set_heranca_real", "class_req": ["samurai", "kensei", "ronin", "shogun"],"image_url": "https://github.com/sua-imagem-da-mascara.png"},
    "luvas_real_samurai":      {"slot": "luvas",    "nome_exibicao": "Kote do Shogun Caído", "set_id": "set_heranca_real", "class_req": ["samurai", "kensei", "ronin", "shogun"],"image_url": "https://github.com/sua-imagem-da-mascara.png"},

    # --- MONGE ---
    "arma_real_monge":         {"slot": "arma",     "nome_exibicao": "Manoplas do Templo Caído", "set_id": "set_heranca_real", "class_req": ["monge", "guardiao_do_templo", "punho_elemental", "ascendente"],"image_url": "https://github.com/sua-imagem-da-mascara.png"},
    "elmo_real_monge":         {"slot": "elmo",     "nome_exibicao": "Bandana do Templo Caído", "set_id": "set_heranca_real", "class_req": ["monge", "guardiao_do_templo", "punho_elemental", "ascendente"],"image_url": "https://github.com/sua-imagem-da-mascara.png"},
    "armadura_real_monge":     {"slot": "armadura", "nome_exibicao": "Gi do Templo Caído", "set_id": "set_heranca_real", "class_req": ["monge", "guardiao_do_templo", "punho_elemental", "ascendente"],"image_url": "https://github.com/sua-imagem-da-mascara.png"},
    "calca_real_monge":        {"slot": "calca",    "nome_exibicao": "Calças do Templo Caído", "set_id": "set_heranca_real", "class_req": ["monge", "guardiao_do_templo", "punho_elemental", "ascendente"],"image_url": "https://github.com/sua-imagem-da-mascara.png"},
    "botas_real_monge":        {"slot": "botas",    "nome_exibicao": "Sandálias do Templo Caído", "set_id": "set_heranca_real", "class_req": ["monge", "guardiao_do_templo", "punho_elemental", "ascendente"],"image_url": "https://github.com/sua-imagem-da-mascara.png"},
    "luvas_real_monge":        {"slot": "luvas",    "nome_exibicao": "Faixas do Templo Caído", "set_id": "set_heranca_real", "class_req": ["monge", "guardiao_do_templo", "punho_elemental", "ascendente"],"image_url": "https://github.com/sua-imagem-da-mascara.png"},

    # --- MAGO ---
    "cajado_real_mago":        {"slot": "arma",     "nome_exibicao": "Cajado Arcano do Rei", "set_id": "set_heranca_real", "class_req": ["mago", "feiticeiro", "elementalista", "arquimago"],"image_url": "https://github.com/sua-imagem-da-mascara.png"},
    "elmo_real_mago":          {"slot": "elmo",     "nome_exibicao": "Coroa Arcana do Rei", "set_id": "set_heranca_real", "class_req": ["mago", "feiticeiro", "elementalista", "arquimago"],"image_url": "https://github.com/sua-imagem-da-mascara.png"},
    "armadura_real_mago":      {"slot": "armadura", "nome_exibicao": "Túnica Arcana do Rei", "set_id": "set_heranca_real", "class_req": ["mago", "feiticeiro", "elementalista", "arquimago"],"image_url": "https://github.com/sua-imagem-da-mascara.png"},
    "calca_real_mago":         {"slot": "calca",    "nome_exibicao": "Calças Arcanas do Rei", "set_id": "set_heranca_real", "class_req": ["mago", "feiticeiro", "elementalista", "arquimago"],"image_url": "https://github.com/sua-imagem-da-mascara.png"},
    "botas_real_mago":         {"slot": "botas",    "nome_exibicao": "Botas Arcanas do Rei", "set_id": "set_heranca_real", "class_req": ["mago", "feiticeiro", "elementalista", "arquimago"],"image_url": "https://github.com/sua-imagem-da-mascara.png"},
    "luvas_real_mago":         {"slot": "luvas",    "nome_exibicao": "Luvas Arcanas do Rei", "set_id": "set_heranca_real", "class_req": ["mago", "feiticeiro", "elementalista", "arquimago"],"image_url": "https://github.com/sua-imagem-da-mascara.png"},

    # --- BARDO ---
    "arma_real_bardo":         {"slot": "arma",     "nome_exibicao": "Alaúde do Réquiem Real", "set_id": "set_heranca_real", "class_req": ["bardo", "menestrel", "encantador", "maestro"],"image_url": "https://github.com/sua-imagem-da-mascara.png"},
    "elmo_real_bardo":         {"slot": "elmo",     "nome_exibicao": "Chapéu do Réquiem Real", "set_id": "set_heranca_real", "class_req": ["bardo", "menestrel", "encantador", "maestro"],"image_url": "https://github.com/sua-imagem-da-mascara.png"},
    "armadura_real_bardo":     {"slot": "armadura", "nome_exibicao": "Casaco do Réquiem Real", "set_id": "set_heranca_real", "class_req": ["bardo", "menestrel", "encantador", "maestro"],"image_url": "https://github.com/sua-imagem-da-mascara.png"},
    "calca_real_bardo":        {"slot": "calca",    "nome_exibicao": "Calças do Réquiem Real", "set_id": "set_heranca_real", "class_req": ["bardo", "menestrel", "encantador", "maestro"],"image_url": "https://github.com/sua-imagem-da-mascara.png"},
    "botas_real_bardo":        {"slot": "botas",    "nome_exibicao": "Botas do Réquiem Real", "set_id": "set_heranca_real", "class_req": ["bardo", "menestrel", "encantador", "maestro"],"image_url": "https://github.com/sua-imagem-da-mascara.png"},
    "luvas_real_bardo":        {"slot": "luvas",    "nome_exibicao": "Luvas do Réquiem Real", "set_id": "set_heranca_real", "class_req": ["bardo", "menestrel", "encantador", "maestro"],"image_url": "https://github.com/sua-imagem-da-mascara.png"},

    # --- CAÇADOR ---
    "arma_real_cacador":       {"slot": "arma",     "nome_exibicao": "Arco do Caçador Real", "set_id": "set_heranca_real", "class_req": ["cacador", "patrulheiro", "franco_atirador", "mestre_da_selva"],"image_url": "https://github.com/sua-imagem-da-mascara.png"},
    "elmo_real_cacador":       {"slot": "elmo",     "nome_exibicao": "Capuz do Caçador Real", "set_id": "set_heranca_real", "class_req": ["cacador", "patrulheiro", "franco_atirador", "mestre_da_selva"],"image_url": "https://github.com/sua-imagem-da-mascara.png"},
    "armadura_real_cacador":   {"slot": "armadura", "nome_exibicao": "Peitoral do Caçador Real", "set_id": "set_heranca_real", "class_req": ["cacador", "patrulheiro", "franco_atirador", "mestre_da_selva"],"image_url": "https://github.com/sua-imagem-da-mascara.png"},
    "calca_real_cacador":      {"slot": "calca",    "nome_exibicao": "Calças do Caçador Real", "set_id": "set_heranca_real", "class_req": ["cacador", "patrulheiro", "franco_atirador", "mestre_da_selva"],"image_url": "https://github.com/sua-imagem-da-mascara.png"},
    "botas_real_cacador":      {"slot": "botas",    "nome_exibicao": "Botas do Caçador Real", "set_id": "set_heranca_real", "class_req": ["cacador", "patrulheiro", "franco_atirador", "mestre_da_selva"],"image_url": "https://github.com/sua-imagem-da-mascara.png"},
    "luvas_real_cacador":      {"slot": "luvas",    "nome_exibicao": "Luvas do Caçador Real", "set_id": "set_heranca_real", "class_req": ["cacador", "patrulheiro", "franco_atirador", "mestre_da_selva"],"image_url": "https://github.com/sua-imagem-da-mascara.png"},

    # --- CURANDEIRO ---
    "arma_real_curandeiro":    {"slot": "arma",     "nome_exibicao": "Cajado do Milagre Real", "set_id": "set_heranca_real", "class_req": ["curandeiro", "clerigo", "druida", "sacerdote"],"image_url": "https://github.com/sua-imagem-da-mascara.png"},
    "elmo_real_curandeiro":    {"slot": "elmo",     "nome_exibicao": "Capuz do Milagre Real", "set_id": "set_heranca_real", "class_req": ["curandeiro", "clerigo", "druida", "sacerdote"],"image_url": "https://github.com/sua-imagem-da-mascara.png"},
    "armadura_real_curandeiro":{"slot": "armadura", "nome_exibicao": "Veste do Milagre Real", "set_id": "set_heranca_real", "class_req": ["curandeiro", "clerigo", "druida", "sacerdote"],"image_url": "https://github.com/sua-imagem-da-mascara.png"},
    "calca_real_curandeiro":   {"slot": "calca",    "nome_exibicao": "Calças do Milagre Real", "set_id": "set_heranca_real", "class_req": ["curandeiro", "clerigo", "druida", "sacerdote"],"image_url": "https://github.com/sua-imagem-da-mascara.png"},
    "botas_real_curandeiro":   {"slot": "botas",    "nome_exibicao": "Sandálias do Milagre Real", "set_id": "set_heranca_real", "class_req": ["curandeiro", "clerigo", "druida", "sacerdote"],"image_url": "https://github.com/sua-imagem-da-mascara.png"},
    "luvas_real_curandeiro":   {"slot": "luvas",    "nome_exibicao": "Luvas do Milagre Real", "set_id": "set_heranca_real", "class_req": ["curandeiro", "clerigo", "druida", "sacerdote"],"image_url": "https://github.com/sua-imagem-da-mascara.png"},
}

def get_item_info(base_id: str) -> dict:
    """Retorna metadados estáticos do item base."""
    return ITEM_DATABASE.get(base_id, {})
