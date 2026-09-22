# modules/game_data/map_spawns.py

# modules/game_data/map_spawns.py

def gerar_spawns(prefixo_regiao, lista_mobs, respawn_padrao=30):
    """
    Função mágica que gera os dicionários de monstros rapidamente!
    Ele já multiplica o X e Y por 32 automaticamente e gera um ID único.
    """
    spawns = []
    for index, (monster_id, x, y) in enumerate(lista_mobs):
        spawns.append({
            "spawn_id": f"{prefixo_regiao}_{monster_id}_{index + 1:02d}", # Ex: capital_slime_verde_01
            "monster_id": monster_id,
            "x": x * 32, # Já multiplica direto aqui!
            "y": y * 32,
            "respawn_segundos": respawn_padrao
        })
    return spawns

# ==========================================
# LISTA DE MONSTROS NO MAPA
# Formato: ("id_do_monstro", posicao_x, posicao_y)
# ==========================================

MAP_SPAWNS = {
    
    "capital_eldora": gerar_spawns("capital", [
        ("pequeno_slime", 3, 54),
        ("pequeno_slime", 5, 50),
        ("slime_verde", 7, 56),
        ("slime_verde", 12, 56),
        ("slime_escuridao", 17, 51),
        ("slime_terra", 21, 55),
        ("pequeno_slime", 25, 51),
        ("pequeno_slime", 33, 50),
        ("slime_terra", 36, 53),
        ("pequeno_slime", 39, 55),
        ("goblin_batedor", 44, 56),
        ("pequeno_slime", 46, 50),
        ("slime_terra", 50, 51),
        ("slime_escuridao", 50, 55),
        ("slime_terra", 54, 56),
        ("goblin_batedor", 59, 52),
        
    ]),
    
    "pradaria_inicial": gerar_spawns("pradaria", [
        
        # ==========================================
        # 🟢 ZONA NOROESTE (Top-Left) - Nível Baixo
        # ==========================================
        ("pequeno_slime", 8, 5), 
        ("pequeno_slime", 8, 8), 
        ("pequeno_slime", 12, 7),
        ("pequeno_slime", 10, 6), 
        ("pequeno_slime", 10, 1), 
        ("pequeno_slime", 13, 5),
        ("pequeno_slime", 14, 7),    
        ("pequeno_slime", 4, 3), 
        ("pequeno_slime", 6, 6), 
        ("pequeno_slime", 11, 3),
        ("pequeno_slime", 15, 4), 
        ("pequeno_slime", 5, 9), 
        ("pequeno_slime", 12, 10),
        ("pequeno_slime", 16, 2), 
        ("pequeno_slime", 18, 6),
        
        # ==========================================
        # 🟩 ZONA CENTRO-OESTE (Mid-Left)
        # ==========================================
        ("slime_verde", 13, 15), 
        ("slime_verde", 9, 13), 
        ("slime_verde", 6, 13), 
        ("slime_verde", 10, 22), 
        ("slime_verde", 15, 25), 
        ("slime_verde", 20, 21),
        ("slime_verde", 5, 15),
        ("slime_verde", 8, 17), 
        ("slime_verde", 12, 19), 
        ("slime_verde", 16, 14), 
        ("slime_verde", 18, 18), 
        ("slime_verde", 22, 16), 
        ("slime_verde", 7, 24), 
        ("slime_verde", 12, 26), 
        ("slime_verde", 18, 24),
        ("slime_verde", 24, 20), 
        ("slime_verde", 26, 26),
        
        # ==========================================
        # 🔵 ZONA SUDOESTE (Bottom-Left)
        # ==========================================
        ("slime_azul", 8, 40), 
        ("slime_azul", 12, 48), 
        ("slime_azul", 18, 42),
        ("slime_azul", 5, 39), 
        ("slime_azul", 9, 42), 
        ("slime_azul", 14, 40), 
        ("slime_azul", 16, 46), 
        ("slime_azul", 19, 39), 
        ("slime_azul", 7, 47),
        ("slime_azul", 11, 44), 
        ("slime_azul", 22, 40),

        ("slime_terra", 10, 52), 
        ("slime_terra", 22, 45), 
        ("slime_terra", 20, 54),
        ("slime_terra", 8, 51), 
        ("slime_terra", 12, 54), 
        ("slime_terra", 15, 50), 
        ("slime_terra", 18, 56), 
        ("slime_terra", 24, 50), 
        ("slime_terra", 25, 55),
        ("slime_terra", 13, 57), 
        ("slime_terra", 27, 52),

        # ==========================================
        # ✨ ZONA NORDESTE (Top-Right)
        # ==========================================
        ("slime_brilhante", 36, 8), 
        ("slime_brilhante", 42, 6),
        ("slime_brilhante", 46, 9),
        ("slime_brilhante", 35, 5),
        ("slime_brilhante", 39, 10), 
        ("slime_brilhante", 44, 4), 
        ("slime_brilhante", 49, 7), 
        ("slime_brilhante", 53, 5), 
        ("slime_brilhante", 55, 10), 
        ("slime_brilhante", 41, 13), 
        ("slime_brilhante", 48, 14), 
        ("slime_brilhante", 56, 15),
        
        # ==========================================
        # ☠️ ZONA CENTRO-LESTE (Mid-Right)
        # ==========================================
        ("slime_venenoso", 38, 28), 
        ("slime_venenoso", 42, 32), 
        ("slime_venenoso", 36, 35),
        ("slime_venenoso", 35, 22),
        ("slime_venenoso", 39, 24), 
        ("slime_venenoso", 43, 20), 
        ("slime_venenoso", 34, 29), 
        ("slime_venenoso", 39, 34), 
        ("slime_venenoso", 44, 31),
        ("slime_venenoso", 32, 25), 
        ("slime_venenoso", 31, 33),

        ("slime_eletrico", 48, 25), 
        ("slime_eletrico", 52, 30), 
        ("slime_eletrico", 50, 34),  
        ("slime_eletrico", 47, 21), 
        ("slime_eletrico", 52, 23), 
        ("slime_eletrico", 54, 28), 
        ("slime_eletrico", 47, 32),
        ("slime_eletrico", 53, 35), 
        ("slime_eletrico", 57, 22),
        ("slime_eletrico", 56, 31),

        # ==========================================
        # 🌑 ZONA SUDESTE (Bottom-Right) - Nível Alto
        # ==========================================
        ("slime_escuridao", 35, 45), 
        ("slime_escuridao", 38, 52), 
        ("slime_escuridao", 32, 48),
        ("slime_escuridao", 30, 44), 
        ("slime_escuridao", 33, 52), 
        ("slime_escuridao", 37, 43), 
        ("slime_escuridao", 40, 48), 
        ("slime_escuridao", 43, 44),
        ("slime_escuridao", 44, 54),
        ("slime_escuridao", 31, 56), 
        ("slime_escuridao", 41, 56),
        
        ("slime_magma", 48, 46), 
        ("slime_magma", 54, 50), 
        ("slime_magma", 50, 54),
        ("slime_magma", 47, 43), 
        ("slime_magma", 51, 48), 
        ("slime_magma", 55, 45), 
        ("slime_magma", 46, 52), 
        ("slime_magma", 53, 55), 
        ("slime_magma", 57, 42),
        ("slime_magma", 58, 49),

        # ==========================================
        # 👑 CHEFE DO MAPA
        # ==========================================
        ("rei_slime", 52, 40)
    ]),
    
    "floresta_sombria": gerar_spawns("floresta", [
        
        # ==========================================
        # 🗡️ ENTRADA SOMBRIA (Noroeste / Top-Left)
        # ==========================================
        ("goblin_batedor", 5, 5), 
        ("goblin_batedor", 8, 7), 
        ("goblin_batedor", 12, 4),
        ("goblin_batedor", 10, 10), 
        ("goblin_batedor", 15, 8), 
        ("goblin_batedor", 6, 12),
        ("goblin_batedor", 14, 14),
        ("goblin_batedor", 18, 6),
        
        ("espectro_do_bosque", 7, 18), 
        ("espectro_do_bosque", 11, 22), 
        ("espectro_do_bosque", 15, 17), 
        ("espectro_do_bosque", 18, 20),

        # ==========================================
        # 🐺 BOSQUE DOS UIVOS (Nordeste / Top-Right)
        # ==========================================
        ("lobo_magro", 35, 6), 
        ("lobo_magro", 40, 5), 
        ("lobo_magro", 45, 8),
        ("lobo_magro", 38, 12), 
        ("lobo_magro", 42, 15), 
        ("lobo_magro", 48, 10),
        ("lobo_magro", 52, 6), 
        ("lobo_magro", 55, 12), 
        ("lobo_magro", 50, 18),
        ("lobo_alfa", 44, 12), 
        ("lobo_alfa", 49, 15), 
        ("lobo_alfa", 54, 9),

        # ==========================================
        # 🐗 CLAREIRA CENTRAL (Centro / Mid)
        # ==========================================
        ("javali_com_presas", 25, 25), 
        ("javali_com_presas", 28, 22), 
        ("javali_com_presas", 32, 28), 
        ("javali_com_presas", 35, 25), 
        ("javali_com_presas", 22, 30),
        ("javali_com_presas", 30, 32), 
        ("javali_com_presas", 38, 30), 
        ("javali_com_presas", 26, 35),

        # ==========================================
        # ⛺ ACAMPAMENTO GOBLIN (Centro-Oeste / Mid-Left)
        # ==========================================
        ("goblin_batedor", 5, 25), 
        ("goblin_batedor", 9, 28), 
        ("goblin_batedor", 14, 26),
        ("goblin_batedor", 6, 32),
        ("goblin_batedor", 12, 35),
        
        ("xama_goblin", 8, 30),
        ("xama_goblin", 15, 32),
        ("xama_goblin", 10, 38), 
        ("xama_goblin", 5, 40),

        # ==========================================
        # 🍄 PÂNTANO FÚNGICO (Sudoeste / Bottom-Left)
        # ==========================================
        ("cogumelo_gigante", 6, 45),
        ("cogumelo_gigante", 10, 42),
        ("cogumelo_gigante", 14, 48),
        ("cogumelo_gigante", 8, 52), 
        ("cogumelo_gigante", 12, 55),
        ("cogumelo_gigante", 16, 50),
        ("cogumelo_gigante", 20, 45),
        ("cogumelo_gigante", 22, 52), 
        ("cogumelo_gigante", 25, 48),
        ("cogumelo_gigante", 18, 56),

        # ==========================================
        # 🌳 CORAÇÃO DA FLORESTA (Sudeste / Bottom-Right)
        # ==========================================
        ("ent_jovem", 35, 45), 
        ("ent_jovem", 40, 42),
        ("ent_jovem", 45, 48),
        ("ent_jovem", 38, 52),
        ("ent_jovem", 42, 55), 
        ("ent_jovem", 48, 50),
        ("ent_jovem", 52, 45),
        ("ent_jovem", 55, 52), 
        ("ent_jovem", 50, 56),
        
        ("espectro_do_bosque", 30, 48),
        ("espectro_do_bosque", 33, 54), 
        ("espectro_do_bosque", 45, 54),
        ("espectro_do_bosque", 56, 48)
    ]),
    
    # ==========================================
    # ⛰️ PEDREIRA DE GRANITO (LOTADA)
    # ==========================================
    "pedreira_granito": gerar_spawns("pedreira", [
        # ⛏️ Kobolds Escavadores (Infestando o Norte e o Oeste)
        ("kobold_escavador", 8, 10), 
        ("kobold_escavador", 12, 11), 
        ("kobold_escavador", 15, 15),
        ("kobold_escavador", 10, 18), 
        ("kobold_escavador", 18, 12), 
        ("kobold_escavador", 22, 10),
        ("kobold_escavador", 5, 25), 
        ("kobold_escavador", 8, 30), 
        ("kobold_escavador", 12, 28),
        ("kobold_escavador", 25, 15), 
        ("kobold_escavador", 28, 12), 
        ("kobold_escavador", 30, 18),
        ("kobold_escavador", 15, 20), 
        ("kobold_escavador", 18, 22), 
        ("kobold_escavador", 20, 25),

        # 🪨 Tatus de Rocha (Espalhados pelo Centro e Leste)
        ("tatu_de_rocha", 20, 20), 
        ("tatu_de_rocha", 25, 22), 
        ("tatu_de_rocha", 22, 26),
        ("tatu_de_rocha", 30, 25), 
        ("tatu_de_rocha", 35, 20), 
        ("tatu_de_rocha", 38, 24),
        ("tatu_de_rocha", 40, 28), 
        ("tatu_de_rocha", 45, 25), 
        ("tatu_de_rocha", 48, 20),
        ("tatu_de_rocha", 50, 30), 
        ("tatu_de_rocha", 55, 28), 
        ("tatu_de_rocha", 42, 32),
        ("tatu_de_rocha", 32, 22), 
        ("tatu_de_rocha", 28, 28), 
        ("tatu_de_rocha", 48, 28),

        # 🗿 Golens de Pedra Pequenos (Miolo e áreas rochosas)
        ("golem_de_pedra_pequeno", 35, 35), 
        ("golem_de_pedra_pequeno", 38, 38), 
        ("golem_de_pedra_pequeno", 40, 34),
        ("golem_de_pedra_pequeno", 45, 36), 
        ("golem_de_pedra_pequeno", 48, 40), 
        ("golem_de_pedra_pequeno", 50, 35),
        ("golem_de_pedra_pequeno", 30, 40), 
        ("golem_de_pedra_pequeno", 32, 45), 
        ("golem_de_pedra_pequeno", 25, 38),
        ("golem_de_pedra_pequeno", 28, 42), 
        ("golem_de_pedra_pequeno", 42, 38), 
        ("golem_de_pedra_pequeno", 38, 42),

        # 🔥 Salamandras de Pedra (Parte Sul, onde deve ser mais quente/profundo)
        ("salamandra_de_pedra", 15, 45), 
        ("salamandra_de_pedra", 18, 48), 
        ("salamandra_de_pedra", 20, 52),
        ("salamandra_de_pedra", 25, 50), 
        ("salamandra_de_pedra", 30, 55), 
        ("salamandra_de_pedra", 35, 48),
        ("salamandra_de_pedra", 40, 52), 
        ("salamandra_de_pedra", 45, 50), 
        ("salamandra_de_pedra", 50, 55),
        ("salamandra_de_pedra", 22, 48), 
        ("salamandra_de_pedra", 38, 55), 
        ("salamandra_de_pedra", 48, 52),

        # 🦇 Gárgulas de Vigia (Vigiando os extremos e cantos isolados)
        ("gargula_de_vigia", 5, 5), 
        ("gargula_de_vigia", 55, 5), 
        ("gargula_de_vigia", 5, 55),
        ("gargula_de_vigia", 55, 55), 
        ("gargula_de_vigia", 50, 10), 
        ("gargula_de_vigia", 10, 50),
        ("gargula_de_vigia", 48, 48), 
        ("gargula_de_vigia", 12, 45), 
        ("gargula_de_vigia", 30, 10),

        # 🦎 Basiliscos Jovens (Os perigos reais espalhados estrategicamente)
        ("basilisco_jovem", 30, 30), 
        ("basilisco_jovem", 45, 45), 
        ("basilisco_jovem", 20, 35),
        ("basilisco_jovem", 38, 50), 
        ("basilisco_jovem", 52, 42), 
        ("basilisco_jovem", 15, 35),
    ]),

    # ==========================================
    # 🏰 DUNGEON 01
    # ==========================================
    "dungeon_01": gerar_spawns("dungeon01", [

        # Os mobs normais da dungeon serão
        # adicionados aqui depois.

        # IMPORTANTE:
        # mimico_dungeon_01 NÃO entra aqui.
        # Ele só nasce através do puzzle do baú.

    ]),
}
