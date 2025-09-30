# Em modules/chat_responses.py

CHAT_RESPONSES = {
    ("bom dia",): [
        {"type": "text", "content": "Bom dia, aventureiro! Que seus saques sejam épicos hoje!"},
        {"type": "text", "content": "Bom dia! O sol brilha para mais uma jornada em Eldora!"},
        # Para obter o file_id, envie um Sticker para o seu bot e encaminhe para @JsonDumpBot
        {"type": "sticker", "content": "CAACAgIAAxkBAAIBp2T5y6mDk2c2Vw_VLroe2i37h-5_AAJqAAM-vKAZ3z2aY2a-5gQzBA"} 
    ],
    ("boa noite", "fui"): [
        {"type": "text", "content": "Boa noite! Que seus sonhos sejam livres de dragões..."},
        {"type": "text", "content": "Até amanhã! Descanse bem, a aventura continua ao amanhecer."},
        # Para obter o file_id, envie um GIF para o seu bot e encaminhe para @JsonDumpBot
        {"type": "gif", "content": "CgACAgQAAxkBAAIBqGT5zBf3hGuUP0w3QNP2i_g3Z5aPAAIKAwACjPqBUCEv2Y36Z5KEMwQ"}
    ],
    ("loot", "drop", "lendario", "item raro"): [
        {"type": "text", "content": "Ouvi falar em loot? Que a sorte dos deuses esteja com você!"},
        {"type": "text", "content": "Que venha um item lendário!  легендарный!"},
        {"type": "gif", "content": "CgACAgQAAxkBAAIBqWT5zB_WzXgwbz4u6AWaK8e_U1pPAAIBAwAC-pCgUAVZ1Z42LGBIMwQ"}
    ],
    ("ajuda", "dúvida", "como faz", "socorro"): [
        {"type": "text", "content": "Um aventureiro sábio é aquele que não tem medo de perguntar! Qual é a sua dúvida?"},
        {"type": "text", "content": "Ajuda a caminho! O que precisa, nobre colega?"},
        {"type": "sticker", "content": "ID_DO_STICKER_DE_AJUDA_AQUI"}
    ],
    ("farmar", "upar", "grind", "preciso de xp"): [
        {"type": "text", "content": "Ah, a eterna busca por poder! Que seus drops sejam fartos e seu XP, abundante!"},
        {"type": "text", "content": "Cada monstro derrotado é um passo a mais para a glória. Continue assim!"},
        {"type": "gif", "content": "ID_DO_GIF_DE_LEVEL_UP_AQUI"}
    ],
    ("morri", "derrotado", "fui de base", "perdi"): [
        {"type": "text", "content": "Até os maiores heróis caem. Levante-se, recupere suas forças e volte para a vingança!"},
        {"type": "text", "content": "A morte em Eldora é apenas um contratempo. O que aprendemos com essa derrota?"},
        {"type": "sticker", "content": "ID_DO_STICKER_DE_CONSOLO_AQUI"}
    ],
    ("clã", "guilda", "recrutando"): [
        {"type": "text", "content": "A união faz a força! Um clã forte é a base de um reino próspero."},
        {"type": "text", "content": "Busca por novos membros? Que encontrem os mais bravos e leais!"}
    ],
    ("@Eldora_py_bot", "gemini", "bot"): [
        {"type": "text", "content": "Chamou por mim? Estou aqui para ajudar!"},
        {"type": "text", "content": "Senti uma perturbação na Força... ah, não, era só você me chamando. Em que posso ser útil?"},
        {"type": "text", "content": "Presente! Pronto para a próxima ordem, capitão!"}
    ],
    ("obrigado", "vlw", "valeu"): [
        {"type": "text", "content": "De nada! Precisando, é só chamar."},
        {"type": "text", "content": "Tamo junto! 👍"},
        {"type": "text", "content": "É para isso que servem os parceiros de aventura!"}
    ],
    ("sorte", "lendário", "dropei um", "olha isso"): [
        {"type": "text", "content": "UAU! Que item incrível! A taverna inteira brinda em sua homenagem! 🍻"},
        {"type": "text", "content": "A sorte sorriu para você! Parabéns pela conquista, herói!"},
        {"type": "gif", "content": "ID_DO_GIF_DE_COMEMORACAO_AQUI"}
    ],
    ("party", "pt", "grupo", "masmorra", "dungeon"): [
        {"type": "text", "content": "Aventura em grupo? Excelente! Nenhum monstro é páreo para heróis unidos."},
        {"type": "text", "content": "Quem vai se juntar a esta nobre missão? A glória (e o loot) esperam por vocês!"},
    ],
    ("sou novo", "comecei agora", "iniciante"): [
        {"type": "text", "content": "Seja bem-vindo a Eldora, forasteiro! Que sua jornada seja longa e suas bolsas, pesadas de ouro."},
        {"type": "text", "content": "Um novo herói entre nós! Bem-vindo! A primeira rodada na taverna é por minha conta. 🍺"},
    ],
    ("piada", "conte algo"): [
        {"type": "text", "content": "O que um esqueleto disse para o outro no bar? 'Me vê uma cerveja e um esfregão, por favor!'"},
        {"type": "text", "content": "Por que o anão foi reprovado na escola? Porque ele tinha notas muito baixas!"}
    ],
    ("historia", "história", "lore"): [
        {"type": "text", "content": "Você sabia que a Grande Árvore de Edora só floresce quando a lua azul está no céu? Dizem que suas pétalas podem curar qualquer mal..."},
        {"type": "text", "content": "Contam as lendas que o dragão Vermithrax ainda dorme sob a Montanha de Cinzas, guardando o tesouro dos antigos reis..."},
        {"type": "text", "content": "Dizem que nos Picos Sussurrantes, o vento carrega as vozes dos gigantes de pedra que um dia governaram o mundo. Poucos que sobem até lá retornam com a sanidade intacta..."},
        {"type": "text", "content": "Você já ouviu falar da Cidade Afundada de Aeridor? Fica no fundo do Lago da Meia-Noite. Dizem que o tesouro da antiga rainha élfica ainda está lá, guardado por sereias de canto mortal."},
        {"type": "text", "content": "Os Golens de Ferro que guardam as ruínas anãs não são máquinas. São armaduras vazias possuídas pelos espíritos dos seus antigos donos, condenados a proteger seus salões para sempre."},
        {"type": "text", "content": "Muitos acham que a névoa da Floresta Sombria é apenas o tempo, mas os caçadores mais velhos não entram nela sem um amuleto. Eles juram que a névoa é o sopro de um deus antigo que dorme sob as raízes."},
        {"type": "text", "content": "Já reparou que os Cogumelos Gigantes da Floresta Sombria às vezes parecem sussurrar? Dizem que eles guardam as últimas palavras dos aventureiros que se perderam por lá."},
        {"type": "text", "content": "Existe um riacho escondido no coração da Floresta Sombria cujas águas brilham sob a lua. Dizem que beber delas pode curar qualquer veneno, mas a trilha para o encontrar só aparece para os puros de coração."},
        {"type": "text", "content": "Os sinos da catedral do Reino de Eldora não tocam com o vento. A lenda diz que eles soam sozinhos para anunciar o nascimento de um futuro herói ou a chegada de uma grande desgraça."},
    ],  







}