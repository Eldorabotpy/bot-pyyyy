window.dadosEldoraClasses = [];
        
async function carregarClasses() {
    const conteudo = document.getElementById('conteudo-wiki');
    conteudo.innerHTML = '<p style="text-align: center; color: #888;">Lendo os tomos antigos... 🔮</p>';
    try {
        const resposta = await fetch(`/wiki/classes?v=${Date.now()}`);
        window.dadosEldoraClasses = await resposta.json();
        
        const classes = window.dadosEldoraClasses;
        let html = `<div style="text-align: center; margin-bottom: 20px;"><h2 style="color: #f39c12; margin: 0;">🎭 Classes Base</h2></div>`;
        
        classes.forEach(cls => {
            const hp = cls.hp || 0; const atk = cls.ataque || 0; const def = cls.defesa || 0;
            const desc = cls.descricao || "Sem descrição."; const emoji = cls.emoji || "❓";
            let tagEvo = cls.total_evolucoes > 0 ? `<span style="background: #2c3e50; padding: 2px 6px; border-radius: 4px; font-size: 0.7em; color: #aaa;">${cls.total_evolucoes} Evoluções</span>` : '';
            
            let mediaTag = cls.video 
                ? `<video src="${cls.video}" autoplay loop muted playsinline style="width: 80px; height: 80px; border-radius: 8px; object-fit: cover; border: 2px solid #1e1e1e;"></video>`
                : `<img src="${cls.imagem}" onerror="this.src='https://placehold.co/80x80/2c3e50/f39c12?text=${emoji}'" style="width: 80px; height: 80px; border-radius: 8px; object-fit: cover; border: 2px solid #1e1e1e;">`;

            html += `<div onclick="abrirDetalhesClasse('${cls.id}')" style="background: #252525; margin-bottom: 15px; padding: 12px; border-radius: 8px; border-left: 4px solid #f39c12; display: flex; gap: 15px; align-items: center; cursor: pointer;">
                ${mediaTag}
                <div style="flex: 1;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 5px;">
                        <h3 style="margin: 0; color: #f39c12; font-size: 1.2em;">${emoji} ${cls.nome}</h3>${tagEvo}
                    </div>
                    <p style="margin: 0 0 10px 0; font-size: 0.85em; color: #ccc; line-height: 1.3;">${desc}</p>
                    <div style="display: flex; gap: 10px; font-size: 0.75em; background: #1a1a1a; padding: 6px; border-radius: 5px; justify-content: space-around; color: #bbb;">
                        <span>❤️ HP: ${hp}</span><span>⚔️ ATQ: ${atk}</span><span>🛡️ DEF: ${def}</span>
                    </div>
                </div>
            </div>`;
        });
        conteudo.innerHTML = html;
    } catch (erro) { conteudo.innerHTML = '<p style="color: red; text-align: center;">Erro ao ler escrituras.</p>'; }
}

