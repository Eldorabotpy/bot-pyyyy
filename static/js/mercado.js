// Atualizações remotas preservam o formulário de venda em preenchimento.
let mercadoSocketAtual = null;
let mercadoSincronizando = false;
let mercadoPerfilPendente = false;
let mercadoVitrinePendente = false;
async function sincronizarMercadoRemoto(atualizarPerfil = false) {
    mercadoPerfilPendente ||= atualizarPerfil;
    mercadoVitrinePendente ||= !!window.__mercadoAberto;
    if (mercadoSincronizando) return;
    mercadoSincronizando = true;
    try {
        while (mercadoPerfilPendente || mercadoVitrinePendente) {
            const perfil = mercadoPerfilPendente, vitrine = mercadoVitrinePendente;
            mercadoPerfilPendente = mercadoVitrinePendente = false;
            const tarefas = [];
            if (perfil && typeof window.carregarMeuPerfil === 'function') tarefas.push(window.carregarMeuPerfil());
            if (vitrine && window.__mercadoAberto) tarefas.push(carregarVitrineMercado());
            await Promise.allSettled(tarefas);
        }
    } finally { mercadoSincronizando = false; }
}
function receberAtualizacaoMercado(dados) {
    const meuId = String(localStorage.getItem('jogadorEldoraID') || '');
    const afetado = Array.isArray(dados?.jogadores) && dados.jogadores.some(id => String(id) === meuId);
    return sincronizarMercadoRemoto(afetado);
}
function reconectarMercado() { return sincronizarMercadoRemoto(true); }
window.configurarOuvintesMercado = function(socket) {
    if (!socket || socket === mercadoSocketAtual) return;
    if (mercadoSocketAtual) {
        mercadoSocketAtual.off('mercadoAtualizado', receberAtualizacaoMercado);
        mercadoSocketAtual.off('connect', reconectarMercado);
    }
    mercadoSocketAtual = socket;
    socket.on('mercadoAtualizado', receberAtualizacaoMercado);
    socket.on('connect', reconectarMercado);
};
if (window.eldoraSocket) window.configurarOuvintesMercado(window.eldoraSocket);
document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'visible' && mercadoSocketAtual) reconectarMercado();
});

const mercadoOperacoesPendentes = new Set();
// ==========================================
// LÓGICA DO MERCADO DO AVENTUREIRO
// ==========================================

let mercadoEntradaAnterior = null;
function mercadoIsolarEventos(modal) {
    if (!modal || modal.dataset.entradaIsolada) return;
    modal.dataset.entradaIsolada = '1';
    for (const evento of ['pointerdown', 'pointerup', 'pointermove', 'mousedown', 'mouseup', 'touchstart', 'touchend', 'touchmove', 'wheel', 'keydown', 'keyup', 'click', 'dblclick']) {
        modal.addEventListener(evento, e => {
            // Preserva foco, digitação, seleção e rolagem nativos.
            if (evento === 'click') {
                const lista = document.getElementById('lista-dropdown-venda');
                const botao = document.getElementById('btn-dropdown-venda');
                if (lista && !lista.contains(e.target) && !botao?.contains(e.target)) lista.style.display = 'none';
            }
            e.stopPropagation();
        });
    }
}

function abrirMercado() {
    if (!window.__mercadoAberto) {
        const cena = window.jogoEldora?.scene?.getScene('MapaScene');
        mercadoEntradaAnterior = cena ? { cena, mouse: cena.input?.enabled, teclado: cena.input?.keyboard?.enabled } : null;
        if (cena) {
            cena.motorCacada?.pararAutoCacada?.('mercado', false);
            cena.isMoving = false;
            cena.player?.body?.stop();
            if (cena.input) cena.input.enabled = false;
            if (cena.input?.keyboard) {
                cena.input.keyboard.resetKeys?.();
                cena.input.keyboard.enabled = false;
            }
        }
    }
    window.__mercadoAberto = true;
    mercadoIsolarEventos(document.getElementById('ui-mercado'));
    if (typeof window.ocultarMenuGlobalEldora === "function") {
        window.ocultarMenuGlobalEldora();
    }

    document.getElementById('ui-mercado').style.display = 'flex';
    mudarAbaMercado('aba-comprar-ouro', null);
    
    document.querySelectorAll('.btn-passe-mapa, .btn-social-mapa').forEach(btn => btn.style.display = 'none');

    if (typeof carregarInventarioNoMercado === 'function') carregarInventarioNoMercado(); 
    if (typeof carregarVitrineMercado === 'function') carregarVitrineMercado();      
}

function fecharMercado() {
    document.activeElement?.blur?.();
    window.__mercadoAberto = false;
    const anterior = mercadoEntradaAnterior;
    mercadoEntradaAnterior = null;
    if (anterior?.cena?.input) {
        anterior.cena.input.enabled = anterior.mouse;
        if (anterior.cena.input.keyboard) {
            anterior.cena.input.keyboard.resetKeys?.();
            anterior.cena.input.keyboard.enabled = anterior.teclado;
        }
    }
    const detalhes = document.getElementById('modal-detalhes-mercado');
    if (detalhes) detalhes.style.display = 'none';
    document.getElementById('ui-mercado').style.display = 'none';

    if (typeof window.mostrarMenuGlobalEldora === "function") {
        window.mostrarMenuGlobalEldora();
    }

    document.querySelectorAll('.btn-passe-mapa, .btn-social-mapa').forEach(btn => btn.style.display = 'flex');
}

