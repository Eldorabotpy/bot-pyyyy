// ==========================================
// CONFIGURAÇÕES GERAIS E DADOS (perfil.js)
// ==========================================
// ==========================================
// BÚSSOLA DE PASTAS DE ITENS
// ==========================================
window.obterPastaItem = function(dado) {
    // Pega o tipo seja lá como ele vier (se mandarem o objeto inteiro ou só o texto)
    let tipo = typeof dado === 'object' ? (dado.tipo || dado.type || "") : (dado || "");
    const t = tipo.toLowerCase();
    
    // 1. Ferramentas de Profissão
    const tiposFerramenta = ['tool', 'ferramenta', 'lenhador', 'minerador', 'colhedor', 'esfolador', 'ferreiro', 'armeiro', 'alfaiate', 'joalheiro', 'curtidor'];
    if (tiposFerramenta.includes(t)) return 'ferramentas';

    // 2. Equipamentos (Armas e Armaduras)
    const tiposEquipamento = ['weapon', 'armor', 'helmet', 'boots', 'bota', 'ring', 'necklace', 'earring', 'equipamento', 'arma', 'armadura', 'elmo', 'anel', 'colar', 'brinco'];
    if (tiposEquipamento.includes(t)) return 'equipamentos';
    
    // 3. Consumíveis e itens especiais
    const tiposUsaveis = ['potion', 'pocao', 'consumable', 'scroll', 'pergaminho', 'chest', 'box', 'consumivel', 'reagent', 'especial', 'event_ticket'];
    if (tiposUsaveis.includes(t)) return 'consumiveis';
    
    // Fallback absoluto
    return 'materiais'; 
};

window.getCaminhosImagemItemEldora = function(item) {
    const linkBaseNuvem = "https://raw.githubusercontent.com/Eldorabotpy/static-img/main/assets/";
    const pasta = window.obterPastaItem ? window.obterPastaItem(item) : 'materiais';

    const idReal = (
        item?.base_id ||
        item?.item_id ||
        item?.uid ||
        item?.id ||
        ""
    );

    if (!idReal) {
        return ["/static/assets/box.png"];
    }

    const caminhos = [];

    // Equipamentos da forja no GitHub usam prefixo work_
    if (pasta === "equipamentos") {
        caminhos.push(`${linkBaseNuvem}itens/${pasta}/work_${idReal}.png`);
        caminhos.push(`${linkBaseNuvem}itens/${pasta}/${idReal}.png`);
    } else {
        caminhos.push(`${linkBaseNuvem}itens/${pasta}/${idReal}.png`);
        caminhos.push(`${linkBaseNuvem}itens/${pasta}/work_${idReal}.png`);
    }

    // Fallbacks extras caso o tipo esteja errado
    caminhos.push(`${linkBaseNuvem}itens/equipamentos/work_${idReal}.png`);
    caminhos.push(`${linkBaseNuvem}itens/equipamentos/${idReal}.png`);
    caminhos.push(`${linkBaseNuvem}itens/ferramentas/${idReal}.png`);
    caminhos.push(`${linkBaseNuvem}itens/materiais/${idReal}.png`);
    caminhos.push("/static/assets/box.png");

    return [...new Set(caminhos)];
};

window.aplicarImagemItemEldora = function(imgEl, item) {
    if (!imgEl) return;

    const caminhos = window.getCaminhosImagemItemEldora(item);
    let index = 0;

    imgEl.onerror = function() {
        index++;

        if (index < caminhos.length) {
            this.src = caminhos[index];
        } else {
            this.onerror = null;
            this.src = "/static/assets/box.png";
        }
    };

    imgEl.src = caminhos[0];
};

const CLASSES_INFO = {
    'aprendiz': { nome: 'Aventureiro', emoji: '🎒', base: 'aprendiz' },
    'aventureiro': { nome: 'Aventureiro', emoji: '🎒', base: 'aprendiz' },
    'guerreiro': { nome: 'Guerreiro', emoji: '⚔️', base: 'guerreiro' },
    'cavaleiro': { nome: 'Cavaleiro', emoji: '🛡️', base: 'guerreiro' },
    'gladiador': { nome: 'Gladiador', emoji: '🔱', base: 'guerreiro' },
    'templario': { nome: 'Templário', emoji: '⚜️', base: 'guerreiro' },
    'guardiao_divino': { nome: 'Guardião Divino', emoji: '🛡️', base: 'guerreiro' },
    'berserker': { nome: 'Berserker', emoji: '🪓', base: 'berserker' },
    'barbaro': { nome: 'Bárbaro', emoji: '🗿', base: 'berserker' },
    'juggernaut': { nome: 'Juggernaut', emoji: '🐗', base: 'berserker' },
    'ira_primordial': { nome: 'Ira Primordial', emoji: '👹', base: 'berserker' },
    'cacador': { nome: 'Caçador', emoji: '🏹', base: 'cacador' },
    'patrulheiro': { nome: 'Patrulheiro', emoji: '🐾', base: 'cacador' },
    'franco_atirador': { nome: 'Franco-Atirador', emoji: '🎯', base: 'cacador' },
    'olho_de_aguia': { nome: 'Olho de Águia', emoji: '🦅', base: 'cacador' },
    'monge': { nome: 'Monge', emoji: '🧘', base: 'monge' },
    'guardiao_do_templo': { nome: 'Guardião do Templo', emoji: '🏯', base: 'monge' },
    'punho_elemental': { nome: 'Punho Elemental', emoji: '🔥', base: 'monge' },
    'ascendente': { nome: 'Ascendente', emoji: '🕊️', base: 'monge' },
    'mago': { nome: 'Mago', emoji: '🧙', base: 'mago' },
    'feiticeiro': { nome: 'Feiticeiro', emoji: '🔮', base: 'mago' },
    'elementalista': { nome: 'Elementalista', emoji: '☄️', base: 'mago' },
    'arquimago': { nome: 'Arquimago', emoji: '🌌', base: 'mago' },
    'bardo': { nome: 'Bardo', emoji: '🎶', base: 'bardo' },
    'menestrel': { nome: 'Menestrel', emoji: '📜', base: 'bardo' },
    'encantador': { nome: 'Encantador', emoji: '✨', base: 'bardo' },
    'maestro': { nome: 'Maestro', emoji: '🎼', base: 'bardo' },
    'assassino': { nome: 'Assassino', emoji: '🔪', base: 'assassino' },
    'ladrao_de_sombras': { nome: 'Ladrão de Sombras', emoji: '💨', base: 'assassino' },
    'ninja': { nome: 'Ninja', emoji: '🥷', base: 'assassino' },
    'mestre_das_laminas': { nome: 'Mestre das Lâminas', emoji: '⚔️', base: 'assassino' },
    'samurai': { nome: 'Samurai', emoji: '🥷', base: 'samurai' },
    'kensei': { nome: 'Kensei', emoji: '🗡️', base: 'samurai' },
    'ronin': { nome: 'Ronin', emoji: '🧧', base: 'samurai' },
    'shogun': { nome: 'Shogun', emoji: '🏯', base: 'samurai' },
    'curandeiro': { nome: 'Curandeiro', emoji: '🩹', base: 'curandeiro' },
    'clerigo': { nome: 'Clérigo', emoji: '✝️', base: 'curandeiro' },
    'druida': { nome: 'Druida', emoji: '🌳', base: 'curandeiro' },
    'sacerdote': { nome: 'Sacerdote', emoji: '⛪', base: 'curandeiro' }
};

function normalizarProfissaoPerfil(valor) {
    return String(valor || "")
        .trim()
        .toLowerCase()
        .normalize("NFD")
        .replace(/[\u0300-\u036f]/g, "");
}

function getNivelProfissaoPerfil(profKey) {
    const p = window.perfilDadosGlobais || {};
    const key = normalizarProfissaoPerfil(profKey);

    const learned = p.learned_professions || {};
    const profData = learned[key];

    if (profData && typeof profData === "object") {
        return Math.max(1, parseInt(profData.level || 1) || 1);
    }

    const legacy = p.profession || {};
    const legacyKey = normalizarProfissaoPerfil(legacy.key || legacy.type);

    if (legacyKey === key) {
        return Math.max(1, parseInt(legacy.level || 1) || 1);
    }

    return 1;
}

function getTierFerramentaPerfil(itemData) {
    if (!itemData) return 1;

    const direto = parseInt(itemData.tool_tier || itemData.tier || 0);
    if (direto > 0) return direto;

    const baseId = String(itemData.base_id || itemData.id || "").toLowerCase();

    const porSufixo = baseId.match(/_t([1-5])\b/);
    if (porSufixo) return parseInt(porSufixo[1]) || 1;

    if (baseId.includes("t5")) return 5;
    if (baseId.includes("t4")) return 4;
    if (baseId.includes("t3")) return 3;
    if (baseId.includes("t2")) return 2;

    return 1;
}

function getNivelRefinoPerfilItem(itemData) {
    return parseInt(
        itemData?.upgrade_level ??
        itemData?.refino ??
        itemData?.upgrade ??
        itemData?.nivel_refino ??
        0
    ) || 0;
}

function isFerramentaPerfil(itemData) {
    if (!itemData) return false;

    const tipo = normalizarProfissaoPerfil(itemData.tipo || itemData.type);
    const slot = normalizarProfissaoPerfil(itemData.slot);
    const toolType = normalizarProfissaoPerfil(itemData.tool_type || itemData.slot_profissao);

    return (
        tipo === "tool" ||
        tipo === "ferramenta" ||
        slot === "tool" ||
        slot.startsWith("tool_") ||
        !!toolType
    );
}

function gerarHtmlBonusTempoFerramentaPerfil(itemData) {
    if (!isFerramentaPerfil(itemData)) return "";

    const profKey = normalizarProfissaoPerfil(
        itemData.tool_type ||
        itemData.slot_profissao ||
        String(itemData.slot || "").replace("tool_", "") ||
        "ferreiro"
    );

    const profNivel = getNivelProfissaoPerfil(profKey);

    const tier = getTierFerramentaPerfil(itemData);
    const upgrade = getNivelRefinoPerfilItem(itemData);

    // Igual ao backend:
    // T1 0%, T2 5%, T3 10%, T4 15%, T5 20%
    const bonusTier = Math.min(20, Math.max(0, tier - 1) * 5);

    // +1% por melhoria, máximo 10%
    const bonusUpgrade = Math.min(10, upgrade);

    // Profissão: 0.5% por nível, máximo 25%
    const bonusProf = Math.min(25, profNivel * 0.5);

    const bonusFerramenta = bonusTier + bonusUpgrade;

    // Total final máximo: 50%
    const totalAplicado = Math.min(50, bonusProf + bonusFerramenta);

    const nomeProf = profKey
        ? profKey.charAt(0).toUpperCase() + profKey.slice(1)
        : "Profissão";

    const corTotal =
        totalAplicado >= 40 ? "#22c55e" :
        totalAplicado >= 25 ? "#3b82f6" :
        totalAplicado >= 10 ? "#facc15" :
        "#94a3b8";

    return `
        <div style="
            width:100%;
            margin-top:8px;
            padding:10px;
            border-radius:10px;
            border:1px solid rgba(250,204,21,.35);
            background:linear-gradient(180deg, rgba(120,53,15,.35), rgba(15,23,42,.75));
            text-align:left;
            box-shadow: inset 0 0 14px rgba(0,0,0,.35);
        ">
            <div style="
                font-family:'Cinzel',serif;
                font-weight:900;
                color:#facc15;
                font-size:.82em;
                margin-bottom:7px;
                text-align:center;
                letter-spacing:.4px;
            ">
                ⏱️ BÔNUS DE TEMPO
            </div>

            <div style="display:grid; gap:5px; font-size:.78em; color:#cbd5e1;">
                <div style="display:flex; justify-content:space-between; gap:8px;">
                    <span>Profissão</span>
                    <b style="color:#fff;">${nomeProf} Nv. ${profNivel}</b>
                </div>

                <div style="display:flex; justify-content:space-between; gap:8px;">
                    <span>Redução da profissão</span>
                    <b style="color:#93c5fd;">-${bonusProf.toFixed(1)}%</b>
                </div>

                <div style="display:flex; justify-content:space-between; gap:8px;">
                    <span>Tier da ferramenta</span>
                    <b style="color:#fff;">T${tier} / -${bonusTier.toFixed(1)}%</b>
                </div>

                <div style="display:flex; justify-content:space-between; gap:8px;">
                    <span>Melhoria da ferramenta</span>
                    <b style="color:#fff;">+${upgrade} / -${bonusUpgrade.toFixed(1)}%</b>
                </div>

                <div style="
                    margin-top:6px;
                    padding-top:7px;
                    border-top:1px solid rgba(255,255,255,.1);
                    display:flex;
                    justify-content:space-between;
                    gap:8px;
                    font-size:1.05em;
                ">
                    <span style="color:#f8fafc; font-weight:800;">Total aplicado</span>
                    <b style="color:${corTotal};">-${totalAplicado.toFixed(1)}%</b>
                </div>
            </div>
        </div>
    `;
}

