// /static/js/forja.js

const GITHUB_BASE_ITENS = "https://raw.githubusercontent.com/Eldorabotpy/static-img/refs/heads/main/assets/itens/";

function descobrirPastaForja(receita, idReceita) {
    let outputId = idReceita; 
    if (receita.result_base_id) outputId = receita.result_base_id;
    else if (receita.output) outputId = receita.output;
    else if (receita.outputs && Object.keys(receita.outputs).length > 0) outputId = Object.keys(receita.outputs)[0];

    let pasta = 'equipamentos'; 
    const nomeItem = outputId.toLowerCase();
    const idRec = idReceita.toLowerCase();

    // 🛡️ REGRA DE OURO: Se o Armeiro ou Alfaiate fazem, é sempre Arma/Armadura (Equipamento)!
    let prof = receita.profession || receita.profession_req || "";
    if (Array.isArray(prof)) prof = prof.join(" ");
    prof = prof.toLowerCase();

    if (prof.includes('armeiro') || prof.includes('alfaiate')) {
        return { pasta: 'equipamentos', outputId, idReceita };
    }

    // Regra normal para ferramentas de coleta do Ferreiro
    const isTool = receita.type === 'tool' || 
                   receita.required_tool_type === 'tool' ||
                   nomeItem.includes('martelo') ||
                   nomeItem.includes('faca') ||
                   nomeItem.includes('machado') ||
                   nomeItem.includes('picareta') ||
                   nomeItem.includes('foice') ||
                   nomeItem.includes('frasco') ||
                   nomeItem.includes('ferramentas') ||
                   nomeItem.includes('extrator') ||
                   nomeItem.includes('coletor') ||
                   nomeItem.includes('cubo') ||
                   idRec.includes('martelo') ||
                   idRec.includes('machado');

    if (isTool) {
        pasta = 'ferramentas';
    }

    return { pasta, outputId, idReceita };
}

function getNivelRefinoItem(item) {
    return parseInt(
        item?.refino ??
        item?.upgrade_level ??
        item?.upgrade ??
        item?.nivel_refino ??
        0
    ) || 0;
}

const UPGRADE_STONE_ITEM_ID = "pedra_de_aprimoramento";
const UPGRADE_PROTECTION_ITEM_ID = "sigilo_de_protecao";

const UPGRADE_SKIP_RECIPE_MATERIALS = new Set([
    "nucleo_de_forja",
    "nucleo_forja_fraco",
    "carvao",
    "martelo_gasto",
    "fluxo_solda"
]);

function getChanceSucessoMelhoria(proximoNivel) {
    const n = parseInt(proximoNivel || 1);

    if (n <= 3) return 100;
    if (n <= 5) return 90;
    if (n <= 10) return 75;
    if (n <= 15) return 60;
    if (n <= 20) return 45;

    return 30;
}

function getMultiplicadorMateriaisMelhoria(proximoNivel) {
    const n = parseInt(proximoNivel || 1);

    if (n <= 3) return 0.25;
    if (n <= 5) return 0.35;
    if (n <= 10) return 0.50;
    if (n <= 15) return 0.65;
    if (n <= 20) return 0.80;

    return 1.00;
}

function normalizarProfissaoForja(valor) {
    return String(valor || "")
        .trim()
        .toLowerCase()
        .normalize("NFD")
        .replace(/[\u0300-\u036f]/g, "");
}

function getProfissaoReceitaForja(receita, fallback = "ferreiro") {
    if (!receita || typeof receita !== "object") {
        return normalizarProfissaoForja(fallback);
    }

    let raw =
        receita.profession ||
        receita.profession_req ||
        receita.required_tool_type ||
        receita.tool_type ||
        fallback;

    if (Array.isArray(raw)) raw = raw[0];

    return normalizarProfissaoForja(raw || fallback);
}

function getProfissaoItemForja(item, fallback = "ferreiro") {
    const baseId = item?.base_id || item?.item_id || item?.id;
    const receitaInfo = buscarReceitaDoItemForja(baseId);

    if (receitaInfo?.receita) {
        return getProfissaoReceitaForja(receitaInfo.receita, fallback);
    }

    return normalizarProfissaoForja(fallback);
}

function getNivelProfissaoForja(profKey) {
    const p = window.perfilDadosGlobais || {};
    const key = normalizarProfissaoForja(profKey);

    const learned = p.learned_professions || {};
    const profData = learned[key];

    if (profData && typeof profData === "object") {
        return Math.max(1, parseInt(profData.level || 1) || 1);
    }

    const legacy = p.profession || {};
    const legacyKey = normalizarProfissaoForja(legacy.key || legacy.type);

    if (legacyKey === key) {
        return Math.max(1, parseInt(legacy.level || 1) || 1);
    }

    return 1;
}

function getFerramentaEquipadaForja(profKey) {
    const p = window.perfilDadosGlobais || {};
    const key = normalizarProfissaoForja(profKey);
    const equips = p.equipamentos || [];

    return equips.find(e => {
        if (!e || e.vazio) return false;

        const slotProf = normalizarProfissaoForja(e.slot_profissao);
        const toolType = normalizarProfissaoForja(e.tool_type);
        const slot = normalizarProfissaoForja(e.slot);

        return (
            slotProf === key ||
            toolType === key ||
            slot === `tool_${key}` ||
            slot === "tool"
        );
    }) || null;
}

function getTierFerramentaForja(tool) {
    if (!tool) return 1;

    const direto = parseInt(tool.tier || tool.tool_tier || 0);
    if (direto > 0) return direto;

    const baseId = String(tool.base_id || tool.id || "").toLowerCase();
    const achou = baseId.match(/_t([1-5])\b/);

    if (achou) return parseInt(achou[1]) || 1;

    return 1;
}

function calcularTempoTrabalhoForjaLocal(baseSeconds, profKey) {
    const base = Math.max(1, parseInt(baseSeconds || 1) || 1);
    const key = normalizarProfissaoForja(profKey || "ferreiro");

    const nivelProf = getNivelProfissaoForja(key);
    const ferramenta = getFerramentaEquipadaForja(key);

    const bonusProf = Math.min(0.25, nivelProf * 0.005);

    const tier = getTierFerramentaForja(ferramenta);
    const bonusTier = Math.min(0.20, Math.max(0, tier - 1) * 0.05);

    const upgradeFerramenta = getNivelRefinoItem(ferramenta);
    const bonusUpgrade = Math.min(0.10, upgradeFerramenta * 0.01);

    const reducaoTotal = Math.min(0.50, bonusProf + bonusTier + bonusUpgrade);

    return {
        duration_seconds: Math.max(1, Math.floor(base * (1.0 - reducaoTotal))),
        base_seconds: base,
        profession_key: key,
        profession_level: nivelProf,
        tool_tier: tier,
        tool_upgrade: upgradeFerramenta,
        total_reduction: reducaoTotal
    };
}

function getMateriaisReceitaForja(receita) {
    if (!receita || typeof receita !== "object") return {};

    return receita.inputs || receita.materials || receita.ingredients || {};
}

function calcularCustoMelhoriaLocal(item) {
    const nivelAtual = getNivelRefinoItem(item);
    const proximo = nivelAtual + 1;

    const custo = {};

    // Pedra obrigatória.
    custo[UPGRADE_STONE_ITEM_ID] = 1 + Math.floor((proximo - 1) / 5);

    // Materiais da receita original do item.
    const baseId = item?.base_id || item?.item_id || item?.id;
    const receitaInfo = buscarReceitaDoItemForja(baseId);
    const receita = receitaInfo?.receita || null;

    const materiaisReceita = getMateriaisReceitaForja(receita);
    const mult = getMultiplicadorMateriaisMelhoria(proximo);

    for (const [matId, qtdOriginal] of Object.entries(materiaisReceita)) {
        if (UPGRADE_SKIP_RECIPE_MATERIALS.has(matId)) continue;

        const qtd = Math.max(1, Math.ceil(Number(qtdOriginal || 1) * mult));
        custo[matId] = (custo[matId] || 0) + qtd;
    }

    // Sigilo opcional, se depois ligarmos checkbox.
    if (ForjaEngine?.usarSigiloMelhoria) {
        custo[UPGRADE_PROTECTION_ITEM_ID] = (custo[UPGRADE_PROTECTION_ITEM_ID] || 0) + 1;
    }

    return custo;
}

function getQtdMaterialInventario(matId) {
    const p = window.perfilDadosGlobais || {};
    const inv = p.inventario || p.inventory || [];

    let total = 0;

    if (Array.isArray(inv)) {
        inv.forEach(i => {
            if (!i) return;

            const base = i.base_id || i.id;
            if (base === matId) {
                total += parseInt(i.qtd || i.quantity || i.quantidade || 0) || 0;
            }
        });

        return total;
    }

    if (typeof inv === "object") {
        for (const [uid, obj] of Object.entries(inv)) {
            if (obj && typeof obj === "object") {
                const base = obj.base_id || uid;
                if (base === matId) {
                    total += parseInt(obj.quantity || obj.qtd || 1) || 0;
                }
            } else if (uid === matId) {
                total += parseInt(obj || 0) || 0;
            }
        }
    }

    return total;
}

function buscarReceitaDoItemForja(baseId) {
    if (!baseId || !ForjaEngine || !ForjaEngine.receitas) return null;

    for (const [recipeId, receita] of Object.entries(ForjaEngine.receitas)) {
        const outputId =
            receita.result_base_id ||
            receita.output ||
            (receita.outputs && Object.keys(receita.outputs)[0]) ||
            "";

        if (outputId === baseId) {
            return { recipeId, receita };
        }
    }

    return null;
}

const DISMANTLE_SKIP_RECIPE_MATERIALS = new Set([
    "nucleo_forja_fraco",
    "nucleo_de_forja",
    "carvao",
    "martelo_gasto",
    "fluxo_solda"
]);

