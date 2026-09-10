// ============================================================
// 🏰 MUNDO DE ELDORA - GUILDA DOS AVENTUREIROS
// ============================================================

(() => {

    const estadoGuilda = {

        dados: null,

        // individual = contratos do personagem
        // coletivo   = contratos pertencentes ao clã
        escopo: "individual",

        aba: "disponiveis",

        filtro: "todos",

        carregando: false,

        // "atendente" = dentro da Guilda com Lyria
        // "diario" = botão permanente do HUD
        modo: "atendente"
    };


    // ========================================================
    // 🔧 HELPERS
    // ========================================================

    function escaparHTML(valor) {
        return String(valor ?? "")
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }


    function obterUserId() {
        return localStorage.getItem(
            "jogadorEldoraID"
        );
    }


    function falarLyria(texto) {
        const el = document.getElementById(
            "guild-dialogo-texto"
        );

        if (el) {
            el.innerText = texto;
        }
    }


    function bloquearMenuGlobal() {
        if (
            typeof window.ocultarMenuGlobalEldora
            === "function"
        ) {
            window.ocultarMenuGlobalEldora();
        } else {
            document.body.classList.add(
                "ui-modal-aberta"
            );
        }
    }


    function liberarMenuGlobal() {
        if (
            typeof window.mostrarMenuGlobalEldora
            === "function"
        ) {
            window.mostrarMenuGlobalEldora();
        } else {
            document.body.classList.remove(
                "ui-modal-aberta"
            );
        }
    }


    function mostrarErro(mensagem) {

        falarLyria(
            mensagem ||
            "Algo deu errado. Tente novamente."
        );

        if (
            typeof window.alertaEldora
            === "function"
        ) {
            window.alertaEldora(
                "Guilda dos Aventureiros",
                mensagem ||
                "Ocorreu um erro.",
                "erro"
            );
        }
    }


    // ========================================================
    // 🚪 ABRIR / FECHAR
    // ========================================================

    window.abrirGuildaMissoes = async function() {

        estadoGuilda.modo = "atendente";
        estadoGuilda.escopo = "individual";
        
        const container = document.getElementById(
            "guild-missions-container"
        );

        if (!container) {
            console.error(
                "guild-missions-container não encontrado."
            );
            return;
        }

        bloquearMenuGlobal();

        container.style.display = "flex";

        estadoGuilda.aba = "disponiveis";
        estadoGuilda.filtro = "todos";

        atualizarAbas();
        atualizarFiltros();
        atualizarEscopoGuilda();

        configurarModoInterface();

        falarLyria(
            "Saudações, aventureiro. Estou verificando os contratos disponíveis."
        );

        
        await carregarGuildaMissoes();
    };
    
    // ========================================================
    // 📜 DIÁRIO DE MISSÕES DA GUILDA
    // ========================================================

    window.abrirDiarioGuilda = async function() {

        const container =
            document.getElementById(
                "guild-missions-container"
            );

        if (!container) {
            console.error(
                "guild-missions-container não encontrado."
            );
            return;
        }

        estadoGuilda.modo = "diario";

        estadoGuilda.escopo = "individual";

        // Diário mostra somente o que foi aceito.
        estadoGuilda.aba = "ativas";

        estadoGuilda.filtro = "todos";

        bloquearMenuGlobal();

        container.style.display = "flex";

        configurarModoInterface();

        atualizarAbas();
        atualizarFiltros();
        atualizarEscopoGuilda();

        await carregarGuildaMissoes();
    };

    function configurarModoInterface() {

        const areaLyria =
            document.getElementById(
                "guild-atendente-area"
            );

        const titulo =
            document.getElementById(
                "guild-titulo-principal"
            );

        const pontos =
            document.getElementById(
                "guild-pontos-area"
            );

        const abas =
            document.getElementById(
                "guild-abas-area"
            );

        const escopoArea =
            document.getElementById(
                "guild-escopo-area"
            );

        // ==========================================
        // 👩 MODO LYRIA / GUILDA
        // ==========================================

        if (
            estadoGuilda.modo ===
            "atendente"
        ) {

            if (areaLyria) {
                areaLyria.style.display = "flex";
            }

            if (pontos) {
                pontos.style.display = "block";
            }

            if (abas) {
                abas.style.display = "grid";
            }

            if (titulo) {
                titulo.innerHTML =
                    "⚔️ GUILDA DOS AVENTUREIROS";
            } 
            
            if (escopoArea) {
                escopoArea.style.display = "grid";
            }
            
            return;
        }


        // ==========================================
        // 📜 MODO DIÁRIO
        // ==========================================

        if (areaLyria) {
            areaLyria.style.display = "none";
        }
        
        if (escopoArea) {
            escopoArea.style.display = "none";
        }

        if (pontos) {
            pontos.style.display = "block";
        }

        // Não precisamos das abas no Diário.
        if (abas) {
            abas.style.display = "none";
        }

        if (titulo) {
            titulo.innerHTML =
                "📜 DIÁRIO DE MISSÕES DA GUILDA";
        }
    }

    window.fecharGuildaMissoes = function() {

        const container = document.getElementById(
            "guild-missions-container"
        );

        if (container) {
            container.style.display = "none";
        }

        liberarMenuGlobal();
    };


    // ========================================================
    // 📡 CARREGAR DADOS
    // ========================================================

    async function carregarGuildaMissoes() {

        if (estadoGuilda.carregando) {
            return;
        }

        const userId = obterUserId();

        if (!userId) {
            mostrarErro(
                "Não consegui identificar seu herói."
            );
            return;
        }

        estadoGuilda.carregando = true;

        const lista = document.getElementById(
            "guild-missoes-lista"
        );

        if (lista) {
            lista.innerHTML = `
                <div class="guild-carregando">
                    📜 Lyria está consultando os contratos...
                </div>
            `;
        }

        try {

            const endpoint =
                estadoGuilda.escopo ===
                    "coletivo"

                    ? (
                        "/api/guild/cla/missoes/"
                        +
                        encodeURIComponent(userId)
                    )

                    : (
                        "/api/guild/missoes/"
                        +
                        encodeURIComponent(userId)
                    );


            const resposta = await fetch(
                `${endpoint}?t=${Date.now()}`,
                {
                    method: "GET",
                    cache: "no-store"
                }
            );

            const dados =
                await resposta.json();

            if (!dados.success) {
                throw new Error(
                    dados.error ||
                    "Não foi possível carregar as missões."
                );
            }

            estadoGuilda.dados = dados;

            atualizarPontos();

            renderizarGuildaMissoes();

            atualizarFalaLyria();

        } catch (erro) {

            console.error(
                "❌ [GUILDA] Erro ao carregar:",
                erro
            );

            if (lista) {
                lista.innerHTML = `
                    <div class="guild-vazio">
                        ❌ ${escaparHTML(
                            erro.message ||
                            "Não foi possível consultar os contratos."
                        )}
                    </div>
                `;
            }

            falarLyria(
                erro.message ||
                "Parece que os registros da Guilda estão indisponíveis no momento."
            );

        } finally {
            estadoGuilda.carregando = false;
        }
    }


    window.recarregarGuildaMissoes =
        carregarGuildaMissoes;


    // ========================================================
    // 🗣️ FALA DINÂMICA DA LYRIA
    // ========================================================

    function atualizarFalaLyria() {

        const dados = estadoGuilda.dados;

        if (!dados) return;

        const ativas =
            dados.ativas || [];

        const prontas =
            ativas.filter(
                m =>
                    m.status ===
                    "pronta_entrega"
            );

        if (prontas.length > 0) {

            falarLyria(
                prontas.length === 1
                    ? "Excelente trabalho! Você concluiu um contrato. Posso registrar sua recompensa agora."
                    : `Excelente trabalho! Você possui ${prontas.length} contratos prontos para entrega.`
            );

            return;
        }

        if (ativas.length > 0) {

            falarLyria(
                "Seus contratos ainda estão em andamento. Volte quando tiver novidades."
            );

            return;
        }

        const disponiveis =
            dados.disponiveis || [];

        if (disponiveis.length > 0) {

            falarLyria(
                "Há novos contratos disponíveis. Escolha aquele que melhor combina com sua jornada."
            );

            return;
        }

        falarLyria(
            "No momento não tenho novos contratos para você."
        );
    }


    // ========================================================
    // 🏅 PONTOS
    // ========================================================

    function atualizarPontos() {

        const pontos =
            document.getElementById(
                "guild-pontos-total"
            );

        const label =
            document.getElementById(
                "guild-pontos-label"
            );

        if (!pontos) {
            return;
        }


        if (
            estadoGuilda.escopo ===
            "coletivo"
        ) {

            pontos.innerText =
                estadoGuilda.dados
                    ?.pontos_cla || 0;

            if (label) {
                label.innerText =
                    "Pontos do clã:";
            }

            return;
        }


        pontos.innerText =
            estadoGuilda.dados
                ?.pontos_guilda || 0;


        if (label) {
            label.innerText =
                "Pontos pessoais:";
        }
    }

     
    // ========================================================
    // 🏰 ESCOPO - PERSONAGEM / CLÃ
    // ========================================================

    window.mudarEscopoGuilda =
        async function(escopo) {
 
            if (
                ![
                    "individual",
                    "coletivo"
                ].includes(escopo)
            ) {
                return;
            }

            if (
                estadoGuilda.carregando
            ) {

                falarLyria(
                    "Um momento... ainda estou consultando os registros da Guilda."
                );

                return;
            }

            if (
                estadoGuilda.escopo === escopo
                &&
                estadoGuilda.dados
            ) {
                return;
            }

            estadoGuilda.escopo =
                escopo;

            // Não reutiliza dados do escopo anterior.
            estadoGuilda.dados =
                null;

            estadoGuilda.aba =
                "disponiveis";

            estadoGuilda.filtro =
                "todos";

            atualizarEscopoGuilda();
            atualizarAbas();
            atualizarFiltros();

            await carregarGuildaMissoes();
        };


    function atualizarEscopoGuilda() {

        const individual =
            document.getElementById(
                "guild-escopo-individual"
            );

        const coletivo =
            document.getElementById(
                "guild-escopo-coletivo"
            );

        const filtros =
            document.getElementById(
                "guild-filtros-area"
            );


        if (individual) {

            individual.classList.toggle(
                "ativa",
                estadoGuilda.escopo ===
                    "individual"
            );
        }


        if (coletivo) {

            coletivo.classList.toggle(
                "ativa",
                estadoGuilda.escopo ===
                    "coletivo"
            );
        }


        // Os filtros Pessoal / Clã fazem sentido
        // somente para os contratos individuais.
        //
        // Contratos coletivos já são sempre do clã.
        if (filtros) {

            filtros.style.display =
                estadoGuilda.escopo ===
                    "coletivo"
                    ? "none"
                    : "";
        }


        atualizarPontos();
    }
    // ========================================================
     // 📑 ABAS
    // ========================================================

    window.mudarAbaGuildaMissoes =
        function(aba) {

            if (
                ![
                    "disponiveis",
                    "ativas",
                    "concluidas"
                ].includes(aba)
            ) {
                return;
            }

            estadoGuilda.aba = aba;

            atualizarAbas();
            renderizarGuildaMissoes();
        };


    function atualizarAbas() {

        const mapa = {
            disponiveis:
                "guild-aba-disponiveis",

            ativas:
                "guild-aba-ativas",

            concluidas:
                "guild-aba-concluidas"
        };

        Object.entries(mapa)
            .forEach(
                ([aba, id]) => {

                    const btn =
                        document.getElementById(id);

                    if (!btn) return;

                    btn.classList.toggle(
                        "ativa",
                        aba === estadoGuilda.aba
                    );
                }
            );
    }


    // ========================================================
    // 🔍 FILTROS
    // ========================================================

    window.filtrarGuildaMissoes =
        function(filtro, botao) {

            if (
                ![
                    "todos",
                    "pessoal",
                    "cla"
                ].includes(filtro)
            ) {
                return;
            }

            estadoGuilda.filtro = filtro;

            document
                .querySelectorAll(
                    ".guild-filtro"
                )
                .forEach(
                    el =>
                        el.classList.remove(
                            "ativo"
                        )
                );

            if (botao) {
                botao.classList.add(
                    "ativo"
                );
            }

            renderizarGuildaMissoes();
        };


    function atualizarFiltros() {

        document
            .querySelectorAll(
                ".guild-filtro"
            )
            .forEach(
                botao => {

                    const filtro =
                        botao.dataset
                            .guildFiltro;

                    botao.classList.toggle(
                        "ativo",
                        filtro ===
                        estadoGuilda.filtro
                    );
                }
            );
    }


    // ========================================================
    // 📜 PEGAR LISTA DA ABA
    // ========================================================

    function obterListaAtual() {

        const dados =
            estadoGuilda.dados;

        if (!dados) {
            return [];
        }

        let lista = [];

        if (
            estadoGuilda.aba ===
            "disponiveis"
        ) {
            lista =
                dados.disponiveis || [];
        }

        else if (
            estadoGuilda.aba ===
            "ativas"
        ) {
            lista =
                dados.ativas || [];
        }

        else if (
            estadoGuilda.aba ===
            "concluidas"
        ) {
            lista =
                dados.concluidas || [];
        }

        if (
            estadoGuilda.escopo ===
                "individual"
            &&
            estadoGuilda.filtro !==
                "todos"
        ) {

            lista = lista.filter(
                missao =>
                    missao.tipo ===
                    estadoGuilda.filtro
            );
        }

        return lista;
    }


    // ========================================================
    // 🖼️ RENDER PRINCIPAL
    // ========================================================

    function renderizarGuildaMissoes() {

        const listaEl =
            document.getElementById(
                "guild-missoes-lista"
            );

        if (!listaEl) return;

        const lista =
            obterListaAtual();

        if (lista.length === 0) {

            let texto =
                "Nenhum contrato encontrado.";

            if (
                estadoGuilda.aba ===
                "ativas"
            ) {
                texto =
                    "Você não possui contratos em andamento.";
            }

            if (
                estadoGuilda.aba ===
                "concluidas"
            ) {
                texto =
                    "Seu histórico da Guilda ainda está vazio.";
            }

            listaEl.innerHTML = `
                <div class="guild-vazio">
                    ${texto}
                </div>
            `;

            return;
        }

        listaEl.innerHTML =
            lista
                .map(
                    criarHTMLMissao
                )
                .join("");
    }


    // ========================================================
    // 📜 CARTÃO
    // ========================================================
    function formatarNomeItemGuilda(item) {

        // ==========================================
        // 1. SE O BACKEND JÁ MANDAR O NOME BONITO
        // ==========================================

        const nomeOficial =
            item?.display_name ||
            item?.nome ||
            item?.name;

        if (nomeOficial) {
            return String(nomeOficial);
        }


        // ==========================================
        // 2. PEGA O ID INTERNO DO ITEM
        // ==========================================

        const id =
            item?.item_id ||
            item?.base_id ||
            item?.id ||
            "";


        if (!id) {
            return "Item";
        }


        // ==========================================
        // 3. TRANSFORMA:
        //
        // pedra_de_aprimoramento
        // ↓
        // Pedra de Aprimoramento
        // ==========================================

        const minusculas = [
            "de",
            "da",
            "do",
            "das",
            "dos",
            "e"
        ];


        return String(id)
 
            .replace(/_/g, " ")
 
            .trim()

            .split(/\s+/)

            .map(
                (palavra, indice) => {
 
                    const p =
                        palavra.toLowerCase();


                    if (
                        indice > 0 &&
                        minusculas.includes(p)
                    ) {
                        return p;
                    }


                    return (
                        p.charAt(0).toUpperCase()
                        +
                        p.slice(1)
                    );
                }
            )

            .join(" ");
    }

    function criarHTMLMissao(missao) {

        const tipo =
            missao.tipo || "pessoal";

        const modo =
            missao.modo || "solo";

        const coletiva =
            (
                missao.escopo ===
                    "coletivo"
                ||
                estadoGuilda.escopo ===
                    "coletivo"
            );


        const frequencia =
            missao.frequencia ||
                "unica";
        
        const podeGerenciarCla =
            estadoGuilda.escopo !==
                "coletivo"
            ||
            estadoGuilda.dados
                ?.pode_gerenciar === true;

        const pronta =
            missao.status ===
            "pronta_entrega";

        const progresso =
            Number(
                missao.progresso || 0
            );

        const total =
            Number(
                missao.progresso_total ||
                missao.objetivo?.quantidade ||
                1
            );

        const percentual =
            Math.max(
                0,
                Math.min(
                    100,
                    Math.round(
                        (
                            progresso /
                            Math.max(1, total)
                        ) * 100
                    )
                )
            );


        // ==========================================
        // TAGS
        // ==========================================

        const tipoTexto =
            coletiva
                ? "🏰 Coletiva"
                : (
                    tipo === "cla"
                        ? "🛡️ Clã"
                        : "👤 Pessoal"
                );


        let modoTexto = "⚔️ Solo";

        if (modo === "grupo") {
            modoTexto =
                "👥 Grupo";
        }

        else if (modo === "qualquer") {
            modoTexto =
                "⚔️ Solo ou Grupo";
        }


        const frequenciaTexto = {

            unica:
                "📜 Única",

            diaria:
                "☀️ Diária",

            semanal:
                "🌙 Semanal"

        }[frequencia] || "📜 Única";


        // ==========================================
        // RECOMPENSAS
        // ==========================================

        const recompensas =
            criarHTMLRecompensas(
                missao.recompensas || {}
            );


        // ==========================================
        // PROGRESSO
        // ==========================================

        let htmlProgresso = "";

        if (
            estadoGuilda.aba === "ativas"
        ) {

            htmlProgresso = `
                <div class="guild-progresso-area">

                    <div class="guild-progresso-info">
                        <span>
                            ${
                                coletiva
                                    ? "Progresso do Clã"
                                    : "Progresso"
                            }
                        </span>
                        
                        <strong>
                            ${progresso}/${total}
                        </strong>
                    </div>

                    <div class="guild-progresso-barra">

                        <div
                            class="guild-progresso-preenchimento"
                            style="width:${percentual}%"
                        ></div>

                    </div>

                </div>
            `;
        }
        
        // ==========================================
        // 🏆 CONTRIBUIÇÕES DO CLÃ
        // ==========================================

        let htmlRanking = "";

        const ranking =
            Array.isArray(missao.ranking)
                ? missao.ranking
                : [];


        if (
            coletiva
            &&
            ranking.length > 0
            &&
            estadoGuilda.aba === "ativas"
        ) {

            htmlRanking = `

                <div class="guild-recompensas">

                    <div class="guild-recompensas-titulo">
                        🏆 Contribuições
                    </div>

                    <div class="guild-recompensas-lista">

                        ${
                            ranking
                                .slice(0, 10)
                                .map(
                                    (
                                        membro,
                                        indice
                                    ) => `

                                        <span
                                            class="guild-recompensa"
                                        >

                                            ${indice + 1}º

                                            ${escaparHTML(
                                                membro.nome ||
                                                "Aventureiro"
                                            )}

                                            — ${Number(
                                                membro.quantidade ||
                                                0
                                            )}

                                        </span>
                                    `
                                )
                                .join("")
                        }

                    </div>

                </div>
            `;
        }

        // ==========================================
        // PRONTA PARA ENTREGA
        // ==========================================

        let htmlPronta = "";

        if (pronta) {

            htmlPronta = `
                <div class="guild-pronta-aviso">
                    ✅ Contrato concluído!
                    Fale com Lyria para receber
                    sua recompensa.
                </div>
            `;
        }


        // ==========================================
        // BLOQUEIO
        // ==========================================

        let htmlBloqueio = "";

        if (
            estadoGuilda.aba ===
            "disponiveis"
            &&
            missao.disponivel === false
        ) {

            htmlBloqueio = `
                <div class="guild-bloqueio">
                    🔒
                    ${escaparHTML(
                        missao.bloqueio ||
                        "Contrato bloqueado."
                    )}
                </div>
            `;
        }


        // ==========================================
        // BOTÃO
        // ==========================================

        let htmlBotao = "";

        const missaoId =
            escaparHTML(missao.id);


        if (
            estadoGuilda.aba ===
            "disponiveis"
        ) {

            if (
                missao.disponivel ===
                false
            ) {

                htmlBotao = `
                    <button
                        class="
                            guild-btn
                            guild-btn-bloqueado
                        "
                        disabled
                    >
                        BLOQUEADO
                    </button>
                `;

            }

            else if (
                coletiva
                &&
                !podeGerenciarCla
            ) {

                htmlBotao = `
                    <button
                        class="
                            guild-btn
                            guild-btn-bloqueado
                        "
                        disabled
                    >
                        👑 AGUARDANDO OFICIAL
                    </button>
                `;

            }

            else {

                htmlBotao = `
                    <button
                        class="
                            guild-btn
                            guild-btn-aceitar
                        "
                        onclick="
                            window.aceitarMissaoGuilda(
                                '${missaoId}',
                                this
                            )
                        "
                    >
                        📜 ACEITAR
                    </button>
                `;
            }
        }


        else if (
            estadoGuilda.aba ===
            "ativas"
        ) {

            if (pronta) {

                if (
                    coletiva
                    &&
                    !podeGerenciarCla
                ) {

                    htmlBotao = `
                        <button
                            class="
                                guild-btn
                                guild-btn-bloqueado
                            "
                            disabled
                        >
                            👑 AGUARDANDO ENTREGA
                        </button>
                    `;
                }


                else if (
                    estadoGuilda.modo ===
                    "atendente"
                ) {

                    htmlBotao = `
                        <button
                            class="
                                guild-btn
                                guild-btn-resgatar
                            "
                            onclick="
                                window.resgatarMissaoGuilda(
                                    '${missaoId}',
                                    this
                                )
                            "
                        >
                            🎁 RESGATAR
                        </button>
                    `;
                }


                else {

                    htmlBotao = `
                        <button
                            class="
                                guild-btn
                                guild-btn-bloqueado
                            "
                            disabled
                        >
                            🏰 VOLTE À GUILDA
                        </button>
                    `;
                }

            }

            else {

                htmlBotao = `
                    <button
                        class="
                            guild-btn
                            guild-btn-bloqueado
                        "
                        disabled
                    >
                        EM ANDAMENTO
                    </button>
                `;
            }
        }        


        // Histórico não precisa de botão.


        // ==========================================
        // RESULTADO
        // ==========================================

        return `
            <div
                class="
                    guild-card
                    ${
                        tipo === "cla"
                            ? "tipo-cla"
                            : ""
                    }
                    ${
                        pronta
                            ? "pronta-entrega"
                            : ""
                    }
                "
            >

                <div class="guild-card-topo">

                    <div>

                        <div class="guild-card-nome">
                            ${escaparHTML(
                                missao.nome ||
                                "Contrato"
                            )}
                        </div>

                        <div class="guild-card-regiao">
                            📍
                            ${escaparHTML(
                                missao.regiao_nome ||
                                missao.objetivo?.regiao ||
                                "Eldora"
                            )}
                        </div>

                    </div>

                </div>


                <div class="guild-tags">

                    <span
                        class="
                            guild-tag
                            ${
                                tipo === "cla"
                                    ? "guild-tag-cla"
                                    : "guild-tag-pessoal"
                            }
                        "
                    >
                        ${tipoTexto}
                    </span>


                    <span
                        class="
                            guild-tag
                            ${
                                modo === "grupo"
                                    ? "guild-tag-grupo"
                                    : "guild-tag-solo"
                            }
                        "
                    >
                        ${modoTexto}
                    </span>
                    
                    <span class="guild-tag">
                        ${frequenciaTexto}
                    </span>
                </div>


                <div class="guild-card-descricao">
                    ${escaparHTML(
                        missao.descricao || ""
                    )}
                </div>


                <div class="guild-objetivo">
                    🎯
                    ${escaparHTML(
                        missao.objetivo?.texto ||
                        "Complete o objetivo do contrato."
                    )}
                </div>


                ${htmlProgresso}

                ${htmlRanking}

                ${htmlPronta}

                ${htmlBloqueio}


                <div class="guild-recompensas">

                    <div class="guild-recompensas-titulo">
                        🎁 Recompensas
                    </div>

                    <div class="guild-recompensas-lista">
                        ${recompensas}
                    </div>

                </div>


                ${
                    htmlBotao
                        ? `
                            <div class="guild-card-acoes">
                                ${htmlBotao}
                            </div>
                        `
                        : ""
                }

            </div>
        `;
    }


    // ========================================================
    // 🎁 RECOMPENSAS
    // ========================================================

    function criarHTMLRecompensas(
        recompensas
    ) {

        const partes = [];

        const gold =
            Number(
                recompensas.gold || 0
            );

        const xp =
            Number(
                recompensas.xp || 0
            );
        
        const ouroCla =
            Number(
                recompensas.ouro_cla || 0
            );

        const pontosCla =
            Number(
                recompensas.pontos_cla || 0
            );

        const pontos =
            Number(
                recompensas
                    .pontos_guilda || 0
            );

        const xpCla =
            Number(
                recompensas.xp_cla || 0
            );


        if (gold > 0) {
            partes.push(
                `💰 ${gold} Ouro`
            );
        }

        if (xp > 0) {
            partes.push(
                `⭐ ${xp} XP`
            );
        }
     
        if (ouroCla > 0) {
            partes.push(
                `🏦 ${ouroCla} Ouro para o Tesouro`
            );
        }

        if (pontosCla > 0) {
            partes.push(
                `🏰 ${pontosCla} Pontos do Clã`
            );
        }

        if (pontos > 0) {
            partes.push(
                `🏅 ${pontos} Pontos`
            );
        }

        if (xpCla > 0) {
            partes.push(
                `🛡️ ${xpCla} XP do Clã`
            );
        }


        const itens =
            recompensas.itens || [];

    itens.forEach(
        item => {

            const nomeItem =
                formatarNomeItemGuilda(
                    item
                );


            const quantidade =
                Number(
                    item.quantidade ||
                    item.quantity ||
                    item.qtd ||
                    1
                );


            partes.push(
                `📦 ${
                    escaparHTML(
                        nomeItem
                    )
                } x${quantidade}`
            );
        }
    );


        if (partes.length === 0) {
            return `
                <span class="guild-recompensa">
                    Honra da Guilda
                </span>
            `;
        }

        return partes
            .map(
                texto => `
                    <span class="guild-recompensa">
                        ${texto}
                    </span>
                `
            )
            .join("");
    }


    // ========================================================
    // 📜 ACEITAR MISSÃO
    // ========================================================

    window.aceitarMissaoGuilda =
        async function(
            missaoId,
            botao
        ) {

            const userId =
                obterUserId();

            if (
                !userId ||
                !missaoId
            ) {
                return;
            }

            if (botao) {
                botao.disabled = true;
                botao.innerText =
                    "AGUARDE...";
            }

            if (
                estadoGuilda.escopo ===
                "coletivo"
            ) {

                falarLyria(
                    "Um momento... vou registrar este contrato para o seu clã."
                );

            } else {

                falarLyria(
                    "Um momento... vou registrar este contrato em seu nome."
                );
            }

            try {

                const endpoint =
                    estadoGuilda.escopo ===
                        "coletivo"

                        ? "/api/guild/cla/missoes/aceitar"

                        : "/api/guild/missoes/aceitar";


                const resposta =
                    await fetch(
                        endpoint,
                        
                        {
                            method: "POST",

                            headers: {
                                "Content-Type":
                                    "application/json"
                            },

                            body:
                                JSON.stringify({
                                    user_id:
                                        userId,

                                    missao_id:
                                        missaoId
                                })
                        }
                    );


                const resultado =
                    await resposta.json();


                if (!resultado.success) {

                    throw new Error(
                        resultado.error ||
                        "Não foi possível aceitar o contrato."
                    );
                }


                if (
                    estadoGuilda.escopo ===
                    "coletivo"
                ) {

                    falarLyria(
                        `Contrato coletivo registrado! "${resultado.missao?.nome || "Missão"}" agora está ativo para todo o clã.`
                    );

                } else {

                    falarLyria(
                        `Contrato registrado! "${resultado.missao?.nome || "Missão"}" agora está em seu diário.`
                    );
                }

                await carregarGuildaMissoes();


                // Vai automaticamente para
                // "Em andamento".
                estadoGuilda.aba =
                    "ativas";

                atualizarAbas();

                renderizarGuildaMissoes();


            } catch (erro) {

                console.error(
                    "❌ [GUILDA] Aceitar:",
                    erro
                );

                mostrarErro(
                    erro.message
                );

                if (botao) {
                    botao.disabled = false;
                    botao.innerText =
                        "📜 ACEITAR";
                }
            }
        };


    // ========================================================
    // 🎁 RESGATAR MISSÃO
    // ========================================================

    window.resgatarMissaoGuilda =
        async function(
            missaoId,
            botao
        ) {

            const userId =
                obterUserId();

            if (
                !userId ||
                !missaoId
            ) {
                return;
            }

            if (botao) {
                botao.disabled = true;
                botao.innerText =
                    "ENTREGANDO...";
            }


            falarLyria(
                "Excelente trabalho. Vou registrar sua conclusão e preparar sua recompensa."
            );


            try {

                const endpoint =
                    estadoGuilda.escopo ===
                        "coletivo"

                       ? "/api/guild/cla/missoes/resgatar"

                        : "/api/guild/missoes/resgatar";


                const resposta =
                    await fetch(
                        endpoint,
                        
                        {
                            method: "POST",

                            headers: {
                                "Content-Type":
                                    "application/json"
                            },

                            body:
                                JSON.stringify({
                                    user_id:
                                        userId,

                                    missao_id:
                                        missaoId
                                })
                        }
                    );


                const resultado =
                    await resposta.json();


                if (!resultado.success) {

                    throw new Error(
                        resultado.error ||
                        "Não foi possível entregar o contrato."
                    );
                }


                const r =
                    resultado.recompensas ||
                    {};


                let texto =
                    "Recompensa registrada!";


                if (
                    Number(r.gold || 0) > 0
                ) {
                    texto +=
                        ` +${r.gold} ouro.`;
                }


                if (
                    Number(r.xp || 0) > 0
                ) {
                    texto +=
                        ` +${r.xp} XP.`;
                }


                if (
                    Number(
                        r.pontos_guilda || 0
                    ) > 0
                ) {
                    texto +=
                        ` +${r.pontos_guilda} pontos da Guilda.`;
                }
                if (
                    Number(
                        r.xp_cla || 0
                    ) > 0
                ) {

                    texto +=
                        ` Seu clã recebeu +${r.xp_cla} XP.`;
                }


                if (
                    Number(
                        r.ouro_cla || 0
                    ) > 0
                ) {

                    texto +=
                        ` +${r.ouro_cla} ouro para o tesouro do clã.`;
                }


                if (
                    Number(
                        r.pontos_cla || 0
                    ) > 0
                ) {

                    texto +=
                        ` +${r.pontos_cla} pontos do clã.`;
                }

                falarLyria(texto);


                // Atualiza perfil/HUD se
                // a função existir.
                try {

                    if (
                        typeof window
                            .carregarMeuPerfil
                        === "function"
                    ) {
                        await window
                            .carregarMeuPerfil();
                    }

                } catch (e) {
                    console.warn(
                        "Perfil não atualizado:",
                        e
                    );
                }


                await carregarGuildaMissoes();


                // Depois da entrega mostra
                // o histórico.
                estadoGuilda.aba =
                    "concluidas";

                atualizarAbas();

                renderizarGuildaMissoes();


            } catch (erro) {

                console.error(
                    "❌ [GUILDA] Resgate:",
                    erro
                );

                mostrarErro(
                    erro.message
                );

                if (botao) {
                    botao.disabled = false;
                    botao.innerText =
                        "🎁 RESGATAR";
                }
            }
        };


    // ========================================================
    // 🧹 FECHA CLICANDO FORA DA JANELA
    // ========================================================

    document.addEventListener(
        "click",
        function(event) {

            const overlay =
                document.getElementById(
                    "guild-missions-container"
                );

            if (
                overlay &&
                overlay.style.display !==
                    "none" &&
                event.target === overlay
            ) {

                window
                    .fecharGuildaMissoes();
            }
        }
    );


    console.log(
        "🏰 Guilda dos Aventureiros carregada."
    );

})();