function mercadoEscapeHtml(valor) {
    return String(valor ?? "")
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

function mercadoItemUid(item) {
    return String(item?.id || item?.uid || item?.item_id || "");
}

function mercadoItemBaseId(item) {
    return String(item?.base_id || item?.item_id || item?.id || "");
}

function mercadoItemEstaEquipado(item) {
    const uid = mercadoItemUid(item);
    if (!uid) return false;

    const equips = window.perfilDadosGlobais?.equipamentos || [];

    return equips.some(eq => {
        if (!eq || eq.vazio) return false;
        return String(eq.uid || eq.id || "") === uid;
    });
}

function mercadoItemEhUnico(item) {
    const tipo = String(item?.tipo || item?.type || '').toLowerCase();
    if (item?.stackable === false || ['weapon','armor','helmet','boots','ring','necklace','earring','tool','equipamento','arma','armadura','ferramenta'].includes(tipo)) return true;
    if (item?.stackable === true || ['potion','pocao','consumable','consumivel','material','reagent'].includes(tipo)) return false;
    return !!(item?.durability || Number(item?.upgrade_level || item?.refino || 0) > 0 || Object.keys(item?.enchantments || {}).length);
}

function mercadoInteiroPositivo(valor) {
    const texto = String(valor ?? '').trim();
    const numero = Number(texto);
    return /^\d+$/.test(texto) && Number.isSafeInteger(numero) && numero > 0 ? numero : 0;
}

function mercadoObterPastaItem(item) {
    if (typeof window.obterPastaItem === "function") {
        return window.obterPastaItem(item);
    }

    const tipo = String(item?.tipo || item?.type || "").toLowerCase();

    if (["tool", "ferramenta", "lenhador", "minerador", "colhedor", "esfolador", "ferreiro", "armeiro", "alfaiate", "joalheiro", "curtidor"].includes(tipo)) {
        return "ferramentas";
    }

    if (["weapon", "armor", "helmet", "boots", "ring", "necklace", "earring", "equipamento", "arma", "armadura", "elmo", "anel", "colar", "brinco"].includes(tipo)) {
        return "equipamentos";
    }

    if (["potion", "pocao", "consumable", "scroll", "pergaminho", "chest", "box", "consumivel"].includes(tipo)) {
        return "consumiveis";
    }

    return "materiais";
}

function mercadoCaminhosImagemItem(item) {
    const base = "https://raw.githubusercontent.com/Eldorabotpy/static-img/main/assets/";
    const id = mercadoItemBaseId(item);

    if (!id) return ["/static/assets/box.png"];

    const pasta = mercadoObterPastaItem(item);
    const caminhos = [];

    if (pasta === "equipamentos") {
        caminhos.push(`${base}itens/equipamentos/work_${id}.png`);
        caminhos.push(`${base}itens/equipamentos/${id}.png`);
    } else {
        caminhos.push(`${base}itens/${pasta}/${id}.png`);
        caminhos.push(`${base}itens/${pasta}/work_${id}.png`);
    }

    caminhos.push(`${base}itens/equipamentos/work_${id}.png`);
    caminhos.push(`${base}itens/equipamentos/${id}.png`);
    caminhos.push(`${base}itens/ferramentas/${id}.png`);
    caminhos.push(`${base}itens/consumiveis/${id}.png`);
    caminhos.push(`${base}itens/materiais/${id}.png`);
    caminhos.push("/static/assets/box.png");

    return [...new Set(caminhos)];
}

function aplicarImagemMercado(imgEl, item) {
    if (!imgEl) return;

    const caminhos = mercadoCaminhosImagemItem(item);
    let idx = 0;

    imgEl.onerror = function() {
        idx++;

        if (idx < caminhos.length) {
            this.src = caminhos[idx];
        } else {
            this.onerror = null;
            this.src = "/static/assets/box.png";
        }
    };

    imgEl.src = caminhos[0];
}

// 🔥 MÁGICA DO INVENTÁRIO NO MERCADO (MODERNO) 🔥
function carregarInventarioNoMercado() {
    const listaDropdown = document.getElementById('lista-dropdown-venda');
    const inputEscondido = document.getElementById('select-item-venda');
    const displaySelecionado = document.getElementById('dropdown-venda-selecionado');
    const btnDropdown = document.getElementById('btn-dropdown-venda');
    
    if (!listaDropdown || !inputEscondido) return;

    // Reseta o formulário visualmente ao carregar a tela
    listaDropdown.innerHTML = '';
    inputEscondido.value = '';
    listaDropdown.style.display = 'none';
    const preview = document.getElementById('preview-item-venda-mercado');
    if (preview) preview.style.display = 'none';
    const quantidade = document.getElementById('input-qtd');
    quantidade.disabled = false;
    quantidade.value = '1';
    quantidade.removeAttribute('max');
    displaySelecionado.innerHTML = '<span style="font-size: 1.2em; opacity: 0.3;">📦</span> <span style="color: #cbd5e1;">Selecionar item...</span>';
    btnDropdown.style.borderColor = '#475569';
    btnDropdown.style.boxShadow = '0 4px 6px rgba(0,0,0,0.4)';

    if (!window.perfilDadosGlobais || !window.perfilDadosGlobais.inventario) {
        listaDropdown.innerHTML = '<div style="padding: 15px; text-align: center; color: #64748b;">Mochila vazia.</div>';
        return;
    }

    const inventario = window.perfilDadosGlobais.inventario;
    const linkBaseNuvem = window.CATALOGO_SISTEMA ? "https://raw.githubusercontent.com/Eldorabotpy/static-img/main/assets/" : "/static/assets/";

    let itensValidos = 0;

    inventario.forEach(item => {
        // Bloqueia itens não trocáveis e moedas base (gemas)
        if (item.tradable === false || item.id === 'gems' || item.base_id === 'gems') {
            return; 
        }
        
        // Segurança visual: item equipado nem aparece na lista.
        // A segurança real fica no backend.
        if (mercadoItemEstaEquipado(item)) {
            return;
        }

        itensValidos++;

        let idItem = mercadoItemBaseId(item);
        let urlImg = mercadoCaminhosImagemItem(item)[0];
        
        // Log de debug para você ver no F12 (Console do navegador) se ele está tentando baixar o link certo
        console.log("Tentando carregar imagem de:", urlImg);
        
        let textoQuantidade = item.qtd > 1 ? `<span style="color: #facc15; font-size: 0.85em; font-weight: bold; background: rgba(0,0,0,0.5); padding: 2px 6px; border-radius: 6px;">x${item.qtd}</span>` : '';
        let nomeItem = item.display_name || item.nome || 'Item Desconhecido';
        
        // Sistema de cores por raridade
        const coresRaridade = {'comum': '#94a3b8', 'incomum': '#22c55e', 'raro': '#3b82f6', 'epico': '#a855f7', 'lendario': '#eab308', 'mitico': '#ef4444'};
        const corBordaItem = coresRaridade[(item.raridade || 'comum').toLowerCase()] || '#475569';

        // Cria a linha (opção) clicável
        let divOpcao = document.createElement('div');
        divOpcao.style.cssText = "padding: 10px 15px; display: flex; align-items: center; gap: 12px; border-bottom: 1px solid #0f172a; cursor: pointer; transition: background 0.2s;";
        divOpcao.onmouseover = () => divOpcao.style.background = 'rgba(59, 130, 246, 0.1)';
        divOpcao.onmouseout = () => divOpcao.style.background = 'transparent';
        
        divOpcao.onclick = () => {
            selecionarItemDropdown(item, nomeItem, textoQuantidade, corBordaItem);
        };

        divOpcao.innerHTML = `
            <div style="width: 38px; height: 38px; background: #000; border-radius: 8px; display: flex; align-items: center; justify-content: center; border: 2px solid ${corBordaItem}; box-shadow: inset 0 0 10px rgba(0,0,0,0.8);">
                <img data-img-mercado-venda="1" src="/static/assets/box.png" style="max-width: 28px; max-height: 28px; object-fit: contain; filter: drop-shadow(0 2px 4px rgba(0,0,0,0.8));">
            </div>
            <div style="color: #f8fafc; font-size: 0.95em; font-weight: bold; flex: 1;">${mercadoEscapeHtml(nomeItem)}</div>
            <div>${textoQuantidade}</div>
        `;

        listaDropdown.appendChild(divOpcao);
        aplicarImagemMercado(divOpcao.querySelector('[data-img-mercado-venda="1"]'), item);

    });

    if (itensValidos === 0) {
        listaDropdown.innerHTML = '<div style="padding: 20px; text-align: center; color: #64748b; font-size: 0.9em; font-style: italic;">Nenhum item da sua mochila pode ser vendido.</div>';
    }
}

// 🖱️ Lógica para abrir/fechar o menu suspenso customizado
function toggleDropdownVenda() {
    const lista = document.getElementById('lista-dropdown-venda');
    if (lista.style.display === 'none' || lista.style.display === '') {
        lista.style.display = 'block';
    } else {
        lista.style.display = 'none';
    }
}

// ✅ Lógica que roda ao clicar em um item da lista
function selecionarItemDropdown(item, nomeItem, textoQuantidade, corBorda) {
    const idItem = mercadoItemUid(item);
    const urlImg = mercadoCaminhosImagemItem(item)[0];

    document.getElementById('select-item-venda').value = idItem;

    const display = document.getElementById('dropdown-venda-selecionado');

    display.innerHTML = `
        <div style="width: 38px; height: 38px; min-width: 38px; background: #000; border-radius: 8px; display: flex; align-items: center; justify-content: center; border: 1px solid ${corBorda}; box-shadow: 0 0 8px rgba(0,0,0,0.8);">
            <img id="img-item-venda-selecionado" src="/static/assets/box.png" style="max-width: 26px; max-height: 26px; object-fit: contain;">
        </div>
        <div style="display: flex; flex-direction: column; justify-content: center; overflow: hidden; width: 100%;">
            <div style="color: #f8fafc; font-weight: bold; font-size: 1em; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; line-height: 1.2;">
                ${mercadoEscapeHtml(nomeItem)}
            </div>
            <div style="font-size: 0.8em; margin-top: 2px;">
                ${textoQuantidade || '<span style="color: #64748b;">1 unidade</span>'}
            </div>
        </div>
    `;

    aplicarImagemMercado(document.getElementById("img-item-venda-selecionado"), item);

    const btnDropdown = document.getElementById('btn-dropdown-venda');
    btnDropdown.style.borderColor = corBorda;

    document.getElementById('lista-dropdown-venda').style.display = 'none';

    renderizarPreviewItemVendaMercado(item);
}

function renderizarPreviewItemVendaMercado(item) {
    let painel = document.getElementById("preview-item-venda-mercado");

    if (!painel) {
        const area = document.getElementById("btn-dropdown-venda")?.parentElement;

        if (!area) return;

        area.insertAdjacentHTML("beforeend", `
            <div id="preview-item-venda-mercado" style="
                display:none;
                margin-top:10px;
                background:rgba(15,23,42,.92);
                border:1px solid #334155;
                border-radius:10px;
                padding:10px;
                box-shadow: inset 0 0 18px rgba(0,0,0,.45);
            "></div>
        `);

        painel = document.getElementById("preview-item-venda-mercado");
    }

    const nome = item.nome || item.display_name || item.name || mercadoItemBaseId(item).replace(/_/g, " ");
    const desc = item.desc || item.description || "Sem descrição.";
    const raridade = item.raridade || item.rarity || "comum";
    const refino = Number(item.upgrade_level ?? item.refino ?? item.upgrade ?? 0) || 0;
    const classe = item.classe_req || item.class_req || item.required_class || item.class || "Livre";
    const tipo = item.tipo || item.type || "item";
    const qtd = Number(item.qtd || item.quantity || item.quantidade || 1) || 1;

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

    const cor = cores[String(raridade).toLowerCase()] || "#94a3b8";

    const stats = item.stats || item.attributes || item.enchantments || {};
    let statsHtml = "";

    if (stats && Object.keys(stats).length > 0) {
        for (const [key, raw] of Object.entries(stats)) {
            let valor = raw;

            if (typeof raw === "object" && raw !== null) {
                if (raw.value !== undefined && raw.value !== null) {
                    valor = raw.value;
                } else if (raw.valor !== undefined && raw.valor !== null) {
                    valor = raw.valor;
                } else if (raw.min !== undefined && raw.max !== undefined) {
                    valor = `${raw.min}-${raw.max}`;
                } else {
                    valor = "";
                }
            }

            if (valor === "" || valor === undefined || valor === null) continue;

            statsHtml += `
                <span style="
                    background:#020617;
                    border:1px solid #334155;
                    color:#e2e8f0;
                    border-radius:6px;
                    padding:3px 7px;
                    font-size:.75em;
                    font-weight:bold;
                ">
                    ${mercadoEscapeHtml(key).replace(/_/g, " ").toUpperCase()}: +${mercadoEscapeHtml(valor)}
                </span>
            `;
        }
    } else {
        statsHtml = `<span style="color:#64748b; font-size:.78em;">Sem atributos especiais.</span>`;
    }

    const unico = mercadoItemEhUnico(item);
    const inputQtd = document.getElementById("input-qtd");

    if (inputQtd) {
        inputQtd.max = qtd;

        if (unico) {
            inputQtd.value = 1;
            inputQtd.disabled = true;
        } else {
            inputQtd.disabled = false;
            if (Number(inputQtd.value || 1) > qtd) inputQtd.value = qtd;
        }
    }

    painel.innerHTML = `
        <div style="display:flex; gap:10px; align-items:flex-start;">
            <div style="
                width:46px;
                height:46px;
                background:#020617;
                border:2px solid ${cor};
                border-radius:9px;
                display:flex;
                align-items:center;
                justify-content:center;
                flex-shrink:0;
            ">
                <img id="preview-img-venda-mercado" src="/static/assets/box.png" style="max-width:36px; max-height:36px; object-fit:contain;">
            </div>

            <div style="flex:1; min-width:0;">
                <div style="
                    color:#fff;
                    font-weight:900;
                    font-family:'Cinzel',serif;
                    font-size:.92em;
                    line-height:1.2;
                ">
                    ${mercadoEscapeHtml(nome)} ${refino > 0 ? `<span style="color:#facc15;">+${refino}</span>` : ""}
                </div>

                <div style="font-size:.72em; color:${cor}; font-weight:900; text-transform:uppercase; margin-top:2px;">
                    ${mercadoEscapeHtml(raridade)}
                </div>

                <div style="font-size:.72em; color:#94a3b8; margin-top:4px;">
                    Tipo: <b style="color:#e2e8f0;">${mercadoEscapeHtml(tipo)}</b> |
                    Classe: <b style="color:#e2e8f0;">${mercadoEscapeHtml(classe)}</b>
                </div>
            </div>
        </div>

        <div style="
            margin-top:8px;
            color:#cbd5e1;
            font-size:.78em;
            line-height:1.35;
            border-top:1px solid rgba(255,255,255,.08);
            padding-top:8px;
        ">
            ${mercadoEscapeHtml(desc)}
        </div>

        <div style="
            display:flex;
            flex-wrap:wrap;
            gap:5px;
            margin-top:8px;
        ">
            ${statsHtml}
        </div>

        ${item.durability ? `
            <div style="margin-top:8px;">
                <div style="display:flex; justify-content:space-between; color:#94a3b8; font-size:.72em; font-weight:bold;">
                    <span>DURABILIDADE</span>
                    <span>${item.durability[0]} / ${item.durability[1]}</span>
                </div>
                <div style="height:5px; background:#020617; border-radius:4px; overflow:hidden; border:1px solid #334155;">
                    <div style="height:100%; width:${Math.max(0, Math.min(100, (Number(item.durability[0] || 0) / Number(item.durability[1] || 1)) * 100))}%; background:#22c55e;"></div>
                </div>
            </div>
        ` : ""}

        ${unico ? `
            <div style="margin-top:8px; color:#facc15; font-size:.72em; font-weight:bold;">
                ⚠️ Item único: só pode vender 1 unidade por anúncio.
            </div>
        ` : ""}
    `;

    aplicarImagemMercado(document.getElementById("preview-img-venda-mercado"), item);

    painel.style.display = "block";
}

// 🛡️ Segurança: Fecha a lista se o jogador clicar em qualquer outro lugar da tela
document.addEventListener('click', function(event) {
    const btn = document.getElementById('btn-dropdown-venda');
    const lista = document.getElementById('lista-dropdown-venda');
    if (btn && lista && !btn.contains(event.target) && !lista.contains(event.target)) {
        lista.style.display = 'none';
    }
});

function mudarAbaMercado(abaId) {
    document.querySelectorAll('#ui-mercado .conteudo-mercado').forEach(aba => {
        aba.style.display = aba.id === abaId ? 'block' : 'none';
    });
    document.querySelectorAll('#ui-mercado .tab-mercado').forEach(btn => {
        btn.setAttribute('aria-selected', String(btn.dataset.aba === abaId));
    });
    const busca = document.getElementById('mercado-busca-area');
    if (busca) busca.hidden = abaId === 'aba-vender';
    const dropdown = document.getElementById('lista-dropdown-venda');
    if (dropdown) dropdown.style.display = 'none';
    filtrarMercado();
}

function filtrarMercado() {
    const normalizar = valor => String(valor || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
    const busca = normalizar(document.getElementById('mercado-busca')?.value);
    for (const id of ['lista-ouro', 'lista-gemas']) {
        const lista = document.getElementById(id);
        if (!lista) continue;
        const cards = lista.querySelectorAll('.mercado-card');
        let visiveis = 0;
        cards.forEach(card => {
            card.hidden = !normalizar(card.dataset.busca).includes(busca);
            if (!card.hidden) visiveis++;
        });
        const vazio = lista.parentElement.querySelector('.mercado-sem-resultados');
        if (vazio) vazio.hidden = !busca || !cards.length || visiveis > 0;
    }
}

// 🔥 CÁLCULO DA TAXA DO REINO (10%) 🔥
function calcularTaxaReino() {
    let precoInput = mercadoInteiroPositivo(document.getElementById('input-preco').value);
    let moeda = document.getElementById('select-moeda').value;
    
    if (!precoInput || precoInput <= 0) {
        document.getElementById('res-bruto').innerText = `0`;
        document.getElementById('res-taxa').innerText = `-0`;
        document.getElementById('res-liquido').innerText = `0`;
        return;
    }

    let precoBruto = parseInt(precoInput);
    let taxa = Math.floor(precoBruto / 10); 
    let precoLiquido = precoBruto - taxa;

    let simbolo = (moeda === 'ouro') ? '🪙' : '💎';

    document.getElementById('res-bruto').innerText = `${precoBruto} ${simbolo}`;
    document.getElementById('res-taxa').innerText = `-${taxa} ${simbolo}`;
    document.getElementById('res-liquido').innerText = `${precoLiquido} ${simbolo}`;
}

window.__mercadoAnunciosPorId = window.__mercadoAnunciosPorId || {};

function mercadoHtml(valor) {
    return String(valor ?? "")
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

function mercadoCorRaridade(raridade) {
    const r = String(raridade || "comum").toLowerCase();

    return {
        comum: "#94a3b8",
        bom: "#22c55e",
        incomum: "#22c55e",
        raro: "#3b82f6",
        epico: "#a855f7",
        lendario: "#eab308",
        unico: "#ef4444",
        mitico: "#00f2fe"
    }[r] || "#94a3b8";
}

function mercadoItemLikeFromAnuncio(anuncio) {
    const d = anuncio.item_details || {};

    return {
        base_id: anuncio.item_id || d.base_id,
        id: anuncio.item_id || d.base_id,
        tipo: d.tipo || anuncio.tipo,
        type: d.tipo || anuncio.tipo,
        raridade: d.raridade,
        rarity: d.raridade
    };
}

function mercadoPastaItem(item) {
    if (typeof window.obterPastaItem === "function") {
        return window.obterPastaItem(item);
    }

    const tipo = String(item?.tipo || item?.type || "").toLowerCase();

    if (["tool", "ferramenta", "lenhador", "minerador", "colhedor", "esfolador", "ferreiro", "armeiro", "alfaiate", "joalheiro", "curtidor"].includes(tipo)) {
        return "ferramentas";
    }

    if (["weapon", "armor", "helmet", "boots", "ring", "necklace", "earring", "equipamento", "arma", "armadura", "elmo", "anel", "colar", "brinco"].includes(tipo)) {
        return "equipamentos";
    }

    if (["potion", "pocao", "consumable", "scroll", "pergaminho", "chest", "box", "consumivel"].includes(tipo)) {
        return "consumiveis";
    }

    return "materiais";
}

function mercadoCaminhosImagem(item) {
    const base = "https://raw.githubusercontent.com/Eldorabotpy/static-img/main/assets/";
    const id = item?.base_id || item?.item_id || item?.id || "";

    if (!id) return ["/static/assets/box.png"];

    const pasta = mercadoPastaItem(item);
    const caminhos = [];

    if (pasta === "equipamentos") {
        caminhos.push(`${base}itens/equipamentos/work_${id}.png`);
        caminhos.push(`${base}itens/equipamentos/${id}.png`);
    } else {
        caminhos.push(`${base}itens/${pasta}/${id}.png`);
        caminhos.push(`${base}itens/${pasta}/work_${id}.png`);
    }

    caminhos.push(`${base}itens/equipamentos/work_${id}.png`);
    caminhos.push(`${base}itens/equipamentos/${id}.png`);
    caminhos.push(`${base}itens/ferramentas/${id}.png`);
    caminhos.push(`${base}itens/consumiveis/${id}.png`);
    caminhos.push(`${base}itens/materiais/${id}.png`);
    caminhos.push("/static/assets/box.png");

    return [...new Set(caminhos)];
}

function mercadoAplicarImagem(imgEl, item) {
    if (!imgEl) return;

    const caminhos = mercadoCaminhosImagem(item);
    let idx = 0;

    imgEl.onerror = function() {
        idx++;

        if (idx < caminhos.length) {
            this.src = caminhos[idx];
        } else {
            this.onerror = null;
            this.src = "/static/assets/box.png";
        }
    };

    imgEl.src = caminhos[0];
}

function mercadoStatsHtml(stats) {
    if (!stats || Object.keys(stats).length === 0) {
        return `<span style="color:#64748b; font-size:.78em;">Sem atributos especiais.</span>`;
    }

    let html = "";

    for (const [key, raw] of Object.entries(stats)) {
        let valor = raw;

        if (typeof raw === "object" && raw !== null) {
            if (raw.value !== undefined) valor = raw.value;
            else if (raw.valor !== undefined) valor = raw.valor;
            else if (raw.min !== undefined && raw.max !== undefined) valor = `${raw.min}-${raw.max}`;
            else continue;
        }

        if (valor === undefined || valor === null || valor === "") continue;

        html += `
            <span style="
                background:#020617;
                border:1px solid #334155;
                color:#e2e8f0;
                border-radius:7px;
                padding:4px 7px;
                font-size:.75em;
                font-weight:bold;
            ">
                ${mercadoHtml(key).replace(/_/g, " ").toUpperCase()}: +${mercadoHtml(valor)}
            </span>
        `;
    }

    return html || `<span style="color:#64748b; font-size:.78em;">Sem atributos especiais.</span>`;
}

function abrirDetalhesMercado(idVenda) {
    const anuncio = window.__mercadoAnunciosPorId[idVenda];
    if (!anuncio) return;

    const d = anuncio.item_details || {};
    const itemLike = mercadoItemLikeFromAnuncio(anuncio);

    const raridade = d.raridade || "comum";
    const cor = mercadoCorRaridade(raridade);
    const refino = Number(d.refino || 0);
    const qtd = Number(anuncio.quantidade || 1);
    const simbolo = anuncio.moeda === "ouro" ? "🪙" : "💎";
    const meuId = String(localStorage.getItem("jogadorEldoraID") || "");
    const meuAnuncio = String(anuncio.seller_id || "") === meuId;

    let modal = document.getElementById("modal-detalhes-mercado");

    if (!modal) {
        modal = document.createElement("div");
        modal.id = "modal-detalhes-mercado";
        mercadoIsolarEventos(modal);
        modal.style.cssText = `
            display:none;
            position:fixed;
            inset:0;
            background:rgba(0,0,0,.82);
            z-index:100000;
            justify-content:center;
            align-items:center;
            backdrop-filter:blur(5px);
            padding:12px;
            box-sizing:border-box;
        `;
        document.body.appendChild(modal);
    }

    modal.innerHTML = `
        <div style="
            width:min(92vw, 380px);
            max-height:88vh;
            overflow:hidden;
            display:flex;
            flex-direction:column;
            background:linear-gradient(180deg, #1e293b, #020617);
            border:2px solid ${cor};
            border-radius:16px;
            box-shadow:0 18px 45px rgba(0,0,0,.9), 0 0 25px ${cor}55;
            color:#fff;
            position:relative;
        ">
            <button onclick="document.getElementById('modal-detalhes-mercado').style.display='none'" style="
                position:absolute;
                top:10px;
                right:10px;
                width:30px;
                height:30px;
                border-radius:50%;
                border:1px solid #ef4444;
                background:#7f1d1d;
                color:#fecaca;
                font-weight:900;
                cursor:pointer;
                z-index:2;
            ">✕</button>

            <div style="
                padding:16px 16px 10px;
                overflow-y:auto;
                min-height:0;
                flex:1;
                text-align:center;
                scrollbar-width:thin;
            ">
                <div style="
                    width:118px;
                    height:118px;
                    margin:0 auto 10px;
                    background:radial-gradient(circle, rgba(255,255,255,.08), rgba(0,0,0,.65));
                    border:2px solid ${cor};
                    border-radius:18px;
                    display:flex;
                    align-items:center;
                    justify-content:center;
                    box-shadow:inset 0 0 22px rgba(0,0,0,.7), 0 0 18px ${cor}55;
                ">
                    <img id="modal-img-mercado-detalhe" src="/static/assets/box.png" style="max-width:96px; max-height:96px; object-fit:contain;">
                </div>

                <div style="font-family:'Cinzel',serif; font-size:1.12em; font-weight:900; line-height:1.25;">
                    ${mercadoHtml(d.nome || anuncio.nome_item)}
                    ${refino > 0 ? `<span style="color:#facc15;"> +${refino}</span>` : ""}
                </div>

                <div style="margin-top:4px; color:${cor}; font-weight:900; font-size:.78em; text-transform:uppercase;">
                    ${mercadoHtml(raridade)}
                </div>

                <div style="
                    margin-top:8px;
                    display:flex;
                    gap:6px;
                    justify-content:center;
                    flex-wrap:wrap;
                    font-size:.78em;
                ">
                    <span style="background:#020617; border:1px solid #334155; padding:4px 8px; border-radius:8px;">
                        Tipo: <b>${mercadoHtml(d.tipo || anuncio.tipo || "item")}</b>
                    </span>
                    <span style="background:#020617; border:1px solid #334155; padding:4px 8px; border-radius:8px;">
                        Classe: <b>${mercadoHtml(d.classe || "Livre")}</b>
                    </span>
                    <span style="background:#020617; border:1px solid #334155; padding:4px 8px; border-radius:8px;">
                        Qtd: <b>${qtd}</b>
                    </span>
                </div>

                <div style="
                    margin-top:10px;
                    padding-top:10px;
                    border-top:1px solid rgba(255,255,255,.1);
                    color:#cbd5e1;
                    font-size:.86em;
                    line-height:1.4;
                    text-align:left;
                ">
                    ${mercadoHtml(d.descricao || "Sem descrição.")}
                </div>

                <div style="
                    margin-top:10px;
                    display:flex;
                    flex-wrap:wrap;
                    gap:6px;
                    justify-content:center;
                ">
                    ${mercadoStatsHtml(d.stats || {})}
                    ${window.renderRuneDetails?.(d) || ''}
                </div>

                ${d.durability ? `
                    <div style="margin-top:12px; text-align:left;">
                        <div style="display:flex; justify-content:space-between; color:#94a3b8; font-size:.75em; font-weight:bold;">
                            <span>DURABILIDADE</span>
                            <span>${d.durability[0]} / ${d.durability[1]}</span>
                        </div>
                        <div style="height:7px; background:#020617; border:1px solid #334155; border-radius:5px; overflow:hidden;">
                            <div style="
                                height:100%;
                                width:${Math.max(0, Math.min(100, (Number(d.durability[0] || 0) / Number(d.durability[1] || 1)) * 100))}%;
                                background:#22c55e;
                            "></div>
                        </div>
                    </div>
                ` : ""}

                <div style="
                    margin-top:12px;
                    padding:10px;
                    background:rgba(0,0,0,.35);
                    border:1px dashed #475569;
                    border-radius:10px;
                    display:grid;
                    gap:5px;
                    text-align:left;
                    font-size:.86em;
                ">
                    <div style="display:flex; justify-content:space-between;">
                        <span>Vendedor</span>
                        <b style="color:${meuAnuncio ? '#facc15' : '#e2e8f0'};">${meuAnuncio ? 'Você' : mercadoHtml(anuncio.vendedor)}</b>
                    </div>
                    <div style="display:flex; justify-content:space-between;">
                        <span>Preço total</span>
                        <b style="color:${anuncio.moeda === 'ouro' ? '#facc15' : '#60a5fa'};">${anuncio.preco} ${simbolo}</b>
                    </div>
                    <div style="display:flex; justify-content:space-between;">
                        <span>Preço unitário</span>
                        <b>${Number(anuncio.preco_unitario ?? anuncio.preco / Math.max(1, qtd)).toLocaleString("pt-BR", { maximumFractionDigits: 2 })} ${simbolo}</b>
                    </div>
                </div>
            </div>

            <div style="
                padding:12px;
                border-top:1px solid rgba(255,255,255,.08);
                background:#020617;
                display:flex;
                gap:8px;
            ">
                ${meuAnuncio ? `
                    <button onclick="document.getElementById('modal-detalhes-mercado').style.display='none'; cancelarVendaMercado('${anuncio.id_venda}')" style="
                        flex:1;
                        padding:11px;
                        border-radius:8px;
                        border:1px solid #f87171;
                        background:linear-gradient(180deg, #ef4444, #991b1b);
                        color:white;
                        font-weight:900;
                        cursor:pointer;
                    ">Cancelar anúncio</button>
                ` : `
                    <button onclick="document.getElementById('modal-detalhes-mercado').style.display='none'; comprarItemMercado('${anuncio.id_venda}', '${anuncio.moeda}')" style="
                        flex:1;
                        padding:11px;
                        border-radius:8px;
                        border:1px solid #22c55e;
                        background:linear-gradient(180deg, #16a34a, #14532d);
                        color:white;
                        font-weight:900;
                        cursor:pointer;
                    ">Comprar por ${anuncio.preco} ${simbolo}</button>
                `}
            </div>
        </div>
    `;

    mercadoAplicarImagem(document.getElementById("modal-img-mercado-detalhe"), itemLike);
    modal.style.display = "flex";
}

// 🔥 MÁGICA DA VITRINE DO MERCADO (COM VISUAL PREMIUM) 🔥
let mercadoVersaoVitrine = 0;
async function carregarVitrineMercado() {
    try {
        const versao = ++mercadoVersaoVitrine;
        const res = await fetch('/api/mercado/listar', { cache: 'no-store' });
        const data = await res.json();
        if (versao !== mercadoVersaoVitrine) return;

        if (!data.sucesso) {
            if (window.alertaEldora) window.alertaEldora("Mercado", data.erro || "Erro ao carregar mercado.", "erro");
            return;
        }

        const listaOuro = document.getElementById('lista-ouro');
        const listaGemas = document.getElementById('lista-gemas');
        const meuId = String(localStorage.getItem("jogadorEldoraID") || "");

        listaOuro.innerHTML = '';
        listaGemas.innerHTML = '';
        window.__mercadoAnunciosPorId = {};

        function criarCard(anuncio, simbolo) {
            window.__mercadoAnunciosPorId[anuncio.id_venda] = anuncio;

            const d = anuncio.item_details || {};
            const itemLike = mercadoItemLikeFromAnuncio(anuncio);
            const cor = mercadoCorRaridade(d.raridade || "comum");
            const isMeuAnuncio = String(anuncio.seller_id || "") === meuId;
            const refino = Number(d.refino || 0);
            const qtd = Number(anuncio.quantidade || 1);

            const card = document.createElement('div');
            card.className = 'mercado-card';
            card.dataset.busca = [anuncio.nome_item, anuncio.vendedor, anuncio.item_id].join(' ');
            card.style.cssText = `
                position:relative;
                background:linear-gradient(180deg, rgba(15,23,42,.96), rgba(2,6,23,.96));
                border:1px solid ${isMeuAnuncio ? '#facc15' : cor};
                border-radius:12px;
                padding:10px;
                display:flex;
                gap:10px;
                align-items:center;
                width:100%;
                box-sizing:border-box;
                margin-bottom:10px;
                box-shadow:0 6px 16px rgba(0,0,0,.45), inset 0 0 14px rgba(0,0,0,.35);
                cursor:pointer;
            `;

            card.onclick = () => abrirDetalhesMercado(anuncio.id_venda);

            card.innerHTML = `
                <div style="
                    width:52px;
                    height:52px;
                    flex:0 0 52px;
                    background:#020617;
                    border:2px solid ${cor};
                    border-radius:10px;
                    display:flex;
                    align-items:center;
                    justify-content:center;
                    box-shadow:inset 0 0 14px rgba(0,0,0,.8), 0 0 10px ${cor}55;
                ">
                    <img data-img-card-mercado="1" src="/static/assets/box.png" style="max-width:42px; max-height:42px; object-fit:contain;">
                </div>

                <div style="flex:1; min-width:0;">
                    <div style="
                        color:#f8fafc;
                        font-family:'Cinzel',serif;
                        font-weight:900;
                        font-size:.92em;
                        line-height:1.2;
                        white-space:nowrap;
                        overflow:hidden;
                        text-overflow:ellipsis;
                    ">
                        ${mercadoHtml(d.nome || anuncio.nome_item)}
                        ${refino > 0 ? `<span style="color:#facc15;"> +${refino}</span>` : ""}
                    </div>

                    <div style="
                        margin-top:2px;
                        color:${cor};
                        font-size:.68em;
                        font-weight:900;
                        text-transform:uppercase;
                    ">
                        ${mercadoHtml(d.raridade || "comum")}
                    </div>

                    <div style="
                        margin-top:5px;
                        display:flex;
                        gap:5px;
                        flex-wrap:wrap;
                        font-size:.7em;
                        color:#94a3b8;
                    ">
                        <span style="background:#020617; border:1px solid #334155; border-radius:6px; padding:2px 5px;">
                            Qtd ${qtd}
                        </span>
                        <span style="background:#020617; border:1px solid #334155; border-radius:6px; padding:2px 5px;">
                            ${isMeuAnuncio ? "Seu anúncio" : "Vendedor: " + mercadoHtml(anuncio.vendedor)}
                        </span>
                    </div>
                </div>

                <div style="
                    display:flex;
                    flex-direction:column;
                    align-items:flex-end;
                    gap:6px;
                    flex:0 0 auto;
                ">
                    <div style="
                        color:${anuncio.moeda === 'ouro' ? '#facc15' : '#60a5fa'};
                        background:rgba(0,0,0,.45);
                        border:1px solid ${anuncio.moeda === 'ouro' ? '#ca8a04' : '#3b82f6'};
                        border-radius:8px;
                        padding:5px 8px;
                        font-weight:900;
                        font-size:.88em;
                        white-space:nowrap;
                    ">
                        ${anuncio.preco} ${simbolo}
                    </div>

                    <button style="
                        background:${isMeuAnuncio ? 'linear-gradient(180deg, #ef4444, #991b1b)' : 'linear-gradient(180deg, #334155, #1e293b)'};
                        color:white;
                        border:1px solid ${isMeuAnuncio ? '#f87171' : '#475569'};
                        padding:5px 8px;
                        border-radius:7px;
                        font-size:.72em;
                        font-weight:900;
                        cursor:pointer;
                    ">
                        ${isMeuAnuncio ? 'Cancelar' : 'Detalhes'}
                    </button>
                </div>
            `;

            const btn = card.querySelector('button');
            btn.onclick = (ev) => {
                ev.stopPropagation();

                if (isMeuAnuncio) {
                    cancelarVendaMercado(anuncio.id_venda);
                } else {
                    abrirDetalhesMercado(anuncio.id_venda);
                }
            };

            mercadoAplicarImagem(card.querySelector('[data-img-card-mercado="1"]'), itemLike);

            return card;
        }

        if (!data.ouro || data.ouro.length === 0) {
            listaOuro.innerHTML = '<p style="text-align:center; color:#64748b;">Nenhum item à venda por ouro.</p>';
        } else {
            data.ouro.forEach(a => listaOuro.appendChild(criarCard(a, '🪙')));
        }

        if (!data.gemas || data.gemas.length === 0) {
            listaGemas.innerHTML = '<p style="text-align:center; color:#64748b;">Nenhum item à venda por gemas.</p>';
        } else {
            data.gemas.forEach(a => listaGemas.appendChild(criarCard(a, '💎')));
        }

        filtrarMercado();
    } catch(e) {
        console.error(e);
        if (window.alertaEldora) window.alertaEldora("Mercado", "Falha ao carregar a vitrine.", "erro");
    }
}

async function confirmarVenda() {
    if (window.__mercadoVendendo) return;
    const btnContrato = document.querySelector('#aba-vender button[onclick="confirmarVenda()"]');

    let itemSelecionado = document.getElementById('select-item-venda')?.value;
    let preco = mercadoInteiroPositivo(document.getElementById('input-preco')?.value);
    let moeda = document.getElementById('select-moeda')?.value || "ouro";
    let qtd = mercadoInteiroPositivo(document.getElementById('input-qtd')?.value);

    if (!itemSelecionado || !preco || preco <= 0 || !qtd || qtd <= 0) {
        if (window.alertaEldora) {
            window.alertaEldora("Atenção", "Preencha a quantidade e um preço válido!", "erro");
        }
        return;
    }

    const limite = Number(document.getElementById('input-qtd').max);
    if (limite > 0 && qtd > limite) {
        window.alertaEldora?.('Quantidade inválida', `Você possui apenas ${limite} unidades desse item.`, 'erro');
        return;
    }
    window.__mercadoVendendo = true;
    if (btnContrato) {
        btnContrato.disabled = true;
        btnContrato.style.opacity = "0.6";
        btnContrato.innerText = "Publicando…";
    }

    const charId = localStorage.getItem("jogadorEldoraID");

    try {
        const res = await fetch('/api/mercado/criar_anuncio', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                user_id: charId,
                item_id: itemSelecionado,
                preco: preco,
                moeda: moeda,
                quantidade: qtd
            })
        });

        const textoBruto = await res.text();

        let data = null;
        try {
            data = JSON.parse(textoBruto);
        } catch (e) {
            console.error("[MERCADO criar_anuncio] Resposta não JSON:", {
                status: res.status,
                resposta: textoBruto
            });

            throw new Error(
                `Servidor respondeu erro ${res.status}. Veja o console F12 para o detalhe.`
            );
        }

        console.log("[MERCADO criar_anuncio] resposta:", data);

        if (!res.ok || !data.sucesso) {
            const msgErro = data.erro || data.error || data.message || "Erro ao anunciar item.";
            if (window.alertaEldora) {
                window.alertaEldora("Aviso", msgErro, "erro");
            }
            return;
        }

        if (window.alertaEldora) {
            window.alertaEldora("Sucesso", data.mensagem || "Item anunciado! O Rei agradece os 10%.", "sucesso");
        }

        document.getElementById('input-preco').value = "";
        document.getElementById('input-qtd').value = "1";
        document.getElementById('select-item-venda').value = "";

        const preview = document.getElementById("preview-item-venda-mercado");
        if (preview) preview.style.display = "none";

        calcularTaxaReino();

        if (typeof carregarVitrineMercado === 'function') {
            await carregarVitrineMercado();
        }

        if (typeof window.carregarMeuPerfil === 'function') {
            await window.carregarMeuPerfil();
        }

        if (typeof carregarInventarioNoMercado === 'function') {
            carregarInventarioNoMercado();
        }

    } catch (e) {
        console.error("Falha real ao anunciar:", e);

        if (window.alertaEldora) {
            window.alertaEldora("Erro", e.message || "Falha ao anunciar item.", "erro");
        }
    } finally {
        window.__mercadoVendendo = false;
        if (btnContrato) {
            btnContrato.disabled = false;
            btnContrato.style.opacity = "1";
            btnContrato.innerText = "Publicar anúncio →";
        }
    }
}

// 🔥 EFETUA A COMPRA DO ITEM 🔥
async function comprarItemMercado(idVenda, moeda) {
    if (mercadoOperacoesPendentes.has(idVenda)) return;
    // 1. Confirmação de segurança para evitar clique acidental
    let nomeMoeda = moeda === 'ouro' ? 'Ouro 🪙' : 'Gemas 💎';
    if (!await window.confirmarEldora(`O Rei exige certeza absoluta! Deseja comprar este item com ${nomeMoeda}?`)) {
        return;
    }

    mercadoOperacoesPendentes.add(idVenda);
    let charId = localStorage.getItem("jogadorEldoraID");

    try {
        const res = await fetch('/api/mercado/comprar', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                user_id: charId, 
                id_venda: idVenda 
            })
        });
        
        const data = await res.json();
        
        if (data.sucesso) {
            // Avisa que deu certo!
            if (window.alertaEldora) {
                window.alertaEldora("Transação Concluída", data.mensagem, "sucesso");
            } else {
                window.avisoEldora(data.mensagem);
            }
            
            // Toca um som de moedas (opcional)
            if (typeof window.AudioManager !== 'undefined') {
                window.AudioManager.tocarSFX('som_compra_item'); // Ajuste para o seu som de ouro
            }
            
            // 2. Atualiza a tela (O item some da loja na hora)
            carregarVitrineMercado(); 
            
            // 3. Atualiza o perfil do jogador para ele ver o dinheiro sumindo e o item aparecendo!
            if (typeof window.carregarMeuPerfil === 'function') {
                window.carregarMeuPerfil();
            }
        } else {
            // Se o cara não tiver dinheiro, avisa!
            if (window.alertaEldora) {
                window.alertaEldora("Aviso Real", data.erro, "erro");
            } else {
                window.avisoEldora("Erro: " + data.erro);
            }
        }
    } catch(e) {
        console.error("Falha ao processar compra:", e);
    } finally {
        mercadoOperacoesPendentes.delete(idVenda);
    }
}