function calcularFallbackDesmonteLocal(raridade) {
    const r = String(raridade || "comum").toLowerCase();

    const tabela = {
        comum: { po_de_ferro: 2 },
        incomum: { po_de_ferro: 4, couro_tratado: 1 },
        bom: { po_de_ferro: 4, couro_tratado: 1 },
        raro: { cristal_bruto: 1, po_de_ferro: 5 },
        epico: { essencia_magica: 1 },
        lendario: { alma_do_dragao: 1 }
    };

    return tabela[r] || { sucata: 1 };
}

function calcularPreviewDesmonteLocal(item) {
    const baseId = item?.base_id || item?.item_id || item?.id;
    const receitaInfo = buscarReceitaDoItemForja(baseId);
    const receita = receitaInfo?.receita || null;

    const retorno = {};

    if (receita) {
        const materiais = getMateriaisReceitaForja(receita);

        for (const [matId, qtdOriginal] of Object.entries(materiais)) {
            if (DISMANTLE_SKIP_RECIPE_MATERIALS.has(matId)) continue;

            const qtd = Math.max(1, Math.ceil(Number(qtdOriginal || 1) * 0.5));
            retorno[matId] = (retorno[matId] || 0) + qtd;
        }

        return retorno;
    }

    return calcularFallbackDesmonteLocal(item?.raridade || item?.rarity || "comum");
}

function getPastasPossiveisItemForja(item) {
    const tipo = String(item?.tipo || item?.type || "").toLowerCase();
    const baseId = String(item?.base_id || item?.id || "").toLowerCase();
    const nome = String(item?.nome || "").toLowerCase();

    const isFerramenta =
        tipo.includes("tool") ||
        tipo.includes("ferramenta") ||
        tipo.includes("lenhador") ||
        tipo.includes("minerador") ||
        tipo.includes("colhedor") ||
        tipo.includes("esfolador") ||
        baseId.includes("martelo") ||
        baseId.includes("faca") ||
        baseId.includes("machado") ||
        baseId.includes("picareta") ||
        baseId.includes("foice") ||
        nome.includes("martelo") ||
        nome.includes("faca") ||
        nome.includes("machado") ||
        nome.includes("picareta") ||
        nome.includes("foice");

    if (isFerramenta) {
        return ["ferramentas", "equipamentos", "materiais"];
    }

    return ["equipamentos", "ferramentas", "materiais"];
}

function getCaminhosImagemItemForja(item) {
    const baseId = item?.base_id || item?.id || "";
    const idsPossiveis = [];

    if (baseId) idsPossiveis.push(baseId);

    const receitaInfo = buscarReceitaDoItemForja(baseId);
    if (receitaInfo?.recipeId) {
        idsPossiveis.push(receitaInfo.recipeId);
    }

    const pastas = getPastasPossiveisItemForja(item);
    const caminhos = [];

    for (const pasta of pastas) {
        for (const id of idsPossiveis) {
            if (!id) continue;
            caminhos.push(`${GITHUB_BASE_ITENS}${pasta}/${id}.png`);
        }
    }

    // Remove repetidos e deixa o baú só no final.
    return [...new Set(caminhos)].concat(["/static/assets/box.png"]);
}

function aplicarImagemItemForja(imgEl, item) {
    if (!imgEl) return;

    const caminhos = getCaminhosImagemItemForja(item);
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

    imgEl.src = caminhos[0] || "/static/assets/box.png";
}
const FORJA_MAT_INFO = {
    pedra_de_aprimoramento: {
        nome: "Pedra de Aprimoramento",
        emoji: "✨",
        pastas: ["consumiveis", "materiais", "especiais"]
    },
    sigilo_de_protecao: {
        nome: "Sigilo de Proteção",
        emoji: "🛡️",
        pastas: ["consumiveis", "materiais", "especiais"]
    },
    pergaminho_de_reparo: {
        nome: "Pergaminho de Reparo",
        emoji: "📜",
        pastas: ["consumiveis", "materiais", "especiais"]
    },
    nucleo_de_forja: {
        nome: "Núcleo de Forja",
        emoji: "🔥",
        pastas: ["consumiveis", "materiais", "especiais"]
    }
};

function getNomeMaterialForja(matId) {
    return FORJA_MAT_INFO[matId]?.nome || String(matId || "").replace(/_/g, " ");
}

function getEmojiMaterialForja(matId) {
    return FORJA_MAT_INFO[matId]?.emoji || "📦";
}

function getCaminhosImagemMaterialForja(matId) {
    const info = FORJA_MAT_INFO[matId] || {};
    const pastas = info.pastas || ["materiais", "consumiveis", "equipamentos", "ferramentas"];

    const caminhos = [];

    pastas.forEach(pasta => {
        caminhos.push(`${GITHUB_BASE_ITENS}${pasta}/${matId}.png`);
    });

    caminhos.push("/static/assets/box.png");

    return [...new Set(caminhos)];
}

function aplicarImagemMaterialForja(imgEl, matId) {
    if (!imgEl) return;

    const caminhos = getCaminhosImagemMaterialForja(matId);
    let index = 0;

    imgEl.onerror = function() {
        index++;

        if (index < caminhos.length) {
            this.src = caminhos[index];
        } else {
            const span = document.createElement("span");
            span.textContent = getEmojiMaterialForja(matId);
            span.style.fontSize = "22px";
            span.style.width = "24px";
            span.style.height = "24px";
            span.style.display = "inline-flex";
            span.style.alignItems = "center";
            span.style.justifyContent = "center";
            this.replaceWith(span);
        }
    };

    imgEl.src = caminhos[0];
}
const ForjaEngine = {
    receitas: {},
    unlocksGuilda: new Set(),
    profSelecionada: null,
    receitaSelecionada: null,
    itemDesmontarSelecionado: null,
    itemMelhorarSelecionado: null,
    usarSigiloMelhoria: false,

    async iniciar() {
        try {
            const charId = localStorage.getItem("jogadorEldoraID");

            const resReceitas = await fetch(
                '/api/crafting/recipes',
                {
                    cache: 'no-store'
                }
            );

            this.receitas = await resReceitas.json();
            this.unlocksGuilda = new Set();

            if (charId) {
                try {
                    const resLoja = await fetch(
                        `/api/guild/loja/${encodeURIComponent(charId)}?t=${Date.now()}`,
                        {
                            method: 'GET',
                            cache: 'no-store'
                        }
                    );

                    const dadosLoja = await resLoja.json();

                    if (dadosLoja.success) {
                        const desbloqueios = Array.isArray(
                            dadosLoja.receitas_desbloqueadas
                        )
                            ? dadosLoja.receitas_desbloqueadas
                            : [];

                        this.unlocksGuilda = new Set(
                            desbloqueios
                                .map(id => String(id || "").trim())
                                .filter(Boolean)
                        );
                    }

                } catch (erroLoja) {
                    console.warn(
                        "⚠️ Não foi possível consultar os desbloqueios da Guilda:",
                        erroLoja
                    );
                }
            }

            this.definirAbaInicial();
            ForjaUI.renderizarTudo();

        } catch (e) {
            console.error(
                "Erro fatal ao carregar Forja:",
                e
            );
        }
    },

    receitaGuildaEstaDesbloqueada(receita) {
        if (!receita || typeof receita !== "object") {
            return true;
        }

        const unlockId = String(
            receita.unlock_id || ""
        ).trim();

        if (!unlockId) {
            return true;
        }

        return this.unlocksGuilda.has(
            unlockId
        );
    },

    definirAbaInicial() {

        const profs = this.getProfissoesJogador();
        if (profs.length > 0 && !this.profSelecionada) {
            this.profSelecionada = profs[0];
        }
    },

    getProfissoesJogador() {
        const p = window.perfilDadosGlobais;
        const permitidas = ['ferreiro', 'armeiro', 'joalheiro', 'alfaiate'];
        let profs = [];

        if (p) {
            let conhecidas = p.learned_professions || {};
            if (p.profession?.key) conhecidas[p.profession.key] = p.profession;
        
            profs = Object.keys(conhecidas)
                .map(k => k.toLowerCase())
                .filter(k => permitidas.includes(k));
        }

        // A Forja sempre mostra melhorar e desmontar.
        if (!profs.includes('melhorar')) {
            profs.push('melhorar');
        }

        if (!profs.includes('desmontar')) {
            profs.push('desmontar');
        }
    
        return profs;
    },

    getReceitasDaAbaAtual() {
        if (this.profSelecionada === 'desmontar') return {};
        if (this.profSelecionada === 'melhorar') return {};
    
        let filtradas = {};
        let profAtiva = this.profSelecionada ? this.profSelecionada.toLowerCase() : "";

        for (let id in this.receitas) {
            let receita = this.receitas[id];
            let profRaw = receita.profession || receita.profession_req;
            if (!profRaw) continue; 
            let profMatch = Array.isArray(profRaw) ? profRaw.some(p => p.toLowerCase() === profAtiva) : (profRaw.toLowerCase() === profAtiva);
            if (profMatch) filtradas[id] = receita;
        }
        return filtradas;
    },

    getItensParaDesmontar() {
        const p = window.perfilDadosGlobais;
        // Se o inventário ainda não carregou, retorna vazio
        if (!p || !p.inventario) return [];
        
        // 1. Pega os IDs únicos de tudo o que está equipado no corpo do personagem
        const equipados = p.equipamentos.map(e => e.uid);
        
        // 2. Filtra a mochila procurando o que é reciclável
        return p.inventario.filter(i => {
            const t = (i.tipo || "").toLowerCase();
            
            // A lista completa e atualizada de tudo o que pode ser desmontado!
            const isEquipOrTool = [
                'weapon', 'armor', 'helmet', 'boots', 'ring', 'necklace', 'earring', 
                'equipamento', 'arma', 'armadura', 
                'tool', 'ferramenta', 'lenhador', 'minerador', 'colhedor', 'esfolador', 
                'ferreiro', 'armeiro', 'alfaiate', 'joalheiro', 'curtidor'
            ].includes(t);
            
            // Só aparece na lista se for equipamento/ferramenta E NÃO estiver equipado
            return isEquipOrTool && !equipados.includes(i.id);
        });
    },
    getItensParaMelhorar() {
        const p = window.perfilDadosGlobais;
        if (!p || !p.equipamentos) return [];

        return (p.equipamentos || []).filter(i => {
            if (!i || i.vazio) return false;

            const t = String(i.tipo || i.type || "").toLowerCase();

            const isEquip = [
                'weapon', 'armor', 'helmet', 'boots', 'ring', 'necklace', 'earring',
                'equipamento', 'arma', 'armadura',
                'tool', 'ferramenta'
            ].includes(t);

            return isEquip && getNivelRefinoItem(i) < 10;
        });
    },

    verificarPermissaoDeMelhoria(item) {
        const custo = calcularCustoMelhoriaLocal(item);
        let podeMelhorar = true;
        let statusMateriais = [];

        for (const [mat_id, qtd_req] of Object.entries(custo)) {
            const qtdTenho = getQtdMaterialInventario(mat_id);
            if (qtdTenho < qtd_req) podeMelhorar = false;
            statusMateriais.push({ id: mat_id, tenho: qtdTenho, precisa: qtd_req });
        }

        return { podeMelhorar, statusMateriais };
    },

    verificarPermissaoDeCraft(receita) {
        const p = window.perfilDadosGlobais;
        const inv = p.inventario || p.inventory || [];
        const desbloqueada = this.receitaGuildaEstaDesbloqueada(receita);

        let statusMateriais = [];
        let podeCriar = desbloqueada;

        let ingredientes = receita.inputs || receita.ingredients || receita.materials || {};

        for (const [mat_id, qtd_req] of Object.entries(ingredientes)) {
            const itemInv = inv.find(i => i.base_id === mat_id);
            const qtdTenho = itemInv ? (itemInv.qtd || itemInv.quantity || 0) : 0;

            if (qtdTenho < qtd_req) {
                podeCriar = false;
            }

            statusMateriais.push({
                id: mat_id,
                tenho: qtdTenho,
                precisa: qtd_req
            });
        }

        return {
            podeCriar,
            statusMateriais,
            desbloqueada
        };
    },

    mudarAba(prof) {
        this.profSelecionada = prof.toLowerCase();
        this.receitaSelecionada = null;
        this.itemDesmontarSelecionado = null;
        this.itemMelhorarSelecionado = null;
        this.usarSigiloMelhoria = false;
        ForjaUI.renderizarTudo();
    }
};