// ==========================================
// FUNÇÃO PRINCIPAL DE CARREGAMENTO DO PERFIL
// ==========================================
async function carregarMeuPerfil() {
    const charId = localStorage.getItem("jogadorEldoraID");
    const conteudo = document.getElementById('perfil-dados');

    if (!charId) {
        document.getElementById('perfil-msg-carregando').innerHTML = "<span style='color: #e74c3c;'>Nenhum herói selecionado.</span>";
        return;
    }

    try {
        // 1. 🔥 ROTA CORRIGIDA (Puxa todos os dados do inventário e status)
        const resposta = await fetch(`/perfil/${charId}?t=${new Date().getTime()}`, { cache: 'no-store' });
        const p = await resposta.json();
        
        if (p.erro) { 
            document.getElementById('perfil-msg-carregando').innerText = "⚠️ " + p.erro; 
            return; 
        }

        // 2. BLINDAGEM ANTI-CRASH (Evita erros se faltar algum dado)
        p.status = p.status || {};
        p.equipamentos = p.equipamentos || [];
        p.inventario = p.inventario || []; 
        p.pontos_livres = p.pontos_livres || 0;
        p.hp_atual = p.hp_atual || 0; p.hp_max = p.hp_max || 100;
        p.mp_atual = p.mp_atual || 0; p.mp_max = p.mp_max || 50;
        p.gold = p.gold || 0; p.gems = p.gems || 0;
        p.xp = p.xp || 0; p.xp_max = p.xp_max || 1;
        p.level = p.level || 1; p.energy = p.energy || 20;

        if (!Array.isArray(p.inventario)) {
            p.inventario = Object.entries(p.inventario).map(([id, dados]) => {
                let item = typeof dados === 'object' ? { id, ...dados } : { id, base_id: id, quantity: dados };

                // Puxa a quantidade certa
                item.qtd = item.quantity || item.quantidade || (typeof dados === 'number' ? dados : 0);

                // 👇 A MÁGICA DA TRADUÇÃO DE TIPOS 👇
                item.tipo = (item.type || item.tipo || item.categoria || "").toLowerCase();

                // Se o backend não mandou o tipo, a gente descobre pelo nome do ID!
                if (!item.tipo || item.tipo === "") {
                    const tempId = (item.base_id || item.id || "").toLowerCase();
                    
                    if (tempId.includes('pocao') || tempId.includes('potion')) item.tipo = 'potion';
                    else if (tempId.includes('pergaminho') || tempId.includes('scroll')) item.tipo = 'scroll';
                    else if (tempId.includes('espada') || tempId.includes('arco') || tempId.includes('cajado')) item.tipo = 'weapon';
                    else if (tempId.includes('armadura') || tempId.includes('elmo') || tempId.includes('bota')) item.tipo = 'armor';
                    else if (tempId.includes('picareta') || tempId.includes('machado') || tempId.includes('foice') || tempId.includes('martelo')) item.tipo = 'tool';
                    else item.tipo = 'material';
                }

                return item;
            });
        }

        window.perfilDadosGlobais = p; 
        
        const classeKey = (p.classe || "aprendiz").toLowerCase();
        const infoClasse = CLASSES_INFO[classeKey] || CLASSES_INFO['aprendiz'];
        let percentXP = Math.min((p.xp / p.xp_max) * 100, 100);

        // ==========================================
        // 🌟 NOVO: MULTI-PROFISSÕES (LISTA COM SCROLL E BÔNUS)
        // ==========================================
        let htmlProfissao = '';
        
        // Junta a profissão atual com as aprendidas (caso o backend não tenha sincronizado 100%)
        let profsAprendidas = p.learned_professions || {};
        if (p.profession && (p.profession.key || p.profession.type)) {
            let pKey = p.profession.key || p.profession.type;
            if (!profsAprendidas[pKey]) profsAprendidas[pKey] = p.profession;
        }

        const listaProfs = Object.values(profsAprendidas);

        if (listaProfs.length > 0) { 
            // Cria a caixa com scroll para caber várias profissões
            htmlProfissao = `<div style="max-height: 250px; overflow-y: auto; padding-right: 5px; margin-bottom: 20px; display: flex; flex-direction: column; gap: 12px; scrollbar-width: thin; scrollbar-color: #ca8a04 #0f172a;">`;
            
            // Ordena pelo maior nível
            listaProfs.sort((a, b) => (b.level || 1) - (a.level || 1));

            listaProfs.forEach(profInfo => {
                let profNivel = profInfo.level || 1;
                let profXp = profInfo.xp || 0;
                
                let xpNecessarioProf = 40 + (25 * (profNivel - 1)) + (8 * Math.pow(profNivel - 1, 2));
                let percentProfXP = Math.min((profXp / xpNecessarioProf) * 100, 100);
                
                let nomeProf = profInfo.display_name || profInfo.nome || profInfo.type || "Aprendiz";
                
                let keyword = "";
                let iconeProfFall = "⚒️";
                let imgGenerica = ""; 
                let isCrafting = false;
                
                const profStr = (profInfo.key || profInfo.type || "").toLowerCase();
                
                // 🌿 PROFISSÕES DE COLETA
                if (profStr.includes('lenhador')) { keyword = "machado"; iconeProfFall = "🪓"; imgGenerica = "machado"; }
                else if (profStr.includes('minerador')) { keyword = "picareta"; iconeProfFall = "⛏️"; imgGenerica = "picareta"; }
                else if (profStr.includes('colhedor')) { keyword = "foice"; iconeProfFall = "🌿"; imgGenerica = "foice"; }
                else if (profStr.includes('esfolador')) { keyword = "faca"; iconeProfFall = "🔪"; imgGenerica = "faca"; }
                else if (profStr.includes('alquimista')) { keyword = "frasco"; iconeProfFall = "🧪"; imgGenerica = "frasco"; }
                
                // 🔨 PROFISSÕES DE PRODUÇÃO
                else if (profStr.includes('ferreiro')) { keyword = "martelo_ferreiro"; iconeProfFall = "🔨"; imgGenerica = "martelo_ferreiro"; isCrafting = true; }
                else if (profStr.includes('armeiro')) { keyword = "martelo_armeiro"; iconeProfFall = "⚔️"; imgGenerica = "martelo_armeiro"; isCrafting = true; }
                else if (profStr.includes('alfaiate')) { keyword = "alfaiate"; iconeProfFall = "🧵"; imgGenerica = "kit_alfaiate"; isCrafting = true; }
                else if (profStr.includes('joalheiro')) { keyword = "joalheiro"; iconeProfFall = "💎"; imgGenerica = "kit_joalheiro"; isCrafting = true; }
                else if (profStr.includes('curtidor')) { keyword = "curtidor"; iconeProfFall = "👞"; imgGenerica = "kit_curtidor"; isCrafting = true; }
                
                // 🔥 CÁLCULO DOS BÔNUS 🔥
                let bonusTexto = "";
                if (isCrafting) {
                    bonusTexto = `⏱️ Tempo de Forja: -${(profNivel * 0.5).toFixed(1)}%`;
                } else {
                    bonusTexto = `🎯 Drop Fixo: +${Math.floor(profNivel / 10)} | ✨ Chance Duplo: ${(profNivel * 0.5).toFixed(1)}%`;
                }
                
                let imgFerramentaHtml = `<span style="font-size: 1.6em;">${iconeProfFall}</span>`;
                
                // CORES PADRÃO (Tier 1)
                let corBordaT = "#475569"; 
                let corFundoT = "#0f172a";
                let glowT = "rgba(0,0,0,0.5)";
                let tierTxt = "T1";

                if (keyword) {
                    const ferramentaUser = p.inventario.find(i => i.base_id && i.base_id.toLowerCase().includes(keyword));
                    if (ferramentaUser) {
                        const idItem = ferramentaUser.base_id.toLowerCase();
                        
                        if (idItem.includes('ferro') || idItem.includes('ceramica') || idItem.includes('_t2')) {
                            corBordaT = "#22c55e"; corFundoT = "rgba(34, 197, 94, 0.1)"; glowT = "rgba(34, 197, 94, 0.4)"; tierTxt = "T2";
                        } 
                        else if (idItem.includes('aco') || idItem.includes('cristal') || idItem.includes('_t3')) {
                            corBordaT = "#3b82f6"; corFundoT = "rgba(59, 130, 246, 0.1)"; glowT = "rgba(59, 130, 246, 0.4)"; tierTxt = "T3";
                        } 
                        else if (idItem.includes('mithril') || idItem.includes('obsidiana') || idItem.includes('runico') || idItem.includes('_t4')) {
                            corBordaT = "#a855f7"; corFundoT = "rgba(168, 85, 247, 0.1)"; glowT = "rgba(168, 85, 247, 0.4)"; tierTxt = "T4";
                        } 
                        else if (idItem.includes('adamantio') || idItem.includes('vorpal') || idItem.includes('vazio') || idItem.includes('druidica') || idItem.includes('_t5')) {
                            corBordaT = "#eab308"; corFundoT = "rgba(234, 179, 8, 0.1)"; glowT = "rgba(234, 179, 8, 0.4)"; tierTxt = "T5";
                        }

                        const linkBaseNuvem = window.CATALOGO_SISTEMA ? "https://raw.githubusercontent.com/Eldorabotpy/static-img/refs/heads/main/assets/" : "/static/assets/";
                        const imgPath = `${linkBaseNuvem}itens/equipamentos/${imgGenerica}.png`;
                        
                        imgFerramentaHtml = `<img src="${imgPath}" onerror="this.outerHTML='<span style=\\'font-size:1.6em;\\'>${iconeProfFall}</span>'" style="width: 32px; height: 32px; object-fit: contain; filter: drop-shadow(0px 2px 3px rgba(0,0,0,0.8));">`;
                    }
                }

                htmlProfissao += `
                <div style="background: rgba(30, 41, 59, 0.8); padding: 12px; border-radius: 10px; border: 1px solid #ca8a04; box-shadow: inset 0 0 15px rgba(202, 138, 4, 0.1); position: relative;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                        <div style="display: flex; align-items: center; gap: 10px;">
                            
                            <span style="background: ${corFundoT}; width: 48px; height: 48px; display: flex; justify-content: center; align-items: center; border-radius: 8px; border: 2px solid ${corBordaT}; box-shadow: 0 0 10px ${glowT}; position: relative;">
                                ${imgFerramentaHtml}
                                <div style="position: absolute; bottom: -6px; right: -6px; background: ${corBordaT}; color: #fff; font-size: 0.6em; font-weight: bold; padding: 2px 5px; border-radius: 6px; text-shadow: 1px 1px 1px #000;">${tierTxt}</div>
                            </span>
                            <div>
                                <div style="color: #facc15; font-weight: 900; font-family: 'Cinzel', serif; text-transform: uppercase; text-shadow: 1px 1px 2px #000; letter-spacing: 1px;">${nomeProf}</div>
                                <div style="color: #cbd5e1; font-size: 0.8em; font-weight: bold;">Nível ${profNivel}</div>
                            </div>
                        </div>
                        <div style="text-align: right;">
                            <span style="color: #fff; font-size: 0.75em; font-weight: bold; background: #000; padding: 4px 8px; border-radius: 6px; border: 1px solid #333;">${profXp.toLocaleString('pt-BR')} / ${xpNecessarioProf.toLocaleString('pt-BR')} XP</span>
                        </div>
                    </div>
                    
                    <div style="width: 100%; height: 8px; background: #020617; border-radius: 4px; border: 1px solid #000; overflow: hidden; margin-bottom: 8px;">
                        <div style="width: ${percentProfXP}%; height: 100%; background: linear-gradient(90deg, #a16207, #facc15); border-radius: 4px; box-shadow: 0 0 8px rgba(250, 204, 21, 0.6); transition: width 0.5s ease-in-out;"></div>
                    </div>
                    
                    <div style="text-align: right; color: #6ee7b7; font-size: 0.75em; font-weight: bold; text-shadow: 1px 1px 2px #000; background: rgba(0,0,0,0.4); padding: 4px 8px; border-radius: 4px; border: 1px dashed #059669; display: inline-block; float: right;">
                        ${bonusTexto}
                    </div>
                    <div style="clear: both;"></div>
                </div>`;
            });
            
            htmlProfissao += `</div>`;
        } else {
            // 👇 SE NÃO TIVER PROFISSÃO, MOSTRA ISTO 👇
            htmlProfissao = `
            <div style="background: rgba(15, 23, 42, 0.6); padding: 12px; border-radius: 10px; border: 1px dashed #475569; margin-bottom: 20px; text-align: center;">
                <div style="color: #94a3b8; font-size: 0.9em; font-weight: bold; margin-bottom: 4px;">Nenhum Ofício Aprendido</div>
                <div style="color: #64748b; font-size: 0.75em; font-style: italic;">Encontra um Mestre de Guilda para aprenderes uma profissão.</div>
            </div>`;
        }
        // ==========================================
        // 3. O TRADUTOR DO GITHUB E CORPO COMPLETO
        // ==========================================
        
        // --- BANNER ---
        let bannerCaminho = p.banner_customizado;
        if (typeof bannerCaminho === 'object' && bannerCaminho !== null) bannerCaminho = bannerCaminho.path;
        
        let bannerImgCss = 'linear-gradient(135deg, #2c3e50, #1a1a1a)'; 
        let bannerRawUrl = ''; 
        if (bannerCaminho && bannerCaminho !== 'padrao' && bannerCaminho !== '') {
            if (window.CATALOGO_SISTEMA && window.CATALOGO_SISTEMA.banners[bannerCaminho]) {
                bannerRawUrl = window.CATALOGO_SISTEMA.banners[bannerCaminho].path;
                bannerImgCss = `url('${bannerRawUrl}')`;
            } else if (bannerCaminho.startsWith('http')) {
                bannerRawUrl = bannerCaminho;
                bannerImgCss = `url('${bannerCaminho}')`;
            }
        }

        // --- AVATAR (ROSTO PARA O HUD) ---
        let avatarCaminho = p.avatar_customizado;
        if (typeof avatarCaminho === 'object' && avatarCaminho !== null) avatarCaminho = avatarCaminho.path;
        
        let avatarFinalRosto = p.avatar || 'https://raw.githubusercontent.com/Eldorabotpy/static-img/main/assets/avatares/avatar_padrao_m.png';

        if (avatarCaminho && avatarCaminho !== 'padrao' && avatarCaminho !== '') {
            if (window.CATALOGO_SISTEMA && window.CATALOGO_SISTEMA.avatares[avatarCaminho]) {
                avatarFinalRosto = window.CATALOGO_SISTEMA.avatares[avatarCaminho].path;
            } else if (avatarCaminho.startsWith('http')) {
                avatarFinalRosto = avatarCaminho;
            }
        }

        // Atualiza a bolinha do Mapa
        const imgHudMapa = document.getElementById('hud-img-avatar');
        if (imgHudMapa) {
            imgHudMapa.src = avatarFinalRosto;
            imgHudMapa.onerror = function() { this.src = 'https://raw.githubusercontent.com/Eldorabotpy/static-img/main/assets/avatares/avatar_padrao_m.png'; };
        }

        // --- AVATAR CORPO COMPLETO (MOSTRA A SKIN EQUIPADA!) ---
        const generoCurto = (p.gender && p.gender.toLowerCase() === 'feminino') ? 'f' : 'm';
        const linkBaseNuvem = window.CATALOGO_SISTEMA ? "https://raw.githubusercontent.com/Eldorabotpy/static-img/main/assets/" : "/static/assets/";
        
        // 1. Descobre qual é a Skin atual (Se não tiver nenhuma, usa a classe base do jogador)
        let skinDoCorpo = p.equipped_skin;
        if (!skinDoCorpo || skinDoCorpo === 'padrao') {
            skinDoCorpo = `${classeKey}_${generoCurto}`; 
        }
        
        // 👇 ADICIONE ESTA LINHA: Garante que o mapa sempre saiba a skin que veio do Banco de Dados!
        localStorage.setItem("skinEquipada", skinDoCorpo);

        // 2. Constrói a URL para puxar a arte de corpo inteiro na pasta 'corpo_completo'
        const fullBodyImgUrl = `${linkBaseNuvem}corpo_completo/${skinDoCorpo}_full.png`;
        const fallbackFullBody = `${linkBaseNuvem}corpo_completo/aventureiro_m_full.png`;
        
        // ==========================================
        // 4. CONSTRUÇÃO DO HTML DAS ABAS
        // ==========================================

        // --- Status ---
        let htmlStatus = `<div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-top: 15px;">`;
        for (const key in p.status) {
            const st = p.status[key];
            const podeUpar = p.pontos_livres > 0 ? `<button onclick="distribuirPonto('${key}')" style="background:#2ecc71; color:#000; border:none; border-radius:4px; width:24px; height:24px; font-weight:bold; cursor:pointer;">+</button>` : '';
            htmlStatus += `
                <div style="background: #1e293b; border: 1px solid #334155; padding: 10px; border-radius: 8px; display: flex; justify-content: space-between; align-items: center;">
                    <div><span style="font-size: 1.2em;">${st.emoji}</span> <span style="color: #cbd5e1; font-size: 0.8em; text-transform: uppercase; font-weight: bold;">${st.nome}</span></div>
                    <div style="display: flex; align-items: center; gap: 8px;"><strong style="color: #f8fafc; font-size: 1.2em;">${st.valor}</strong>${podeUpar}</div>
                </div>`;
        }
        htmlStatus += `</div>
            <div style="margin-top: 15px; background: #1e293b; border: 1px solid #334155; padding: 10px; border-radius: 8px;">
                <div style="color: #94a3b8; font-size: 0.7em; font-weight: bold; text-transform: uppercase; margin-bottom: 8px;">🎲 Chances Secundárias</div>
                <div style="display: flex; justify-content: space-around; font-size: 0.9em;">
                    <div><span style="font-size: 1.2em;">💨</span> Esquiva: <strong style="color: #38bdf8;">${p.esquiva || 0}%</strong></div>
                    <div><span style="font-size: 1.2em;">⚔️</span> Atk Duplo: <strong style="color: #f87171;">${p.atk_duplo || 0}%</strong></div>
                </div>
            </div>`;

        // --- Equipamentos e Slots ---
        const POSICOES_SLOTS = {
            'elmo':     { top: '12%', left: '12%', transform: 'translate(-50%, -50%)' },
            'arma':     { top: '31%', left: '12%', transform: 'translate(-50%, -50%)' },
            'armadura': { top: '50%', left: '12%', transform: 'translate(-50%, -50%)' },
            'luvas':    { top: '69%', left: '12%', transform: 'translate(-50%, -50%)' },
            'tool':     { top: '88%', left: '12%', transform: 'translate(-50%, -50%)' },
            'colar':    { top: '12%', left: '88%', transform: 'translate(-50%, -50%)' },
            'brinco':   { top: '31%', left: '88%', transform: 'translate(-50%, -50%)' },
            'calca':    { top: '50%', left: '88%', transform: 'translate(-50%, -50%)' },
            'anel':     { top: '69%', left: '88%', transform: 'translate(-50%, -50%)' },
            'botas':    { top: '88%', left: '88%', transform: 'translate(-50%, -50%)' }
        };

        let htmlSlots = '';
        let htmlFerramentas = '';

        const equipamentosCorpo = (p.equipamentos || []).filter(eq => {
            const slot = String(eq.slot || '');
            return !slot.startsWith('tool_') && slot !== 'tool';
        });

        const ferramentasProfissao = (p.equipamentos || []).filter(eq => {
            const slot = String(eq.slot || '');
            return slot.startsWith('tool_');
        });

        equipamentosCorpo.forEach(eq => {
            const pos = POSICOES_SLOTS[eq.slot] || { top: '50%', left: '50%' };
            const corBorda = eq.vazio ? "#334155" : "#f59e0b";
            const corFundo = eq.vazio ? "rgba(15, 23, 42, 0.8)" : "rgba(245, 158, 11, 0.15)";

            let visualItem = eq.vazio ? `<span style="font-size: 1.4em; opacity: 0.3;">${eq.emoji}</span>` : 
            `<img data-equip-img="${eq.uid || eq.id || eq.slot}" src="/static/assets/box.png" onerror="this.style.display='none'; this.nextElementSibling.style.display='inline-block';" style="max-width: 85%; max-height: 85%; object-fit: contain; filter: drop-shadow(0 2px 4px rgba(0,0,0,0.8));">
            <span style="display:none; font-size: 1.8em;">${eq.icon || eq.emoji || '📦'}</span>`;

            htmlSlots += `
                <div onclick="${!eq.vazio ? `abrirModalItem('${eq.slot}', 'equipado')` : ''}" 
                     style="position: absolute; ${Object.entries(pos).map(([k, v]) => `${k}:${v};`).join('')} 
                            width: 50px; height: 50px; background: ${corFundo}; border: 2px solid ${corBorda}; 
                            border-radius: 8px; display: flex; justify-content: center; align-items: center; 
                            cursor: ${eq.vazio ? 'default' : 'pointer'}; box-shadow: 0 4px 8px rgba(0,0,0,0.6);">
                    ${visualItem}
                </div>`;
        });

        if (ferramentasProfissao.length > 0) {
            htmlFerramentas = `
                <div style="margin-top: 12px; background: #020617; border: 2px solid #334155; border-radius: 12px; padding: 10px; box-shadow: inset 0 0 20px rgba(0,0,0,0.8);">
                    <div style="color: #facc15; font-family: 'Cinzel', serif; font-size: 0.8em; font-weight: 900; text-transform: uppercase; margin-bottom: 8px; text-align: center; letter-spacing: 1px;">
                        🛠️ Ferramentas de Profissão
                    </div>

                    <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(62px, 1fr)); gap: 8px;">
            `;

            ferramentasProfissao.forEach(eq => {
                const corBorda = eq.vazio ? "#334155" : "#22c55e";
                const corFundo = eq.vazio ? "rgba(15, 23, 42, 0.8)" : "rgba(34, 197, 94, 0.12)";
                const nomeProf = String(eq.slot_profissao || eq.tool_type || eq.slot || "")
                    .replace("tool_", "")
                    .replace(/_/g, " ")
                    .toUpperCase();

                let durBadge = "";

                if (!eq.vazio && Array.isArray(eq.durability)) {
                    const atual = Number(eq.durability[0] || 0);
                    const maximo = Number(eq.durability[1] || 1);
                    const porc = maximo > 0 ? (atual / maximo) * 100 : 0;
                    const corDur = porc > 50 ? "#22c55e" : (porc > 20 ? "#eab308" : "#ef4444");

                    durBadge = `
                        <div style="position:absolute; left:5px; right:5px; bottom:4px; height:4px; background:#020617; border-radius:4px; overflow:hidden; border:1px solid #111827;">
                            <div style="width:${Math.max(0, Math.min(100, porc))}%; height:100%; background:${corDur};"></div>
                        </div>
                    `;
                }

                const visualTool = eq.vazio
                    ? `<span style="font-size: 1.7em; opacity: 0.35;">${eq.emoji || '🛠️'}</span>`
                    : `<img data-equip-img="${eq.uid || eq.id || eq.slot}" src="/static/assets/box.png" onerror="this.style.display='none'; this.nextElementSibling.style.display='inline-block';" style="max-width: 78%; max-height: 72%; object-fit: contain; filter: drop-shadow(0 2px 4px rgba(0,0,0,0.8));">
                       <span style="display:none; font-size: 1.7em;">${eq.icon || eq.emoji || '🛠️'}</span>`;

                htmlFerramentas += `
                    <div onclick="${!eq.vazio ? `abrirModalItem('${eq.slot}', 'equipado')` : ''}"
                         title="${eq.nome || nomeProf}"
                         style="position: relative; height: 62px; background: ${corFundo}; border: 2px solid ${corBorda}; border-radius: 9px; display: flex; justify-content: center; align-items: center; cursor: ${eq.vazio ? 'default' : 'pointer'}; box-shadow: 0 4px 8px rgba(0,0,0,0.5);">
                        
                        ${visualTool}

                        <div style="position:absolute; top:-6px; right:-6px; background:#0f172a; color:#facc15; border:1px solid #475569; border-radius:7px; padding:1px 4px; font-size:0.55em; font-weight:900;">
                            ${nomeProf.substring(0, 3)}
                        </div>

                        ${durBadge}
                    </div>
                `;
            });

            htmlFerramentas += `
                    </div>
                </div>
            `;
        }

        // Aba Equipamentos Visual com Corpo Completo no Fundo
        const htmlEquips = `
            <div style="margin-top: 15px;">
                <div style="position: relative; width: 100%; height: 420px; background: #020617; border-radius: 12px; border: 2px solid #334155; overflow: hidden; box-shadow: inset 0 0 30px rgba(0,0,0,0.9);">
                    <div style="position: absolute; top: 0; left: 0; width: 100%; height: 100%; z-index: 0; opacity: 0.4;">
                        <img src="${bannerRawUrl}" onerror="this.style.display='none'" style="width: 100%; height: 100%; object-fit: cover;">
                    </div>
                    <div style="position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); width: 70%; height: 95%; z-index: 1; display: flex; justify-content: center; align-items: center; opacity: 0.7;">
                        <img src="${fullBodyImgUrl}" onerror="this.src='${fallbackFullBody}'; this.onerror=null;" style="width: 100%; height: 100%; object-fit: contain; filter: drop-shadow(0px 10px 15px rgba(0,0,0,0.9)); pointer-events: none;">
                    </div>
                    <div style="position: relative; width: 100%; height: 100%; z-index: 2;">${htmlSlots}</div>
                </div>

                ${htmlFerramentas}
            </div>`;

        // --- Inventário ---
        let htmlInv = `
            <div style="display: flex; gap: 5px; margin-top: 15px; margin-bottom: 15px; overflow-x: auto; padding-bottom: 5px;">
                <button onclick="filtrarMochila('todos')" id="btn-filtro-todos" style="flex: 1; padding: 6px; background: #3b82f6; color: #fff; border: none; border-radius: 4px; font-weight: bold; cursor: pointer; font-size: 0.75em;">Todos</button>
                <button onclick="filtrarMochila('equips')" id="btn-filtro-equips" style="flex: 1; padding: 6px; background: #1e293b; color: #94a3b8; border: none; border-radius: 4px; font-weight: bold; cursor: pointer; font-size: 0.75em;">Equips</button>
                <button onclick="filtrarMochila('materiais')" id="btn-filtro-materiais" style="flex: 1; padding: 6px; background: #1e293b; color: #94a3b8; border: none; border-radius: 4px; font-weight: bold; cursor: pointer; font-size: 0.75em;">Materiais</button>
                <button onclick="filtrarMochila('usaveis')" id="btn-filtro-usaveis" style="flex: 1; padding: 6px; background: #1e293b; color: #94a3b8; border: none; border-radius: 4px; font-weight: bold; cursor: pointer; font-size: 0.75em;">Usáveis</button>
            </div>
            <div id="grid-mochila" style="display: grid; grid-template-columns: repeat(auto-fill, minmax(70px, 1fr)); gap: 8px;"></div>
        `;

        // ==========================================
        // 5. INJEÇÃO FINAL NO ECRÃ
        // ==========================================
        conteudo.innerHTML = `
            <div style="background-image: ${bannerImgCss}; background-size: cover; background-position: center; position: relative; width: 100%; height: 350px; border-radius: 12px; border: 2px solid #334155; overflow: hidden; box-shadow: inset 0 0 50px rgba(0,0,0,0.9); margin-bottom: 15px;">
                <div style="position: absolute; top: 0; left: 0; width: 100%; height: 100%; background: linear-gradient(0deg, rgba(0,0,0,0.9) 0%, rgba(0,0,0,0.4) 50%, rgba(0,0,0,0.6) 100%); z-index: 1;"></div>
                
                <img src="${fullBodyImgUrl}" onerror="this.src='${fallbackFullBody}'; this.onerror=null;" style="position: absolute; bottom: -5px; left: 50%; transform: translateX(-50%); height: 95%; width: auto; object-fit: contain; z-index: 2; filter: drop-shadow(0 0 15px rgba(0,0,0,0.9)); pointer-events: none;">

                <div style="position: absolute; bottom: 20px; right: 20px; z-index: 3; text-align: right;">
                    <h2 style="margin: 0 0 5px 0; color: #fff; font-size: 2em; text-shadow: 2px 2px 6px #000; text-transform: uppercase;">${p.nome}</h2>
                    <div style="display: flex; justify-content: flex-end; align-items: center; gap: 8px;">
                        <span style="color: #fbbf24; font-size: 1.1em; font-weight: bold;">${infoClasse.emoji} ${p.classe || infoClasse.nome}</span>
                        <span style="background: rgba(243, 156, 18, 0.2); border: 1px solid #f39c12; color: #f39c12; padding: 2px 8px; border-radius: 4px; font-weight: 900; font-size: 0.7em;">Nível ${p.level}</span>
                    </div>
                    <button onclick="window.perfilVisual.renderizarEdicao()" style="margin-top: 10px; background: rgba(0,0,0,0.5); color:#fff; border: 1px solid #666; padding: 6px 12px; font-size: 0.8em; border-radius: 6px; cursor: pointer;">⚙️ Editar Visual</button>
                </div>
            </div>
            
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-bottom: 15px;">
                <div style="background: #1a1a1a; padding: 8px 12px; border-radius: 8px; border-left: 3px solid #e74c3c; display: flex; justify-content: space-between; align-items: center;">
                    <span style="color: #e74c3c; font-size: 0.7em; font-weight: bold;">❤️ HP</span>
                    <div style="font-size: 1em; color: #fff; font-weight: bold;">${p.hp_atual} <span style="font-size:0.7em; color:#777;">/ ${p.hp_max}</span></div>
                </div>
                <div style="background: #1a1a1a; padding: 8px 12px; border-radius: 8px; border-left: 3px solid #3b82f6; display: flex; justify-content: space-between; align-items: center;">
                    <span style="color: #3b82f6; font-size: 0.7em; font-weight: bold;">💧 MP</span>
                    <div style="font-size: 1em; color: #fff; font-weight: bold;">${p.mp_atual} <span style="font-size:0.7em; color:#777;">/ ${p.mp_max}</span></div>
                </div>
                <!-- 👇 AQUI DIVIDIMOS O ESPAÇO: MEIO A MEIO PARA OURO E GEMAS 👇 -->
                <div style="background: #1a1a1a; padding: 8px 12px; border-radius: 8px; border-left: 3px solid #f1c40f; display: flex; justify-content: space-between; align-items: center;">
                    <span style="color: #f1c40f; font-size: 0.7em; font-weight: bold;">💰 Ouro</span>
                    <div style="font-size: 1em; color: #fff; font-weight: bold;">${p.gold.toLocaleString('pt-BR')}</div>
                </div>
                <div style="background: #1a1a1a; padding: 8px 12px; border-radius: 8px; border-left: 3px solid #9b59b6; display: flex; justify-content: space-between; align-items: center;">
                    <span style="color: #9b59b6; font-size: 0.7em; font-weight: bold;">💎 Gemas</span>
                    <div style="font-size: 1em; color: #fff; font-weight: bold;">${p.gems.toLocaleString('pt-BR')}</div>
                </div>
            </div>

            <div style="background: #1e1e1e; padding: 12px; border-radius: 10px; border: 1px solid #333; margin-bottom: 20px;">
                <div style="display: flex; justify-content: space-between; font-size: 0.75em; margin-bottom: 5px;"><span style="color: #aaa; font-weight: bold;">Experiência</span><span style="color: #fff;">${p.xp.toLocaleString('pt-BR')} / ${p.xp_max.toLocaleString('pt-BR')}</span></div>
                <div style="width: 100%; height: 8px; background: #111; border-radius: 4px; border: 1px solid #000;"><div style="width: ${percentXP}%; height: 100%; background: linear-gradient(90deg, #8e44ad, #9b59b6); border-radius: 4px;"></div></div>
            </div>
            
            ${htmlProfissao}
            <div style="display: flex; gap: 5px; background: #0f172a; padding: 5px; border-radius: 8px; border: 1px solid #1e293b; margin-bottom: 15px;">
                <button onclick="alternarAbaPerfil('status')" id="btn-perf-status" style="flex:1; padding:8px 5px; background:#1e293b; color:#fff; border:none; border-radius:6px; font-weight:bold; cursor:pointer; font-size:0.85em;">Atributos ${p.pontos_livres > 0 ? `<span style="background:#e74c3c; padding:2px 6px; border-radius:10px; font-size:0.8em; color:white;">${p.pontos_livres}</span>` : ''}</button>
                <button onclick="alternarAbaPerfil('equips')" id="btn-perf-equips" style="flex:1; padding:8px 5px; background:transparent; color:#94a3b8; border:none; border-radius:6px; font-weight:bold; cursor:pointer; font-size:0.85em;">Equips</button>
                <button onclick="alternarAbaPerfil('inv')" id="btn-perf-inv" style="flex:1; padding:8px 5px; background:transparent; color:#94a3b8; border:none; border-radius:6px; font-weight:bold; cursor:pointer; font-size:0.85em;">Mochila</button>
                <button onclick="alternarAbaPerfil('magias')" id="btn-perf-magias" style="flex:1; padding:8px 5px; background:transparent; color:#94a3b8; border:none; border-radius:6px; font-weight:bold; cursor:pointer; font-size:0.85em;">✨ Magias</button>
            </div>

            <div id="conteudo-perf-status" style="display: block;">${htmlStatus}</div>
            <div id="conteudo-perf-equips" style="display: none;">${htmlEquips}</div>
            <div id="conteudo-perf-inv" style="display: none;">${htmlInv}</div>
            <div id="conteudo-perf-magias" style="display: none;"></div>
        `;
        setTimeout(() => {
            document.querySelectorAll("[data-equip-img]").forEach(img => {
                const uid = img.getAttribute("data-equip-img");

                const eq = (window.perfilDadosGlobais.equipamentos || []).find(e =>
                    String(e.uid || e.id || e.slot) === String(uid)
                );

                if (eq && typeof window.aplicarImagemItemEldora === "function") {
                    window.aplicarImagemItemEldora(img, eq);
                }
            });
        }, 0);
        
        document.getElementById('perfil-carregando').style.display = 'none';
        conteudo.style.display = 'block';
        
        // Mantém a aba atual. Se for primeira abertura, começa em Atributos.
        const abaInicialPerfil = window.perfilAbaAtual || 'status';
        alternarAbaPerfil(abaInicialPerfil);

        if (abaInicialPerfil === 'inv' && typeof filtrarMochila === 'function') {
            filtrarMochila(window.perfilFiltroMochilaAtual || 'todos');
        }

    } catch (erro) {
        console.error("🚨 ERRO GRAVE NO PERFIL:", erro);
        document.getElementById('perfil-msg-carregando').innerText = "⚠️ Erro ao carregar perfil. Verifique a conexão.";
    }
}

