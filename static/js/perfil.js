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
    const runeId = String(idReal).trim();
    if (/^runa_(crueldade|precisao|vampiro|rocha|mente|eco|midas|sabio)_(menor|maior|ancestral)$/.test(runeId)) {
        caminhos.push(`${linkBaseNuvem}runas/${runeId}.png`);
    }
    if (typeof item?.icon_url === 'string' && /^(https?:\/\/|\/static\/)/.test(item.icon_url)) {
        caminhos.push(item.icon_url);
    }
    for (const caminho of (window.FORJA_IMAGENS?.[idReal] || [])) {
        caminhos.push(`${linkBaseNuvem}itens/${caminho}`);
    }


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


// Resolve as artes da mochila apenas nesta tela, usando os nomes reais do catálogo público.
window.getCaminhosImagemPerfilEldora = function(item) {
    const base = "https://raw.githubusercontent.com/Eldorabotpy/static-img/main/assets/itens/";
    const cacheVersion = "1122";
    const bruto = String(item?.base_id || item?.item_id || item?.uid || item?.id || "").trim();
    if (!bruto) return [];

    const idSemWork = bruto.replace(/^work_/i, "");
    const ids = [...new Set([bruto, idSemWork, "work_" + idSemWork].filter(Boolean))];
    const caminhos = [];
    const urlIcone = typeof item?.icon_url === "string" ? item.icon_url.trim() : "";
    const iconePlaceholder = /(?:seuusuario|seurepositorio|example\.com|placeholder)/i.test(urlIcone);
    if (!iconePlaceholder && /^(https?:\/\/|\/static\/)/i.test(urlIcone)) caminhos.push(urlIcone);

    const runeId = String(item?.base_id || item?.item_id || item?.uid || item?.id || "").trim();
    if (/^runa_(crueldade|precisao|vampiro|rocha|mente|eco|midas|sabio)_(menor|maior|ancestral)$/.test(runeId)) {
        caminhos.unshift(base + "runas/" + runeId + ".png", "/static/assets/runas/" + runeId.split("_")[1] + ".svg?v=2");
    }

    // Os itens de forja têm chaves "work_*" no índice, embora o base_id não tenha esse prefixo.
    for (const id of ids) {
        const cadastrados = window.FORJA_IMAGENS?.[id];
        if (!Array.isArray(cadastrados)) continue;
        for (const caminho of cadastrados) {
            if (typeof caminho === "string" && caminho) {
                caminhos.push(base + caminho.replace(/^\/?(?:assets\/)?itens\//, "") + "?v=" + cacheVersion);
            }
        }
    }

    const tipo = String(item?.tipo || item?.type || item?.categoria || item?.category || "")
        .trim().toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "");
    const tiposEquipamento = new Set([
        "weapon", "armor", "helmet", "boots", "bota", "botas", "ring", "necklace", "earring",
        "equipamento", "arma", "armadura", "elmo", "anel", "colar", "brinco", "calca", "calcas",
        "luva", "luvas", "peitoral", "capuz", "chapeu", "capacete", "tunica", "manto", "escudo",
        "adaga", "espada", "arco", "cajado", "equipment"
    ]);
    const idPareceEquipamento = /^(?:work_)?(?:espada|adaga|arco|cajado|machado|peitoral|armadura|calca|calcas|bota|botas|luva|luvas|anel|colar|brinco|capuz|chapeu|elmo|capacete|tunica|manto|escudo|capa)(?:_|$)/i.test(bruto);
    const temMapaEquipamento = ids.some(id => (window.FORJA_IMAGENS?.[id] || []).some(path => /^equipamentos\//i.test(path)));
    const equipamento = tiposEquipamento.has(tipo) || tipo === "equipamentos" || idPareceEquipamento || temMapaEquipamento;
    const tiposFerramenta = new Set(["tool", "ferramenta", "lenhador", "minerador", "colhedor", "esfolador", "ferreiro", "armeiro", "alfaiate", "joalheiro", "curtidor"]);
    const tiposUsaveis = new Set(["potion", "pocao", "consumable", "consumivel", "scroll", "pergaminho", "chest", "box", "reagent", "especial", "event_ticket"]);
    const pastas = equipamento ? ["equipamentos"] : tiposFerramenta.has(tipo) ? ["ferramentas", "equipamentos"] : tiposUsaveis.has(tipo) ? ["consumiveis", "materiais"] : ["materiais"];

    for (const pasta of pastas) {
        for (const id of ids) caminhos.push(base + pasta + "/" + id + ".png?v=" + cacheVersion);
    }
    if (equipamento) {
        for (const id of ids) {
            const nomeArquivo = /^work_/i.test(id) ? id : "work_" + id;
            caminhos.push(base + "equipamentos/" + nomeArquivo + ".png?v=" + cacheVersion);
        }
    }

    return [...new Set(caminhos)];
};

window.aplicarImagemPerfilEldora = function(imgEl, item) {
    if (!imgEl) return;
    const caminhos = window.getCaminhosImagemPerfilEldora(item);
    let index = 0;

    imgEl.alt = item?.nome || item?.display_name || item?.base_id || "Item";
    imgEl.onload = function() {
        this.hidden = false;
        if (this.nextElementSibling) {
            this.nextElementSibling.classList.add("eldora-image-fallback");
            this.nextElementSibling.classList.remove("is-visible");
        }
    };
    imgEl.onerror = function() {
        index++;
        if (index < caminhos.length) {
            this.src = caminhos[index];
            return;
        }
        this.onerror = null;
        this.onload = null;
        this.hidden = true;
        if (this.nextElementSibling) {
            this.nextElementSibling.classList.add("eldora-image-fallback", "is-visible");
        }
    };

    if (caminhos.length) imgEl.src = caminhos[0];
    else imgEl.onerror();
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

    const tier = getTierFerramentaPerfil(
        itemData
    );

    const upgrade = getNivelRefinoPerfilItem(
        itemData
    );

    const velocidadePontos =
        getTotalAtributoFerramentaPerfil(
            itemData,
            "velocidade_trabalho"
        );

    // Igual ao backend:
    // T1 0%, T2 5%, T3 10%, T4 15%, T5 20%
    const bonusTier = Math.min(20, Math.max(0, tier - 1) * 5);

    // +1% por melhoria, máximo 10%
    const bonusUpgrade = Math.min(
        10,
        upgrade
    );

    // ⚡ Velocidade de Trabalho:
    // 0.5% por ponto, máximo 10%
    const bonusVelocidade = Math.min(
        10,
        velocidadePontos * 0.5
    );

    // Profissão: 0.5% por nível, máximo 25%
    const bonusProf = Math.min(25, profNivel * 0.5);

    const bonusFerramenta =
        bonusTier
        + bonusUpgrade
        + bonusVelocidade;

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
        <div class="eldora-profile-style-96492c5f">
            <div class="eldora-profile-style-7d747603">
                ⏱️ BÔNUS DE TEMPO
            </div>

            <div class="eldora-profile-style-f1c6317c">
                <div class="eldora-profile-style-665bd398">
                    <span>Profissão</span>
                    <b class="eldora-profile-style-0d75823b">${nomeProf} Nv. ${profNivel}</b>
                </div>

                <div class="eldora-profile-style-665bd398">
                    <span>Redução da profissão</span>
                    <b class="eldora-profile-style-4560323b">-${bonusProf.toFixed(1)}%</b>
                </div>

                <div class="eldora-profile-style-665bd398">
                    <span>Tier da ferramenta</span>
                    <b class="eldora-profile-style-0d75823b">T${tier} / -${bonusTier.toFixed(1)}%</b>
                </div>

                <div class="eldora-profile-style-665bd398">
                    <span>Melhoria da ferramenta</span>
                    <b class="eldora-profile-style-0d75823b">+${upgrade} / -${bonusUpgrade.toFixed(1)}%</b>
                </div>

                <div class="eldora-profile-style-665bd398">
                    <span>⚡ Velocidade de Trabalho</span>
                    <b class="eldora-profile-style-1a0fc93d">
                        +${velocidadePontos}
                        / -${bonusVelocidade.toFixed(1)}%
                    </b>
                </div>

                <div class="eldora-profile-style-4681584a">
                    <span class="eldora-profile-style-52e2d98a">Total aplicado</span>
                    <b class="eldora-profession-total" style="--total-color:${corTotal}">-${totalAplicado.toFixed(1)}%</b>
                </div>
            </div>
        </div>
    `;
}

function getTotalAtributoFerramentaPerfil(
    itemData,
    statProcurado
) {
    if (!itemData) return 0;

    const alvo = normalizarProfissaoPerfil(
        statProcurado
    );

    const blocos = [
        itemData.enchantments,
        itemData.attributes,
        itemData.stats
    ];

    const bloco = blocos.find(
        b =>
            b &&
            typeof b === "object" &&
            Object.keys(b).length > 0
    ) || {};

    let total = 0;

    for (
        const [chave, entrada]
        of Object.entries(bloco)
    ) {

        let statReal = chave;

        if (
            entrada &&
            typeof entrada === "object" &&
            entrada.stat
        ) {
            statReal = entrada.stat;
        } else {
            statReal = String(chave)
                .replace(/_\d+$/, "");
        }

        statReal = normalizarProfissaoPerfil(
            statReal
        );

        if (statReal !== alvo) {
            continue;
        }

        let valor = entrada;

        if (
            entrada &&
            typeof entrada === "object"
        ) {
            valor =
                entrada.value ??
                entrada.valor ??
                0;
        }

        const numero = Number(
            valor || 0
        );

        if (
            Number.isFinite(numero)
        ) {
            total += numero;
        }
    }

    return total;
}
// ==========================================
// FUNÇÃO PRINCIPAL DE CARREGAMENTO DO PERFIL
// ==========================================
async function carregarMeuPerfil() {
    const charId = localStorage.getItem("jogadorEldoraID");
    const conteudo = document.getElementById('perfil-dados');

    if (!charId) {
        document.getElementById('perfil-msg-carregando').innerHTML = "<span class='eldora-profile-style-984655ef'>Nenhum herói selecionado.</span>";
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
        window.dispatchEvent(new CustomEvent("eldora:xp-boost", { detail: p }));

        const classeKey = (p.classe || "aprendiz").toLowerCase();
        const infoClasse = CLASSES_INFO[classeKey] || CLASSES_INFO['aprendiz'];
        let percentXP = Math.min((p.xp / p.xp_max) * 100, 100);
        const percentHP = Math.min(100, Math.max(0, (Number(p.hp_atual) / Math.max(1, Number(p.hp_max))) * 100));
        const percentMP = Math.min(100, Math.max(0, (Number(p.mp_atual) / Math.max(1, Number(p.mp_max))) * 100));

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
            // Cartões responsivos de profissão; os dados e cálculos permanecem os mesmos.
            htmlProfissao = `<section class="perfil-v2-profissoes" aria-label="Profissões do personagem">
                <header class="perfil-v2-prof-cabecalho"><h3>Profissões</h3><span>${listaProfs.length} ${listaProfs.length === 1 ? 'ofício' : 'ofícios'}</span></header>
                <div class="perfil-v2-profissoes-lista">`;

            // Ordena pelo maior nível
            listaProfs.sort((a, b) => (b.level || 1) - (a.level || 1));

            listaProfs.forEach(profInfo => {
                let profNivel = profInfo.level || 1;
                let profXp = profInfo.xp || 0;

                let xpNecessarioProf = 40 + (25 * (profNivel - 1)) + (8 * Math.pow(profNivel - 1, 2));
                let percentProfXP = Math.min((profXp / xpNecessarioProf) * 100, 100);

                let nomeProf = profInfo.display_name || profInfo.nome || profInfo.type || "Aprendiz";

                let keyword = "";
                let imgGenerica = "martelo_ferreiro";
                let isCrafting = false;

                const profStr = (profInfo.key || profInfo.type || "").toLowerCase();

                // 🌿 PROFISSÕES DE COLETA
                if (profStr.includes('lenhador')) { keyword = "machado"; imgGenerica = "machado"; }
                else if (profStr.includes('minerador')) { keyword = "picareta"; imgGenerica = "picareta"; }
                else if (profStr.includes('colhedor')) { keyword = "foice"; imgGenerica = "foice"; }
                else if (profStr.includes('esfolador')) { keyword = "faca"; imgGenerica = "faca"; }
                else if (profStr.includes('alquimista')) { keyword = "frasco"; imgGenerica = "frasco"; }

                // 🔨 PROFISSÕES DE PRODUÇÃO
                else if (profStr.includes('ferreiro')) { keyword = "martelo_ferreiro"; imgGenerica = "martelo_ferreiro"; isCrafting = true; }
                else if (profStr.includes('armeiro')) { keyword = "martelo_armeiro"; imgGenerica = "martelo_armeiro"; isCrafting = true; }
                else if (profStr.includes('alfaiate')) { keyword = "alfaiate"; imgGenerica = "kit_alfaiate"; isCrafting = true; }
                else if (profStr.includes('joalheiro')) { keyword = "joalheiro"; imgGenerica = "kit_joalheiro"; isCrafting = true; }
                else if (profStr.includes('curtidor')) { keyword = "curtidor"; imgGenerica = "kit_curtidor"; isCrafting = true; }

                // 🔥 CÁLCULO DOS BÔNUS 🔥
                let bonusTexto = "";
                if (isCrafting) {
                    bonusTexto = `Tempo de forja: -${(profNivel * 0.5).toFixed(1)}%`;
                } else {
                    bonusTexto = `Drop fixo: +${Math.floor(profNivel / 10)} | Chance dupla: ${(profNivel * 0.5).toFixed(1)}%`;
                }

                let imgFerramentaHtml = '';

                // CORES PADRÃO (Tier 1)
                let corBordaT = "#475569";
                let corFundoT = "#0f172a";
                let glowT = "rgba(0,0,0,0.5)";
                let tierTxt = "T1";

                if (keyword) {
                    const inventario = Array.isArray(p.inventario) ? p.inventario : [];
                    const ferramentaUser = inventario.find(i => i.base_id && i.base_id.toLowerCase().includes(keyword));
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
                    }
                }

                // Cada profissão usa a arte genérica correspondente hospedada no GitHub,
                // mesmo antes de o personagem obter uma ferramenta.
                const imgPath = `https://raw.githubusercontent.com/Eldorabotpy/static-img/main/assets/itens/equipamentos/${imgGenerica}.png`;
                imgFerramentaHtml = `<img src="${imgPath}" alt="Ferramenta de ${nomeProf}" loading="lazy" decoding="async" class="perfil-v2-prof-ferramenta">`;

                htmlProfissao += `
                <article class="perfil-v2-prof-card" style="--prof-cor:${corBordaT}; --prof-fundo:${corFundoT}; --prof-glow:${glowT};">
                    <div class="perfil-v2-prof-topo">
                        <div class="perfil-v2-prof-identidade">
                            <span class="perfil-v2-prof-icone">
                                ${imgFerramentaHtml}
                                <span class="perfil-v2-prof-tier">${tierTxt}</span>
                            </span>
                            <span class="perfil-v2-prof-nome-nivel"><strong>${nomeProf}</strong><small>Nível ${profNivel}</small></span>
                        </div>
                        <span class="perfil-v2-prof-xp">${profXp.toLocaleString('pt-BR')} <small>/ ${xpNecessarioProf.toLocaleString('pt-BR')} XP</small></span>
                    </div>
                    <div class="perfil-v2-prof-trilho"><i style="width:${percentProfXP}%;"></i></div>
                    <div class="perfil-v2-prof-bonus">${bonusTexto}</div>
                </article>`;
            });

            htmlProfissao += `</div></section>`;
        } else {
            // 👇 SE NÃO TIVER PROFISSÃO, MOSTRA ISTO 👇
            htmlProfissao = `
            <section class="perfil-v2-profissoes perfil-v2-profissoes-vazio" aria-label="Profissões do personagem">
                <header class="perfil-v2-prof-cabecalho"><h3>Profissões</h3><span>0 ofícios</span></header>
                <div class="perfil-v2-prof-vazio"><strong>Nenhum ofício aprendido</strong><span>Encontre um Mestre de Guilda para aprender uma profissão.</span></div>
            </section>`;
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

        const urlPerfilAssets = 'https://raw.githubusercontent.com/Eldorabotpy/static-img/main/assets/perfil/';
        const slugEmblemaClasse = ({ cacador: 'arqueiro', aprendiz: 'guerreiro' })[infoClasse.base] || infoClasse.base;
        const emblemaClasseUrl = `${urlPerfilAssets}classes/${slugEmblemaClasse}.png`;

        // ==========================================
        // 4. CONSTRUÇÃO DO HTML DAS ABAS
        // ==========================================

        // --- Status ---
        const imagensStatusGitHub = {
            attack: 'atributo_forca.png',
            defense: 'atributo_defesa.png',
            initiative: 'atributo_agilidade.png',
            luck: 'atributo_sorte.png'
        };
        let htmlStatus = `<div class="eldora-status-grid eldora-profile-style-0ae0d5ee" >`;
        for (const key in p.status) {
            const st = p.status[key];
            const podeUpar = p.pontos_livres > 0 ? `<button onclick="distribuirPonto('${key}')" class="eldora-profile-style-72bf51c5">+</button>` : '';
            const imagemStatus = imagensStatusGitHub[key];
            const iconeStatus = imagemStatus
                ? `<img src="${urlPerfilAssets}${imagemStatus}?v=20261016-2" alt="" loading="lazy">`
                : `<svg viewBox="0 0 32 32" aria-hidden="true" focusable="false"><path d="M16 2 19.7 12.3 30 16l-10.3 3.7L16 30l-3.7-10.3L2 16l10.3-3.7L16 2Z" fill="currentColor"/></svg>`;
            htmlStatus += `
                <div class="eldora-status-card perfil-v2-status-card eldora-profile-style-31e41829" >
                    <div class="perfil-v2-status-identidade"><span class="perfil-status-icone" aria-hidden="true">${iconeStatus}</span><span class="perfil-v2-status-nome eldora-profile-style-b3871c39">${st.nome}</span></div>
                    <div class="eldora-profile-style-3088da11 perfil-v2-status-valor"><strong class="eldora-profile-style-51cfd0f1">${st.valor}</strong>${podeUpar}</div>
                </div>`;
        }
        const percentualEsquiva = Math.max(0, Math.min(100, Number(p.esquiva) || 0));
        const percentualAtkDuplo = Math.max(0, Math.min(100, Number(p.atk_duplo) || 0));
        htmlStatus += `</div>
            <section class="eldora-status-chances perfil-v2-chances" aria-label="Chances secundárias">
                <div class="perfil-v2-chances-titulo">Chances secundárias</div>
                <div class="perfil-v2-chances-grid">
                    <article class="perfil-v2-chance-card is-dodge" aria-label="Esquiva: ${percentualEsquiva}%">
                        <img class="perfil-v2-chance-icone" src="${urlPerfilAssets}atributo_atk_duplo.png?v=20261016-3" alt="" loading="lazy">
                        <div class="perfil-v2-chance-conteudo">
                            <span class="perfil-v2-chance-nome">Esquiva</span>
                            <span class="perfil-v2-chance-descricao">Evita um golpe recebido</span>
                            <strong class="perfil-v2-chance-valor">${percentualEsquiva}%</strong>
                            <span class="perfil-v2-chance-trilho" aria-hidden="true"><span style="width:${percentualEsquiva}%"></span></span>
                        </div>
                    </article>
                    <article class="perfil-v2-chance-card is-double" aria-label="Ataque duplo: ${percentualAtkDuplo}%">
                        <img class="perfil-v2-chance-icone" src="${urlPerfilAssets}atribito_esquiva.png?v=20261016-3" alt="" loading="lazy">
                        <div class="perfil-v2-chance-conteudo">
                            <span class="perfil-v2-chance-nome">Ataque duplo</span>
                            <span class="perfil-v2-chance-descricao">Repete o ataque</span>
                            <strong class="perfil-v2-chance-valor">${percentualAtkDuplo}%</strong>
                            <span class="perfil-v2-chance-trilho" aria-hidden="true"><span style="width:${percentualAtkDuplo}%"></span></span>
                        </div>
                    </article>
                </div>
            </section>`;

        // --- Equipamentos e Slots ---
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

            const corBorda = eq.vazio ? "#334155" : "#f59e0b";
            const corFundo = eq.vazio ? "rgba(15, 23, 42, 0.8)" : "rgba(245, 158, 11, 0.15)";

            let visualItem = eq.vazio ? `<span class="eldora-profile-style-21853e97">${eq.emoji}</span>` :
            `<img data-equip-img="${eq.uid || eq.id || eq.slot}" src="/static/assets/box.png" onerror="this.hidden=true; if(this.nextElementSibling){this.nextElementSibling.classList.add('eldora-image-fallback','is-visible')}" class="eldora-profile-style-008017cb">
            <span class="eldora-profile-style-b7f7a8e4">${eq.icon || eq.emoji || '📦'}</span>`;

            htmlSlots += `
                <div class="eldora-equipment-slot" data-empty="${eq.vazio}" data-slot="${eq.slot}" onclick="${!eq.vazio ? `abrirModalItem('${eq.slot}', 'equipado')` : ''}"
                     >
                    ${visualItem}
                    ${window.renderRuneSockets?.(eq) || ''}
                </div>`;
        });

        if (ferramentasProfissao.length > 0) {
            htmlFerramentas = `
                <div class="eldora-profession-tools eldora-profile-style-841f7e3a" >
                    <div class="eldora-profile-style-be0a0ad8">
                        🛠️ Ferramentas de Profissão
                    </div>

                    <div class="eldora-profile-style-c25e3c96">
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
                        <div class="eldora-profile-style-b5fecb8f">
                            <div style="--progress:${Math.max(0, Math.min(100, porc))}%;--durability-color:${corDur}"></div>
                        </div>
                    `;
                }

                const visualTool = eq.vazio
                    ? `<span class="eldora-profile-style-cf178804">${eq.emoji || '🛠️'}</span>`
                    : `<img data-equip-img="${eq.uid || eq.id || eq.slot}" src="/static/assets/box.png" onerror="this.hidden=true; if(this.nextElementSibling){this.nextElementSibling.classList.add('eldora-image-fallback','is-visible')}" class="eldora-profile-style-30188eda">
                       <span class="eldora-profile-style-950dd573">${eq.icon || eq.emoji || '🛠️'}</span>`;

                htmlFerramentas += `
                    <div class="eldora-tool-slot" data-empty="${eq.vazio}" onclick="${!eq.vazio ? `abrirModalItem('${eq.slot}', 'equipado')` : ''}"
                         title="${eq.nome || nomeProf}"
                         >

                        ${visualTool}

                        <div class="eldora-profile-style-adecf77c">
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
            <div class="eldora-equipment-panel eldora-profile-style-b62ee557" >
                <div class="eldora-equipment-stage eldora-profile-style-ff9781f7" >
                    <div class="eldora-equipment-backdrop eldora-profile-style-83ad1f84" >
                        <img src="${bannerRawUrl}" onerror="this.hidden=true" class="eldora-profile-style-4a466668">
                    </div>
                    <div class="eldora-equipment-avatar eldora-profile-style-4ec5f851" >
                        <img src="${fullBodyImgUrl}" onerror="this.src='${fallbackFullBody}'; this.onerror=null;" class="eldora-profile-style-918da39f">
                    </div>
                    <div class="eldora-equipment-slots eldora-profile-style-d9b56f37" >${htmlSlots}</div>
                </div>

                <button class="eldora-companion-button eldora-profile-style-ca6eb74e" type="button" onclick="window.abrirCodiceHunter().then(() => window.abrirCompanheiros())" >
                    🐾 Companheiro<br><span class="eldora-profile-style-e18a3df1">${p.companion ? `${p.companion.icon} ${p.companion.name} · ${p.companion.form} · Nv. ${p.companion.level}` : 'Nenhum equipado · Abrir Bestiário'}</span>
                </button>
                ${htmlFerramentas}
            </div>`;

        // --- Inventário ---
        let htmlInv = `
            <div class="eldora-inventory-filters eldora-profile-style-494596d6" >
                <button class="eldora-inventory-filter active eldora-profile-style-2cadcdff" onclick="filtrarMochila('todos')" id="btn-filtro-todos" >Todos</button>
                <button class="eldora-inventory-filter eldora-profile-style-9b604a42" onclick="filtrarMochila('equips')" id="btn-filtro-equips" >Equips</button>
                <button class="eldora-inventory-filter eldora-profile-style-9b604a42" onclick="filtrarMochila('materiais')" id="btn-filtro-materiais" >Materiais</button>
                <button class="eldora-inventory-filter eldora-profile-style-9b604a42" onclick="filtrarMochila('usaveis')" id="btn-filtro-usaveis" >Usáveis</button>
            </div>
            <div id="grid-mochila" class="eldora-inventory-grid eldora-profile-style-5bf71092" ></div>
        `;

        // ==========================================
        // 5. INJEÇÃO FINAL NO ECRÃ
        // ==========================================
        conteudo.innerHTML = `
            <section class="eldora-profile-hero perfil-v2-hero" aria-label="Perfil do herói">
                <div class="eldora-profile-hero-shade perfil-v2-sombra eldora-profile-style-c58de097" aria-hidden="true"></div>
                <img class="eldora-profile-hero-avatar perfil-v2-personagem eldora-profile-style-4ffcc85c" src="${fullBodyImgUrl}" alt="${p.classe || infoClasse.nome}" onerror="this.src='${fallbackFullBody}'; this.onerror=null;">
                <div class="eldora-profile-hero-info perfil-v2-identidade eldora-profile-style-93b71188">
                    <h2 class="perfil-v2-nome">${p.nome}</h2>
                    <img class="perfil-v2-emblema-classe" src="${emblemaClasseUrl}" alt="${p.classe || infoClasse.nome}" onerror="this.hidden=true;this.nextElementSibling.style.display='inline-flex';">
                    <span class="perfil-v2-classe-fallback" style="display:none">${infoClasse.emoji} ${p.classe || infoClasse.nome}</span>
                    <span class="perfil-v2-nivel">NÍVEL ${p.level}</span>
                </div>
                <button class="eldora-profile-edit perfil-v2-editar" type="button" onclick="window.perfilVisual.renderizarEdicao()">
                    <span aria-hidden="true">⚙</span> EDITAR VISUAL
                </button>
            </section>

            <section class="eldora-profile-resources perfil-v2-recursos" aria-label="Recursos do personagem">
                <div class="eldora-profile-resource resource-hp perfil-v2-recurso perfil-v2-hp">
                    <img src="${urlPerfilAssets}hp.png" alt="">
                    <div><span>HP</span><strong>${p.hp_atual}<small> / ${p.hp_max}</small></strong></div>
                </div>
                <div class="eldora-profile-resource resource-mp perfil-v2-recurso perfil-v2-mana">
                    <img src="${urlPerfilAssets}mana.png" alt="">
                    <div><span>MP</span><strong>${p.mp_atual}<small> / ${p.mp_max}</small></strong></div>
                </div>
                <div class="eldora-profile-resource resource-gold perfil-v2-recurso perfil-v2-ouro">
                    <img src="${urlPerfilAssets}ouro.png" alt="">
                    <div><span>OURO</span><strong>${p.gold.toLocaleString('pt-BR')}</strong></div>
                </div>
                <div class="eldora-profile-resource resource-gems perfil-v2-recurso perfil-v2-gemas">
                    <img src="${urlPerfilAssets}gemas.png" alt="">
                    <div><span>GEMAS</span><strong>${p.gems.toLocaleString('pt-BR')}</strong></div>
                </div>
            </section>

            <section class="eldora-profile-xp perfil-v2-experiencia" aria-label="Experiência do personagem">
                <span class="perfil-v2-icone-exp" aria-label="EXP">EXP</span>
                <div class="perfil-v2-exp-conteudo">
                    <div class="perfil-v2-exp-cabecalho"><strong>Experiência</strong><span>${p.xp.toLocaleString('pt-BR')} / ${p.xp_max.toLocaleString('pt-BR')}</span></div>
                    <div class="perfil-v2-exp-trilho"><i style="width:${percentXP}%;"></i></div>
                    <small class="perfil-v2-exp-percentual">${Math.floor(percentXP)}% até o próximo nível</small>
                </div>
            </section>

            <div class="eldora-profile-professions">${htmlProfissao}</div>
            <nav class="eldora-profile-tabs" aria-label="Abas do perfil">
                <button onclick="alternarAbaPerfil('status')" id="btn-perf-status" class="eldora-profile-tab is-active"><img src="${urlPerfilAssets}aba_atributos.png?v=20261016-1" alt="" loading="lazy"><span>Atributos</span>${p.pontos_livres > 0 ? `<span class="eldora-points-badge">${p.pontos_livres}</span>` : ''}</button>
                <button onclick="alternarAbaPerfil('equips')" id="btn-perf-equips" class="eldora-profile-tab"><img src="${urlPerfilAssets}aba_equipamentos.png?v=20261016-1" alt="" loading="lazy"><span>Equips</span></button>
                <button onclick="alternarAbaPerfil('inv')" id="btn-perf-inv" class="eldora-profile-tab"><img src="${urlPerfilAssets}aba_mochila.png?v=20261016-1" alt="" loading="lazy"><span>Mochila</span></button>
                <button onclick="alternarAbaPerfil('magias')" id="btn-perf-magias" class="eldora-profile-tab"><img src="${urlPerfilAssets}aba_magias.png?v=20261016-1" alt="" loading="lazy"><span>Magias</span></button>
            </nav>

            <section id="conteudo-perf-status" class="eldora-profile-pane eldora-status-pane eldora-profile-style-048b9a2b" >
                <header class="eldora-pane-heading"><span>PERSONAGEM</span><h3>Atributos do herói</h3></header>
                ${htmlStatus}
            </section>
            <section id="conteudo-perf-equips" class="eldora-profile-pane eldora-equipment-pane eldora-profile-style-f2892a2e" >
                <header class="eldora-pane-heading"><span>PREPARAÇÃO</span><h3>Equipamentos</h3></header>
                ${htmlEquips}
            </section>
            <section id="conteudo-perf-inv" class="eldora-profile-pane eldora-inventory-pane eldora-profile-style-f2892a2e" >
                <header class="eldora-pane-heading"><span>ITENS DO HERÓI</span><h3>Mochila</h3></header>
                ${htmlInv}
            </section>
            <section id="conteudo-perf-magias" class="eldora-profile-pane eldora-spells-pane eldora-profile-style-f2892a2e" >
                <header class="eldora-pane-heading"><span>GRIMÓRIO</span><h3>Magias</h3></header>
            </section>
        `;
        const heroProfile = conteudo.querySelector(".eldora-profile-hero");
        if (heroProfile) heroProfile.style.setProperty("--eldora-profile-banner", bannerImgCss);

        setTimeout(() => {
            document.querySelectorAll("[data-equip-img]").forEach(img => {
                const uid = img.getAttribute("data-equip-img");

                const eq = (window.perfilDadosGlobais.equipamentos || []).find(e =>
                    String(e.uid || e.id || e.slot) === String(uid)
                );

                if (eq && typeof window.aplicarImagemItemEldora === "function") {
                    window.aplicarImagemPerfilEldora(img, eq);
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

    ['status', 'equips', 'inv', 'skins', 'magias'].forEach(id => {
        const pane = document.getElementById('conteudo-perf-' + id);
        if (pane) pane.classList.remove('is-active');
    });

    ['btn-perf-status', 'btn-perf-equips', 'btn-perf-inv', 'btn-perf-skins', 'btn-perf-magias'].forEach(b => {
        let btn = document.getElementById(b);
        if(btn) {
            btn.classList.remove('is-active');
        }
    });

    let abaConteudo = document.getElementById(`conteudo-perf-${abaID}`);
    if (abaConteudo) abaConteudo.classList.add('is-active');

    let abaBotao = document.getElementById(`btn-perf-${abaID}`);
    if(abaBotao) {
        abaBotao.classList.add('is-active');
    }

    if (abaID === 'equips' && window._avatarAtualEldora) {
        const imgCentro = document.getElementById('avatar-equip-tab');
        if (imgCentro) imgCentro.src = window._avatarAtualEldora;
    }

    if (abaID === 'skins') carregarMenuSkins();
    if (abaID === 'magias') carregarMenuMagias();
    if (abaID === 'inv') filtrarMochila(window.perfilFiltroMochilaAtual || 'todos');
}

// --- FUNÇÃO PARA DESENHAR AS SKINS ---
window.carregarMenuSkins = function() {
    const p = window.perfilDadosGlobais;
    const container = document.getElementById('conteudo-perf-skins');
    if (!p || !container) return;

    let html = `<div class="eldora-profile-style-90d64983">`;
    const isEquipadaPadrao = !p.equipped_skin;
    html += `
        <div onclick="equiparNovaSkin(null)" class="eldora-skin-card ${isEquipadaPadrao ? 'is-equipped' : ''}">
            <div class="eldora-profile-style-c11effc7">👤</div>
            <div class="eldora-profile-style-c1b8e467">Padrão</div>
        </div>`;

    if (p.skins_disponiveis && p.skins_disponiveis.length > 0) {
        p.skins_disponiveis.forEach(skin => {
            const isEquipada = p.equipped_skin === skin.id;
            html += `
                <div onclick="equiparNovaSkin('${skin.id}')" class="eldora-skin-card ${isEquipada ? 'is-equipped' : ''}">
                    <div class="eldora-profile-style-c11effc7">🎨</div>
                    <div class="eldora-profile-style-c1b8e467">${skin.nome}</div>
                </div>`;
        });
    } else {
        html += `<div class="eldora-profile-style-ad7f0944">Nenhuma aparência extra encontrada.</div>`;
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
            window.avisoEldora("Erro: " + data.erro);
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
    container.innerHTML = `<p class="eldora-profile-style-28886218">A abrir o Grimório...</p>`;

    try {
        const res = await fetch(`/api/personagem/${charId}?t=${new Date().getTime()}`);
        const pdata = await res.json();

        window._skillsDataTemp = pdata.database_skills || {};
        window._skillsEquipadasTemp = pdata.skills_equipadas || {};
        const skillsPossuidas = pdata.skills_desbloqueadas || {};

        let html = `<div class="eldora-profile-style-801160c3">
                        <h4 class="eldora-profile-style-593914d0">Grimório de Eldora</h4>`;

        if (Object.keys(skillsPossuidas).length === 0) {
            html += `<p class="eldora-profile-style-111cc8c9">Nenhuma habilidade aprendida ainda. Fale com a Arquimaga Selene no nível 17.</p>`;
        } else {
            html += `<div class="eldora-profile-style-6b96c2c2">`;

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
                         class="eldora-spell-card ${slotEquipado ? 'is-equipped' : ''}">

                        ${slotEquipado ? `<span class="eldora-profile-style-15475bc2">S${slotEquipado}</span>` : ""}

                        <div class="eldora-profile-style-29af6337">
                            <img src="${iconPath}" onerror="this.src='${fallbackIcon}'" class="eldora-profile-style-4a466668">
                        </div>
                    </div>`;
            }
            html += `</div>
                     <p class="eldora-profile-style-84043008">Clique para equipar nos slots de combate</p>`;
        }

        container.innerHTML = html + `</div>`;
    } catch (e) {
        container.innerHTML = `<p class="eldora-profile-style-f48620d5">Erro ao canalizar o Grimório.</p>`;
    }
}

// 2. Janela Modal de Detalhes da Magia (CORREÇÃO DE IMAGEM)
window.abrirModalSkillDetalhes = function(skillId, infoDb, slotAtual) {
    let modal = document.getElementById('modal-skill-detalhes');
    if (modal) modal.remove();

    modal = document.createElement('div');
    modal.id = 'modal-skill-detalhes';
    modal.classList.add('eldora-skill-modal');
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
        areaBotoes = `<button class="eldora-skill-action is-remove" onclick="window.processarEquiparSkill('', ${slotAtual})">Desequipar (Slot ${slotAtual})</button>`;
    } else {
        areaBotoes = `<button class="eldora-skill-action is-equip" onclick="window.iniciarEquiparSkill('${skillId}')" ${!magiaExiste ? 'disabled' : ''}>Equipar</button>`;
    }

    // Adicionei this.onerror=null para evitar que ele quebre de vez se o fallback também falhar
    modal.innerHTML = `
        <div class="eldora-profile-style-3395e2db">
            <div class="eldora-profile-style-8894607e">
                <img src="${imgUrlModal}" onerror="this.onerror=null; this.src='${fallbackIconModal}'" class="eldora-profile-style-2dbd2893">
                <div>
                    <h3 class="eldora-skill-modal-title ${magiaExiste ? '' : 'is-unavailable'}">${nome}</h3>
                    <div class="eldora-profile-style-2ed4b0fd">Mana: <span class="eldora-profile-style-c73cb885">${mana}</span> | Recarga: <span class="eldora-profile-style-e85027a3">${cooldown} turnos</span></div>
                </div>
            </div>
            <div onclick="document.getElementById('modal-skill-detalhes').remove()" class="eldora-profile-style-bc4392d5">×</div>
        </div>
        <div class="eldora-profile-style-bf3d6245">
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
        else { window.avisoEldora("Erro: " + data.erro); }
    } catch(e) {}
}
// ==========================================
// FILTRO E RENDERIZAÇÃO DA MOCHILA (CORRIGIDO)
// ==========================================
window.filtrarMochila = function(filtro) {
    window.perfilFiltroMochilaAtual = filtro || 'todos';
    filtro = window.perfilFiltroMochilaAtual;

    if (!window.perfilDadosGlobais || !window.perfilDadosGlobais.inventario) return;

    const inv = window.perfilDadosGlobais.inventario;
    const grid = document.getElementById('grid-mochila');
    if (!grid) return;

    // Atualiza o visual dos botões de filtro
    ['todos', 'equips', 'materiais', 'usaveis'].forEach(f => {
        const btn = document.getElementById(`btn-filtro-${f}`);
        if (btn) {
            btn.classList.toggle('is-active', f === filtro);
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
        grid.innerHTML = `<div class="eldora-profile-style-21776fc0">Mochila vazia nesta categoria.</div>`;
        return;
    }

    // Pega o caminho base do GitHub
    const linkBaseNuvem = window.CATALOGO_SISTEMA ? "https://raw.githubusercontent.com/Eldorabotpy/static-img/main/assets/" : "/static/assets/";
    const coresRaridade = {
        comum: '#94a3b8', common: '#94a3b8',
        incomum: '#22c55e', uncommon: '#22c55e',
        raro: '#3b82f6', rare: '#3b82f6',
        epico: '#a855f7', epic: '#a855f7',
        lendario: '#eab308', legendary: '#eab308',
        mitico: '#ef4444', mythic: '#ef4444',
        divino: '#f0d48e', divine: '#f0d48e'
    };

    filtrados.forEach(item => {
        // Envia o item inteiro para a bússola decidir


        const raridade = String(item.raridade || 'comum').trim().toLowerCase()
            .normalize('NFD').replace(/[\u0300-\u036f]/g, '');
        const corBorda = coresRaridade[raridade] || '#334155';

        const slotHtml = `
            <div class="eldora-item-slot" onclick="abrirModalItem('${item.id}', 'mochila')"
                 style="--rarity-border:${corBorda}">

                <img data-item-img="${item.id}" src="/static/assets/box.png" onerror="this.hidden=true; if(this.nextElementSibling){this.nextElementSibling.classList.add('eldora-image-fallback','is-visible')}" class="eldora-profile-style-c8590c2b">
                <span class="eldora-profile-style-e6b19889">${item.emoji || '📦'}</span>

                <div class="eldora-item-quantity eldora-profile-style-6a5a7d0d" >
                    x${item.qtd || item.quantidade || 1}
                </div>

                ${window.renderRuneSockets?.(item) || ''}
                ${item.refino > 0 ? `<div class="eldora-item-refinement eldora-profile-style-7acfd725" >+${item.refino}</div>` : ''}
            </div>
        `;
        grid.innerHTML += slotHtml;
        const imgEl = grid.querySelector(`img[data-item-img="${item.id}"]`);
        window.aplicarImagemPerfilEldora(imgEl, item);
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
            <div id="modal-item" class="eldora-profile-style-a210d4af">
                <div class="eldora-profile-style-1d2f3eda">
                    <span onclick="fecharModalItem()" class="eldora-profile-style-84ab6d66">&times;</span>
                    <div id="modal-item-icon" class="eldora-profile-style-4132a818"></div>

                    <h3 id="modal-item-nome" class="eldora-profile-style-f3fd4aeb">Nome</h3>
                    <div id="modal-item-raridade" class="eldora-profile-style-df5f89ff"></div>
                    <p id="modal-item-desc" class="eldora-profile-style-d4d63d08">Descrição</p>
                    <div id="modal-item-stats" class="eldora-profile-style-eeef0f29"></div>
                    <div id="modal-item-acoes" class="eldora-profile-style-7e45cc0e"></div>
                </div>
            </div>`;
        document.body.insertAdjacentHTML('beforeend', modalHtml);
    }

    const refinoTxt = (itemData.refino && itemData.refino > 0) ? ` [+${itemData.refino}]` : '';
    const qtdValor = itemData.qtd || itemData.quantidade || 1;
    const qtdTxt = (origem === 'mochila' || origem === 'inventario') && qtdValor > 1
        ? ` <span class="eldora-profile-style-1b346c3f">(x${qtdValor})</span>`
        : '';

    document.getElementById('modal-item-nome').innerHTML = itemData.nome + refinoTxt + qtdTxt;

    // 👇 MÁGICA 1: BLINDAGEM DE INGLÊS/PORTUGUÊS E IDs 👇
    const t = (itemData.tipo || itemData.type || "").toLowerCase();
    const idReal = itemData.base_id || itemData.item_id || itemData.id || "indefinido";
    const nomeLower = (itemData.nome || itemData.display_name || "").toLowerCase();

    const imgUrl = "/static/assets/box.png";

    document.getElementById('modal-item-icon').innerHTML = `
        <img id="modal-img-item-real"
             src="${imgUrl}"
             onerror="this.hidden=true; if(this.nextElementSibling){this.nextElementSibling.classList.add('eldora-image-fallback','is-visible')}"
             class="eldora-profile-style-f47716cb">
        <span class="eldora-profile-style-6e6fc52f">${itemData.emoji || itemData.icon || '📦'}</span>
    `;

    window.aplicarImagemPerfilEldora(document.getElementById("modal-img-item-real"), itemData);

    document.getElementById('modal-item-desc').innerText = itemData.desc || "Sem descrição.";

    const rari = document.getElementById('modal-item-raridade');
    rari.innerText = itemData.raridade || "Comum";
    const raridadeClasse = String(itemData.raridade || 'comum').toLowerCase().normalize('NFD').replace(/[\\u0300-\\u036f]/g, '').replace(/[^a-z0-9_-]/g, '') || 'comum';
    rari.classList.add('is-rarity-' + raridadeClasse);

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
        'ataque':'⚔️',
        'velocidade_trabalho':'⚡',
        'sorte_oficio':'🍀',
        'maestria':'🔨',
        'resistencia_ferramenta':'🛡️',
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
            ataque: 'ATAQUE',
            velocidade_trabalho: 'VELOCIDADE DE TRABALHO',
            sorte_oficio: 'SORTE DE OFÍCIO',
            maestria: 'MAESTRIA',
            resistencia_ferramenta: 'RESISTÊNCIA DA FERRAMENTA',
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

            const statReal = String(
                (
                    valObj &&
                    typeof valObj === "object" &&
                    valObj.stat
                )
                    ? valObj.stat
                    : kLower.replace(
                        /_\d+$/,
                        ""
                    )
            ).toLowerCase();

            // Se tiver vários atributos,
            // esconde o dmg espelhado.
            if (
                statReal === 'dmg' &&
                Object.keys(
                    statsDoItem
                ).length > 1
            ) {
                continue;
            }

            const emoji =
                mapEmojis[statReal]
                || '✨';

            const nomeStat =
                nomeBonitoStat(
                    statReal
                );

            const prefixo = String(val).includes('-') ? '' : '+';

            statsHtml += `
                <span class="eldora-profile-style-6f0e3ff5">
                    ${emoji} ${nomeStat}: ${prefixo}${val}
                </span>
            `;
        }
    } else if (['weapon', 'armor', 'helmet', 'boots', 'ring', 'necklace', 'earring', 'equipamento', 'tool', 'arma', 'armadura', 'lenhador', 'minerador', 'colhedor', 'esfolador', 'ferreiro', 'armeiro', 'alfaiate', 'joalheiro', 'curtidor'].includes(t)) {
        statsHtml = `<span class="eldora-profile-style-775e837e">Sem atributos base</span>`;
    }

    if (
        isFerramentaPerfil(
            itemData
        )
    ) {
        const tierTool =
            getTierFerramentaPerfil(
                itemData
            );

        const profTool =
            normalizarProfissaoPerfil(
                itemData.tool_type ||
                itemData.slot_profissao ||
                ""
            );

        const profNome = profTool
            ? profTool
                .charAt(0)
                .toUpperCase()
                + profTool.slice(1)
            : "Profissão";

        statsHtml =
            `
            <span class="eldora-profile-style-3849b30a">
                🛠️ T${tierTool} • ${profNome}
            </span>
            `
            + statsHtml;
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
            <div class="eldora-profile-style-f0547d36">
                <div class="eldora-profile-style-7ae2014d">
                    <span>DURABILIDADE</span>
                    <span>${atual} / ${maximo}</span>
                </div>
                <div class="eldora-profile-style-1b874464">
                    <div style="--progress:${porc}%;--durability-color:${corBarra}"></div>
                </div>
            </div>
        `;
        statsHtml = durHtml + statsHtml; // Adiciona a barra em cima dos atributos
    }

    document.getElementById('modal-item-stats').innerHTML = statsHtml;


    // 👇 BOTÃO DE CONSERTAR (Aparece se o item estiver gasto e o jogador tiver o pergaminho) 👇
    // 👇 MÁGICA 2: RECONHECIMENTO INFALÍVEL DE POÇÕES 👇
    if (origem === 'mochila' || origem === 'inventario') {

        if (['weapon', 'armor', 'helmet', 'boots', 'ring', 'necklace', 'earring', 'equipamento', 'tool', 'arma', 'armadura', 'lenhador', 'minerador', 'colhedor', 'esfolador', 'ferreiro', 'armeiro', 'alfaiate', 'joalheiro', 'curtidor'].includes(t)) {
            botoesHtml = `<button onclick="usarOuEquiparItem('${itemData.id}')" class="eldora-profile-style-7c693876">Equipar</button>`;
        }
        else if (itemData.on_use?.effect === 'xp_boost' || ['pocao_xp_boost', 'pocao_xp_boost_g', 'elixir_xp_dobrado_10m', 'elixir_xp_dobrado_30m'].includes(idReal)) {
            botoesHtml = `<button onclick="consumirItemDireto('${itemData.id}', '${idReal}')" class="eldora-profile-style-038e3ada">Usar · XP ×2</button>`;
        }
        else if (idReal.includes('pocao') || nomeLower.includes('poção') || ['potion'].includes(t)) {
            botoesHtml = `
                <button onclick="equiparPocaoAtalho('${idReal}', 'hp')" class="eldora-profile-style-e9e08d6a">Slot ❤️</button>
                <button onclick="equiparPocaoAtalho('${idReal}', 'mp')" class="eldora-profile-style-43efeeaf">Slot 💧</button>
            `;
        }
        else if (idReal === 'carta_recomendacao') {
            botoesHtml = '<div class="eldora-profile-style-3198545b">📜 Apresente esta carta à recepcionista da Guilda dos Aventureiros. Ela será recolhida automaticamente no seu registro.</div>';
        }
        else if (t === 'reagent') {

            botoesHtml = `
                <div class="eldora-profile-style-f1ce6332">
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
                    class="eldora-profile-style-873b2342"
                >
                    Usar Item
                </button>
            `;
        }
        else {
            botoesHtml = `<div class="eldora-profile-style-3a71e7e3">🛠️ Leve este item a um NPC (Ferreiro, Alquimista...) para utilizá-lo.</div>`;
        }
    } else if (origem === 'equipado') {
        botoesHtml = `<button onclick="desequiparItem('${itemData.slot}')" class="eldora-profile-style-e9e08d6a">Remover</button>`;
    }

    const temPergaminho = window.perfilDadosGlobais.inventario.some(i => ['pergaminho_durabilidade', 'pergaminho_de_reparo'].includes(i.base_id || i.id));
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
        botoesHtml += `<button onclick="repararFerramentaAPI('${itemData.id}')" class="eldora-profile-style-50b8d325">CONSERTAR (1x 📜)</button>`;
    }

    botoesHtml += `<button onclick="fecharModalItem()" class="eldora-profile-style-e4b50000">Fechar</button>`;

    if (itemData.rune_slots?.length) {
        document.getElementById('modal-item-stats').insertAdjacentHTML('beforeend', window.renderRuneDetails(itemData));
    }
    document.getElementById('modal-item-acoes').innerHTML = botoesHtml;
    if (itemData.rune_slots?.length) {
        const manage = document.createElement('button');
        manage.className = 'rune-manage'; manage.textContent = 'Gerenciar runas na Forja';
        manage.onclick = () => window.abrirOficinaRunas(itemData.uid || itemData.id);
        document.getElementById('modal-item-acoes').appendChild(manage);
    }
    document.getElementById('modal-item').classList.add('is-open');
}

window.fecharModalItem = function() {
    document.getElementById('modal-item').classList.remove('is-open');
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
            else window.avisoEldora("Aviso: " + msg);
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
        else window.avisoEldora("⚠️ ERRO: " + e.message);
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
            if (data.xp_boost) window.dispatchEvent(new CustomEvent("eldora:xp-boost", { detail: data }));
            carregarMeuPerfil();
            setTimeout(() => alternarAbaPerfil('equips'), 200);

            // ⚡ SINCRONIA FINA: Força a atualização imediata dos HUDs
            if (window.atualizarHudCircular) window.atualizarHudCircular();
            if (window.carregarDadosDoHUD && document.getElementById('hud-status-flutuante').style.display === 'block') {
                window.carregarDadosDoHUD();
            }
        } else { window.avisoEldora("Aviso: " + data.erro); }
    } catch(e) { window.avisoEldora("⚠️ ERRO: " + e.message); }
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
        } else { window.avisoEldora("Aviso: " + data.erro); }
    } catch(e) { window.avisoEldora("⚠️ ERRO: " + e.message); }
}

// ==========================================
// ALERTA ÉPICO CUSTOMIZADO
// ==========================================
// Os diálogos compartilhados são carregados por dialogos_eldora.js.
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
            else window.avisoEldora(data.erro);
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
    container.classList.add('eldora-combat-skill-slots');

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
        quadrado.className = "eldora-combat-skill-slot" + (slotEquipado ? " is-equipped" : "");

        // Se estiver equipada, o quadrado ganha uma aura mágica (roxa)

        // A Imagem Redonda no centro
        const imgContainer = document.createElement('div');
        imgContainer.className = "eldora-combat-skill-icon";

        const img = document.createElement('img');
        img.src = imgUrl;
        img.className = "eldora-combat-skill-image";
        imgContainer.appendChild(img);
        quadrado.appendChild(imgContainer);

        // Indicador numérico do Slot
        if (slotEquipado) {
            const badge = document.createElement('div');
            badge.innerHTML = `S${slotEquipado}`;
            badge.className = "eldora-combat-skill-badge";
            quadrado.appendChild(badge);
        }

        quadrado.onclick = () => window.abrirModalSkillDetalhes(skillId, infoDb, slotEquipado);
        container.appendChild(quadrado);
    }

    if (!encontrouSkill) {
        container.innerHTML = `<div class="eldora-profile-style-3442af12">O teu grimório está vazio.</div>`;
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
        let htmlSlots = `<div class="eldora-profile-style-98b031ef">Sem espaço livre. Qual magia queres substituir?</div><div class="eldora-profile-style-d6e5fed8">`;

        for (let i = 1; i <= 5; i++) {
            const idEquipada = equipadas[`slot_${i}`];
            const db = p.database_skills || {};
            const info = db[idEquipada] || {};
            const iconeInfo = info.icon || 'default_skill';
            const url = `/static/assets/sprites/skills/${iconeInfo}.png`;

            htmlSlots += `
                <div onclick="window.processarEquiparSkill('${skillId}', ${i})" class="eldora-profile-style-847ec13b" title="${info.display_name || 'Substituir'}">
                    <img src="${url}" class="eldora-profile-style-f369cd95">
                    <span class="eldora-profile-style-bba53f06">S${i}</span>
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
                window.avisoEldora(data.msg);
            }
        } else {
            if (window.alertaEldora) {
                window.alertaEldora("Falha no Reparo", data.error, "erro");
            } else {
                window.avisoEldora(data.error);
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

