// ==========================================
// CONFIGURAÇÕES GERAIS E DADOS (perfil.js)
// ==========================================
// ==========================================
// BÚSSOLA DE PASTAS DE ITENS
// ==========================================
function itemEUmaFerramenta(dado) {
    const tiposFerramenta = new Set(['tool', 'ferramenta', 'lenhador', 'minerador', 'colhedor', 'esfolador', 'ferreiro', 'armeiro', 'alfaiate', 'joalheiro', 'curtidor', 'alquimista', 'fundidor']);
    if (typeof dado !== 'object' || !dado) return tiposFerramenta.has(String(dado || '').trim().toLowerCase());

    const normalizar = valor => String(valor || '').trim().toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '');
    const tipo = normalizar(dado.tipo || dado.type || dado.categoria || dado.category);
    const slot = normalizar(dado.slot || dado.slot_profissao);
    const tipoFerramenta = normalizar(dado.tool_type);
    return tiposFerramenta.has(tipo) || tiposFerramenta.has(slot) || slot.startsWith('tool_') || tiposFerramenta.has(tipoFerramenta);
}

function caminhoPertencePastaFerramentas(caminho) {
    return /(?:^|\/)ferramentas\//i.test(String(caminho || '').replace(/\\/g, '/'));
}

window.obterPastaItem = function(dado) {
    // Pega o tipo seja lá como ele vier (se mandarem o objeto inteiro ou só o texto)
    let tipo = typeof dado === 'object' ? (dado.tipo || dado.type || "") : (dado || "");
    const t = tipo.toLowerCase();

    // 1. Ferramentas de Profissão
    if (itemEUmaFerramenta(dado)) return 'ferramentas';

    // 2. Equipamentos (Armas e Armaduras)
    const tiposEquipamento = ['weapon', 'armor', 'helmet', 'boots', 'bota', 'ring', 'necklace', 'earring', 'equipamento', 'arma', 'armadura', 'elmo', 'anel', 'colar', 'brinco'];
    if (tiposEquipamento.includes(t)) return 'equipamentos';

    // 3. Consumíveis e itens especiais
    const tiposUsaveis = ['potion', 'pocao', 'consumable', 'scroll', 'pergaminho', 'chest', 'box', 'consumivel', 'reagent', 'especial', 'event_ticket'];
    if (tiposUsaveis.includes(t)) return 'consumiveis';

    // Fallback absoluto
    return 'materiais';
};

const FILTROS_MOCHILA = [
    { id: 'todos', nome: 'Todos', icone: '🎒' },
    { id: 'consumiveis', nome: 'Consumíveis', icone: '🧪' },
    { id: 'combate', nome: 'Combate', icone: '⚔️' },
    { id: 'profissao', nome: 'Profissão', icone: '🛠️' },
    { id: 'materiais', nome: 'Materiais', icone: '📦' },
    { id: 'essencias', nome: 'Essências', icone: '✨' },
    { id: 'runas', nome: 'Runas', icone: '🔮' },
    { id: 'livros', nome: 'Livros', icone: '📘' },
    { id: 'outros', nome: 'Outros', icone: '🗝️' }
];

function normalizarCategoriaMochila(valor) {
    return String(valor || '').trim().toLowerCase()
        .normalize('NFD').replace(/[\u0300-\u036f]/g, '');
}