window.abrirUIForja = async function() {
    const container = document.getElementById('forja-container');
    if (!container) return;
    container.style.display = 'flex';
    await ForjaEngine.iniciar();
    document.querySelectorAll('.btn-passe-mapa, .btn-social-mapa').forEach(btn => btn.style.display = 'none');
};

window.fecharUIForja = function() {
    document.getElementById('forja-container').style.display = 'none';
    document.querySelectorAll('.btn-passe-mapa, .btn-social-mapa').forEach(btn => btn.style.display = 'flex');
};

window.tentarIniciarForja = async function() {
    const charId = localStorage.getItem("jogadorEldoraID");
    const btn = document.getElementById('btn-iniciar-forja');
    
    // MODO MELHORAR EQUIPAMENTO
    if (ForjaEngine.profSelecionada === 'melhorar') {
        if (!ForjaEngine.itemMelhorarSelecionado) return;

        btn.disabled = true;
        btn.innerText = "MELHORANDO...";

        try {
            const res = await fetch('/api/equipment/upgrade/start', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    user_id: charId,
                    item_uid: ForjaEngine.itemMelhorarSelecionado.uid || ForjaEngine.itemMelhorarSelecionado.id,
                    use_protection: !!ForjaEngine.usarSigiloMelhoria
                })
            });

            const data = await res.json();

            if (data.success) {
                window.fecharUIForja();
                window.iniciarAnimacaoTrabalho(data.duration_seconds, 'melhorar', {
                    ...data,
                    selected_item: ForjaEngine.itemMelhorarSelecionado
               });
            } else {
                if (window.alertaEldora) window.alertaEldora("Aviso da Forja", data.error || "Não foi possível melhorar.", "erro");
                btn.disabled = false;
                btn.innerText = "MELHORAR ITEM";
            }
        } catch (e) {
            console.error(e);
            btn.disabled = false;
            btn.innerText = "MELHORAR ITEM";
        }

        return;
    }

    // MODO DESMONTE
    if (ForjaEngine.profSelecionada === 'desmontar') {
        if (!ForjaEngine.itemDesmontarSelecionado) return;
        btn.disabled = true;
        btn.innerText = "DESMONTANDO...";
        
        try {
            const res = await fetch('/api/dismantle/start', {
                method: 'POST', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ user_id: charId, unique_id: ForjaEngine.itemDesmontarSelecionado.id })
            });
            const data = await res.json();
            if (data.success) {
                window.fecharUIForja();
                window.iniciarAnimacaoTrabalho(data.duration_seconds, 'desmontar', {
                    ...data,
                    selected_item: ForjaEngine.itemDesmontarSelecionado
                });
            } else {
                if (window.alertaEldora) window.alertaEldora("Aviso", data.error, "erro");
                btn.disabled = false; btn.innerText = "DESMONTAR ITEM";
            }
        } catch(e) { btn.disabled = false; btn.innerText = "DESMONTAR ITEM"; }
        return;
    }
    
    // MODO FORJA NORMAL
    if (!ForjaEngine.receitaSelecionada) return;

    const receitaAtual =
        ForjaEngine.receitas[
            ForjaEngine.receitaSelecionada
        ];

    if (
        receitaAtual &&
        !ForjaEngine.receitaGuildaEstaDesbloqueada(
            receitaAtual
        )
    ) {
        if (window.alertaEldora) {
            window.alertaEldora(
                "Receita Bloqueada",
                "Desbloqueie esta receita na Loja da Guilda dos Aventureiros.",
                "erro"
            );
        }

        return;
    }

    btn.disabled = true;
    btn.innerText = "AQUECENDO FORJA...";
    try {
        const res = await fetch('/api/crafting/start', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: charId, recipe_id: ForjaEngine.receitaSelecionada })
        });
        const data = await res.json();
        
        if (data.success || data.duration_seconds) {
            const dadosTrabalho = data.data || data;

            window.fecharUIForja();
            window.iniciarAnimacaoTrabalho(
                dadosTrabalho.duration_seconds,
                'forja',
                dadosTrabalho
            );
        } else {
            if (window.alertaEldora) window.alertaEldora("Aviso da Forja", data.error, "erro");
            btn.disabled = false; btn.innerText = "INICIAR FORJA";
        }
    } catch (e) { btn.disabled = false; btn.innerText = "INICIAR FORJA"; }
};