function abrirDetalhesClasse(idClasse) {
    const cls = window.dadosEldoraClasses.find(c => c.id === idClasse);
    if (!cls) return;
    const conteudo = document.getElementById('conteudo-wiki');
    
    let htmlEvolucoes = '';
    if (cls.evolucoes && cls.evolucoes.length > 0) {
        htmlEvolucoes = '<h4 style="color: #f39c12; margin-top: 20px; border-bottom: 1px solid #333; padding-bottom: 5px;">Caminhos de Evolução</h4>';
        cls.evolucoes.forEach(evo => {
            // Adicionado cursor:pointer, hover, onclick e a setinha de "Ver Requisitos"
            htmlEvolucoes += `<div onclick="abrirDetalhesEvolucao('${cls.id}', '${evo.id}')" style="background: #1a1a1a; padding: 10px; border-radius: 5px; margin-bottom: 8px; border-left: 3px solid #3498db; cursor: pointer; transition: 0.2s; box-shadow: 0 2px 4px rgba(0,0,0,0.3);">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <strong style="color: #fff; font-size: 0.9em;">Tier ${evo.tier} - ${evo.emoji} ${evo.nome}</strong>
                    <span style="font-size: 0.8em; color: #3498db; font-weight: bold;">Ver Requisitos ➔</span>
                </div>
                <p style="margin: 5px 0 0 0; font-size: 0.8em; color: #aaa;">${evo.descricao}</p>
            </div>`;
        });
    }
    
    let mediaTagGrande = cls.video 
        ? `<video src="${cls.video}" autoplay loop muted playsinline style="width: 100%; border-radius: 8px; border: 2px solid #1a1a1a; object-fit: cover;"></video>`
        : `<img src="${cls.imagem}" onerror="this.src='https://placehold.co/300x400/2c3e50/f39c12?text=${cls.emoji}'" style="width: 100%; border-radius: 8px; border: 2px solid #1a1a1a; object-fit: cover;">`;

    conteudo.innerHTML = `<button onclick="carregarClasses()" style="background: none; border: none; color: #f39c12; font-size: 1em; cursor: pointer; margin-bottom: 15px; padding: 0; display: flex; align-items: center; gap: 5px;">⬅️ Voltar</button>
    <div style="display: flex; flex-wrap: wrap; gap: 20px; background: #252525; padding: 20px; border-radius: 8px; border-top: 4px solid #f39c12;">
        <div style="flex: 1; min-width: 150px;">
            ${mediaTagGrande}
        </div>
        <div style="flex: 2; min-width: 200px;">
            <h2 style="margin: 0 0 10px 0; color: #f39c12; font-size: 1.8em;">${cls.emoji} ${cls.nome}</h2>
            <p style="font-size: 0.95em; color: #ddd; line-height: 1.4; margin-bottom: 15px;">${cls.descricao}</p>
            <div style="display: flex; gap: 15px; background: #1a1a1a; padding: 12px; border-radius: 8px; justify-content: space-around; font-size: 0.85em; color: #ccc;">
                <span>❤️ <b>HP:</b> ${cls.hp}</span><span>⚔️ <b>ATQ:</b> ${cls.ataque}</span><span>🛡️ <b>DEF:</b> ${cls.defesa}</span>
            </div>
            ${htmlEvolucoes}
        </div>
    </div>`;
}