function classificarItemMochila(item) {
    const tipo = normalizarCategoriaMochila(item?.tipo || item?.type);
    const categoria = normalizarCategoriaMochila(item?.categoria || item?.category);
    const slot = normalizarCategoriaMochila(item?.slot || item?.slot_profissao);
    const id = normalizarCategoriaMochila(item?.base_id || item?.item_id || item?.id);
    const toolType = normalizarCategoriaMochila(item?.tool_type || item?.slot_profissao);

    // Ferramentas de coleta e produção ficam separadas dos equipamentos de combate.
    const slotsProfissao = new Set(['tool', 'ferramenta', 'lenhador', 'minerador', 'colhedor', 'esfolador', 'ferreiro', 'armeiro', 'alfaiate', 'joalheiro', 'curtidor', 'alquimista', 'fundidor']);
    if (tipo === 'tool' || tipo === 'ferramenta' || slot === 'tool' || slot.startsWith('tool_') || slotsProfissao.has(slot) || toolType) return 'profissao';

    if (tipo === 'skill_book') return 'livros';
    if (['essencia', 'essencias', 'essence'].includes(tipo) || categoria === 'essencia' || id.startsWith('essencia_')) return 'essencias';
    if (['runa', 'rune'].includes(tipo) || categoria === 'runas' || categoria === 'socketable' || id.startsWith('runa_')) return 'runas';

    const slotsCombate = new Set([
        'arma', 'weapon', 'armadura', 'armor', 'elmo', 'helmet', 'capacete', 'chapeu',
        'calca', 'calcas', 'botas', 'bota', 'luvas', 'luva', 'anel', 'ring', 'colar',
        'necklace', 'brinco', 'earring', 'acessorio', 'escudo', 'capa', 'peitoral',
        'capuz', 'tunica', 'manto', 'adaga', 'espada', 'arco', 'cajado'
    ]);
    const tiposCombate = new Set([
        'equipment', 'equipment_base', 'equipamento', 'equipamentos', 'weapon', 'armor', 'helmet',
        'boots', 'ring', 'necklace', 'earring', 'arma', 'armadura', 'elmo', 'bota', 'botas',
        'anel', 'colar', 'brinco', 'acessorio'
    ]);
    const categoriasCombate = new Set(['arma', 'armadura', 'acessorio', 'equipamento']);
    if (slotsCombate.has(slot) || tiposCombate.has(tipo) || categoriasCombate.has(categoria)) return 'combate';

    if (['skill_book', 'livro', 'book'].includes(tipo)) return 'livros';
    if (['consumable', 'consumivel', 'potion', 'pocao', 'scroll', 'pergaminho', 'chest', 'box', 'event_ticket'].includes(tipo) || categoria === 'consumivel') return 'consumiveis';
    if (tipo === 'especial' && item?.on_use && Object.keys(item.on_use).length) return 'consumiveis';

    if (tipo.startsWith('material') || ['material', 'coletavel', 'cacada', 'reagente', 'alquimia', 'mineral', 'madeira', 'couro', 'fibra', 'runas'].includes(categoria)
        || ['reagent', 'resource', 'sucata', 'fragmento_divino', 'divino'].includes(tipo)) return 'materiais';

    return 'outros';
}

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
    const ehFerramenta = pasta === 'ferramentas';
    if (typeof item?.icon_url === 'string' && /^(https?:\/\/|\/static\/)/.test(item.icon_url)
        && (!ehFerramenta || caminhoPertencePastaFerramentas(item.icon_url))) {
        caminhos.push(item.icon_url);
    }
    for (const caminho of (window.FORJA_IMAGENS?.[idReal] || [])) {
        if (ehFerramenta && !caminhoPertencePastaFerramentas(caminho)) continue;
        caminhos.push(`${linkBaseNuvem}itens/${caminho}`);
    }

    if (ehFerramenta) {
        caminhos.push(`${linkBaseNuvem}itens/ferramentas/${idReal}.png`);
        caminhos.push(`${linkBaseNuvem}itens/ferramentas/work_${idReal}.png`);
        caminhos.push("/static/assets/box.png");
        return [...new Set(caminhos)];
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
    const baseRunas = "https://raw.githubusercontent.com/Eldorabotpy/static-img/main/assets/runas/";
    const cacheVersion = "20261025-2";
    const bruto = String(item?.base_id || item?.item_id || item?.uid || item?.id || "").trim();
    if (!bruto) return [];

    const idSemWork = bruto.replace(/^work_/i, "");
    const ids = [...new Set([bruto, idSemWork, "work_" + idSemWork].filter(Boolean))];
    const tipo = String(item?.tipo || item?.type || item?.categoria || item?.category || "")
        .trim().toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "");
    const categoria = String(item?.categoria || item?.category || "")
        .trim().toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "");
    const ferramenta = itemEUmaFerramenta(item);
    const caminhos = [];
    if (["skill_book", "livro", "book"].includes(tipo) || categoria === "aprendizado") {
        // Alguns tomos antigos ficam no inventário pelo ID da própria skill
        // (ex.: evo_templar_divine_light), enquanto a arte pública usa o ID
        // canônico do tomo (tomo_evo_templar_divine_light.png).
        const skillId = String(item?.skill_id || "").trim();
        const idTomo = /^tomo_/i.test(bruto) ? bruto : `tomo_${skillId || bruto}`;
        caminhos.push(`${base}materiais/${encodeURIComponent(idTomo)}.png?v=${cacheVersion}`);
    }
    const urlIcone = typeof item?.icon_url === "string" ? item.icon_url.trim() : "";
    const iconePlaceholder = /(?:seuusuario|seurepositorio|example\.com|placeholder)/i.test(urlIcone);
    if (!iconePlaceholder && /^(https?:\/\/|\/static\/)/i.test(urlIcone)
        && (!ferramenta || caminhoPertencePastaFerramentas(urlIcone))) caminhos.push(urlIcone);

    const runeId = String(item?.base_id || item?.item_id || item?.uid || item?.id || "").trim();
    const runeMatch = runeId.match(/^runa_(crueldade|precisao|vampiro|rocha|mente|eco|midas|sabio)_(menor|maior|ancestral)$/);
    if (runeMatch) {
        const imagemRuna = `${baseRunas}${runeId}.png?v=${cacheVersion}`;
        const fallbackFamilia = `/static/assets/runas/${runeMatch[1]}.svg?v=3`;
        // Runas ficam em assets/runas (fora de assets/itens). Tenta a arte
        // específica do nível antes do símbolo genérico da família.
        return [...new Set([imagemRuna, ...caminhos, fallbackFamilia])];
    }

    // Os itens de forja têm chaves "work_*" no índice, embora o base_id não tenha esse prefixo.
    for (const id of ids) {
        const cadastrados = window.FORJA_IMAGENS?.[id];
        if (!Array.isArray(cadastrados)) continue;
        for (const caminho of cadastrados) {
            if (ferramenta && !caminhoPertencePastaFerramentas(caminho)) continue;
            if (typeof caminho === "string" && caminho) {
                caminhos.push(base + caminho.replace(/^\/?(?:assets\/)?itens\//, "") + "?v=" + cacheVersion);
            }
        }
    }

    const tiposEquipamento = new Set([
        "weapon", "armor", "helmet", "boots", "bota", "botas", "ring", "necklace", "earring",
        "equipamento", "arma", "armadura", "elmo", "anel", "colar", "brinco", "calca", "calcas",
        "luva", "luvas", "peitoral", "capuz", "chapeu", "capacete", "tunica", "manto", "escudo",
        "adaga", "espada", "arco", "cajado", "equipment"
    ]);
    const idPareceEquipamento = /^(?:work_)?(?:espada|adaga|arco|cajado|machado|peitoral|armadura|calca|calcas|bota|botas|luva|luvas|anel|colar|brinco|capuz|chapeu|elmo|capacete|tunica|manto|escudo|capa)(?:_|$)/i.test(bruto);
    const temMapaEquipamento = ids.some(id => (window.FORJA_IMAGENS?.[id] || []).some(path => /^equipamentos\//i.test(path)));
    const equipamento = !ferramenta && (
        tiposEquipamento.has(tipo) || tipo === "equipamentos" || temMapaEquipamento || (!tipo && idPareceEquipamento)
    );
    const tiposUsaveis = new Set(["potion", "pocao", "consumable", "consumivel", "scroll", "pergaminho", "chest", "box", "reagent", "especial", "event_ticket"]);
    const pastas = ferramenta ? ["ferramentas"] : equipamento ? ["equipamentos"] : tiposUsaveis.has(tipo) ? ["consumiveis", "materiais"] : ["materiais"];

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

function instalarAbasProfissoesPerfil() {
    if (window.__eldoraAbasProfissoesInstaladas) return;
    window.__eldoraAbasProfissoesInstaladas = true;

    document.addEventListener('click', event => {
        const tab = event.target?.closest?.('.perfil-v2-prof-tab');
        const section = tab?.closest('.perfil-v2-profissoes');
        if (!tab || !section) return;

        const index = tab.dataset.profIndex;
        section.querySelectorAll('.perfil-v2-prof-tab').forEach(button => {
            const selected = button === tab;
            button.classList.toggle('selecionada', selected);
            button.setAttribute('aria-selected', String(selected));
            button.tabIndex = selected ? 0 : -1;
        });

        section.querySelectorAll('.perfil-v2-prof-detalhe').forEach(panel => {
            const selected = panel.dataset.profIndex === index;
            panel.hidden = !selected;
            panel.classList.remove('is-entering');
            if (selected) {
                void panel.offsetWidth;
                panel.classList.add('is-entering');
            }
        });
    });

    document.addEventListener('keydown', event => {
        const tab = event.target?.closest?.('.perfil-v2-prof-tab');
        if (!tab || !['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return;
        const tabs = Array.from(tab.closest('[role="tablist"]')?.querySelectorAll('.perfil-v2-prof-tab') || []);
        const current = tabs.indexOf(tab);
        if (current < 0 || !tabs.length) return;
        event.preventDefault();
        const next = event.key === 'Home' ? 0
            : event.key === 'End' ? tabs.length - 1
            : (current + (event.key === 'ArrowRight' ? 1 : -1) + tabs.length) % tabs.length;
        tabs[next].focus();
        tabs[next].click();
    });
}

instalarAbasProfissoesPerfil();

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
        p.mochila = p.mochila || { tier: 1, name: 'Mochila de Viajante', used: (p.inventario || []).length, capacity: 40, stack_limit: 500, next_tier: 2, next_name: 'Mochila Reforçada', next_capacity: 80, next_cost_gems: 100 };

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
        // PROFISSÕES: SELEÇÃO POR ÍCONE E PAINEL DE STATUS
        // ==========================================
        let htmlProfissao = '';

        // Junta a profissão atual às profissões aprendidas sem alterar os dados do personagem.
        const profsAprendidas = { ...(p.learned_professions || {}) };
        if (p.profession && (p.profession.key || p.profession.type)) {
            const pKey = p.profession.key || p.profession.type;
            if (!profsAprendidas[pKey]) profsAprendidas[pKey] = p.profession;
        }

        const listaProfs = Object.values(profsAprendidas);

        if (listaProfs.length > 0) {
            listaProfs.sort((a, b) => (Number(b.level) || 1) - (Number(a.level) || 1));
            const paineisProfissoes = [];
            htmlProfissao = `<section class="perfil-v2-profissoes" aria-label="Profissões do personagem">
                <header class="perfil-v2-prof-cabecalho"><h3>Profissões</h3><span>${listaProfs.length} ${listaProfs.length === 1 ? 'ofício' : 'ofícios'}</span></header>
                <p class="perfil-v2-prof-instrucao">Toque em uma profissão para consultar seus status.</p>
                <div class="perfil-v2-profissoes-lista" role="tablist" aria-label="Selecionar profissão">`;

            listaProfs.forEach((profInfo, index) => {
                const profNivel = Math.max(1, Number(profInfo.level) || 1);
                const profXp = Math.max(0, Number(profInfo.xp) || 0);
                const xpNecessarioProf = 40 + (25 * (profNivel - 1)) + (8 * Math.pow(profNivel - 1, 2));
                const percentProfXP = Math.min((profXp / Math.max(1, xpNecessarioProf)) * 100, 100);
                const nomeProf = profInfo.display_name || profInfo.nome || profInfo.type || 'Aprendiz';
                let keyword = '';
                let imgGenerica = 'martelo_ferreiro';
                let isCrafting = false;
                const profStr = String(profInfo.key || profInfo.type || '').toLowerCase();

                // Profissões de coleta
                if (profStr.includes('lenhador')) { keyword = 'machado'; imgGenerica = 'machado'; }
                else if (profStr.includes('minerador')) { keyword = 'picareta'; imgGenerica = 'picareta'; }
                else if (profStr.includes('colhedor')) { keyword = 'foice'; imgGenerica = 'foice'; }
                else if (profStr.includes('esfolador')) { keyword = 'faca'; imgGenerica = 'faca'; }
                else if (profStr.includes('alquimista')) { keyword = 'frasco'; imgGenerica = 'frasco'; }
                // Profissões de produção
                else if (profStr.includes('ferreiro')) { keyword = 'martelo_ferreiro'; imgGenerica = 'martelo_ferreiro'; isCrafting = true; }
                else if (profStr.includes('armeiro')) { keyword = 'martelo_armeiro'; imgGenerica = 'martelo_armeiro'; isCrafting = true; }
                else if (profStr.includes('alfaiate')) { keyword = 'alfaiate'; imgGenerica = 'kit_alfaiate'; isCrafting = true; }
                else if (profStr.includes('joalheiro')) { keyword = 'joalheiro'; imgGenerica = 'kit_joalheiro'; isCrafting = true; }
                else if (profStr.includes('curtidor')) { keyword = 'curtidor'; imgGenerica = 'kit_curtidor'; isCrafting = true; }

                const bonusTexto = isCrafting
                    ? `Tempo de forja: -${(profNivel * 0.5).toFixed(1)}%`
                    : `Drop fixo: +${Math.floor(profNivel / 10)} | Chance dupla: ${(profNivel * 0.5).toFixed(1)}%`;

                const inventario = Array.isArray(p.inventario) ? p.inventario : [];
                const ferramentaUser = keyword
                    ? inventario.find(item => String(item?.base_id || '').toLowerCase().includes(keyword))
                    : null;
                let corBordaT = '#475569';
                let corFundoT = '#0f172a';
                let glowT = 'rgba(0,0,0,0.5)';
                let tierTxt = 'T1';

                if (ferramentaUser) {
                    const idItem = String(ferramentaUser.base_id || '').toLowerCase();
                    if (idItem.includes('ferro') || idItem.includes('ceramica') || idItem.includes('_t2')) {
                        corBordaT = '#22c55e'; corFundoT = 'rgba(34, 197, 94, 0.1)'; glowT = 'rgba(34, 197, 94, 0.4)'; tierTxt = 'T2';
                    } else if (idItem.includes('aco') || idItem.includes('cristal') || idItem.includes('_t3')) {
                        corBordaT = '#3b82f6'; corFundoT = 'rgba(59, 130, 246, 0.1)'; glowT = 'rgba(59, 130, 246, 0.4)'; tierTxt = 'T3';
                    } else if (idItem.includes('mithril') || idItem.includes('obsidiana') || idItem.includes('runico') || idItem.includes('_t4')) {
                        corBordaT = '#a855f7'; corFundoT = 'rgba(168, 85, 247, 0.1)'; glowT = 'rgba(168, 85, 247, 0.4)'; tierTxt = 'T4';
                    } else if (idItem.includes('adamantio') || idItem.includes('vorpal') || idItem.includes('vazio') || idItem.includes('druidica') || idItem.includes('_t5')) {
                        corBordaT = '#eab308'; corFundoT = 'rgba(234, 179, 8, 0.1)'; glowT = 'rgba(234, 179, 8, 0.4)'; tierTxt = 'T5';
                    }
                }

                const imgPath = `https://raw.githubusercontent.com/Eldorabotpy/static-img/main/assets/itens/ferramentas/${imgGenerica}.png`;
                const statusFerramenta = ferramentaUser ? `No inventário · ${tierTxt}` : 'Não encontrada no inventário';
                const ariaId = `perfil-prof-tab-${index}`;
                const painelId = `perfil-prof-detalhe-${index}`;
                const barraXP = Math.min(profXp, xpNecessarioProf);

                htmlProfissao += `
                    <button id="${ariaId}" class="perfil-v2-prof-tab${index === 0 ? ' selecionada' : ''}" type="button" role="tab"
                        aria-selected="${index === 0 ? 'true' : 'false'}" aria-controls="${painelId}" tabindex="${index === 0 ? '0' : '-1'}"
                        aria-label="${nomeProf}, nível ${profNivel}" data-prof-index="${index}" title="${nomeProf} — nível ${profNivel}">
                        <span class="perfil-v2-prof-tab-icone"><img src="${imgPath}" alt="" loading="lazy" decoding="async"><small>Nv ${profNivel}</small></span>
                        <span class="perfil-v2-prof-tab-nome">${nomeProf}</span>
                    </button>`;

                paineisProfissoes.push(`
                    <section id="${painelId}" class="perfil-v2-prof-detalhe${index === 0 ? ' is-entering' : ''}" role="tabpanel" tabindex="0"
                        aria-labelledby="${ariaId}" data-prof-index="${index}"${index === 0 ? '' : ' hidden'}>
                        <div class="perfil-v2-prof-detalhe-topo">
                            <span class="perfil-v2-prof-detalhe-icone" style="--prof-cor:${corBordaT}; --prof-fundo:${corFundoT}; --prof-glow:${glowT};"><img src="${imgPath}" alt="" loading="lazy" decoding="async"></span>
                            <div class="perfil-v2-prof-detalhe-titulo"><small>${isCrafting ? 'OFÍCIO DE PRODUÇÃO' : 'OFÍCIO DE COLETA'}</small><h4>${nomeProf}</h4></div>
                            <span class="perfil-v2-prof-nivel">Nível ${profNivel}</span>
                        </div>
                        <div class="perfil-v2-prof-xp-heading"><span>Experiência</span><strong>${profXp.toLocaleString('pt-BR')} <small>/ ${xpNecessarioProf.toLocaleString('pt-BR')} XP</small></strong></div>
                        <div class="perfil-v2-prof-trilho" role="progressbar" aria-label="Progresso de experiência de ${nomeProf}" aria-valuemin="0" aria-valuemax="${xpNecessarioProf}" aria-valuenow="${barraXP}"><i style="width:${percentProfXP}%;"></i></div>
                        <div class="perfil-v2-prof-status">
                            <div><span>Bônus atual</span><strong>${bonusTexto}</strong></div>
                            <div><span>Ferramenta</span><strong>${statusFerramenta}</strong></div>
                        </div>
                    </section>`);
            });

            htmlProfissao += `</div>${paineisProfissoes.join('')}</section>`;
        } else {
            htmlProfissao = `
            <section class="perfil-v2-profissoes perfil-v2-profissoes-vazio" aria-label="Profissões do personagem">
                <header class="perfil-v2-prof-cabecalho"><h3>Profissões</h3><span>0 ofícios</span></header>
                <div class="perfil-v2-prof-vazio"><strong>Nenhum ofício aprendido</strong><span>Encontre um Mestre de Guilda para aprender uma profissão.</span></div>
            </section>`;
        }
        // ==========================================
        // ==========================================
        // 3. O TRADUTOR DO GITHUB E CORPO COMPLETO
        // ==========================================

        // --- BANNER ---
        let bannerCaminho = p.banner_customizado;
        if (typeof bannerCaminho === 'object' && bannerCaminho !== null) bannerCaminho = bannerCaminho.path;

        let bannerImgCss = 'linear-gradient(135deg, #2c3e50, #1a1a1a)';
        let bannerRawUrl = '';
        if (bannerCaminho && bannerCaminho !== '') {
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
        const arquivoSkinDoCorpo = window.resolverArquivoSkinGenero(skinDoCorpo);
        const fullBodyImgUrl = `${linkBaseNuvem}corpo_completo/${arquivoSkinDoCorpo}_full.png`;
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

        const rotulosSlots = {
            elmo: 'Elmo', armadura: 'Armadura', calca: 'Calças', luvas: 'Luvas',
            botas: 'Botas', colar: 'Colar', anel: 'Anel', brinco: 'Brinco', arma: 'Arma'
        };
        const classesSpriteSlots = {
            elmo: 'eldora-slot-sprite--elmo', armadura: 'eldora-slot-sprite--armadura',
            calca: 'eldora-slot-sprite--calca', luvas: 'eldora-slot-sprite--luvas',
            botas: 'eldora-slot-sprite--botas', colar: 'eldora-slot-sprite--colar',
            anel: 'eldora-slot-sprite--anel', brinco: 'eldora-slot-sprite--brinco',
            arma: 'eldora-slot-sprite--arma'
        };
        const renderIconeSlotVazio = slot => {
            const classeSprite = classesSpriteSlots[slot];
            if (!classeSprite) return '<span class="eldora-slot-sprite eldora-slot-sprite--fallback" aria-hidden="true"></span>';
            const rotulo = rotulosSlots[slot] || 'Equipamento';
            return `<span class="eldora-slot-sprite ${classeSprite}" role="img" aria-label="Espaço vazio: ${rotulo}"></span>`;
        };

        const ferramentasProfissao = (p.equipamentos || []).filter(eq => {
            const slot = String(eq.slot || '');
            return slot.startsWith('tool_');
        });

        equipamentosCorpo.forEach(eq => {

            const corBorda = eq.vazio ? "#334155" : "#f59e0b";
            const corFundo = eq.vazio ? "rgba(15, 23, 42, 0.8)" : "rgba(245, 158, 11, 0.15)";

            let visualItem = eq.vazio ? renderIconeSlotVazio(String(eq.slot || '')) :
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

                <button class="eldora-companion-button eldora-profile-style-ca6eb74e" type="button" onclick="window.abrirCompanheiros()" >
                    🐾 Companheiro<br><span class="eldora-profile-style-e18a3df1">${p.companion ? `${p.companion.icon} ${p.companion.name} · ${p.companion.form} · Nv. ${p.companion.level}` : 'Nenhum equipado · Abrir Companheiros'}</span>
                </button>
                ${htmlFerramentas}
            </div>`;

        // --- Mochila: categorias construídas a partir dos metadados reais de cada item ---
        const itensInventario = Array.isArray(p.inventario) ? p.inventario : [];
        const mochila = p.mochila || {};
        const espacosMochila = Number(mochila.used ?? itensInventario.length);
        const capacidadeMochila = Number(mochila.capacity || 40);
        const progressoMochila = Math.min(100, Math.max(0, capacidadeMochila ? espacosMochila / capacidadeMochila * 100 : 0));
        const mochilaCheia = espacosMochila >= capacidadeMochila;
        const htmlMelhoriaMochila = mochila.next_tier
            ? `<button type="button" class="eldora-backpack-upgrade" onclick="window.aprimorarMochilaPerfil()" ${Number(p.gems || 0) < Number(mochila.next_cost_gems || 0) ? 'disabled' : ''}>
                    <span>Ampliar para ${Number(mochila.next_capacity).toLocaleString('pt-BR')} espaços</span>
                    <strong>💎 ${Number(mochila.next_cost_gems || 0).toLocaleString('pt-BR')}</strong>
               </button>`
            : `<span class="eldora-backpack-max">Mochila no tamanho máximo</span>`;
        const contagensMochila = Object.fromEntries(FILTROS_MOCHILA.map(filtro => [
            filtro.id,
            filtro.id === 'todos' ? itensInventario.length : itensInventario.filter(item => classificarItemMochila(item) === filtro.id).length
        ]));
        let htmlInv = `
            <div class="eldora-inventory-toolbar">
                <label class="eldora-inventory-search" for="busca-mochila">
                    <span aria-hidden="true">⌕</span>
                    <input id="busca-mochila" type="search" placeholder="Buscar item pelo nome…" autocomplete="off" aria-label="Buscar item na mochila">
                </label>
                <span id="contagem-itens-mochila" class="eldora-inventory-count" aria-live="polite">${itensInventario.length} ${itensInventario.length === 1 ? 'item' : 'itens'}</span>
            </div>
            <section class="eldora-backpack-summary" aria-label="Capacidade da mochila">
                <div class="eldora-backpack-heading">
                    <div><span>MOCHILA · NÍVEL ${Number(mochila.tier || 1)}</span><strong>${mochila.name || 'Mochila de Viajante'}</strong></div>
                    <b>${espacosMochila}/${capacidadeMochila}<small> espaços</small></b>
                </div>
                <div class="eldora-backpack-track" role="progressbar" aria-valuemin="0" aria-valuemax="${capacidadeMochila}" aria-valuenow="${Math.min(espacosMochila, capacidadeMochila)}"><i style="width:${progressoMochila}%"></i></div>
                <div class="eldora-backpack-footer">
                    <small>${mochilaCheia ? 'Mochila cheia. Venda ou use itens para liberar espaço.' : `Até ${Number(mochila.stack_limit || 500)} unidades por pilha.`}</small>
                    ${htmlMelhoriaMochila}
                </div>
            </section>
            <div id="filtros-mochila" class="eldora-inventory-filters eldora-profile-style-494596d6" role="group" aria-label="Categorias da mochila">
                ${FILTROS_MOCHILA.map(filtro => `
                    <button type="button" class="eldora-inventory-filter${filtro.id === 'todos' ? ' is-active' : ''}" onclick="filtrarMochila('${filtro.id}')" id="btn-filtro-${filtro.id}" aria-pressed="${filtro.id === 'todos'}">
                        <span aria-hidden="true">${filtro.icone}</span><span>${filtro.nome}</span><small>${contagensMochila[filtro.id]}</small>
                    </button>
                `).join('')}
            </div>
            <div id="grid-mochila" class="eldora-inventory-grid eldora-profile-style-5bf71092" aria-live="polite"></div>
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

        const buscaMochila = document.getElementById('busca-mochila');
        if (buscaMochila) {
            buscaMochila.value = window.perfilBuscaMochilaAtual || '';
            buscaMochila.addEventListener('input', () => {
                window.perfilBuscaMochilaAtual = buscaMochila.value;
                filtrarMochila(window.perfilFiltroMochilaAtual || 'todos');
            });
        }

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
        await alternarAbaPerfil(abaInicialPerfil);

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
    if (abaID === 'magias') return carregarMenuMagias();
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
        window._skillsPossuidasTemp = skillsPossuidas;

        let html = `<div class="eldora-profile-style-801160c3">
                        <h4 class="eldora-profile-style-593914d0">Grimório de Eldora</h4>
                        <nav class="eldora-skill-view-tabs" aria-label="Seções de habilidades">
                            <button type="button" class="is-active" aria-current="page">Habilidades</button>
                            <button type="button" onclick="window.abrirPainelAprimoramentoSkills()">Aprimorar</button>
                        </nav>`;

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
                const nivelSkill = Math.max(1, Number(skillInst?.level || 1));

                html += `
                    <div onclick="window.abrirModalSkillDetalhes('${skillId}', window._skillsDataTemp['${skillId}'], ${slotEquipado || 'null'})"
                         class="eldora-spell-card ${slotEquipado ? 'is-equipped' : ''}">

                        ${slotEquipado ? `<span class="eldora-profile-style-15475bc2">S${slotEquipado}</span>` : ""}
                        <span class="eldora-spell-level">NV ${nivelSkill}</span>

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

window.abrirPainelAprimoramentoSkills = function() {
    const container = document.getElementById('conteudo-perf-magias');
    if (!container) return;

    const skillsPossuidas = window._skillsPossuidasTemp || {};
    const skillsAprimoraveis = Object.entries(skillsPossuidas).filter(([skillId]) =>
        Boolean(window._skillsDataTemp?.[skillId]?.skill_upgrade_available)
    );

    let html = `<div class="eldora-profile-style-801160c3">
        <div class="eldora-skill-upgrade-page-heading">
            <div>
                <p>Grimório de Eldora</p>
                <h4>Aprimorar habilidades</h4>
            </div>
            <button type="button" class="eldora-skill-back" onclick="window.carregarMenuMagias()">← Habilidades</button>
        </div>
        <p class="eldora-skill-upgrade-intro">Cada nível aumenta em 4% a potência de dano, cura e bônus passivos. Habilidades de evolução de classe terão outro fluxo. Confira a fórmula antes de confirmar.</p>`;

    if (!skillsAprimoraveis.length) {
        html += `<div class="eldora-skill-upgrade-empty">Nenhuma habilidade comum aprendida e compatível com sua classe pode ser aprimorada. Habilidades de evolução de classe terão um fluxo próprio.</div>`;
    } else {
        html += `<div class="eldora-skill-upgrade-list">`;
        for (const [skillId, skillInst] of skillsAprimoraveis) {
            const info = window._skillsDataTemp[skillId] || {};
            const nome = info.display_name || skillId.replaceAll('_', ' ');
            const maxNivel = Number(info.skill_upgrade_max_level || 10);
            const bonusPorNivel = Number(info.skill_upgrade_bonus_per_level_pct || 4);
            const nivel = Math.max(1, Number(skillInst?.level || 1));
            const icon = info.icon || 'default_skill';
            const imagem = `https://raw.githubusercontent.com/Eldorabotpy/static-img/refs/heads/main/assets/sprites/skills/${icon}.png`;
            const fallback = 'https://raw.githubusercontent.com/Eldorabotpy/static-img/refs/heads/main/assets/sprites/skills/default_skill.png';
            const noMaximo = nivel >= maxNivel;
            html += `<article class="eldora-skill-upgrade-row">
                <img src="${imagem}" onerror="this.onerror=null;this.src='${fallback}'" alt="" loading="lazy">
                <div class="eldora-skill-upgrade-row-copy">
                    <strong>${nome}</strong>
                    <span>Nível ${nivel} de ${maxNivel} · potência +${(nivel - 1) * bonusPorNivel}%</span>
                </div>
                <button type="button" ${noMaximo ? 'disabled' : ''} onclick="window.abrirMenuAprimoramentoSkill('${skillId}')">${noMaximo ? 'Máximo' : 'Ver fórmula'}</button>
            </article>`;
        }
        html += `</div>`;
    }

    container.innerHTML = html + `</div>`;
};

window.aprimorarMochilaPerfil = async function() {
    const player = window.perfilDadosGlobais;
    const mochila = player?.mochila;
    if (!player || !mochila?.next_tier) return;
    const custo = Number(mochila.next_cost_gems || 0);
    const confirmado = await window.confirmarEldora(
        `Ampliar para ${Number(mochila.next_capacity).toLocaleString('pt-BR')} espaços por ${custo.toLocaleString('pt-BR')} gemas?`,
        'Melhorar mochila'
    );
    if (!confirmado) return;
    try {
        const headers = await window.portalSessionHeaders({ 'Content-Type': 'application/json' });
        const response = await fetch('/api/personagem/mochila/aprimorar', {
            method: 'POST',
            headers,
            body: JSON.stringify({ user_id: localStorage.getItem('jogadorEldoraID') })
        });
        const data = await response.json();
        if (!response.ok || !data.sucesso) throw new Error(data.erro || 'Não foi possível melhorar a mochila.');
        window.alertaEldora?.('Mochila ampliada', `${data.mochila.name}: ${data.mochila.capacity} espaços.`, 'sucesso');
        await carregarMeuPerfil();
    } catch (error) {
        window.alertaEldora?.('Mochila', error.message || 'Não foi possível ampliar a mochila.', 'erro');
    }
};

function garantirModalDetalhesSkill() {
    let modal = document.getElementById('modal-skill-detalhes');
    if (!modal) {
        modal = document.createElement('div');
        modal.id = 'modal-skill-detalhes';
        modal.classList.add('eldora-skill-modal');
        document.body.appendChild(modal);
    }
    return modal;
}

// 2. Janela Modal de Detalhes da Magia (CORREÇÃO DE IMAGEM)
window.abrirModalSkillDetalhes = function(skillId, infoDb, slotAtual) {
    let modal = document.getElementById('modal-skill-detalhes');
    if (modal) modal.remove();
    modal = garantirModalDetalhesSkill();

    const magiaExiste = infoDb && infoDb.display_name;
    const nome = magiaExiste ? infoDb.display_name : '⚠️ Magia Não Encontrada';
    const instanciaSkill = window._skillsPossuidasTemp?.[skillId];
    const nivelSkill = Math.max(1, Number(instanciaSkill?.level || 1));

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
    const botaoAprimorar = magiaExiste && infoDb.skill_upgrade_available
        ? `<button class="eldora-skill-action is-upgrade" onclick="window.abrirMenuAprimoramentoSkill('${skillId}')">Ver aprimoramento</button>`
        : '';

    if (slotAtual) {
        areaBotoes = `<button class="eldora-skill-action is-remove" onclick="window.processarEquiparSkill('', ${slotAtual})">Desequipar (Slot ${slotAtual})</button>${botaoAprimorar}`;
    } else {
        areaBotoes = `<button class="eldora-skill-action is-equip" onclick="window.iniciarEquiparSkill('${skillId}')" ${!magiaExiste ? 'disabled' : ''}>Equipar</button>${botaoAprimorar}`;
    }

    // Adicionei this.onerror=null para evitar que ele quebre de vez se o fallback também falhar
    modal.innerHTML = `
        <div class="eldora-profile-style-3395e2db">
            <div class="eldora-profile-style-8894607e">
                <img src="${imgUrlModal}" onerror="this.onerror=null; this.src='${fallbackIconModal}'" class="eldora-profile-style-2dbd2893">
                <div>
                    <h3 class="eldora-skill-modal-title ${magiaExiste ? '' : 'is-unavailable'}">${nome}</h3>
                    <div class="eldora-profile-style-2ed4b0fd">Mana: <span class="eldora-profile-style-c73cb885">${mana}</span> | Recarga: <span class="eldora-profile-style-e85027a3">${cooldown} turnos</span></div>
                    <div class="eldora-skill-modal-level">Nível ${nivelSkill}/10 · Potência +${(nivelSkill - 1) * 4}%</div>
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
window.carregarMaisItensMochila = function() {
    const estado = window.__perfilMochilaRender;
    const grid = document.getElementById('grid-mochila');
    if (!estado || !grid || estado.indice >= estado.itens.length) return;

    grid.querySelector('#btn-carregar-mais-mochila')?.remove();

    const lote = estado.itens.slice(estado.indice, estado.indice + estado.tamanhoLote);
    estado.indice += lote.length;

    const html = lote.map(item => {
        const raridade = String(
            item.raridade ?? item.rarity ?? item.base?.raridade ?? item.base?.rarity ??
            item.item_data?.raridade ?? item.item_data?.rarity ?? 'comum'
        ).trim().toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '')
            .replace(/[^a-z0-9_-]/g, '');
        const corBorda = estado.coresRaridade[raridade] || '#334155';

        return `
            <div class="eldora-item-slot" onclick="abrirModalItem('${item.id}', 'mochila')"
                 style="--rarity-border:${corBorda}">
                <img data-item-img="${item.id}" src="/static/assets/box.png" loading="lazy" decoding="async" onerror="this.hidden=true; if(this.nextElementSibling){this.nextElementSibling.classList.add('eldora-image-fallback','is-visible')}" class="eldora-profile-style-c8590c2b">
                <span class="eldora-profile-style-e6b19889">${item.emoji || '📦'}</span>
                <div class="eldora-item-quantity eldora-profile-style-6a5a7d0d">x${item.qtd || item.quantidade || 1}</div>
                ${window.renderRuneSockets?.(item) || ''}
                ${item.refino > 0 ? `<div class="eldora-item-refinement eldora-profile-style-7acfd725">+${item.refino}</div>` : ''}
            </div>
        `;
    }).join('');

    grid.insertAdjacentHTML('beforeend', html);

    const idsDoLote = new Map(lote.map(item => [String(item.id), item]));
    grid.querySelectorAll('img[data-item-img]:not([data-perfil-imagem-pronta])').forEach(img => {
        const item = idsDoLote.get(img.dataset.itemImg);
        if (!item) return;
        img.dataset.perfilImagemPronta = 'true';
        window.aplicarImagemPerfilEldora(img, item);
    });

    if (estado.indice < estado.itens.length) {
        const restantes = estado.itens.length - estado.indice;
        const botao = document.createElement('button');
        botao.id = 'btn-carregar-mais-mochila';
        botao.type = 'button';
        botao.textContent = `Carregar mais ${Math.min(estado.tamanhoLote, restantes)} · ${restantes} restantes`;
        botao.setAttribute('aria-label', `Carregar mais itens da mochila. ${restantes} restantes.`);
        botao.style.cssText = 'grid-column:1/-1;width:100%;min-height:44px;margin:8px 0;padding:10px 14px;border:1px solid rgba(201,164,92,.55);border-radius:10px;background:linear-gradient(180deg,#26344a,#152033);color:#f4ead2;font-weight:800;cursor:pointer;';
        botao.addEventListener('click', window.carregarMaisItensMochila);
        grid.appendChild(botao);
    }
};

window.filtrarMochila = function(filtro) {
    const aliases = { equips: 'combate', usaveis: 'consumiveis' };
    filtro = aliases[filtro] || filtro;
    if (!FILTROS_MOCHILA.some(categoria => categoria.id === filtro)) filtro = 'todos';
    window.perfilFiltroMochilaAtual = filtro;

    if (!window.perfilDadosGlobais || !window.perfilDadosGlobais.inventario) return;

    const inv = window.perfilDadosGlobais.inventario;
    const grid = document.getElementById('grid-mochila');
    if (!grid) return;

    // Mantém os filtros separados por uso e inclui tudo o que não tinha aba dedicada.
    const filtros = document.querySelectorAll('#filtros-mochila .eldora-inventory-filter');
    filtros.forEach(botao => {
        const ativo = botao.id === `btn-filtro-${filtro}`;
        botao.classList.toggle('is-active', ativo);
        botao.setAttribute('aria-pressed', String(ativo));
    });

    const busca = normalizarCategoriaMochila(window.perfilBuscaMochilaAtual);
    let filtrados = inv.filter(item => {
        const correspondeCategoria = filtro === 'todos' || classificarItemMochila(item) === filtro;
        if (!correspondeCategoria) return false;
        if (!busca) return true;
        const texto = normalizarCategoriaMochila([
            item.nome, item.display_name, item.base_id, item.item_id, item.id, item.tipo, item.categoria
        ].filter(Boolean).join(' '));
        return texto.includes(busca);
    });

    const contagem = document.getElementById('contagem-itens-mochila');
    if (contagem) contagem.textContent = `${filtrados.length} ${filtrados.length === 1 ? 'item' : 'itens'}`;

    grid.replaceChildren();

    if (filtrados.length === 0) {
        grid.innerHTML = `<div class="eldora-inventory-empty">${busca ? 'Nenhum item encontrado. Tente outro nome ou categoria.' : 'Mochila vazia nesta categoria.'}</div>`;
        window.__perfilMochilaRender = null;
        return;
    }

    const coresRaridade = {
        comum: '#94a3b8', common: '#94a3b8',
        incomum: '#22c55e', uncommon: '#22c55e', bom: '#22c55e', good: '#22c55e',
        raro: '#3b82f6', rare: '#3b82f6',
        epico: '#a855f7', epic: '#a855f7',
        lendario: '#eab308', legendary: '#eab308',
        mitico: '#06b6d4', mythic: '#06b6d4',
        unico: '#ef4444', unique: '#ef4444',
        divino: '#f0d48e', divine: '#f0d48e'
    };

    window.__perfilMochilaRender = {
        itens: filtrados,
        indice: 0,
        tamanhoLote: 60,
        coresRaridade
    };
    window.carregarMaisItensMochila();
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
        else if (t === 'skill_book' && itemData.skill_tome_purpose === 'upgrade') {
            const skillIdDoTomo = String(itemData.skill_id || '').replace(/[^a-zA-Z0-9_-]/g, '');
            botoesHtml = `
                <div class="eldora-profile-style-3198545b">Este tomo não ensina uma habilidade. Use-o no Grimório para aprimorar uma habilidade que você já aprendeu.</div>
                ${skillIdDoTomo ? `<button onclick="window.abrirSkillParaAprimorar('${skillIdDoTomo}')" class="eldora-profile-style-873b2342">Abrir no Grimório</button>` : ''}
            `;
        }
        else if (t === 'skill_book') {
            botoesHtml = `
                <div class="eldora-profile-style-3198545b">📘 Este tomo ensina uma habilidade compatível com sua classe. Depois, equipe-a no Grimório para usá-la em combate.</div>
                <button onclick="aprenderHabilidadePeloTomo('${itemData.id}', this)" class="eldora-profile-style-873b2342">Aprender habilidade</button>
            `;
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
        else if (['pergaminho_de_reparo', 'pergaminho_durabilidade'].includes(idReal)) {
            botoesHtml = `<button onclick="equiparPergaminhoReparoAtalho('${idReal}')" class="eldora-profile-style-50b8d325">Equipar no atalho 📜</button>`;
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

window.equiparPergaminhoReparoAtalho = async function(itemId) {
    const charId = localStorage.getItem("jogadorEldoraID");
    if (!charId) return;

    try {
        const res = await fetch('/api/personagem/equipar_pergaminho_reparo', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: charId, item_id: itemId })
        });
        const data = await res.json();

        if (!res.ok || !data.sucesso) {
            const mensagem = data.erro || "Não foi possível equipar o pergaminho.";
            if (window.alertaEldora) window.alertaEldora("Atalho de Reparo", mensagem, "erro");
            else window.avisoEldora(mensagem);
            return;
        }

        if (typeof window.fecharModalItem === 'function') window.fecharModalItem();
        if (typeof window.carregarMeuPerfil === 'function') window.carregarMeuPerfil();
        if (typeof window.atualizarHudCircular === 'function') window.atualizarHudCircular();
        if (typeof window.carregarDadosDoHUD === 'function') window.carregarDadosDoHUD();
        if (window.alertaEldora) {
            window.alertaEldora("Atalho de Reparo", "Pergaminho equipado no novo slot rápido.", "sucesso");
        }
    } catch (e) {
        console.error("Erro ao equipar pergaminho no atalho:", e);
        if (window.alertaEldora) window.alertaEldora("Atalho de Reparo", "Falha ao equipar o pergaminho.", "erro");
    }
};

window.aprenderHabilidadePeloTomo = async function(itemId, botao) {
    const charId = localStorage.getItem("jogadorEldoraID");
    if (!charId) {
        window.avisoEldora("Entre novamente para aprender uma habilidade.");
        return;
    }
    if (!window.portalSessionHeaders) {
        window.avisoEldora("A sessão expirou. Atualize a página e tente novamente.");
        return;
    }

    if (botao) {
        botao.disabled = true;
        botao.textContent = "Decifrando tomo…";
    }

    try {
        const headers = await window.portalSessionHeaders({ 'Content-Type': 'application/json' });
        const res = await fetch('/api/personagem/aprender_habilidade', {
            method: 'POST',
            headers,
            body: JSON.stringify({ user_id: charId, item_id: itemId })
        });
        const data = await res.json();
        if (!res.ok || !data.sucesso) {
            throw new Error(data.erro || "Não foi possível aprender a habilidade.");
        }

        fecharModalItem();
        if (typeof carregarMeuPerfil === 'function') await carregarMeuPerfil();
        if (typeof window.carregarMenuMagias === 'function') await window.carregarMenuMagias();
        if (window.alertaEldora) {
            window.alertaEldora("Habilidade aprendida", data.msg || "A habilidade foi adicionada ao Grimório.", "sucesso");
        }
    } catch (erro) {
        if (botao) {
            botao.disabled = false;
            botao.textContent = "Aprender habilidade";
        }
        if (window.alertaEldora) window.alertaEldora("Não foi possível aprender", erro.message, "erro");
        else window.avisoEldora(erro.message);
    }
};

const escaparHtmlSkillUpgrade = valor => String(valor ?? '').replace(/[&<>"']/g, caractere => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
}[caractere]));
const numeroSkillUpgrade = valor => Number(valor || 0).toLocaleString('pt-BR');
const URL_BASE_IMAGENS_SKILL_UPGRADE = 'https://raw.githubusercontent.com/Eldorabotpy/static-img/main/assets/';
const CAMINHOS_IMAGENS_SKILL_UPGRADE = {
    ouro: 'perfil/ouro.png',
    pedra_de_aprimoramento: 'itens/consumiveis/pedra_de_aprimoramento.png',
    cristal_mana_bruto: 'itens/materiais/cristal_mana_bruto.png',
    essencia_purificadora: 'itens/materiais/essencia_purificadora.png',
};
const urlImagemCustoSkillUpgrade = itemId => {
    const id = String(itemId || '');
    const caminho = CAMINHOS_IMAGENS_SKILL_UPGRADE[id]
        || (id.startsWith('tomo_') ? `itens/materiais/${encodeURIComponent(id)}.png` : '');
    return caminho ? `${URL_BASE_IMAGENS_SKILL_UPGRADE}${caminho}` : '';
};
const htmlIconeCustoSkillUpgrade = (itemId, fallback) => {
    const imagem = urlImagemCustoSkillUpgrade(itemId);
    const textoFallback = escaparHtmlSkillUpgrade(fallback || '📦');
    return imagem
        ? `<img src="${escaparHtmlSkillUpgrade(imagem)}" data-skill-cost-image data-fallback="${textoFallback}" alt="" loading="lazy" decoding="async">`
        : `<span class="eldora-skill-cost-fallback" aria-hidden="true">${textoFallback}</span>`;
};

window.abrirMenuAprimoramentoSkill = async function(skillId) {
    let modal = null;
    let info = {};
    const requestId = (window.__skillUpgradeFormulaRequestId || 0) + 1;
    window.__skillUpgradeFormulaRequestId = requestId;

    try {
        const charId = localStorage.getItem("jogadorEldoraID");
        if (!charId) throw new Error("Entre novamente para consultar a fórmula da habilidade.");

        modal = garantirModalDetalhesSkill();
        modal.setAttribute('role', 'dialog');
        modal.setAttribute('aria-modal', 'true');
        modal.setAttribute('aria-label', 'Custos para aprimorar a habilidade');
        modal.setAttribute('aria-busy', 'true');
        modal.innerHTML = `<div class="eldora-skill-upgrade-loading" role="status" aria-live="polite">Consultando materiais e fórmula…</div>`;

        info = window._skillsDataTemp?.[skillId] || {};
        const nome = escaparHtmlSkillUpgrade(info.display_name || skillId);
        const nomeIcone = escaparHtmlSkillUpgrade(info.icon || 'default_skill');
        const imagem = `https://raw.githubusercontent.com/Eldorabotpy/static-img/refs/heads/main/assets/sprites/skills/${nomeIcone}.png`;
        const fallback = 'https://raw.githubusercontent.com/Eldorabotpy/static-img/refs/heads/main/assets/sprites/skills/default_skill.png';
        if (typeof window.portalSessionHeaders !== 'function') {
            throw new Error("A sessão expirou. Atualize a página e tente novamente.");
        }
        const headers = await window.portalSessionHeaders();
        const url = `/api/personagem/${encodeURIComponent(charId)}/habilidades/${encodeURIComponent(skillId)}/aprimoramento`;
        const res = await fetch(url, { headers });
        const data = await res.json();
        if (!res.ok || !data.sucesso) throw new Error(data.erro || 'Não foi possível consultar os requisitos.');
        if (requestId !== window.__skillUpgradeFormulaRequestId || !modal.isConnected) return;

        const formula = data.formula || {};
        const ouro = formula.gold || {};
        const nivelAtual = Number(formula.current_level || 1);
        const maximo = nivelAtual >= Number(formula.max_level || 10);
        const proximoNivel = formula.next_level ? Number(formula.next_level) : nivelAtual;
        const ouroHtml = `<li class="eldora-skill-cost-row ${ouro.enough ? 'has-enough' : 'needs-more'}">
            <span class="eldora-skill-cost-icon">${htmlIconeCustoSkillUpgrade('ouro', '🪙')}</span>
            <span class="eldora-skill-cost-copy"><strong>Ouro</strong><small>Em mãos: ${numeroSkillUpgrade(ouro.owned)}</small></span>
            <b><small>PRECISA</small>${numeroSkillUpgrade(ouro.required)}</b>
        </li>`;
        const itensHtml = (formula.items || []).map(item => `<li class="eldora-skill-cost-row ${item.enough ? 'has-enough' : 'needs-more'}">
            <span class="eldora-skill-cost-icon">${htmlIconeCustoSkillUpgrade(item.id, item.emoji || '📦')}</span>
            <span class="eldora-skill-cost-copy"><strong>${escaparHtmlSkillUpgrade(item.name)}</strong><small>Em mãos: ${numeroSkillUpgrade(item.owned)}</small></span>
            <b><small>PRECISA</small>${numeroSkillUpgrade(item.required)}</b>
        </li>`).join('');
        const progresso = formula.next_level
            ? `Nível ${nivelAtual} <span>→</span> ${formula.next_level}`
            : `Nível ${nivelAtual} · máximo`;
        const potencia = formula.next_level
            ? `Potência +${formula.current_power_pct || 0}% → +${formula.next_power_pct || 0}%`
            : `Potência +${formula.current_power_pct || 0}%`;
        const faltasAprimoramento = [];
        if (!ouro.enough && !maximo) {
            faltasAprimoramento.push(`${numeroSkillUpgrade(Math.max(0, ouro.required - ouro.owned))} ouro`);
        }
        for (const item of formula.items || []) {
            if (!item.enough) {
                faltasAprimoramento.push(`${item.name} ×${numeroSkillUpgrade(Math.max(0, item.required - item.owned))}`);
            }
        }
        const statusAprimoramento = maximo
            ? 'Esta habilidade já está no nível máximo.'
            : formula.can_upgrade
                ? 'Você tem tudo que precisa para o próximo nível.'
                : faltasAprimoramento.length
                    ? `Faltam: ${faltasAprimoramento.join(', ')}.`
                    : formula.reason || 'Confira os materiais necessários.';
        const custosHtml = maximo
            ? '<li class="eldora-skill-cost-empty">Não há outro nível para aprimorar.</li>'
            : `${ouroHtml}${itensHtml || '<li class="eldora-skill-cost-empty">Materiais indisponíveis para esta habilidade.</li>'}`;
        const estadoBotao = formula.can_upgrade ? 'Confirmar aprimoramento' : (maximo ? 'Nível máximo' : 'Faltam materiais');

        modal.innerHTML = `<div class="eldora-skill-upgrade-heading">
                <button type="button" class="eldora-skill-upgrade-back" data-skill-upgrade-back>← Voltar</button>
                <div class="eldora-skill-upgrade-heading-copy"><span>APRIMORAMENTO</span><h3>${nome}</h3></div>
                <button type="button" class="eldora-skill-upgrade-close" aria-label="Fechar" data-skill-upgrade-close>×</button>
            </div>
            <div class="eldora-skill-upgrade-summary">
                <img src="${imagem}" onerror="this.onerror=null;this.src='${fallback}'" alt="" class="eldora-skill-upgrade-icon">
                <div><strong>${progresso}</strong><span>${potencia}</span></div>
            </div>
            <section class="eldora-skill-cost-panel" aria-label="Materiais necessários para o próximo nível">
                <header><h4>Materiais do próximo nível</h4><span>Do nível ${nivelAtual} para o ${proximoNivel}</span></header>
                <ul>${custosHtml}</ul>
            </section>
            <p class="eldora-skill-upgrade-status ${formula.can_upgrade ? 'is-ready' : 'is-missing'}" role="status" aria-live="polite">${escaparHtmlSkillUpgrade(statusAprimoramento)}</p>
            <button type="button" class="eldora-skill-action is-upgrade" data-skill-upgrade-confirm ${formula.can_upgrade ? '' : 'disabled'}>${estadoBotao}</button>`;
        modal.setAttribute('aria-busy', 'false');

        modal.querySelectorAll('[data-skill-cost-image]').forEach(imagemItem => {
            imagemItem.addEventListener('error', () => {
                const fallbackItem = document.createElement('span');
                fallbackItem.className = 'eldora-skill-cost-fallback';
                fallbackItem.setAttribute('aria-hidden', 'true');
                fallbackItem.textContent = imagemItem.dataset.fallback || '📦';
                imagemItem.replaceWith(fallbackItem);
            }, { once: true });
        });

        modal.querySelector('[data-skill-upgrade-back]')?.addEventListener('click', () => {
            const equipadas = window._skillsEquipadasTemp || {};
            const slot = Object.keys(equipadas).find(key => equipadas[key] === skillId);
            window.abrirModalSkillDetalhes(skillId, info, slot ? Number(slot.replace('slot_', '')) : null);
        });
        modal.querySelector('[data-skill-upgrade-close]')?.addEventListener('click', () => modal.remove());
        const confirmar = modal.querySelector('[data-skill-upgrade-confirm]');
        if (confirmar && formula.can_upgrade) {
            confirmar.addEventListener('click', () => window.aprimorarSkillPeloTomo(skillId, confirmar));
        }
    } catch (erro) {
        if (!modal) modal = garantirModalDetalhesSkill();
        if (requestId !== window.__skillUpgradeFormulaRequestId || !modal.isConnected) return;
        modal.setAttribute('role', 'dialog');
        modal.setAttribute('aria-modal', 'true');
        modal.setAttribute('aria-label', 'Custos para aprimorar a habilidade');
        modal.setAttribute('aria-busy', 'false');
        modal.innerHTML = `<div class="eldora-skill-upgrade-heading">
                <button type="button" class="eldora-skill-upgrade-back" data-skill-upgrade-back>← Voltar</button>
                <h3>Fórmula indisponível</h3>
                <button type="button" class="eldora-skill-upgrade-close" aria-label="Fechar" data-skill-upgrade-close>×</button>
            </div><p class="eldora-skill-upgrade-status is-missing" data-skill-upgrade-error role="alert"></p>`;
        modal.querySelector('[data-skill-upgrade-error]').textContent = erro?.message || 'Não foi possível consultar os requisitos.';
        modal.querySelector('[data-skill-upgrade-back]')?.addEventListener('click', () => {
            const equipadas = window._skillsEquipadasTemp || {};
            const slot = Object.keys(equipadas).find(key => equipadas[key] === skillId);
            window.abrirModalSkillDetalhes(skillId, info, slot ? Number(slot.replace('slot_', '')) : null);
        });
        modal.querySelector('[data-skill-upgrade-close]')?.addEventListener('click', () => modal.remove());
    }
};

window.aprimorarSkillPeloTomo = async function(skillId, botao) {
    const charId = localStorage.getItem("jogadorEldoraID");
    if (!charId || !window.portalSessionHeaders) {
        window.avisoEldora("Entre novamente para aprimorar uma habilidade.");
        return;
    }
    if (botao) {
        botao.disabled = true;
        botao.textContent = "Canalizando…";
    }
    try {
        const headers = await window.portalSessionHeaders({ 'Content-Type': 'application/json' });
        const res = await fetch('/api/personagem/aprimorar_habilidade', {
            method: 'POST',
            headers,
            body: JSON.stringify({ user_id: charId, skill_id: skillId })
        });
        const data = await res.json();
        if (!res.ok || !data.sucesso) throw new Error(data.erro || data.mensagem || "Não foi possível aprimorar a habilidade.");
        document.getElementById('modal-skill-detalhes')?.remove();
        if (typeof carregarMeuPerfil === 'function') await carregarMeuPerfil();
        else if (typeof window.carregarMenuMagias === 'function') await window.carregarMenuMagias();
        if (window.perfilAbaAtual === 'magias' && typeof window.abrirPainelAprimoramentoSkills === 'function') {
            window.abrirPainelAprimoramentoSkills();
        }
        if (window.alertaEldora) window.alertaEldora("Habilidade aprimorada", data.mensagem || "O nível da habilidade aumentou.", "sucesso");
    } catch (erro) {
        if (botao) {
            botao.disabled = false;
            botao.textContent = "Confirmar aprimoramento";
        }
        if (window.alertaEldora) window.alertaEldora("Não foi possível aprimorar", erro.message, "erro");
        else window.avisoEldora(erro.message);
    }
};

window.abrirSkillParaAprimorar = async function(skillId) {
    if (typeof window.fecharModalItem === 'function') window.fecharModalItem();
    if (typeof window.alternarAbaPerfil === 'function') {
        await window.alternarAbaPerfil('magias');
    } else if (typeof window.carregarMenuMagias === 'function') {
        await window.carregarMenuMagias();
    }
    const info = window._skillsDataTemp?.[skillId];
    if (!info || !window.abrirModalSkillDetalhes) {
        window.avisoEldora("Esta habilidade ainda não está no seu Grimório.");
        return;
    }
    const equipadas = window._skillsEquipadasTemp || {};
    const slot = Object.keys(equipadas).find(key => equipadas[key] === skillId);
    window.abrirModalSkillDetalhes(skillId, info, slot ? Number(slot.replace('slot_', '')) : null);
};

window.usarPergaminhoReparoRapido = async function() {
    const charId = localStorage.getItem("jogadorEldoraID");
    if (!charId || window.__usandoPergaminhoReparoRapido) return;

    window.__usandoPergaminhoReparoRapido = true;
    const slot = document.getElementById("hud-slot-pergaminho-reparo");
    if (slot) slot.style.pointerEvents = "none";

    try {
        const res = await fetch('/api/personagem/usar_pergaminho_reparo_rapido', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: charId })
        });
        const data = await res.json();

        if (!res.ok || !data.sucesso) {
            const mensagem = data.erro || "Não foi possível usar o pergaminho.";
            if (window.alertaEldora) window.alertaEldora("Atalho de Reparo", mensagem, "erro");
            else window.avisoEldora(mensagem);
            return;
        }

        if (typeof window.carregarMeuPerfil === 'function') window.carregarMeuPerfil();
        if (typeof window.atualizarHudCircular === 'function') window.atualizarHudCircular();
        if (typeof window.carregarDadosDoHUD === 'function') window.carregarDadosDoHUD();
        if (window.alertaEldora) {
            window.alertaEldora("Reparo Concluído!", data.msg || "Equipamentos reparados com sucesso!", "sucesso");
        }
    } catch (e) {
        console.error("Erro ao usar pergaminho rápido:", e);
        if (window.alertaEldora) window.alertaEldora("Atalho de Reparo", "Falha ao usar o pergaminho.", "erro");
    } finally {
        window.__usandoPergaminhoReparoRapido = false;
        if (slot) slot.style.pointerEvents = "auto";
    }
};

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