const ForjaUI = {
    renderizarTudo() {
        this.desenharAbas();
        
        if (ForjaEngine.profSelecionada === 'desmontar') {
            this.desenharListaDesmontar();
        } else if (ForjaEngine.profSelecionada === 'melhorar') {
            this.desenharListaMelhorar();
        } else {
            this.desenharLista();
        }

        // 👇 FORÇA BRUTA: Esconde a direita e expande a esquerda quando nada está selecionado
        const sidebar = document.querySelector('.forja-sidebar');
        const detailsView = document.querySelector('.forja-details-view');
        
        if (sidebar && detailsView) {
            sidebar.classList.remove('forja-sidebar-compacta');

            detailsView.style.display = 'none'; 
            sidebar.style.cssText = 'width: 100% !important; max-width: 100% !important; height: 100% !important; border: none !important; flex: 1 !important;';
        }
        document.getElementById('detalhe-vazio').style.display = 'block';
        document.getElementById('detalhe-receita').style.display = 'none';
    },

    desenharAbas() {
        const container = document.getElementById('abas-profissoes-forja');
        if(!container) return;
        container.innerHTML = '';
        
        const profs = ForjaEngine.getProfissoesJogador();
        profs.forEach(prof => {
            const btn = document.createElement('button');
            btn.className = `aba-forja-btn ${ForjaEngine.profSelecionada === prof ? 'active' : ''}`;
            btn.innerText = prof.toUpperCase();
            if (prof === 'desmontar') {
                btn.style.backgroundColor = ForjaEngine.profSelecionada === prof ? '#ef4444' : '#450a0a';
                btn.style.borderColor = '#991b1b';
                btn.innerHTML = '♻️ DESMONTAR';
            }
            if (prof === 'melhorar') {
                btn.style.backgroundColor = ForjaEngine.profSelecionada === prof ? '#3b82f6' : '#0f172a';
                btn.style.borderColor = '#1d4ed8';
                btn.innerHTML = '⬆️ MELHORAR';
            }
            btn.onclick = () => ForjaEngine.mudarAba(prof);
            container.appendChild(btn);
        });
        const runasBtn = document.createElement('button');
        runasBtn.className = 'aba-forja-btn';
        runasBtn.textContent = '◇ RUNAS';
        runasBtn.onclick = () => window.abrirOficinaRunas();
        container.appendChild(runasBtn);
        this.ativarScrollAbas(container);
    },
    
    ativarScrollAbas(container) {
        if (!container || container.dataset.dragReady === "true") return;
        container.dataset.dragReady = "true";

        let isDown = false;
        let startX = 0;
        let scrollLeft = 0;
        let moved = false;

        container.addEventListener('wheel', (e) => {
            if (Math.abs(e.deltaY) > Math.abs(e.deltaX)) {
                container.scrollLeft += e.deltaY;
                e.preventDefault();
            }
        }, { passive: false });

        container.addEventListener('mousedown', (e) => {
            isDown = true;
            moved = false;
            startX = e.pageX - container.offsetLeft;
            scrollLeft = container.scrollLeft;
            container.classList.add('dragging-tabs');
        });

        container.addEventListener('mouseleave', () => {
            isDown = false;
            container.classList.remove('dragging-tabs');
        });

        container.addEventListener('mouseup', () => {
            isDown = false;
            container.classList.remove('dragging-tabs');
            setTimeout(() => moved = false, 0);
        });

        container.addEventListener('mousemove', (e) => {
            if (!isDown) return;
            e.preventDefault();

            const x = e.pageX - container.offsetLeft;
            const walk = (x - startX) * 1.4;

            if (Math.abs(walk) > 5) moved = true;
            container.scrollLeft = scrollLeft - walk;
        });

        container.addEventListener('click', (e) => {
            if (moved) {
                e.preventDefault();
                e.stopPropagation();
            }
        }, true);
    },

    desenharLista() {
        const lista = document.getElementById('lista-receitas');
        lista.innerHTML = '';
        const receitas = ForjaEngine.getReceitasDaAbaAtual();

        if (Object.keys(receitas).length === 0) {
            lista.innerHTML = `<div style="padding:20px; text-align:center; color:#94a3b8;">Nenhum projeto encontrado.</div>`;
            return;
        }

        Object.keys(receitas).forEach(id => {
            const r = receitas[id];
            const info = descobrirPastaForja(r, id);
            const imgPath1 = `${GITHUB_BASE_ITENS}${info.pasta}/${info.outputId}.png`; 
            const imgPath2 = `${GITHUB_BASE_ITENS}${info.pasta}/${info.idReceita}.png`; 

            const bloqueadaGuilda =
                Boolean(r.unlock_id) &&
                !ForjaEngine.receitaGuildaEstaDesbloqueada(r);

            const card = document.createElement('div');

            card.className =
                `recipe-card ${ForjaEngine.receitaSelecionada === id ? 'active' : ''}`;

            card.style.position = 'relative';

            if (bloqueadaGuilda) {
                card.style.opacity = '0.68';
                card.style.borderColor = '#92400e';
            }

            card.innerHTML = `
                <img
                    src="${imgPath1}"
                    class="card-icon"
                    onerror="
                        if(this.getAttribute('data-tried') !== 'true') {
                            this.setAttribute('data-tried', 'true');
                            this.src='${imgPath2}';
                        } else {
                            this.src='/static/assets/box.png';
                        }
                    "
                >

                <span class="recipe-name">
                    ${r.display_name}
                </span>

                ${
                    bloqueadaGuilda
                        ? `
                            <span
                                style="
                                    position: absolute;
                                    top: 4px;
                                    right: 4px;
                                    padding: 2px 5px;
                                    border: 1px solid #92400e;
                                    border-radius: 6px;
                                    background: rgba(69, 26, 3, 0.95);
                                    color: #fed7aa;
                                    font-size: 9px;
                                    font-weight: 900;
                                "
                            >
                                🔒
                            </span>
                        `
                        : ""
                }
            `;

            card.onclick = () => {

                document.querySelectorAll('#lista-receitas .recipe-card').forEach(el => el.classList.remove('active'));
                card.classList.add('active');
                ForjaEngine.receitaSelecionada = id;
                this.atualizarDetalhesDaReceita(id, r);
            };
            lista.appendChild(card);
        });
    },
    desenharListaMelhorar() {
        const lista = document.getElementById('lista-receitas');
        lista.innerHTML = '';

        const itens = ForjaEngine.getItensParaMelhorar();

        if (itens.length === 0) {
            lista.innerHTML = `<div style="padding:20px; text-align:center; color:#94a3b8;">Nenhum equipamento equipado para melhorar.</div>`;
            return;
        }

        itens.forEach(item => {
            const nivel = getNivelRefinoItem(item);

            const corRaridade = {
                'comum': '#94a3b8',
                'incomum': '#22c55e',
                'bom': '#22c55e',
                'raro': '#3b82f6',
                'epico': '#a855f7',
                'lendario': '#eab308'
            }[(item.raridade || 'comum').toLowerCase()] || '#cbd5e1';

            const card = document.createElement('div');
            card.className = `recipe-card ${ForjaEngine.itemMelhorarSelecionado?.id === item.id ? 'active' : ''}`;

            card.innerHTML = `
                <div style="position:relative;">
                    <img src="/static/assets/box.png" class="card-icon" style="border-bottom: 2px solid ${corRaridade};">
                    ${nivel > 0 ? `<span style="position:absolute; top:-5px; left:-5px; background:#3b82f6; color:#fff; font-size:10px; font-weight:bold; border-radius:4px; padding:1px 3px;">+${nivel}</span>` : ''}
                </div>
                <span class="recipe-name" style="color:${corRaridade}">${item.nome}</span>
            `;
            aplicarImagemItemForja(card.querySelector("img.card-icon"), item);

            card.onclick = () => {
                document.querySelectorAll('#lista-receitas .recipe-card').forEach(el => el.classList.remove('active'));
                card.classList.add('active');
                ForjaEngine.itemMelhorarSelecionado = item;
                this.atualizarDetalhesMelhorar(item, corRaridade);
            };

            lista.appendChild(card);
        });
    },

    atualizarDetalhesMelhorar(item, corRaridade) {
        const sidebar = document.querySelector('.forja-sidebar');
        const detailsView = document.querySelector('.forja-details-view');

        if (sidebar && detailsView) {
            detailsView.style.display = 'flex';
            sidebar.style.cssText = '';

            if (window.innerWidth <= 768) {
                sidebar.classList.add('forja-sidebar-compacta');
            }
        }

        const nivelAtual = getNivelRefinoItem(item);
        const proximoNivel = nivelAtual + 1;

        document.getElementById('detalhe-vazio').style.display = 'none';
        document.getElementById('detalhe-receita').style.display = 'flex';

        const nomeEl = document.getElementById('nome-item-resultado');
        nomeEl.innerText = `${item.nome} +${nivelAtual} → +${proximoNivel}`;
        nomeEl.style.color = corRaridade;

        document.getElementById('label-materiais').innerText = "Materiais para Melhorar";
        const chanceSucesso = getChanceSucessoMelhoria(proximoNivel);
        const temRisco = chanceSucesso < 100;

        document.getElementById('prof-texto-xp-forja').innerHTML = `
            Chance de sucesso: <b style="color:${temRisco ? '#facc15' : '#22c55e'}">${chanceSucesso}%</b>
            ${temRisco ? " | Sem Sigilo, falha pode reduzir nível." : " | Sucesso garantido."}
        `;
        document.getElementById('prof-barra-xp-forja').style.width = `0%`;

        const profTempoMelhoria = getProfissaoItemForja(item, "ferreiro");
        const baseTempoMelhoria = 60 + (nivelAtual * 30);
        const tempoMelhoria = calcularTempoTrabalhoForjaLocal(baseTempoMelhoria, profTempoMelhoria);

        document.getElementById('tempo-forja').innerText = tempoMelhoria.duration_seconds;

        document.getElementById('nvl-req').innerText = "-";

        const imgElement = document.getElementById('img-item-resultado');
        aplicarImagemItemForja(imgElement, item);

        const verificacao = ForjaEngine.verificarPermissaoDeMelhoria(item);
        const grid = document.getElementById('lista-materiais');
        grid.innerHTML = '';

        const qtdSigilo = getQtdMaterialInventario(UPGRADE_PROTECTION_ITEM_ID);
        const sigiloAtivo = !!ForjaEngine.usarSigiloMelhoria;
        const podeUsarSigilo = temRisco && qtdSigilo > 0;

        if (!temRisco && ForjaEngine.usarSigiloMelhoria) {
            ForjaEngine.usarSigiloMelhoria = false;
        }

        const corAtualMelhoria = JSON.stringify(corRaridade || "#cbd5e1");

        const boxSigilo = document.createElement('div');
        boxSigilo.className = `mat-pill ${sigiloAtivo && qtdSigilo < 1 ? 'missing' : ''}`;
        boxSigilo.style.borderColor = sigiloAtivo ? "#60a5fa" : "#334155";
        boxSigilo.style.background = sigiloAtivo ? "rgba(37, 99, 235, 0.18)" : "";

        boxSigilo.innerHTML = `
            <div class="mat-info">
                <input
                    type="checkbox"
                    id="check-sigilo-melhoria"
                    ${sigiloAtivo ? "checked" : ""}
                    ${!podeUsarSigilo ? "disabled" : ""}
                    onchange='
                        ForjaEngine.usarSigiloMelhoria = this.checked;
                            ForjaUI.atualizarDetalhesMelhorar(ForjaEngine.itemMelhorarSelecionado, ${corAtualMelhoria});
                        '
                        style="width:18px; height:18px; accent-color:#3b82f6; cursor:pointer;"
                    >

                    <img data-mat-img="sigilo-opcional" src="/static/assets/box.png" style="width:24px; height:24px; object-fit:contain;">

                    <span>
                        Sigilo de Proteção
                        <small style="display:block; color:#94a3b8; font-size:0.72em;">
                            ${temRisco ? "Protege contra perda de nível se falhar" : "Não necessário neste nível"}
                        </small>
                    </span>
                </div>

                <b>${qtdSigilo}/1</b>
            `;

            grid.appendChild(boxSigilo);
            aplicarImagemMaterialForja(
                boxSigilo.querySelector(`[data-mat-img="sigilo-opcional"]`),
                UPGRADE_PROTECTION_ITEM_ID
            );

            verificacao.statusMateriais.forEach(mat => {
                if (mat.id === UPGRADE_PROTECTION_ITEM_ID) return;
            const pill = document.createElement('div');
            pill.className = `mat-pill ${mat.tenho < mat.precisa ? 'missing' : ''}`;
            pill.innerHTML = `
                <div class="mat-info">
                    <img data-mat-img="${mat.id}" src="/static/assets/box.png" style="width:24px; height:24px; object-fit:contain;">
                    <span>${getNomeMaterialForja(mat.id)}</span>
                </div>
                <b>${mat.tenho}/${mat.precisa}</b>
            `;

            grid.appendChild(pill);
            aplicarImagemMaterialForja(pill.querySelector(`[data-mat-img="${mat.id}"]`), mat.id);
        });

        const btn = document.getElementById('btn-iniciar-forja');
        btn.disabled = !verificacao.podeMelhorar;
        btn.innerText = "MELHORAR ITEM";
        btn.style.background = "linear-gradient(180deg, #3b82f6, #1d4ed8)";
    },
    desenharListaDesmontar() {
        const lista = document.getElementById('lista-receitas');
        lista.innerHTML = '';
        const itens = ForjaEngine.getItensParaDesmontar();

        if (itens.length === 0) {
            lista.innerHTML = `<div style="padding:20px; text-align:center; color:#94a3b8;">Nenhum equipamento velho na mochila para reciclar.</div>`;
            return;
        }

        itens.forEach(item => {
            const corRaridade = {
                comum: '#94a3b8',
                incomum: '#22c55e',
                bom: '#22c55e',
                raro: '#3b82f6',
                epico: '#a855f7',
                lendario: '#eab308'
            }[(item.raridade || item.rarity || 'comum').toLowerCase()] || '#cbd5e1';

            const nivel = getNivelRefinoItem(item);

            const card = document.createElement('div');
            card.className = `recipe-card ${ForjaEngine.itemDesmontarSelecionado?.id === item.id ? 'active' : ''}`;

            card.innerHTML = `
                <div style="position:relative;">
                    <img src="/static/assets/box.png" class="card-icon" style="border-bottom: 2px solid ${corRaridade};">
                    ${nivel > 0 ? `<span style="position:absolute; top:-5px; left:-5px; background:#eab308; color:#000; font-size:10px; font-weight:bold; border-radius:4px; padding:1px 3px;">+${nivel}</span>` : ''}
                </div>
                <span class="recipe-name" style="color: ${corRaridade}">${item.nome}</span>
            `;

            aplicarImagemItemForja(card.querySelector("img.card-icon"), item);

            card.onclick = () => {
                document.querySelectorAll('#lista-receitas .recipe-card').forEach(el => el.classList.remove('active'));
                card.classList.add('active');
                ForjaEngine.itemDesmontarSelecionado = item;
                this.atualizarDetalhesDesmontar(item, corRaridade);
            };

            lista.appendChild(card);
        });
    },

    atualizarDetalhesDaReceita(id, receita) {
        // 👇 FORÇA BRUTA: Limpa a injeção e devolve o layout dividido
        const sidebar = document.querySelector('.forja-sidebar');
        const detailsView = document.querySelector('.forja-details-view');
        if (sidebar && detailsView) {
            detailsView.style.display = 'flex'; 
            sidebar.style.cssText = '';

            if (window.innerWidth <= 768) {
                sidebar.classList.add('forja-sidebar-compacta');
            }
        }
        
        document.getElementById('detalhe-vazio').style.display = 'none';
        document.getElementById('detalhe-receita').style.display = 'flex';
        document.getElementById('label-materiais').innerText = "Materiais Necessários";

        const profKey = (ForjaEngine.profSelecionada || 'ferreiro').toLowerCase();
        const learned = window.perfilDadosGlobais.learned_professions || {};
        let profData = learned[profKey] || {};
        if (!profData.level && window.perfilDadosGlobais.profession?.key === profKey) profData = window.perfilDadosGlobais.profession;
        
        const myLvl = parseInt(profData.level || 1);
        const profXp = parseInt(profData.xp || 0);
        let xpNecessario = 40 + (25 * (myLvl - 1)) + (8 * Math.pow(myLvl - 1, 2));
        
        document.getElementById('nome-item-resultado').innerText = receita.display_name || "Item";
        document.getElementById('prof-texto-xp-forja').innerHTML = `<span style="color:#facc15; font-weight:bold;">${profKey.toUpperCase()} Nv. ${myLvl}</span> &nbsp;|&nbsp; XP: ${myLvl >= 50 ? "MÁX" : `${profXp} / ${xpNecessario}`}`;
        
        let percXp = (profXp / xpNecessario) * 100;
        document.getElementById('prof-barra-xp-forja').style.width = `${Math.min(percXp, 100)}%`;
        
        // Cálculo de Tempo Local com profissão + ferramenta
        const baseTime = receita.time_seconds || receita.craft_time || 60;
        const tempoCraft = calcularTempoTrabalhoForjaLocal(baseTime, profKey);

        document.getElementById('tempo-forja').innerText = tempoCraft.duration_seconds;
        document.getElementById('nvl-req').innerText = receita.level_req || 1;

        const info = descobrirPastaForja(receita, id);
        const imgElement = document.getElementById('img-item-resultado');
        imgElement.src = `${GITHUB_BASE_ITENS}${info.pasta}/${info.outputId}.png`; 
        imgElement.setAttribute('data-tried', 'false');
        imgElement.onerror = function() {
            if (this.getAttribute('data-tried') !== 'true') {
                this.setAttribute('data-tried', 'true');
                this.src = `${GITHUB_BASE_ITENS}${info.pasta}/${info.idReceita}.png`;
            } else { this.onerror = null; this.src = '/static/assets/box.png'; }
        };
        
        const verificacao = ForjaEngine.verificarPermissaoDeCraft(receita);
        const grid = document.getElementById('lista-materiais');

        grid.innerHTML = '';

        if (!verificacao.desbloqueada) {
            const aviso = document.createElement('div');

            aviso.style.cssText = `
                grid-column: 1 / -1;
                width: 100%;
                box-sizing: border-box;
                padding: 10px;
                margin-bottom: 6px;
                border: 1px solid #92400e;
                border-radius: 9px;
                background: rgba(69, 26, 3, 0.35);
                color: #fed7aa;
                font-size: 11px;
                line-height: 1.4;
                text-align: center;
            `;

            aviso.innerHTML = `
                <strong>🔒 Receita exclusiva da Guilda</strong>
                <br>
                Desbloqueie esta receita na
                <strong>Loja da Guilda dos Aventureiros</strong>.
            `;

            grid.appendChild(aviso);
        }

        verificacao.statusMateriais.forEach(mat => {

            const pill = document.createElement('div');
            pill.className = `mat-pill ${mat.tenho < mat.precisa ? 'missing' : ''}`;
            pill.innerHTML = `
                <div class="mat-info">
                    <img data-mat-img="${mat.id}" src="/static/assets/box.png" style="width:24px; height:24px; object-fit:contain;">
                    <span>${getNomeMaterialForja(mat.id)}</span>
                </div>
                <b>${mat.tenho}/${mat.precisa}</b>
            `;

            grid.appendChild(pill);
            aplicarImagemMaterialForja(pill.querySelector(`[data-mat-img="${mat.id}"]`), mat.id);
        });

        const btn = document.getElementById('btn-iniciar-forja');

        if (!verificacao.desbloqueada) {
            btn.disabled = true;
            btn.innerText = "🔒 DESBLOQUEIE NA GUILDA";
            btn.style.background = "linear-gradient(180deg, #475569, #1e293b)";
            return;
        }

        btn.disabled = !verificacao.podeCriar;
        btn.innerText = "INICIAR FORJA";
        btn.style.background = "linear-gradient(180deg, #ca8a04, #a16207)";
    },
    
    atualizarDetalhesDesmontar(item, corRaridade) {
        const sidebar = document.querySelector('.forja-sidebar');
        const detailsView = document.querySelector('.forja-details-view');
        if (sidebar && detailsView) {
            detailsView.style.display = 'flex';
            sidebar.style.cssText = '';

            if (window.innerWidth <= 768) {
                sidebar.classList.add('forja-sidebar-compacta');
            }
        }
        
        document.getElementById('detalhe-vazio').style.display = 'none';
        document.getElementById('detalhe-receita').style.display = 'flex';
        
        document.getElementById('nome-item-resultado').innerText = item.nome;
        document.getElementById('nome-item-resultado').style.color = corRaridade;
        document.getElementById('label-materiais').innerText = "Materiais a Recuperar (Aproximado)";
        
        document.getElementById('prof-texto-xp-forja').innerHTML = "Ao desmontar, você recupera materiais brutos.";
        document.getElementById('prof-barra-xp-forja').style.width = `0%`;
        
        const profTempoDesmonte = getProfissaoItemForja(item, "ferreiro");
        const tempoDesmonte = calcularTempoTrabalhoForjaLocal(180, profTempoDesmonte);

        document.getElementById('tempo-forja').innerText = tempoDesmonte.duration_seconds;
        
        document.getElementById('nvl-req').innerText = "-";

        const imgElement = document.getElementById('img-item-resultado');
        aplicarImagemItemForja(imgElement, item);

        const grid = document.getElementById('lista-materiais');
        grid.innerHTML = '';

        const retornoPreview = calcularPreviewDesmonteLocal(item);

        for (const [matId, qtd] of Object.entries(retornoPreview)) {
            const pill = document.createElement('div');
            pill.className = `mat-pill`;

            pill.innerHTML = `
                <div class="mat-info">
                    <img data-mat-img="${matId}" src="/static/assets/box.png" style="width:24px; height:24px; object-fit:contain;">
                    <span>${getNomeMaterialForja(matId)}</span>
                </div>
                <b>${qtd}</b>
            `;

            grid.appendChild(pill);
            aplicarImagemMaterialForja(pill.querySelector(`[data-mat-img="${matId}"]`), matId);
        }

        if (Object.keys(retornoPreview).length === 0) {
            grid.innerHTML = `
                <div class="mat-pill missing">
                    <div class="mat-info">
                        <span>📦</span>
                        <span>Nenhum material previsto</span>
                    </div>
                    <b>0</b>
                </div>
            `;
        }

        const btn = document.getElementById('btn-iniciar-forja');
        btn.disabled = false;
        btn.innerText = "DESMONTAR ITEM";
        btn.style.background = "linear-gradient(180deg, #ef4444, #991b1b)";
    }
};