window.abrirDetalhesEvolucao = function(idClasseBase, idEvolucao) {
    // Procura a classe e depois a evolução específica na memória
    const cls = window.dadosEldoraClasses.find(c => c.id === idClasseBase);
    if (!cls) return;
    const evo = cls.evolucoes.find(e => e.id === idEvolucao);
    if (!evo) return;

    const conteudo = document.getElementById('conteudo-wiki');
    
    // Monta a lista de requisitos (Custos)
    let htmlRequisitos = '';
    if (evo.custos && evo.custos.length > 0) {
        htmlRequisitos = `<div style="display: grid; gap: 8px; margin-top: 10px;">`;
        evo.custos.forEach(req => {
            htmlRequisitos += `<div style="background: #1e1e1e; padding: 10px; border-radius: 6px; display: flex; justify-content: space-between; align-items: center; border-left: 3px solid #e74c3c;">
                <span style="color: #ddd;">${req.emoji} ${req.nome}</span>
                <span style="color: #e74c3c; font-weight: bold; background: #111; padding: 2px 8px; border-radius: 4px;">x${req.qtd}</span>
            </div>`;
        });
        htmlRequisitos += `</div>`;
    } else {
        htmlRequisitos = `<p style="color: #888; font-size: 0.9em;">Nenhum requisito especial ou custo desconhecido.</p>`;
    }

    // A imagem da evolução (com o fallback do emoji se a foto não existir)
    let mediaTagGrande = `<img src="${evo.imagem}" onerror="this.src='https://placehold.co/300x400/2c3e50/3498db?text=${evo.emoji}'" style="width: 100%; border-radius: 8px; border: 2px solid #1a1a1a; object-fit: cover; box-shadow: 0 4px 10px rgba(0,0,0,0.5);">`;

    // Desenha a tela toda!
    conteudo.innerHTML = `<button onclick="abrirDetalhesClasse('${idClasseBase}')" style="background: none; border: none; color: #3498db; font-size: 1em; cursor: pointer; margin-bottom: 15px; padding: 0; display: flex; align-items: center; gap: 5px;">⬅️ Voltar para ${cls.nome}</button>
    
    <div style="display: flex; flex-wrap: wrap; gap: 20px; background: #252525; padding: 20px; border-radius: 8px; border-top: 4px solid #3498db;">
        <div style="flex: 1; min-width: 150px;">
            ${mediaTagGrande}
        </div>
        <div style="flex: 2; min-width: 200px;">
            <h2 style="margin: 0 0 5px 0; color: #3498db; font-size: 1.8em;">${evo.emoji} ${evo.nome}</h2>
            <span style="background: #111; padding: 4px 10px; border-radius: 4px; font-size: 0.8em; color: #ccc;">Evolução Tier ${evo.tier}</span>
            
            <p style="font-size: 0.95em; color: #ddd; line-height: 1.4; margin: 15px 0;">${evo.descricao}</p>
            
            <h4 style="color: #aaa; border-bottom: 1px solid #333; padding-bottom: 5px; margin-bottom: 10px;">Atributos Base (Multiplicadores)</h4>
            <div style="display: flex; gap: 15px; background: #1a1a1a; padding: 12px; border-radius: 8px; justify-content: space-around; font-size: 0.85em; color: #ccc; margin-bottom: 20px;">
                <span>❤️ <b>HP:</b> ${evo.hp}</span><span>⚔️ <b>ATQ:</b> ${evo.ataque}</span><span>🛡️ <b>DEF:</b> ${evo.defesa}</span>
            </div>
            
            <h4 style="color: #aaa; border-bottom: 1px solid #333; padding-bottom: 5px; margin-bottom: 10px;">Custo de Ascensão (Total)</h4>
            ${htmlRequisitos}
        </div>
    </div>`;
}

async function carregarRegioes() {
    const conteudo = document.getElementById('conteudo-wiki');
    conteudo.innerHTML = '<p style="text-align: center; color: #888;">Desenhando o mapa... 🗺️</p>';
    try {
        const resposta = await fetch(`/wiki/regioes?v=${Date.now()}`);
        const regioes = await resposta.json();
        
        let html = `<div style="text-align: center; margin-bottom: 20px;"><h2 style="color: #3498db;">🗺️ Mapas de Eldora</h2></div>`;
        
        regioes.forEach(reg => {
            html += `<div style="background: #252525; margin-bottom: 15px; padding: 15px; border-radius: 8px; border-left: 4px solid #3498db; display: flex; gap: 15px; align-items: center;">
                <img src="${reg.imagem}" onerror="this.src='https://placehold.co/80x80/2c3e50/3498db?text=${reg.emoji}'" style="width: 80px; height: 80px; border-radius: 8px; object-fit: cover;">
                <div style="flex: 1;">
                    <h3 style="margin: 0 0 5px 0; color: #3498db; font-size: 1.1em;">${reg.emoji} ${reg.nome}</h3>
                    <p style="margin: 0 0 8px 0; font-size: 0.8em; color: #aaa;">${reg.descricao}</p>
                    <span style="background: #1a1a1a; padding: 4px 8px; border-radius: 4px; font-size: 0.75em; color: #ccc;">Recomendado: Lvl ${reg.level_min}+</span>
                </div>
            </div>`;
        });
        conteudo.innerHTML = html;
    } catch (erro) { conteudo.innerHTML = '<p style="color: red; text-align: center;">Erro ao carregar o mapa.</p>'; }
}

window.dadosEldoraMonstros = [];

