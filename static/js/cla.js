// ============================================================
// 🛡️ MUNDO DE ELDORA - INTERFACE DOS CLÃS
// ============================================================

(function () {
    "use strict";

    const estadoCla = {
        userId: null,
        clan: null,
        meuCargo: null,
        carregando: false,
        custoCriacaoOuro: 5000,

        cargos: [],
        permissoesCatalogo: [],
        minhasPermissoes: {},

        podeEditarEstrutura: false,

        limiteCargosPersonalizados: 0,
        cargosPersonalizadosTotal: 0,

        logos: [],
        logoSelecionada: null
    };

    // ========================================================
    // 🔧 HELPERS
    // ========================================================

    function elemento(id) {
        return document.getElementById(id);
    }


    function obterUserId() {
        const userId = localStorage.getItem(
            "jogadorEldoraID"
        );

        if (
            !userId ||
            userId === "null" ||
            userId === "undefined"
        ) {
            return null;
        }

        return userId;
    }


    function escaparHtml(valor) {
        return String(valor ?? "")
            .replaceAll("&", "&amp;")
            .replaceAll("<", "&lt;")
            .replaceAll(">", "&gt;")
            .replaceAll('"', "&quot;")
            .replaceAll("'", "&#039;");
    }


    function formatarNumero(valor) {
        return Number(valor || 0)
            .toLocaleString("pt-BR");
    }


    function obterConfigCargo(cargoId) {
        const id = String(
            cargoId || ""
        ).trim();

        if (!id) {
            return null;
        }

        return (
            estadoCla.cargos.find(
                function (cargo) {
                    return (
                        String(cargo.id) === id
                    );
                }
            ) || null
        );
    }


    function traduzirCargo(cargoId) {
        const configuracao =
            obterConfigCargo(
                cargoId
            );

        if (
            configuracao &&
            configuracao.nome
        ) {
            return String(
                configuracao.nome
            );
        }

        /*
         * Fallback para compatibilidade caso
         * a API de cargos ainda esteja carregando.
         */
        const nomesPadrao = {
            lider: "Líder",
            vice_lider: "Vice-líder",
            oficial: "Oficial",
            membro: "Membro"
        };

        if (nomesPadrao[cargoId]) {
            return nomesPadrao[cargoId];
        }

        const texto = String(
            cargoId || ""
        )
            .replaceAll("_", " ")
            .trim();

        if (!texto) {
            return "Membro";
        }

        return texto.replace(
            /\b\w/g,
            function (letra) {
                return letra.toUpperCase();
            }
        );
    }


    function hierarquiaCargo(cargoId) {
        const configuracao =
            obterConfigCargo(
                cargoId
            );

        if (configuracao) {
            return Number(
                configuracao.ordem || 0
            );
        }

        /*
         * Fallback com as mesmas ordens
         * utilizadas pelo backend.
         */
        const hierarquiaPadrao = {
            lider: 100,
            vice_lider: 90,
            oficial: 70,
            membro: 10
        };

        return Number(
            hierarquiaPadrao[cargoId] || 0
        );
    }


    function temPermissaoCla(permissao) {
        return Boolean(
            estadoCla.minhasPermissoes &&
            estadoCla.minhasPermissoes[
                permissao
            ]
        );
    }


    function souLiderReal() {
        return (
            String(
                estadoCla.clan?.lider_id || ""
            ) ===
            String(
                estadoCla.userId || ""
            )
        );
    }


    function podeExpulsarMembro(
        cargoAutor,
        cargoAlvo
    ) {
        if (
            !temPermissaoCla(
                "expulsar"
            )
        ) {
            return false;
        }

        return (
            hierarquiaCargo(
                cargoAutor
            ) >
            hierarquiaCargo(
                cargoAlvo
            )
        );
    }

    function podeAlterarCargoMembro(
        cargoAlvo,
        souEu
    ) {
        if (souEu) {
            return false;
        }


        if (
            String(cargoAlvo) ===
            "lider"
        ) {
            return false;
        }


        if (
            !temPermissaoCla(
                "gerenciar_cargos"
            )
        ) {
            return false;
        }


        /*
         * O verdadeiro líder pode administrar
         * qualquer membro que não seja ele mesmo.
         */
        if (souLiderReal()) {
            return true;
        }


        /*
         * Administradores delegados só podem
         * alterar membros abaixo deles.
         */
        return (
            hierarquiaCargo(
                estadoCla.meuCargo
            )
            >
            hierarquiaCargo(
                cargoAlvo
            )
        );
    }

    function cargosDisponiveisParaAtribuir() {
        const cargos = Array.isArray(
            estadoCla.cargos
        )
            ? [...estadoCla.cargos]
            : [];

        const ehLider =
            souLiderReal();

        const ordemAutor =
            hierarquiaCargo(
                estadoCla.meuCargo
            );


        return cargos
            .filter(
                function (cargo) {
                    const cargoId = String(
                        cargo?.id || ""
                    );

                    /*
                     * Liderança só pode ser transferida
                     * pelo botão especial.
                     */
                    if (
                        cargoId ===
                        "lider"
                    ) {
                        return false;
                    }

                    /*
                     * O líder pode conceder qualquer
                     * cargo abaixo de Líder.
                     */
                    if (ehLider) {
                        return true;
                    }

                    /*
                     * Administradores delegados nunca
                     * concedem cargo igual ou superior
                     * ao próprio.
                     */
                    return (
                        Number(
                            cargo?.ordem || 0
                        )
                        <
                        ordemAutor
                    );
                }
            )
            .sort(
                function (a, b) {
                    const ordemA = Number(
                        a?.ordem || 0
                    );

                    const ordemB = Number(
                        b?.ordem || 0
                    );

 
                    if (
                        ordemA !== ordemB
                    ) {
                        return (
                            ordemB -
                            ordemA
                        );
                    }


                    return String(
                        a?.nome || ""
                    ).localeCompare(
                        String(
                            b?.nome || ""
                        ),
                        "pt-BR"
                    );
                }
            );
    }


    function montarOpcoesCargoMembro(
        cargoAtual
    ) {
        return (
            cargosDisponiveisParaAtribuir()
                .map(
                    function (cargo) {
                        const cargoId =
                            String(
                                cargo.id ||
                                ""
                            );

                        const selecionado =
                            cargoId ===
                            String(
                                cargoAtual ||
                                ""
                            );


                        return `
                            <option
                                value="${
                                    escaparHtml(
                                        cargoId
                                    )
                                }"
                                ${
                                    selecionado
                                        ? "selected"
                                        : ""
                                }
                            >
                                ${
                                    escaparHtml(
                                        cargo.nome ||
                                        traduzirCargo(
                                            cargoId
                                        )
                                    )
                                }
                            </option>
                        `;
                    }
                )
                .join("")
        );
    }

    function mostrarAreaSemClan(areaId) {
        const areas = [
            "cla-area-criacao",
            "cla-area-lista-publica",
            "cla-area-convites"
        ];

        areas.forEach(function (id) {
            const area = elemento(id);

            if (!area) {
                return;
            }

            area.style.display =
                id === areaId
                    ? "block"
                    : "none";
        });
    }

    function formatarData(dataIso) {
        if (!dataIso) {
            return "Data desconhecida";
        }

        const data = new Date(dataIso);

        if (Number.isNaN(data.getTime())) {
            return "Data desconhecida";
        }

        return data.toLocaleDateString(
            "pt-BR",
            {
                day: "2-digit",
                month: "2-digit",
                year: "numeric"
            }
        );
    }

    function traduzirTipoEntrada(tipoEntrada) {
        const nomes = {
            solicitacao: "Aceitar solicitações",
            convite: "Somente por convite",
            fechado: "Recrutamento fechado"
        };

        return nomes[tipoEntrada] || nomes.convite;
    }


    function atualizarExplicacaoRecrutamento(
        tipoEntrada
    ) {
        const explicacao = elemento(
            "cla-config-explicacao-entrada"
        );

        if (!explicacao) {
            return;
        }

        const textos = {
            solicitacao:
                "Jogadores poderão enviar pedidos de entrada. Membros com permissão de recrutamento poderão aceitar ou recusar.",

            convite:
                "Somente jogadores convidados por membros autorizados do clã poderão entrar.",

            fechado:
                "Nenhum convite ou solicitação será aceito enquanto o recrutamento estiver fechado."
        };

        explicacao.textContent =
            textos[tipoEntrada] ||
            textos.convite;
    }


    function formatarDataHora(dataIso) {
        if (!dataIso) {
            return "";
        }

        const data = new Date(dataIso);

        if (Number.isNaN(data.getTime())) {
            return "";
        }

        return data.toLocaleString(
            "pt-BR",
            {
                day: "2-digit",
                month: "2-digit",
                year: "numeric",
                hour: "2-digit",
                minute: "2-digit"
            }
        );
    }


    function iconeAtividade(tipo) {
        const icones = {
            criacao: "🏰",
            entrada: "👤",
            saida: "🚪",
            expulsao: "🚫",
            cargo: "🎖️",
            lideranca: "👑",
            doacao: "🪙",
            tesouro: "💰",
            evolucao: "⭐",
            logo: "🎨",
            configuracao: "⚙️"
        };

        return icones[tipo] || "📜";
    }


    function renderizarAtividades(atividades) {
        const lista = elemento(
            "cla-lista-atividades"
        );

        if (!lista) {
            return;
        }

        if (
            !Array.isArray(atividades) ||
            !atividades.length
        ) {
            lista.innerHTML = `
                <div class="cla-vazio">
                    Nenhuma atividade registrada.
                </div>
            `;

            return;
        }

        lista.innerHTML = atividades
            .slice(0, 50)
            .map(function (atividade) {
                const tipo = String(
                    atividade.tipo || "geral"
                );

                const mensagem = escaparHtml(
                    atividade.mensagem ||
                    "Uma atividade foi registrada."
                );

                const autor = escaparHtml(
                    atividade.autor_nome ||
                    "Sistema"
                );

                const data = escaparHtml(
                    formatarDataHora(
                        atividade.criado_em
                    )
                );

                return `
                    <div class="cla-item-lista">
                        <div style="
                            display: grid;
                            grid-template-columns:
                                42px minmax(0, 1fr);
                            gap: 11px;
                            align-items: center;
                        ">
                            <div style="
                                width: 42px;
                                height: 42px;
                                display: flex;
                                align-items: center;
                                justify-content: center;
                                border-radius: 12px;
                                border:
                                    1px solid rgba(
                                        216,
                                        184,
                                        90,
                                        0.25
                                    );
                                background:
                                    rgba(
                                        216,
                                        184,
                                        90,
                                        0.08
                                    );
                                font-size: 20px;
                            ">
                                ${iconeAtividade(tipo)}
                            </div>

                            <div style="min-width: 0;">
                                <div style="
                                    color: #e7edf5;
                                    font-size: 0.80rem;
                                    font-weight: 700;
                                    line-height: 1.4;
                                ">
                                    ${mensagem}
                                </div>

                                <div style="
                                    margin-top: 4px;
                                    color: #7f8da0;
                                    font-size: 0.68rem;
                                ">
                                    ${
                                        autor !== "Sistema"
                                            ? `Por ${autor} · `
                                            : ""
                                    }
                                    ${data}
                                </div>
                            </div>
                        </div>
                    </div>
                `;
            })
            .join("");
    }

    function mostrarMensagem(
        texto,
        tipo = "sucesso"
    ) {
        const caixa = elemento("cla-mensagem");

        if (!caixa) {
            return;
        }

        caixa.style.display = "block";
        caixa.textContent = texto;

        if (tipo === "erro") {
            caixa.style.background =
                "rgba(127, 29, 29, 0.92)";
            caixa.style.border =
                "1px solid #ef4444";
            caixa.style.color = "#fee2e2";
        } else {
            caixa.style.background =
                "rgba(20, 83, 45, 0.92)";
            caixa.style.border =
                "1px solid #22c55e";
            caixa.style.color = "#dcfce7";
        }

        clearTimeout(
            window.__claMensagemTimer
        );

        window.__claMensagemTimer = setTimeout(
            function () {
                caixa.style.display = "none";
            },
            5000
        );
    }
    
    function confirmarAcaoCla({
        titulo = "Confirmar ação",
        mensagem = "Deseja continuar?",
        confirmarTexto = "Confirmar",
        cancelarTexto = "Cancelar",
        icone = "⚠️",
        perigo = false
    } = {}) {
        return new Promise(
            function (resolve) {
                const anterior = elemento(
                    "cla-confirmacao-overlay"
                );

                if (anterior) {
                    anterior.remove();
                }


                const overlay =
                    document.createElement(
                        "div"
                    );

                overlay.id =
                    "cla-confirmacao-overlay";


                const tituloSeguro =
                    escaparHtml(titulo);
 
                const mensagemSegura =
                    escaparHtml(mensagem);
 
                const confirmarSeguro =
                    escaparHtml(
                        confirmarTexto
                    );

                const cancelarSeguro =
                    escaparHtml(
                        cancelarTexto
                    );

                const iconeSeguro =
                    escaparHtml(icone);


                const fundoConfirmar =
                    perigo
                        ? `
                            linear-gradient(
                                180deg,
                                #b91c1c,
                                #7f1d1d
                            )
                        `
                        : `
                            linear-gradient(
                                180deg,
                                #9a741c,
                                #6f5014
                            )
                        `;


                const bordaConfirmar =
                    perigo
                        ? "rgba(248, 113, 113, 0.65)"
                        : "rgba(244, 220, 145, 0.65)";


                overlay.innerHTML = `
                    <div
                        role="dialog"
                        aria-modal="true"
                        aria-labelledby="cla-confirmacao-titulo"
                        style="
                            width:
                                min(
                                    360px,
                                    calc(
                                        100vw - 32px
                                    )
                                );

                            padding: 18px;

                            background:
                                linear-gradient(
                                    145deg,
                                    #182235,
                                    #0d1421
                                );

                            border:
                                1px solid
                                rgba(
                                    216,
                                    184,
                                    90,
                                    0.48
                                );

                            border-radius: 18px;

                            box-shadow:
                                0 25px 70px
                                rgba(
                                    0,
                                    0,
                                    0,
                                    0.72
                                );

                            color: #f4f7fb;
                        "
                    >
                        <div style="
                            width: 48px;
                            height: 48px;

                            display: flex;
                            align-items: center;
                            justify-content: center;

                            margin:
                                0 auto 12px;

                            border:
                                1px solid
                                rgba(
                                    216,
                                    184,
                                    90,
                                    0.30
                                );

                            border-radius: 14px;

                            background:
                                rgba(
                                    216,
                                    184,
                                    90,
                                    0.10
                                );

                            font-size: 23px;
                        ">
                            ${iconeSeguro}
                        </div>

 
                        <h3
                            id="cla-confirmacao-titulo"
                            style="
                                margin:
                                    0 0 8px;

                                color: #f4dc91;
    
                                font-family:
                                    Cinzel,
                                    serif;

                                font-size:
                                    1rem;

                                text-align:
                                    center;
                            "
                        >
                            ${tituloSeguro}
                        </h3>


                        <div style="
                            color: #c5ceda;
  
                            font-size:
                                0.84rem;
  
                            line-height:
                                1.5;
 
                            text-align:
                                center;
                        ">
                            ${mensagemSegura}
                        </div>


                        <div style="
                            display: grid;
    
                            grid-template-columns:
                                1fr 1fr;

                            gap: 9px;
  
                            margin-top:
                                18px;
                        ">
                            <button
                                type="button"
                                id="cla-confirmacao-cancelar"
                                style="
                                    min-height:
                                        43px;

                                    padding:
                                        9px 12px;
  
                                    border:
                                        1px solid
                                        rgba(
                                            148,
                                            163,
                                            184,
                                            0.32
                                        );

                                    border-radius:
                                        10px;
   
                                    background:
                                        linear-gradient(
                                            180deg,
                                            #27364d,
                                            #182235
                                        );

                                    color:
                                        #e4eaf2;
 
                                    font-weight:
                                        800;
    
                                    cursor:
                                        pointer;
                                "
                            >
                                ${cancelarSeguro}
                            </button>


                            <button
                                type="button"
                                id="cla-confirmacao-confirmar"
                                style="
                                    min-height:
                                        43px;

                                    padding:
                                        9px 12px;

                                    border:
                                        1px solid
                                        ${bordaConfirmar};
 
                                    border-radius:
                                        10px;

                                    background:
                                    ${fundoConfirmar};

                                    color:
                                        #fff7dc;
 
                                    font-weight:
                                        800;

                                    cursor:
                                        pointer;
                                "
                            >
                                ${confirmarSeguro}
                            </button>
                        </div>
                    </div>
                `;


                Object.assign(
                    overlay.style,
                    {
                        position: "fixed",
                        inset: "0",

                        zIndex: "20000",
 
                        display: "flex",
                        alignItems: "center",
                        justifyContent:
                            "center",

                        padding: "16px",

                        background:
                            "rgba(2, 6, 13, 0.78)",

                        backdropFilter:
                            "blur(6px)",

                        WebkitBackdropFilter:
                            "blur(6px)"
                    }
                );


                document.body.appendChild(
                    overlay
                );


                const btnCancelar =
                    elemento(
                        "cla-confirmacao-cancelar"
                    );

                const btnConfirmar =
                    elemento(
                        "cla-confirmacao-confirmar"
                    );


                let encerrado = false;


                function finalizar(
                    resultado
                ) {
                    if (encerrado) {
                        return;
                    }

                    encerrado = true;

                    document.removeEventListener(
                        "keydown",
                        aoPressionarTecla
                    );

                    overlay.remove();

                    resolve(resultado);
                }


                function aoPressionarTecla(
                    evento
                ) {
                    if (
                        evento.key ===
                        "Escape"
                    ) {
                        evento.preventDefault();

                        finalizar(false);
                    }
                }


                btnCancelar
                    ?.addEventListener(
                        "click",
                        function () {
                            finalizar(false);
                        }
                    );


                btnConfirmar
                    ?.addEventListener(
                        "click",
                        function () {
                            finalizar(true);
                        }
                    );


                document.addEventListener(
                    "keydown",
                    aoPressionarTecla
                );


                requestAnimationFrame(
                    function () {
                        btnConfirmar
                            ?.focus();
                    }
                );
            }
        );
    }

    async function requisicao(
        url,
        opcoes = {}
    ) {
        const resposta = await fetch(
            url,
            {
                cache: "no-store",
                ...opcoes
            }
        );

        let dados = {};

        try {
            dados = await resposta.json();
        } catch (erro) {
            dados = {};
        }

        if (
            !resposta.ok ||
            dados.success === false
        ) {
            throw new Error(
                dados.error ||
                dados.erro ||
                "A operação não pôde ser concluída."
            );
        }

        return dados;
    }


    // ========================================================
    // 🏅 LOJA DO CLÃ
    // ========================================================

    async function carregarLojaCla() {
        const saldo = elemento(
            "cla-loja-saldo"
        );

        const lista = elemento(
            "cla-loja-lista"
        );


        if (
            !saldo ||
            !lista ||
            !estadoCla.userId
        ) {
            return;
        }


        saldo.textContent =
            "🏅 ...";


        lista.innerHTML = `
            <div class="cla-vazio">
                Carregando Loja do Clã...
            </div>
        `;


        try {

            const dados = await requisicao(
                `/api/clan/loja/${
                    encodeURIComponent(
                        estadoCla.userId
                    )
                }?t=${Date.now()}`
            );


            // ================================================
            // 🏅 SALDO REAL
            // ================================================

            saldo.textContent =
                `🏅 ${
                    formatarNumero(
                        dados.medalhas_cla
                    )
                }`;


            // ================================================
            // 📦 CATÁLOGO REAL
            // ================================================

            const itens = Array.isArray(
                dados.itens
            )
                ? dados.itens
                : [];


            if (!itens.length) {

                lista.innerHTML = `
                    <div class="cla-vazio">
                        Nenhum item disponível
                        nesta semana.
                    </div>
                `;

                return;
            }


            lista.innerHTML = itens
                .map(
                    function (item) {

                        const itemId =
                            escaparHtml(
                                item.item_id ||
                                ""
                            );


                        const nome =
                            escaparHtml(
                                item.nome ||
                                item.item_id ||
                                "Item"
                            );


                        const emoji =
                            escaparHtml(
                                item.emoji ||
                                "📦"
                            );


                        const descricao =
                            escaparHtml(
                                item.descricao ||
                                "Item especial da Loja do Clã."
                            );


                        const custo =
                            Number(
                                item.custo_medalhas ||
                                0
                            );


                        const limite =
                            Number(
                                item.limite_semanal ||
                                0
                            );


                        return `
                            <div
                                class="cla-item-lista"
                                data-loja-item-id="${itemId}"
                            >
                                <div
                                    style="
                                        display: grid;

                                        grid-template-columns:
                                            48px
                                            minmax(0, 1fr)
                                            auto;

                                        gap: 11px;

                                        align-items:
                                            center;
                                    "
                                >

                                    <!-- ÍCONE -->
                                    <div
                                        style="
                                            width: 48px;
                                            height: 48px;

                                            display: flex;
                                            align-items: center;
                                            justify-content: center;

                                            border-radius:
                                                13px;

                                            border:
                                                1px solid
                                                rgba(
                                                    216,
                                                    184,
                                                    90,
                                                    0.28
                                                );

                                            background:
                                                rgba(
                                                    216,
                                                    184,
                                                    90,
                                                    0.08
                                                );

                                            font-size:
                                                24px;
                                        "
                                    >
                                        ${emoji}
                                    </div>


                                    <!-- INFORMAÇÕES -->
                                    <div
                                        style="
                                            min-width: 0;
                                        "
                                    >
                                        <div
                                            style="
                                                color:
                                                    #eef2f7;

                                                font-size:
                                                    0.82rem;

                                                font-weight:
                                                    900;
                                            "
                                        >
                                            ${nome}
                                        </div>


                                        <div
                                            style="
                                                margin-top:
                                                    3px;

                                                color:
                                                    #8f9bad;

                                                font-size:
                                                    0.68rem;

                                                line-height:
                                                    1.35;
                                            "
                                        >
                                            ${descricao}
                                        </div>


                                        <div
                                            style="
                                                margin-top:
                                                    6px;

                                                color:
                                                    #b5bfcc;

                                                font-size:
                                                    0.66rem;
                                            "
                                        >
                                            Limite:
                                            <strong>
                                                ${formatarNumero(
                                                    limite
                                                )}
                                            </strong>
                                            por semana
                                        </div>
                                    </div>


                                    <!-- PREÇO -->
                                    <div
                                        style="
                                            min-width:
                                                58px;

                                            text-align:
                                                center;

                                            padding:
                                                8px 7px;

                                            border-radius:
                                                10px;

                                            border:
                                                1px solid
                                                rgba(
                                                    216,
                                                    184,
                                                    90,
                                                    0.30
                                                );

                                            background:
                                                rgba(
                                                    216,
                                                    184,
                                                    90,
                                                    0.08
                                                );

                                            color:
                                                #f4dc91;

                                            font-size:
                                                0.75rem;

                                            font-weight:
                                                900;
                                        "
                                    >
                                        🏅
                                        ${formatarNumero(
                                            custo
                                        )}
                                    </div>
                                </div>
                            </div>
                        `;
                    }
                )
                .join("");


        } catch (erro) {

            console.error(
                "❌ Erro ao carregar Loja do Clã:",
                erro
            );


            saldo.textContent =
                "🏅 --";


            lista.innerHTML = `
                <div class="cla-vazio">
                    Não foi possível carregar
                    a Loja do Clã.
                </div>
            `;


            mostrarMensagem(
                erro.message ||
                "Erro ao carregar a Loja do Clã.",
                "erro"
            );
        }
    }


    function resetarDadosCargos() {
        estadoCla.cargos = [];
        estadoCla.permissoesCatalogo = [];
        estadoCla.minhasPermissoes = {};

        estadoCla.podeEditarEstrutura =
            false;

        estadoCla.limiteCargosPersonalizados =
            0;

        estadoCla.cargosPersonalizadosTotal =
            0;
    }


    async function carregarDadosCargos(
        clan
    ) {
        resetarDadosCargos();


        /*
         * Primeiro usa os dados que já vieram
         * junto com /meu_clan como fallback.
         */
        if (
            Array.isArray(
                clan?.cargos_lista
            )
        ) {
            estadoCla.cargos = [
                ...clan.cargos_lista
            ];
        }


        const membros = Array.isArray(
            clan?.membros
        )
            ? clan.membros
            : [];


        const meuMembro = membros.find(
            function (membro) {
                return (
                    String(
                        membro.user_id
                    ) ===
                    String(
                        estadoCla.userId
                    )
                );
            }
        );


        estadoCla.meuCargo =
            meuMembro?.cargo ||
            "membro";


        /*
         * Fallback local das permissões.
         */
        const configFallback =
            obterConfigCargo(
                estadoCla.meuCargo
            );


        if (
            configFallback?.permissoes
        ) {
            estadoCla.minhasPermissoes = {
                ...configFallback.permissoes
            };
        }


        estadoCla.podeEditarEstrutura =
            souLiderReal();


        estadoCla.limiteCargosPersonalizados =
            Number(
                clan
                    ?.limite_cargos_personalizados ||
                0
            );


        estadoCla.cargosPersonalizadosTotal =
            Number(
                clan
                    ?.cargos_personalizados_total ||
                0
            );


        /*
         * Agora consulta a rota especializada.
         */
        try {
            const dados = await requisicao(
                `/api/clan/cargos/listar/${
                    encodeURIComponent(
                        estadoCla.userId
                    )
                }?t=${Date.now()}`
            );


            estadoCla.meuCargo =
                dados.meu_cargo ||
                estadoCla.meuCargo;


            estadoCla.cargos =
                Array.isArray(
                    dados.cargos
                )
                    ? dados.cargos
                    : estadoCla.cargos;


            estadoCla.permissoesCatalogo =
                Array.isArray(
                    dados.permissoes
                )
                    ? dados.permissoes
                    : [];


            estadoCla.minhasPermissoes =
                (
                    dados.minhas_permissoes &&
                    typeof dados.minhas_permissoes ===
                        "object"
                )
                    ? {
                        ...dados.minhas_permissoes
                    }
                    : {};


            estadoCla.podeEditarEstrutura =
                Boolean(
                    dados.pode_editar_estrutura
                );


            estadoCla.limiteCargosPersonalizados =
                Number(
                    dados
                        .limite_cargos_personalizados ||
                    0
                );


            estadoCla.cargosPersonalizadosTotal =
                Number(
                    dados
                        .cargos_personalizados_total ||
                    0
                );


        } catch (erro) {
            /*
             * Não derruba a tela de clã se somente
             * a rota de cargos tiver problema.
             */
            console.warn(
                "⚠️ Não foi possível carregar "
                + "os dados completos dos cargos:",
                erro
            );
        }
    }
    
    // ========================================================
    // 🎖️ CARGOS - LISTAGEM E GERENCIAMENTO
    // ========================================================

    function permissoesCargoVisiveis() {
        const catalogo = Array.isArray(
            estadoCla.permissoesCatalogo
        )
            ? estadoCla.permissoesCatalogo
            : [];

        /*
         * Todas as permissões cadastradas no backend
         * já possuem ação correspondente na interface,
         * incluindo a administração do tesouro.
         */
        return catalogo;
    }


    function nomePermissaoCargo(
        permissaoId
    ) {
        const id = String(
            permissaoId || ""
        );

        const configuracao =
            estadoCla.permissoesCatalogo.find(
                function (permissao) {
                    return (
                        String(
                            permissao?.id || ""
                        ) === id
                    );
                }
            );

        if (
            configuracao &&
            configuracao.nome
        ) {
            return String(
                configuracao.nome
            );
        }

        return id
            .replaceAll("_", " ")
            .replace(
                /\b\w/g,
                function (letra) {
                    return letra.toUpperCase();
                }
            );
    }


    function renderizarPermissoesFormulario(
        permissoesAtuais = {}
    ) {
        const area = elemento(
            "cla-cargo-permissoes"
        );

        if (!area) {
            return;
        }

        const catalogo =
            permissoesCargoVisiveis();

        if (!catalogo.length) {
            area.innerHTML = `
                <div class="cla-vazio">
                    Nenhuma permissão disponível.
                </div>
            `;

            return;
        }

        area.innerHTML = catalogo
            .map(function (permissao) {
                const id = String(
                    permissao.id || ""
                );

                const nome = escaparHtml(
                    permissao.nome ||
                    nomePermissaoCargo(id)
                );

                const marcado = Boolean(
                    permissoesAtuais &&
                    permissoesAtuais[id]
                );

                return `
                    <label
                        class="
                            cla-cargo-permissao-opcao
                        "
                    >
                        <input
                            type="checkbox"
                            class="
                                cla-cargo-permissao-checkbox
                            "
                            data-permissao-id="${
                                escaparHtml(id)
                            }"
                            ${
                                marcado
                                    ? "checked"
                                    : ""
                            }
                        >

                        <span>
                            ${nome}
                        </span>
                    </label>
                `;
            })
            .join("");
    }


    function resetarFormularioCargo() {
        const campoId = elemento(
            "cla-cargo-id-edicao"
        );

        const campoNome = elemento(
            "cla-cargo-nome"
        ); 

        const campoOrdem = elemento(
            "cla-cargo-ordem"
        );

        const titulo = elemento(
            "cla-cargo-form-titulo"
        );

        const btnSalvar = elemento(
            "cla-btn-salvar-cargo"
        );

        const btnCancelar = elemento(
            "cla-btn-cancelar-cargo"
        );


        if (campoId) {
            campoId.value = "";
        }

        if (campoNome) {
            campoNome.value = "";
        }

        if (campoOrdem) {
            campoOrdem.value = "50";
        }

        if (titulo) {
            titulo.textContent =
                "➕ Criar novo cargo";
        }

        if (btnCancelar) {
            btnCancelar.style.display =
                "none";
        }


        renderizarPermissoesFormulario(
            {}
        );


        if (btnSalvar) {
            const limite = Number(
                estadoCla
                    .limiteCargosPersonalizados ||
                0
            );

            const total = Number(
                estadoCla
                    .cargosPersonalizadosTotal ||
                0
            );

            const limiteAtingido =
                limite > 0 &&
                total >= limite;

            btnSalvar.disabled =
                limiteAtingido;
 
            btnSalvar.textContent =
                "➕ Criar cargo";

            btnSalvar.title =
                limiteAtingido
                    ? (
                        "O clã atingiu o limite "
                        + "de cargos personalizados "
                        + "para o nível atual."
                    )
                    : "";
        }
    }


    function renderizarCargos() {
        preencherTexto(
            "cla-cargos-meu-cargo",
            traduzirCargo(
                estadoCla.meuCargo
            )
        );

        preencherTexto(
            "cla-cargos-total",
            formatarNumero(
                estadoCla
                    .cargosPersonalizadosTotal
            )
        );

        preencherTexto(
            "cla-cargos-limite",
            formatarNumero(
                estadoCla
                    .limiteCargosPersonalizados
            )
        );


        const areaGerenciar = elemento(
            "cla-area-gerenciar-cargos"
        );

        if (areaGerenciar) {
            areaGerenciar.style.display =
                estadoCla.podeEditarEstrutura
                    ? "block"
                    : "none";
        }


        const lista = elemento(
            "cla-lista-cargos"
        );

        if (!lista) {
            return;
        }


        const cargos = Array.isArray(
            estadoCla.cargos
        ) 
            ? [...estadoCla.cargos]
            : [];


        cargos.sort(
            function (a, b) {
                const ordemA = Number(
                    a?.ordem || 0
                );

                const ordemB = Number(
                    b?.ordem || 0
                );

                if (ordemA !== ordemB) {
                    return ordemB - ordemA;
                }

                return String(
                    a?.nome || ""
                ).localeCompare(
                    String(
                        b?.nome || ""
                    ),
                    "pt-BR"
                );
            }
        );


        if (!cargos.length) {
            lista.innerHTML = `
                <div class="cla-vazio">
                    Nenhum cargo encontrado.
                </div>
            `;

            return;
        }


        lista.innerHTML = cargos
            .map(function (cargo) {
                const cargoId = String(
                    cargo.id || ""
                );

                const nome = escaparHtml(
                    cargo.nome ||
                    traduzirCargo(cargoId)
                );

                const ordem = Number(
                    cargo.ordem || 0
                );

                const sistema = Boolean(
                    cargo.sistema
                );
 
                const protegido = Boolean(
                    cargo.protegido
                );

                const permissoes =
                    (
                        cargo.permissoes &&
                        typeof cargo.permissoes ===
                            "object"
                    )
                        ? cargo.permissoes
                        : {};


                const permissoesAtivas =
                    Object.keys(
                        permissoes
                    )
                        .filter(
                            function (id) {
                                return Boolean(
                                    permissoes[id]
                                );
                            }
                        )

                        .map(
                            function (id) {
                                return `
                                    <span
                                        class="
                                            cla-cargo-permissao
                                        "
                                    >
                                        ${
                                            escaparHtml(
                                                nomePermissaoCargo(
                                                    id
                                                )
                                            )
                                        }
                                    </span>
                                `;
                            }
                        )
                        .join("");


                const podeEditar =
                    estadoCla
                        .podeEditarEstrutura &&
                    !sistema &&
                    !protegido;


                return `
                    <div
                        class="cla-cargo-card"
                        data-cargo-id="${
                            escaparHtml(
                                cargoId
                            )
                        }"
                    >
                        <div
                            class="
                                cla-cargo-card-topo
                            "
                        >
                            <div>
                                <div
                                    class="
                                        cla-cargo-card-nome
                                    "
                                >
                                    ${nome}
                                </div>

                                <div
                                    class="
                                        cla-cargo-card-ordem
                                    "
                                >
                                    Hierarquia:
                                    <strong>
                                        ${ordem}
                                    </strong>
                                </div>
                            </div>
  
                            <span
                                class="
                                    cla-cargo-selo
                                    ${
                                        sistema
                                            ? "sistema"
                                            : "personalizado"
                                    }
                                "
                            >
                                ${
                                    sistema
                                        ? "Sistema"
                                        : "Personalizado"
                                }
                            </span>
                        </div>
   
   
                        <div
                            class="
                                cla-cargo-permissoes
                            "
                        >
                            ${
                                permissoesAtivas ||
                                `
                                    <span style="
                                        color: #8491a3;
                                        font-size: 0.68rem;
                                    ">
                                        Sem permissões
                                        administrativas.
                                    </span>
                                `
                            }
                        </div>


                        ${
                            podeEditar
                                ? `
                                    <div style="
                                        display: grid;
                                        grid-template-columns:
                                            1fr 1fr;
                                        gap: 7px;
                                        margin-top: 11px;
                                    ">
                                        <button
                                            type="button"
                                            class="
                                                cla-btn
                                                cla-btn-secundario
                                                cla-btn-editar-cargo
                                            "
                                            data-cargo-id="${
                                                escaparHtml(
                                                    cargoId
                                                )
                                            }"
                                        >
                                            ✏️ Editar
                                        </button>

                                        <button
                                            type="button"
                                            class="
                                                cla-btn
                                                cla-btn-perigo
                                                cla-btn-excluir-cargo
                                            "
                                            data-cargo-id="${
                                                escaparHtml(
                                                    cargoId
                                                )
                                            }"
                                        >
                                            🗑️ Excluir
                                        </button>
                                    </div>
                                `
                                : ""
                        }
                    </div>
                `;
            })
            .join("");


        if (
            estadoCla.podeEditarEstrutura
        ) {
            resetarFormularioCargo();
        }
    }


    function editarCargoNoFormulario(
        cargoId
    ) {
        if (
            !estadoCla.podeEditarEstrutura
        ) {
            return;
        }

        const cargo =
            obterConfigCargo(
                cargoId
            );

        if (
            !cargo ||
            cargo.sistema ||
            cargo.protegido
        ) {
            mostrarMensagem(
                "Esse cargo não pode ser editado.",
                "erro"
            );

            return;
        }


        const campoId = elemento(
            "cla-cargo-id-edicao"
        );

        const campoNome = elemento(
            "cla-cargo-nome"
        );

        const campoOrdem = elemento(
            "cla-cargo-ordem"
        );

        const titulo = elemento(
            "cla-cargo-form-titulo"
        );

        const btnSalvar = elemento(
            "cla-btn-salvar-cargo"
        );

        const btnCancelar = elemento(
            "cla-btn-cancelar-cargo"
        );


        if (campoId) {
            campoId.value =
                String(cargo.id);
        }

        if (campoNome) {
            campoNome.value =
                String(cargo.nome || "");
        }

        if (campoOrdem) {
            campoOrdem.value =
                String(
                    Number(
                        cargo.ordem || 50
                    )
                );
        }

        if (titulo) {
            titulo.textContent =
                `✏️ Editar ${cargo.nome}`;
        }

        if (btnSalvar) {
            btnSalvar.disabled = false;
            btnSalvar.textContent =
                "💾 Salvar alterações";
            btnSalvar.title = "";
        }

        if (btnCancelar) {
            btnCancelar.style.display =
                "flex";
        }


        renderizarPermissoesFormulario(
            cargo.permissoes || {}
        );
    }


    function coletarPermissoesFormulario() {
        const campoId = elemento(
            "cla-cargo-id-edicao"
        );

        const cargoId = String(
            campoId?.value || ""
        ).trim();

        const cargoAtual =
            cargoId
                ? obterConfigCargo(
                    cargoId
                )
                : null;


        /*
         * Em edição preservamos permissões
         * que ainda não aparecem na tela.
         */
        const resultado = {
            ...(
                cargoAtual?.permissoes ||
                {}
            )
        };


        document
            .querySelectorAll(
                "#cla-cargo-permissoes "
                + ".cla-cargo-permissao-checkbox"
            )
            .forEach(
                function (checkbox) {
                    const id = String(
                        checkbox.dataset
                            .permissaoId ||
                        ""
                    );

                    if (!id) {
                        return;
                    }

                    resultado[id] =
                        Boolean(
                            checkbox.checked
                        );
                }
            );


        return resultado;
    }


    async function salvarCargoClan() {
        if (
            !estadoCla.podeEditarEstrutura
        ) {
            mostrarMensagem(
                "Somente o líder pode gerenciar "
                + "a estrutura dos cargos.",
                "erro"
            );

            return;
        }


        const campoId = elemento(
            "cla-cargo-id-edicao"
        );

        const campoNome = elemento(
            "cla-cargo-nome"
        );

        const campoOrdem = elemento(
            "cla-cargo-ordem"
        );

        const btnSalvar = elemento(
            "cla-btn-salvar-cargo"
        );


        const cargoId = String(
            campoId?.value || ""
        ).trim();

        const editando =
            Boolean(cargoId);

        const nome = String(
            campoNome?.value || ""
        ).trim();

        const ordem = Number.parseInt(
            campoOrdem?.value,
            10
        );


        if (
            nome.length < 2 ||
            nome.length > 24
        ) {
            mostrarMensagem(
                "O nome do cargo precisa ter "
                + "de 2 a 24 caracteres.",
                "erro"
            );

            return;
        }


        if (
            !Number.isInteger(ordem) ||
            ordem < 20 ||
            ordem > 80
        ) {
            mostrarMensagem(
                "A hierarquia precisa estar "
                + "entre 20 e 80.",
                "erro"
            );

            return;
        }


        if (!editando) {
            const limite = Number(
                estadoCla
                    .limiteCargosPersonalizados ||
                0
            );

            const total = Number(
                estadoCla
                    .cargosPersonalizadosTotal ||
                0
            );

            if (
                limite > 0 &&
                total >= limite
            ) {
                mostrarMensagem(
                    "O clã atingiu o limite "
                    + "de cargos personalizados.",
                    "erro"
                );

                return;
            }
        }


        const permissoes =
            coletarPermissoesFormulario();


        const url = editando
            ? "/api/clan/cargos/editar"
            : "/api/clan/cargos/criar";


        const payload = {
            user_id:
                estadoCla.userId,

            nome,
            ordem,
            permissoes
        };


        if (editando) {
            payload.cargo_id =
                cargoId;
        }


        if (btnSalvar) {
            btnSalvar.disabled = true;
 
            btnSalvar.textContent =
                editando
                    ? "Salvando..."
                    : "Criando...";
        }


        try {
            const dados = await postJson(
                url,
                payload
            );


            mostrarMensagem(
                dados.message ||
                (
                    editando
                        ? "Cargo atualizado."
                        : "Cargo criado."
                )
            );


            await carregarMeuCla();
  
            trocarAba(
                "cargos",
                false
            );


        } catch (erro) {
            mostrarMensagem(
                erro.message,
                "erro"
            );

            if (btnSalvar) {
                btnSalvar.disabled = false;
 
                btnSalvar.textContent =
                    editando
                        ? "💾 Salvar alterações"
                        : "➕ Criar cargo";
            }
        }
    }


    async function excluirCargoClan(
        cargoId
    ) {
        if (
            !estadoCla.podeEditarEstrutura
        ) {
            return;
        }


        const cargo =
            obterConfigCargo(
                cargoId
            );


        if (
            !cargo ||
            cargo.sistema ||
            cargo.protegido
        ) {
            mostrarMensagem(
                "Esse cargo não pode ser excluído.",
                "erro"
            );

            return;
        }


        const confirmou =
            await confirmarAcaoCla({
                titulo:
                    "Excluir cargo",

                mensagem:
                    `Deseja excluir o cargo "${cargo.nome}"?`,

                confirmarTexto:
                    "🗑️ Excluir",

                icone:
                    "🗑️",

                perigo:
                    true
            });


        if (!confirmou) {
            return;
        }


        try {
            const dados = await postJson(
                "/api/clan/cargos/excluir",
                {
                    user_id:
                        estadoCla.userId,

                    cargo_id:
                        cargo.id
                }
            );


            mostrarMensagem(
                dados.message ||
                "Cargo excluído."
            );


            await carregarMeuCla();
 
            trocarAba(
                "cargos",
                false
            );


        } catch (erro) {
            mostrarMensagem(
                erro.message,
                "erro"
            );
        }
    }

    // ========================================================
    // 🚪 ABRIR E FECHAR
    // ========================================================

    window.abrirTelaCla = async function () {
        const userId = obterUserId();

        if (!userId) {
            window.location.replace(
                "/login"
            );

            return;
        }

        estadoCla.userId = userId;

        const modal = elemento(
            "cla-modal"
        );

        if (!modal) {
            console.error(
                "❌ cla-modal não foi encontrado."
            );

            return;
        }

        modal.style.display = "flex";

        document.body.classList.add(
            "ui-modal-aberta"
        );

        const areaRolagem = elemento(
            "cla-conteudo-scroll"
        );

        const barraAbas = elemento(
            "cla-abas"
        );

        /*
         * Limpa posições antigas antes de
         * carregar o clã.
         */
        if (areaRolagem) {
            areaRolagem.scrollTop = 0;
        }

        if (barraAbas) {
            barraAbas.scrollLeft = 0;
        }

        await carregarMeuCla();

        /*
         * Sempre abre na visão geral,
         * começando pelo topo da tela.
         */
        if (estadoCla.clan) {
            trocarAba(
                "visao-geral",
                false
            );
        }

        if (areaRolagem) {
            areaRolagem.scrollTop = 0;
        }

        if (barraAbas) {
            barraAbas.scrollLeft = 0;
        }
    };


    window.fecharTelaCla = function () {
        const modal = elemento("cla-modal");

        if (modal) {
            modal.style.display = "none";
        }

        const modalPerfil = elemento(
            "modal-ver-perfil"
        );

        if (
            !modalPerfil ||
            modalPerfil.style.display === "none"
        ) {
            document.body.classList.remove(
                "ui-modal-aberta"
            );
        }
    };


    // ========================================================
    // 📥 CARREGAR CLÃ
    // ========================================================

    async function carregarMeuCla() {
        if (estadoCla.carregando) {
            return;
        }

        estadoCla.carregando = true;

        const carregando = elemento(
            "cla-carregando"
        );

        const semClan = elemento(
            "cla-sem-clan"
        );

        const comClan = elemento(
            "cla-com-clan"
        );

        if (carregando) {
            carregando.style.display = "block";
        }

        if (semClan) {
            semClan.style.display = "none";
        }

        if (comClan) {
            comClan.style.display = "none";
        }

        try {
            const dados = await requisicao(
                `/api/clan/meu_clan/${
                    encodeURIComponent(
                        estadoCla.userId
                    )
                }?t=${Date.now()}`
            );

            estadoCla.custoCriacaoOuro =
                Number(
                    dados.custo_criacao_ouro ||
                    5000
                );

            if (!dados.possui_clan) {
                estadoCla.clan = null;
                estadoCla.meuCargo = null;

                resetarDadosCargos();

                renderizarSemClan();
                return;
            }


            estadoCla.clan = dados.clan;


            await carregarDadosCargos(
                dados.clan
            );


            renderizarComClan(
                dados.clan
            );

                } catch (erro) {
            console.error(
                "❌ Erro ao carregar/renderizar clã:",
                erro
            );

            mostrarMensagem(
                erro.message ||
                "Erro ao carregar o clã.",
                "erro"
            );

            /*
             * Um erro de JavaScript não pode
             * fazer o jogador aparecer sem clã.
             */
            if (!estadoCla.clan) {
                renderizarSemClan();
            }

        } finally {
            
            estadoCla.carregando = false;

            if (carregando) {
                carregando.style.display = "none";
            }
        }
    }


    function renderizarSemClan() {
        const semClan = elemento(
            "cla-sem-clan"
        );

        const comClan = elemento(
            "cla-com-clan"
        );

        if (semClan) {
            semClan.style.display = "block";
        }

        if (comClan) {
            comClan.style.display = "none";
        }

                const custo = Number(
            estadoCla
                .custoCriacaoOuro ||
            5000
        );


        preencherTexto(
            "cla-custo-criacao",
            `${formatarNumero(
                custo
            )} 🪙`
        );


        const btnCriar = elemento(
            "cla-btn-criar"
        );


        if (btnCriar) {
            btnCriar.textContent =
                `🛡️ Fundar clã — ${
                    formatarNumero(
                        custo
                    )
                } 🪙`;
        }
    }


    function renderizarComClan(clan) {
        const semClan = elemento(
            "cla-sem-clan"
        );

        const comClan = elemento(
            "cla-com-clan"
        );

        if (semClan) {
            semClan.style.display = "none";
        }

        if (comClan) {
            comClan.style.display = "block";
        }

        const membros = Array.isArray(
            clan.membros
        )
            ? clan.membros
            : [];

        const meuMembro = membros.find(
            function (membro) {
                return String(membro.user_id) ===
                    String(estadoCla.userId);
            }
        );

        estadoCla.meuCargo = meuMembro
            ? meuMembro.cargo
            : "membro";

        const tesouro = clan.tesouro || {};

        preencherTexto(
            "cla-nome",
            clan.nome || "Clã"
        );

        preencherTexto(
            "cla-tag",
            clan.tag || ""
        );

        preencherTexto(
            "cla-descricao",
            clan.descricao ||
            "Este clã ainda não possui descrição."
        );

        preencherTexto(
            "cla-nivel",
            `Nv. ${Number(clan.nivel || 1)}`
        );
        
        const logoImagem = elemento("cla-logo");
        const logoFallback = elemento(
            "cla-logo-fallback"
        );

        if (logoImagem) {
            const logoUrl = String(
                clan.logo_url || ""
            ).trim();

            if (logoUrl) {
                logoImagem.style.display = "block";
                logoImagem.src =
                    `${logoUrl}?v=${Date.now()}`;

                if (logoFallback) {
                    logoFallback.style.display = "none";
                }

                logoImagem.onerror = function () {
                    logoImagem.style.display = "none";

                    if (logoFallback) {
                        logoFallback.style.display = "block";
                    }
                };
            } else {
                logoImagem.removeAttribute("src");
                logoImagem.style.display = "none";

                if (logoFallback) {
                    logoFallback.style.display = "block";
                }
            }
        }
        
        preencherTexto(
            "cla-total-membros",
            `${
                Number(
                    clan.membros_total ||
                    membros.length
                )
            } / ${
                Number(
                    clan.capacidade_membros ||
                    10
                )
            }`
        );

        preencherTexto(
            "cla-xp",
            formatarNumero(clan.xp)
        );

        preencherTexto(
            "cla-tesouro",
            `${formatarNumero(
                tesouro.ouro
            )} 🪙`
        );

        preencherTexto(
            "cla-tesouro-saldo",
            `${formatarNumero(
                tesouro.ouro
            )} 🪙`
        );

        preencherTexto(
            "cla-meu-cargo",
            traduzirCargo(
                estadoCla.meuCargo
            )
        );

        const btnSair = elemento(
            "cla-btn-sair"
        );

        const btnDissolver = elemento(
            "cla-btn-dissolver"
        );

        const ehLider =
            souLiderReal();


        const podeAlterarBrasao =
            temPermissaoCla(
                "alterar_brasao"
            );


        const podeEditarCla =
            temPermissaoCla(
                "editar_cla"
            );


        const podeMelhorarCla =
            temPermissaoCla(
                "melhorar_cla"
            );
        
        if (btnSair) {
            btnSair.style.display =
                ehLider
                    ? "none"
                    : "flex";
        }

        if (btnDissolver) {
            btnDissolver.style.display =
                ehLider
                    ? "flex"
                    : "none";
        }    
        
        const areaLogo = elemento(
            "cla-gerenciar-logo"
        );

        if (areaLogo) {
            areaLogo.style.display =
                podeAlterarBrasao
                    ? "block"
                    : "none";
        }

        const btnAbaConfiguracoes = elemento(
            "cla-aba-configuracoes-btn"
        );

        if (btnAbaConfiguracoes) {
            btnAbaConfiguracoes.style.display =
                podeEditarCla
                    ? "block"
                    : "none";
        }

        const abaConfiguracoes = elemento(
            "cla-tab-configuracoes"
        );

        if (podeEditarCla) {
            const configuracoes =
                clan.configuracoes || {};

            const campoDescricao = elemento(
                "cla-config-descricao"
            );

            const campoTipoEntrada = elemento(
                "cla-config-tipo-entrada"
            );

            const campoNivelMinimo = elemento(
                "cla-config-nivel-minimo"
            );

            if (campoDescricao) {
                campoDescricao.value =
                    clan.descricao || "";
            }

            if (campoTipoEntrada) {
                campoTipoEntrada.value =
                    configuracoes.tipo_entrada ||
                    "convite";

                atualizarExplicacaoRecrutamento(
                    campoTipoEntrada.value
                );
            }

            if (campoNivelMinimo) {
                campoNivelMinimo.value = Number(
                    configuracoes.nivel_minimo || 1
                );
            }


        } else if (
            abaConfiguracoes &&
            abaConfiguracoes.style.display === "block"
        ) {
            trocarAba("visao-geral");
        }
        
        if (podeAlterarBrasao) {
            carregarCatalogoLogos(
                clan.logo_id
            );
        }

        const btnMelhorar = elemento(
            "cla-btn-melhorar"
        );

        const areaMelhoria = elemento(
            "cla-dados-melhoria"
        );

        const melhoria =
            clan.proxima_melhoria || null;

        if (!melhoria) {
            if (areaMelhoria) {
                areaMelhoria.innerHTML = `
                    <div style="
                        padding: 12px;
                        text-align: center;
                        color: #f4dc91;
                        font-weight: 800;
                    ">
                        🏆 O clã alcançou o nível máximo.
                    </div>

                    <div style="
                        margin-top: 8px;
                        color: #8491a3;
                        text-align: center;
                        font-size: 0.76rem;
                    ">
                        Capacidade atual:
                        ${formatarNumero(
                            clan.capacidade_membros || 50
                        )} membros
                    </div>
                `;
            }

            if (btnMelhorar) {
                btnMelhorar.disabled = true;
                btnMelhorar.textContent =
                    "🏆 Nível máximo";
                btnMelhorar.title =
                    "O clã já alcançou o nível máximo.";
            }

        } else {
            const xpAtual = Number(
                melhoria.xp_atual ||
                clan.xp ||
                0
            );

            const xpNecessario = Number(
                melhoria.xp_necessario || 0
            );

            const xpFaltante = Number(
                melhoria.xp_faltante || 0
            );

            const ouroAtual = Number(
                melhoria.ouro_atual ||
                clan.tesouro?.ouro ||
                0
            );

            const ouroNecessario = Number(
                melhoria.ouro_necessario || 0
            );

            const ouroFaltante = Number(
                melhoria.ouro_faltante || 0
            );

            const percentualXp =
                xpNecessario > 0
                    ? Math.min(
                        100,
                        Math.max(
                            0,
                            (
                                xpAtual /
                                xpNecessario
                            ) * 100
                        )
                    )
                    : 100;

            const percentualOuro =
                ouroNecessario > 0
                    ? Math.min(
                        100,
                        Math.max(
                            0,
                            (
                                ouroAtual /
                                ouroNecessario
                            ) * 100
                        )
                    )
                    : 100;

            if (areaMelhoria) {
                areaMelhoria.innerHTML = `
                    <div style="
                        display: grid;
                        grid-template-columns:
                            repeat(2, minmax(0, 1fr));
                        gap: 8px;
                        margin-bottom: 16px;
                    ">
                        <div style="
                            padding: 10px;
                            text-align: center;
                            background:
                                rgba(22, 32, 51, 0.72);
                            border:
                                1px solid rgba(
                                    148,
                                    163,
                                    184,
                                    0.18
                                );
                            border-radius: 10px;
                        ">
                            <div style="
                                color: #8491a3;
                                font-size: 0.68rem;
                            ">
                                Nível atual
                            </div>

                            <strong style="
                                display: block;
                                margin-top: 4px;
                                color: #f4f7fb;
                            ">
                                ${Number(
                                    clan.nivel || 1
                                )}
                            </strong>
                        </div>

                        <div style="
                            padding: 10px;
                            text-align: center;
                            background:
                                rgba(139, 108, 36, 0.15);
                            border:
                                1px solid rgba(
                                    216,
                                    184,
                                    90,
                                    0.25
                                );
                            border-radius: 10px;
                        ">
                            <div style="
                                color: #d8b85a;
                                font-size: 0.68rem;
                            ">
                                Próximo nível
                            </div>
        
                            <strong style="
                                display: block;
                                margin-top: 4px;
                                color: #f4dc91;
                            ">
                                ${Number(
                                    melhoria.nivel
                                )}
                            </strong>
                        </div>
                    </div>
        
                    <!-- XP -->
                    <div style="margin-bottom: 16px;">
                        <div style="
                            display: flex;
                            justify-content: space-between;
                            gap: 10px;
                            margin-bottom: 6px;
                            font-size: 0.76rem;
                        ">
                            <strong style="color: #e2e8f0;">
                                ✨ XP do clã
                            </strong>
        
                            <span style="color: #c5ceda;">
                                ${formatarNumero(xpAtual)}
                                /
                                ${formatarNumero(
                                    xpNecessario
                                )}
                            </span>
                        </div>
        
                        <div style="
                            height: 10px;
                            overflow: hidden;
                            background: #050914;
                            border:
                                1px solid rgba(
                                    96,
                                    165,
                                    250,
                                    0.25
                                );
                            border-radius: 999px;
                        ">
                            <div style="
                                width: ${percentualXp}%;
                                height: 100%;
                                background:
                                    linear-gradient(
                                        90deg,
                                        #2563eb,
                                        #60a5fa
                                    );
                                border-radius: 999px;
                            "></div>
                        </div>
        
                        <div style="
                            margin-top: 5px;
                            color: ${
                                xpFaltante > 0
                                    ? "#94a3b8"
                                    : "#4ade80"
                            };
                            font-size: 0.70rem;
                        ">
                            ${
                                xpFaltante > 0
                                    ? `
                                        Faltam
                                        <strong>
                                            ${formatarNumero(
                                                xpFaltante
                                            )} XP
                                        </strong>
                                    `
                                    : `
                                        ✅ XP necessário alcançado
                                    `
                            }
                        </div>
                    </div>
        
                    <!-- OURO -->
                    <div style="margin-bottom: 16px;">
                        <div style="
                            display: flex;
                            justify-content: space-between;
                            gap: 10px;
                            margin-bottom: 6px;
                            font-size: 0.76rem;
                        ">
                            <strong style="color: #e2e8f0;">
                                🪙 Ouro do tesouro
                            </strong>
        
                            <span style="color: #c5ceda;">
                                ${formatarNumero(ouroAtual)}
                                /
                                ${formatarNumero(
                                    ouroNecessario
                                )}
                            </span>
                        </div>
        
                        <div style="
                            height: 10px;
                            overflow: hidden;
                            background: #050914;
                            border:
                                1px solid rgba(
                                    216,
                                    184,
                                    90,
                                    0.28
                                );
                            border-radius: 999px;
                        ">
                            <div style="
                                width: ${percentualOuro}%;
                                height: 100%;
                                background:
                                    linear-gradient(
                                        90deg,
                                        #8b6c24,
                                        #e7c75f
                                    );
                                border-radius: 999px;
                            "></div>
                        </div>
        
                        <div style="
                            margin-top: 5px;
                            color: ${
                                ouroFaltante > 0
                                    ? "#94a3b8"
                                    : "#4ade80"
                            };
                            font-size: 0.70rem;
                        ">
                            ${
                                ouroFaltante > 0
                                    ? `
                                        Faltam
                                        <strong>
                                            ${formatarNumero(
                                                ouroFaltante
                                            )} moedas
                                        </strong>
                                    `
                                    : `
                                        ✅ Ouro necessário alcançado
                                    `
                            }
                        </div>
                    </div>
        
                    <!-- CAPACIDADE -->
                    <div style="
                        padding-top: 12px;
                        border-top:
                            1px solid rgba(
                                148,
                                163,
                                184,
                                0.18
                            );
                        color: #cbd5e1;
                        font-size: 0.77rem;
                        line-height: 1.6;
                    ">
                        <div>
                            Capacidade atual:
                            <strong>
                                ${formatarNumero(
                                    melhoria
                                        .capacidade_atual
                                )} membros
                            </strong>
                        </div>
        
                        <div>
                            Próxima capacidade:
                            <strong style="
                                color: #f4dc91;
                            ">
                                ${formatarNumero(
                                    melhoria
                                        .proxima_capacidade
                                )} membros
                            </strong>
                        </div>
                    </div>
                `;
            }

            const possuiRecursos =
                Boolean(
                    melhoria.pode_melhorar
                );

            if (btnMelhorar) {
                btnMelhorar.textContent =
                    "⬆️ Melhorar clã";
        
                btnMelhorar.disabled =
                    !podeMelhorarCla ||
                    !possuiRecursos;

                if (!podeMelhorarCla) {
                    btnMelhorar.title =
                        "Seu cargo não permite melhorar o clã.";

                } else if (!possuiRecursos) {
                    btnMelhorar.title =
                        `Faltam ${formatarNumero(
                            xpFaltante
                        )} XP e ${formatarNumero(
                            ouroFaltante
                        )} moedas.`;

                } else {
                    btnMelhorar.title =
                        "Recursos completos. Melhorar clã.";
                }
            }
        }

        renderizarCargos();

        renderizarMembros(membros);

        prepararTesouroClan(
            membros,
            tesouro
        );

        renderizarAtividades(
            Array.isArray(clan.atividades)
                ? clan.atividades
                : []
        );

        prepararAreaSolicitacoes();
    }


    function preencherTexto(id, texto) {
        const alvo = elemento(id);

        if (alvo) {
            alvo.textContent = texto;
        }
    }


    // ========================================================
    // 👥 MEMBROS
    // ========================================================

    function renderizarMembros(membros) {
        const lista = elemento(
            "cla-lista-membros"
        );

        if (!lista) {
            return;
        }

        if (!membros.length) {
            lista.innerHTML = `
                <div class="cla-vazio">
                    Nenhum membro encontrado.
                </div>
            `;

            return;
        }

        const membrosOrdenados = [
            ...membros
        ].sort(function (a, b) {
            const cargoA =
                hierarquiaCargo(
                    a.cargo
                );

            const cargoB =
                hierarquiaCargo(
                    b.cargo
                );
  
            if (cargoA !== cargoB) {
                return cargoB - cargoA;
            }

            return String(
                a.nome || ""
            ).localeCompare(
                String(b.nome || ""),
                "pt-BR"
            );
        });

        lista.innerHTML = membrosOrdenados
            .map(function (membro) {
                const membroId = escaparHtml(
                    membro.user_id
                );

                const nome = escaparHtml(
                    membro.nome ||
                    "Aventureiro"
                );

                const cargoOriginal =
                    membro.cargo || "membro";

                const cargo = escaparHtml(
                    traduzirCargo(
                        cargoOriginal
                    )
                );

                const xp = formatarNumero(
                    membro.contribuicao_xp
                );

                const ouro = formatarNumero(
                    membro.contribuicao_ouro
                );

                const souEu =
                    String(membro.user_id) ===
                    String(estadoCla.userId);

                const possoAlterarCargo =
                    podeAlterarCargoMembro(
                        cargoOriginal,
                        souEu
                    );

                const possoExpulsar =
                    !souEu &&
                    podeExpulsarMembro(
                        estadoCla.meuCargo,
                        cargoOriginal
                    );

                const possoTransferir =
                    souLiderReal() &&
                    !souEu &&
                    cargoOriginal !== "lider";

                const opcoesCargoHtml =
                    possoAlterarCargo
                        ? montarOpcoesCargoMembro(
                            cargoOriginal
                        )
                        : "";

                let gerenciamentoHtml = "";

                if (possoAlterarCargo) {
                    gerenciamentoHtml += `
                        <div style="
                            display: grid;
                            grid-template-columns:
                                minmax(0, 1fr) auto;
                            gap: 6px;
                            margin-top: 8px;
                        ">
                            <select
                                class="cla-select-cargo"
                                data-membro-id="${membroId}"
                                style="
                                    width: 100%;
                                    padding: 8px;
                                    border-radius: 7px;
                                    border:
                                        1px solid #475569;
                                    background: #0f172a;
                                    color: #f8fafc;
                                "
                            >
                                ${opcoesCargoHtml}
                            </select>
 
                            <button
                                type="button"
                                class="
                                    cla-btn
                                    cla-btn-alterar-cargo
                                "
                                data-membro-id="${membroId}"
                                style="
                                    min-height: 36px;
                                    padding: 7px 10px;
                                "
                            >
                                Salvar
                            </button>
                        </div>
                    `;
                }

                if (
                    possoExpulsar ||
                    possoTransferir
                ) {
                    gerenciamentoHtml += `
                        <div style="
                            display: grid;
                            grid-template-columns:
                                repeat(
                                    auto-fit,
                                    minmax(125px, 1fr)
                                );
                            gap: 6px;
                            margin-top: 7px;
                        ">
                            ${
                                possoTransferir
                                    ? `
                                        <button
                                            type="button"
                                            class="
                                                cla-btn
                                                cla-btn-transferir-lideranca
                                            "
                                            data-membro-id="${membroId}"
                                            data-membro-nome="${nome}"
                                        >
                                            👑 Tornar líder
                                        </button>
                                    `
                                    : ""
                            }
 
                            ${
                                possoExpulsar
                                    ? `
                                        <button
                                            type="button"
                                            class="
                                                cla-btn
                                                cla-btn-perigo
                                                cla-btn-expulsar-membro
                                            "
                                            data-membro-id="${membroId}"
                                            data-membro-nome="${nome}"
                                        >
                                            🚫 Expulsar
                                        </button>
                                    `
                                    : ""
                            }
                        </div>
                    `;
                }

                return `
                    <div class="cla-item-lista">
                        <div style="
                            display: flex;
                            justify-content:
                                space-between;
                            align-items:
                                flex-start;
                            gap: 10px;
                        ">
                            <div>
                                <strong style="
                                    color: #facc15;
                                ">
                                    ${nome}
                                    ${
                                        souEu
                                            ? `
                                                <span style="
                                                    color: #94a3b8;
                                                    font-size: 0.72rem;
                                                ">
                                                    (você)
                                                </span>
                                            `
                                            : ""
                                    }
                                </strong>

                                <div style="
                                    color: #cbd5e1;
                                    font-size: 0.85rem;
                                    margin-top: 3px;
                                ">
                                    ${cargo}
                                </div>

                                <div style="
                                    color: #94a3b8;
                                    font-size: 0.78rem;
                                    margin-top: 5px;
                                ">
                                    XP: ${xp}
                                    · Ouro: ${ouro}
                                </div>
                            </div>

                            <button
                                type="button"
                                class="
                                    cla-btn
                                    cla-btn-secundario
                                    cla-btn-inspecionar
                                "
                                data-membro-id="${membroId}"
                                style="
                                    min-height: 36px;
                                    padding: 7px 10px;
                                "
                            >
                                🕵️ Inspecionar
                            </button>
                        </div>

                        ${gerenciamentoHtml}
                    </div>
                `;
            })
            .join("");
    }
    
    // ========================================================
    // 📩 SOLICITAÇÕES PARA ENTRAR NO CLÃ
    // ========================================================

    function prepararAreaSolicitacoes() {
        const abaConvites = elemento(
            "cla-tab-convites"
        );

        const btnAbaConvites = elemento(
            "cla-aba-convites-btn"
        );

        const areaConvidar = elemento(
            "cla-area-convidar-herois"
        );


        if (!abaConvites) {
            return;
        }


        let areaSolicitacoes = elemento(
            "cla-area-solicitacoes-clan"
        );


        if (!areaSolicitacoes) {
            abaConvites.insertAdjacentHTML(
                "afterbegin",
                `
                    <div
                        id="cla-area-solicitacoes-clan"
                        style="
                            display: none;
                            padding-bottom: 14px;
                            margin-bottom: 14px;
                            border-bottom:
                                1px solid rgba(
                                    148,
                                    163,
                                    184,
                                    0.20
                                );
                        "
                    >
                        <h3 class="cla-titulo-bloco">
                            📩 Pedidos para entrar
                        </h3>

                        <p
                            class="cla-subtitulo-bloco"
                            style="margin-bottom: 12px;"
                        >
                            Avalie os aventureiros que
                            solicitaram entrada no clã.
                        </p>

                        <div
                            id="cla-lista-solicitacoes"
                            class="cla-lista"
                        ></div>
                    </div>
                `
            );


            areaSolicitacoes = elemento(
                "cla-area-solicitacoes-clan"
            );
        }


        const tipoEntrada = String(
            estadoCla.clan
                ?.configuracoes
                ?.tipo_entrada ||
            "convite"
        );


        const recrutamentoFechado =
            tipoEntrada === "fechado";


        const podeConvidar =
            temPermissaoCla(
                "convidar"
            ) &&
            !recrutamentoFechado;


        const podeReceberSolicitacoes =
            temPermissaoCla(
                "aceitar_solicitacoes"
            ) &&
            tipoEntrada ===
                "solicitacao";


        /*
         * Área de busca e convite.
         */
        if (areaConvidar) {
            areaConvidar.style.display =
                podeConvidar
                    ? "block"
                    : "none";
        }


        /*
         * Área de pedidos recebidos.
         */
        if (areaSolicitacoes) {
            areaSolicitacoes.style.display =
                podeReceberSolicitacoes
                    ? "block"
                    : "none";
        }


        /*
         * A aba só existe visualmente quando
         * há alguma ação disponível.
         */
        const deveMostrarAba =
            podeConvidar ||
            podeReceberSolicitacoes;


        if (btnAbaConvites) {
            btnAbaConvites.style.display =
                deveMostrarAba
                    ? "block"
                    : "none";
        }


        /*
         * Se perdeu a permissão enquanto estava
         * nesta aba, volta para a visão geral.
         */
        if (
            !deveMostrarAba &&
            abaConvites.style.display ===
                "block"
        ) {
            trocarAba(
                "visao-geral",
                false
            );
        }


        if (
            podeReceberSolicitacoes
        ) {  
            listarSolicitacoesRecebidas();
        }
    }


    async function listarSolicitacoesRecebidas() {
        const lista = elemento(
            "cla-lista-solicitacoes"
        );

        if (!lista) {
            return;
        }

        lista.innerHTML = `
            <div class="cla-vazio">
                Consultando pedidos...
            </div>
        `;

        try {
            const dados = await requisicao(
                `/api/clan/solicitacoes/${
                    encodeURIComponent(
                        estadoCla.userId
                    )
                }?t=${Date.now()}`
            );

            const solicitacoes = Array.isArray(
                dados.solicitacoes
            )
                ? dados.solicitacoes
                : [];

            if (!solicitacoes.length) {
                lista.innerHTML = `
                    <div class="cla-vazio">
                        Nenhum pedido pendente.
                    </div>
                `;

                return;
            }

            lista.innerHTML = solicitacoes
                .map(function (pedido) {
                    const userId = escaparHtml(
                        pedido.user_id
                    );

                    const nome = escaparHtml(
                        pedido.nome ||
                        "Aventureiro"
                    );

                    const classe = escaparHtml(
                        pedido.classe ||
                       "aventureiro"
                    );

                    return `
                        <div class="cla-item-lista">
                            <strong style="
                                color: #facc15;
                            ">
                                ${nome}
                            </strong>

                            <div style="
                                color: #cbd5e1;
                                font-size: 0.82rem;
                                margin-top: 5px;
                            ">
                                ${classe}
                                · Nível ${
                                    Number(
                                        pedido.nivel || 1
                                    )
                                }
                            </div>
  
                            <div style="
                                color: #94a3b8;
                                font-size: 0.74rem;
                                margin-top: 5px;
                            ">
                                Pedido enviado em
                                ${
                                    escaparHtml(
                                        formatarData(
                                            pedido.criado_em
                                        )
                                    )
                                }
                            </div>

                            <div style="
                                display: grid;
                                grid-template-columns: 1fr 1fr;
                                gap: 7px;
                                margin-top: 10px;
                            ">
                                <button
                                    type="button"
                                    class="
                                        cla-btn
                                        cla-btn-aceitar-solicitacao
                                    "
                                    data-user-id="${userId}"
                                >
                                    ✅ Aceitar
                                </button>

                            <button
                                    type="button"
                                    class="
                                        cla-btn
                                        cla-btn-perigo
                                        cla-btn-recusar-solicitacao
                                    "
                                    data-user-id="${userId}"
                                >
                                    ❌ Recusar
                                </button>
                            </div>
                        </div>
                    `;
                })
                .join("");

        } catch (erro) {
            lista.innerHTML = "";

            mostrarMensagem(
                erro.message,
                "erro"
            );
        }
    }


    async function aceitarSolicitacaoClan(
        alvoId
    ) {
        try {
            const dados = await postJson(
                "/api/clan/solicitacao/aceitar",
                {
                    user_id: estadoCla.userId,
                    alvo_id: alvoId
                }
            );

            mostrarMensagem(
                dados.message ||
                "Solicitação aceita."
            );

            await carregarMeuCla();

        } catch (erro) {
            mostrarMensagem(
                erro.message,
                "erro"
            );
        }
    }


    async function recusarSolicitacaoClan(
        alvoId
    ) {
        try {
            const dados = await postJson(
                "/api/clan/solicitacao/recusar",
                {
                    user_id: estadoCla.userId,
                    alvo_id: alvoId
                }
            );

            mostrarMensagem(
                dados.message ||
                "Solicitação recusada."
            );

            await listarSolicitacoesRecebidas();

        } catch (erro) {
            mostrarMensagem(
                erro.message,
                "erro"
            );
        }
    }

    async function alterarCargoMembro(
        alvoId,
        novoCargo
    ) {
        try {
            const dados = await postJson(
                "/api/clan/cargo",
                {
                    user_id: estadoCla.userId,
                    alvo_id: alvoId,
                    novo_cargo: novoCargo
                }
            );

            mostrarMensagem(
                dados.message ||
                "Cargo alterado."
            );

            await carregarMeuCla();

        } catch (erro) {
            mostrarMensagem(
                erro.message,
                "erro"
            );
        }
    }


    async function expulsarMembroClan(
        alvoId,
        nome
    ) {
        const confirmou =
            await confirmarAcaoCla({
                titulo:
                    "Expulsar membro",

            mensagem:
                `Deseja expulsar ${nome} do clã?`,

            confirmarTexto:
                "🚫 Expulsar",

            cancelarTexto:
                "Cancelar",

            icone:
                "🚫",

            perigo:
                true
        });

        if (!confirmou) {
            return;
        }

        try {
            const dados = await postJson(
                "/api/clan/expulsar",
                {
                    user_id: estadoCla.userId,
                    alvo_id: alvoId
                }
            );

            mostrarMensagem(
                dados.message ||
                "Membro expulso."
            );

            await carregarMeuCla();

        } catch (erro) {
            mostrarMensagem(
                erro.message,
                "erro"
            );
        }
    }


    async function transferirLiderancaClan(
        alvoId,
        nome
    ) {
        const confirmou =
            await confirmarAcaoCla({
                titulo:
                    "Transferir liderança",

                mensagem:
                    `Deseja transferir a liderança para ${nome}?`,

                confirmarTexto:
                    "Continuar",

                icone:
                    "👑"
            });

        if (!confirmou) {
            return;
        }

        const confirmouNovamente =
            await confirmarAcaoCla({
                titulo:
                    "Confirmar transferência",

                mensagem:
                    "Você passará a ser vice-líder e o outro membro assumirá a liderança.",

                confirmarTexto:
                    "👑 Transferir",

                icone:
                    "⚠️",

                perigo:
                    true
            });

        if (!confirmouNovamente) {
            return;
        }

        try {
            const dados = await postJson(
                "/api/clan/transferir_lideranca",
                {
                    user_id: estadoCla.userId,
                    novo_lider_id: alvoId
                }
            );

            mostrarMensagem(
                dados.message ||
                "Liderança transferida."
            );

            await carregarMeuCla();

        } catch (erro) {
            mostrarMensagem(
                erro.message,
                "erro"
          );
        }
    }

    // ========================================================
    // 🕵️ INSPEÇÃO
    // ========================================================

    window.abrirInspecaoMembroCla =
        async function (alvoId) {
            const modal = elemento(
                "modal-ver-perfil"
            );

            const conteudo = elemento(
                "conteudo-ver-perfil"
            );

            if (!modal || !conteudo) {
                mostrarMensagem(
                    "O modal de perfil não foi encontrado.",
                    "erro"
                );

                return;
            }

            modal.style.display = "flex";

            document.body.classList.add(
                "ui-modal-aberta"
            );

            conteudo.innerHTML = `
                <div style="
                    padding: 35px 10px;
                    color: #94a3b8;
                ">
                    🛡️ Consultando o membro...
                </div>
            `;

            try {
                const dados = await requisicao(
                    `/api/clan/membro/${
                        encodeURIComponent(
                            alvoId
                        )
                    }?user_id=${
                        encodeURIComponent(
                            estadoCla.userId
                        )
                    }&t=${Date.now()}`
                );

                renderizarInspecao(
                    dados.membro
                );

            } catch (erro) {
                conteudo.innerHTML = `
                    <div style="
                        padding: 30px 10px;
                        color: #fecaca;
                    ">
                        ${
                            escaparHtml(
                                erro.message
                            )
                        }
                    </div>
                `;
            }
        };


    function renderizarInspecao(membro) {
        const conteudo = elemento(
            "conteudo-ver-perfil"
        );

        if (!conteudo) {
            return;
        }

        const status = membro.status || {};

        const equipamentos = Array.isArray(
            membro.equipamentos
        )
            ? membro.equipamentos
            : [];

        const equipamentosHtml =
            equipamentos.length
                ? equipamentos.map(
                    function (item) {
                        const refino =
                            Number(
                                item.refino || 0
                            );

                        return `
                            <div style="
                                padding: 8px;
                                margin-bottom: 6px;
                                background:
                                    rgba(
                                        15,
                                        23,
                                        42,
                                        0.85
                                    );
                                border:
                                    1px solid #475569;
                                border-radius: 7px;
                                text-align: left;
                            ">
                                <strong>
                                    ${
                                        escaparHtml(
                                            item.icone ||
                                            "📦"
                                        )
                                    }
                                    ${
                                        escaparHtml(
                                            item.nome
                                        )
                                    }
                                </strong>

                                <div style="
                                    font-size: 0.78rem;
                                    color: #94a3b8;
                                    margin-top: 3px;
                                ">
                                    ${
                                        escaparHtml(
                                            item.slot
                                        )
                                    }
                                    · ${
                                        escaparHtml(
                                            item.raridade
                                        )
                                    }
                                    ${
                                        refino > 0
                                            ? ` · +${refino}`
                                            : ""
                                    }
                                </div>
                            </div>
                        `;
                    }
                ).join("")
                : `
                    <div style="
                        color: #94a3b8;
                        padding: 12px;
                    ">
                        Nenhum equipamento utilizado.
                    </div>
                `;

        const avatar =
            escaparHtml(
                membro.avatar_url || ""
            );

        const bannerStyle =
            membro.banner_url
                ? `
                    background-image:
                        linear-gradient(
                            rgba(0,0,0,0.25),
                            rgba(0,0,0,0.75)
                        ),
                        url('${
                            escaparHtml(
                                membro.banner_url
                            )
                        }');
                    background-size: cover;
                    background-position: center;
                `
                : `
                    background:
                        linear-gradient(
                            135deg,
                            #451a03,
                            #172033
                        );
                `;

        conteudo.innerHTML = `
            <div style="
                ${bannerStyle}
                margin: -15px -15px 14px;
                padding: 28px 15px 18px;
                border-radius: 12px 12px 0 0;
            ">
                <img
                    src="${avatar}"
                    alt="Avatar"
                    style="
                        width: 88px;
                        height: 88px;
                        object-fit: cover;
                        border-radius: 50%;
                        border: 3px solid #d4af37;
                        background: #111827;
                    "
                    onerror="
                        this.style.display='none'
                    "
                >

                <h3 style="
                    color: #facc15;
                    margin: 10px 0 3px;
                    font-family: Cinzel, serif;
                ">
                    ${
                        escaparHtml(
                            membro.nome
                        )
                    }
                </h3>

                <div style="color: #e2e8f0;">
                    ${
                        escaparHtml(
                            String(
                                membro.classe ||
                                "Aprendiz"
                            )
                        )
                    }
                    · Nível ${
                        Number(
                            membro.nivel || 1
                        )
                    }
                </div>

                <div style="
                    color: #fbbf24;
                    margin-top: 5px;
                    font-size: 0.86rem;
                ">
                    ${
                        escaparHtml(
                            traduzirCargo(
                                membro.cargo
                            )
                        )
                    }
                </div>
            </div>

            <div style="
                display: grid;
                grid-template-columns:
                    repeat(2, 1fr);
                gap: 7px;
                margin-bottom: 12px;
            ">
                ${cardStatus(
                    "⚔️ Ataque",
                    status.attack
                )}

                ${cardStatus(
                    "🛡️ Defesa",
                    status.defense
                )}

                ${cardStatus(
                    "🏃 Agilidade",
                    status.initiative
                )}

                ${cardStatus(
                    "🍀 Sorte",
                    status.luck
                )}

                ${cardStatus(
                    "❤️ HP",
                    `${
                        membro.hp_atual
                    }/${membro.hp_max}`
                )}

                ${cardStatus(
                    "💙 MP",
                    `${
                        membro.mp_atual
                    }/${membro.mp_max}`
                )}

                ${cardStatus(
                    "💨 Esquiva",
                    `${status.esquiva || 0}%`
                )}

                ${cardStatus(
                    "⚡ Ataque duplo",
                    `${
                        status.ataque_duplo ||
                        0
                    }%`
                )}
            </div>

            <div style="
                text-align: left;
                margin-bottom: 12px;
                padding: 10px;
                border: 1px solid #475569;
                border-radius: 8px;
                background: rgba(
                    15,
                    23,
                    42,
                    0.75
                );
            ">
                <div>
                    <strong>Profissão:</strong>
                    ${
                        escaparHtml(
                            membro.profissao
                                ?.nome ||
                            "Nenhuma"
                        )
                    }
                    ${
                        Number(
                            membro.profissao
                                ?.nivel ||
                            0
                        ) > 0
                            ? `Nv. ${
                                Number(
                                    membro
                                        .profissao
                                        .nivel
                                )
                            }`
                            : ""
                    }
                </div>

                <div style="margin-top: 5px;">
                    <strong>XP contribuído:</strong>
                    ${
                        formatarNumero(
                            membro
                                .contribuicao_xp
                        )
                    }
                </div>

                <div style="margin-top: 5px;">
                    <strong>Ouro doado:</strong>
                    ${
                        formatarNumero(
                            membro
                                .contribuicao_ouro
                        )
                    }
                </div>

                <div style="margin-top: 5px;">
                    <strong>Entrou no clã:</strong>
                    ${
                        escaparHtml(
                            formatarData(
                                membro.entrou_em
                            )
                        )
                    }
                </div>
            </div>

            <h4 style="
                color: #facc15;
                text-align: left;
                margin-bottom: 8px;
            ">
                Equipamentos
            </h4>

            <div>
                ${equipamentosHtml}
            </div>
        `;
    }


    function cardStatus(titulo, valor) {
        return `
            <div style="
                padding: 8px 5px;
                background:
                    rgba(
                        30,
                        41,
                        59,
                        0.9
                    );
                border: 1px solid #475569;
                border-radius: 7px;
            ">
                <div style="
                    color: #94a3b8;
                    font-size: 0.72rem;
                ">
                    ${escaparHtml(titulo)}
                </div>

                <strong style="
                    display: block;
                    color: #f8fafc;
                    margin-top: 3px;
                ">
                    ${escaparHtml(valor)}
                </strong>
            </div>
        `;
    }
    
    // ========================================================
    // 🌍 LISTA PÚBLICA DE CLÃS
    // ========================================================

    async function listarClansPublicos(
        termo = ""
    ) {
        const lista = elemento(
            "cla-lista-publica"
        );

        if (!lista) {
            return;
        }

        lista.innerHTML = `
            <div class="cla-vazio">
                Consultando os clãs de Eldora...
            </div>
        `;

        try {
            const dados = await requisicao(
                `/api/clan/listar?termo=${
                    encodeURIComponent(termo)
                }&limite=30&t=${Date.now()}`
            );

            const clans = Array.isArray(
                dados.clans
            )
                ? dados.clans
                : [];

            if (!clans.length) {
                lista.innerHTML = `
                    <div class="cla-vazio">
                        Nenhum clã encontrado.
                    </div>
                `;

                return;
            }

            lista.innerHTML = clans.map(
                function (clan) {
                    const clanId = escaparHtml(
                        clan.id
                    );

                    const nome = escaparHtml(
                        clan.nome || "Clã"
                    );

                    const tag = escaparHtml(
                        clan.tag || ""
                    );

                    const descricao = escaparHtml(
                        clan.descricao ||
                        "Este clã ainda não possui descrição."
                    );

                    const membros = Number(
                        clan.membros_total || 0
                    );

                    const capacidade = Number(
                        clan.capacidade_membros ||
                        10
                    );

                    const vagaTexto =
                        clan.possui_vaga
                            ? "Possui vagas"
                            : "Clã lotado";

                    return `
                        <div class="cla-item-lista">
                            <div style="
                                display: flex;
                                justify-content: space-between;
                                align-items: flex-start;
                                gap: 10px;
                            ">
                                <div>
                                    <strong style="
                                        color: #facc15;
                                        font-family: Cinzel, serif;
                                    ">
                                        ${nome}
                                    </strong>
    
                                    <span style="
                                        color: #94a3b8;
                                        margin-left: 4px;
                                    ">
                                        [${tag}]
                                    </span>
  
                                    <div style="
                                        color: #cbd5e1;
                                        font-size: 0.82rem;
                                        margin-top: 5px;
                                    ">
                                        ${descricao}
                                    </div>

                                    <div style="
                                        color: #94a3b8;
                                        font-size: 0.78rem;
                                        margin-top: 7px;
                                    ">
                                        Nível ${
                                            Number(
                                                clan.nivel || 1
                                            )
                                        }
                                        · ${membros}/${capacidade}
                                        membros
                                        · ${vagaTexto}
                                    </div>
                                </div>

                                <div class="cla-card-publico-icone">
                                    ${
                                        clan.logo_url
                                            ? `
                                                <img
                                                    src="${
                                                        escaparHtml(
                                                            clan.logo_url
                                                        )
                                                    }"
                                                    alt="Brasão de ${nome}"
                                                    style="
                                                        width: 100%;
                                                        height: 100%;
                                                        object-fit: contain;
                                                        padding: 3px;
                                                    "
                                                    onerror="
                                                        this.style.display='none';
                                                        this.nextElementSibling.style.display='block';
                                                    "
                                                >

                                                <span style="display: none;">
                                                    🛡️
                                                </span>
                                            `
                                            : `
                                                <span>
                                                    🛡️
                                                </span>
                                            `
                                    }
                                </div>
                            </div>

                            <button
                                type="button"
                                class="
                                    cla-btn
                                    cla-btn-secundario
                                    cla-btn-detalhes-publicos
                                "
                                data-clan-id="${clanId}"
                                style="
                                    width: 100%;
                                    margin-top: 9px;
                                "
                            >
                                📜 Ver detalhes
                            </button>
 
                            <div
                                class="cla-detalhes-publicos"
                                data-detalhes-clan="${clanId}"
                                style="display: none;"
                            ></div>
                        </div>
                    `;
                }
            ).join("");

        } catch (erro) {
            lista.innerHTML = "";

            mostrarMensagem(
                erro.message,
                "erro"
            );
        } 
    }


    async function verDetalhesClanPublico(
        clanId,
        botao
    ) {
        const card = botao.closest(
            ".cla-item-lista"
        );

        const area = card?.querySelector(
            ".cla-detalhes-publicos"
        );

        if (!area) {
            return;
        }

        if (area.style.display === "block") {
            area.style.display = "none";
            botao.textContent = "📜 Ver detalhes";
            return;
        }

        area.style.display = "block";

        area.innerHTML = `
            <div class="cla-vazio">
                Consultando detalhes...
            </div>
        `;

        botao.textContent = "Fechar detalhes";

        try {
            const dados = await requisicao(
                `/api/clan/detalhes/${
                    encodeURIComponent(clanId)
                }?t=${Date.now()}`
            );

            const clan = dados.clan || {};

            const membros = Array.isArray(
                clan.membros
            )
                ? clan.membros
                : [];

            const membrosHtml = membros
                .slice(0, 10)
                .map(function (membro) {
                    return `
                        <div style="
                            display: flex;
                            justify-content: space-between;
                            gap: 8px;
                            padding: 6px 0;
                            border-bottom:
                                1px solid rgba(
                                    71,
                                    85,
                                    105,
                                    0.45
                                );
                        ">
                            <span>
                                ${
                                    escaparHtml(
                                        membro.nome ||
                                        "Aventureiro"
                                    )
                                }
                            </span>

                            <span style="
                                color: #fbbf24;
                                font-size: 0.8rem;
                            ">
                                ${
                                    escaparHtml(
                                        membro.cargo_nome ||
                                        traduzirCargo(
                                            membro.cargo
                                        )
                                    )
                                }
                            </span>
                        </div>
                    `;
                })
                .join("");
                 
                const tipoEntrada = String(
                    clan.tipo_entrada || "convite"
                );

                let botaoSolicitarHtml = "";

                if (!clan.possui_vaga) {
                    botaoSolicitarHtml = `
                        <div style="
                            margin-top: 12px;
                            padding: 10px;
                            border-radius: 8px;
                            text-align: center;
                            color: #fca5a5;
                            background:
                                rgba(127, 29, 29, 0.18);
                            border:
                                1px solid rgba(
                                    248,
                                    113,
                                    113,
                                    0.28
                                );
                        ">
                            Este clã está lotado.
                        </div>
                    `;

                } else if (
                    tipoEntrada === "solicitacao"
                ) {
                    botaoSolicitarHtml = `
                        <button
                            type="button"
                            class="
                                cla-btn
                                cla-btn-solicitar-entrada
                            "
                            data-clan-id="${
                                escaparHtml(clanId)
                            }"
                            style="
                                width: 100%;
                                margin-top: 12px;
                            "
                        >
                            📨 Solicitar entrada
                        </button>
                    `;

                } else if (
                    tipoEntrada === "convite"
                ) {
                    botaoSolicitarHtml = `
                        <div style="
                            margin-top: 12px;
                            padding: 10px;
                            border-radius: 8px;
                            text-align: center;
                            color: #cbd5e1;
                            background:
                                rgba(30, 41, 59, 0.58);
                            border:
                                1px solid rgba(
                                    148,
                                    163,
                                    184,
                                    0.24
                                );
                        ">
                            ✉️ Este clã aceita apenas jogadores convidados.
                        </div>
                    `;

                } else {
                    botaoSolicitarHtml = `
                        <div style="
                            margin-top: 12px;
                            padding: 10px;
                            border-radius: 8px;
                            text-align: center;
                            color: #fca5a5;
                            background:
                                rgba(127, 29, 29, 0.18);
                            border:
                                1px solid rgba(
                                    248,
                                    113,
                                    113,
                                    0.28
                                );
                        ">
                            🔒 O recrutamento deste clã está fechado.
                        </div>
                    `;
                }

            area.innerHTML = `
                <div style="
                    margin-top: 10px;
                    padding: 10px;
                    background:
                        rgba(2, 6, 23, 0.65);
                    border:
                        1px solid #475569;
                    border-radius: 8px;
                ">
                    <div style="
                        color: #cbd5e1;
                        font-size: 0.82rem;
                    ">
                        <strong>Entrada:</strong>
                        ${
                            escaparHtml(
                                traduzirTipoEntrada(
                                    tipoEntrada
                                )
                            )
                        }
                    </div>

                    <div style="
                        color: #cbd5e1;
                        font-size: 0.82rem;
                        margin-top: 5px;
                    ">
                        <strong>Nível mínimo:</strong>
                        ${
                            Number(
                                clan.nivel_minimo ||
                                1
                            )
                        }
                    </div>

                    <h4 style="
                        color: #facc15;
                        margin: 12px 0 5px;
                    ">
                        Membros
                    </h4>

                    ${
                        membrosHtml ||
                        `
                            <div style="
                                color: #94a3b8;
                            ">
                                Nenhum membro encontrado.
                            </div>
                        `
                    }

                    ${
                        membros.length > 10
                            ? `
                                <div style="
                                    color: #94a3b8;
                                    font-size: 0.76rem;
                                    margin-top: 8px;
                                    text-align: center;
                                ">
                                    E mais ${
                                        membros.length - 10
                                    } membros...
                                </div>
                            `
                            : ""
                    }

                    ${botaoSolicitarHtml}

                </div>
            `;

        } catch (erro) {
            area.innerHTML = `
                <div style="
                    color: #fecaca;
                    padding: 10px 0;
                ">
                    ${
                        escaparHtml(
                            erro.message
                        )
                    }
                </div>
            `;
        }
    }
    
    async function solicitarEntradaClan(
        clanId,
        botao
    ) {
        const textoOriginal = botao.textContent;

        botao.disabled = true;
        botao.textContent = "Enviando pedido...";

        try {
            const dados = await postJson(
                "/api/clan/solicitar_entrada",
                {
                    user_id: estadoCla.userId,
                    clan_id: clanId
                }
            );

            botao.textContent =
                "✅ Pedido enviado";

            mostrarMensagem(
                dados.message ||
                "Solicitação enviada."
            );

        } catch (erro) {
            botao.disabled = false;
            botao.textContent = textoOriginal;

            mostrarMensagem(
                erro.message,
                "erro"
            );
        }
    }

    // ========================================================
    // ✉️ CONVITES RECEBIDOS
    // ========================================================

    async function listarConvitesRecebidos() {
        const lista = elemento(
            "cla-lista-convites"
        );

        if (!lista) {
            return;
        }

        lista.innerHTML = `
            <div class="cla-vazio">
                Consultando convites...
            </div>
        `;

        try {
            const dados = await requisicao(
                `/api/clan/convites/${
                    encodeURIComponent(
                        estadoCla.userId
                    )
                }?t=${Date.now()}`
            );

            const convites = Array.isArray(
                dados.convites
            )
                ? dados.convites
                : [];

            if (!convites.length) {
                lista.innerHTML = `
                    <div class="cla-vazio">
                        Você não possui convites pendentes.
                    </div>
                `;

                return;
            }

            lista.innerHTML = convites.map(
                function (convite) {
                    const clanId = escaparHtml(
                        convite.clan_id
                    );

                    return `
                        <div class="cla-item-lista">
                            <strong style="
                                color: #facc15;
                            ">
                                ${
                                    escaparHtml(
                                        convite.nome ||
                                        "Clã"
                                    )
                                }
                            </strong>

                            <span style="
                                color: #94a3b8;
                                margin-left: 4px;
                            ">
                                [${
                                    escaparHtml(
                                        convite.tag ||
                                        ""
                                    )
                                }]
                            </span>

                            <div style="
                                color: #cbd5e1;
                                font-size: 0.82rem;
                                margin-top: 6px;
                            ">
                                Nível ${
                                    Number(
                                        convite.nivel ||
                                        1
                                    )
                                }
                                · ${
                                    Number(
                                        convite
                                            .membros_total ||
                                        0
                                    )
                                }/${
                                    Number(
                                        convite
                                            .capacidade_membros ||
                                        10
                                    )
                                } membros
                            </div>

                            <div style="
                                color: #94a3b8;
                                font-size: 0.76rem;
                                margin-top: 5px;
                            ">
                                Expira em:
                                ${
                                    escaparHtml(
                                        formatarData(
                                            convite
                                                .expira_em
                                        )
                                    )
                                }
                            </div>

                            <div style="
                                display: grid;
                                grid-template-columns:
                                    1fr 1fr;
                                gap: 7px;
                                margin-top: 10px;
                            ">
                                <button
                                    type="button"
                                    class="
                                        cla-btn
                                        cla-btn-aceitar-convite
                                    "
                                    data-clan-id="${clanId}"
                                >
                                    ✅ Aceitar
                                </button>

                                <button
                                    type="button"
                                    class="
                                        cla-btn
                                        cla-btn-perigo
                                        cla-btn-recusar-convite
                                    "
                                    data-clan-id="${clanId}"
                                >
                                    ❌ Recusar
                                </button>
                            </div>
                        </div>
                    `;
                }
            ).join("");
  
        } catch (erro) {
            lista.innerHTML = "";
 
            mostrarMensagem(
                erro.message,
                "erro"
            );
        }
    }


    async function aceitarConviteClan(
        clanId
    ) {
        try {
            const dados = await postJson(
                "/api/clan/convite/aceitar",
                {
                    user_id: estadoCla.userId,
                        clan_id: clanId
                }
            );

            mostrarMensagem(
                dados.message ||
                "Você entrou no clã."
            );

            await carregarMeuCla();

        } catch (erro) {
            mostrarMensagem(
                erro.message,
                "erro"
            );
        }
    }


    async function recusarConviteClan(
        clanId
    ) {
        try {
            const dados = await postJson(
                "/api/clan/convite/recusar",
                {
                    user_id: estadoCla.userId,
                    clan_id: clanId
                }
            );

            mostrarMensagem(
                dados.message ||
                "Convite recusado."
            );

            await listarConvitesRecebidos();

        } catch (erro) {
            mostrarMensagem(
                erro.message,
                "erro"
            );
        }
    }

    // ========================================================
    // 🏰 CRIAR CLÃ
    // ========================================================

    async function criarClan(evento) {
        evento.preventDefault();


        const nome = elemento(
            "cla-criar-nome"
        )?.value.trim();


        const tag = elemento(
            "cla-criar-tag"
        )?.value.trim();


        const descricao = elemento(
            "cla-criar-descricao"
        )?.value.trim();


        const custo = Number(
            estadoCla
                .custoCriacaoOuro ||
            5000
        );


        const confirmou =
            await confirmarAcaoCla({
                titulo:
                    "Fundar novo clã",

                mensagem:
                    `Fundar "${nome}" custará ${
                        formatarNumero(
                            custo
                        )
                    } moedas de ouro. Deseja continuar?`,

                confirmarTexto:
                    `🪙 Fundar por ${
                        formatarNumero(
                            custo
                        )
                    }`,

                cancelarTexto:
                    "Cancelar",

                icone:
                    "🏰"
            });


        if (!confirmou) {
            return;
        }


        const botao = elemento(
            "cla-btn-criar"
        );


        if (botao) {
            botao.disabled = true;
            botao.textContent =
                "⏳ Fundando clã...";
        }


        try {
            const dados = await postJson(
                "/api/clan/criar",
                {
                    user_id: estadoCla.userId,
                    nome,
                    tag,
                    descricao
                }
            );

            mostrarMensagem(
                dados.message ||
                "Clã criado com sucesso."
            );

            await carregarMeuCla();

        } catch (erro) {

            mostrarMensagem(
                erro.message,
                "erro"
            );

        } finally {

            if (botao) {
                botao.disabled = false;

                botao.textContent =
                    `🛡️ Fundar clã — ${
                        formatarNumero(
                            custo
                        )
                    } 🪙`;
            }
        }
    }


    // ========================================================
    // 🔍 BUSCAR JOGADORES E CONVIDAR
    // ========================================================

    async function buscarJogadores() {
        const termo = elemento(
            "cla-buscar-jogador"
        )?.value.trim();

        const lista = elemento(
            "cla-resultado-jogadores"
        );

        if (!lista) {
            return;
        }

        if (!termo || termo.length < 2) {
            mostrarMensagem(
                "Digite pelo menos 2 caracteres.",
                "erro"
            );

            return;
        }

        lista.innerHTML = `
            <div class="cla-vazio">
                Procurando heróis...
            </div>
        `;

        try {
            const dados = await requisicao(
                `/api/clan/buscar_jogadores?user_id=${
                    encodeURIComponent(
                        estadoCla.userId
                    )
                }&termo=${
                    encodeURIComponent(
                        termo
                    )
                }`
            );

            const jogadores =
                dados.jogadores || [];

            if (!jogadores.length) {
                lista.innerHTML = `
                    <div class="cla-vazio">
                        Nenhum jogador encontrado.
                    </div>
                `;

                return;
            }

            lista.innerHTML = jogadores
                .map(
                    function (jogador) {
                        return `
                            <div class="cla-item-lista">
                                <strong>
                                    ${
                                        escaparHtml(
                                            jogador.nome
                                        )
                                    }
                                </strong>

                                <div style="
                                    color: #94a3b8;
                                    font-size: 0.8rem;
                                    margin: 4px 0 8px;
                                ">
                                    ${
                                        escaparHtml(
                                            jogador.classe
                                        )
                                    }
                                    · Nível ${
                                        Number(
                                            jogador.level ||
                                            1
                                        )
                                    }
                                </div>

                                <button
                                    type="button"
                                    class="cla-btn
                                           cla-btn-convidar"
                                    data-jogador-id="${
                                        escaparHtml(
                                            jogador.id
                                        )
                                    }"
                                    style="width: 100%;"
                                >
                                    ✉️ Convidar
                                </button>
                            </div>
                        `;
                    }
                )
                .join("");

        } catch (erro) {
            lista.innerHTML = "";

            mostrarMensagem(
                erro.message,
                "erro"
            );
        }
    }


    async function convidarJogador(
        alvoId,
        botao
    ) {
        if (!alvoId) {
            mostrarMensagem(
                "O ID do jogador não foi encontrado.",
                "erro"
            );

            return;
        }

        const textoOriginal =
            botao?.textContent ||
            "✉️ Convidar";

        const card = botao?.closest(
            ".cla-item-lista"
        );

        let status = card?.querySelector(
            ".cla-status-convite"
        );

        if (!status && card) {
            card.insertAdjacentHTML(
                "beforeend",
                `
                    <div
                        class="cla-status-convite"
                        style="
                            display: none;
                            margin-top: 8px;
                            padding: 8px 10px;
                            border-radius: 8px;
                            font-size: 0.74rem;
                            font-weight: 700;
                            text-align: center;
                        "
                    ></div>
                `
            );

            status = card.querySelector(
                ".cla-status-convite"
            );
        }

        if (botao) {
            botao.disabled = true;
            botao.textContent =
                "⏳ Enviando convite...";
        }

        if (status) {
            status.style.display = "block";
            status.style.color = "#cbd5e1";
            status.style.background =
                "rgba(30, 41, 59, 0.75)";
            status.style.border =
                "1px solid rgba(148, 163, 184, 0.25)";
            status.textContent =
                "Enviando convite...";
        }

        try {
            const dados = await postJson(
                "/api/clan/convidar",
                {
                    user_id: estadoCla.userId,
                    alvo_id: alvoId
                }
            );

            const mensagem =
                dados.message ||
                "Convite enviado com sucesso.";

            if (botao) {
                botao.disabled = true;
                botao.textContent =
                    "✅ Convite enviado";
            }

            if (status) {
                status.style.display = "block";
                status.style.color = "#dcfce7";
                status.style.background =
                    "rgba(20, 83, 45, 0.55)";
                status.style.border =
                    "1px solid rgba(74, 222, 128, 0.40)";
                status.textContent = mensagem;
            }

            mostrarMensagem(mensagem);

        } catch (erro) {
            const mensagem =
                erro.message ||
                "Não foi possível enviar o convite.";

            if (botao) {
                botao.disabled = false;
                botao.textContent =
                    textoOriginal;
            }
   
             if (status) {
                status.style.display = "block";
                status.style.color = "#fee2e2";
                status.style.background =
                    "rgba(127, 29, 29, 0.55)";
                status.style.border =
                    "1px solid rgba(248, 113, 113, 0.42)";
                status.textContent = mensagem;
            }

            mostrarMensagem(
                mensagem,
                "erro"
            );

            console.error(
                "❌ Erro ao convidar jogador:",
                erro
            );
        }
    }

    // ========================================================
    // 🎨 LOGOS DO CLÃ
    // ========================================================

    async function carregarCatalogoLogos(
        logoAtualId
    ) {
        const grade = elemento(
            "cla-logo-grade"
        );

        if (!grade) {
            return;
        }

        estadoCla.logoSelecionada =
            logoAtualId || null;

        grade.innerHTML = `
            <div class="cla-vazio">
                Carregando brasões...
            </div>
        `;

        try {
            if (!estadoCla.logos.length) {
                const dados = await requisicao(
                    `/api/clan/logos?t=${Date.now()}`
                );

                estadoCla.logos = Array.isArray(
                    dados.logos
                )
                    ? dados.logos
                    : [];
            }

            renderizarCatalogoLogos();

        } catch (erro) {
            grade.innerHTML = "";

            mostrarMensagem(
                erro.message,
                "erro"
            );
        }
    }


    function renderizarCatalogoLogos() {
        const grade = elemento(
            "cla-logo-grade"
        );

        const btnSalvar = elemento(
            "cla-btn-salvar-logo"
        );

        if (!grade) {
            return;
        }

        if (!estadoCla.logos.length) {
            grade.innerHTML = `
                <div class="cla-vazio">
                    Nenhuma logo cadastrada.
                </div>
            `;

            return;
        }

        grade.innerHTML = estadoCla.logos
            .map(function (logo) {
                const ativa =
                    String(logo.id) ===
                    String(
                        estadoCla.logoSelecionada
                    );

                return `
                    <button
                        type="button"
                        class="
                            cla-logo-opcao
                            ${ativa ? "active" : ""}
                        "
                        data-logo-id="${
                            escaparHtml(logo.id)
                        }"
                    >
                        <img
                            src="${
                                escaparHtml(logo.url)
                            }"
                            alt="${
                                escaparHtml(logo.nome)
                            }"
                        >

                        <span>
                            ${
                                escaparHtml(logo.nome)
                            }
                        </span>
                    </button>
                `;
            })
            .join("");

        if (btnSalvar) {
            btnSalvar.disabled =
                !estadoCla.logoSelecionada ||
                String(
                    estadoCla.logoSelecionada
                ) ===
                String(
                    estadoCla.clan?.logo_id
                );
        }
    }


    async function salvarLogoClan() {
        const logoId =
            estadoCla.logoSelecionada;

        if (!logoId) {
            mostrarMensagem(
                "Selecione uma logo.",
                "erro"
            );

            return;
        }

        try {
            const dados = await postJson(
                "/api/clan/alterar_logo",
                {
                    user_id: estadoCla.userId,
                    logo_id: logoId
                }
            );

            mostrarMensagem(
                dados.message ||
                "Logo alterada com sucesso."
            );

            await carregarMeuCla();

        } catch (erro) {
            mostrarMensagem(
                erro.message,
                "erro"
            );
        }
    }

    // ========================================================
    // 💰 TESOURO E EVOLUÇÃO
    // ========================================================
    function prepararTesouroClan(
        membros,
        tesouro
    ) {
        const area = elemento(
            "cla-area-administrar-tesouro"
        );

        const seletor = elemento(
            "cla-tesouro-destinatario"
        );

        const saldo = Number(
            tesouro?.ouro || 0
        );


        preencherTexto(
            "cla-tesouro-saldo",
            `${formatarNumero(saldo)} 🪙`
        );

        // ====================================================
        // 💼 LICENÇA DA TESOURARIA
        // ====================================================

        const tesouraria =
            estadoCla.clan
                ?.tesouraria ||
            {};


        const tesourariaAtiva =
            Boolean(
                tesouraria.ativa
            );


        const custoTesouraria =
            Number(
                tesouraria.custo_gemas ||
                100
            );


        const duracaoTesouraria =
            Number(
                tesouraria.duracao_dias ||
                30
            );


        const statusTesouraria =
            elemento(
                "cla-tesouraria-status"
            );


        const seloTesouraria =
            elemento(
                "cla-tesouraria-selo"
            );


        const infoCompra =
            elemento(
                "cla-tesouraria-compra-info"
            );


        const btnComprar =
            elemento(
                "cla-btn-comprar-tesouraria"
            );


        if (tesourariaAtiva) {

            const validade =
                tesouraria.expira_em
                    ? formatarDataHora(
                        tesouraria.expira_em
                    )
                    : "";


            if (statusTesouraria) {
                statusTesouraria.innerHTML = `
                    ✅ Tesouraria ativa
                    ${
                        validade
                            ? `<br>Validade: ${
                                escaparHtml(
                                    validade
                                )
                            }`
                            : ""
                    }

                    ${
                        Number(
                            tesouraria.dias_restantes ||
                            0
                        ) > 0
                            ? `
                                <br>⏳ Restam aproximadamente
                                <strong>
                                    ${
                                        Number(
                                            tesouraria
                                                .dias_restantes
                                        )
                                    } dia(s)
                                </strong>
                            `
                            : ""
                    }
                `;
            }


            if (seloTesouraria) {
                seloTesouraria.textContent =
                    "ATIVA";

                seloTesouraria.style.color =
                    "#bbf7d0";

                seloTesouraria.style.background =
                    "rgba(20,83,45,.25)";

                seloTesouraria.style.border =
                    "1px solid rgba(74,222,128,.30)";
            }


            if (infoCompra) {
                infoCompra.textContent =
                    "Os cargos autorizados podem administrar o tesouro.";
            }


            if (btnComprar) {
                btnComprar.style.display =
                    "none";
            }

        } else {

            if (statusTesouraria) {
                statusTesouraria.innerHTML =
                    `
                        🔒 A administração do ouro
                        está bloqueada até que o
                        líder ative a licença.
                    `;
            }


            if (seloTesouraria) {
                seloTesouraria.textContent =
                    "INATIVA";

                seloTesouraria.style.color =
                    "#fecaca";

                seloTesouraria.style.background =
                    "rgba(127,29,29,.22)";

                seloTesouraria.style.border =
                    "1px solid rgba(248,113,113,.25)";
            }


            if (infoCompra) {
                infoCompra.innerHTML = `
                    💎
                    <strong>
                        ${formatarNumero(
                            custoTesouraria
                        )} Gemas
                    </strong>
                    ·
                    ⏳
                    ${formatarNumero(
                        duracaoTesouraria
                    )} dias
                `;
            }


            if (btnComprar) {
                btnComprar.style.display =
                    souLiderReal()
                        ? "flex"
                        : "none";

                btnComprar.textContent =
                    `💎 Ativar por ${formatarNumero(
                        custoTesouraria
                    )} Gemas`;
            }
        }        

        const podeAdministrar =
            tesourariaAtiva &&
            (
                souLiderReal() ||
                temPermissaoCla(
                    "gerenciar_tesouro"
                )
            );


        if (area) {
            area.style.display =
                podeAdministrar
                    ? "block"
                    : "none";
        }


        if (!seletor) {
            return;
        }


        if (!podeAdministrar) {
            seletor.innerHTML = `
                <option value="">
                    Selecione um membro
                </option>
            `;

            return;
        }


        const listaMembros =
            Array.isArray(membros)
                ? [...membros]
                : [];


        listaMembros.sort(
            function (a, b) {
                return String(
                    a?.nome || ""
                ).localeCompare(
                    String(
                        b?.nome || ""
                    ),
                    "pt-BR"
                );
            }
        );


        seletor.innerHTML = `
            <option value="">
                Selecione um membro
            </option>

            ${
                listaMembros
                    .map(
                        function (membro) {
                            const membroId =
                                escaparHtml(
                                    membro?.user_id ||
                                    ""
                                );

                            const nome =
                                escaparHtml(
                                    membro?.nome ||
                                    "Aventureiro"
                                );

                            const cargo =
                                escaparHtml(
                                    traduzirCargo(
                                        membro?.cargo ||
                                        "membro"
                                    )
                                );

                            const souEu =
                                String(
                                    membro?.user_id ||
                                    ""
                                ) ===
                                String(
                                    estadoCla.userId ||
                                    ""
                                );


                            return `
                                <option
                                    value="${membroId}"
                                >
                                    ${nome}
                                    ${souEu ? " (você)" : ""}
                                    — ${cargo}
                                </option>
                            `;
                        }
                    )
                    .join("")
            }
        `;
    }

    async function comprarTesourariaClan() {

        if (!souLiderReal()) {
            mostrarMensagem(
                "Somente o líder pode ativar "
                + "a Tesouraria.",
                "erro"
            );

            return;
        }


        const tesouraria =
            estadoCla.clan
                ?.tesouraria ||
            {};


        if (tesouraria.ativa) {
            mostrarMensagem(
                "A Tesouraria já está ativa.",
                "erro"
            );

            return;
        }


        const custo =
            Number(
                tesouraria.custo_gemas ||
                100
            );


        const confirmou =
            await confirmarAcaoCla({
                titulo:
                    "Ativar Tesouraria",

                mensagem:
                    `Deseja gastar ${formatarNumero(
                        custo
                    )} Gemas para liberar a administração do tesouro por 30 dias?`,

                confirmarTexto:
                    `💎 Ativar por ${formatarNumero(
                        custo
                    )} Gemas`,

                cancelarTexto:
                    "Cancelar",

                icone:
                    "💼"
            });


        if (!confirmou) {
            return;
        }


        const botao = elemento(
            "cla-btn-comprar-tesouraria"
        );


        if (botao) {
            botao.disabled = true;
            botao.textContent =
                "⏳ Ativando Tesouraria...";
        }


        try {

            const dados = await postJson(
                "/api/clan/tesouraria/comprar",
                {
                    user_id:
                        estadoCla.userId
                }
            );


            mostrarMensagem(
                dados.message ||
                "Tesouraria ativada!"
            );


            await carregarMeuCla();


            trocarAba(
                "tesouro",
                false
            );


        } catch (erro) {

            mostrarMensagem(
                erro.message,
                "erro"
            );


        } finally {

            if (botao) {
                botao.disabled = false;
            }
        }
    }

    async function enviarOuroTesouro() {
        if (
            !souLiderReal() &&
            !temPermissaoCla(
                "gerenciar_tesouro"
            )
        ) {
            mostrarMensagem(
                "Seu cargo não permite administrar "
                + "o tesouro do clã.",
                "erro"
            );

            return;
        }


        const seletor = elemento(
            "cla-tesouro-destinatario"
        );

        const campoQuantidade = elemento(
            "cla-tesouro-quantidade"
        );

        const botao = elemento(
            "cla-btn-enviar-ouro-tesouro"
        );


        const alvoId = String(
            seletor?.value || ""
        ).trim();

        const quantidade =
            Number.parseInt(
                campoQuantidade?.value ||
                "0",
                10
            );


        if (!alvoId) {
            mostrarMensagem(
                "Selecione o membro que receberá "
                + "o ouro.",
                "erro"
            );

            return;
        }


        if (
            !Number.isInteger(
                quantidade
            ) ||
            quantidade <= 0
        ) {
            mostrarMensagem(
                "Informe uma quantidade válida "
                + "de ouro.",
                "erro"
            );

            return;
        }


        const saldoAtual = Number(
            estadoCla.clan
                ?.tesouro
                ?.ouro ||
            0
        );


        if (
            quantidade >
            saldoAtual
        ) {
            mostrarMensagem(
                "O tesouro do clã não possui "
                + "ouro suficiente.",
                "erro"
            );

            return;
        }


        const membros = Array.isArray(
            estadoCla.clan?.membros
        )
            ? estadoCla.clan.membros
            : [];


        const destinatario =
            membros.find(
                function (membro) {
                    return (
                        String(
                            membro?.user_id ||
                            ""
                        ) === alvoId
                    );
                }
            );


        const nomeDestinatario =
            destinatario?.nome ||
            "o membro selecionado";


        const confirmou =
            await confirmarAcaoCla({
                titulo:
                    "Enviar ouro do tesouro",

                mensagem:
                    `Enviar ${formatarNumero(
                        quantidade
                    )} moedas para ${nomeDestinatario}?`,

                confirmarTexto:
                    "💰 Enviar ouro",

                cancelarTexto:
                    "Cancelar",

                icone:
                    "💰"
            });


        if (!confirmou) {
            return;
        }


        const textoOriginal =
            botao?.textContent ||
            "💰 Enviar ouro";


        if (botao) {
            botao.disabled = true;
            botao.textContent =
                "Enviando ouro...";
        }


        try {
            const dados = await postJson(
                "/api/clan/tesouro/enviar",
                {
                    user_id:
                        estadoCla.userId,

                    alvo_id:
                        alvoId,
  
                    quantidade
                }
            );


            mostrarMensagem(
                dados.message ||
                "Ouro enviado com sucesso."
            );


            if (campoQuantidade) {
                campoQuantidade.value = "";
            }


            await carregarMeuCla();
 
            trocarAba(
                "tesouro",
                false
            );


        } catch (erro) {
            mostrarMensagem(
                erro.message,
                "erro"
            );

        } finally {
            if (botao) {
                botao.disabled = false;
                botao.textContent =
                    textoOriginal;
            }
        }
    }

    async function doarOuro() {
        const quantidade = Number(
            elemento(
                "cla-doacao-ouro"
            )?.value || 0
        );

        if (quantidade <= 0) {
            mostrarMensagem(
                "Informe uma quantidade válida.",
                "erro"
            );

            return;
        }

        try {
            const dados = await postJson(
                "/api/clan/doar_ouro",
                {
                    user_id: estadoCla.userId,
                    quantidade
                }
            );

            mostrarMensagem(
                dados.message ||
                "Doação realizada."
            );

            await carregarMeuCla();

        } catch (erro) {
            mostrarMensagem(
                erro.message,
                "erro"
            );
        }
    }

    async function salvarConfiguracoesClan() {
        const campoDescricao = elemento(
            "cla-config-descricao"
        );

        const campoTipoEntrada = elemento(
            "cla-config-tipo-entrada"
        );

        const campoNivelMinimo = elemento(
            "cla-config-nivel-minimo"
        );

        const botaoSalvar = elemento(
            "cla-btn-salvar-configuracoes"
        );

        if (
            !campoDescricao ||
            !campoTipoEntrada ||
            !campoNivelMinimo
        ) {
            mostrarMensagem(
                "A área de configurações não foi encontrada.",
                "erro"
            );

            return;
        }

        const descricao =
            campoDescricao.value.trim();

        const tipoEntrada =
            campoTipoEntrada.value;

        const nivelMinimo = Number.parseInt(
            campoNivelMinimo.value,
            10
        );

        if (descricao.length > 300) {
            mostrarMensagem(
                "A descrição pode ter no máximo 300 caracteres.",
                "erro"
            );

            return;
        }

        if (
            ![
                "solicitacao",
                "convite",
                "fechado"
            ].includes(tipoEntrada)
        ) {
            mostrarMensagem(
                "A política de recrutamento é inválida.",
                "erro"
            );

            return;
        }

        if (
            !Number.isInteger(nivelMinimo) ||
            nivelMinimo < 1 ||
            nivelMinimo > 999
        ) {
            mostrarMensagem(
                "O nível mínimo precisa estar entre 1 e 999.",
                "erro"
            );

            return;
        }

        if (botaoSalvar) {
            botaoSalvar.disabled = true;
            botaoSalvar.textContent =
                "Salvando configurações...";
        }

        try {
            const dados = await postJson(
                "/api/clan/configuracoes",
                {
                    user_id: estadoCla.userId,
                    descricao,
                    tipo_entrada: tipoEntrada,
                    nivel_minimo: nivelMinimo
                }
            );

            mostrarMensagem(
                dados.message ||
                "Configurações atualizadas."
            );

            await carregarMeuCla();

            trocarAba("configuracoes");

        } catch (erro) {
            mostrarMensagem(
                erro.message,
                "erro"
            );

        } finally {
            if (botaoSalvar) {
                botaoSalvar.disabled = false;
                botaoSalvar.textContent =
                    "💾 Salvar configurações";
            }
        }
    }

    async function melhorarClan() {
        try {
            const dados = await postJson(
                "/api/clan/melhorar",
                {
                    user_id: estadoCla.userId
                }
            );

            mostrarMensagem(
                dados.message ||
                "Clã melhorado."
            );

            await carregarMeuCla();

        } catch (erro) {
            mostrarMensagem(
                erro.message,
                "erro"
            );
        }
    }


    async function sairClan() {
        const confirmou =
            await confirmarAcaoCla({
                titulo:
                    "Sair do clã",

                mensagem:
                    "Deseja realmente sair do clã?",

                confirmarTexto:
                    "🚪 Sair",

                icone:
                    "🚪",

                perigo:
                    true
            });

        if (!confirmou) {
            return;
        }

        try {
            const dados = await postJson(
                "/api/clan/sair",
                {
                    user_id: estadoCla.userId
                }
            );

            mostrarMensagem(
                dados.message ||
                "Você saiu do clã."
            );

            await carregarMeuCla();

        } catch (erro) {
            mostrarMensagem(
                erro.message,
                "erro"
            );
        }
    }


    async function dissolverClan() {
        const nome = estadoCla.clan?.nome ||
            "este clã";

        const confirmou =
            await confirmarAcaoCla({
                titulo:
                    "Dissolver clã",

                mensagem:
                    `Deseja realmente dissolver ${nome}?`,

                confirmarTexto:
                    "Continuar",

                icone:
                    "💀",

                perigo:
                    true
            });

        if (!confirmou) {
            return;
        }

        const confirmouNovamente =
            await confirmarAcaoCla({
                titulo:
                    "Última confirmação",

                mensagem:
                    "Todos os membros serão removidos e o clã será dissolvido.",

                confirmarTexto:
                    "💀 Dissolver clã",

                icone:
                    "⚠️",

                perigo:
                    true
            });

        if (!confirmouNovamente) {
            return;
        }

        try {
            const dados = await postJson(
                "/api/clan/dissolver",
                {
                    user_id: estadoCla.userId
                }
            );

            mostrarMensagem(
                dados.message ||
                "O clã foi dissolvido."
            );

            await carregarMeuCla();

        } catch (erro) {
            mostrarMensagem(
                erro.message,
                "erro"
            );
        }
    }


    // ========================================================
    // 📑 ABAS
    // ========================================================

    function trocarAba(
        aba,
        reposicionar = true
    ) {
        document
            .querySelectorAll(
                ".cla-tab-conteudo"
            )
            .forEach(function (conteudoAba) {
                conteudoAba.style.display =
                    "none";
            });

        document
            .querySelectorAll(
                ".cla-aba-btn"
            )
            .forEach(function (botaoAba) {
                botaoAba.classList.remove(
                    "active"
                );
            });

        const conteudo = elemento(
            `cla-tab-${aba}`
        );

        const botao = document.querySelector(
            `[data-cla-tab="${aba}"]`
        );

        if (conteudo) {
            conteudo.style.display = "block";
        }

        if (botao) {
            botao.classList.add("active");
        }


        // ================================================
        // 🏅 LOJA DO CLÃ
        // ================================================

        if (
            aba === "loja"
        ) {
            carregarLojaCla();
        }


        /*
         * Centraliza horizontalmente a aba ativa.
         */
        const barraAbas = elemento(
            "cla-abas"
        );

        if (barraAbas && botao) {
            const destinoHorizontal =
                botao.offsetLeft -
                (
                    barraAbas.clientWidth -
                    botao.offsetWidth
                ) / 2;

            barraAbas.scrollTo({
                left: Math.max(
                    0,
                    destinoHorizontal
                ), 
                behavior: "smooth"
            });
        }

        if (
            !reposicionar ||
            !conteudo
        ) {
            return;
        }

        /*
         * Reposiciona a rolagem vertical para
         * mostrar o começo da aba abaixo da
         * barra fixa.
         */
        requestAnimationFrame(function () {
            const areaRolagem = elemento(
                "cla-conteudo-scroll"
            );

            const barra = elemento(
                "cla-abas"
            );

            if (
                !areaRolagem ||
                !barra
            ) {
                return;
            }

            const areaRect =
                areaRolagem.getBoundingClientRect();

            const conteudoRect =
                conteudo.getBoundingClientRect();

            const destinoVertical =
                areaRolagem.scrollTop +
                (
                    conteudoRect.top -
                    areaRect.top
                ) -
                barra.offsetHeight -
                10;

            areaRolagem.scrollTo({
                top: Math.max(
                    0,
                    destinoVertical
                ),
                behavior: "smooth"
            });
        });
    }


    // ========================================================
    // 🔌 EVENTOS
    // ========================================================

    function instalarEventos() {
        elemento("cla-form-criar")
            ?.addEventListener(
                "submit",
                criarClan
            );

        elemento("cla-btn-buscar-jogador")
            ?.addEventListener(
                "click",
                buscarJogadores
            );

        elemento("cla-btn-doar-ouro")
            ?.addEventListener(
                "click",
                doarOuro
            );

        elemento(
            "cla-btn-comprar-tesouraria"
        )?.addEventListener(
            "click",
            comprarTesourariaClan
        );

        elemento(
            "cla-btn-enviar-ouro-tesouro"
        )?.addEventListener(
            "click",
            enviarOuroTesouro
        );

        elemento("cla-btn-melhorar")
            ?.addEventListener(
                "click",
                melhorarClan
            );

        elemento("cla-btn-sair")
            ?.addEventListener(
                "click",
                sairClan
            );

        elemento("cla-btn-dissolver")
            ?.addEventListener(
                "click",
                dissolverClan
            );

        elemento("cla-btn-mostrar-criacao")
            ?.addEventListener(
                "click",
                function () {
                    mostrarAreaSemClan(
                        "cla-area-criacao"
                    );
                }
            );

        document
            .querySelectorAll(
                ".cla-aba-btn"
            )
            .forEach(
                function (botao) {
                    botao.addEventListener(
                        "click",
                        function () {
                            trocarAba(
                                botao.dataset
                                    .claTab
                            );
                        }
                    );
                }
            );
        
        elemento("cla-config-tipo-entrada")
            ?.addEventListener(
                "change",
                function (evento) {
                    atualizarExplicacaoRecrutamento(
                        evento.target.value
                    );
                }
            );


        elemento(
            "cla-btn-salvar-configuracoes"
        )?.addEventListener(
            "click",
            salvarConfiguracoesClan
        );

        elemento("cla-logo-grade")
            ?.addEventListener(
                "click",
                function (evento) {
                    const opcao =
                        evento.target.closest(
                            ".cla-logo-opcao"
                        );

                    if (!opcao) {
                        return;
                    }

                    estadoCla.logoSelecionada =
                        opcao.dataset.logoId;

                    document
                        .querySelectorAll(
                            "#cla-logo-grade .cla-logo-opcao"
                        )
                        .forEach(function (item) {
                            item.classList.remove(
                                "active"
                            );
                        });

                    opcao.classList.add("active");
  
                    const btnSalvar = elemento(
                        "cla-btn-salvar-logo"
                    );

                    if (btnSalvar) {
                        btnSalvar.disabled =
                            String(
                                estadoCla.logoSelecionada
                            ) ===
                            String(
                                estadoCla.clan?.logo_id
                            );
                    }
                }
            );


        elemento("cla-btn-salvar-logo")
            ?.addEventListener(
                "click",
                salvarLogoClan
            );
        
        elemento("cla-btn-salvar-cargo")
            ?.addEventListener(
                "click",
                salvarCargoClan
            );


        elemento("cla-btn-cancelar-cargo")
            ?.addEventListener(
                "click",
                resetarFormularioCargo
            );


        elemento("cla-lista-cargos")
            ?.addEventListener(
                "click",
                function (evento) {
                    const btnEditar =
                        evento.target.closest(
                            ".cla-btn-editar-cargo"
                        );

                    if (btnEditar) {
                        editarCargoNoFormulario(
                            btnEditar.dataset
                                .cargoId
                        );

                        return;
                    }


                    const btnExcluir =
                        evento.target.closest(
                            ".cla-btn-excluir-cargo"
                        );

                    if (btnExcluir) {
                        excluirCargoClan(
                            btnExcluir.dataset
                                .cargoId
                        );
                    }
                }
            );

        elemento("cla-lista-membros")
            ?.addEventListener(
                "click",
                function (evento) {
                    const btnInspecionar =
                        evento.target.closest(
                            ".cla-btn-inspecionar"
                        );

                    if (btnInspecionar) {
                        window
                            .abrirInspecaoMembroCla(
                                btnInspecionar.dataset
                                    .membroId
                            );

                        return;
                    }

                    const btnCargo =
                        evento.target.closest(
                            ".cla-btn-alterar-cargo"
                        );

                    if (btnCargo) {
                        const card = btnCargo.closest(
                            ".cla-item-lista"
                        );

                        const select = card?.querySelector(
                            ".cla-select-cargo"
                        );

                        if (!select) {
                            return;
                        }

                        alterarCargoMembro(
                            btnCargo.dataset.membroId,
                            select.value
                        );

                        return;
                    }

                    const btnExpulsar =
                        evento.target.closest(
                            ".cla-btn-expulsar-membro"
                        );

                    if (btnExpulsar) {
                        expulsarMembroClan(
                            btnExpulsar.dataset.membroId,
                            btnExpulsar.dataset.membroNome
                        );

                        return;
                    }

                    const btnTransferir =
                        evento.target.closest(
                            ".cla-btn-transferir-lideranca"
                        );

                    if (btnTransferir) {
                        transferirLiderancaClan(
                            btnTransferir.dataset.membroId,
                            btnTransferir.dataset.membroNome
                        );
                    }
                }
            );
        
        elemento("cla-btn-listar-publicos")
            ?.addEventListener(
                "click",
                function () {
                    mostrarAreaSemClan(
                        "cla-area-lista-publica"
                    );

                    listarClansPublicos();
                }
            );


        elemento("cla-busca-publica")
            ?.addEventListener(
                "input",
                function (evento) {
                    clearTimeout(
                        window.__claBuscaPublicaTimer
                    );

                    const termo =
                        evento.target.value.trim();

                    window.__claBuscaPublicaTimer =
                        setTimeout(
                            function () {
                                listarClansPublicos(
                                    termo
                                );
                            },
                            400
                        );
                }
            );


        elemento("cla-lista-publica")
            ?.addEventListener(
                "click",
                function (evento) {
                    const btnSolicitar =
                        evento.target.closest(
                            ".cla-btn-solicitar-entrada"
                        );

                    if (btnSolicitar) {
                        solicitarEntradaClan(
                            btnSolicitar.dataset.clanId,
                            btnSolicitar
                        );

                        return;
                    }

                    const btnDetalhes =
                        evento.target.closest(
                            ".cla-btn-detalhes-publicos"
                        );

                    if (btnDetalhes) {
                        verDetalhesClanPublico(
                            btnDetalhes.dataset.clanId,
                            btnDetalhes
                        );
                    }
                }
            );  
        
        elemento("cla-tab-convites")
            ?.addEventListener(
                "click",
                function (evento) {
                    const btnAceitar =
                        evento.target.closest(
                            ".cla-btn-aceitar-solicitacao"
                        );

                    if (btnAceitar) {
                        aceitarSolicitacaoClan(
                            btnAceitar.dataset.userId
                        );

                        return;
                    }

                    const btnRecusar =
                        evento.target.closest(
                            ".cla-btn-recusar-solicitacao"
                        );

                    if (btnRecusar) {
                        recusarSolicitacaoClan(
                            btnRecusar.dataset.userId
                        );
                    }
                }
            );

        elemento("cla-btn-ver-convites")
            ?.addEventListener(
                "click",
                function () {
                    mostrarAreaSemClan(
                        "cla-area-convites"
                    );

                    listarConvitesRecebidos();
                }
            );


        elemento("cla-lista-convites")
            ?.addEventListener(
                "click",
                function (evento) {
                    const btnAceitar =
                        evento.target.closest(
                            ".cla-btn-aceitar-convite"
                        );

                    if (btnAceitar) {
                        aceitarConviteClan(
                            btnAceitar.dataset.clanId
                        );

                        return;
                    }

                    const btnRecusar =
                        evento.target.closest(
                            ".cla-btn-recusar-convite"
                        );

                    if (btnRecusar) {
                        recusarConviteClan(
                            btnRecusar.dataset.clanId
                        );
                    }
                }
            );

        elemento(
            "cla-resultado-jogadores"
        )?.addEventListener(
            "click",
            function (evento) {
                const botao =
                    evento.target.closest(
                        ".cla-btn-convidar"
                    );

                if (!botao) {
                    return;
                }

                convidarJogador(
                    botao.dataset.jogadorId,
                    botao
                );
            }
        );
    }


    if (
        document.readyState === "loading"
    ) {
        document.addEventListener(
            "DOMContentLoaded",
            instalarEventos
        );
    } else {
        instalarEventos();
    }

})();