// =====================================================================
// ⏳ ANIMAÇÃO DE FORJA E DESMONTE
// =====================================================================
function nomeBonitoForja(id, itemObj = null) {
    if (itemObj && typeof itemObj === "object") {
        return (
            itemObj.display_name ||
            itemObj.nome ||
            itemObj.name ||
            itemObj.base_id ||
            id ||
            "Item"
        );
    }

    return String(id || "item")
        .replace(/_/g, " ")
        .replace(/\b\w/g, l => l.toUpperCase());
}

function formatarRecompensasForja(rewards) {
    if (!rewards) return "Nada recebido.";

    const linhas = [];

    if (Array.isArray(rewards)) {
        rewards.forEach(r => {
            if (!r) return;

            if (typeof r === "string") {
                linhas.push(`• ${nomeBonitoForja(r)}`);
                return;
            }

            const id = r.id || r.base_id || r.item_id || r.nome || r.name;
            const qtd = r.qtd || r.qty || r.quantity || r.quantidade || 1;
            linhas.push(`• ${qtd}x ${nomeBonitoForja(id, r)}`);
        });

        return linhas.length ? linhas.join("\n") : "Nada recebido.";
    }

    if (typeof rewards === "object") {
        for (const [id, valor] of Object.entries(rewards)) {
            if (valor === undefined || valor === null) continue;

            if (typeof valor === "object") {
                const realId = valor.id || valor.base_id || id;
                const qtd = valor.qtd || valor.qty || valor.quantity || valor.quantidade || 1;
                linhas.push(`• ${qtd}x ${nomeBonitoForja(realId, valor)}`);
            } else {
                const qtd = parseInt(valor || 0);
                if (qtd > 0) linhas.push(`• ${qtd}x ${nomeBonitoForja(id)}`);
            }
        }

        return linhas.length ? linhas.join("\n") : "Nada recebido.";
    }

    return String(rewards);
}