const coresRegiao = {
    'pradaria_inicial': '#2ecc71', 'floresta_sombria': '#27ae60', 'pedreira_granito': '#95a5a6',
    'campos_linho': '#f1c40f', 'pico_grifo': '#3498db', 'mina_ferro': '#d35400',
    'forja_abandonada': '#e74c3c', 'pantano_maldito': '#1abc9c', 'picos_gelados': '#82ccdd',
    'deserto_ancestral': '#f39c12', '_evolution_trials': '#9b59b6', 'defesa_reino': '#e056fd'
};

async function carregarMonstros() {
    const conteudo = document.getElementById('conteudo-wiki');
    conteudo.innerHTML = '<p style="text-align: center; color: #888;">Lendo os mapas de caçada... 🗺️</p>';
    try {
        if (window.dadosEldoraMonstros.length === 0) {
            const resposta = await fetch(`/wiki/monstros?v=${Date.now()}`);
            window.dadosEldoraMonstros = await resposta.json();
        }
        
        const regioesAgrupadas = {};
        window.dadosEldoraMonstros.forEach(mob => {
            if (!regioesAgrupadas[mob.regiao_id]) {
                regioesAgrupadas[mob.regiao_id] = { 
                    nome: mob.regiao_nome, 
                    is_evento: mob.is_evento, 
                    qnts: 0,
                    nivel_regiao: mob.nivel_regiao || 999 
                };
            }
            regioesAgrupadas[mob.regiao_id].qnts++;
        });

        const regioesOrdenadas = Object.entries(regioesAgrupadas).sort((a, b) => a[1].nivel_regiao - b[1].nivel_regiao);

        let htmlCacada = `<div style="text-align: center; margin: 25px 0 15px 0;"><h3 style="color: #2ecc71; margin: 0;">🌲 Habitats de Caçada</h3></div><div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px;">`;
        let htmlEvento = `<div style="text-align: center; margin: 25px 0 15px 0;"><h3 style="color: #9b59b6; margin: 0;">⚔️ Áreas de Evento</h3></div><div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px;">`;
        let temCacada = false; let temEvento = false;

        for (const [id, reg] of regioesOrdenadas) {
            const cor = coresRegiao[id] || '#e74c3c';
            const btn = `<button onclick="abrirRegiaoMonstros('${id}')" style="padding: 15px; background: #252525; color: white; border: 1px solid ${cor}; border-radius: 8px; cursor: pointer; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 5px; transition: 0.2s;">
                <span style="font-weight: bold; color: ${cor}; font-size: 0.9em; text-align: center;">${reg.nome}</span>
                <span style="font-size: 0.7em; color: #888; background: #111; padding: 2px 8px; border-radius: 4px;">${reg.qnts} Monstros</span>
            </button>`;
            if (reg.is_evento) { htmlEvento += btn; temEvento = true; } 
            else { htmlCacada += btn; temCacada = true; }
        }
        
        htmlCacada += `</div>`; htmlEvento += `</div>`;
        let htmlFinal = `<div style="text-align: center; margin-bottom: 10px;"><h2 style="color: #e74c3c; margin: 0;">🗺️ Onde você quer caçar?</h2></div>`;
        if (temCacada) htmlFinal += htmlCacada;
        if (temEvento) htmlFinal += htmlEvento;

        conteudo.innerHTML = htmlFinal;
    } catch (erro) { conteudo.innerHTML = '<p style="color: red; text-align: center;">Erro ao carregar os habitats.</p>'; }
}

