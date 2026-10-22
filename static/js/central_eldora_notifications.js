(() => {
    "use strict";

    const API = "/api/central-eldora/novidades";
    let novidadeAtual = null;

    function renderizar(novidades) {
        const aviso = document.getElementById("aviso-central-eldora");
        const botaoTaverna = document.getElementById("btn-chat-mapa");
        if (!aviso || !botaoTaverna) return;

        novidadeAtual = novidades[0] || null;
        aviso.hidden = !novidadeAtual;
        let badge = botaoTaverna.querySelector(".badge-central-eldora");
        if (novidadeAtual && !badge) {
            badge = document.createElement("span");
            badge.className = "badge-central-eldora";
            badge.textContent = "!";
            badge.setAttribute("aria-label", "Há uma novidade não vista na Central de Eldora");
            botaoTaverna.appendChild(badge);
            botaoTaverna.setAttribute("aria-label", "Abrir Taverna. Há novidades não vistas na Central de Eldora.");
            botaoTaverna.title = "Há uma novidade na Central de Eldora";
        } else if (!novidadeAtual && badge) {
            badge.remove();
            botaoTaverna.removeAttribute("aria-label");
            botaoTaverna.removeAttribute("title");
        }

        if (novidadeAtual) {
            document.getElementById("aviso-central-titulo").textContent = novidadeAtual.titulo;
            document.getElementById("aviso-central-mensagem").textContent = novidadeAtual.mensagem;
        }
    }

    async function carregarNovidades() {
        if (!window.eldoraCharacterId) return;
        try {
            const resposta = await fetch(`${API}?t=${Date.now()}`, { cache: "no-store" });
            if (!resposta.ok) return;
            const dados = await resposta.json();
            renderizar(Array.isArray(dados.novidades) ? dados.novidades : []);
        } catch (erro) {
            console.warn("Não foi possível carregar as novidades da Central.", erro);
        }
    }

    window.carregarNovidadesCentralEldora = carregarNovidades;

    async function abrirNovidade() {
        if (!novidadeAtual) return;
        const botao = document.getElementById("aviso-central-abrir");
        if (botao) botao.disabled = true;
        try {
            const headers = await (window.portalSessionHeaders
                ? window.portalSessionHeaders({ "Content-Type": "application/json" })
                : { "Content-Type": "application/json" });
            const resposta = await fetch(`${API}/lida`, {
                method: "POST",
                headers,
                body: JSON.stringify({ id: novidadeAtual.id }),
            });
            if (!resposta.ok) throw new Error("Não foi possível registrar a leitura.");

            const aba = novidadeAtual.aba || "atualizacoes";
            await carregarNovidades();
            const taverna = document.getElementById("hub-social");
            if (taverna) taverna.style.display = "none";
            document.querySelectorAll(".btn-passe-mapa, .btn-social-mapa").forEach((el) => { el.style.display = "flex"; });
            if (typeof window.abrirCentralEldora === "function") window.abrirCentralEldora(aba);
        } catch (erro) {
            console.error("Falha ao abrir a novidade da Central:", erro);
        } finally {
            if (botao) botao.disabled = false;
        }
    }

    document.addEventListener("DOMContentLoaded", () => {
        const botao = document.getElementById("aviso-central-abrir");
        if (botao) botao.addEventListener("click", abrirNovidade);
        Promise.resolve(window.portalSessionReady).then(() => {
            if (window.eldoraCharacterId) carregarNovidades();
        });
        window.setInterval(() => {
            if (window.eldoraCharacterId && document.visibilityState === "visible") carregarNovidades();
        }, 120000);
    });
})();