function normalizarRaridadeForjaPopup(raridade) {
    return String(raridade || "comum")
        .toLowerCase()
        .normalize("NFD")
        .replace(/[\u0300-\u036f]/g, "");
}

function getCorRaridadeForjaPopup(raridade, fallback = "#22c55e") {
    const r = normalizarRaridadeForjaPopup(raridade);

    const cores = {
        comum: "#94a3b8",
        bom: "#22c55e",
        incomum: "#22c55e",
        raro: "#3b82f6",
        epico: "#a855f7",
        lendario: "#eab308",
        unico: "#ef4444",
        mitico: "#00f2fe"
    };

    return cores[r] || fallback;
}

function getIconeRaridadeForjaPopup(raridade, fallback = "✨") {
    const r = normalizarRaridadeForjaPopup(raridade);

    const icones = {
        comum: "⚪",
        bom: "🟢",
        incomum: "🟢",
        raro: "🔵",
        epico: "🟣",
        lendario: "🟡",
        unico: "🔴",
        mitico: "💠"
    };

    return icones[r] || fallback;
}

function getTituloRaridadeForjaPopup(raridade) {
    const r = normalizarRaridadeForjaPopup(raridade);

    const nomes = {
        comum: "COMUM",
        bom: "BOM",
        incomum: "INCOMUM",
        raro: "RARO",
        epico: "ÉPICO",
        lendario: "LENDÁRIO",
        unico: "ÚNICO",
        mitico: "MÍTICO"
    };

    return nomes[r] || String(raridade || "COMUM").toUpperCase();
}

function gerarHtmlAtributosForjaPopup(item) {
    if (!item || typeof item !== "object") {
        return "";
    }

    /*
     * Junta todos os locais possíveis de atributos.
     *
     * Não usamos "um OU outro", porque equipamentos podem possuir:
     * - attributes
     * - enchantments
     * - stats
     * - damage separado
     *
     * Se a mesma chave existir em mais de um bloco,
     * ela aparece apenas uma vez.
     *
     * Atributos realmente repetidos com chaves diferentes
     * (ex.: sorte_oficio_2) continuam preservados.
     */
    const atributos = {};

    const blocos = [
        item.attributes,
        item.enchantments,
        item.stats
    ];

    blocos.forEach(bloco => {
        if (!bloco || typeof bloco !== "object" || Array.isArray(bloco)) {
            return;
        }

        Object.entries(bloco).forEach(([chave, valor]) => {
            if (!chave) return;

            atributos[chave] = valor;
        });
    });


    /*
     * DANO DA ARMA
     *
     * Alguns equipamentos salvam dano fora de stats:
     *
     * damage: {
     *     min: 10,
     *     max: 15
     * }
     *
     * Também protegemos outros formatos antigos.
     */
    if (
        item.damage !== undefined &&
        item.damage !== null &&
        atributos.dmg === undefined &&
        atributos.damage === undefined
    ) {
        const damage = item.damage;

        if (
            damage &&
            typeof damage === "object" &&
            !Array.isArray(damage)
        ) {
            const minimo =
                damage.min ??
                damage.min_damage ??
                damage.minimum ??
                null;

            const maximo =
                damage.max ??
                damage.max_damage ??
                damage.maximum ??
                null;

            if (minimo !== null && maximo !== null) {
                atributos.dmg = {
                    stat: "dmg",
                    value: `${minimo}-${maximo}`,
                    source: "damage"
                };
            }
            else if (damage.value !== undefined) {
                atributos.dmg = {
                    stat: "dmg",
                    value: damage.value,
                    source: "damage"
                };
            }
        }
        else if (
            Array.isArray(damage) &&
            damage.length >= 2
        ) {
            atributos.dmg = {
                stat: "dmg",
                value: `${damage[0]}-${damage[1]}`,
                source: "damage"
            };
        }
        else if (
            typeof damage === "number" ||
            typeof damage === "string"
        ) {
            atributos.dmg = {
                stat: "dmg",
                value: damage,
                source: "damage"
            };
        }
    }


    if (Object.keys(atributos).length === 0) {
        return "";
    }


    const nomes = {

        // =========================
        // FERRAMENTAS / PROFISSÕES
        // =========================
        velocidade_trabalho: "Velocidade de Trabalho",
        sorte_oficio: "Sorte de Ofício",
        maestria: "Maestria",
        resistencia_ferramenta: "Resistência da Ferramenta",

        // =========================
        // COMBATE
        // =========================
        attack: "Ataque",
        ataque: "Ataque",

        defense: "Defesa",
        defesa: "Defesa",

        dmg: "Dano",
        damage: "Dano",

        hp: "Vida",
        vida: "Vida",
        health: "Vida",

        mp: "Mana",
        mana: "Mana",

        initiative: "Iniciativa",
        iniciativa: "Iniciativa",

        luck: "Sorte",
        sorte: "Sorte",

        crit_chance: "Chance Crítica",
        critical_chance: "Chance Crítica",
        crit_chance_flat: "Chance Crítica",

        crit_damage: "Dano Crítico",
        critical_damage: "Dano Crítico",

        dodge: "Esquiva",
        esquiva: "Esquiva",

        accuracy: "Precisão",
        precisao: "Precisão",

        strength: "Força",
        forca: "Força",

        agility: "Agilidade",
        agilidade: "Agilidade",

        intelligence: "Inteligência",
        inteligencia: "Inteligência",

        vitality: "Vitalidade",
        vitalidade: "Vitalidade",

        resistance: "Resistência",
        resistencia: "Resistência"
    };


    const emojis = {

        // Ferramentas
        velocidade_trabalho: "⚡",
        sorte_oficio: "🍀",
        maestria: "🔨",
        resistencia_ferramenta: "🛡️",

        // Combate
        attack: "⚔️",
        ataque: "⚔️",

        defense: "🛡️",
        defesa: "🛡️",

        dmg: "🗡️",
        damage: "🗡️",

        hp: "❤️",
        vida: "❤️",
        health: "❤️",

        mp: "💧",
        mana: "💧",

        initiative: "🏃",
        iniciativa: "🏃",

        luck: "🍀",
        sorte: "🍀",

        crit_chance: "💥",
        critical_chance: "💥",
        crit_chance_flat: "💥",

        crit_damage: "🔥",
        critical_damage: "🔥",

        dodge: "💨",
        esquiva: "💨",

        accuracy: "🎯",
        precisao: "🎯",

        strength: "💪",
        forca: "💪",

        agility: "🪽",
        agilidade: "🪽",

        intelligence: "🧠",
        inteligencia: "🧠",

        vitality: "❤️",
        vitalidade: "❤️",

        resistance: "🛡️",
        resistencia: "🛡️"
    };


    const linhas = [];

    for (const [chaveOriginal, entrada] of Object.entries(atributos)) {

        /*
         * Exemplo:
         *
         * velocidade_trabalho_2
         *
         * pode carregar:
         * {
         *     stat: "velocidade_trabalho",
         *     value: 10
         * }
         */
        let statReal = chaveOriginal;

        if (
            entrada &&
            typeof entrada === "object" &&
            !Array.isArray(entrada) &&
            entrada.stat
        ) {
            statReal = entrada.stat;
        }
        else {
            statReal = String(chaveOriginal).replace(
                /_\d+$/,
                ""
            );
        }

        statReal = String(statReal || "")
            .trim()
            .toLowerCase();


        let valor = entrada;

        if (
            entrada &&
            typeof entrada === "object" &&
            !Array.isArray(entrada)
        ) {
            valor =
                entrada.value ??
                entrada.valor ??
                entrada.amount ??
                0;
        }


        if (
            valor === undefined ||
            valor === null ||
            valor === ""
        ) {
            continue;
        }


        const nome =
            nomes[statReal] ||
            statReal
                .replace(/_/g, " ")
                .replace(
                    /\b\w/g,
                    letra => letra.toUpperCase()
                );


        const emoji =
            emojis[statReal] ||
            "✨";


        /*
         * Intervalos como "15-22" não recebem "+".
         *
         * Valores numéricos:
         * 10  -> +10
         * -2  -> -2
         */
        const numero = Number(valor);

        let valorTxt;

        if (
            typeof valor === "string" &&
            valor.includes("-") &&
            !Number.isFinite(numero)
        ) {
            valorTxt = valor;
        }
        else if (Number.isFinite(numero)) {
            valorTxt =
                `${numero >= 0 ? "+" : ""}${numero}`;
        }
        else {
            valorTxt = String(valor);
        }


        linhas.push(`
            <div style="
                display:flex;
                align-items:center;
                justify-content:space-between;
                gap:10px;
                padding:6px 8px;
                background:rgba(2,6,23,.45);
                border:1px solid rgba(71,85,105,.45);
                border-radius:8px;
            ">
                <span style="
                    min-width:0;
                    color:#cbd5e1;
                    font-size:.82em;
                    text-align:left;
                ">
                    ${emoji} ${nome}
                </span>

                <b style="
                    color:#86efac;
                    font-size:.84em;
                    flex-shrink:0;
                ">
                    ${valorTxt}
                </b>
            </div>
        `);
    }


    if (linhas.length === 0) {
        return "";
    }


    return `
        <div style="
            margin-top:10px;
            padding-top:10px;
            border-top:1px solid rgba(255,255,255,.08);
        ">
            <div style="
                margin-bottom:7px;
                color:#facc15;
                font-size:.72em;
                font-weight:900;
                text-transform:uppercase;
                letter-spacing:.5px;
            ">
                ✨ Atributos
            </div>

            <div style="
                display:grid;
                gap:6px;
            ">
                ${linhas.join("")}
            </div>
        </div>
    `;
}