function abrirRegiaoMonstros(regiao_id) {
    const mobs = window.dadosEldoraMonstros.filter(m => m.regiao_id === regiao_id);
    if (mobs.length === 0) return;
    
    const cor = coresRegiao[regiao_id] || '#e74c3c';
    const conteudo = document.getElementById('conteudo-wiki');
    
    let html = `<button onclick="carregarMonstros()" style="background: none; border: none; color: ${cor}; font-size: 1em; cursor: pointer; margin-bottom: 15px; padding: 0; display: flex; align-items: center; gap: 5px;">⬅️ Voltar para Mapas</button>`;
    html += `<div style="text-align: center; margin-bottom: 20px;"><h2 style="color: ${cor}; margin: 0; border-bottom: 2px solid ${cor}; padding-bottom: 5px;">📍 ${mobs[0].regiao_nome}</h2></div>`;

    mobs.forEach(mob => {
        html += `<div onclick="abrirDetalhesMonstro('${mob.id}')" style="background: #252525; margin-bottom: 15px; padding: 12px; border-radius: 8px; border-left: 4px solid ${cor}; display: flex; gap: 15px; align-items: center; cursor: pointer;">
            <img src="${mob.imagem}" onerror="this.src='https://placehold.co/70x70/2c3e50/${cor.replace('#','')}?text=?'" style="width: 70px; height: 70px; border-radius: 50%; object-fit: cover; border: 2px solid ${cor};">
            <div style="flex: 1;">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <h3 style="margin: 0 0 5px 0; color: ${cor}; font-size: 1.1em;">${mob.nome}</h3>
                    <span style="font-size: 0.8em; color: #aaa;">Lvl ${mob.level}</span>
                </div>
                <p style="margin: 0; font-size: 0.75em; color: #888;">Clique para ver os drops e status ➔</p>
            </div>
        </div>`;
    });
    conteudo.innerHTML = html;
}

function abrirDetalhesMonstro(mob_id) {
    const mob = window.dadosEldoraMonstros.find(m => m.id === mob_id);
    if (!mob) return;
    
    const cor = coresRegiao[mob.regiao_id] || '#e74c3c';
    const conteudo = document.getElementById('conteudo-wiki');
    
    let htmlDrops = '<p style="color: #888; font-size: 0.85em; text-align: center;">Este monstro não dropa itens.</p>';
    if (mob.loot && mob.loot.length > 0) {
        htmlDrops = `<div style="display: grid; gap: 8px;">`;
        mob.loot.forEach(item => {
            let corDrop = item.chance <= 10 ? '#e74c3c' : (item.chance <= 40 ? '#f39c12' : '#2ecc71');
            htmlDrops += `<div style="background: #1e1e1e; padding: 10px 12px; border-radius: 6px; display: flex; justify-content: space-between; align-items: center; border-left: 3px solid ${corDrop}; font-size: 0.85em;">
                <span style="color: #ddd;">${item.nome}</span>
                <span style="color: ${corDrop}; font-weight: bold; background: #111; padding: 2px 6px; border-radius: 4px;">${item.chance}% chance</span>
            </div>`;
        });
        htmlDrops += `</div>`;
    }

    let html = `<button onclick="abrirRegiaoMonstros('${mob.regiao_id}')" style="background: none; border: none; color: ${cor}; font-size: 1em; cursor: pointer; margin-bottom: 15px; padding: 0; display: flex; align-items: center; gap: 5px;">⬅️ Voltar para ${mob.regiao_nome}</button>
    
    <div style="background: #252525; padding: 20px; border-radius: 8px; border-top: 4px solid ${cor};">
        <div style="text-align: center; margin-bottom: 20px;">
            <img src="${mob.imagem}" onerror="this.src='https://placehold.co/150x150/2c3e50/${cor.replace('#','')}?text=?'" style="width: 120px; height: 120px; border-radius: 50%; object-fit: cover; border: 3px solid ${cor}; box-shadow: 0 4px 10px rgba(0,0,0,0.5);">
            <h2 style="margin: 10px 0 5px 0; color: ${cor}; font-size: 1.6em;">${mob.nome}</h2>
            <span style="background: #111; padding: 4px 10px; border-radius: 4px; font-size: 0.8em; color: #ccc;">Nível ${mob.level}</span>
        </div>
        
        <h4 style="color: #aaa; border-bottom: 1px solid #333; padding-bottom: 5px; margin-bottom: 10px;">Atributos de Combate</h4>
        <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 10px; text-align: center; margin-bottom: 20px;">
            <div style="background: #1a1a1a; padding: 10px; border-radius: 8px; border: 1px solid #c0392b;">
                <span style="color: #e74c3c; font-size: 0.7em; display: block; font-weight: bold;">HP MAX</span>
                <strong style="color: #fff; font-size: 1.1em;">${mob.hp}</strong>
            </div>
            <div style="background: #1a1a1a; padding: 10px; border-radius: 8px; border: 1px solid #d35400;">
                <span style="color: #e67e22; font-size: 0.7em; display: block; font-weight: bold;">ATAQUE</span>
                <strong style="color: #fff; font-size: 1.1em;">${mob.ataque}</strong>
            </div>
            <div style="background: #1a1a1a; padding: 10px; border-radius: 8px; border: 1px solid #2980b9;">
                <span style="color: #3498db; font-size: 0.7em; display: block; font-weight: bold;">DEFESA</span>
                <strong style="color: #fff; font-size: 1.1em;">${mob.defesa}</strong>
            </div>
        </div>
        
        <h4 style="color: #aaa; border-bottom: 1px solid #333; padding-bottom: 5px; margin-bottom: 10px;">Recompensas Garantidas</h4>
        <div style="display: flex; gap: 15px; margin-bottom: 25px;">
            <div style="flex: 1; background: #1a1a1a; padding: 10px; border-radius: 8px; display: flex; align-items: center; justify-content: space-between; border-left: 3px solid #8e44ad;">
                <span style="color: #ccc; font-size: 0.8em;">Experiência</span>
                <strong style="color: #9b59b6;">${mob.xp} XP</strong>
            </div>
            <div style="flex: 1; background: #1a1a1a; padding: 10px; border-radius: 8px; display: flex; align-items: center; justify-content: space-between; border-left: 3px solid #f1c40f;">
                <span style="color: #ccc; font-size: 0.8em;">Ouro</span>
                <strong style="color: #f1c40f;">${mob.gold} 💰</strong>
            </div>
        </div>

        <h4 style="color: #aaa; border-bottom: 1px solid #333; padding-bottom: 5px; margin-bottom: 10px;">🎁 Itens de Drop (Loot)</h4>
        ${htmlDrops}
        
    </div>`;
    conteudo.innerHTML = html;
}