// --- FUNÇÃO PARA ALTERNAR AS ABAS ---
window.alternarAbaPerfil = function(abaID) {
    window.perfilAbaAtual = abaID || 'status';

    document.getElementById('conteudo-perf-status').style.display = 'none';
    document.getElementById('conteudo-perf-equips').style.display = 'none';
    document.getElementById('conteudo-perf-inv').style.display = 'none';
    if(document.getElementById('conteudo-perf-skins')) document.getElementById('conteudo-perf-skins').style.display = 'none';
    if(document.getElementById('conteudo-perf-magias')) document.getElementById('conteudo-perf-magias').style.display = 'none';
    
    ['btn-perf-status', 'btn-perf-equips', 'btn-perf-inv', 'btn-perf-skins', 'btn-perf-magias'].forEach(b => {
        let btn = document.getElementById(b);
        if(btn) {
            btn.style.background = 'transparent';
            btn.style.color = '#94a3b8';
        }
    });

    let abaConteudo = document.getElementById(`conteudo-perf-${abaID}`);
    if(abaConteudo) abaConteudo.style.display = 'block';
    
    let abaBotao = document.getElementById(`btn-perf-${abaID}`);
    if(abaBotao) {
        abaBotao.style.background = '#1e293b';
        abaBotao.style.color = '#fff';
    }

    if (abaID === 'equips' && window._avatarAtualEldora) {
        const imgCentro = document.getElementById('avatar-equip-tab');
        if (imgCentro) imgCentro.src = window._avatarAtualEldora;
    }
    
    if (abaID === 'skins') carregarMenuSkins();
    if (abaID === 'magias') carregarMenuMagias();
}

