// ============================================================
// 💎 MUNDO DE ELDORA - LOJA PREMIUM
// ============================================================

(() => {

    const estadoLojaPremium = {
        catalogo: null,
        carregandoCatalogo: false,
        carregandoPedidos: false,
        criandoPedido: false,

        codigoPedidoCheckout: null,
        enviandoComprovante: false,
    };


    // =========================================================
    // 🔧 HELPERS
    // =========================================================

    function obterUserIdLojaPremium() {

        const userId = localStorage.getItem(
            "jogadorEldoraID"
        );


        if (
            !userId ||
            userId === "undefined" ||
            userId === "null"
        ) {
            return null;
        }


        return userId;
    }


    function escaparHtml(valor) {

        return String(
            valor ?? ""
        )
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
    }


    function formatarNumero(valor) {

        const numero = Number(
            valor || 0
        );


        return new Intl.NumberFormat(
            "pt-BR"
        ).format(
            numero
        );
    }


    function formatarData(valor) {

        if (!valor) {
            return "";
        }


        try {

            const data = new Date(
                valor
            );


            return data.toLocaleString(
                "pt-BR",
                {
                    day: "2-digit",
                    month: "2-digit",
                    year: "numeric",
                    hour: "2-digit",
                    minute: "2-digit",
                }
            );

        } catch (erro) {

            return "";
        }
    }


    function mostrarMensagemLojaPremium(
        texto,
        tipo = "info"
    ) {

        const box = document.getElementById(
            "loja-premium-mensagem"
        );


        if (!box) {
            return;
        }


        box.textContent = texto;
        box.style.display = "block";


        if (tipo === "erro") {

            box.style.color = "#fecaca";
            box.style.background =
                "rgba(127, 29, 29, 0.34)";

            box.style.border =
                "1px solid rgba(248, 113, 113, 0.35)";

        } else if (tipo === "sucesso") {

            box.style.color = "#bbf7d0";
            box.style.background =
                "rgba(20, 83, 45, 0.34)";

            box.style.border =
                "1px solid rgba(74, 222, 128, 0.30)";

        } else {

            box.style.color = "#ddd6fe";
            box.style.background =
                "rgba(76, 29, 149, 0.24)";

            box.style.border =
                "1px solid rgba(167, 139, 250, 0.26)";
        }


        clearTimeout(
            window.__eldoraTimerMensagemLoja
        );


        window.__eldoraTimerMensagemLoja =
            setTimeout(
                () => {

                    if (box) {
                        box.style.display = "none";
                    }

                },
                4500
            );
    }


    // =========================================================
    // 🪟 ABRIR / FECHAR
    // =========================================================

    window.abrirLojaPremium = async function() {

        const modal = document.getElementById(
            "loja-premium-modal"
        );


        if (!modal) {

            console.error(
                "❌ loja-premium-modal não encontrado."
            );

            return;
        }


        if (
            typeof window.ocultarMenuGlobalEldora
            === "function"
        ) {

            window.ocultarMenuGlobalEldora();

        } else if (
            typeof fecharMenu === "function"
        ) {

            fecharMenu();
        }


        modal.style.display = "flex";


        mudarAbaLojaPremium(
            "pacotes"
        );


        await carregarCatalogoLojaPremium();
    };


    window.fecharLojaPremium = function() {

        const modal = document.getElementById(
            "loja-premium-modal"
        );


        if (modal) {
            modal.style.display = "none";
        }


        if (
            typeof window.mostrarMenuGlobalEldora
            === "function"
        ) {

            window.mostrarMenuGlobalEldora();
        }
    };


    // =========================================================
    // 📑 ABAS
    // =========================================================

    function mudarAbaLojaPremium(
        aba
    ) {

        document
            .querySelectorAll(
                ".loja-premium-aba"
            )
            .forEach(
                botao => {

                    botao.classList.toggle(
                        "active",
                        botao.dataset
                            .lojaPremiumAba
                            === aba
                    );
                }
            );


        document
            .querySelectorAll(
                ".loja-premium-conteudo"
            )
            .forEach(
                conteudo => {

                    conteudo.classList.remove(
                        "active"
                    );
                }
            );


        const alvo = document.getElementById(
            `loja-premium-aba-${aba}`
        );


        if (alvo) {
            alvo.classList.add(
                "active"
            );
        }


        if (aba === "pedidos") {
            carregarPedidosLojaPremium();
        }
    }


    // =========================================================
    // 🛍️ CATÁLOGO
    // =========================================================

    async function carregarCatalogoLojaPremium() {

        if (
            estadoLojaPremium
                .carregandoCatalogo
        ) {
            return;
        }


        const userId =
            obterUserIdLojaPremium();


        if (!userId) {

            mostrarMensagemLojaPremium(
                "Herói não encontrado.",
                "erro"
            );

            return;
        }


        const carregando =
            document.getElementById(
                "loja-premium-carregando"
            );


        const grade =
            document.getElementById(
                "loja-premium-pacotes"
            );


        if (carregando) {

            carregando.style.display =
                "block";

            carregando.textContent =
                "✨ Consultando o Tesouro Real...";
        }


        if (grade) {
            grade.innerHTML = "";
        }


        estadoLojaPremium
            .carregandoCatalogo = true;


        try {

            const resposta = await fetch(
                `/api/premium/catalogo/${encodeURIComponent(userId)}?t=${Date.now()}`,
                {
                    method: "GET",
                    cache: "no-store",
                }
            );


            const dados =
                await resposta.json();


            if (
                !resposta.ok ||
                !dados.success
            ) {

                throw new Error(
                    dados.error ||
                    "Não foi possível carregar a loja."
                );
            }


            estadoLojaPremium.catalogo =
                dados;


            atualizarCabecalhoLojaPremium(
                dados.jogador
            );


            renderizarPacotesLojaPremium(
                dados.pacotes || []
            );


            if (carregando) {

                carregando.style.display =
                    "none";
            }


        } catch (erro) {

            console.error(
                "❌ [LOJA PREMIUM]",
                erro
            );


            if (carregando) {

                carregando.style.display =
                    "block";

                carregando.textContent =
                    "❌ Não foi possível carregar a Loja de Eldora.";
            }


            mostrarMensagemLojaPremium(
                erro.message,
                "erro"
            );


        } finally {

            estadoLojaPremium
                .carregandoCatalogo = false;
        }
    }


    function atualizarCabecalhoLojaPremium(
        jogador
    ) {

        jogador = jogador || {};


        const nome =
            document.getElementById(
                "loja-premium-jogador"
            );


        const saldo =
            document.getElementById(
                "loja-premium-saldo"
            );


        if (nome) {

            nome.textContent =
                jogador.nome ||
                "Aventureiro";
        }


        if (saldo) {

            saldo.textContent =
                formatarNumero(
                    jogador.gems || 0
                );
        }
    }


    function renderizarPacotesLojaPremium(
        pacotes
    ) {

        const grade =
            document.getElementById(
                "loja-premium-pacotes"
            );


        if (!grade) {
            return;
        }


        if (
            !Array.isArray(pacotes) ||
            pacotes.length === 0
        ) {

            grade.innerHTML = `
                <div class="loja-premium-vazio">
                    Nenhum pacote disponível no momento.
                </div>
            `;

            return;
        }


        grade.innerHTML = pacotes
            .map(
                pacote => {

                    const id =
                        escaparHtml(
                            pacote.id
                        );


                    const nome =
                        escaparHtml(
                            pacote.nome
                        );


                    const descricao =
                        escaparHtml(
                            pacote.descricao
                        );


                    const icone =
                        escaparHtml(
                            pacote.icone || "💎"
                        );


                    const valor =
                        escaparHtml(
                            pacote.valor_formatado
                        );


                    const gemas =
                        formatarNumero(
                            pacote.gemas
                        );


                    return `
                        <article
                            class="
                                loja-premium-pacote
                                ${pacote.destaque
                                    ? "destaque"
                                    : ""}
                            "
                        >

                            ${
                                pacote.destaque
                                ? `
                                    <div class="loja-premium-badge">
                                        🔥 MAIS POPULAR
                                    </div>
                                `
                                : ""
                            }


                            <div
                                class="loja-premium-pacote-icone"
                            >
                                ${icone}
                            </div>


                            <div
                                class="loja-premium-pacote-gemas"
                            >
                                💎 ${gemas}
                            </div>


                            <div
                                class="loja-premium-pacote-nome"
                            >
                                ${nome}
                            </div>


                            <div
                                class="loja-premium-pacote-descricao"
                            >
                                ${descricao}
                            </div>


                            <div
                                class="loja-premium-pacote-preco"
                            >
                                ${valor}
                            </div>


                            <button
                                type="button"
                                class="loja-premium-comprar"
                                data-pacote-id="${id}"
                            >
                                COMPRAR
                            </button>

                        </article>
                    `;
                }
            )
            .join("");


        grade
            .querySelectorAll(
                ".loja-premium-comprar"
            )
            .forEach(
                botao => {

                    botao.addEventListener(
                        "click",
                        () => {

                            criarPedidoLojaPremium(
                                botao.dataset.pacoteId,
                                botao
                            );
                        }
                    );
                }
            );
    }


    // =========================================================
    // 🧾 CRIAR PEDIDO
    // =========================================================

    async function criarPedidoLojaPremium(
        pacoteId,
        botao
    ) {

        if (
            estadoLojaPremium
                .criandoPedido
        ) {
            return;
        }


        const userId =
            obterUserIdLojaPremium();


        if (!userId) {

            mostrarMensagemLojaPremium(
                "Herói não encontrado.",
                "erro"
            );

            return;
        }


        estadoLojaPremium
            .criandoPedido = true;


        const textoAnterior =
            botao?.textContent;


        if (botao) {

            botao.disabled = true;
            botao.textContent =
                "CRIANDO PEDIDO...";
        }


        try {

            const resposta = await fetch(
                "/api/premium/pedido/criar",
                {
                    method: "POST",

                    headers: {
                        "Content-Type":
                            "application/json",
                    },

                    body: JSON.stringify({
                        user_id:
                            userId,

                        pacote_id:
                            pacoteId,
                    }),
                }
            );


            const dados =
                await resposta.json();


            if (
                !resposta.ok ||
                !dados.success
            ) {

                throw new Error(
                    dados.error ||
                    "Não foi possível criar o pedido."
                );
            }


            const pedido =
                dados.pedido || {};


            mostrarMensagemLojaPremium(
                `✅ Pedido ${pedido.codigo} criado com sucesso.`,
                "sucesso"
            );


            await abrirCheckoutPix(
                pedido.codigo
            );


        } catch (erro) {

            console.error(
                "❌ [PEDIDO PREMIUM]",
                erro
            );


            mostrarMensagemLojaPremium(
                erro.message,
                "erro"
            );


        } finally {

            estadoLojaPremium
                .criandoPedido = false;


            if (botao) {

                botao.disabled = false;

                botao.textContent =
                    textoAnterior ||
                    "COMPRAR";
            }
        }
    }

    // =========================================================
    // 💠 CHECKOUT PIX
    // =========================================================

    async function abrirCheckoutPix(
        codigoPedido
    ) {

        const userId =
            obterUserIdLojaPremium();


        if (
            !userId ||
            !codigoPedido
        ) {

            mostrarMensagemLojaPremium(
                "Pedido inválido.",
                "erro"
            );

            return;
        }


        mudarAbaLojaPremium(
            "checkout"
        );


        const carregando =
            document.getElementById(
                "loja-premium-checkout-carregando"
            );


        const conteudo =
            document.getElementById(
                "loja-premium-checkout-conteudo"
            );


        if (carregando) {
  
            carregando.style.display =
                "block";
        }


        if (conteudo) {
 
            conteudo.style.display =
                "none";
        }

        const areaComprovante =
            document.getElementById(
                "loja-premium-comprovante-area"
            );


        const arquivoComprovante =
            document.getElementById(
                "loja-premium-comprovante-arquivo"
            );


        const nomeComprovante =
            document.getElementById(
                "loja-premium-comprovante-nome"
            );


        if (areaComprovante) {
            areaComprovante.style.display =
                "none";
        }


        if (arquivoComprovante) {
            arquivoComprovante.value = "";
        }


        if (nomeComprovante) {
            nomeComprovante.textContent =
                "Nenhum arquivo selecionado";
        }

        try {

            const resposta = await fetch(
                "/api/premium/pedido/pix",
                {
                    method: "POST",

                    headers: {
                        "Content-Type":
                            "application/json",
                    },

                    body: JSON.stringify({
                        user_id:
                            userId,

                        codigo_pedido:
                            codigoPedido,
                    }),
                }
            );


            const dados =
                await resposta.json();


            if (
                !resposta.ok ||
                !dados.success
            ) {

                throw new Error(
                    dados.error ||
                    "Não foi possível gerar o Pix."
                );
            }


            const pedido =
                dados.pedido || {};
            
            estadoLojaPremium.codigoPedidoCheckout =
                pedido.codigo || codigoPedido;    

            const pix =
                dados.pix || {};


            const campoPedido =
                document.getElementById(
                    "loja-premium-checkout-pedido"
                );


            const campoGemas =
                document.getElementById(
                    "loja-premium-checkout-gemas"
                );


            const campoValor =
                document.getElementById(
                    "loja-premium-checkout-valor"
                );


            const campoCodigo =
                document.getElementById(
                    "loja-premium-pix-codigo"
                );


            if (campoPedido) {
 
                campoPedido.textContent =
                    pedido.codigo || "-";
            }


            if (campoGemas) {

                campoGemas.textContent =
                    formatarNumero(
                        pedido.gemas || 0
                    );
            }


            if (campoValor) {
 
                campoValor.textContent =
                    pedido.valor_formatado ||
                    "";
            }


            if (campoCodigo) {

                campoCodigo.value =
                    pix.codigo || "";
            }


            gerarQrCodePix(
                pix.codigo
            );


            if (carregando) {

                carregando.style.display =
                    "none";
            }


            if (conteudo) {

                conteudo.style.display =
                    "block";
            }


        } catch (erro) {

            console.error(
                "❌ [PIX PREMIUM]",
                erro
            );


            if (carregando) {

                carregando.style.display =
                    "block";

                carregando.textContent =
                    `❌ ${erro.message}`;
            }


            mostrarMensagemLojaPremium(
                erro.message,
                "erro"
            );
        }
    }


    function gerarQrCodePix(
        codigoPix
    ) {

        const area =
            document.getElementById(
                "loja-premium-qrcode"
            );


        if (!area) {
            return;
        }


        area.innerHTML = "";


        if (!codigoPix) {

            area.textContent =
                "QR indisponível";

            return;
        }


        if (
            typeof QRCode
            === "undefined"
        ) {

            area.textContent =
                "QR Code indisponível.";

            return;
        }


        new QRCode(
            area,
            {
                text:
                    codigoPix,

                width:
                    190,

                height:
                    190,

                correctLevel:
                    QRCode.CorrectLevel.M,
            }
        );
    }


    async function copiarCodigoPix() {
 
        const campo =
            document.getElementById(
                "loja-premium-pix-codigo"
            );


        const codigo =
            campo?.value || "";


        if (!codigo) {

            mostrarMensagemLojaPremium(
                "Código Pix indisponível.",
                "erro"
            );

            return;
        }


        try {
 
            if (
                navigator.clipboard &&
                window.isSecureContext
            ) {

                await navigator.clipboard.writeText(
                    codigo
                );

            } else {

                campo.focus();
                campo.select();

                document.execCommand(
                    "copy"
                );

                campo.setSelectionRange(
                    0,
                    0
                );
            }  


            mostrarMensagemLojaPremium(
                "📋 Código Pix copiado!",
                "sucesso"
            );


        } catch (erro) {

            mostrarMensagemLojaPremium(
                "Não foi possível copiar automaticamente. Segure o código para copiar.",
                "erro"
            );
        }
    }

    // =========================================================
    // 📜 PEDIDOS
    // =========================================================

    async function carregarPedidosLojaPremium() {

        if (
            estadoLojaPremium
                .carregandoPedidos
        ) {
            return;
        }


        const userId =
            obterUserIdLojaPremium();


        const area =
            document.getElementById(
                "loja-premium-pedidos"
            );


        if (
            !userId ||
            !area
        ) {
            return;
        }


        estadoLojaPremium
            .carregandoPedidos = true;


        area.innerHTML = `
            <div class="loja-premium-vazio">
                📜 Consultando seus pedidos...
            </div>
        `;


        try {

            const resposta = await fetch(
                `/api/premium/pedidos/${encodeURIComponent(userId)}?t=${Date.now()}`,
                {
                    method: "GET",
                    cache: "no-store",
                }
            );


            const dados =
                await resposta.json();


            if (
                !resposta.ok ||
                !dados.success
            ) {

                throw new Error(
                    dados.error ||
                    "Não foi possível carregar os pedidos."
                );
            }


            renderizarPedidosLojaPremium(
                dados.pedidos || []
            );


        } catch (erro) {

            console.error(
                "❌ [PEDIDOS PREMIUM]",
                erro
            );


            area.innerHTML = `
                <div class="loja-premium-vazio">
                    ❌ ${escaparHtml(
                        erro.message
                    )}
                </div>
            `;


        } finally {

            estadoLojaPremium
                .carregandoPedidos = false;
        }
    }


    function renderizarPedidosLojaPremium(
        pedidos
    ) {

        const area =
            document.getElementById(
                "loja-premium-pedidos"
            );


        if (!area) {
            return;
        }


        if (
            !Array.isArray(pedidos) ||
            pedidos.length === 0
        ) {

            area.innerHTML = `
                <div class="loja-premium-vazio">
                    Você ainda não possui pedidos.
                </div>
            `;

            return;
        }


        const statusConfig = {

            aguardando_pagamento: {
                texto:
                    "Aguardando pagamento",
                icone:
                    "⏳",
            },

            em_analise: {
                texto:
                    "Em análise",
                icone:
                    "🔎",
            },

            aprovado: {
                texto:
                    "Aprovado",
                icone:
                    "✅",
            },

            recusado: {
                texto:
                    "Recusado",
                icone:
                    "❌",
            },

            cancelado: {
                texto:
                    "Cancelado",
                icone:
                    "🚫",
            },

            expirado: {
                texto:
                    "Expirado",
                icone:
                    "⌛",
            },
        };


        area.innerHTML = pedidos
            .map(
                pedido => {

                    const config =
                        statusConfig[
                            pedido.status
                        ] || {
                            texto:
                                pedido.status,
                            icone:
                                "📜",
                        };


                    const statusHtml = `
                        <span
                            style="
                                color:#a7b0be;
                                font-size:0.60rem;
                                font-weight:800;
                            "
                        >
                            ${config.icone}
                            ${escaparHtml(
                                config.texto
                            )}
                        </span>
                    `;


                    let infoExtra = "";


                    if (
                        pedido.status === "aprovado"
                    ) {

                        infoExtra = `
                            <div
                                style="
                                    margin-top:10px;
                                    padding:9px 10px;
                                    color:#bbf7d0;
                                    background:rgba(20, 83, 45, 0.30);
                                    border:1px solid rgba(74, 222, 128, 0.25);
                                    border-radius:8px;
                                    font-size:0.64rem;
                                    line-height:1.45;
                                "
                            >
                                <div
                                    style="
                                        font-weight:900;
                                        margin-bottom:4px;
                                    "
                                >
                                    ✅ PAGAMENTO APROVADO
                                </div>
                    
                                <div>
                                    💎 ${formatarNumero(
                                        pedido.gemas || 0
                                    )} Gemas adicionadas à sua conta.
                                </div>

                                ${
                                    pedido.aprovado_em
                                    ? `
                                        <div
                                            style="
                                                margin-top:4px;
                                                color:#d1fae5;
                                            "
                                        >
                                            Confirmado em:
                                            ${escaparHtml(
                                                formatarData(
                                                    pedido.aprovado_em
                                                )
                                            )}
                                        </div>
                                    `
                                    : ""
                                }
                            </div>
                        `;
                    }


                    if (
                        pedido.status === "recusado"
                    ) {

                        infoExtra = `
                            <div
                                style="
                                    margin-top:10px;
                                    padding:9px 10px;
                                    color:#fecaca;
                                    background:rgba(127, 29, 29, 0.30);
                                    border:1px solid rgba(248, 113, 113, 0.25);
                                    border-radius:8px;
                                    font-size:0.64rem;
                                    line-height:1.45;
                                "
                            >
                                <div
                                    style="
                                        font-weight:900;
                                        margin-bottom:4px;
                                    "
                                >
                                    ❌ PAGAMENTO NÃO CONFIRMADO
                                </div>
                    
                                <div>
                                    ${
                                        pedido.motivo_recusa
                                        ? `Motivo: ${escaparHtml(
                                            pedido.motivo_recusa
                                        )}`
                                        : "Motivo: Não informado."
                                    }
                                </div>
                    
                                ${
                                    pedido.recusado_em
                                    ? `
                                        <div
                                            style="
                                                margin-top:4px;
                                                color:#fecaca;
                                            "
                                        >
                                            Atualizado em:
                                            ${escaparHtml(
                                                formatarData(
                                                    pedido.recusado_em
                                                )
                                            )}
                                        </div>
                                    `
                                    : ""
                                }
                            </div>
                        `;
                    }


                    return `
                        <div
                            class="loja-premium-pedido"
                        >
                    
                            <div
                                style="
                                    display:flex;
                                    justify-content:space-between;
                                    gap:8px;
                                    align-items:center;
                                "
                            >
                    
                                <strong
                                    style="
                                        color:#f4dc91;
                                        font-size:0.72rem;
                                    "
                                >
                                    ${escaparHtml(
                                        pedido.codigo
                                    )}
                                </strong>
                    
                                ${statusHtml}
                    
                            </div>
                    
                    
                            <div
                                style="
                                    margin-top:7px;
                                    color:#ddd6fe;
                                    font-size:0.74rem;
                                    font-weight:900;
                                "
                            >
                                💎 ${formatarNumero(
                                    pedido.gemas
                                )} Gemas
                            </div>
                    
                    
                            <div
                                style="
                                    margin-top:3px;
                                    color:#e4c875;
                                    font-size:0.72rem;
                                    font-weight:900;
                                "
                            >
                                ${escaparHtml(
                                    pedido.valor_formatado
                                )}
                            </div>
                    
                    
                            <div
                                style="
                                    margin-top:7px;
                                    color:#718096;
                                    font-size:0.57rem;
                                "
                            >
                                Criado em:
                                ${escaparHtml(
                                    formatarData(
                                        pedido.criado_em
                                    )
                                )}
                            </div>

                            ${infoExtra}

                        </div>
                    `;
                }
            )
            .join("");
    }

    
    // =========================================================
    // 📎 COMPROVANTE
    // =========================================================

    async function enviarComprovantePremium() {

        if (
            estadoLojaPremium
                .enviandoComprovante
        ) {
            return;
        }


        const userId =
            obterUserIdLojaPremium();


        const codigoPedido =
            estadoLojaPremium
                .codigoPedidoCheckout;


        const input =
            document.getElementById(
                "loja-premium-comprovante-arquivo"
            );


        const botao =
            document.getElementById(
                "loja-premium-enviar-comprovante"
            );


        const arquivo =
            input?.files?.[0];


        if (!userId) {

            mostrarMensagemLojaPremium(
                "Herói não encontrado.",
                "erro"
            );

            return;
        }


        if (!codigoPedido) {

            mostrarMensagemLojaPremium(
                "Pedido não encontrado.",
                "erro"
            );

            return;
        }


        if (!arquivo) {

            mostrarMensagemLojaPremium(
                "Selecione o comprovante.",
                "erro"
            );

            return;
        }


        if (
            arquivo.size
            > 5 * 1024 * 1024
        ) {

            mostrarMensagemLojaPremium(
                "O arquivo pode ter no máximo 5 MB.",
                "erro"
            );

            return;
        }


        const permitidos = new Set([
            "image/jpeg",
            "image/png",
            "image/webp",
            "application/pdf",
        ]);


        if (
            arquivo.type
            && !permitidos.has(
                arquivo.type
            )
        ) {

            mostrarMensagemLojaPremium(
                "Envie JPG, PNG, WEBP ou PDF.",
                "erro"
            );

            return;
        }


        estadoLojaPremium
            .enviandoComprovante = true;


        const textoAnterior =
            botao?.textContent;


        if (botao) {

            botao.disabled = true;
  
            botao.textContent =
                "ENVIANDO...";
        }


        try {

            const formData =
                new FormData();


            formData.append(
                "user_id",
                userId
            );


            formData.append(
                "codigo_pedido",
                codigoPedido
            );


            formData.append(
                "comprovante",
                arquivo
            );


            const resposta = await fetch(
                "/api/premium/pedido/comprovante",
                {
                    method: "POST",
                    body: formData,
                }
            );


            const dados =
                await resposta.json();


            if (
                !resposta.ok
                || !dados.success
            ) {

                throw new Error(
                    dados.error
                    || "Falha ao enviar comprovante."
                );
            }


            mostrarMensagemLojaPremium(
                "✅ Comprovante enviado! Seu pedido está em análise.",
                "sucesso"
            );


            mudarAbaLojaPremium(
                "pedidos"
            );


        } catch (erro) {

            console.error(
                "❌ [COMPROVANTE PREMIUM]",
                erro
            );


            mostrarMensagemLojaPremium(
                erro.message,
                "erro"
            );


        } finally {

            estadoLojaPremium
                .enviandoComprovante = false;


            if (botao) {
  
                botao.disabled = false;

                botao.textContent =
                    textoAnterior
                    || "📤 ENVIAR PARA ANÁLISE";
            }
        }
    }

    // =========================================================
    // 🎮 EVENTOS
    // =========================================================

    function instalarEventosLojaPremium() {
        
        const jaPaguei =
            document.getElementById(
                "loja-premium-ja-paguei"
            );


        if (jaPaguei) {

            jaPaguei.addEventListener(
                "click",
                () => {

                    const area =
                        document.getElementById(
                            "loja-premium-comprovante-area"
                        );


                    if (area) {

                        area.style.display =
                            area.style.display === "none"
                            ? "block"
                            : "none";
                    }
                }
            );
        }


        const inputComprovante =
            document.getElementById(
                "loja-premium-comprovante-arquivo"
            );


        if (inputComprovante) {

            inputComprovante.addEventListener(
                "change",
                () => {

                    const nome =
                        document.getElementById(
                            "loja-premium-comprovante-nome"
                        );


                    const arquivo =
                        inputComprovante
                            .files?.[0];


                    if (nome) {

                        nome.textContent =
                            arquivo
                            ? arquivo.name
                            : "Nenhum arquivo selecionado";
                    }
                }
            );
        }


        const enviarComprovante =
            document.getElementById(
                "loja-premium-enviar-comprovante"
            );


        if (enviarComprovante) {

            enviarComprovante.addEventListener(
                "click",
                enviarComprovantePremium
            );
        }

        const fechar =
            document.getElementById(
                "loja-premium-fechar"
            );


        if (fechar) {

            fechar.addEventListener(
                "click",
                window.fecharLojaPremium
            );
        }


        const modal =
            document.getElementById(
                "loja-premium-modal"
            );


        if (modal) {

            modal.addEventListener(
                "click",
                evento => {

                    if (
                        evento.target
                        === modal
                    ) {

                        window.fecharLojaPremium();
                    }
                }
            );
        }


        document
            .querySelectorAll(
                ".loja-premium-aba"
            )
            .forEach(
                botao => {

                    botao.addEventListener(
                        "click",
                        () => {

                            mudarAbaLojaPremium(
                                botao.dataset
                                    .lojaPremiumAba
                            );
                        }
                    );
                }
            );


        document.addEventListener(
            "keydown",
            evento => {

                if (
                    evento.key !== "Escape"
                ) {
                    return;
                }


                const modalAtual =
                    document.getElementById(
                        "loja-premium-modal"
                    );


                if (
                    modalAtual &&
                    modalAtual.style.display
                        !== "none"
                ) {

                    window.fecharLojaPremium();
                }
            }
        );
    }


    if (
        document.readyState
        === "loading"
    ) {

        document.addEventListener(
            "DOMContentLoaded",
            instalarEventosLojaPremium
        );

    } else {

        instalarEventosLojaPremium();
    }
    const voltarCheckout =
        document.getElementById(
            "loja-premium-voltar-checkout"
        );


    if (voltarCheckout) {

        voltarCheckout.addEventListener(
            "click",
            () => {

                mudarAbaLojaPremium(
                    "pedidos"
                );
            }
        );
    }


    const copiarPix =
        document.getElementById(
            "loja-premium-copiar-pix"
        );


    if (copiarPix) {

        copiarPix.addEventListener(
            "click",
            copiarCodigoPix
        );
    }

})();