function normalizarListaRecompensasForja(rewards) {
    const lista = [];
    if (!rewards) return lista;

    if (Array.isArray(rewards)) {
        rewards.forEach(r => {
            if (!r) return;

            if (typeof r === "string") {
                lista.push({
                    id: r,
                    nome: getNomeMaterialForja ? getNomeMaterialForja(r) : String(r).replace(/_/g, " "),
                    qtd: 1
                });
                return;
            }

            const id = r.id || r.base_id || r.item_id || r.nome || r.name;
            const qtd = parseInt(r.qtd || r.qty || r.quantity || r.quantidade || 1) || 1;

            lista.push({
                id,
                nome: r.display_name || r.nome || r.name || (getNomeMaterialForja ? getNomeMaterialForja(id) : String(id).replace(/_/g, " ")),
                qtd
            });
        });

        return lista;
    }

    if (typeof rewards === "object") {
        for (const [id, valor] of Object.entries(rewards)) {
            if (valor == null) continue;

            if (typeof valor === "object") {
                const realId = valor.id || valor.base_id || id;
                const qtd = parseInt(valor.qtd || valor.qty || valor.quantity || valor.quantidade || 1) || 1;

                lista.push({
                    id: realId,
                    nome: valor.display_name || valor.nome || valor.name || (getNomeMaterialForja ? getNomeMaterialForja(realId) : String(realId).replace(/_/g, " ")),
                    qtd
                });
            } else {
                const qtd = parseInt(valor || 0) || 0;
                if (qtd > 0) {
                    lista.push({
                        id,
                        nome: getNomeMaterialForja ? getNomeMaterialForja(id) : String(id).replace(/_/g, " "),
                        qtd
                    });
                }
            }
        }
    }

    return lista;
}

function removerPopupResultadoForja() {
    const antigo = document.getElementById("popup-resultado-forja-overlay");
    if (antigo) antigo.remove();
}

window.mostrarPopupResultadoForja = function({
    titulo = "Resultado",
    subtitulo = "",
    itemPrincipal = null,
    materiais = [],
    cor = "#22c55e",
    icone = "✨",
    infoExtra = ""
}) {
    removerPopupResultadoForja();

    const overlay = document.createElement("div");
    overlay.id = "popup-resultado-forja-overlay";
    overlay.style.cssText = `
        position: fixed;
        inset: 0;
        background: rgba(0,0,0,0.72);
        backdrop-filter: blur(3px);
        z-index: 999999;
        display: flex;
        align-items: center;
        justify-content: center;
        padding: 16px;
    `;

    const semMateriais =
        !materiais ||
        materiais.length === 0;

    const atributosHtml =
        gerarHtmlAtributosForjaPopup(
            itemPrincipal
        );

    overlay.innerHTML = `
        <div style="
            width: min(92vw, 420px);
            background: linear-gradient(180deg, #0b1220 0%, #111827 100%);
            border: 2px solid ${cor};
            border-radius: 18px;
            box-shadow: 0 0 28px rgba(0,0,0,.65), 0 0 20px ${cor}44;
            overflow: hidden;
            position: relative;
            color: #e5e7eb;
            animation: surgirResultadoForja .18s ease-out;
        ">
            <button id="fechar-popup-resultado-forja" style="
                position:absolute;
                top:10px;
                right:10px;
                width:32px;
                height:32px;
                border:none;
                border-radius:50%;
                background: rgba(255,255,255,0.08);
                color:#fff;
                font-size:20px;
                cursor:pointer;
            ">×</button>

            <div style="padding: 22px 18px 12px; text-align:center;">
                <div style="font-size: 42px; line-height: 1; margin-bottom: 10px;">${icone}</div>
                <div style="
                    font-family: 'Cinzel', serif;
                    font-weight: 900;
                    font-size: 1.15em;
                    color: ${cor};
                    text-transform: uppercase;
                    letter-spacing: .5px;
                ">${titulo}</div>
                ${subtitulo ? `<div style="margin-top:10px; color:#d1d5db; font-size:.98em;">${subtitulo}</div>` : ""}
            </div>

            <div style="padding: 0 18px 16px;">
                <div style="
                    background: rgba(255,255,255,0.04);
                    border: 1px solid rgba(255,255,255,0.08);
                    border-radius: 14px;
                    padding: 14px;
                ">
                    <div style="
                        display:flex;
                        align-items:center;
                        gap:12px;
                        margin-bottom:${infoExtra ? "10px" : "0"};
                    ">
                        <div style="
                            width:72px;
                            height:72px;
                            border-radius:14px;
                            border:2px solid ${cor};
                            background: rgba(255,255,255,.04);
                            display:flex;
                            align-items:center;
                            justify-content:center;
                            overflow:hidden;
                            flex-shrink:0;
                        ">
                            ${
                                itemPrincipal
                                ? `<img data-popup-item-principal src="/static/assets/box.png" style="width:80%; height:80%; object-fit:contain;">`
                                : `<span style="font-size:38px;">${icone}</span>`
                            }
                        </div>

                        <div style="min-width:0; flex:1;">
                            <div style="
                                font-size:1.02em;
                                font-weight:800;
                                color:#f8fafc;
                                line-height:1.25;
                                word-break:break-word;
                            ">
                                ${itemPrincipal?.nome || itemPrincipal?.display_name || itemPrincipal?.name || itemPrincipal?.item_name || "Resultado"}
                            </div>
                            ${
                                itemPrincipal?.raridade ||
                                itemPrincipal?.rarity

                                ? `
                                    <div style="
                                        margin-top:4px;
                                        font-size:.85em;
                                        color:#cbd5e1;
                                    ">
                                        Raridade:
                                        <b>
                                            ${String(
                                                itemPrincipal.raridade ||
                                                itemPrincipal.rarity
                                            ).toUpperCase()}
                                        </b>
                                    </div>
                                `
                                : ``
                            }
                        </div>
                    </div>

                    ${atributosHtml}

                    ${infoExtra ? `
                        <div style="
                            white-space: pre-line;
                            color:#d1d5db;
                            font-size:.93em;
                            line-height:1.45;
                            margin-top:8px;
                        ">${infoExtra}</div>
                    ` : ""}
                </div>

                ${
                    semMateriais ? "" : `
                    <div style="
                        margin-top:14px;
                        font-family: 'Cinzel', serif;
                        font-weight:800;
                        color:#facc15;
                        font-size:.92em;
                        text-transform:uppercase;
                        letter-spacing:.4px;
                    ">
                        Recompensas
                    </div>

                    <div style="margin-top:10px; display:grid; gap:8px;">
                        ${materiais.map((mat, idx) => `
                            <div style="
                                display:flex;
                                align-items:center;
                                justify-content:space-between;
                                gap:10px;
                                background: rgba(255,255,255,.045);
                                border:1px solid rgba(255,255,255,.08);
                                border-radius:10px;
                                padding:8px 10px;
                            ">
                                <div style="display:flex; align-items:center; gap:10px; min-width:0;">
                                    <div style="
                                        width:34px;
                                        height:34px;
                                        border-radius:8px;
                                        background: rgba(255,255,255,.04);
                                        display:flex;
                                        align-items:center;
                                        justify-content:center;
                                        overflow:hidden;
                                        flex-shrink:0;
                                    ">
                                        <img data-popup-mat-img="${idx}" src="/static/assets/box.png" style="width:24px; height:24px; object-fit:contain;">
                                    </div>
                                    <div style="
                                        color:#f3f4f6;
                                        font-size:.93em;
                                        line-height:1.2;
                                        word-break:break-word;
                                    ">${mat.nome}</div>
                                </div>
                                <div style="
                                    flex-shrink:0;
                                    color:#fde68a;
                                    font-weight:800;
                                    font-size:.95em;
                                ">x${mat.qtd}</div>
                            </div>
                        `).join("")}
                    </div>
                    `
                }

                <button id="btn-confirmar-popup-resultado-forja" style="
                    margin-top:16px;
                    width:100%;
                    border:none;
                    border-radius:10px;
                    padding:12px 14px;
                    background: linear-gradient(180deg, #334155, #1e293b);
                    color:#fff;
                    font-weight:800;
                    cursor:pointer;
                    box-shadow: inset 0 1px 0 rgba(255,255,255,0.08);
                ">ENTENDIDO</button>
            </div>
        </div>
    `;

    document.body.appendChild(overlay);

    if (!document.getElementById("style-popup-resultado-forja")) {
        const style = document.createElement("style");
        style.id = "style-popup-resultado-forja";
        style.textContent = `
            @keyframes surgirResultadoForja {
                from { transform: scale(.96); opacity: 0; }
                to   { transform: scale(1); opacity: 1; }
            }
        `;
        document.head.appendChild(style);
    }

    const fechar = () => removerPopupResultadoForja();

    overlay.addEventListener("click", (ev) => {
        if (ev.target === overlay) fechar();
    });

    const btnX = document.getElementById("fechar-popup-resultado-forja");
    const btnOk = document.getElementById("btn-confirmar-popup-resultado-forja");
    if (btnX) btnX.onclick = fechar;
    if (btnOk) btnOk.onclick = fechar;

    if (itemPrincipal) {
        const imgPrincipal = overlay.querySelector("[data-popup-item-principal]");
        if (imgPrincipal && typeof aplicarImagemItemForja === "function") {
            aplicarImagemItemForja(imgPrincipal, itemPrincipal);
        }
    }

    materiais.forEach((mat, idx) => {
        const imgMat = overlay.querySelector(`[data-popup-mat-img="${idx}"]`);
        if (imgMat && typeof aplicarImagemMaterialForja === "function") {
            aplicarImagemMaterialForja(imgMat, mat.id);
        }
    });
};