// 🔥 EFETUA O CANCELAMENTO DO ITEM 🔥
async function cancelarVendaMercado(idVenda) {
    if (mercadoOperacoesPendentes.has(idVenda)) return;
    // 1. Confirmação de segurança para não cancelar sem querer
    if (!await window.confirmarEldora("O Rei devolverá este item para a sua mochila. Deseja confirmar o cancelamento?")) {
        return;
    }

    mercadoOperacoesPendentes.add(idVenda);
    let charId = localStorage.getItem("jogadorEldoraID");

    try {
        const res = await fetch('/api/mercado/cancelar', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                user_id: charId, 
                id_venda: idVenda 
            })
        });
        
        const data = await res.json();
        
        if (data.sucesso) {
            if (window.alertaEldora) {
                window.alertaEldora("Sucesso", "Anúncio cancelado! O item voltou para a sua mochila.", "sucesso");
            } else {
                window.avisoEldora("Anúncio cancelado! O item voltou para a sua mochila.");
            }
            
            // 2. Atualiza a tela (O item some da loja na hora)
            carregarVitrineMercado(); 
            
            // 3. Atualiza o perfil e a aba de venda para o item reaparecer
            if (typeof window.carregarMeuPerfil === 'function') {
                await window.carregarMeuPerfil();
            }
            carregarInventarioNoMercado();
            
        } else {
            if (window.alertaEldora) {
                window.alertaEldora("Aviso Real", data.erro, "erro");
            } else {
                window.avisoEldora("Erro: " + data.erro);
            }
        }
    } catch(e) {
        console.error("Falha ao processar o cancelamento:", e);
    } finally {
        mercadoOperacoesPendentes.delete(idVenda);
    }
}