// --- FUNÇÃO PARA DESENHAR AS SKINS ---
window.carregarMenuSkins = function() {
    const p = window.perfilDadosGlobais;
    const container = document.getElementById('conteudo-perf-skins');
    if (!p || !container) return;

    let html = `<div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px;">`;
    const isEquipadaPadrao = !p.equipped_skin;
    html += `
        <div onclick="equiparNovaSkin(null)" style="background:#1e293b; padding:10px; border-radius:8px; border:1px solid ${isEquipadaPadrao ? '#f1c40f' : '#334155'}; text-align:center; cursor:pointer;">
            <div style="font-size:1.5em; margin-bottom:5px;">👤</div>
            <div style="font-size:0.7em; color:#fff;">Padrão</div>
        </div>`;

    if (p.skins_disponiveis && p.skins_disponiveis.length > 0) {
        p.skins_disponiveis.forEach(skin => {
            const isEquipada = p.equipped_skin === skin.id;
            html += `
                <div onclick="equiparNovaSkin('${skin.id}')" style="background:#1e293b; padding:10px; border-radius:8px; border:1px solid ${isEquipada ? '#f1c40f' : '#334155'}; text-align:center; cursor:pointer;">
                    <div style="font-size:1.5em; margin-bottom:5px;">🎨</div>
                    <div style="font-size:0.7em; color:#fff;">${skin.nome}</div>
                </div>`;
        });
    } else {
        html += `<div style="grid-column: 1/-1; text-align: center; color: #64748b; font-size: 0.8em; margin-top: 10px;">Nenhuma aparência extra encontrada.</div>`;
    }
    container.innerHTML = html + `</div>`;
}