window.notificarResultadoTrabalhoForja = function(tipoAcao, data, cena, metaTrabalho = {}) {
    if (!data) return;

    let titulo = "Resultado";
    let subtitulo = "";
    let cor = "#22c55e";
    let icone = "✨";
    let itemPrincipal = null;
    let materiais = [];
    let infoExtra = "";

    if (tipoAcao === "forja") {
        const item = data.item_criado || data.item || data.result_item || null;
        const raridadeItem = item?.rarity || item?.raridade || "comum";

        titulo = `${getIconeRaridadeForjaPopup(raridadeItem, "⚒️")} FORJA ${getTituloRaridadeForjaPopup(raridadeItem)}!`;
        subtitulo = "Você criou um novo item.";
        cor = getCorRaridadeForjaPopup(raridadeItem, "#22c55e");
        icone = getIconeRaridadeForjaPopup(raridadeItem, "⚒️");

        if (item) {
            itemPrincipal = {
                ...item,
                nome: item.display_name || item.nome || item.base_id || "Item Forjado"
            };
        }

        if (item?.rarity || item?.raridade) {
            infoExtra += `Raridade: ${String(item.rarity || item.raridade).toUpperCase()}`;
        }

        if (data.xp_ganho) {
            infoExtra += `${infoExtra ? "\n" : ""}XP de profissão: +${data.xp_ganho}`;
        }

        if (window.mostrarLootFlutuante && item?.base_id && cena) {
            const loot = {};
            loot[item.base_id] = 1;
            window.mostrarLootFlutuante(cena, loot, data.xp_ganho || 0);
        }
    }

    else if (tipoAcao === "desmontar") {
        const raridadeItem = (
            metaTrabalho?.selected_item?.rarity ||
            metaTrabalho?.selected_item?.raridade ||
            "comum"
        );

        titulo = "DESMONTE CONCLUÍDO!";
        subtitulo = `Você desmontou: ${data.item_name || "Item"}`;
        cor = getCorRaridadeForjaPopup(raridadeItem, "#22c55e");
        icone = "♻️";

        itemPrincipal = metaTrabalho?.selected_item || {
            base_id: metaTrabalho?.base_id || data.base_id,
            nome: data.item_name || "Item Desmontado",
            display_name: data.item_name || "Item Desmontado",
            rarity: metaTrabalho?.selected_item?.rarity || metaTrabalho?.selected_item?.raridade
        };

        materiais = normalizarListaRecompensasForja(data.rewards);

        if (window.mostrarLootFlutuante && data.rewards && cena) {
            window.mostrarLootFlutuante(cena, data.rewards, 0);
        }
    }

    else if (tipoAcao === "melhorar") {
        const nomeItem = data.item_name || "Equipamento";
        const oldLevel = data.old_level ?? "?";
        const newLevel = data.new_level ?? data.final_level ?? oldLevel;
        const item = data.item || metaTrabalho?.selected_item || null;

        itemPrincipal = item
            ? {
                ...item,
                nome: item.display_name || item.nome || nomeItem
            }
            : {
                nome: nomeItem,
                display_name: nomeItem
            };

        if (data.upgrade_success) {
            const raridadeItem = item?.rarity || item?.raridade || "raro";

            titulo = "MELHORIA CONCLUÍDA!";
            subtitulo = `${nomeItem}`;
            cor = getCorRaridadeForjaPopup(raridadeItem, "#3b82f6");
            icone = "⬆️";
            infoExtra = `Nível: +${oldLevel} → +${newLevel}`;
        } else if (data.protected) {
            titulo = "SIGILO PROTEGEU!";
            subtitulo = `${nomeItem}`;
            cor = "#60a5fa";
            icone = "🛡️";
            infoExtra = data.message || `A melhoria falhou, mas o item permaneceu em +${oldLevel}.`;
        } else if (data.downgraded) {
            titulo = "MELHORIA FALHOU!";
            subtitulo = `${nomeItem}`;
            cor = "#ef4444";
            icone = "⚠️";
            infoExtra = data.message || `O item caiu de +${oldLevel} para +${newLevel}.`;
        } else {
            titulo = "MELHORIA FALHOU!";
            subtitulo = `${nomeItem}`;
            cor = "#ef4444";
            icone = "❌";
            infoExtra = data.message || `A melhoria falhou.`;
        }
    }

    if (metaTrabalho && metaTrabalho.tool_broke) {
        infoExtra += `${infoExtra ? "\n\n" : ""}⚠️ ${metaTrabalho.tool_message || "Sua ferramenta quebrou."}`;
    }

    if (typeof window.mostrarPopupResultadoForja === "function") {
        window.mostrarPopupResultadoForja({
            titulo,
            subtitulo,
            itemPrincipal,
            materiais,
            cor,
            icone,
            infoExtra
        });
        return;
    }

    // fallback
    if (window.alertaEldora) {
        window.alertaEldora(titulo, `${subtitulo}\n${infoExtra}`, "sucesso");
    }
};

window.iniciarAnimacaoTrabalho = function(duracaoSegundos, tipoAcao, metaTrabalho = {}) {
    const cena = window.jogoEldora.scene.getScene('MapaScene');
    if (!cena || !cena.player) return;

    cena.player.isGathering = true;
    cena.pararPersonagem();

    let uiContainer = cena.add.container(cena.player.x, cena.player.y - 65).setDepth(200);
    
    let txtPrincipal =
        tipoAcao === 'desmontar' ? '♻️ Desmontando ♻️' :
        tipoAcao === 'melhorar' ? '⬆️ Melhorando ⬆️' :
        '⚒️ Forjando ⚒️';

    let corPrincipal =
        tipoAcao === 'desmontar' ? '#ef4444' :
        tipoAcao === 'melhorar' ? '#3b82f6' :
        '#facc15';

    let textoRefino = cena.add.text(0, -16, txtPrincipal, {
        fontSize: '11px', fontFamily: 'Arial', color: corPrincipal, stroke: '#000', strokeThickness: 3, fontStyle: 'bold'
    }).setOrigin(0.5);

    let bgBar = cena.add.graphics();
    bgBar.fillStyle(0x0f0502, 0.8); bgBar.lineStyle(1.5, parseInt(corPrincipal.replace('#','0x')), 1);
    bgBar.fillRoundedRect(-30, -4, 60, 8, 4); bgBar.strokeRoundedRect(-30, -4, 60, 8, 4);

    let fillBar = cena.add.graphics();
    let timerTexto = cena.add.text(0, 10, `${duracaoSegundos}s`, { fontSize: '10px', color: '#fff', stroke: '#000', strokeThickness: 2 }).setOrigin(0.5);
    uiContainer.add([bgBar, fillBar, textoRefino, timerTexto]);

    let animBatida = cena.tweens.add({ targets: cena.player, y: cena.player.y - 2, angle: 3, yoyo: true, duration: 400, repeat: -1 });

    let progresso = { valor: 0 };
    cena.tweens.add({
        targets: progresso, valor: 56, duration: duracaoSegundos * 1000,
        onUpdate: () => {
            fillBar.clear();
            if (progresso.valor > 0) {
                fillBar.fillStyle(parseInt(corPrincipal.replace('#','0x')), 1);
                fillBar.fillRoundedRect(-28, -2, progresso.valor, 4, 2);
            }
            timerTexto.setText(`${Math.ceil(duracaoSegundos - (progresso.valor / 56) * duracaoSegundos)}s`);
        },
        onComplete: async () => {
            animBatida.stop(); cena.player.angle = 0; uiContainer.destroy(); cena.player.isGathering = false;
            const charId = localStorage.getItem("jogadorEldoraID");
            try {
                const endpoint =
                    tipoAcao === 'desmontar' ? '/api/dismantle/finish' :
                    tipoAcao === 'melhorar' ? '/api/equipment/upgrade/finish' :
                    '/api/crafting/finish';
                
                    const res = await fetch(endpoint, {
                    method: 'POST', headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ user_id: charId })
                });
                const data = await res.json();
                
                if (data.success || data.status === 'success') {
                    if (typeof window.carregarMeuPerfil === 'function') {
                        // Força a atualização do cache se a API devolver dados frescos
                        if (data.player_data) window.perfilDadosGlobais = data.player_data;
                        await window.carregarMeuPerfil();
                    }

                    // Notificação centralizada:
                    // - forja: mostra item criado, raridade e XP
                    // - desmontar: mostra item desmontado e materiais recebidos
                    // - melhorar: mostra sucesso/falha/proteção e nível final
                    if (typeof window.notificarResultadoTrabalhoForja === "function") {
                        window.notificarResultadoTrabalhoForja(tipoAcao, data, cena, metaTrabalho);
                    } else if (window.alertaEldora) {
                        window.alertaEldora("Trabalho Concluído", "A ação foi finalizada com sucesso.", "sucesso");
                    }

                } else {
                    if (window.alertaEldora) window.alertaEldora("Aviso", data.error || "Ocorreu um erro no processo.", "erro");
                }
            } catch (e) { console.error(e); }
        }
    }); 
};