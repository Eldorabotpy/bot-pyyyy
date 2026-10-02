"""Public, read-only encyclopedia built from the game's catalogues."""
import unicodedata


def build_catalog():
    from modules.game_data.classes import CLASSES_DATA
    from modules.game_data.class_evolution import EVOLUTIONS
    from modules.game_data.skills import SKILL_DATA
    from modules.game_data.worldmap import REGIONS_DATA, WORLD_MAP
    from modules.game_data.professions import PROFESSIONS_DATA
    from modules.game_data.items import ITEMS_DATA
    from modules.game_data.monsters import MONSTERS_DATA
    from modules.game_data.map_spawns import MAP_SPAWNS
    from modules.game_data.rune_rules import FAMILIES, EVOLUTION_COSTS, EXTRACTION_GOLD
    from modules.game_data.refining import REFINING_RECIPES
    from modules.alchemy.bruxa_pocoes import RECEITAS_BRUXA
    from modules.crafting_registry import _RECIPES
    from modules.guild_missions.guild_mission_registry import GUILD_MISSIONS
    from modules.dungeons.regions import REGIONAL_DUNGEONS
    from modules.game_data.dungeon_events import DUNGEON_EVENTS
    from modules.clan.clan_registry import CLAN_NIVEIS
    from modules.guild_missions.guild_mission_registry import GUILD_RANKS

    nodes = []
    def clean(value):
        return unicodedata.normalize('NFKC', str(value or '')).strip()

    def name(key):
        labels = {'gold': 'Ouro', 'hp': 'HP', 'max_hp': 'HP máximo', 'max_mana': 'Mana máxima', 'attack': 'Ataque', 'defense': 'Defesa', 'initiative': 'Iniciativa', 'luck': 'Sorte', 'xp': 'Experiência', 'xp_cla': 'Experiência do clã', 'pontos_guilda': 'Pontos da Guilda', 'pontos_cla': 'Pontos do clã', 'heal': 'Recupera HP', 'mana': 'Recupera mana', 'skill_book': 'Tomos de habilidades', 'equipment_base': 'Bases de equipamento', 'consumable': 'Consumíveis especiais', 'consumivel': 'Consumíveis', 'tool': 'Ferramentas', 'reagent': 'Reagentes', 'epica': 'Épica', 'lendaria': 'Lendária', 'epico': 'Épico', 'lendario': 'Lendário', 'runa': 'Runas', 'equipamento': 'Equipamentos'}
        if key in labels:
            return labels[key]
        row = ITEMS_DATA.get(key) or CLASSES_DATA.get(key) or REGIONS_DATA.get(key) or PROFESSIONS_DATA.get(key) or {}
        return clean(row.get('display_name') or key.replace('_', ' ').capitalize())

    def quantities(values):
        def value_text(value):
            if isinstance(value, dict):
                return quantities(value)
            if isinstance(value, (list, tuple)):
                return ', '.join(value_text(v) for v in value)
            if isinstance(value, bool):
                return 'Sim' if value else 'Não'
            return str(value)
        return ' • '.join(f'{name(k)}: {value_text(v)}' for k, v in (values or {}).items()) or 'Nenhum'

    def add(key, parent, title, summary, sections=(), icon='📖'):
        node = dict(id=key, parent=parent, titulo=clean(title), resumo=clean(summary), icone=icon,
                    secoes=[[clean(a), clean(b)] for a, b in sections if b is not None and b != ''])
        nodes.append(node)
        return key

    # Locations verified against the interactive objects and NPC spawns in mapa.js.
    capital = add('regiao:reino_eldora', 'mundo', 'Reino de Eldora', 'Conheça os serviços, mestres e arredores da capital.', icon='🏰')
    places = [
        ('merlin', 'Merlin · Loja do Aventureiro', 'Tenda a sudoeste da capital.', [('Onde encontrar', 'Na tenda da capital. Aproxime-se de Merlin e toque nele para abrir a loja.'), ('Como usar', 'Consulte os produtos e as condições mostradas na Loja do Aventureiro antes de comprar.')]),
        ('flora', 'Flora · Loja do Reino', 'Lojista a leste do Mercado Real.', [('Onde encontrar', 'Procure a Lojista Flora na área comercial a leste. É necessário chegar perto dela para abrir a loja.'), ('Compras', 'Escolha o item e confira seu preço e saldo. Os itens comprados são entregues ao herói.')]),
        ('mercado', 'Mercado Real', 'Comércio entre jogadores.', [('Onde encontrar', 'Edifício com a balança, na região central a leste da capital. Toque na porta para se aproximar; junto à porta, toque novamente para abrir.'), ('Comprar', 'Escolha a aba Ouro ou Gemas. O preço é pelo lote inteiro.'), ('Anunciar', 'Selecione um item da mochila, quantidade, moeda e preço total. O item fica reservado até vender ou cancelar.'), ('Taxa da Coroa', 'A interface desconta 10% e mostra quanto o vendedor receberá. Confira o valor líquido antes de publicar.')]),
        ('guilda', 'Guilda dos Aventureiros · Lyria', 'Contratos e reconhecimento no noroeste da capital.', [('Entrada', 'Procure o emblema da Guilda no canto noroeste da capital.'), ('Reconhecimento', 'Conclua a missão de reconhecimento de Selene e apresente a carta à recepcionista. Ela é recolhida ao registrar o aventureiro.'), ('Contratos', 'Pessoais e Do clã possuem listas de disponíveis, em andamento e histórico. Leia objetivos, modo de caça e participação mínima.'), ('Entrega e loja', 'Concluir os abates não substitui a entrega: registre a recompensa. A loja da Guilda possui produtos com requisitos de rank e pontos.')]),
        ('forja', 'Forja de Thorek', 'Bancada na área leste da capital.', [('Onde encontrar', 'Bigorna com a placa Forja, próxima ao Mestre Thorek.'), ('Fabricação', 'Escolha a profissão e a receita. Confira nível, ferramenta, ingredientes e tempo; inicie o trabalho e recolha o resultado ao terminar.'), ('Melhoria', 'Escolha o equipamento e confira materiais, chance de sucesso e proteção apresentados na tela.'), ('Runas', 'A área de runas permite consultar encaixes e executar as operações disponíveis no equipamento.')]),
        ('refino', 'Fornalha de Refino', 'Fornalha a sudeste, perto de Paracelso.', [('Onde encontrar', 'Procure a placa Refino, abaixo da área da Forja.'), ('Funcionamento', 'Escolha uma profissão compatível e uma receita. O refino transforma ingredientes em componentes para outras fabricações.'), ('Requisitos', 'Cada receita define profissões permitidas, nível, ingredientes, produção e tempo. Consulte o catálogo em Forja e alquimia.')]),
        ('varek', 'Capitão Varek', 'Guia dos primeiros passos.', [('Onde encontrar', 'Na parte central oeste da capital, patrulhando os arredores.'), ('Primeiros objetivos', 'As missões iniciais pedem alcançar os níveis 2, 4 e 5. Retorne para registrar cada etapa.'), ('Próximo passo', 'Após a provação, Varek encaminha o herói à Arquimaga Selene para o despertar da classe.')]),
        ('selene', 'Arquimaga Selene', 'Despertar, Grimório e reconhecimento.', [('Onde encontrar', 'No pátio do castelo, ao norte da capital.'), ('Classe', 'Conclua a provação de Varek e alcance o nível 5 para seguir o despertar.'), ('Grimório', 'Após o ofício de Thorek, a missão exige nível 17, 15 Ectoplasmas e 30 Couros de Lobo Alfa. A habilidade liberada é equipada pela área de Magias do perfil.'), ('Reconhecimento', 'Depois do Grimório, retorne no nível 20 e cumpra a prova de reconhecimento para obter a recomendação à Guilda.')]),
        ('thorek', 'Mestre-Artesão Thorek', 'Licença de profissão, Ferreiro e Armeiro.', [('Onde encontrar', 'Na área leste, perto da Forja.'), ('Primeiro ofício', 'A etapa de profissão vem após o despertar de classe e indica nível 7. Fale com Thorek para avançar.'), ('Especialidades', 'Thorek é mestre de Ferreiro e Armeiro. Outros ofícios possuem seus próprios mestres.'), ('Maestria', 'Ao atingir nível 50 no ofício, procure o mestre correspondente para o Selo de Maestria. O Tratado das Guildas orienta a próxima categoria de profissão.')]),
        ('paracelso', 'Alquimista Paracelso', 'Mestre de Alquimista e Joalheiro.', [('Onde encontrar', 'Na parte sudeste da capital, perto da fornalha de refino.'), ('Acesso', 'Conclua a etapa de profissão de Thorek antes de procurar Paracelso.'), ('Ofícios', 'Alquimista coleta fluidos e essências; Joalheiro é uma profissão de produção. Consulte as ferramentas e receitas de cada ofício.')]),
        ('arredores', 'Arredores e saída', 'Caça inicial e caminho para a Pradaria.', [('Criaturas', 'Os arredores da capital possuem Pequeno Slime, Slime Verde, Slime da Terra, Slime da Escuridão e Goblin Batedor. A cidade não é inteiramente livre de inimigos.'), ('Exploração', 'A saída da capital leva à Pradaria Inicial. Prepare consumíveis e equipamentos antes de seguir.')]),
    ]
    for key, title, summary, sections in places:
        add('capital:' + key, capital, title, summary, sections)
    add('merlin:estoque', 'capital:merlin', 'Poções e materiais vendidos', 'Produtos da loja a ouro.', [('Poções', 'Cura e Mana P: 100 Ouro cada; M: 300 Ouro; G: 1.000 Ouro.'), ('Materiais', 'Pedra de Aprimoramento: 500 Ouro; Núcleo de Forja: 500 Ouro; Pergaminho de Reparo: 1.000 Ouro.'), ('Antes de comprar', 'Confira o preço atual exibido na loja e o saldo do herói.')])
    add('flora:estoque', 'capital:flora', 'Tesouro do Rei', 'Compras com Gemas.', [('Produtos', 'Poção de XP P: 15 Gemas, XP de combate dobrado por 15 minutos. Poção de XP G: 60 Gemas, por 60 minutos. Ative as poções na mochila; o tempo continua offline e usos adicionais somam duração. Incubadora: 25 Gemas, um único ovo. Use em Bestiário → Companheiros.'), ('Como comprar', 'Abra a loja junto de Flora e selecione Adquirir. Confira o saldo em Gemas antes de confirmar.')])
    add('capital:estatua', capital, 'Monumento de Pedroca', 'Memória da origem de Eldora.', [('Onde encontrar', 'Na praça central da capital.'), ('Inscrição', 'Foi daqui que tudo começou. Aqui nasceu o sonho de Eldora.')], '🗿')
    for key in ('merlin', 'flora', 'mercado'):
        original = next(n for n in nodes if n['id'] == 'capital:' + key)
        add('economia:' + key, 'economia', original['titulo'], original['resumo'], original['secoes'], '⚖️')
    for key, title, summary, sections in [
        ('fisico', 'Ataque e defesa', 'Como os golpes encontram a proteção do alvo.', [('Ataque físico', 'Ataques físicos usam o ataque do herói. A defesa do alvo participa do cálculo do dano.'), ('Penetração', 'Habilidades e efeitos podem reduzir a defesa considerada para um golpe.'), ('Equipamento', 'Classe, equipamentos e efeitos ativos alteram os atributos usados no combate.')]),
        ('magico', 'Magias e mana', 'Poder mágico, custo e recarga.', [('Poder mágico', 'Dano mágico usa o poder mágico do atacante. Cada habilidade define seu efeito e condições.'), ('Mana e recarga', 'Confira custo de mana e tempo de recarga antes de escolher a habilidade. Consulte a página da classe para ver cada magia.'), ('Grimório', 'A missão de Selene libera a primeira habilidade; equipe-a na área de Magias do perfil.')]),
        ('duplo', 'Iniciativa e ataque duplo', 'Uma ação pode produzir mais de um golpe.', [('Ataque duplo', 'Nos ataques básicos, a iniciativa e os bônus de ataque duplo contribuem para uma chance adicional, limitada a 50%.'), ('Sequência', 'Os golpes são resolvidos separadamente. Acompanhe dano e efeitos de cada ataque no registro de combate.')]),
        ('critico', 'Sorte e críticos', 'Chance e força dos acertos críticos.', [('Sorte', 'A sorte contribui para a chance crítica, com retornos decrescentes.'), ('Excedente', 'A chance teórica acima do limite contribui para o dano crítico. Efeitos e habilidades também podem modificar o golpe.')]),
        ('vampiro', 'Roubo de vida', 'Recuperação ligada ao dano causado.', [('Origem', 'A família de runas Vampiro concede roubo de vida. Confira se a runa está encaixada em um equipamento em uso.'), ('Recuperação', 'O efeito depende do dano e da vida que falta ao herói. Com a vida cheia, a cura efetiva pode ser zero.')]),
    ]:
        add('combate:' + key, 'combate', title, summary, sections, '⚔️')

    monsters = {m['id']: m for group in MONSTERS_DATA.values() if isinstance(group, list) for m in group if isinstance(m, dict) and m.get('id')}
    for key, region in REGIONS_DATA.items():
        if key == 'reino_eldora':
            rid = capital
        else:
            rid = add('regiao:' + key, 'mundo', name(key), region.get('description') or 'Explore os habitantes e recursos desta região.', [('Caminhos', ', '.join(name(x) for x in WORLD_MAP.get(key, []))), ('Recurso regional', name(region['resource']) if region.get('resource') else 'Sem recurso indicado.')], region.get('emoji', '🌍'))
        spawn_key = 'capital_eldora' if key == 'reino_eldora' else key
        mob_ids = list(dict.fromkeys(s['monster_id'] for s in MAP_SPAWNS.get(spawn_key, [])))
        if not mob_ids:
            mob_ids = [m['id'] for m in MONSTERS_DATA.get(key, []) if isinstance(m, dict) and m.get('id')]
        bestiary = add('bestiario:' + key, 'criaturas', 'Criaturas · ' + name(key), 'Atributos de referência; podem variar no combate.')
        for mid in mob_ids:
            m = monsters.get(mid)
            if not m:
                continue
            sections = [('Atributos base', ' • '.join(f'{label}: {m[k]}' for k, label in [('hp', 'HP'), ('attack', 'Ataque'), ('defense', 'Defesa'), ('initiative', 'Iniciativa'), ('luck', 'Sorte')] if k in m)), ('Recompensas base', f"XP: {m.get('xp_reward', 0)} • Ouro: {m.get('gold_drop', 0)}"), ('Região', name(key))]
            add('mob:' + key + ':' + mid, bestiary, m.get('name', mid), m.get('description') or 'Criatura de ' + name(key), sections, '🐾')
            add('encontro:' + key + ':' + mid, rid, m.get('name', mid), 'Criatura encontrada nesta região.', sections, '🐾')

    for key, c in CLASSES_DATA.items():
        if c.get('tier') != 1:
            continue
        cid = add('classe:' + key, 'classes', c['display_name'], c.get('description'), [('Perfil de atributos', ' • '.join(f'{name(k)}: ×{v}' for k, v in c.get('stat_modifiers', {}).items())), ('Como despertar', 'Complete a provação de Varek e procure Selene no nível 5. A seleção da classe acontece no diálogo de despertar.')], c.get('emoji', '⚔️'))
        for sid, skill in SKILL_DATA.items():
            if key not in skill.get('allowed_classes', []):
                continue
            sections = [('Descrição', skill.get('description')), ('Mana', skill.get('mana_cost')), ('Recarga', skill.get('cooldown'))]
            sections += [(name(r), data.get('description')) for r, data in skill.get('rarity_effects', {}).items()]
            add('skill:' + key + ':' + sid, cid, skill.get('display_name', sid), 'Habilidade · ' + skill.get('type', 'classe'), sections, '✨')
        for i, evo in enumerate(EVOLUTIONS.get(key, [])):
            sections = [('Nível mínimo', evo.get('min_level')), ('Classe anterior', name(evo.get('from', key)))]
            sections += [(step.get('desc', 'Etapa'), quantities(step.get('cost'))) for step in evo.get('ascension_path', [])]
            if evo.get('trial_monster_id'):
                sections.append(('Prova de evolução', monsters.get(evo['trial_monster_id'], {}).get('name', name(evo['trial_monster_id']))))
            add(f'evolucao:{key}:{i}', cid, evo.get('display_name') or name(evo['to']), evo.get('desc', 'Evolução de classe'), sections, '🌟')

    mentors = {'lenhador': 'Sylas · Floresta Sombria', 'minerador': 'Bórin · Pedreira de Granito', 'esfolador': 'Grom · Pradaria Inicial', 'curtidor': 'Grom · Pradaria Inicial', 'colhedor': 'Elara · Pradaria Inicial', 'alfaiate': 'Elara · Pradaria Inicial', 'alquimista': 'Paracelso · Capital', 'joalheiro': 'Paracelso · Capital', 'ferreiro': 'Thorek · Capital', 'armeiro': 'Thorek · Capital'}
    for key, p in PROFESSIONS_DATA.items():
        add('profissao:' + key, 'profissoes', name(key), 'Coleta' if p.get('category') == 'gathering' else 'Produção', [('Mestre', mentors.get(key)), ('Recursos', ', '.join(name(r) for r in p.get('resources', {}).values())), ('Ferramenta', 'Equipe a ferramenta do ofício e confira a durabilidade antes de trabalhar.')], '🛠️')
    for key, region, title, professions in [('grom', 'pradaria_inicial', 'Grom, o Caçador', 'Esfolador e Curtidor'), ('elara', 'pradaria_inicial', 'Madame Elara', 'Colhedor e Alfaiate'), ('sylas', 'floresta_sombria', 'Guarda-Bosque Sylas', 'Lenhador'), ('borin', 'pedreira_granito', 'Mestre Bórin', 'Minerador')]:
        add('npc:' + key, 'regiao:' + region, title, 'Mestre de ' + professions, [('Ofícios', professions), ('Aprendizado', 'Complete a etapa de profissão de Thorek. Procure o mestre e confira as condições do ofício que deseja aprender.'), ('Maestria', 'Volte ao mestre correspondente ao atingir nível 50 no ofício para consultar o reconhecimento de maestria.')], '🛠️')
    add('npc:bruxa', 'regiao:floresta_sombria', 'Bruxa das Poções', 'O Caldeirão da Bruxa', [('Preparação', 'Leve os ingredientes de cada receita. Cada preparo produz uma poção.'), ('Custo', 'As receitas de HP e Mana não cobram ouro. Elixir de Experiência: 500 Ouro; Elixir Superior: 1.000 Ouro.'), ('Receitas', 'Encontre a lista completa de ingredientes em Forja e alquimia → Caldeirão da Bruxa.')], '⚗️')

    groups = {}
    for key, item in ITEMS_DATA.items():
        kind = item.get('type', 'material')
        if kind not in groups:
            groups[kind] = add('tipo-item:' + kind, 'itens', name(kind), 'Itens desta categoria.', icon='🎒')
        sections = [('Descrição', item.get('description') or item.get('desc')), ('Raridade', item.get('rarity')), ('Tier', item.get('tier')), ('Nível exigido', item.get('level_req')), ('Durabilidade inicial', ' / '.join(map(str, item['durability'])) if isinstance(item.get('durability'), list) else item.get('durability'))]
        if item.get('effects'):
            sections.append(('Efeitos', quantities(item['effects'])))
        if item.get('class_req'):
            req = item['class_req']
            sections.append(('Classes permitidas', ', '.join(name(c) for c in (req if isinstance(req, list) else [req]))))
        if item.get('slot'):
            sections.append(('Espaço de equipamento', name(item['slot'])))
        add('item:' + key, groups[kind], name(key), item.get('description') or item.get('desc') or 'Consulte as características do item.', sections, item.get('emoji', '📦'))
        if item.get('tool_type') in PROFESSIONS_DATA:
            add('ferramenta:' + key, 'profissao:' + item['tool_type'], name(key), 'Ferramenta deste ofício.', sections, '🔧')

    for family, (title, stat, values, label, unit, color) in FAMILIES.items():
        fid = add('runa:' + family, 'runas', 'Runa de ' + title, label, [('Extração', f'{EXTRACTION_GOLD} Ouro'), ('Encaixes', 'Raro: 1 • Épico: 2 • Lendário: 3')], '🔮')
        for i, value in enumerate(values):
            add(f'runa:{family}:{i}', fid, ['Menor', 'Maior', 'Ancestral'][i], f'+{value}{unit} {label}', [('Efeito', f'+{value}{unit} {label}'), ('Próxima evolução', quantities(EVOLUTION_COSTS[i+1]) if i+1 in EVOLUTION_COSTS else 'Nível máximo desta família.')])

    for label, recipes in [('Forja', _RECIPES), ('Refino', REFINING_RECIPES), ('Caldeirão da Bruxa', RECEITAS_BRUXA)]:
        parent = add('receitas:' + label, 'forja_alquimia', label, 'Receitas, ingredientes e requisitos.', icon='⚗️')
        for key, recipe in recipes.items():
            prof = recipe.get('profession', [])
            if isinstance(prof, str):
                prof = [prof]
            sections = [('Ingredientes', quantities(recipe.get('inputs'))), ('Profissão', ', '.join(name(x) for x in prof)), ('Nível exigido', recipe.get('level_req')), ('Tempo em segundos', recipe.get('time_seconds')), ('Custo em ouro', recipe.get('gold_cost')), ('Resultado', quantities(recipe.get('outputs')) if recipe.get('outputs') else name(recipe.get('result_base_id', key)))]
            title = recipe.get('display_name') or recipe.get('name') or name(key)
            add('receita:' + label + ':' + key, parent, title, 'Consulte o preparo e os requisitos.', sections)
            for p in prof:
                if p in PROFESSIONS_DATA:
                    add('oficio-receita:' + label + ':' + key + ':' + p, 'profissao:' + p, title, label, sections)

    for key, m in GUILD_MISSIONS.items():
        if not m.get('ativa', True):
            continue
        add('contrato:' + key, 'guilda', m.get('nome', key), m.get('descricao'), [('Objetivo', m.get('objetivo', {}).get('texto')), ('Nível mínimo', m.get('nivel_minimo')), ('Modo', m.get('modo')), ('Tipo', m.get('tipo')), ('Recompensas', quantities(m.get('recompensas')))], '📜')
    for key, d in REGIONAL_DUNGEONS.items():
        did = add('calabouco:' + key, 'dungeons', d.get('label', name(key)), 'Calabouço regional · ' + name(key), [('Chave', name(d['key_item']) if d.get('key_item') else 'Consulte a entrada.'), ('Ouro base', d.get('gold_base'))], '🏰')
        for i, floor in enumerate(d.get('floors', [])):
            if hasattr(floor, 'display'):
                add(f'andar:{key}:{i}', did, f'Andar {i+1} · {clean(floor.display)}', 'Encontro do calabouço.', [('Atributos base', quantities(floor.stats_base))], floor.emoji)
    for level, data in CLAN_NIVEIS.items():
        add(f'cla:nivel:{level}', 'clas', f'Clã · Nível {level}', f"Capacidade: {data['capacidade']} membros.", [('Capacidade', data['capacidade']), ('XP para evolução', data.get('xp_evolucao')), ('Ouro para evolução', data.get('ouro_evolucao')), ('Limites da loja', quantities(data.get('beneficios', {}).get('limites_loja')))], '🛡️')
    for rank in GUILD_RANKS:
        add('guilda:rank:' + rank['id'], 'guilda', 'Rank ' + rank['nome'], 'Progressão de reputação.', [('Reputação mínima', rank['reputacao_minima']), ('Como avançar', 'Conclua e entregue contratos. Confira o rank exigido antes de gastar pontos na loja.')], '🏅')
    for region, events in DUNGEON_EVENTS.items():
        eid = add('eventos:' + region, 'eventos', 'Tesouros · ' + name(region), 'Eventos de exploração e baús.', icon='📦')
        did = add('exploracao:' + region, 'dungeons', name(region), 'Mapa de exploração com baús e enigmas.', [('Baús', 'Procure os tesouros no mapa. O baú especial exige atenção ao enigma; os demais seguem suas próprias regras de abertura.')], '🏰')
        for key, event in events.items():
            sections = [('Funcionamento', 'Observe e repita a sequência das pedras. Erros ou a abertura antecipada podem despertar um Mímico.' if event.get('event_type') == 'mimic_sequence' else 'Interaja com o baú durante a exploração. Um Mímico pode transformar a abertura em combate.'), ('Preparação', 'Confira HP, mana e equipamentos antes de interagir. A recompensa depende do evento.')]
            add(f'evento:{region}:{key}', eid, name(key), 'Enigma' if event.get('event_type') == 'mimic_sequence' else 'Baú de exploração', sections, '📦')
            add(f'tesouro:{region}:{key}', did, name(key), 'Tesouro do mapa', sections, '📦')
    return nodes