// --- FUNÇÃO PARA SALVAR A SKIN NO BANCO ---
window.equiparNovaSkin = async function(skinId) {
    const charId = localStorage.getItem("jogadorEldoraID");
    try {
        const res = await fetch('/api/personagem/equipar_skin', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: charId, skin_id: skinId })
        });
        const data = await res.json();
        if (data.sucesso) {
            await carregarMeuPerfil(); 
            setTimeout(() => alternarAbaPerfil('skins'), 200);
        } else {
            alert("Erro: " + data.erro);
        }
    } catch (e) { console.error(e); }
}

// ==========================================
// GRIMÓRIO DE SKILLS (MAGIAS) - ESTILO RPG GRID!
// ==========================================
window.carregarMenuMagias = async function() {
    const charId = localStorage.getItem("jogadorEldoraID");
    const container = document.getElementById('conteudo-perf-magias');
    
    if (!container) return;
    container.innerHTML = `<p style="text-align: center; color: #94a3b8; padding: 20px;">A abrir o Grimório...</p>`;

    try {
        const res = await fetch(`/api/personagem/${charId}?t=${new Date().getTime()}`);
        const pdata = await res.json();

        window._skillsDataTemp = pdata.database_skills || {};
        window._skillsEquipadasTemp = pdata.skills_equipadas || {};
        const skillsPossuidas = pdata.skills_desbloqueadas || {};

        let html = `<div style="padding: 10px;">
                        <h4 style="color:#facc15; text-align:center; margin-bottom:15px; font-family: 'Cinzel', serif; text-shadow: 0 0 10px rgba(250, 204, 21, 0.3);">Grimório de Eldora</h4>`;

        if (Object.keys(skillsPossuidas).length === 0) {
            html += `<p style="text-align: center; color: #64748b; font-style: italic; margin-top: 30px;">Nenhuma habilidade aprendida ainda. Fale com a Arquimaga Selene no nível 17.</p>`;
        } else {
            html += `<div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(65px, 1fr)); gap: 12px;">`;
            
            for (const [skillId, skillInst] of Object.entries(skillsPossuidas)) {
                const infoBase = window._skillsDataTemp[skillId] || {};
                const nomeIcone = infoBase.icon || 'default_skill';
                
                // 🌐 CAMINHO EXATO DO GITHUB ATUALIZADO
                const iconPath = `https://raw.githubusercontent.com/Eldorabotpy/static-img/refs/heads/main/assets/sprites/skills/${nomeIcone}.png`;
                const fallbackIcon = `https://raw.githubusercontent.com/Eldorabotpy/static-img/refs/heads/main/assets/sprites/skills/default_skill.png`;
                
                let slotEquipado = null;
                for (let i = 1; i <= 5; i++) {
                    if (window._skillsEquipadasTemp[`slot_${i}`] === skillId) slotEquipado = i;
                }

                const corBorda = slotEquipado ? '#8b5cf6' : '#334155';
                const sombra = slotEquipado ? '0 0 12px rgba(139, 92, 246, 0.5)' : 'none';

                html += `
                    <div onclick="window.abrirModalSkillDetalhes('${skillId}', window._skillsDataTemp['${skillId}'], ${slotEquipado || 'null'})" 
                         style="background: rgba(15, 23, 42, 0.9); border: 2px solid ${corBorda}; border-radius: 10px; aspect-ratio: 1; display: flex; flex-direction: column; justify-content: center; align-items: center; cursor: pointer; position: relative; box-shadow: ${sombra}; transition: transform 0.1s;">
                        
                        ${slotEquipado ? `<span style="position: absolute; bottom: -5px; right: -5px; background: #8b5cf6; color: #fff; font-size: 0.7em; padding: 2px 6px; border-radius: 8px; font-weight: bold; border: 2px solid #0f172a; z-index: 5;">S${slotEquipado}</span>` : ""}
                        
                        <div style="width: 42px; height: 42px; border-radius: 50%; overflow: hidden; background: #000; border: 1px solid #1e293b;">
                            <img src="${iconPath}" onerror="this.src='${fallbackIcon}'" style="width: 100%; height: 100%; object-fit: cover;">
                        </div>
                    </div>`;
            }
            html += `</div>
                     <p style="text-align:center; font-size:0.7em; color:#94a3b8; margin-top:20px; letter-spacing: 0.5px;">Clique para equipar nos slots de combate</p>`;
        }
        
        container.innerHTML = html + `</div>`;
    } catch (e) {
        container.innerHTML = `<p style="text-align: center; color: #ef4444;">Erro ao canalizar o Grimório.</p>`;
    }
}

// 2. Janela Modal de Detalhes da Magia (CORREÇÃO DE IMAGEM)
window.abrirModalSkillDetalhes = function(skillId, infoDb, slotAtual) {
    let modal = document.getElementById('modal-skill-detalhes');
    if (modal) modal.remove();

    modal = document.createElement('div');
    modal.id = 'modal-skill-detalhes';
    modal.style = "position:fixed; top:50%; left:50%; transform:translate(-50%, -50%); background:rgba(15, 23, 42, 0.98); border:2px solid #8b5cf6; border-radius:12px; padding:20px; z-index:100000; width:320px; box-shadow:0 0 30px rgba(0,0,0,0.8); display:flex; flex-direction:column; gap:15px; color:#fff;";
    document.body.appendChild(modal);

    const magiaExiste = infoDb && infoDb.display_name;
    const nome = magiaExiste ? infoDb.display_name : '⚠️ Magia Não Encontrada';
    
    let desc = magiaExiste ? infoDb.description : `ID "${skillId}" não encontrado no arquivo skills.py.`;
    let mana = 0;
    let cooldown = 0;

    if (magiaExiste) {
        mana = infoDb.mana_cost || infoDb.mp_cost || 0;
        cooldown = infoDb.cooldown_turns || 0;
        
        if (infoDb.rarity_effects && infoDb.rarity_effects.comum) {
            mana = infoDb.rarity_effects.comum.mana_cost || infoDb.rarity_effects.comum.mp_cost || mana;
            if (infoDb.rarity_effects.comum.effects && infoDb.rarity_effects.comum.effects.cooldown_turns !== undefined) {
                cooldown = infoDb.rarity_effects.comum.effects.cooldown_turns;
            }
            if (infoDb.rarity_effects.comum.description) {
                desc = infoDb.rarity_effects.comum.description;
            }
        }
    }

    // 🛠️ O SEGREDO ESTAVA AQUI: Puxando o nome igualzinho ao primeiro menu
    const nomeIconeModal = magiaExiste && infoDb.icon ? infoDb.icon : 'default_skill';
    
    // 🌐 CAMINHO EXATO DO GITHUB
    const imgUrlModal = `https://raw.githubusercontent.com/Eldorabotpy/static-img/refs/heads/main/assets/sprites/skills/${nomeIconeModal}.png`;
    const fallbackIconModal = `https://raw.githubusercontent.com/Eldorabotpy/static-img/refs/heads/main/assets/sprites/skills/default_skill.png`;

    let areaBotoes = '';
    
    if (slotAtual) {
        areaBotoes = `<button onclick="window.processarEquiparSkill('', ${slotAtual})" style="width:100%; padding:10px; background:#ef4444; color:white; border:none; border-radius:8px; font-weight:bold; cursor:pointer; box-shadow: 0 4px 6px rgba(0,0,0,0.3);">Desequipar (Slot ${slotAtual})</button>`;
    } else {
        areaBotoes = `<button onclick="window.iniciarEquiparSkill('${skillId}')" style="width:100%; padding:10px; background:#10b981; color:white; border:none; border-radius:8px; font-weight:bold; cursor:pointer; box-shadow: 0 4px 6px rgba(0,0,0,0.3);" ${!magiaExiste ? 'disabled style="opacity:0.5;"' : ''}>Equipar</button>`;
    }

    // Adicionei this.onerror=null para evitar que ele quebre de vez se o fallback também falhar
    modal.innerHTML = `
        <div style="display:flex; justify-content:space-between; align-items:flex-start;">
            <div style="display:flex; gap:12px; align-items:center;">
                <img src="${imgUrlModal}" onerror="this.onerror=null; this.src='${fallbackIconModal}'" style="width:54px; height:54px; border-radius:50%; border:2px solid #8b5cf6; object-fit:cover; background: #000;">
                <div>
                    <h3 style="margin:0; font-size:16px; color:${magiaExiste ? '#c4b5fd' : '#ef4444'}; font-family:'Cinzel', serif;">${nome}</h3>
                    <div style="font-size:12px; color:#94a3b8; margin-top:4px;">Mana: <span style="color:#60a5fa">${mana}</span> | Recarga: <span style="color:#f87171">${cooldown} turnos</span></div>
                </div>
            </div>
            <div onclick="document.getElementById('modal-skill-detalhes').remove()" style="cursor:pointer; color:#ef4444; font-weight:bold; font-size:20px; line-height:1;">×</div>
        </div>
        <div style="font-size:13px; color:#cbd5e1; background:#1e293b; padding:12px; border-radius:8px; border:1px solid #334155;">
            ${desc}
        </div>
        <div id="area-botoes-skill">
            ${areaBotoes}
        </div>
    `;
};

