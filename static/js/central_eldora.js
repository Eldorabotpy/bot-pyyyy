// ============================================================
// 📜 MUNDO DE ELDORA - CENTRAL DE ELDORA
// ============================================================

(function () {
    "use strict";

        // ========================================================
    // 🖼️ IDENTIDADE VISUAL DAS ABAS
    // ========================================================

    const CONFIG_ABAS_CENTRAL = {

        atualizacoes: {
            imagem:
                "https://raw.githubusercontent.com/Eldorabotpy/static-img/main/assets/central_eldora/baner_site.png",

            eyebrow:
                "Crônicas oficiais",

            titulo:
                "As Crônicas do Reino estão abertas",

            texto:
                "Acompanhe novidades, melhorias e tudo que está mudando no Mundo de Eldora."
        },


        enciclopedia: {
            imagem:
                "https://raw.githubusercontent.com/Eldorabotpy/static-img/main/assets/central_eldora/enciclopedia.png",

            eyebrow:
                "Conhecimento de Eldora",

            titulo:
                "Enciclopédia do Reino",

            texto:
                "Descubra regiões, classes, profissões, criaturas, sistemas e os segredos do mundo."
        },


        rankings: {
            imagem:
                "https://raw.githubusercontent.com/Eldorabotpy/static-img/main/assets/central_eldora/rankings.png",

            eyebrow:
                "Glória e prestígio",

            titulo:
                "Os maiores nomes de Eldora",

            texto:
                "Acompanhe os clãs e guerreiros que conquistaram seu lugar entre os melhores do reino."
        },


        guerra: {
            imagem:
                "https://raw.githubusercontent.com/Eldorabotpy/static-img/main/assets/central_eldora/guerra_clans.png",

            eyebrow:
                "Bandeiras em conflito",

            titulo:
                "Guerra de Clãs",

            texto:
                "Prepare seu clã, organize seus guerreiros e dispute a supremacia nas guerras semanais de Eldora."
        },


        pvp: {
            imagem:
                "https://raw.githubusercontent.com/Eldorabotpy/static-img/main/assets/central_eldora/pvp.png",

            eyebrow:
                "Arena competitiva",

            titulo:
                "PvP de Eldora",

            texto:
                "Enfrente outros aventureiros, suba nas classificações e prove sua força em combate."
        },


        eventos: {
            imagem:
                "https://raw.githubusercontent.com/Eldorabotpy/static-img/main/assets/central_eldora/eventos.png",

            eyebrow:
                "O mundo está em movimento",

            titulo:
                "Eventos do Reino",

            texto:
                "Acompanhe invasões, fendas dimensionais e acontecimentos especiais que ameaçam Eldora."
        }
    };
    
    let centralHeroTrocaId =
    0;

    function elemento(id) {
        return document.getElementById(id);
    }

    function escaparHtmlCentral(
        valor
    ) {
        return String(
            valor ?? ""
        )
            .replaceAll(
                "&",
                "&amp;"
            )
            .replaceAll(
                "<",
                "&lt;"
            )
            .replaceAll(
                ">",
                "&gt;"
            )
            .replaceAll(
                '"',
                "&quot;"
            )
            .replaceAll(
                "'",
                "&#039;"
            );
    }


    function formatarNumeroCentral(
        valor
    ) {
        return Number(
            valor || 0
        ).toLocaleString(
            "pt-BR"
        );
    }


    /*
     * Cache somente da sessão atual
     * da página.
     */
    let rankingClansCache =
        null;

    let rankingGuerraCache =
        null;

    let rankingAtualCentral =
        null;
    
    // ========================================================
    // ⚔️ ESTADO DA GUERRA DE CLÃS
    // ========================================================

    let estadoGuerraCentral =
        null;

    let carregandoGuerraCentral =
        false;

    // ========================================================
    // 🎵 MÚSICA DA GUERRA DE CLÃS
    // ========================================================

    let musicaAntesGuerraCentral =
        null;


    let musicaGuerraCentralAtiva =
        false;


    function iniciarMusicaGuerraCentral() {

        if (
            !window.AudioManager
        ) {

            return;
        }


        // ====================================================
        // 🔊 TELEGRAM / WEBVIEW
        // ====================================================

        if (
            typeof window.AudioManager
                .desbloquearAudio ===
                "function"
        ) {

            window.AudioManager
                .desbloquearAudio();
        }


        // ====================================================
        // 🎵 JÁ ESTAMOS NA GUERRA
        //
        // Não sorteia outra música.
        // Não reinicia a atual.
        // ====================================================

        if (
            musicaGuerraCentralAtiva
            &&
            window.AudioManager
                .chaveAtual ===
                "bgm_guerra_clans"
            &&
            window.AudioManager
                .musicaAtual
        ) {

            return;
        }


        // ====================================================
        // 💾 GUARDA A MÚSICA ANTERIOR
        // ====================================================

        if (
            !musicaGuerraCentralAtiva
        ) {

            const chaveAtual =
                window.AudioManager
                    .chaveAtual;


            if (
                chaveAtual
                &&
                chaveAtual !==
                    "bgm_guerra_clans"
            ) {

                musicaAntesGuerraCentral =
                    chaveAtual;
            }
        }


        musicaGuerraCentralAtiva =
            true;


        // ====================================================
        // ⚔️ MÚSICA EXCLUSIVA DA GUERRA
        // ====================================================

        window.AudioManager
            .tocarMusica(
                "bgm_guerra_clans"
            );
    }


    function restaurarMusicaAposGuerraCentral() {

        if (
            !musicaGuerraCentralAtiva
        ) {

            return;
        }


        musicaGuerraCentralAtiva =
            false;


        if (
            !window.AudioManager
        ) {

            musicaAntesGuerraCentral =
                null;

            return;
        }


        const musicaAnterior =
            musicaAntesGuerraCentral;


        musicaAntesGuerraCentral =
            null;


        if (
            musicaAnterior
            &&
            musicaAnterior !==
                "bgm_guerra_clans"
        ) {

            window.AudioManager
                .tocarMusica(
                    musicaAnterior
                );


        } else {

            window.AudioManager
                .pararMusica();
        }
    }        
    // ========================================================
    // 👑 SELEÇÃO TEMPORÁRIA DA ESCALAÇÃO
    // ========================================================

    let titularesSelecionadosGuerraCentral =
        new Set();

    let chaveEscalacaoGuerraCentral =
        null;

    // ========================================================
    // 📜 ABRIR CENTRAL
    // ========================================================

    window.abrirCentralEldora = function (
        abaInicial = "atualizacoes"
    ) {
        const modal = elemento(
            "central-eldora-modal"
        );

        if (!modal) {
            console.error(
                "❌ central-eldora-modal não encontrado."
            );

            return;
        }


        /*
         * Fecha o menu lateral e trava
         * interação com o mapa.
         */
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


        modal.style.display = "flex";

        modal.setAttribute(
            "aria-hidden",
            "false"
        );


        window.abrirAbaCentralEldora(
            abaInicial
        );


        const scroll = elemento(
            "central-eldora-scroll"
        );

        if (scroll) {
            scroll.scrollTop = 0;
        }
    };


    // ========================================================
    // ❌ FECHAR CENTRAL
    // ========================================================

    window.fecharCentralEldora = function () {
        const modal = elemento(
            "central-eldora-modal"
        );

        if (!modal) {
            return;
        }


        modal.style.display = "none";

        modal.setAttribute(
            "aria-hidden",
            "true"
        );


        // Se estava na Guerra, devolve
        // a música que tocava anteriormente.
        restaurarMusicaAposGuerraCentral();


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
    };

    // ========================================================
    // 🖼️ ATUALIZAR BANNER DA ABA
    // ========================================================

    function atualizarHeroCentral(
        abaId
    ) {
        const config =
            CONFIG_ABAS_CENTRAL[
                abaId
            ] ||
            CONFIG_ABAS_CENTRAL
                .atualizacoes;


        const imagem = elemento(
            "central-eldora-hero-imagem"
        );

        const eyebrow = elemento(
            "central-eldora-hero-eyebrow"
        );

        const titulo = elemento(
            "central-eldora-hero-titulo"
        );

        const texto = elemento(
            "central-eldora-hero-texto"
        );


        if (eyebrow) {
            eyebrow.textContent =
                config.eyebrow;
        }


        if (titulo) {
            titulo.textContent =
                config.titulo;
        }


        if (texto) {
            texto.textContent =
                config.texto;
        }

        const trocaAtual =
            ++centralHeroTrocaId;

        if (
            imagem &&
            imagem.src !== config.imagem
        ) {
            /*
             * Faz uma pequena transição
             * antes de trocar a arte.
             */
            imagem.style.opacity =
                "0.15";


            setTimeout(
                function () {

                    if (
                        trocaAtual !==
                        centralHeroTrocaId
                    ) {
                        return;
                    }
                                        
                    imagem.src =
                        config.imagem;


                    imagem.onload =
                        function () {

                            imagem.style.opacity =
                                "0.72";
                        };


                    /*
                     * Se uma imagem ainda não
                     * existir no GitHub, volta
                     * para o banner principal.
                     */
                    imagem.onerror =
                        function () {

                            imagem.onerror =
                                null;

                            imagem.src =
                                CONFIG_ABAS_CENTRAL
                                    .atualizacoes
                                    .imagem;

                            imagem.style.opacity =
                                "0.72";
                        };

                },
                120
            );
        }
    }

    // ========================================================
    // 📑 TROCAR ABAS
    // ========================================================

    window.abrirAbaCentralEldora = function (
        abaId
    ) {
        abaId = String(
            abaId || "atualizacoes"
        ).trim();


        const alvo = elemento(
            `central-tab-${abaId}`
        );


        if (!alvo) {
            abaId = "atualizacoes";
        }


        document
            .querySelectorAll(
                ".central-eldora-tab"
            )
            .forEach(
                function (tab) {
                    tab.classList.remove(
                        "active"
                    );
                }
            );


        document
            .querySelectorAll(
                ".central-eldora-aba-btn"
            )
            .forEach(
                function (botao) {
                    botao.classList.remove(
                        "active"
                    );

                    if (
                        String(
                            botao.dataset
                                .centralTab ||
                            ""
                        ) === abaId
                    ) {
                        botao.classList.add(
                            "active"
                        );
                    }
                }
            );


        const novaAba = elemento(
            `central-tab-${abaId}`
        );


        if (novaAba) {
            novaAba.classList.add(
                "active"
            );
        }

        atualizarHeroCentral(
            abaId
        );


        // ====================================================
        // 🎵 IDENTIDADE SONORA DA GUERRA
        // ====================================================

        if (
            abaId ===
            "guerra"
        ) {

            iniciarMusicaGuerraCentral();


        } else {

            restaurarMusicaAposGuerraCentral();
        }


        if (
            abaId ===
            "rankings"
        ) {
            mostrarMenuRankings();
        }

        if (
            abaId ===
            "guerra"
        ) {
            carregarEstadoGuerraCentral();
        }

    };

    // ========================================================
    // 🏆 MENU DOS RANKINGS
    // ========================================================

    function mostrarMenuRankings() {

        const menu = elemento(
            "central-rankings-menu"
        );

        const detalhe = elemento(
            "central-ranking-detalhe"
        );


        if (menu) {
            menu.style.display =
                "block";
        }


        if (detalhe) {
            detalhe.style.display =
                "none";
        }


        rankingAtualCentral =
            null;
    }


    // ========================================================
    // 🏆 ABRIR UM RANKING
    // ========================================================

    async function abrirRankingCentral(
        tipo,
        forcarAtualizacao = false
    ) {
        tipo = String(
            tipo || ""
        ).trim();


        const menu = elemento(
            "central-rankings-menu"
        );

        const detalhe = elemento(
            "central-ranking-detalhe"
        );

        const titulo = elemento(
            "central-ranking-titulo"
        );

        const descricao = elemento(
            "central-ranking-descricao"
        );

        const eyebrow = elemento(
            "central-ranking-eyebrow"
        );

        const conteudo = elemento(
            "central-ranking-conteudo"
        );

        const btnAtualizar = elemento(
            "central-ranking-atualizar"
        );


        if (
            !detalhe ||
            !conteudo
        ) {
            return;
        }


        if (menu) {
            menu.style.display =
                "none";
        }


        detalhe.style.display =
            "block";


        rankingAtualCentral =
            tipo;


        // ====================================================
        // 🛡️ CLÃS
        // ====================================================

        if (
            tipo === "clans"
        ) {

            if (eyebrow) {
                eyebrow.textContent =
                    "Classificação oficial";
            }


            if (titulo) {
                titulo.textContent =
                    "🛡️ Grandes Clãs de Eldora";
            }


            if (descricao) {
                descricao.textContent =
                    "Os clãs mais avançados do reino, "
                    + "considerando nível, experiência "
                    + "e desenvolvimento.";
            }


            if (btnAtualizar) {
                btnAtualizar.style.display =
                    "flex";
            }


            await carregarRankingClans(
                forcarAtualizacao
            );

            return;
        }


        // ====================================================
        // ⚔️ GUERRA
        // ====================================================

        if (
            tipo === "guerra"
        ) {

            if (eyebrow) {
                eyebrow.textContent =
                    "Competição de Clãs";
            }


            if (titulo) {
                titulo.textContent =
                    "⚔️ Ranking de Guerra";
            }


            if (descricao) {
                descricao.textContent =
                    "Classificação geral das "
                    + "Guerras oficiais de Eldora.";
            }


            if (btnAtualizar) {
                btnAtualizar.style.display =
                    "flex";
            }


            await carregarRankingGuerra(
                forcarAtualizacao
            );

            return;
        }


        // ====================================================
        // 🥊 PVP
        // ====================================================

        if (
            tipo === "pvp"
        ) {

            if (eyebrow) {
                eyebrow.textContent =
                    "Arena Competitiva";
            }


            if (titulo) {
                titulo.textContent =
                    "🥊 Ranking PvP";
            }


            if (descricao) {
                descricao.textContent =
                    "Classificação dos maiores "
                    + "combatentes de Eldora.";
            }


            if (btnAtualizar) {
                btnAtualizar.style.display =
                    "none";
            }


            conteudo.innerHTML = `
                <div
                    class="
                        central-ranking-futuro
                    "
                >
                    <div
                        class="
                            central-ranking-futuro-icone
                        "
                    >
                        🥊
                    </div>

                    <strong>
                        Ranking PvP em preparação
                    </strong>

                    <p>
                        A classificação competitiva
                        será integrada ao sistema
                        PvP em uma etapa futura.
                    </p>
                </div>
            `;

            return;
        }


        mostrarMenuRankings();
    }


    // ========================================================
    // 🛡️ CARREGAR RANKING DE CLÃS
    // ========================================================

    async function carregarRankingClans(
        forcar = false
    ) {
        const conteudo = elemento(
            "central-ranking-conteudo"
        );


        if (!conteudo) {
            return;
        }


        /*
         * Evita buscar novamente cada vez que
         * o jogador entra e sai do submenu.
         */
        if (
            rankingClansCache &&
            !forcar
        ) {
            renderizarRankingClans(
                rankingClansCache
            );

            return;
        }


        conteudo.innerHTML = `
            <div
                class="
                    central-ranking-carregando
                "
            >
                🛡️ Consultando os registros
                dos grandes clãs de Eldora...
            </div>
        `;


        try {

            const resposta =
                await fetch(
                    (
                        "/api/clan/listar"
                        + "?limite=50"
                        + "&t="
                        + Date.now()
                    ),
                    {
                        method:
                            "GET",

                        cache:
                            "no-store"
                    }
                );


            const dados =
                await resposta.json();


            if (
                !resposta.ok ||
                dados.success === false
            ) {
                throw new Error(
                    dados.error ||
                    dados.erro ||
                    "Não foi possível carregar "
                    + "o ranking de clãs."
                );
            }


            const clans =
                Array.isArray(
                    dados.clans
                )
                    ? [
                        ...dados.clans
                    ]
                    : [];


            /*
             * Ranking de progresso:
             *
             * 1º nível do clã
             * 2º XP do clã
             * 3º quantidade de membros
             * 4º nome
             *
             * Quando a Guerra existir, ela terá
             * ranking próprio separado.
             */
            clans.sort(
                function (
                    a,
                    b
                ) {

                    const nivelA =
                        Number(
                            a.nivel || 1
                        );

                    const nivelB =
                        Number(
                            b.nivel || 1
                        );


                    if (
                        nivelA !==
                        nivelB
                    ) {
                        return (
                            nivelB -
                            nivelA
                        );
                    }


                    const xpA =
                        Number(
                            a.xp || 0
                        );

                    const xpB =
                        Number(
                            b.xp || 0
                        );


                    if (
                        xpA !== xpB
                    ) {
                        return (
                            xpB -
                            xpA
                        );
                    }


                    const membrosA =
                        Number(
                            a.membros_total ||
                            0
                        );

                    const membrosB =
                        Number(
                            b.membros_total ||
                            0
                        );


                    if (
                        membrosA !==
                        membrosB
                    ) {
                        return (
                            membrosB -
                            membrosA
                        );
                    }


                    return String(
                        a.nome || ""
                    ).localeCompare(
                        String(
                            b.nome || ""
                        ),
                        "pt-BR"
                    );
                }
            );


            rankingClansCache =
                clans;


            renderizarRankingClans(
                clans
            );


        } catch (
            erro
        ) {

            console.error(
                "❌ [CENTRAL] Ranking de clãs:",
                erro
            );


            conteudo.innerHTML = `
                <div
                    class="
                        central-ranking-vazio
                    "
                >
                    ⚠️ ${
                        escaparHtmlCentral(
                            erro.message ||
                            "Erro ao carregar ranking."
                        )
                    }
                </div>
            `;
        }
    }


    // ========================================================
    // 🛡️ RENDERIZAR RANKING DE CLÃS
    // ========================================================

    function renderizarRankingClans(
        clans
    ) {
        const conteudo = elemento(
            "central-ranking-conteudo"
        );


        if (!conteudo) {
            return;
        }


        if (
            !Array.isArray(
                clans
            ) ||
            !clans.length
        ) {

            conteudo.innerHTML = `
                <div
                    class="
                        central-ranking-vazio
                    "
                >
                    Nenhum clã foi encontrado
                    nos registros de Eldora.
                </div>
            `;

            return;
        }


        conteudo.innerHTML =
            clans
                .map(
                    function (
                        clan,
                        indice
                    ) {

                        const posicao =
                            indice + 1;
  
 
                        let classeTop =
                            "";
   
                        let posicaoTexto =
                            `${posicao}º`;


                        if (
                            posicao === 1
                        ) {
                            classeTop =
                                "top-1";

                            posicaoTexto =
                                "🥇";
                        }

                        else if (
                            posicao === 2
                        ) {
                            classeTop =
                                "top-2";

                            posicaoTexto =
                                "🥈";
                        }

                        else if (
                            posicao === 3
                        ) {
                            classeTop =
                                "top-3";

                            posicaoTexto =
                                "🥉";
                        }


                        const nome =
                            escaparHtmlCentral(
                                clan.nome ||
                                "Clã"
                            );


                        const tag =
                            escaparHtmlCentral(
                                clan.tag ||
                                ""
                            );


                        const logo =
                            escaparHtmlCentral(
                                clan.logo_url ||
                                ""
                            );


                        const nivel =
                            Number(
                                clan.nivel ||
                                1
                            );


                        const xp =
                            Number(
                                clan.xp ||
                                0
                            );


                        const membros =
                            Number(
                                clan.membros_total ||
                                0
                            );


                        const capacidade =
                            Number(
                                clan
                                    .capacidade_membros ||
                                10
                            );


                        const logoHtml =
                            logo
                                ? `
                                    <img
                                        src="${logo}"
                                        alt="Brasão de ${nome}"
                                        onerror="
                                            this.style.display='none';
                                            this.nextElementSibling.style.display='block';
                                        "
                                    >

                                    <span
                                        style="
                                            display: none;
                                        "
                                    >
                                        🛡️
                                    </span>
                                `
                                : `
                                    <span>
                                        🛡️
                                    </span>
                                `;


                        return `
                            <div
                                class="
                                    central-ranking-linha
                                    ${classeTop}
                                "
                            >

                                <div
                                    class="
                                        central-ranking-posicao
                                    "
                                >
                                    ${posicaoTexto}
                                </div>

 
                                <div
                                    class="
                                        central-ranking-logo
                                    "
                                >
                                    ${logoHtml}
                                </div>


                                <div
                                    class="
                                        central-ranking-identidade
                                    "
                                >
                                    <div
                                        class="
                                            central-ranking-nome
                                        "
                                    >
                                        ${nome}

                                        ${
                                            tag
                                                ? `
                                                    <span
                                                        class="
                                                            central-ranking-tag
                                                        "
                                                    >
                                                        [${tag}]
                                                    </span>
                                                `
                                                : ""
                                        }
                                    </div>


                                    <div
                                        class="
                                            central-ranking-info
                                        "
                                    >
                                        ${
                                            membros
                                        }/${
                                            capacidade
                                        } membros
                                        ·
                                        ${
                                            formatarNumeroCentral(
                                                xp
                                            )
                                        } XP
                                    </div>
                                </div>

 
                                <div
                                    class="
                                        central-ranking-nivel
                                    "
                                >
                                    Nv. ${nivel}
                                </div>

                            </div>
                        `;
                    }
                )
                .join("");
    }

    // ========================================================
    // ⚔️ CARREGAR RANKING DA GUERRA
    // ========================================================

    async function carregarRankingGuerra(
        forcar = false
    ) {
        const conteudo = elemento(
            "central-ranking-conteudo"
        );


        if (!conteudo) {
            return;
        }


        if (
            rankingGuerraCache &&
            !forcar
        ) {

            renderizarRankingGuerra(
                rankingGuerraCache
            );

            return;
        }


        conteudo.innerHTML = `
            <div
                class="
                    central-ranking-carregando
                "
            >
                ⚔️ Consultando os registros
                das Guerras de Clãs...
            </div>
        `;


        try {

            const resposta =
                await fetch(
                    (
                        "/api/clan/guerra/ranking"
                        + "?limite=100"
                        + "&t="
                        + Date.now()
                    ),
                    {
                        method:
                            "GET",

                        cache:
                            "no-store"
                    }
                );


            const dados =
                await resposta.json();


            if (
                !resposta.ok ||
                dados.success === false
            ) {

                throw new Error(
                    dados.error ||
                    dados.erro ||
                    "Não foi possível carregar "
                    + "o Ranking de Guerra."
                );
            }


            rankingGuerraCache = {
                ranking:
                    Array.isArray(
                        dados.ranking
                    )
                        ? dados.ranking
                        : [],

                guerras_consideradas:
                    Number(
                        dados.guerras_consideradas ||
                        0
                    )
            };


            renderizarRankingGuerra(
                rankingGuerraCache
            );


        } catch (
            erro
        ) {

            console.error(
                "❌ [CENTRAL] Ranking de Guerra:",
                erro
            );


            conteudo.innerHTML = `
                <div
                    class="
                        central-ranking-vazio
                    "
                >
                    ⚠️ ${
                        escaparHtmlCentral(
                            erro.message ||
                            "Erro ao carregar "
                            + "Ranking de Guerra."
                        )
                    }
                </div>
            `;
        }
    }


    // ========================================================
    // ⚔️ RENDERIZAR RANKING DA GUERRA
    // ========================================================

    function renderizarRankingGuerra(
        dados
    ) {
        const conteudo = elemento(
            "central-ranking-conteudo"
        );


        if (!conteudo) {
            return;
        }


        const ranking =
            Array.isArray(
                dados?.ranking
            )
                ? dados.ranking
                : [];


        if (!ranking.length) {

            conteudo.innerHTML = `
                <div
                    class="
                        central-ranking-vazio
                    "
                >
                    ⚔️ Nenhuma Guerra oficial
                    finalizada foi encontrada.
                </div>
            `;

            return;
        }


        const guerrasTotal =
            Number(
                dados
                    ?.guerras_consideradas ||
                0
            );


        let html = `
            <div
                class="
                    central-ranking-vazio
                "
                style="
                    padding:10px;
                    margin-bottom:2px;
                "
            >
                ⚔️ ${
                    guerrasTotal === 1
                        ? "1 guerra oficial contabilizada"
                        : `${guerrasTotal} guerras oficiais contabilizadas`
                }
            </div>
        `;


        html +=
            ranking
                .map(
                    function (
                        clan
                    ) {

                        const posicao =
                            Number(
                                clan.posicao ||
                                0
                            );


                        let classeTop =
                            "";


                        let posicaoTexto =
                            `${posicao}º`;


                        if (
                            posicao === 1
                        ) {

                            classeTop =
                                "top-1";

                            posicaoTexto =
                                "🥇";

                        } else if (
                            posicao === 2
                        ) {

                            classeTop =
                                "top-2";

                            posicaoTexto =
                                "🥈";

                        } else if (
                            posicao === 3
                        ) {

                            classeTop =
                                "top-3";

                            posicaoTexto =
                                "🥉";
                        }


                        const nome =
                            escaparHtmlCentral(
                                clan.nome ||
                                "Clã"
                            );


                        const tag =
                            escaparHtmlCentral(
                                clan.tag ||
                                ""
                            );


                        const logo =
                            escaparHtmlCentral(
                                clan.logo_url ||
                                ""
                            );


                        const logoHtml =
                            logo
                                ? `
                                    <img
                                        src="${logo}"
                                        alt="Brasão de ${nome}"
                                        onerror="
                                            this.style.display='none';
                                            this.nextElementSibling.style.display='block';
                                        "
                                    >

                                    <span
                                        style="
                                            display: none;
                                        "
                                    >
                                        🛡️
                                    </span>
                                `
                                : `
                                    <span>
                                        🛡️
                                    </span>
                                `;


                        const pontos =
                            Number(
                                clan.pontos ||
                                0
                            );


                        const jogos =
                            Number(
                                clan.jogos ||
                                0
                            );


                        const vitorias =
                            Number(
                                clan.vitorias ||
                                0
                            );


                        const empates =
                            Number(
                                clan.empates ||
                                0
                            );


                        const derrotas =
                            Number(
                                clan.derrotas ||
                                0
                            );


                        const frentesVencidas =
                            Number(
                                clan.frentes_vencidas ||
                                0
                            );


                        const frentesPerdidas =
                            Number(
                                clan.frentes_perdidas ||
                                0
                            );


                        const saldo =
                            Number(
                                clan.saldo_frentes ||
                                0
                            );


                        const saldoTexto =
                            saldo > 0
                                ? `+${saldo}`
                                : String(
                                    saldo
                                );


                        return `
                            <div
                                class="
                                    central-ranking-linha
                                    ${classeTop}
                                "
                            >

                                <div
                                    class="
                                        central-ranking-posicao
                                    "
                                >
                                    ${posicaoTexto}
                                </div>


                               <div
                                    class="
                                        central-ranking-logo
                                    "
                                >
                                    ${logoHtml}
                                </div>


                                <div
                                    class="
                                        central-ranking-identidade
                                    "
                                >

                                    <div
                                        class="
                                            central-ranking-nome
                                        "
                                    >
                                        ${nome}

                                        ${
                                            tag
                                                ? `
                                                    <span
                                                        class="
                                                            central-ranking-tag
                                                        "
                                                    >
                                                        [${tag}]
                                                    </span>
                                                `
                                                : ""
                                        }
                                    </div>


                                    <div
                                        class="
                                            central-ranking-info
                                        "
                                    >
                                        ${
                                            jogos === 1
                                                ? "1 guerra"
                                                : `${jogos} guerras`
                                        }
                                        ·
                                        ${
                                            empates === 1
                                                ? "1 empate"
                                                : `${empates} empates`
                                       }

                                        <br>

                                        Vitórias:
                                        ${vitorias}
                                        ·
                                        Derrotas:
                                        ${derrotas}

                                        <br>

                                        Frentes:
                                        ${frentesVencidas}
                                        ${
                                            frentesVencidas === 1
                                                ? "vencida"
                                                : "vencidas"
                                        }
                                        ·
                                        ${frentesPerdidas}
                                        ${
                                            frentesPerdidas === 1
                                                ? "perdida"
                                                : "perdidas"
                                        }
                                    </div>

                                </div>


                                <div
                                    class="
                                        central-ranking-nivel
                                    "
                                >
                                    ${
                                        formatarNumeroCentral(
                                            pontos
                                        )
                                    }
                                    ${
                                        pontos === 1
                                            ? "PT"
                                            : "PTS"
                                    }
                                </div>

                            </div>
                        `;
                    }
                )
                .join("");


        conteudo.innerHTML =
            html;
    }

    // ========================================================
    // ⚔️ GUERRA DE CLÃS
    // ========================================================

    function traduzirFaseGuerra(
        fase
    ) {
        const nomes = {
            inscricoes:
                "Inscrições abertas",

            escalacao:
                "Organização das escalações",

            pareamento:
                "Pareamento dos clãs",

            agendada:
                "Confrontos definidos",

            em_andamento:
                "Guerra em andamento",

            finalizada:
                "Guerra encerrada",

            cancelada:
                "Guerra cancelada"
        };


        return (
            nomes[fase]
            ||
            "Guerra Semanal"
        );
    }


    // ========================================================
    // 📅 FORMATAR DATA
    // ========================================================

    function formatarDataGuerra(
        valor
    ) {
        if (!valor) {
            return "—";
        }


        const data =
            new Date(
                valor
            );


        if (
            Number.isNaN(
                data.getTime()
            )
        ) {
            return "—";
        }


        return new Intl.DateTimeFormat(
            "pt-BR",
            {
                weekday:
                    "short",

                day:
                    "2-digit",

                month:
                    "2-digit",

                hour:
                    "2-digit",

                minute:
                    "2-digit"
            }
        ).format(
            data
        );
    }

    // ========================================================
    // ⚔️ RENDERIZAR CONFRONTO PAREADO
    // ========================================================

    function renderizarConfrontoGuerraCentral(
        dados
    ) {

        const painel = elemento(
            "central-guerra-confronto"
        );


        if (!painel) {
            return;
        }


        const guerra =
            dados.guerra ||
            null;


        const adversario =
            dados.adversario ||
            null;


        /*
         * Enquanto ainda não existir
         * pareamento, o card permanece oculto.
         */
        if (
            !guerra ||
            !adversario
        ) {

            painel.style.display =
                "none";

            return;
        }


        const clan =
            dados.clan ||
            {};


        const clanEl = elemento(
            "central-guerra-confronto-clan"
        );

        const adversarioEl = elemento(
            "central-guerra-confronto-adversario"
        );

        const categoriaEl = elemento(
            "central-guerra-confronto-categoria"
        );

        const frentesEl = elemento(
            "central-guerra-confronto-frentes"
        );

        const statusEl = elemento(
            "central-guerra-confronto-status"
        );

        const faseEl = elemento(
            "central-guerra-confronto-fase"
        );


        const minhaSituacaoEl = elemento(
            "central-guerra-minha-situacao"
        );


        const btnEntrar = elemento(
            "central-guerra-btn-entrar"
        );


        const nomeClan =
            String(
                clan.nome ||
                "Seu clã"
            );


        const tagClan =
            String(
                clan.tag ||
                ""
            );


        const nomeAdversario =
            String(
                adversario.nome ||
                "Clã adversário"
            );


        const tagAdversario =
            String(
                adversario.tag ||
                ""
            );


        const statusGuerra =
            String(
                guerra.status ||
                dados.calendario?.fase ||
                ""
            );


        if (clanEl) {

            clanEl.textContent =
                nomeClan
                +
                (
                    tagClan
                        ? ` [${tagClan}]`
                        : ""
                );
        }


        if (adversarioEl) {

            adversarioEl.textContent =
                nomeAdversario
                +
                (
                    tagAdversario
                        ? ` [${tagAdversario}]`
                        : ""
                );
        }


        if (categoriaEl) {

            categoriaEl.textContent =
                guerra.categoria_nome
                ||
                (
                    guerra.categoria
                        ? `${
                            guerra.categoria
                        } x ${
                            guerra.categoria
                        }`
                        : "—"
                );
        }


        if (frentesEl) {

            const totalFrentes =
                Number(
                    guerra.frentes_total ||
                    0
                );


            frentesEl.textContent =
                totalFrentes === 1
                    ? "1 frente"
                    : `${totalFrentes} frentes`;
        }


        const faseTraduzida =
            traduzirFaseGuerra(
                statusGuerra
            );


        if (statusEl) {

            statusEl.textContent =
                faseTraduzida;
        }


        if (faseEl) {

            faseEl.textContent =
                faseTraduzida;
        }


        // ====================================================
        // 👤 PAPEL OFICIAL DO JOGADOR
        // ====================================================

        const souTitular =
            Boolean(
                dados.sou_titular_guerra
            );


        const souReserva =
            Boolean(
                dados.sou_reserva_guerra
            );


        const podeEntrar =
            Boolean(
                dados.pode_entrar_guerra
            );


        const minhaFrente =
            dados.minha_frente ||
            null;


        const numeroFrente =
            Number(
                minhaFrente?.numero ||
                0
            );


        // ====================================================
        // 🪪 SITUAÇÃO DO JOGADOR
        // ====================================================

        if (minhaSituacaoEl) {

            if (souTitular) {

                minhaSituacaoEl.className =
                    (
                        "central-guerra-minha-participacao "
                        + "inscrito"
                    );


                minhaSituacaoEl.textContent =
                    numeroFrente
                        ? (
                            "⚔️ Você é TITULAR desta guerra "
                            + `e pertence à Frente ${numeroFrente}.`
                        )
                        : (
                            "⚔️ Você é TITULAR "
                            + "desta guerra."
                        );


            } else if (souReserva) {

                minhaSituacaoEl.className =
                    (
                        "central-guerra-minha-participacao "
                        + "nao-inscrito"
                    );


                minhaSituacaoEl.textContent =
                    (
                        "🪑 Você é RESERVA nesta guerra. "
                        + "Aguarde uma convocação."
                    );


            } else {

                minhaSituacaoEl.className =
                    (
                        "central-guerra-minha-participacao "
                        + "nao-inscrito"
                    );


                minhaSituacaoEl.textContent =
                    (
                        "🔒 Você não faz parte da "
                        + "escalação desta guerra."
                    );
            }
        }


        // ====================================================
        // ⚔️ BOTÃO DE ENTRADA
        //
        // IMPORTANTE:
        // O frontend NÃO decide a autorização.
        //
        // Apenas respeita:
        // dados.pode_entrar_guerra
        //
        // calculado pelo backend.
        // ====================================================

        if (btnEntrar) {

            const presentesIds =
                (
                    minhaFrente
                        ?.lobby
                        ?.presentes_ids
                    ||
                    []
                ).map(
                    function (id) {
                        return String(id);
                    }
                );


            const userIdAtual =
                String(
                    localStorage.getItem(
                        "jogadorEldoraID"
                    )
                    ||
                    ""
                );


            const jaNoLobby =
                presentesIds.includes(
                    userIdAtual
                );


            btnEntrar.style.display =
                podeEntrar
                    ? "block"
                    : "none";


            if (jaNoLobby) {

                btnEntrar.disabled =
                    true;


                btnEntrar.textContent =
                    numeroFrente
                        ? `✅ No lobby da Frente ${numeroFrente}`
                        : "✅ No lobby";

            } else {

                btnEntrar.disabled =
                    !podeEntrar;


                btnEntrar.textContent =
                    numeroFrente
                        ? `⚔️ Entrar na Frente ${numeroFrente}`
                        : "⚔️ Entrar na Guerra";
            }
        }


        painel.style.display =
            "block";
    }

    // ========================================================
    // 🏰 RENDERIZAR LOBBY DA FRENTE
    // ========================================================

    function renderizarLobbyGuerraCentral(
        dados
    ) {

        const lobbyEl =
            elemento(
                "central-guerra-lobby"
            );


        if (!lobbyEl) {
            return;
        }


        const frente =
            dados.minha_frente ||
            null;


        /*
         * Somente titulares possuem frente.
         */
        if (!frente) {

            lobbyEl.style.display =
                "none";

            return;
        }


        const lobby =
            frente.lobby ||
            {};


        const presentes =
            new Set(
                (
                    lobby.presentes_ids ||
                    []
                ).map(
                    function (id) {
                        return String(id);
                    }
                )
            );


        const prontos =
            new Set(
                (
                    lobby.prontos_ids ||
                    []
                ).map(
                    function (id) {
                        return String(id);
                    }
                )
            );


        const userId =
            String(
                localStorage.getItem(
                    "jogadorEldoraID"
                )
                ||
                ""
            );


        const estouNoLobby =
            presentes.has(
                userId
            );


        const estouPronto =
            prontos.has(
                userId
            );


        /*
         * Enquanto o jogador ainda não entrou,
         * não mostramos o lobby completo.
         */
        if (!estouNoLobby) {

            lobbyEl.style.display =
                "none";

            return;
        }


        const ladoA =
            frente.clan_a ||
            {};


        const ladoB =
            frente.clan_b ||
            {};


        const jogadoresA =
            Array.isArray(
                ladoA.jogadores
            )
                ? ladoA.jogadores
                : [];


        const jogadoresB =
            Array.isArray(
                ladoB.jogadores
            )
                ? ladoB.jogadores
                : [];


        const titulo =
            elemento(
                "central-guerra-lobby-titulo"
            );


        const contador =
            elemento(
                "central-guerra-lobby-contador"
            );


        const listaA =
            elemento(
                "central-guerra-lobby-clan-a"
            );


        const listaB =
            elemento(
                "central-guerra-lobby-clan-b"
            );


        const prontosEl =
            elemento(
                "central-guerra-lobby-prontos"
            );


        const ordemTurnosEl =
            elemento(
                "central-guerra-ordem-turnos"
            );


        const btnPronto =
            elemento(
                "central-guerra-btn-pronto"
            );


        const feedbackPronto =
            elemento(
                "central-guerra-lobby-feedback"
            );


        if (titulo) {

            titulo.textContent =
                (
                    "🏰 Lobby da Frente "
                    +
                    Number(
                        frente.numero ||
                        0
                    )
                );
        }


        const jogadoresTotal =
            jogadoresA.length
            +
            jogadoresB.length;


        if (contador) {

            contador.textContent =
                `${presentes.size}/${jogadoresTotal}`;
        }


        if (prontosEl) {

            const estadoLobby =
                String(
                    lobby.estado ||
                    ""
                );


            const frentePronta =
                estadoLobby ===
                "pronta_para_combate";


            if (
                frente.batalha?.estado ===
                "preparada"
            ) {

                const batalha =
                    frente.batalha;


                const ordem =
                    Array.isArray(
                        batalha.ordem_turnos
                    )
                        ? batalha.ordem_turnos
                        : [];


                const turnoAtualId =
                    String(
                        batalha.turno_user_id ||
                        ""
                    );


                const meuUserId =
                    String(
                        localStorage.getItem(
                            "jogadorEldoraID"
                        )
                        ||
                        ""
                    );


                const turnoAtual =
                    ordem.find(
                        function (
                            item
                        ) {
                            return (
                                String(
                                    item.user_id ||
                                    ""
                                )
                                ===
                                turnoAtualId
                            );
                        }
                    )
                    ||
                    null;


                const rodada =
                    Number(
                        batalha.rodada ||
                        1
                    );


                const meuTurno =
                    Boolean(
                        turnoAtualId
                        &&
                        turnoAtualId ===
                            meuUserId
                    );


                if (meuTurno) {

                    prontosEl.textContent =
                        (
                            "🟢 É O SEU TURNO "
                            + `— Rodada ${rodada}`
                        );


                } else if (
                    turnoAtual
                ) {

                    prontosEl.textContent =
                        (
                            "⏳ Turno de "
                            + `${
                                turnoAtual.nome ||
                                "Aventureiro"
                            } `
                            + `— Rodada ${rodada}`
                        );


                } else {

                    prontosEl.textContent =
                        "⚔️ Batalha preparada!";
                }


            } else if (frentePronta) {

                prontosEl.textContent =
                    (
                        "⚔️ Frente "
                        + `${
                            Number(
                                frente.numero ||
                                0
                            )
                        } pronta para combate!`
                    );


            } else if (
                jogadoresTotal > 0
                &&
                prontos.size ===
                jogadoresTotal
            ) {

                prontosEl.textContent =
                    (
                        "⏳ Todos estão PRONTOS. "
                        + "Confirmando a frente..."
                    );


            } else {

                prontosEl.textContent =
                    (
                        `✅ Prontos: ${
                            prontos.size
                        }/${jogadoresTotal}`
                    );
            }
        }


        // ====================================================
        // ⚡ ORDEM OFICIAL DE INICIATIVA
        // ====================================================

        if (ordemTurnosEl) {

            const batalha =
                frente.batalha ||
                null;


            const ordemTurnos =
                Array.isArray(
                    batalha?.ordem_turnos
                )
                    ? batalha.ordem_turnos
                    : [];


            const turnoAtualId =
                String(
                    batalha?.turno_user_id ||
                    ""
                );


            if (
                batalha?.estado ===
                    "preparada"
                &&
                ordemTurnos.length
            ) {

                let htmlOrdem = `
                    <div
                        style="
                            margin-bottom:7px;
                            color:#f4dc91;
                            font-size:0.62rem;
                            font-weight:900;
                            text-align:center;
                        "
                    >
                        ⚡ ORDEM DE INICIATIVA
                    </div>
                `;


                htmlOrdem +=
                    ordemTurnos
                        .map(
                            function (
                                item
                            ) {

                                const userIdItem =
                                    String(
                                        item.user_id ||
                                        ""
                                    );


                                const turnoAtual =
                                    userIdItem ===
                                    turnoAtualId;


                                const posicao =
                                    Number(
                                        item.posicao ||
                                        0
                                    );


                                const nome =
                                    escaparHtmlCentral(
                                        item.nome ||
                                        "Aventureiro"
                                    );


                                const iniciativa =
                                    Number(
                                        item.initiative ||
                                        0
                                    );


                                const lado =
                                    String(
                                        item.lado ||
                                        ""
                                    )
                                    .toUpperCase();


                                return `
                                    <div
                                        style="
                                            display:grid;
                                            grid-template-columns:
                                                24px
                                                minmax(0,1fr)
                                                auto;
                                            align-items:center;
                                            gap:7px;
                                            margin-top:5px;
                                            padding:7px;
                                            ${
                                                turnoAtual
                                                    ? (
                                                        "background:"
                                                        + "rgba(161,98,7,0.22);"
                                                        + "border:"
                                                        + "1px solid "
                                                        + "rgba(250,204,21,0.30);"
                                                    )
                                                    : (
                                                        "background:"
                                                        + "rgba(2,6,13,0.35);"
                                                        + "border:"
                                                        + "1px solid "
                                                        + "rgba(148,163,184,0.12);"
                                                    )
                                            }
                                            border-radius:7px;
                                        "
                                    >

                                        <strong
                                            style="
                                                color:${
                                                    turnoAtual
                                                        ? "#fde68a"
                                                        : "#94a3b8"
                                                };
                                                font-size:0.60rem;
                                                text-align:center;
                                            "
                                        >
                                            ${posicao}º
                                        </strong>


                                        <div
                                            style="
                                                min-width:0;
                                            "
                                        >
                                            <div
                                                style="
                                                    overflow:hidden;
                                                    color:#edf2f7;
                                                    font-size:0.62rem;
                                                    font-weight:900;
                                                    text-overflow:ellipsis;
                                                    white-space:nowrap;
                                                "
                                            >
                                                ${
                                                    turnoAtual
                                                        ? "▶ "
                                                        : ""
                                                }${nome}
                                            </div>

                                            <div
                                                style="
                                                    margin-top:2px;
                                                    color:#7f8da0;
                                                    font-size:0.52rem;
                                                "
                                            >
                                                Lado ${lado}
                                            </div>
                                        </div>


                                        <span
                                            style="
                                                color:#d9f99d;
                                                font-size:0.56rem;
                                                font-weight:900;
                                            "
                                        >
                                            ⚡ ${iniciativa}
                                        </span>

                                    </div>
                                `;
                            }
                        )
                        .join("");


                ordemTurnosEl.innerHTML =
                    htmlOrdem;


                ordemTurnosEl.style.display =
                    "block";


            } else {

                ordemTurnosEl.innerHTML =
                    "";

                ordemTurnosEl.style.display =
                    "none";
            }
        }


        if (btnPronto) {

            btnPronto.style.display =
                "block";


            const batalhaPreparada =
                frente.batalha?.estado ===
                "preparada";


            if (batalhaPreparada) {

                btnPronto.disabled =
                    false;


                btnPronto.textContent =
                    "⚔️ Entrar no Combate";


                btnPronto.dataset.acaoGuerra =
                    "combate";


            } else {

                btnPronto.disabled =
                    estouPronto;


                btnPronto.textContent =
                    estouPronto
                        ? "✅ Você está PRONTO"
                        : "✅ Estou PRONTO";


                btnPronto.dataset.acaoGuerra =
                    "pronto";
            }
        }


        if (feedbackPronto) {

            feedbackPronto.style.display =
                "none";

            feedbackPronto.textContent =
                "";
        }


        function criarLinhaLobby(
            jogador
        ) {

            const id =
                String(
                    jogador.user_id ||
                    ""
                );


            const presente =
                presentes.has(
                    id
                );


            const pronto =
                prontos.has(
                    id
                );


            const nome =
                escaparHtmlCentral(
                    jogador.nome ||
                    "Aventureiro"
                );


            const nivel =
                Number(
                    jogador.nivel ||
                    1
                );


            const classe =
                escaparHtmlCentral(
                    String(
                        jogador.classe ||
                        "aventureiro"
                    )
                    .replaceAll(
                        "_",
                        " "
                    )
                );


            return `
                <div
                    class="
                        central-guerra-jogador
                    "
                >

                    <div
                        class="
                            central-guerra-jogador-check
                        "
                    >
                        ${
                            pronto
                                ? "⚔️"
                                : (
                                    presente
                                        ? "✅"
                                        : "⏳"
                                )
                        }
                    </div>


                    <div
                        class="
                            central-guerra-jogador-info
                        "
                    >

                        <div
                            class="
                                central-guerra-jogador-nome
                            "
                        >
                            ${nome}
                        </div>


                        <div
                            class="
                                central-guerra-jogador-detalhe
                            "
                        >
                            Nv. ${nivel}
                            ·
                            ${classe}
                        </div>

                    </div>


                    <span
                        class="
                            central-guerra-jogador-funcao
                            ${
                                pronto
                                    ? "titular"
                                    : (
                                        presente
                                            ? "titular"
                                            : "reserva"
                                    )
                            }
                        "
                    >
                        ${
                            pronto
                                ? "PRONTO"
                                : (
                                    presente
                                        ? "PRESENTE"
                                        : "AGUARDANDO"
                                )
                        }
                    </span>

                </div>
            `;
        }


        if (listaA) {

            listaA.innerHTML =
                jogadoresA
                    .map(
                        criarLinhaLobby
                    )
                    .join("");
        }


        if (listaB) {

            listaB.innerHTML =
                jogadoresB
                    .map(
                        criarLinhaLobby
                    )
                    .join("");
        }


        lobbyEl.style.display =
            "block";
    }

    // ========================================================
    // ⚔️ TELA DA BATALHA 5X5
    // ========================================================

    function fecharCombateGuerraCentral() {

        const modal =
            elemento(
                "central-guerra-combate-modal"
            );


        if (modal) {

            modal.style.display =
                "none";
        }
    }


    function garantirTelaCombateGuerraCentral() {

        let modal =
            elemento(
                "central-guerra-combate-modal"
            );


        if (modal) {

            return modal;
        }


        document.body.insertAdjacentHTML(
            "beforeend",
            `
                <style
                    id="central-guerra-combate-style"
                >

                    #central-guerra-combate-modal {
                        position:fixed;
                        inset:0;
                        z-index:10090;

                        display:none;
                        align-items:center;
                        justify-content:center;

                        padding:8px;

                        background:
                            rgba(2,6,13,0.94);

                        backdrop-filter:
                            blur(8px);

                        -webkit-backdrop-filter:
                            blur(8px);
                    }


                    #central-guerra-combate-modal * {
                        box-sizing:border-box;
                    }


                    .central-guerra-combate-painel {
                        width:min(
                            900px,
                            calc(100vw - 16px)
                        );

                        height:min(
                            900px,
                            calc(100dvh - 16px)
                        );

                        display:flex;
                        flex-direction:column;

                        overflow:hidden;

                        background:
                            radial-gradient(
                                circle at 50% 0%,
                                rgba(216,184,90,0.11),
                                transparent 260px
                            ),
                            linear-gradient(
                                180deg,
                                #111827,
                                #060a11
                            );

                        border:
                            1px solid
                            rgba(216,184,90,0.55);

                        border-radius:18px;

                        box-shadow:
                            0 25px 80px
                            rgba(0,0,0,0.85);
                    }


                    .central-guerra-combate-header {
                        flex:0 0 auto;

                        display:flex;
                        align-items:center;
                        justify-content:space-between;

                        gap:10px;

                        padding:12px;

                        background:
                            rgba(15,23,42,0.96);

                        border-bottom:
                            1px solid
                            rgba(216,184,90,0.25);
                    }


                    .central-guerra-combate-header strong {
                        display:block;

                        color:#f4dc91;

                        font-family:
                            "Cinzel",
                            serif;

                        font-size:0.82rem;
                    }


                    .central-guerra-combate-header span {
                        display:block;

                        margin-top:3px;

                        color:#7f8da0;

                        font-size:0.58rem;
                    }


                    #central-guerra-combate-fechar {
                        width:36px;
                        height:36px;

                        flex:0 0 36px;

                        color:#fca5a5;

                        background:
                            rgba(127,29,29,0.20);

                        border:
                            1px solid
                            rgba(248,113,113,0.28);

                        border-radius:10px;

                        font-weight:900;
                    }


                    .central-guerra-combate-scroll {
                        flex:1;
                        min-height:0;

                        overflow-y:auto;

                        padding:10px;

                        overscroll-behavior:
                            contain;
                    }


                    .central-guerra-combate-turno {
                        margin-bottom:10px;
                        padding:10px;

                        text-align:center;

                        border-radius:10px;

                        font-size:0.68rem;
                        font-weight:900;
                    }


                    .central-guerra-combate-turno.meu {
                        color:#bbf7d0;

                        background:
                            rgba(22,101,52,0.25);

                        border:
                            1px solid
                            rgba(74,222,128,0.30);
                    }


                    .central-guerra-combate-turno.outro {
                        color:#fde68a;

                        background:
                            rgba(161,98,7,0.20);

                        border:
                            1px solid
                            rgba(250,204,21,0.26);
                    }


                    .central-guerra-combate-arena {
                        display:grid;

                        grid-template-columns:
                            minmax(0,1fr)
                            minmax(0,1fr);

                        gap:8px;
                    }


                    .central-guerra-combate-time {
                        min-width:0;

                        padding:8px;

                        background:
                            rgba(2,6,13,0.38);

                        border:
                            1px solid
                            rgba(148,163,184,0.14);

                        border-radius:11px;
                    }


                    .central-guerra-combate-time-titulo {
                        min-height:34px;

                        display:flex;
                        align-items:center;
                        justify-content:center;

                        margin-bottom:7px;

                        color:#f5e7b3;

                        font-family:
                            "Cinzel",
                            serif;

                        font-size:0.62rem;
                        font-weight:900;

                        text-align:center;
                    }


                    .central-guerra-combatente {
                        position:relative;

                        margin-top:6px;
                        padding:7px;

                        overflow:hidden;

                        background:
                            rgba(15,23,42,0.72);

                        border:
                            1px solid
                            rgba(148,163,184,0.15);

                        border-radius:8px;
                    }


                    .central-guerra-combatente.turno {
                        background:
                            rgba(113,83,21,0.28);

                        border-color:
                            rgba(250,204,21,0.48);

                        box-shadow:
                            0 0 12px
                            rgba(216,184,90,0.09);
                    }


                    .central-guerra-combatente.derrotado {
                        opacity:0.48;
                    }


                    .central-guerra-combatente-nome {
                        overflow:hidden;

                        color:#f1f5f9;

                        font-size:0.61rem;
                        font-weight:900;

                        white-space:nowrap;
                        text-overflow:ellipsis;
                    }


                    .central-guerra-combatente-info {
                        margin-top:2px;

                        color:#7f8da0;

                        font-size:0.48rem;
                    }


                    .central-guerra-barra-info {
                        display:flex;
                        justify-content:space-between;

                        gap:4px;

                        margin-top:5px;

                        color:#9ca3af;

                        font-size:0.45rem;
                        font-weight:800;
                    }


                    .central-guerra-barra {
                        width:100%;
                        height:6px;

                        margin-top:2px;

                        overflow:hidden;

                        background:
                            rgba(0,0,0,0.55);

                        border-radius:999px;
                    }


                    .central-guerra-barra-hp {
                        height:100%;

                        background:
                            linear-gradient(
                                90deg,
                                #166534,
                                #22c55e
                            );
                    }


                    .central-guerra-barra-mp {
                        height:100%;

                        background:
                            linear-gradient(
                                90deg,
                                #1e40af,
                                #3b82f6
                            );
                    }


                    .central-guerra-combate-acoes {
                        margin-top:10px;
                        padding:10px;

                        color:#7f8da0;

                        background:
                            rgba(2,6,13,0.40);

                        border:
                            1px solid
                            rgba(148,163,184,0.13);

                        border-radius:10px;

                        text-align:center;

                        font-size:0.60rem;
                    }


                    @media (
                        max-width:430px
                    ) {

                        .central-guerra-combate-scroll {
                            padding:7px;
                        }


                        .central-guerra-combate-arena {
                            gap:5px;
                        }


                        .central-guerra-combate-time {
                            padding:5px;
                        }


                        .central-guerra-combatente {
                            padding:6px 5px;
                        }


                        .central-guerra-combatente-nome {
                            font-size:0.56rem;
                        }


                        .central-guerra-combatente-info {
                            font-size:0.44rem;
                        }
                    }

                </style>


                <div
                    id="central-guerra-combate-modal"
                    aria-hidden="true"
                >

                    <div
                        class="
                            central-guerra-combate-painel
                        "
                    >

                        <div
                            class="
                                central-guerra-combate-header
                            "
                        >

                            <div>
                                <strong
                                    id="central-guerra-combate-titulo"
                                >
                                    ⚔️ Guerra de Clãs
                                </strong>

                                <span
                                    id="central-guerra-combate-subtitulo"
                                >
                                    Frente
                                </span>
                            </div>


                            <button
                                type="button"
                                id="central-guerra-combate-fechar"
                            >
                                ✕
                            </button>

                        </div>


                        <div
                            class="
                                central-guerra-combate-scroll
                            "
                        >

                            <div
                                id="central-guerra-combate-turno"
                                class="
                                    central-guerra-combate-turno
                                "
                            >
                            </div>


                            <div
                                class="
                                    central-guerra-combate-arena
                                "
                            >

                                <div
                                    class="
                                        central-guerra-combate-time
                                    "
                                >
                                    <div
                                        id="central-guerra-combate-clan-a"
                                        class="
                                            central-guerra-combate-time-titulo
                                        "
                                    >
                                        Clã A
                                    </div>

                                    <div
                                        id="central-guerra-combate-jogadores-a"
                                    >
                                    </div>
                                </div>


                                <div
                                    class="
                                        central-guerra-combate-time
                                    "
                                >
                                    <div
                                        id="central-guerra-combate-clan-b"
                                        class="
                                            central-guerra-combate-time-titulo
                                        "
                                    >
                                        Clã B
                                    </div>

                                    <div
                                        id="central-guerra-combate-jogadores-b"
                                    >
                                    </div>
                                </div>

                            </div>


                            <div
                                class="
                                    central-guerra-combate-acoes
                                "
                            >
                                ⚔️ Comandos de batalha serão
                                liberados na próxima etapa.
                            </div>

                        </div>

                    </div>

                </div>
            `
        );


        modal =
            elemento(
                "central-guerra-combate-modal"
            );


        const fechar =
            elemento(
                "central-guerra-combate-fechar"
            );


        if (fechar) {

            fechar.addEventListener(
                "click",
                fecharCombateGuerraCentral
            );
        }


        if (modal) {

            modal.addEventListener(
                "click",
                function (
                    evento
                ) {

                    if (
                        evento.target ===
                        modal
                    ) {

                        fecharCombateGuerraCentral();
                    }
                }
            );
        }


        return modal;
    }


    function criarCardCombatenteGuerra(
        combatente,
        turnoAtualId,
        meuUserId
    ) {

        const userId =
            String(
                combatente.user_id ||
                ""
            );


        const stats =
            combatente.stats ||
            {};


        const hpMax =
            Math.max(
                1,
                Number(
                    stats.max_hp ||
                    1
                )
            );


        const hpAtual =
            Math.max(
                0,
                Math.min(
                    hpMax,
                    Number(
                        combatente.hp_atual ||
                        0
                    )
                )
            );


        const mpMax =
            Math.max(
                0,
                Number(
                    stats.max_mana ||
                    0
                )
            );


        const mpAtual =
            Math.max(
                0,
                Math.min(
                    mpMax,
                    Number(
                        combatente.mp_atual ||
                        0
                    )
                )
            );


        const hpPercentual =
            Math.max(
                0,
                Math.min(
                    100,
                    (
                        hpAtual /
                        hpMax
                    ) * 100
                )
            );


        const mpPercentual =
            mpMax > 0
                ? Math.max(
                    0,
                    Math.min(
                        100,
                        (
                            mpAtual /
                            mpMax
                        ) * 100
                    )
                )
                : 0;


        const vivo =
            combatente.vivo !== false
            &&
            hpAtual > 0;


        const turno =
            userId ===
            turnoAtualId;


        const souEu =
            userId ===
            meuUserId;


        const nome =
            escaparHtmlCentral(
                combatente.nome ||
                "Aventureiro"
            );


        const classe =
            escaparHtmlCentral(
                String(
                    combatente.classe ||
                    "aventureiro"
                )
                .replaceAll(
                    "_",
                    " "
                )
            );


        const nivel =
            Number(
                combatente.nivel ||
                1
            );


        return `
            <div
                class="
                    central-guerra-combatente
                    ${
                        turno
                            ? "turno"
                            : ""
                    }
                    ${
                        vivo
                            ? ""
                            : "derrotado"
                    }
                "
            >

                <div
                    class="
                        central-guerra-combatente-nome
                    "
                >
                    ${
                        turno
                            ? "▶ "
                            : ""
                    }

                    ${nome}

                    ${
                        souEu
                            ? " · VOCÊ"
                            : ""
                    }
                </div>


                <div
                    class="
                        central-guerra-combatente-info
                    "
                >
                    ${
                        vivo
                            ? `Nv. ${nivel} · ${classe}`
                            : "💀 DERROTADO"
                    }
                </div>


                <div
                    class="
                        central-guerra-barra-info
                    "
                >
                    <span>
                        ❤️ HP
                    </span>

                    <span>
                        ${hpAtual}/${hpMax}
                    </span>
                </div>


                <div
                    class="
                        central-guerra-barra
                    "
                >
                    <div
                        class="
                            central-guerra-barra-hp
                        "
                        style="
                            width:${hpPercentual}%;
                        "
                    >
                    </div>
                </div>


                <div
                    class="
                        central-guerra-barra-info
                    "
                >
                    <span>
                        🔷 MP
                    </span>

                    <span>
                        ${mpAtual}/${mpMax}
                    </span>
                </div>


                <div
                    class="
                        central-guerra-barra
                    "
                >
                    <div
                        class="
                            central-guerra-barra-mp
                        "
                        style="
                            width:${mpPercentual}%;
                        "
                    >
                    </div>
                </div>

            </div>
        `;
    }


    function renderizarTelaCombateGuerraCentral(
        dados
    ) {

        const frente =
            dados?.minha_frente ||
            null;


        const batalha =
            frente?.batalha ||
            null;


        if (
            !frente
            ||
            batalha?.estado !==
                "preparada"
        ) {

            return false;
        }


        const combatentes =
            Array.isArray(
                batalha.combatentes
            )
                ? batalha.combatentes
                : [];


        if (!combatentes.length) {

            return false;
        }


        garantirTelaCombateGuerraCentral();


        const meuUserId =
            String(
                localStorage.getItem(
                    "jogadorEldoraID"
                )
                ||
                ""
            );


        const turnoAtualId =
            String(
                batalha.turno_user_id ||
                ""
            );


        const turnoAtual =
            combatentes.find(
                function (
                    combatente
                ) {

                    return (
                        String(
                            combatente.user_id ||
                            ""
                        )
                        ===
                        turnoAtualId
                    );
                }
            )
            ||
            null;


        const jogadoresA =
            combatentes.filter(
                function (
                    combatente
                ) {

                    return (
                        String(
                            combatente.lado ||
                            ""
                        ).toLowerCase()
                        ===
                        "a"
                    );
                }
            );


        const jogadoresB =
            combatentes.filter(
                function (
                    combatente
                ) {

                    return (
                        String(
                            combatente.lado ||
                            ""
                        ).toLowerCase()
                        ===
                        "b"
                    );
                }
            );


        // ====================================================
        // 🏰 NOMES DOS CLÃS VÊM DO DOCUMENTO OFICIAL
        // ====================================================

        const clans =
            Array.isArray(
                dados.guerra?.clans
            )
                ? dados.guerra.clans
                : [];


        const clanA =
            clans.find(
                function (
                    clan
                ) {

                    return (
                        String(
                            clan.lado ||
                            ""
                        ).toLowerCase()
                        ===
                        "a"
                    );
                }
            )
            ||
            {};


        const clanB =
            clans.find(
                function (
                    clan
                ) {

                    return (
                        String(
                            clan.lado ||
                            ""
                        ).toLowerCase()
                        ===
                        "b"
                    );
                }
            )
            ||
            {};


        const nomeClanA =
            String(
                clanA.nome ||
                "Clã A"
            );


        const nomeClanB =
            String(
                clanB.nome ||
                "Clã B"
            );


        const tagClanA =
            String(
                clanA.tag ||
                ""
            );


        const tagClanB =
            String(
                clanB.tag ||
                ""
            );


        const titulo =
            elemento(
                "central-guerra-combate-titulo"
            );


        const subtitulo =
            elemento(
                "central-guerra-combate-subtitulo"
            );


        const turnoEl =
            elemento(
                "central-guerra-combate-turno"
            );


        const clanAEl =
            elemento(
                "central-guerra-combate-clan-a"
            );


        const clanBEl =
            elemento(
                "central-guerra-combate-clan-b"
            );


        const jogadoresAEl =
            elemento(
                "central-guerra-combate-jogadores-a"
            );


        const jogadoresBEl =
            elemento(
                "central-guerra-combate-jogadores-b"
            );


        if (titulo) {

            titulo.textContent =
                "⚔️ Guerra de Clãs";
        }


        if (subtitulo) {

            subtitulo.textContent =
                (
                    `Frente ${
                        Number(
                            frente.numero ||
                            0
                        )
                    } · `
                    +
                    `Rodada ${
                        Number(
                            batalha.rodada ||
                            1
                        )
                    }`
                );
        }


        if (clanAEl) {

            clanAEl.textContent =
                nomeClanA
                +
                (
                    tagClanA
                        ? ` [${tagClanA}]`
                        : ""
                );
        }


        if (clanBEl) {

            clanBEl.textContent =
                nomeClanB
                +
                (
                    tagClanB
                        ? ` [${tagClanB}]`
                        : ""
                );
        }


        if (turnoEl) {

            const meuTurno =
                turnoAtualId
                &&
                turnoAtualId ===
                    meuUserId;


            turnoEl.className =
                (
                    "central-guerra-combate-turno "
                    +
                    (
                        meuTurno
                            ? "meu"
                            : "outro"
                    )
                );


            if (meuTurno) {

                turnoEl.textContent =
                    (
                        "🟢 É O SEU TURNO "
                        + `— Rodada ${
                            Number(
                                batalha.rodada ||
                                1
                            )
                        }`
                    );


            } else {

                turnoEl.textContent =
                    (
                        "⏳ Turno de "
                        + `${
                            turnoAtual?.nome ||
                            "Aventureiro"
                        } `
                        + `— Rodada ${
                            Number(
                                batalha.rodada ||
                                1
                            )
                        }`
                    );
            }
        }


        if (jogadoresAEl) {

            jogadoresAEl.innerHTML =
                jogadoresA
                    .map(
                        function (
                            combatente
                        ) {

                            return (
                                criarCardCombatenteGuerra(
                                    combatente,
                                    turnoAtualId,
                                    meuUserId
                                )
                            );
                        }
                    )
                    .join("");
        }


        if (jogadoresBEl) {

            jogadoresBEl.innerHTML =
                jogadoresB
                    .map(
                        function (
                            combatente
                        ) {

                            return (
                                criarCardCombatenteGuerra(
                                    combatente,
                                    turnoAtualId,
                                    meuUserId
                                )
                            );
                        }
                    )
                    .join("");
        }


        return true;
    }


    async function abrirCombateGuerraCentral() {

        if (
            !estadoGuerraCentral
        ) {
            return;
        }


        // ====================================================
        // ⚔️ CARREGA MOTOR VISUAL DA GUERRA UMA ÚNICA VEZ
        // ====================================================

        if (
            typeof window.abrirBatalhaGuerraCla
            !== "function"
        ) {

            let script =
                document.getElementById(
                    "script-clan-war-battle"
                );


            if (!script) {

                script =
                    document.createElement(
                        "script"
                    );


                script.id =
                    "script-clan-war-battle";


                script.src =
                    (
                        "/static/js/"
                        + "clan_war_battle.js"
                        + "?v="
                        + Date.now()
                    );


                document.body.appendChild(
                    script
                );
            }


            await new Promise(
                function (
                    resolve,
                    reject
                ) {

                    if (
                        typeof window
                            .abrirBatalhaGuerraCla
                        === "function"
                    ) {

                        resolve();

                        return;
                    }


                    script.addEventListener(
                        "load",
                        resolve,
                        {
                            once:
                                true
                        }
                    );


                    script.addEventListener(
                        "error",
                        reject,
                        {
                            once:
                                true
                        }
                    );
                }
            );
        }


        if (
            typeof window.abrirBatalhaGuerraCla
            === "function"
        ) {

            window
                .abrirBatalhaGuerraCla(
                    estadoGuerraCentral
                );
        }
    }

    // ========================================================
    // 📡 CARREGAR ESTADO
    // ========================================================

    async function carregarEstadoGuerraCentral() {

        if (
            carregandoGuerraCentral
        ) {
            return;
        }


        const userId =
            localStorage.getItem(
                "jogadorEldoraID"
            );


        if (!userId) {
            return;
        }


        carregandoGuerraCentral =
            true;


        const status = elemento(
            "central-guerra-status"
        );

        const mensagem = elemento(
            "central-guerra-mensagem"
        );


        if (status) {
            status.className =
                "central-guerra-status";

            status.textContent =
                "⏳ CONSULTANDO O REINO...";
        }


        if (mensagem) {
            mensagem.textContent =
                "Consultando os registros "
                + "da Guerra de Clãs...";
        }


        try {

            const resposta =
                await fetch(
                    (
                        "/api/clan/guerra/estado/"
                        +
                        encodeURIComponent(
                            userId
                        )
                        +
                        "?t="
                        +
                        Date.now()
                    ),
                    {
                        method:
                            "GET",

                        cache:
                            "no-store"
                    }
                );


            const dados =
                await resposta.json();


            if (
                !resposta.ok ||
                dados.success === false
            ) {

                throw new Error(
                    dados.error ||
                    "Não foi possível consultar "
                    + "a Guerra de Clãs."
                );
            }


            estadoGuerraCentral =
                dados;


            renderizarEstadoGuerraCentral(
                dados
            );


        } catch (
            erro
        ) {

            console.error(
                "❌ [CENTRAL] Guerra de Clãs:",
                erro
            );


            if (status) {
                status.className =
                    (
                        "central-guerra-status "
                        + "status-fechada"
                    );

                status.textContent =
                    "⚠️ INDISPONÍVEL";
            }


            if (mensagem) {
                mensagem.textContent =
                    erro.message ||
                    "Não foi possível carregar "
                    + "a Guerra de Clãs.";
            }

        } finally {
  
            carregandoGuerraCentral =
                false;
        }
    }
    
    // ========================================================
    // 👥 PROGRESSO DA FORMAÇÃO DA GUERRA
   // ========================================================

    function obterProximaMetaGuerra(
        total,
        maximo
    ) {
        total =
            Number(
                total || 0
            );


        maximo =
            Number(
                maximo || 5
            );


        const categorias = [
            5,
            10,
            15,
            20,
            25
        ];


        const liberadas =
            categorias.filter(
                function (
                    tamanho
                ) {
                    return (
                        tamanho <=
                        maximo
                    );
                }
            );


        for (
            const tamanho
            of liberadas
        ) {

            if (
                total <
                tamanho
            ) {

                return {
                    proxima:
                        tamanho,
 
                    faltam:
                        tamanho - total,
  
                    maxima:
                        false
                };
            }
        }


        return {
            proxima:
                maximo,

            faltam:
                0,

            maxima:
                true
        };
    }


    // ========================================================
    // 👥 RENDERIZAR PARTICIPAÇÃO
    // ========================================================

    function renderizarParticipacaoGuerraCentral(
        dados
    ) {
        const painel = elemento(
            "central-guerra-participacao"
        );

        const totalEl = elemento(
            "central-guerra-participantes-total"
        );

        const badge = elemento(
            "central-guerra-participantes-badge"
        );

        const categoriaEl = elemento(
            "central-guerra-categoria-efetiva"
        );

        const proximaMetaEl = elemento(
            "central-guerra-proxima-meta"
        );

        const progressoTexto = elemento(
            "central-guerra-progresso-texto"
        );

        const progressoNumero = elemento(
            "central-guerra-progresso-numero"
        );

        const progressoBarra = elemento(
            "central-guerra-progresso-preenchimento"
        );

        const minhaParticipacao = elemento(
            "central-guerra-minha-participacao"
        );

        const btnParticipar = elemento(
            "central-guerra-btn-participar"
        );

        const btnSair = elemento(
            "central-guerra-btn-sair"
        );


        /*
         * Sem inscrição do clã não existe
         * inscrição individual.
         */
        if (
            !dados.inscricao
        ) {

            if (painel) {
                painel.style.display =
                    "none";
            }

            return;
        }


        if (painel) {
            painel.style.display =
                "block";
        }


        const total =
            Number(
                dados.participantes_total ||
                0
            );


        const maximo =
            Number(
                dados.clan?.categoria_maxima ||
                5
            );


        const categoriaAtual =
            dados.categoria_efetiva_nome ||
            null;


        const meta =
            obterProximaMetaGuerra(
                total,
                maximo
            );

        const quorum =
            dados.quorum ||
            {};


        const quorumStatus =
            String(
                quorum.status ||
                ""
            );


        const inscricoesAbertas =
            Boolean(
                dados.calendario
                    ?.inscricoes_abertas
            );


        const semQuorum =
            quorumStatus ===
            "sem_quorum";


        const quorumAprovado =
            quorumStatus ===
            "aprovado";


        const minimoQuorum =
            Number(
                quorum.minimo ||
                5
            );

        // ====================================================
        // 👥 CONTADOR
        // ====================================================

        if (totalEl) {
            totalEl.textContent =
                String(
                    total
                );
        }


        if (badge) {
            badge.textContent =
                (
                    total === 1
                        ? "1 inscrito"
                        : `${total} inscritos`
                );
        }


        // ====================================================
        // ⚔️ CATEGORIA ATUAL
        // ====================================================

        if (categoriaEl) {

            if (semQuorum) {

                categoriaEl.textContent =
                    "Sem quórum";

            } else if (categoriaAtual) {

                categoriaEl.textContent =
                    categoriaAtual;

            } else {

                categoriaEl.textContent =
                    inscricoesAbertas
                        ? "Aguardando 5"
                        : "Não formada";
           }
        }


        // ====================================================
        // 🎯 PRÓXIMA META
        // ====================================================

        if (proximaMetaEl) {

            if (!inscricoesAbertas) {

                if (semQuorum) {

                    proximaMetaEl.textContent =
                        "Encerrada";

                } else if (
                    quorumAprovado
                ) {

                    proximaMetaEl.textContent =
                        "Escalação";

                } else {

                    proximaMetaEl.textContent =
                        "Encerrada";
                }

            } else if (
                meta.maxima
            ) {

                proximaMetaEl.textContent =
                    "Máxima atingida";

            } else {

                proximaMetaEl.textContent =
                    `${meta.faltam} p/ ${meta.proxima}x${meta.proxima}`;
            }
        }

        // ====================================================
        // 📊 BARRA
        // ====================================================

        let progresso =
            0;


        /*
         * Depois que as inscrições fecham,
         * a barra deixa de mostrar a próxima
         * categoria e passa a mostrar o
         * resultado final da formação.
         */
        if (
            !inscricoesAbertas
        ) {

            if (semQuorum) {

                progresso =
                    Math.max(
                        0,
                        Math.min(
                            100,
                            (
                                total /
                                minimoQuorum
                            ) * 100
                        )
                    );


                if (progressoNumero) {
                    progressoNumero.textContent =
                        `${total}/${minimoQuorum}`;
                }


                if (progressoTexto) {
                    progressoTexto.textContent =
                        (
                            "Inscrições encerradas: "
                            + `${total}/${minimoQuorum} `
                            + "guerreiros. "
                            + "Clã sem quórum."
                        );
                }

            } else if (
                quorumAprovado
            ) {

                progresso =
                    100;


                if (progressoNumero) {
                    progressoNumero.textContent =
                        `${total} inscritos`;
                }


                if (progressoTexto) {
                    progressoTexto.textContent =
                        (
                            "Inscrições encerradas. "
                            + "Formação definida em "
                            + `${
                                categoriaAtual ||
                                "5 x 5"
                            }.`
                        );
                }

            } else {

                progresso =
                    0;


                if (progressoNumero) {
                    progressoNumero.textContent =
                        `${total}`;
                }


                if (progressoTexto) {
                    progressoTexto.textContent =
                        "Período de inscrições encerrado.";
                }
            }

        } else {

            // ====================================================
            // INSCRIÇÕES AINDA ABERTAS
            // ====================================================

            let inicioMeta =
                0;


            if (
                meta.proxima > 5
            ) {
                inicioMeta =
                    meta.proxima - 5;
            }


            if (meta.maxima) {

                progresso =
                    100;

            } else {

                const quantidadeFaixa =
                    total - inicioMeta;


                progresso =
                    Math.max(
                        0,
                        Math.min(
                            100,
                            (
                                quantidadeFaixa /
                                5
                            ) * 100
                        )
                    );
            }


            if (progressoNumero) {

                if (meta.maxima) {

                    progressoNumero.textContent =
                        `${total}/${maximo}`;

                } else {

                    progressoNumero.textContent =
                        `${total}/${meta.proxima}`;
                }
            }


            if (progressoTexto) {

                if (
                    total < 5
                ) {

                    progressoTexto.textContent =
                        (
                            `Faltam ${
                                5 - total
                            } guerreiros para formar 5x5`
                        );

                } else if (
                    meta.maxima
                ) {

                    progressoTexto.textContent =
                        (
                            total > maximo
                                ? "Categoria máxima formada; excedentes poderão ser reservas"
                                : "Categoria máxima disponível formada"
                        );

                } else {

                    progressoTexto.textContent =
                        (
                            `Faltam ${
                                meta.faltam
                            } para liberar ${
                                meta.proxima
                            }x${
                                meta.proxima
                            }`
                        );
                }
            }
        }


        if (progressoBarra) {

            progressoBarra.style.width =
                `${progresso}%`;
        }


        // ====================================================
        // 👤 ESTADO DO JOGADOR
        // ====================================================

        if (
            !inscricoesAbertas
        ) {

            if (btnParticipar) {
                btnParticipar.style.display =
                    "none";
            }


            if (btnSair) {
                btnSair.style.display =
                    "none";
            }


            if (minhaParticipacao) {

                if (semQuorum) {

                    minhaParticipacao.className =
                        (
                            "central-guerra-minha-participacao "
                            + "nao-inscrito"
                        );
        
        
                    minhaParticipacao.innerHTML =
                        `
                            ❌ O clã não atingiu o mínimo
                            de ${minimoQuorum} guerreiros
                            nesta semana.
                        `;
        
                } else if (
                    quorumAprovado &&
                    dados.estou_inscrito
                ) {
        
                    minhaParticipacao.className =
                        (
                            "central-guerra-minha-participacao "
                            + "inscrito"
                        );
        
        
                    minhaParticipacao.innerHTML =
                        `
                            ✅ Você está entre os guerreiros
                            inscritos. Aguarde a escalação
                            oficial do clã.
                        `;
        
                } else {
        
                    minhaParticipacao.className =
                        (
                            "central-guerra-minha-participacao "
                            + "nao-inscrito"
                        );
        
        
                    minhaParticipacao.innerHTML =
                        `
                            🔒 O período de inscrição
                            dos guerreiros foi encerrado.
                        `;
                }
            }


            return;
        }

        if (
            dados.estou_inscrito
        ) {

            if (minhaParticipacao) {

                minhaParticipacao.className =
                    (
                        "central-guerra-minha-participacao "
                        + "inscrito"
                    );

                minhaParticipacao.innerHTML =
                    `
                        ✅ Você está inscrito para
                        representar seu clã nesta guerra.
                    `;
            }


            if (btnParticipar) {
                btnParticipar.style.display =
                    "none";
            } 


            if (btnSair) {
 
                btnSair.style.display =
                    dados.pode_sair_participacao
                        ? "block"
                        : "none";

                btnSair.disabled =
                    false;

                btnSair.textContent =
                    "✕ Sair da Inscrição";
            }

        } else {

            if (minhaParticipacao) {

                minhaParticipacao.className =
                    (
                        "central-guerra-minha-participacao "
                        + "nao-inscrito"
                    );

                minhaParticipacao.innerHTML =
                    `
                        🛡️ Você ainda não está
                        inscrito entre os guerreiros
                        desta semana.
                    `;
            }


            if (btnSair) {
                btnSair.style.display =
                    "none";
            }


            if (btnParticipar) {

                btnParticipar.style.display =
                    dados.pode_participar
                        ? "block"
                        : "none";
 
                btnParticipar.disabled =
                    false;
 
                btnParticipar.textContent =
                    "⚔️ Quero Participar da Guerra";
            }
        }
    }

    // ========================================================
    // 👑 RENDERIZAR ESCALAÇÃO
    // ========================================================

    function renderizarEscalacaoGuerraCentral(
        dados
    ) {
        const painel = elemento(
            "central-guerra-escalacao"
        );

        const lista = elemento(
            "central-guerra-escalacao-lista"
        );

        const mensagem = elemento(
            "central-guerra-escalacao-mensagem"
        );

        const contador = elemento(
            "central-guerra-escalacao-contador"
        );

        const feedback = elemento(
            "central-guerra-escalacao-feedback"
        );

        const btnConfirmar = elemento(
            "central-guerra-btn-confirmar-escalacao"
        );


        if (
            !painel ||
            !lista
        ) {
            return;
        }


        const inscricao =
            dados.inscricao ||
            null;


        if (!inscricao) {

            painel.style.display =
                "none";

            return;
        }


        const quorum =
            dados.quorum ||
            {};


        const escalacao =
            dados.escalacao ||
            inscricao.escalacao ||
            {};


        const travada =
            Boolean(
                dados.escalacao_travada ||
                escalacao.travada
            );


        const participantes =
            Array.isArray(
                dados.participantes
            )
                ? dados.participantes
                : (
                    Array.isArray(
                        inscricao.participantes
                    )
                        ? inscricao.participantes
                        : []
                );


        const categoria =
            Number(
                escalacao.categoria ||
                dados.categoria_efetiva ||
                inscricao.categoria_efetiva ||
                0
            );


        /*
         * Sem quórum e sem escalação pronta,
         * não existe painel de escalação.
         */
        if (
            !travada &&
            quorum.status !==
                "aprovado"
        ) {

            painel.style.display =
                "none";

            return;
        }


        painel.style.display =
            "block";


        const chaveAtual =
            String(
                dados.calendario
                    ?.semana_id ||
                ""
            )
            +
            ":"
            +
            String(
                dados.clan?.id ||
                ""
            );


        if (
            chaveEscalacaoGuerraCentral
            !== chaveAtual
        ) {

            titularesSelecionadosGuerraCentral
                .clear();

            chaveEscalacaoGuerraCentral =
                chaveAtual;
        }


        if (feedback) {
            feedback.style.display =
                "none";

            feedback.textContent =
                "";
        }


        // ====================================================
        // 🔒 ESCALAÇÃO JÁ CONFIRMADA
        // ====================================================

        if (travada) {

            titularesSelecionadosGuerraCentral
                .clear();


            const titulares =
                Array.isArray(
                    escalacao.jogadores
                )
                    ? escalacao.jogadores
                    : [];


            const reservas =
                Array.isArray(
                    escalacao.reservas
                )
                    ? escalacao.reservas
                    : [];


            if (contador) {
                contador.textContent =
                    `${titulares.length}/${categoria || titulares.length}`;
            }


            if (mensagem) {
                mensagem.innerHTML =
                    `
                        🔒 Escalação confirmada.
                        <strong>
                            ${
                                escaparHtmlCentral(
                                    escalacao
                                        .categoria_nome ||
                                    dados
                                        .categoria_efetiva_nome ||
                                    ""
                                )
                            }
                        </strong>
                    `;
            }


            const criarLinhaTravada =
                function (
                    jogador,
                    funcao
                ) {

                    const nome =
                        escaparHtmlCentral(
                            jogador.nome ||
                            "Aventureiro"
                        );


                    const nivel =
                        Number(
                            jogador.nivel ||
                            1
                        );


                    const classe =
                        escaparHtmlCentral(
                            String(
                                jogador.classe ||
                                "aventureiro"
                            )
                            .replaceAll(
                                "_",
                                " "
                            )
                        );


                    return `
                        <div
                            class="
                                central-guerra-jogador
                            "
                        >

                            <div
                                class="
                                    central-guerra-jogador-check
                                "
                            >
                                ${
                                    funcao ===
                                    "titular"
                                        ? "⚔️"
                                        : "🪑"
                                }
                            </div>


                            <div
                                class="
                                    central-guerra-jogador-info
                                "
                            >
                                <div
                                    class="
                                        central-guerra-jogador-nome
                                    "
                                >
                                    ${nome}
                                </div>

                                <div
                                    class="
                                        central-guerra-jogador-detalhe
                                    "
                                >
                                    Nv. ${nivel}
                                    ·
                                    ${classe}
                                </div>
                            </div>


                            <span
                                class="
                                    central-guerra-jogador-funcao
                                    ${funcao}
                                "
                            >
                                ${
                                    funcao ===
                                    "titular"
                                        ? "TITULAR"
                                        : "RESERVA"
                                }
                            </span>

                        </div>
                    `;
                };


            let html = `
                <div
                    class="
                        central-guerra-escalacao-subtitulo
                    "
                >
                    ⚔️ Titulares
                </div>
            `;


            html +=
                titulares
                    .map(
                        function (
                            jogador
                        ) {
                            return criarLinhaTravada(
                                jogador,
                                "titular"
                            );
                        }
                    )
                    .join("");


            if (reservas.length) {

                html += `
                    <div
                        class="
                            central-guerra-escalacao-subtitulo
                        "
                    >
                        🪑 Reservas
                    </div>
                `;


                html +=
                    reservas
                        .map(
                            function (
                                jogador
                            ) {
                                return criarLinhaTravada(
                                    jogador,
                                    "reserva"
                                );
                            }
                        )
                        .join("");
            }


            lista.innerHTML =
                html;


            if (btnConfirmar) {
                btnConfirmar.style.display =
                    "none";
            }


            return;
        }


        // ====================================================
        // 🧑‍🤝‍🧑 AINDA NÃO FOI CONFIRMADA
        // ====================================================

        const podeGerenciar =
            Boolean(
                dados
                    .pode_gerenciar_escalacao
            );


        if (contador) {
            contador.textContent =
                `${
                    titularesSelecionadosGuerraCentral
                        .size
                }/${categoria}`;
        }


        if (mensagem) {

            if (podeGerenciar) {

                mensagem.innerHTML =
                    `
                        Escolha exatamente
                        <strong>
                            ${categoria}
                        </strong>
                        guerreiros titulares.
                        Os demais inscritos serão
                        reservas automaticamente.
                    `;

            } else {

                mensagem.textContent =
                    (
                        "Aguardando o líder definir "
                        + "a escalação oficial do clã."
                    );
            }
        }


        lista.innerHTML =
            participantes
                .map(
                    function (
                        jogador
                    ) {

                        const userId =
                            String(
                                jogador.user_id ||
                                ""
                            );


                        const selecionado =
                            titularesSelecionadosGuerraCentral
                                .has(
                                    userId
                                );


                        const nome =
                            escaparHtmlCentral(
                                jogador.nome ||
                                "Aventureiro"
                            );


                        const nivel =
                            Number(
                                jogador.nivel ||
                                1
                            );


                        const classe =
                            escaparHtmlCentral(
                                String(
                                    jogador.classe ||
                                    "aventureiro"
                                )
                                .replaceAll(
                                    "_",
                                    " "
                                )
                            );


                        const tag =
                            podeGerenciar
                                ? "button"
                                : "div";


                        const atributo =
                            podeGerenciar
                                ? (
                                    `data-escalacao-user-id="`
                                    + escaparHtmlCentral(
                                        userId
                                    )
                                    + `"`
                                )
                                : "";


                        return `
                            <${tag}
                                type="${
                                    podeGerenciar
                                        ? "button"
                                        : ""
                                }"

                                ${atributo}

                                class="
                                    central-guerra-jogador
                                    ${
                                        selecionado
                                            ? "selecionado"
                                            : ""
                                    }
                                "
                            >

                                <div
                                    class="
                                        central-guerra-jogador-check
                                    "
                                >
                                    ${
                                        selecionado
                                            ? "✓"
                                            : (
                                                podeGerenciar
                                                    ? "○"
                                                    : "⚔️"
                                            )
                                    }
                                </div>


                                <div
                                    class="
                                        central-guerra-jogador-info
                                    "
                                >
                                    <div
                                        class="
                                            central-guerra-jogador-nome
                                        "
                                    >
                                        ${nome}
                                    </div>

                                    <div
                                        class="
                                            central-guerra-jogador-detalhe
                                        "
                                    >
                                        Nv. ${nivel}
                                        ·
                                        ${classe}
                                    </div>
                                </div>


                                ${
                                    selecionado
                                        ? `
                                            <span
                                                class="
                                                    central-guerra-jogador-funcao
                                                    titular
                                                "
                                            >
                                                TITULAR
                                            </span>
                                        `
                                        : ""
                                }

                            </${tag}>
                        `;
                    }
                )
                .join("");


        if (btnConfirmar) {

            btnConfirmar.style.display =
                podeGerenciar
                    ? "block"
                    : "none";


            btnConfirmar.disabled =
                (
                    titularesSelecionadosGuerraCentral
                        .size
                    !==
                    categoria
                );


            btnConfirmar.textContent =
                (
                    titularesSelecionadosGuerraCentral
                        .size
                    ===
                    categoria
                )
                    ? "🔒 Confirmar Escalação"
                    : (
                        "🔒 Selecione "
                        + `${categoria} titulares`
                    );
        }
    }

    // ========================================================
    // 🎨 RENDERIZAR ESTADO DA GUERRA
    // ========================================================

    function renderizarEstadoGuerraCentral(
        dados
    ) {
        const status = elemento(
            "central-guerra-status"
        );

        const mensagem = elemento(
            "central-guerra-mensagem"
        );

        const resumo = elemento(
            "central-guerra-resumo"
        );

        const aviso = elemento(
            "central-guerra-aviso"
        );

        const btnInscrever = elemento(
            "central-guerra-btn-inscrever"
        );


        const calendario =
            dados.calendario ||
            {};


        const fase =
            String(
                calendario.fase ||
                ""
            );


        const inscricao =
            dados.inscricao ||
            null;


        renderizarConfrontoGuerraCentral(
            dados
        );


        renderizarLobbyGuerraCentral(
            dados
        );


        renderizarEscalacaoGuerraCentral(
            dados
        );

        // ====================================================
        // 📅 CALENDÁRIO
        // ====================================================

        const dataInscricao =
            elemento(
                "central-guerra-data-inscricao"
            );

        const dataEscalacao =
            elemento(
                "central-guerra-data-escalacao"
            );

        const dataPareamento =
            elemento(
                "central-guerra-data-pareamento"
            );

        const dataBatalha =
            elemento(
                "central-guerra-data-batalha"
            );


        if (dataInscricao) {
            dataInscricao.textContent =
                (
                    formatarDataGuerra(
                        calendario
                            .inscricoes_abrem
                    )
                    +
                    " → "
                    +
                    formatarDataGuerra(
                        calendario
                            .inscricoes_fecham
                    )
                );
        }


        if (dataEscalacao) {
            dataEscalacao.textContent =
                formatarDataGuerra(
                    calendario
                        .escalacoes_travam
                );
        }


        if (dataPareamento) {
            dataPareamento.textContent =
                formatarDataGuerra(
                    calendario
                        .pareamento
                );
        }


        if (dataBatalha) {
            dataBatalha.textContent =
                (
                    formatarDataGuerra(
                        calendario
                            .guerra_abre
                    )
                    +
                    " → "
                    +
                    formatarDataGuerra(
                        calendario
                            .guerra_fecha
                    )
                );
        }


        // ====================================================
        // 👤 SEM CLÃ
        // ====================================================

        if (
            !dados.possui_clan
        ) {

            if (status) {
                status.className =
                    (
                        "central-guerra-status "
                        + "status-fechada"
                    );

                status.textContent =
                    "🛡️ CLÃ NECESSÁRIO";
            }


            if (mensagem) {
                mensagem.textContent =
                    "Você precisa pertencer "
                    + "a um clã para participar "
                    + "da Guerra Semanal.";
            }


            if (resumo) {
                resumo.style.display =
                    "none";
            } 


            if (aviso) {
                aviso.style.display =
                    "block";

                aviso.className =
                    "central-guerra-aviso";
  
                aviso.textContent =
                    "Entre ou funde um clã "
                    + "para representar uma "
                    + "bandeira na guerra.";
            }


            if (btnInscrever) {
                btnInscrever.style.display =
                    "none";
            }


            return;
        }


        // ====================================================
        // 🏰 DADOS DO CLÃ
        // ====================================================

        const clan =
            dados.clan ||
            {};


        if (resumo) {
            resumo.style.display =
                "grid";
        }


        const clanNome = elemento(
            "central-guerra-clan-nome"
        );

        const clanNivel = elemento(
            "central-guerra-clan-nivel"
        );

        const categoria = elemento(
            "central-guerra-categoria"
        );


        if (clanNome) {
            clanNome.textContent =
                (
                    clan.nome ||
                    "Clã"
                )
                +
                (
                    clan.tag
                        ? ` [${clan.tag}]`
                        : ""
                );
        }


        if (clanNivel) {
            clanNivel.textContent =
                `Nv. ${
                    Number(
                        clan.nivel ||
                        1
                    )
                }`;
        }


        if (categoria) {
            categoria.textContent =
                (
                    clan.categoria_nome
                    ||
                    (
                        clan.categoria_maxima
                            ? `${
                                clan.categoria_maxima
                            } x ${
                                clan.categoria_maxima
                            }`
                            : "—"
                    )
                );
        }
        renderizarParticipacaoGuerraCentral(
            dados
        );

        // ====================================================
        // ✅ JÁ INSCRITO
        // ====================================================

        if (
            inscricao
        ) {

            const quorum =
                dados.quorum ||
                {};

            const quorumStatus =
                String(
                    quorum.status ||
                    ""
                );

            // ====================================================
            // ❌ INSCRIÇÕES FECHARAM SEM QUÓRUM
            // ====================================================

            if (
                quorumStatus ===
                "sem_quorum"
            ) {

                if (status) {

                    status.className =
                        (
                            "central-guerra-status "
                            + "status-fechada"
                        );

                    status.textContent =
                        "❌ CLÃ SEM QUÓRUM";
                }

                if (mensagem) {

                    mensagem.textContent =
                        (
                            "O período de inscrições "
                            + "foi encerrado e o clã "
                            + "não atingiu o número "
                            + "mínimo de guerreiros."
                        );
                }


                if (aviso) {

                    aviso.style.display =
                        "block";

                    aviso.className =
                        (
                            "central-guerra-aviso "
                            + "erro"
                        );


                    aviso.innerHTML =
                        `
                            ❌ Seu clã ficou fora da
                            Guerra desta semana.
                            <br><br>

                            Guerreiros inscritos:
                            <strong>
                                ${
                                    Number(
                                        quorum
                                            .participantes_total ||
                                        0
                                    )
                                }/${
                                    Number(
                                        quorum.minimo ||
                                        5
                                    )
                                }
                            </strong>

                            <br>

                            <span
                                style="
                                    color:#fca5a5;
                                "
                            >
                                O mínimo necessário é
                                ${
                                    Number(
                                        quorum.minimo ||
                                        5
                                    )
                                } guerreiros.
                            </span>
                        `;
                }


                if (btnInscrever) {
                    btnInscrever.style.display =
                        "none";
                }
        
        
                return;
            }


            // ====================================================
            // ✅ QUÓRUM APROVADO
            // ====================================================
        
            if (
                quorumStatus ===
                "aprovado"
            ) {
        
                if (status) {
        
                    status.className =
                        (
                            "central-guerra-status "
                            + "status-inscrito"
                        );
        
                    status.textContent =
                        "✅ QUÓRUM CONFIRMADO";
                }
        
        
                if (mensagem) {
        
                    mensagem.textContent =
                        (
                            "Seu clã atingiu o mínimo "
                            + "necessário e avançou para "
                            + "a fase de escalação."
                        );
                }
        
        
                if (aviso) {
        
                    aviso.style.display =
                        "block";
        
                    aviso.className =
                        (
                            "central-guerra-aviso "
                            + "sucesso"
                        );
        
        
                    aviso.innerHTML =
                        `
                            ⚔️ Formação confirmada.
                            <br>
        
                            Categoria da semana:
                            <strong>
                                ${
                                    escaparHtmlCentral(
                                        dados
                                            .categoria_efetiva_nome
                                        ||
                                        "5 x 5"
                                    )
                                }
                            </strong>
        
                            <br>
        
                            <span
                                style="
                                    color:#a7b3c2;
                                "
                            >
                                O líder deverá organizar
                                os titulares na etapa
                                de escalação.
                            </span>
                        `;
                }
        
        
                if (btnInscrever) {
                    btnInscrever.style.display =
                        "none";
                }
        
        
                return;
            }


            // ====================================================
            // 📝 INSCRIÇÕES AINDA ABERTAS
            // ====================================================
        
            if (status) {
        
                status.className =
                    (
                        "central-guerra-status "
                        + "status-inscrito"
                    );
        
                status.textContent =
                    "✅ CLÃ INSCRITO";
            }
        
        
            if (mensagem) {
        
                mensagem.textContent =
                    (
                        "Seu clã está oficialmente "
                        + "registrado na Guerra "
                        + "desta semana."
                    );
            }
        
        
            if (aviso) {
        
                aviso.style.display =
                    "block";
        
                aviso.className =
                    (
                        "central-guerra-aviso "
                        + "sucesso"
                    );
        
        
                aviso.innerHTML =
                    `
                        🛡️ Inscrição do clã confirmada.
                        <br>
        
                        Categoria máxima:
                        <strong>
                            ${
                                escaparHtmlCentral(
                                    inscricao
                                        .categoria_maxima_nome
                                    ||
                                    clan.categoria_nome
                                    ||
                                    "—"
                                )
                            }
                        </strong>
        
                        <br>
        
                        <span
                            style="
                                color:#a7b3c2;
                            "
                        >
                            Os membros ainda podem
                            registrar interesse enquanto
                            as inscrições estiverem abertas.
                        </span>
                    `;
            }


            if (btnInscrever) {
                btnInscrever.style.display =
                    "none";
            }
        
        
            return;
        }


        // ====================================================
        // 📝 INSCRIÇÕES ABERTAS + LÍDER
        // ====================================================

        if (
            dados.pode_inscrever_clan
        ) {

            if (status) {
                status.className =
                    (
                        "central-guerra-status "
                        + "status-aberta"
                    );

                status.textContent =
                    "🟢 INSCRIÇÕES ABERTAS";
            }


            if (mensagem) {
                mensagem.textContent =
                    "A Guerra Semanal está "
                    + "recebendo inscrições. "
                    + "Como líder, você pode "
                    + "registrar seu clã.";
            }


            if (aviso) {
                aviso.style.display =
                    "block";

                aviso.className =
                    "central-guerra-aviso";
  
                aviso.innerHTML =
                    `
                        Categoria máxima liberada:
                        <strong>
                            ${
                                escaparHtmlCentral(
                                    clan.categoria_nome ||
                                    "—"
                                )
                            }
                        </strong>.
                        <br>
                        O tamanho real da guerra
                        será definido pela quantidade
                        de membros inscritos.
                    `;
            }


            if (btnInscrever) {
                btnInscrever.style.display =
                    "block";

                btnInscrever.disabled =
                    false;
 
                btnInscrever.textContent =
                    "⚔️ Inscrever Clã na Guerra";
            }


            return;
        }


        // ====================================================
        // 🔒 NÃO PODE INSCREVER
        // ====================================================

        if (status) {
            status.className =
                (
                    "central-guerra-status "
                    + "status-fechada"
                );

            status.textContent =
                `🔒 ${traduzirFaseGuerra(
                    fase
                ).toUpperCase()}`;
        }


        if (mensagem) {
            mensagem.textContent =
                dados.motivo_bloqueio ||
                "A inscrição não está "
                + "disponível neste momento.";
        }


        if (aviso) {
            aviso.style.display =
                "block";

            aviso.className =
                "central-guerra-aviso";
 
            if (
                !dados.sou_lider &&
                calendario
                    .inscricoes_abertas
            ) {

                aviso.textContent =
                    "As inscrições estão abertas, "
                    + "mas somente o líder do seu "
                    + "clã pode registrá-lo.";

            } else {
 
                aviso.textContent =
                    `Fase atual: ${
                        traduzirFaseGuerra(
                            fase
                        )
                    }.`;
            }
        }


        if (btnInscrever) {
            btnInscrever.style.display =
                "none";
        }
    }


    // ========================================================
    // ⚔️ INSCREVER CLÃ
    // ========================================================

    window.inscreverClanGuerraCentral =
        async function () {

            const userId =
                localStorage.getItem(
                    "jogadorEldoraID"
                );


            if (!userId) {
                return;
            }


            const botao = elemento(
                "central-guerra-btn-inscrever"
            );


            if (botao) {
                botao.disabled =
                    true;

                botao.textContent =
                    "⏳ Registrando bandeira...";
            }


            try {
 
                const resposta =
                    await fetch(
                        "/api/clan/guerra/inscrever",
                        {
                            method:
                                "POST",

                            headers: {
                                "Content-Type":
                                    "application/json"
                            },

                            body:
                                JSON.stringify({
                                    user_id:
                                        userId
                                })
                        }
                    );

 
                const dados =
                    await resposta.json();


                if (
                    !resposta.ok ||
                    dados.success === false
                ) {

                    throw new Error(
                        dados.error ||
                        "Não foi possível "
                        + "inscrever o clã."
                    );
                }


                /*
                 * Busca novamente o estado
                 * oficial no servidor.
                 */
                await carregarEstadoGuerraCentral();


            } catch (
                erro
            ) {

                console.error(
                    "❌ [CENTRAL] Inscrição Guerra:",
                    erro
                );


                const aviso = elemento(
                    "central-guerra-aviso"
                );


                if (aviso) {
                    aviso.style.display =
                        "block";

                    aviso.className =
                        (
                            "central-guerra-aviso "
                            + "erro"
                        );

                    aviso.textContent =
                        erro.message ||
                        "Erro ao inscrever o clã.";
                }


                if (botao) {
                    botao.disabled =
                        false;

                    botao.textContent =
                        "⚔️ Inscrever Clã na Guerra";
                }
            }
        };

        // ========================================================
        // 👤 PARTICIPAÇÃO DO GUERREIRO
        // ========================================================

        async function alterarParticipacaoGuerraCentral(
            acao
        ) {
            const userId =
                localStorage.getItem(
                    "jogadorEldoraID"
                );


            if (!userId) {
                return;
            }


            const participar =
                acao ===
                "participar";


            const endpoint =
                participar
                    ? "/api/clan/guerra/participar"
                    : "/api/clan/guerra/sair";


            const botao =
                elemento(
                    participar
                        ? "central-guerra-btn-participar"
                        : "central-guerra-btn-sair"
                );


            if (botao) {

                botao.disabled =
                    true;

                botao.textContent =
                    participar
                        ? "⏳ Registrando guerreiro..."
                        : "⏳ Retirando inscrição...";
            }


            try {

                const resposta =
                    await fetch(
                        endpoint,
                        {
                            method:
                                "POST",
        
                            headers: {
                                "Content-Type":
                                    "application/json"
                            },

                            body:
                                JSON.stringify({
                                    user_id:
                                        userId
                                })
                        }
                    );
        
        
                const dados =
                    await resposta.json();
        
        
                if (
                    !resposta.ok ||
                    dados.success === false
                ) {

                    throw new Error(
                        dados.error ||
                        "Não foi possível alterar "
                        + "sua participação."
                    );
                }


                /*
                 * Sempre recarrega o estado oficial
                 * do servidor após a alteração.
                 */
                await carregarEstadoGuerraCentral();


            } catch (
                erro
            ) {

                console.error(
                    "❌ [GUERRA] Participação:",
                    erro
                );


                const aviso =
                    elemento(
                        "central-guerra-aviso"
                    );


                if (aviso) {

                    aviso.style.display =
                        "block";

                    aviso.className =
                        (
                            "central-guerra-aviso "
                            + "erro"
                        );

                    aviso.textContent =
                        erro.message ||
                        "Erro ao alterar participação.";
                }


                if (botao) {

                    botao.disabled =
                        false;

                    botao.textContent =
                        participar
                            ? "⚔️ Quero Participar da Guerra"
                            : "✕ Sair da Inscrição";
                }
            }
        }

        // ========================================================
        // 👑 SELECIONAR TITULAR
        // ========================================================

        function alternarTitularGuerraCentral(
            userId
        ) {
            userId = String(
                userId ||
                ""
            );


            if (
                !userId ||
                !estadoGuerraCentral
            ) {
                return;
            }


            if (
                !estadoGuerraCentral
                    .pode_gerenciar_escalacao
            ) {
                return;
            }


            const categoria =
                Number(
                    estadoGuerraCentral
                        .categoria_efetiva ||
                    0
                );


            if (!categoria) {
                return;
            }


            const feedback = elemento(
                "central-guerra-escalacao-feedback"
            );


            if (
                titularesSelecionadosGuerraCentral
                    .has(
                        userId
                    )
            ) {

                titularesSelecionadosGuerraCentral
                    .delete(
                        userId
                    );

            } else {

                if (
                    titularesSelecionadosGuerraCentral
                        .size
                    >=
                    categoria
                ) {

                    if (feedback) {

                        feedback.style.display =
                            "block";

                        feedback.textContent =
                            (
                                "A categoria permite "
                                + `somente ${categoria} `
                                + "titulares."
                            );
                    }

                    return;
                }


                titularesSelecionadosGuerraCentral
                    .add(
                        userId
                    );
            }


            renderizarEscalacaoGuerraCentral(
                estadoGuerraCentral
            );
        }

        // ========================================================
        // 🔒 CONFIRMAR ESCALAÇÃO
        // ========================================================

        async function confirmarEscalacaoGuerraCentral() {

            if (!estadoGuerraCentral) {
                return;
            }


            const userId =
                localStorage.getItem(
                    "jogadorEldoraID"
                );


            if (!userId) {
                return;
            }


            const categoria =
                Number(
                    estadoGuerraCentral
                        .categoria_efetiva ||
                    0
                );


            const titulares =
                Array.from(
                    titularesSelecionadosGuerraCentral
                );


            const feedback = elemento(
                "central-guerra-escalacao-feedback"
            );


            const botao = elemento(
                "central-guerra-btn-confirmar-escalacao"
            );


            if (
                titulares.length
                !==
                categoria
            ) {

                if (feedback) {

                    feedback.style.display =
                        "block";

                    feedback.textContent =
                        (
                            "Selecione exatamente "
                            + `${categoria} titulares.`
                        );
                }

                return;
            }


            if (botao) {

                botao.disabled =
                    true;

                botao.textContent =
                    "⏳ Confirmando escalação...";
            }


            try {

                const resposta =
                    await fetch(
                        "/api/clan/guerra/escalacao/confirmar",
                        {
                            method:
                                "POST",

                            headers: {
                                "Content-Type":
                                    "application/json"
                            },

                            body:
                                JSON.stringify({
                                    user_id:
                                        userId,

                                    titulares:
                                        titulares
                                })
                        }
                    );


                const dados =
                    await resposta.json();


                if (
                    !resposta.ok ||
                    dados.success === false
                ) {

                    throw new Error(
                        dados.error ||
                        "Não foi possível confirmar "
                        + "a escalação."
                    );
                }


                titularesSelecionadosGuerraCentral
                    .clear();


                await carregarEstadoGuerraCentral();


            } catch (
                erro
            ) {

                console.error(
                    "❌ [GUERRA] Escalação:",
                    erro
                );


                if (feedback) {

                    feedback.style.display =
                        "block";

                    feedback.textContent =
                        erro.message ||
                        "Erro ao confirmar escalação.";
                }


                if (botao) {

                    botao.disabled =
                        false;

                    botao.textContent =
                        "🔒 Confirmar Escalação";
                }
            }
        } 

        // ========================================================
        // ⚔️ QUERO PARTICIPAR
        // ========================================================

        window.participarGuerraCentral =
            function () {

                return (
                    alterarParticipacaoGuerraCentral(
                        "participar"
                    )
                );
            };


        // ========================================================
        // 🚪 SAIR
        // ========================================================

        window.sairParticipacaoGuerraCentral =
            function () {

                return (
                    alterarParticipacaoGuerraCentral(
                        "sair"
                    )
                );
            };

        // ========================================================
        // 🚪 ENTRAR NO LOBBY DA FRENTE
        // ========================================================

        async function entrarLobbyGuerraCentral() {

            const userId =
                localStorage.getItem(
                    "jogadorEldoraID"
                );


            if (!userId) {
                return;
            }


            const botao =
                elemento(
                    "central-guerra-btn-entrar"
                );


            const situacao =
                elemento(
                    "central-guerra-minha-situacao"
                );


            if (botao) {

                botao.disabled =
                    true;

                botao.textContent =
                    "⏳ Entrando na frente...";
            }


            try {

                const resposta =
                    await fetch(
                        "/api/clan/guerra/frente/entrar",
                        {
                            method:
                                "POST",

                            headers: {
                                "Content-Type":
                                    "application/json"
                            },

                            body:
                                JSON.stringify({
                                    user_id:
                                        userId
                                })
                        }
                    );


                const dados =
                    await resposta.json();


                if (
                    !resposta.ok ||
                    dados.success === false
                ) {

                    throw new Error(
                        dados.error ||
                        "Não foi possível entrar "
                        + "na frente."
                    );
                }


                if (situacao) {

                    situacao.className =
                        (
                            "central-guerra-minha-participacao "
                            + "inscrito"
                        );


                    situacao.textContent =
                        (
                            "✅ Você entrou no lobby "
                            + `da Frente ${
                                Number(
                                    dados.frente_numero ||
                                    0
                                )
                            }. `
                            + `Presentes: ${
                                Number(
                                    dados.presentes_total ||
                                    0
                                )
                            }/${
                                Number(
                                    dados.jogadores_total ||
                                    10
                                )
                            }.`
                        );
                }


                if (botao) {

                    botao.disabled =
                        true;

                    botao.textContent =
                        (
                            "✅ No lobby da Frente "
                            + `${
                                Number(
                                    dados.frente_numero ||
                                    0
                                )
                            }`
                        );
                }


            } catch (
                erro
            ) {

                console.error(
                    "❌ [GUERRA] Entrada no lobby:",
                    erro
                );


                if (situacao) {

                    situacao.className =
                        (
                            "central-guerra-minha-participacao "
                            + "nao-inscrito"
                        );


                    situacao.textContent =
                        (
                            "❌ "
                            + (
                                erro.message ||
                                "Não foi possível entrar "
                                + "na frente."
                            )
                        );
                }


                if (botao) {

                    botao.disabled =
                        false;

                    botao.textContent =
                        "⚔️ Entrar na Guerra";
                }
            }
        }

        // ========================================================
        // ✅ MARCAR PRONTO NA FRENTE
        // ========================================================

        async function marcarProntoGuerraCentral() {

            const userId =
                localStorage.getItem(
                    "jogadorEldoraID"
                );


            if (!userId) {
                return;
            }


            const botao =
                elemento(
                    "central-guerra-btn-pronto"
                );


            const feedback =
                elemento(
                    "central-guerra-lobby-feedback"
                );


            if (feedback) {

                feedback.style.display =
                    "none";

                feedback.textContent =
                    "";
            }


            if (botao) {

                botao.disabled =
                    true;

                botao.textContent =
                    "⏳ Confirmando...";
            }


            try {

                const resposta =
                    await fetch(
                        "/api/clan/guerra/frente/pronto",
                        {
                            method:
                                "POST",

                            headers: {
                                "Content-Type":
                                    "application/json"
                            },

                            body:
                                JSON.stringify({
                                    user_id:
                                        userId
                                })
                        }
                    );


                const dados =
                    await resposta.json();


                if (
                    !resposta.ok ||
                    dados.success === false
                ) {

                    throw new Error(
                        dados.error ||
                        "Não foi possível marcar PRONTO."
                    );
                }


                /*
                 * Recarrega o estado oficial.
                 * O MongoDB é a autoridade.
                 */
                await carregarEstadoGuerraCentral();


            } catch (
                erro
            ) {

                console.error(
                    "❌ [GUERRA] PRONTO:",
                    erro
                );


                if (feedback) {

                    feedback.style.display =
                        "block";

                    feedback.textContent =
                        (
                            "❌ "
                            +
                            (
                                erro.message ||
                                "Erro ao marcar PRONTO."
                            )
                        );
                }


                if (botao) {

                    botao.disabled =
                        false;

                    botao.textContent =
                        "✅ Estou PRONTO";
                }
            }
        }


    // ========================================================
    // 🔧 EVENTOS
    // ========================================================

    function prepararCentralEldora() {

        document
            .querySelectorAll(
                ".central-eldora-aba-btn"
            )

            
            .forEach(
                function (botao) {

                    botao.addEventListener(
                        "click",
                        function () {
                            window
                                .abrirAbaCentralEldora(
                                    botao.dataset
                                        .centralTab
                                );
                        }
                    );

                }
            );
        
        const btnInscreverGuerra =
            elemento(
                "central-guerra-btn-inscrever"
            );


        if (
            btnInscreverGuerra
        ) {

            btnInscreverGuerra
                .addEventListener(
                    "click",
                    function () {

                        window
                            .inscreverClanGuerraCentral();

                    }
                );
        }

        // ====================================================
        // 🚪 ENTRAR NA FRENTE DA GUERRA
        // ====================================================

        const btnEntrarGuerra =
            elemento(
                "central-guerra-btn-entrar"
            );


        if (
            btnEntrarGuerra
        ) {

            btnEntrarGuerra
                .addEventListener(
                    "click",
                    function () {

                        entrarLobbyGuerraCentral();

                    }
                );
        }

        // ====================================================
        // ✅ JOGADOR PRONTO NA FRENTE
        // ====================================================

        const btnProntoGuerra =
            elemento(
                "central-guerra-btn-pronto"
            );


        if (
            btnProntoGuerra
        ) {

            btnProntoGuerra
                .addEventListener(
                    "click",
                    function () {

                        const acao =
                            String(
                                btnProntoGuerra
                                    .dataset
                                    .acaoGuerra
                                ||
                                "pronto"
                            );


                        if (
                            acao ===
                            "combate"
                        ) {

                            abrirCombateGuerraCentral();

                            return;
                        }


                        marcarProntoGuerraCentral();

                    }
                );
        }

        // ====================================================
        // ⚔️ PARTICIPAR DA GUERRA
        // ====================================================

        const btnParticiparGuerra =
            elemento(
                "central-guerra-btn-participar"
            );


        if (
            btnParticiparGuerra
        ) {

            btnParticiparGuerra
                .addEventListener(
                    "click",
                    function () {

                        window
                            .participarGuerraCentral();
  
                    }
                );
        }


        // ====================================================
        // 🚪 SAIR DA PARTICIPAÇÃO
        // ====================================================

        const btnSairGuerra =
            elemento(
                "central-guerra-btn-sair"
            );


        if (
            btnSairGuerra
        ) {

            btnSairGuerra
                .addEventListener(
                    "click",
                    function () {

                        window
                            .sairParticipacaoGuerraCentral();
 
                    }
                );
        }
        
        // ====================================================
        // 👑 ESCOLHER TITULARES
        // ====================================================

        const listaEscalacao =
            elemento(
                "central-guerra-escalacao-lista"
            );


        if (listaEscalacao) {

            listaEscalacao.addEventListener(
                "click",
                function (
                    evento
                ) {

                    const alvo =
                        evento.target.closest(
                            "[data-escalacao-user-id]"
                        );


                    if (!alvo) {
                        return;
                    }


                    alternarTitularGuerraCentral(
                        alvo.dataset
                            .escalacaoUserId
                    );
                }
            );
        }


        // ====================================================
        // 🔒 CONFIRMAR ESCALAÇÃO
        // ====================================================

        const btnConfirmarEscalacao =
            elemento(
                "central-guerra-btn-confirmar-escalacao"
            );


        if (btnConfirmarEscalacao) {

            btnConfirmarEscalacao
                .addEventListener(
                    "click",
                    function () {

                        confirmarEscalacaoGuerraCentral();

                    }
                );
        }
                
        // ====================================================
        // 🏆 SUBMENU DOS RANKINGS
        // ====================================================

        document
            .querySelectorAll(
                ".central-ranking-opcao"
            )
            .forEach(
                function (
                    botao
                ) {

                    botao.addEventListener(
                        "click",
                        function () {

                            abrirRankingCentral(
                                botao.dataset
                                    .rankingCentral
                            );

                        }
                    );

                }
            );


        const btnVoltarRanking =
            elemento(
                "central-ranking-voltar"
            );


        if (
            btnVoltarRanking
        ) {

            btnVoltarRanking
                .addEventListener(
                    "click",
                    function () {

                        mostrarMenuRankings();

                    }
                );
        }


        const btnAtualizarRanking =
            elemento(
                "central-ranking-atualizar"
            );


        if (
            btnAtualizarRanking
        ) {

            btnAtualizarRanking
                .addEventListener(
                    "click",
                    function () {

                        if (
                            rankingAtualCentral
                            === "clans"
                        ) {

                            abrirRankingCentral(
                                "clans",
                                true
                            );

                            return;
                        }


                        if (
                            rankingAtualCentral
                            === "guerra"
                        ) {

                            abrirRankingCentral(
                                "guerra",
                                true
                            );
                        }

                    }
                );
        }

        /*
         * Clique fora do painel fecha.
         */
        const modal = elemento(
            "central-eldora-modal"
        );


        if (modal) {
            modal.addEventListener(
                "click",
                function (evento) {

                    if (
                        evento.target === modal
                    ) {
                        window
                            .fecharCentralEldora();
                    }

                }
            );
        }
    }


    // ========================================================
    // ⌨️ ESC
    // ========================================================

    document.addEventListener(
        "keydown",
        function (evento) {

            if (
                evento.key !== "Escape"
            ) {
                return;
            }


            const modalCombate =
                elemento(
                    "central-guerra-combate-modal"
                );


            if (
                modalCombate
                &&
                modalCombate.style.display ===
                    "flex"
            ) {

                evento.preventDefault();


                fecharCombateGuerraCentral();

                return;
            }


            const modal = elemento(
                "central-eldora-modal"
            );


            if (
                modal &&
                modal.style.display ===
                    "flex"
            ) {
                evento.preventDefault();

                window
                    .fecharCentralEldora();
            }

        }
    );


    // ========================================================
    // 🚀 INICIALIZAÇÃO
    // ========================================================

    if (
        document.readyState ===
        "loading"
    ) {
        document.addEventListener(
            "DOMContentLoaded",
            prepararCentralEldora
        );

    } else {
        prepararCentralEldora();
    }

})();