// Variáveis globais para guardar o estado das abas
window.dadosEldoraItens = [];
window.abaAtualItens = 'equipamentos';
window.subAbaAtualItens = 'guerreiro'; // Padrão ao abrir

async function carregarItens() {
    const conteudo = document.getElementById('conteudo-wiki');
    conteudo.innerHTML = '<p style="text-align: center; color: #888;">Abrindo os baús e armarias... ⚔️</p>';
    try {
        // Se a lista estiver vazia, baixa do Python. Se já baixou, reaproveita!
        if (window.dadosEldoraItens.length === 0) {
            const resposta = await fetch(`/wiki/itens?v=${Date.now()}`);
            window.dadosEldoraItens = await resposta.json();
        }
        // Desenha a tela
        renderizarMenuItens();
    } catch (erro) { 
        conteudo.innerHTML = '<p style="color: red; text-align: center;">Erro ao carregar itens.</p>'; 
    }
}

// Nova função que desenha os botões e filtra os itens!
window.renderizarMenuItens = function(aba = null, sub = null) {
    if (aba) window.abaAtualItens = aba;
    if (sub) window.subAbaAtualItens = sub;

    const conteudo = document.getElementById('conteudo-wiki');
    
    // 1. AS ABAS PRINCIPAIS
    const abasPrin = [
        { id: 'equipamentos', nome: '⚔️ Equipamentos' },
        { id: 'materiais', nome: '🦇 Drops (Caçada)' },
        { id: 'coleta', nome: '🪓 Coleta' },
        { id: 'refino', nome: '🔥 Refino & Runas' },
        { id: 'consumiveis', nome: '🧪 Poções' }
    ];

    let html = `<div style="text-align: center; margin-bottom: 15px;"><h2 style="color: #9b59b6; margin:0;">📚 Arsenal e Itens</h2></div>`;
    
    html += `<div style="display: flex; flex-wrap: wrap; gap: 5px; margin-bottom: 15px; justify-content: center;">`;
    abasPrin.forEach(a => {
        const corBg = window.abaAtualItens === a.id ? '#9b59b6' : '#1e1e1e';
        html += `<button onclick="renderizarMenuItens('${a.id}', null)" style="padding: 8px 12px; background: ${corBg}; color: white; border: 1px solid #333; border-radius: 6px; cursor: pointer; font-weight: bold; font-size: 0.8em; transition: 0.2s;">${a.nome}</button>`;
    });
    html += `</div>`;

    // 2. AS SUB-ABAS (SÓ APARECEM SE "EQUIPAMENTOS" ESTIVER SELECIONADO)
    if (window.abaAtualItens === 'equipamentos') {
        const classes = ['guerreiro', 'mago', 'cacador', 'assassino', 'monge', 'berserker', 'samurai', 'bardo', 'curandeiro', 'geral'];
        
        // Garante que uma sub-aba padrão esteja selecionada
        if (!window.subAbaAtualItens || !classes.includes(window.subAbaAtualItens)) window.subAbaAtualItens = 'guerreiro';
        
        html += `<div style="display: flex; flex-wrap: wrap; gap: 5px; margin-bottom: 20px; justify-content: center; background: #111; padding: 10px; border-radius: 8px; border: 1px solid #333;">`;
        classes.forEach(c => {
            const corBg = window.subAbaAtualItens === c ? '#f39c12' : '#252525';
            const corTxt = window.subAbaAtualItens === c ? '#000' : '#aaa';
            html += `<button onclick="renderizarMenuItens('equipamentos', '${c}')" style="padding: 5px 10px; background: ${corBg}; color: ${corTxt}; border: none; border-radius: 4px; cursor: pointer; font-size: 0.75em; text-transform: capitalize; font-weight: bold;">${c}</button>`;
        });
        html += `</div>`;
    } else {
        // Se mudou de aba principal, reseta o filtro secundário para mostrar tudo da aba
        window.subAbaAtualItens = null;
    }

    // 3. FILTRANDO A LISTA DE ITENS
    const itensFiltrados = window.dadosEldoraItens.filter(i => {
        if (i.wiki_tab !== window.abaAtualItens) return false;
        if (window.abaAtualItens === 'equipamentos' && i.wiki_sub !== window.subAbaAtualItens) return false;
        return true;
    });

    // 4. DESENHANDO OS ITENS FILTRADOS
    html += `<div style="display: grid; gap: 10px;">`;
    if (itensFiltrados.length === 0) {
        html += `<p style="text-align: center; color: #666; padding: 20px; background: #1a1a1a; border-radius: 8px;">Nenhum item encontrado nesta categoria.</p>`;
    } else {
        itensFiltrados.forEach(item => {
            html += `<div style="background: #252525; padding: 12px; border-radius: 8px; border-left: 4px solid #9b59b6; display: flex; gap: 12px; align-items: center; box-shadow: 0 4px 6px rgba(0,0,0,0.3);">
                <img src="${item.imagem}" onerror="this.src='https://placehold.co/60x60/2c3e50/9b59b6?text=${item.emoji}'" style="width: 60px; height: 60px; border-radius: 8px; object-fit: contain; background: #111; border: 1px solid #333;">
                <div style="flex: 1;">
                    <div style="display: flex; justify-content: space-between;">
                        <h3 style="margin: 0 0 3px 0; color: #9b59b6; font-size: 1em;">${item.nome}</h3>
                        <span style="font-size: 0.7em; color: #f1c40f;">💰 ${item.preco}</span>
                    </div>
                    <p style="margin: 0 0 5px 0; font-size: 0.75em; color: #aaa;">${item.descricao}</p>
                    <span style="font-size: 0.65em; background: #1a1a1a; padding: 2px 6px; border-radius: 3px; color: #ccc; text-transform: uppercase;">${item.raridade}</span>
                </div>
            </div>`;
        });
    }
    html += `</div>`;
    
    conteudo.innerHTML = html;
}