// --- SALVAR MAGIA ---
window.equiparSkillPerfil = async function(skillId, slotNum) {
    document.getElementById('modal-skill').style.display = 'none';
    const charId = localStorage.getItem("jogadorEldoraID");
    try {
        const res = await fetch('/api/personagem/equipar_skill', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: charId, skill_id: skillId, slot: slotNum })
        });
        const data = await res.json();
        if (data.sucesso) { carregarMenuMagias(); } 
        else { alert("Erro: " + data.erro); }
    } catch(e) {}
}
// ==========================================
// FILTRO E RENDERIZAÇÃO DA MOCHILA (CORRIGIDO)
// ==========================================
window.filtrarMochila = function(filtro) {
    window.perfilFiltroMochilaAtual = filtro || 'todos';

    if (!window.perfilDadosGlobais || !window.perfilDadosGlobais.inventario) return;
    
    const inv = window.perfilDadosGlobais.inventario;
    const grid = document.getElementById('grid-mochila');
    if (!grid) return;

    // Atualiza o visual dos botões de filtro
    ['todos', 'equips', 'materiais', 'usaveis'].forEach(f => {
        const btn = document.getElementById(`btn-filtro-${f}`);
        if (btn) {
            btn.style.background = (f === filtro) ? '#3b82f6' : '#1e293b';
            btn.style.color = (f === filtro) ? '#fff' : '#94a3b8';
        }
    });

    // 🛡️ Filtro Robusto (lendo a propriedade padronizada que criamos)
    let filtrados = inv;
    
    if (filtro === 'equips') {
        filtrados = inv.filter(i => [
            'equipamento', 'weapon', 'armor', 'helmet', 'boots', 'bota', 'ring', 'anel', 'necklace', 'colar', 'earring', 'brinco', 
            'tool', 'ferramenta', 'arma', 'armadura', 'elmo', 'lenhador', 'minerador', 'colhedor', 'esfolador', 
            'ferreiro', 'armeiro', 'alfaiate', 'joalheiro', 'curtidor'
        ].includes((i.tipo || i.type || '').toLowerCase()));

    } else if (filtro === 'materiais') {
        filtrados = inv.filter(i => {
            const t = (i.tipo || i.type || '').toLowerCase();
            // Tudo o que é material ou o que não se encaixou em nada
            return ['material', 'material_bruto', 'material_refinado', 'material_runico', 'divino'].includes(t) || t === '' || t === 'materiais';
        });

    } else if (filtro === 'usaveis') {
        filtrados = inv.filter(i => [
            'potion', 'pocao', 'consumable', 'consumivel', 'scroll', 'pergaminho', 'chest', 'box', 'especial'
        ].includes((i.tipo || i.type || '').toLowerCase()));
    }

    grid.innerHTML = '';

    if (filtrados.length === 0) {
        grid.innerHTML = `<div style="grid-column: 1 / -1; text-align: center; padding: 20px; color: #64748b;">Mochila vazia nesta categoria.</div>`;
        return;
    }

    // Pega o caminho base do GitHub
    const linkBaseNuvem = window.CATALOGO_SISTEMA ? "https://raw.githubusercontent.com/Eldorabotpy/static-img/main/assets/" : "/static/assets/";

    filtrados.forEach(item => {
        // Envia o item inteiro para a bússola decidir

        
        const coresRaridade = {'comum': '#94a3b8', 'incomum': '#22c55e', 'raro': '#3b82f6', 'epico': '#a855f7', 'lendario': '#eab308', 'mitico': '#ef4444'};
        const corBorda = coresRaridade[(item.raridade || 'comum').toLowerCase()] || '#334155';
        
        const slotHtml = `
            <div onclick="abrirModalItem('${item.id}', 'mochila')" 
                 style="position: relative; width: 100%; aspect-ratio: 1; background: rgba(15, 23, 42, 0.8); border: 2px solid ${corBorda}; border-radius: 8px; display: flex; justify-content: center; align-items: center; cursor: pointer; box-shadow: inset 0 0 15px rgba(0,0,0,0.8), 0 2px 4px rgba(0,0,0,0.4); transition: transform 0.1s;">
                
                <img data-item-img="${item.id}" src="/static/assets/box.png" onerror="this.style.display='none'; this.nextElementSibling.style.display='inline-block';" style="max-width: 80%; max-height: 80%; object-fit: contain; filter: drop-shadow(0 4px 6px rgba(0,0,0,0.9));">
                <span style="display:none; font-size: 2em; opacity: 0.8;">${item.emoji || '📦'}</span>
                
                <div style="position: absolute; bottom: -5px; right: -5px; background: #000; color: #fff; font-size: 0.7em; font-weight: bold; padding: 2px 6px; border-radius: 10px; border: 1px solid #333; box-shadow: 0 2px 4px rgba(0,0,0,0.5);">
                    x${item.qtd || item.quantidade || 1}
                </div>
                
                ${item.refino > 0 ? `<div style="position: absolute; top: -5px; left: -5px; background: #eab308; color: #000; font-size: 0.65em; font-weight: bold; padding: 2px 4px; border-radius: 4px; box-shadow: 0 2px 4px rgba(0,0,0,0.5);">+${item.refino}</div>` : ''}
            </div>
        `;
        grid.innerHTML += slotHtml;
        const imgEl = grid.querySelector(`img[data-item-img="${item.id}"]`);
        window.aplicarImagemItemEldora(imgEl, item);
    });
};

// ==========================================
// ABRIR JANELA DE DETALHES DO ITEM
// ==========================================
// ==========================================
// ABRIR JANELA DE DETALHES DO ITEM (ATUALIZADA)
// ==========================================
window.abrirModalItem = function(idAlvo, origem) {
    if(!window.perfilDadosGlobais) return;
    let itemData = null;

    if (origem === 'mochila' || origem === 'inventario') {
        itemData = window.perfilDadosGlobais.inventario.find(i => i.id === idAlvo);
    } else if (origem === 'equipado') {
        itemData = window.perfilDadosGlobais.equipamentos.find(e => e.slot === idAlvo);
    }

    if (!itemData || itemData.vazio) return;

    if (!document.getElementById('modal-item')) {
        const modalHtml = `
            <div id="modal-item" style="display:none; position:fixed; top:0; left:0; width:100%; height:100%; background:rgba(0,0,0,0.85); z-index:99999; justify-content:center; align-items:center; backdrop-filter: blur(4px);">
                <div style="background: linear-gradient(135deg, #1e293b, #0f172a); width: 85%; max-width: 320px; border-radius: 12px; border: 2px solid #3b82f6; padding: 20px; text-align: center; position: relative;">
                    <span onclick="fecharModalItem()" style="position: absolute; top: 10px; right: 15px; font-size: 1.5em; color: #ef4444; cursor: pointer; font-weight:bold;">&times;</span>
                    <div id="modal-item-icon" style="margin-bottom: 10px; min-height: 64px; display:flex; justify-content:center; align-items:center;"></div>
                    <h3 id="modal-item-nome" style="margin: 0 0 5px 0; color: #fff; font-size: 1.2em; font-family:'Cinzel',serif;">Nome</h3>
                    <div id="modal-item-raridade" style="font-size: 0.8em; font-weight: bold; margin-bottom: 10px; text-transform: uppercase;"></div>
                    <p id="modal-item-desc" style="color: #94a3b8; font-size: 0.85em; margin: 10px 0; border-top: 1px solid #334155; padding-top: 10px;">Descrição</p>
                    <div id="modal-item-stats" style="display: flex; flex-wrap: wrap; gap: 5px; justify-content: center; margin-bottom: 15px;"></div>
                    <div id="modal-item-acoes" style="display: flex; gap: 8px; justify-content: center; flex-wrap: wrap;"></div>
                </div>
            </div>`;
        document.body.insertAdjacentHTML('beforeend', modalHtml);
    }

    const refinoTxt = (itemData.refino && itemData.refino > 0) ? ` [+${itemData.refino}]` : '';
    const qtdValor = itemData.qtd || itemData.quantidade || 1;
    const qtdTxt = (origem === 'mochila' || origem === 'inventario') && qtdValor > 1 
        ? ` <span style="color: #fbbf24; font-size: 0.8em;">(x${qtdValor})</span>` 
        : '';
    
    document.getElementById('modal-item-nome').innerHTML = itemData.nome + refinoTxt + qtdTxt;
    
    // 👇 MÁGICA 1: BLINDAGEM DE INGLÊS/PORTUGUÊS E IDs 👇
    const t = (itemData.tipo || itemData.type || "").toLowerCase();
    const idReal = itemData.base_id || itemData.item_id || itemData.id || "indefinido";
    const nomeLower = (itemData.nome || itemData.display_name || "").toLowerCase();

    const imgUrl = "/static/assets/box.png";

    document.getElementById('modal-item-icon').innerHTML = `
        <img id="modal-img-item-real" src="${imgUrl}" onerror="this.style.display='none'; this.nextElementSibling.style.display='inline-block';" style="max-width: 90%; max-height: 90%; object-fit: contain; filter: drop-shadow(0 4px 10px rgba(0,0,0,0.9));">
        <span style="display:none; font-size: 2.5em; text-shadow: 0 0 10px rgba(255,255,255,0.2);">${itemData.emoji || itemData.icon || '📦'}</span>
    `;

    window.aplicarImagemItemEldora(document.getElementById("modal-img-item-real"), itemData);

    document.getElementById('modal-item-desc').innerText = itemData.desc || "Sem descrição.";
    
    const rari = document.getElementById('modal-item-raridade');
    rari.innerText = itemData.raridade || "Comum";
    const coresRaridade = {'comum': '#94a3b8', 'incomum': '#22c55e', 'bom': '#22c55e', 'raro': '#3b82f6', 'epico': '#a855f7', 'lendario': '#eab308', 'unico': '#ef4444', 'mitico': '#00f2fe'};
    rari.style.color = coresRaridade[(itemData.raridade||'comum').toLowerCase()] || '#cbd5e1';

    let statsHtml = '';

    const statsDoItem =
        itemData.stats ||
        itemData.attributes ||
        itemData.enchantments ||
        {};

    const mapEmojis = {
        'vida':'❤️',
        'hp':'❤️',
        'defesa':'🛡️',
        'defense':'🛡️',
        'sorte':'🍀',
        'luck':'🍀',
        'agilidade':'🏃',
        'initiative':'🏃',
        'iniciativa':'🏃',
        'forca':'💪',
        'força':'💪',
        'strength':'💪',
        'inteligencia':'🧠',
        'intelligence':'🧠',
        'furia':'🔥',
        'fúria':'🔥',
        'precisao':'🎯',
        'precisão':'🎯',
        'letalidade':'🗡️',
        'bushido':'🥷',
        'foco':'🧘',
        'carisma':'🎶',
        'fe':'✨',
        'fé':'✨',
        'crit_chance_flat':'💥',
        'crit':'💥',
        'dmg':'⚔️',
        'damage':'⚔️',
        'attack':'⚔️',
        'ataque':'⚔️'
    };

    function nomeBonitoStat(chave) {
        const nomes = {
            vida: 'VIDA',
            hp: 'VIDA',
            defesa: 'DEFESA',
            defense: 'DEFESA',
            sorte: 'SORTE',
            luck: 'SORTE',
            agilidade: 'AGILIDADE',
            initiative: 'INICIATIVA',
            iniciativa: 'INICIATIVA',
            forca: 'FORÇA',
            força: 'FORÇA',
            strength: 'FORÇA',
            inteligencia: 'INTELIGÊNCIA',
            intelligence: 'INTELIGÊNCIA',
            furia: 'FÚRIA',
            precisão: 'PRECISÃO',
            precisao: 'PRECISÃO',
            letalidade: 'LETALIDADE',
            bushido: 'BUSHIDO',
            foco: 'FOCO',
            carisma: 'CARISMA',
            fe: 'FÉ',
            fé: 'FÉ',
            crit_chance_flat: 'CRÍTICO',
            dmg: 'DANO',
            damage: 'DANO',
            attack: 'ATAQUE',
            ataque: 'ATAQUE'
        };

        const k = String(chave || '').toLowerCase();
        return nomes[k] || k.replace(/_/g, ' ').toUpperCase();
    }

    if (statsDoItem && Object.keys(statsDoItem).length > 0) {
        for (const [key, valObj] of Object.entries(statsDoItem)) {
            let val = valObj;

            if (typeof valObj === 'object' && valObj !== null) {
                if (valObj.value !== undefined) val = valObj.value;
                else if (valObj.valor !== undefined) val = valObj.valor;
                else if (valObj.min !== undefined && valObj.max !== undefined) val = `${valObj.min}-${valObj.max}`;
                else continue;
            }

            if (val === undefined || val === null || val === '') continue;

            const kLower = key.toLowerCase();

            // Se tiver vários atributos, esconde o dmg espelhado para não poluir.
            if (kLower === 'dmg' && Object.keys(statsDoItem).length > 1) continue;

            const emoji = mapEmojis[kLower] || '✨';
            const nomeStat = nomeBonitoStat(key);

            const prefixo = String(val).includes('-') ? '' : '+';

            statsHtml += `
                <span style="background: #020617; padding: 4px 8px; border-radius: 6px; font-size: 0.8em; color: #fff; border: 1px solid #3f3f46; box-shadow: 0 2px 4px rgba(0,0,0,0.5);">
                    ${emoji} ${nomeStat}: ${prefixo}${val}
                </span>
            `;
        }
    } else if (['weapon', 'armor', 'helmet', 'boots', 'ring', 'necklace', 'earring', 'equipamento', 'tool', 'arma', 'armadura', 'lenhador', 'minerador', 'colhedor', 'esfolador', 'ferreiro', 'armeiro', 'alfaiate', 'joalheiro', 'curtidor'].includes(t)) {
        statsHtml = `<span style="color: #64748b; font-size: 0.8em;">Sem atributos base</span>`;
    }

    const bonusFerramentaHtml = gerarHtmlBonusTempoFerramentaPerfil(itemData);

    if (bonusFerramentaHtml) {
        if (statsHtml.includes("Sem atributos base")) {
            statsHtml = "";
        }

        statsHtml += bonusFerramentaHtml;
    }

    document.getElementById('modal-item-stats').innerHTML = statsHtml;

    let botoesHtml = '';

    // 👇 MÁGICA DA DURABILIDADE ENTRA AQUI 👇
    if (
        [
            'weapon',
            'armor',
            'helmet',
            'boots',
            'ring',
            'necklace',
            'earring',
            'equipamento',
            'tool',
            'arma',
            'armadura',
            'lenhador',
            'minerador',
            'colhedor',
            'esfolador',
            'ferreiro',
            'armeiro',
            'alfaiate',
            'joalheiro',
            'curtidor'
        ].includes(t)
        &&
        itemData.durability
        &&
        Array.isArray(itemData.durability)
    ) {
        const atual = itemData.durability[0];
        const maximo = itemData.durability[1];
        const porc = (atual / maximo) * 100;
        const corBarra = porc > 50 ? '#2ecc71' : (porc > 20 ? '#f1c40f' : '#e74c3c');

        const durHtml = `
            <div style="width: 100%; margin-top: 10px; margin-bottom: 10px; text-align: left;">
                <div style="display: flex; justify-content: space-between; font-size: 0.75em; color: #94a3b8; margin-bottom: 3px; font-weight: bold;">
                    <span>DURABILIDADE</span>
                    <span>${atual} / ${maximo}</span>
                </div>
                <div style="width: 100%; height: 6px; background: #020617; border-radius: 3px; border: 1px solid #334155;">
                    <div style="width: ${porc}%; height: 100%; background: ${corBarra}; border-radius: 3px; transition: width 0.3s;"></div>
                </div>
            </div>
        `;
        statsHtml = durHtml + statsHtml; // Adiciona a barra em cima dos atributos
    }

    document.getElementById('modal-item-stats').innerHTML = statsHtml;

    
    // 👇 BOTÃO DE CONSERTAR (Aparece se o item estiver gasto e o jogador tiver o pergaminho) 👇
    const temPergaminho = window.perfilDadosGlobais.inventario.some(i => i.base_id === 'pergaminho_durabilidade' || i.id === 'pergaminho_durabilidade');
    if (
        [
            'weapon',
            'armor',
            'helmet',
            'boots',
            'ring',
            'necklace',
            'earring',
            'equipamento',
            'tool',
            'arma',
            'armadura',
            'lenhador',
            'minerador',
            'colhedor',
            'esfolador',
            'ferreiro',
            'armeiro',
            'alfaiate',
            'joalheiro',
            'curtidor'
        ].includes(t)
        &&
        itemData.durability
        &&
        itemData.durability[0] < itemData.durability[1]
        &&
        temPergaminho
    ) {
        botoesHtml += `<button onclick="repararFerramentaAPI('${itemData.id}')" style="width: 100%; padding:10px; background: #ca8a04; color:black; border:none; border-radius:4px; font-weight:bold; cursor:pointer; margin-bottom: 8px;">CONSERTAR (1x 📜)</button>`;
    }
    
    // 👇 MÁGICA 2: RECONHECIMENTO INFALÍVEL DE POÇÕES 👇
    if (origem === 'mochila' || origem === 'inventario') {
        
        if (['weapon', 'armor', 'helmet', 'boots', 'ring', 'necklace', 'earring', 'equipamento', 'tool', 'arma', 'armadura', 'lenhador', 'minerador', 'colhedor', 'esfolador', 'ferreiro', 'armeiro', 'alfaiate', 'joalheiro', 'curtidor'].includes(t)) {
            botoesHtml = `<button onclick="usarOuEquiparItem('${itemData.id}')" style="flex:1; padding:10px; background: linear-gradient(180deg, #27ae60 0%, #1e8449 100%); color:white; border:1px solid #2ecc71; border-radius:4px; font-weight:bold; cursor:pointer;">Equipar</button>`;
        } 
        else if (idReal.includes('pocao') || nomeLower.includes('poção') || ['potion'].includes(t)) {
            botoesHtml = `
                <button onclick="equiparPocaoAtalho('${idReal}', 'hp')" style="flex:1; padding:10px; background: linear-gradient(180deg, #c0392b 0%, #922b21 100%); color:white; border:1px solid #e74c3c; border-radius:4px; font-weight:bold; cursor:pointer;">Slot ❤️</button>
                <button onclick="equiparPocaoAtalho('${idReal}', 'mp')" style="flex:1; padding:10px; background: linear-gradient(180deg, #2980b9 0%, #1f618d 100%); color:white; border:1px solid #3498db; border-radius:4px; font-weight:bold; cursor:pointer;">Slot 💧</button>
            `;
        }
        else if (t === 'reagent') {

            botoesHtml = `
                <div style="
                    width:100%;
                    padding:10px;
                    margin-bottom:8px;
                    background:rgba(59,130,246,0.08);
                    border:1px dashed #3b82f6;
                    color:#93c5fd;
                    font-size:0.85em;
                    border-radius:4px;
                    font-weight:bold;
                    text-align:center;
                ">
                    🧪 Ingrediente de receita.
                    Use este item em Alquimia ou fabricação.
                </div>
            `;

        }
        else if (
            [
                'consumable',
                'scroll',
                'consumivel',
                'chest',
                'box',
                'especial'
            ].includes(t)
        ) {

            botoesHtml = `
                <button
                    onclick="consumirItemDireto('${itemData.id}', '${idReal}')"
                    style="
                        flex:1;
                        padding:10px;
                        background:linear-gradient(180deg,#8e44ad 0%,#732d91 100%);
                        color:white;
                        border:1px solid #9b59b6;
                        border-radius:4px;
                        font-weight:bold;
                        cursor:pointer;
                    "
                >
                    Usar Item
                </button>
            `;
        }
        else {
            botoesHtml = `<div style="width: 100%; padding: 10px; margin-bottom: 8px; background: rgba(241, 196, 15, 0.1); border: 1px dashed #f1c40f; color: #f1c40f; font-size: 0.85em; border-radius: 4px; font-weight: bold; text-align: center;">🛠️ Leve este item a um NPC (Ferreiro, Alquimista...) para utilizá-lo.</div>`;
        }
    } else if (origem === 'equipado') {
        botoesHtml = `<button onclick="desequiparItem('${itemData.slot}')" style="flex:1; padding:10px; background: linear-gradient(180deg, #c0392b 0%, #922b21 100%); color:white; border:1px solid #e74c3c; border-radius:4px; font-weight:bold; cursor:pointer;">Remover</button>`;
    }
    
    botoesHtml += `<button onclick="fecharModalItem()" style="flex:1; padding:10px; background: linear-gradient(180deg, #334155 0%, #1e293b 100%); color:white; border:1px solid #475569; border-radius:4px; font-weight:bold; cursor:pointer;">Fechar</button>`;
    
    document.getElementById('modal-item-acoes').innerHTML = botoesHtml;
    document.getElementById('modal-item').style.display = 'flex';
}

window.fecharModalItem = function() {
    document.getElementById('modal-item').style.display = 'none';
}

window.distribuirPonto = async function(stat) {
    const charId = localStorage.getItem("jogadorEldoraID");
    if (!charId) return;

    if (window.__distribuindoPontoPerfil) return;
    window.__distribuindoPontoPerfil = true;

    const abaAntes = window.perfilAbaAtual || 'status';

    try {
        const res = await fetch('/api/personagem/distribuir_ponto', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: charId, stat: stat })
        });

        const data = await res.json();

        if (!res.ok || !data.sucesso) {
            const msg = data.erro || "Erro ao distribuir ponto.";
            if (window.alertaEldora) window.alertaEldora("Atributos", msg, "erro");
            else alert("Aviso: " + msg);
            return;
        }

        // Atualiza cache local para a aba não parecer travada antes do reload.
        if (window.perfilDadosGlobais) {
            window.perfilDadosGlobais.pontos_livres = data.pontos_livres;
            window.perfilDadosGlobais.status = data.status || window.perfilDadosGlobais.status;
            window.perfilDadosGlobais.esquiva = data.esquiva ?? window.perfilDadosGlobais.esquiva;
            window.perfilDadosGlobais.atk_duplo = data.atk_duplo ?? window.perfilDadosGlobais.atk_duplo;
            window.perfilDadosGlobais.hp_atual = data.hp_atual ?? window.perfilDadosGlobais.hp_atual;
            window.perfilDadosGlobais.hp_max = data.hp_max ?? window.perfilDadosGlobais.hp_max;
            window.perfilDadosGlobais.mp_atual = data.mp_atual ?? window.perfilDadosGlobais.mp_atual;
            window.perfilDadosGlobais.mp_max = data.mp_max ?? window.perfilDadosGlobais.mp_max;
        }

        await carregarMeuPerfil();
        alternarAbaPerfil(abaAntes);

        if (window.atualizarHudCircular) window.atualizarHudCircular();

    } catch(e) {
        if (window.alertaEldora) window.alertaEldora("Erro", e.message, "erro");
        else alert("⚠️ ERRO: " + e.message);
    } finally {
        window.__distribuindoPontoPerfil = false;
    }
}

window.desequiparItem = async function(slot) {
    fecharModalItem();
    const charId = localStorage.getItem("jogadorEldoraID");
    try {
        const res = await fetch('/api/personagem/desequipar', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ user_id: charId, slot: slot }) });
        const data = await res.json();
        if(data.sucesso) { 
            carregarMeuPerfil(); 
            setTimeout(() => alternarAbaPerfil('equips'), 200); 
            
            // ⚡ SINCRONIA FINA: Força a atualização imediata dos HUDs
            if (window.atualizarHudCircular) window.atualizarHudCircular();
            if (window.carregarDadosDoHUD && document.getElementById('hud-status-flutuante').style.display === 'block') {
                window.carregarDadosDoHUD();
            }
        } else { alert("Aviso: " + data.erro); }
    } catch(e) { alert("⚠️ ERRO: " + e.message); }
}

// 👉 ROTA ANTIGA (APENAS PARA ESPADAS E ARMADURAS)
window.usarOuEquiparItem = async function(itemId) {
    fecharModalItem();
    const charId = localStorage.getItem("jogadorEldoraID");
    try {
        const res = await fetch('/api/personagem/equipar', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ user_id: charId, item_id: itemId }) });
        const data = await res.json();
        if(data.sucesso) { 
            carregarMeuPerfil(); 
            setTimeout(() => alternarAbaPerfil('equips'), 300); 
            
            // ⚡ SINCRONIA FINA: Força a atualização imediata dos HUDs
            if (window.atualizarHudCircular) window.atualizarHudCircular();
            if (window.carregarDadosDoHUD && document.getElementById('hud-status-flutuante').style.display === 'block') {
                window.carregarDadosDoHUD();
            }
        } else { alert("Aviso: " + data.erro); }
    } catch(e) { alert("⚠️ ERRO: " + e.message); }
}

// ==========================================
// ALERTA ÉPICO CUSTOMIZADO
// ==========================================
window.alertaEldora = function(titulo, mensagem, tipo = 'sucesso') {
    let modal = document.getElementById('modal-alerta-eldora');
    if (!modal) {
        const html = `
            <div id="modal-alerta-eldora" style="display:none; position:fixed; top:0; left:0; width:100%; height:100%; background:rgba(0,0,0,0.85); z-index:20000; justify-content:center; align-items:center; backdrop-filter: blur(4px);">
                <div id="alerta-eldora-box" style="background: linear-gradient(135deg, #1a120b, #0a0704); width: 85%; max-width: 320px; border-radius: 12px; border: 2px solid #b8860b; padding: 25px 20px; text-align: center; box-shadow: inset 0 0 20px rgba(0,0,0,0.8), 0 10px 25px rgba(0,0,0,0.9);">
                    <div id="alerta-eldora-icone" style="font-size: 3.5em; margin-bottom: 10px;">✨</div>
                    <h3 id="alerta-eldora-titulo" style="margin: 0 0 10px 0; color: #2ecc71; font-size: 1.4em; font-family: 'Cinzel', serif; text-transform: uppercase;">Sucesso</h3>
                    <p id="alerta-eldora-msg" style="color: #b0a084; font-size: 0.95em; margin-bottom: 25px; line-height: 1.4;">Mensagem</p>
                    <button onclick="document.getElementById('modal-alerta-eldora').style.display='none'" style="width: 100%; padding: 12px; background: linear-gradient(180deg, #334155 0%, #1e293b 100%); color: white; border: 1px solid #475569; border-radius: 6px; font-weight: bold; cursor: pointer; font-family: 'Cinzel', serif; text-transform: uppercase;">Entendido</button>
                </div>
            </div>`;
        document.body.insertAdjacentHTML('beforeend', html);
        modal = document.getElementById('modal-alerta-eldora');
    }

    const iconeEl = document.getElementById('alerta-eldora-icone');
    const tituloEl = document.getElementById('alerta-eldora-titulo');
    const boxEl = document.getElementById('alerta-eldora-box');
    
    document.getElementById('alerta-eldora-msg').innerText = mensagem;
    tituloEl.innerText = titulo;

    if (tipo === 'sucesso') {
        iconeEl.innerText = '✨'; iconeEl.style.textShadow = '0 0 15px rgba(46, 204, 113, 0.6)';
        tituloEl.style.color = '#2ecc71'; boxEl.style.borderColor = '#2ecc71';
    } else if (tipo === 'erro') {
        iconeEl.innerText = '❌'; iconeEl.style.textShadow = '0 0 15px rgba(231, 76, 60, 0.6)';
        tituloEl.style.color = '#e74c3c'; boxEl.style.borderColor = '#e74c3c';
    } else if (tipo === 'pocao') {
        iconeEl.innerText = '🧪'; iconeEl.style.textShadow = '0 0 15px rgba(52, 152, 219, 0.6)';
        tituloEl.style.color = '#3498db'; boxEl.style.borderColor = '#3498db';
    }
    modal.style.display = 'flex';
};
// 👉 FUNÇÃO PARA USAR PERGAMINHOS E CAIXAS
window.consumirItemDireto = async function(itemId, baseId) {
    fecharModalItem();
    const charId = localStorage.getItem("jogadorEldoraID");
    try {
        const res = await fetch('/api/personagem/usar_item', { 
            method: 'POST', headers: { 'Content-Type': 'application/json' }, 
            body: JSON.stringify({ user_id: charId, item_id: itemId, base_id: baseId }) 
        });
        const data = await res.json();
        if(data.sucesso) { 
            carregarMeuPerfil(); 
            if(window.alertaEldora) window.alertaEldora("Magia Libertada!", data.msg || "Item usado com sucesso!", "sucesso");
        } else { 
            if(window.alertaEldora) window.alertaEldora("Aviso", data.erro, "erro"); 
        }
    } catch(e) { console.error(e); }
}

// 👉 FUNÇÃO PARA BEBER A POÇÃO PELO BOTÃO DO MAPA
window.usarPocaoRapida = async function(tipoSlot) {
    const charId = localStorage.getItem("jogadorEldoraID");
    if (!charId) return;

    try {
        const res = await fetch('/api/personagem/usar_pocao_rapida', { 
            method: 'POST', 
            headers: { 'Content-Type': 'application/json' }, 
            body: JSON.stringify({ user_id: charId, tipo: tipoSlot }) 
        });
        const data = await res.json();
        
        if (data.sucesso) {
            // Se estiver no mapa, faz o texto verde/azul flutuar!
            if (window.jogoEldora) {
                const cena = window.jogoEldora.scene.getScene('MapaScene');
                if (cena && cena.player) {
                    let textoCura = cena.add.text(cena.player.x, cena.player.y - 40, `+${data.cura}`, {
                        fontFamily: 'Cinzel, Arial', fontSize: '20px', color: data.cor, 
                        stroke: '#000', strokeThickness: 4, fontStyle: 'bold'
                    }).setOrigin(0.5).setDepth(200);

                    cena.tweens.add({ targets: textoCura, y: textoCura.y - 50, alpha: 0, duration: 1500, onComplete: () => textoCura.destroy() });
                }
            }
            if (typeof carregarMeuPerfil === 'function') carregarMeuPerfil();
            if (typeof atualizarHudCircular === 'function') atualizarHudCircular();
        } else {
            if (window.alertaEldora) window.alertaEldora("Cinto de Poções", data.erro, "erro");
            else alert(data.erro);
        }
    } catch(e) { console.error("Erro ao beber poção:", e); }
}

// 👉 EQUIPAR POÇÃO NO CINTO (ATALHOS)
window.equiparPocaoAtalho = async function(itemId, tipoPocao) {
    fecharModalItem();
    const charId = localStorage.getItem("jogadorEldoraID");
    try {
        const res = await fetch('/api/personagem/equipar_pocao', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: charId, item_id: itemId, tipo: tipoPocao })
        });
        const data = await res.json();
        if(data.sucesso) {
            carregarMeuPerfil();
            if(window.alertaEldora) {
                window.alertaEldora("Cinto de Poções", `Poção equipada no Slot ${tipoPocao.toUpperCase()}!`, "pocao");
            }
        } else {
            if(window.alertaEldora) window.alertaEldora("Erro", data.erro, "erro");
        }
    } catch(e) {
        console.error(e);
    }
}

// ==========================================
// SISTEMA DE GRIMÓRIO E SKILLS (perfil.js)
// ==========================================

// 1. Função para renderizar a Aba de Magias (chama isto quando clicares na aba "Magias" do inventário)
window.renderizarAbaMagias = function() {
    const p = window.perfilDadosGlobais;
    if (!p) return;

    // Assumindo que tens uma div principal onde os itens do inventário aparecem
    const container = document.getElementById('grid-inventario-conteudo'); 
    if (!container) return;

    container.innerHTML = '';
    container.style.display = 'grid';
    container.style.gridTemplateColumns = 'repeat(auto-fill, minmax(65px, 1fr))';
    container.style.gap = '12px';
    container.style.padding = '15px';

    const dbSkills = p.database_skills || {};
    const minhasSkills = p.skills_desbloqueadas || {};
    const skillsEquipadas = p.skills_equipadas || {};

    // Mapeamento inverso para saber rapidamente em que slot a magia está
    let mapEquipadas = {};
    for (let i = 1; i <= 5; i++) {
        if (skillsEquipadas[`slot_${i}`]) {
            mapEquipadas[skillsEquipadas[`slot_${i}`]] = i;
        }
    }

    let encontrouSkill = false;

    for (const [skillId, skillDataPlayer] of Object.entries(minhasSkills)) {
        encontrouSkill = true;
        const infoDb = dbSkills[skillId] || {};
        const nomeIcone = infoDb.icon || 'default_skill';
        const imgUrl = `/static/assets/sprites/skills/${nomeIcone}.png`;
        const slotEquipado = mapEquipadas[skillId]; // Devolve 1 a 5 se estiver equipada

        // O Quadrado Base
        const quadrado = document.createElement('div');
        quadrado.style = "width:65px; height:65px; background:#0f172a; border:2px solid #334155; border-radius:8px; display:flex; align-items:center; justify-content:center; cursor:pointer; position:relative; transition: transform 0.1s;";
        
        quadrado.onmouseover = () => quadrado.style.transform = "scale(1.05)";
        quadrado.onmouseout = () => quadrado.style.transform = "scale(1)";

        // Se estiver equipada, o quadrado ganha uma aura mágica (roxa)
        if (slotEquipado) {
            quadrado.style.borderColor = "#8b5cf6";
            quadrado.style.boxShadow = "0 0 12px rgba(139, 92, 246, 0.4)";
        }

        // A Imagem Redonda no centro
        const imgContainer = document.createElement('div');
        imgContainer.style = "width:50px; height:50px; border-radius:50%; overflow:hidden; border:2px solid #1e293b; background:#000;";

        const img = document.createElement('img');
        img.src = imgUrl;
        img.style = "width:100%; height:100%; object-fit:cover;";
        imgContainer.appendChild(img);
        quadrado.appendChild(imgContainer);

        // Indicador numérico do Slot
        if (slotEquipado) {
            const badge = document.createElement('div');
            badge.innerHTML = `S${slotEquipado}`;
            badge.style = "position:absolute; bottom:-6px; right:-6px; background:#8b5cf6; color:white; font-size:11px; font-weight:bold; padding:2px 6px; border-radius:8px; border:2px solid #0f172a;";
            quadrado.appendChild(badge);
        }

        quadrado.onclick = () => window.abrirModalSkillDetalhes(skillId, infoDb, slotEquipado);
        container.appendChild(quadrado);
    }

    if (!encontrouSkill) {
        container.innerHTML = `<div style="color:#94a3b8; font-style:italic; grid-column: 1 / -1; text-align:center; padding-top:30px; font-family:'Cinzel', serif;">O teu grimório está vazio.</div>`;
    }
};

// 3. Lógica Inteligente para Encontrar Espaço
window.iniciarEquiparSkill = function(skillId) {
    const p = window.perfilDadosGlobais;
    const equipadas = p.skills_equipadas || {};
    
    let slotLivre = null;
    for (let i = 1; i <= 5; i++) {
        if (!equipadas[`slot_${i}`] || equipadas[`slot_${i}`] === "") {
            slotLivre = i;
            break;
        }
    }

    if (slotLivre) {
        // Se encontrou espaço, equipa imediatamente
        window.processarEquiparSkill(skillId, slotLivre);
    } else {
        // Se está tudo cheio, transforma a área de botões numa seleção de substituição
        const areaBotoes = document.getElementById('area-botoes-skill');
        let htmlSlots = `<div style="font-size:12px; margin-bottom:10px; text-align:center; color:#fbbf24; font-weight:bold;">Sem espaço livre. Qual magia queres substituir?</div><div style="display:flex; justify-content:space-between;">`;
        
        for (let i = 1; i <= 5; i++) {
            const idEquipada = equipadas[`slot_${i}`];
            const db = p.database_skills || {};
            const info = db[idEquipada] || {};
            const iconeInfo = info.icon || 'default_skill';
            const url = `/static/assets/sprites/skills/${iconeInfo}.png`;

            htmlSlots += `
                <div onclick="window.processarEquiparSkill('${skillId}', ${i})" style="width:45px; height:45px; border-radius:50%; background:#0f172a; border:2px solid #ef4444; cursor:pointer; display:flex; justify-content:center; align-items:center; position:relative; transition: transform 0.1s;" onmouseover="this.style.transform='scale(1.1)'" onmouseout="this.style.transform='scale(1)'" title="${info.display_name || 'Substituir'}">
                    <img src="${url}" style="width:35px; height:35px; border-radius:50%; object-fit:cover;">
                    <span style="position:absolute; bottom:-8px; background:#000; font-size:10px; border-radius:6px; padding:1px 5px; border:1px solid #475569;">S${i}</span>
                </div>
            `;
        }
        htmlSlots += `</div>`;
        areaBotoes.innerHTML = htmlSlots;
    }
};

// 4. Conexão com o Backend (Python)
window.processarEquiparSkill = async function(skillIdOuVazio, slot) {
    const user_id = localStorage.getItem("jogadorEldoraID");
    try {
        const res = await fetch('/api/equipar_skill', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: user_id, skill_id: skillIdOuVazio, slot: slot })
        });
        
        const data = await res.json();
        if(data.sucesso) {
            // Fecha a janela
            const modal = document.getElementById('modal-skill-detalhes');
            if (modal) modal.remove();
            
            // Recarrega o perfil inteiro para atualizar a UI
            if (typeof window.carregarMeuPerfil === 'function') {
                await window.carregarMeuPerfil();
            }
            
            // Se tiveres um sistema de alertas
            if (window.alertaEldora) {
                const acaoTxt = skillIdOuVazio ? "equipada no" : "removida do";
                window.alertaEldora("Grimório Atualizado", `Magia ${acaoTxt} Slot ${slot}.`, "sucesso");
            }
        }
    } catch(e) {
        console.error("Erro ao equipar magia:", e);
    }
};

// ==========================================
// 🛠️ FUNÇÃO PARA CONSERTAR A FERRAMENTA
// ==========================================
window.repararFerramentaAPI = async function(itemUuid) {
    const charId = localStorage.getItem("jogadorEldoraID");
    
    const btn = event.currentTarget;
    const textoOriginal = btn.innerText;
    btn.innerText = "A CONSERTAR... ⏳";
    btn.disabled = true;

    try {
        const res = await fetch('/api/personagem/reparar_ferramenta', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: charId, item_id: itemUuid })
        });
        
        const data = await res.json();
        
        if (data.success) {
            fecharModalItem();
            if (typeof window.carregarMeuPerfil === 'function') window.carregarMeuPerfil();
            
            if (window.alertaEldora) {
                window.alertaEldora("Reparo Concluído!", data.msg, "sucesso");
            } else {
                alert(data.msg);
            }
        } else {
            if (window.alertaEldora) {
                window.alertaEldora("Falha no Reparo", data.error, "erro");
            } else {
                alert(data.error);
            }
            btn.innerText = textoOriginal;
            btn.disabled = false;
        }
    } catch(e) {
        console.error("Erro ao reparar:", e);
        btn.innerText = textoOriginal;
        btn.disabled = false;
    }
};

