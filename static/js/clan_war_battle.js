// ============================================================
// ⚔️ MUNDO DE ELDORA - BATALHA DA GUERRA DE CLÃS
// ============================================================

(function () {
    "use strict";

    const BASE_SKINS =
        "https://raw.githubusercontent.com/Eldorabotpy/static-img/main/assets/classes_costa/";

    const FUNDO_GUERRA =
        "https://raw.githubusercontent.com/Eldorabotpy/static-img/main/assets/fundos/capital.png";


    let estadoAtual =
        null;

    let alvoSelecionadoId =
        null;

    let enviandoAtaque =
        false;


    let enviandoSkill =
        false;


    let intervaloSincronizacao =
        null;

    // ========================================================
    // 🎭 CACHE DAS SKINS DOS COMBATENTES
    // ========================================================

    const skinsCombatentesGuerra =
        new Map();

    function esc(valor) {
        return String(
            valor ?? ""
        )
            .replaceAll("&", "&amp;")
            .replaceAll("<", "&lt;")
            .replaceAll(">", "&gt;")
            .replaceAll('"', "&quot;")
            .replaceAll("'", "&#039;");
    }


    function pct(
        atual,
        maximo
    ) {
        atual =
            Number(
                atual || 0
            );

        maximo =
            Math.max(
                1,
                Number(
                    maximo || 1
                )
            );


        return Math.max(
            0,
            Math.min(
                100,
                (
                    atual /
                    maximo
                ) * 100
            )
        );
    }


    function meuId() {
        return String(
            localStorage.getItem(
                "jogadorEldoraID"
            )
            ||
            ""
        );
    }


    function normalizarSkin(
        valor
    ) {
        let skin =
            String(
                valor || ""
            )
            .trim();


        if (
            skin.includes("/")
        ) {
            skin =
                skin
                    .split("/")
                    .pop();
        }


        skin =
            skin
                .replace(".png", "")
                .toLowerCase()
                .normalize("NFD")
                .replace(
                    /[\u0300-\u036f]/g,
                    ""
                )
                .replace(
                    /\s+/g,
                    "_"
                )
                .replace(
                    "_masculino",
                    "_m"
                )
                .replace(
                    "_feminino",
                    "_f"
                );


        if (
            !skin
            ||
            skin === "padrao"
            ||
            skin === "player"
            ||
            skin === "undefined"
            ||
            skin === "null"
        ) {
            skin =
                "aventureiro_m";
        }


        return skin;
    }


    function urlSkinCombatente(
        combatente
    ) {

        const id =
            String(
                combatente?.user_id ||
                ""
            );


        let skin =
            (
                combatente?.skin
                ||
                combatente?.equipped_skin
                ||
                combatente?.skin_equipada
                ||
                skinsCombatentesGuerra.get(
                    id
                )
                ||
                ""
            );


        // ====================================================
        // 👤 PRÓPRIO JOGADOR
        // ====================================================

        if (
            !skin
            &&
            id === meuId()
        ) {

            skin =
                window
                    .perfilDadosGlobais
                    ?.equipped_skin
                ||
                localStorage.getItem(
                    "skinEquipada"
                )
                ||
                "";
        }


        return (
            BASE_SKINS
            +
            normalizarSkin(
                skin
            )
            +
            ".png?v=3"
        );
    }

    async function carregarSkinCombatenteGuerra(
        combatente
    ) {

        const id =
            String(
                combatente?.user_id ||
                ""
            );


        if (!id) {
            return;
        }


        // ====================================================
        // 🎭 SE O BACKEND JÁ ENVIOU A SKIN
        // ====================================================

        const skinExistente =
            (
                combatente?.skin
                ||
                combatente?.equipped_skin
                ||
                combatente?.skin_equipada
                ||
                ""
            );


        if (skinExistente) {

            skinsCombatentesGuerra.set(
                id,
                skinExistente
            );

            return;
        }


        // Já consultamos este personagem.
        if (
            skinsCombatentesGuerra.has(
                id
            )
        ) {

            return;
        }


        // ====================================================
        // 👤 NOSSA PRÓPRIA SKIN
        // ====================================================

        if (
            id === meuId()
        ) {

            const minhaSkin =
                window
                    .perfilDadosGlobais
                    ?.equipped_skin
                ||
                localStorage.getItem(
                    "skinEquipada"
                )
                ||
                "";


            if (minhaSkin) {

                skinsCombatentesGuerra.set(
                    id,
                    minhaSkin
                );
            }


            return;
        }


        // ====================================================
        // 🌐 SKIN REAL DO OUTRO COMBATENTE
        // ====================================================

        try {

            const resposta =
                await fetch(
                    (
                        "/api/personagem/"
                        +
                        encodeURIComponent(
                            id
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


            const perfil =
                await resposta.json();


            if (
                !resposta.ok
                ||
                perfil.erro
            ) {

                return;
            }


            const skin =
                (
                    perfil.equipped_skin
                    ||
                    perfil.skin_equipada
                    ||
                    perfil.skin
                    ||
                    ""
                );


            if (skin) {

                skinsCombatentesGuerra.set(
                    id,
                    skin
                );


                console.log(
                    "🎭 [GUERRA] Skin carregada:",
                    {
                        jogador:
                            combatente?.nome,

                        skin:
                            skin
                    }
                );
            }


        } catch (
            erro
        ) {

            console.warn(
                "⚠️ [GUERRA] "
                + "Não foi possível carregar "
                + "a skin de "
                + (
                    combatente?.nome ||
                    id
                ),
                erro
            );
        }
    }


    async function carregarSkinsCombatentesGuerra() {

        const lista =
            combatentes();


        if (!lista.length) {
            return;
        }


        await Promise.all(
            lista.map(
                carregarSkinCombatenteGuerra
            )
        );
    }

    function combatentes() {

        return Array.isArray(
            estadoAtual
                ?.minha_frente
                ?.batalha
                ?.combatentes
        )
            ? estadoAtual
                .minha_frente
                .batalha
                .combatentes

            : [];
    }


    function localizarCombatente(
        id
    ) {
        id =
            String(
                id || ""
            );


        return (
            combatentes()
                .find(
                    function (
                        jogador
                    ) {

                        return (
                            String(
                                jogador.user_id ||
                                ""
                            )
                            ===
                            id
                        );
                    }
                )
            ||
            null
        );
    }


    function combatenteVivo(
        combatente
    ) {

        if (!combatente) {
            return false;
        }


        return (
            combatente.vivo !==
                false
            &&
            Number(
                combatente.hp_atual ||
                0
            ) > 0
        );
    }


    function encontrarAlvoVisual(
        atacante
    ) {

        if (!atacante) {
            return null;
        }


        const ladoAtacante =
            String(
                atacante.lado ||
                ""
            )
            .toLowerCase();


        return (
            combatentes()
                .find(
                    function (
                        jogador
                    ) {

                        return (
                            String(
                                jogador.lado ||
                                ""
                            )
                            .toLowerCase()
                            !==
                            ladoAtacante

                            &&
                            combatenteVivo(
                                jogador
                            )
                        );
                    }
                )
            ||
            null
        );
    }


    function obterNomeCla(
        lado
    ) {

        const frente =
            estadoAtual?.minha_frente ||
            {};


        const meuClan =
            estadoAtual?.clan ||
            {};


        const adversario =
            estadoAtual?.adversario ||
            {};


        const clanIdLado =
            String(
                (
                    lado === "a"
                        ? frente.clan_a
                        : frente.clan_b
                )?.clan_id
                ||
                ""
            );


        const meuClanId =
            String(
                meuClan.id ||
                meuClan._id ||
                ""
            );


        const dados =
            clanIdLado ===
                meuClanId
                ? meuClan
                : adversario;


        const nome =
            dados.nome ||
            (
                lado === "a"
                    ? "Clã A"
                    : "Clã B"
            );


        const tag =
            dados.tag ||
            "";


        return (
            nome
            +
            (
                tag
                    ? ` [${tag}]`
                    : ""
            )
        );
    }

    function obterLadoVencedorFrente(
        frente,
        batalha
    ) {

        const vencedorId =
            String(
                batalha?.vencedor_clan_id ||
                ""
            );


        if (!vencedorId) {

            return null;
        }


        const clanAId =
            String(
                frente
                    ?.clan_a
                    ?.clan_id
                ||
                ""
            );


        const clanBId =
            String(
                frente
                    ?.clan_b
                    ?.clan_id
                ||
                ""
            );


        if (
            vencedorId ===
            clanAId
        ) {

            return "a";
        }


        if (
            vencedorId ===
            clanBId
        ) {

            return "b";
        }


        return null;
    }

    function garantirTela() {

        let tela =
            document.getElementById(
                "tela-guerra-clans"
            );


        if (tela) {
            return tela;
        }


        const estilo =
            document.createElement(
                "style"
            );


        estilo.id =
            "guerra-clans-batalha-style";


        estilo.textContent = `

            #tela-guerra-clans * {
                box-sizing:border-box;
            }


            #tela-guerra-clans {
                position:fixed;
                inset:0;
                z-index:1000000;

                display:none;

                background:
                    rgba(2,6,23,.96);

                color:#fff;

                font-family:
                    Arial,
                    sans-serif;

                overflow:hidden;

                pointer-events:auto;
            }


            .guerra-box {
                width:min(100vw,430px);
                height:calc(100vh - 28px);

                margin:0 auto;

                display:flex;
                flex-direction:column;

                overflow:hidden;

                background:
                    linear-gradient(
                        180deg,
                        #0f172a,
                        #020617
                    );

                border:
                    1px solid #8b6c22;

                border-radius:14px;

                box-shadow:
                    0 20px 60px
                    rgba(0,0,0,.9);
            }


            .guerra-topo {
                flex:0 0 auto;

                display:flex;
                align-items:center;
                justify-content:space-between;

                gap:8px;

                padding:8px 10px;

                background:
                    linear-gradient(
                        90deg,
                        rgba(92,63,13,.95),
                        rgba(15,23,42,.98)
                    );

                border-bottom:
                    1px solid #ca8a04;
            }


            .guerra-titulo {
                color:#facc15;

                font-family:
                    Cinzel,
                    serif;

                font-size:15px;
                font-weight:900;
            }


            .guerra-subtitulo {
                margin-top:2px;

                color:#cbd5e1;

                font-size:10px;
            }


            .guerra-sair {
                padding:8px 10px;

                color:#e2e8f0;

                background:#1e293b;

                border:
                    1px solid #64748b;

                border-radius:9px;

                font-weight:900;

                cursor:pointer;
            }


            .guerra-palco {
                position:relative;

                flex:0 0 auto;

                min-height:205px;

                margin:8px;

                overflow:hidden;

                background-image:
                    url('${FUNDO_GUERRA}');

                background-size:cover;
                background-position:center;

                border:
                    1px solid #475569;

                border-radius:14px;

                box-shadow:
                    inset 0 0 70px
                    rgba(0,0,0,.82);
            }


            .guerra-palco::before {
                content:"";

                position:absolute;
                inset:0;

                background:
                    radial-gradient(
                        circle at 50% 50%,
                        rgba(202,138,4,.10),
                        transparent 46%
                    ),
                    linear-gradient(
                        180deg,
                        rgba(2,6,23,.06),
                        rgba(2,6,23,.72)
                    );

                pointer-events:none;
            }


            #guerra-aviso-turno {
                position:absolute;

                top:8px;
                left:50%;

                transform:
                    translateX(-50%);

                z-index:30;

                max-width:90%;

                padding:6px 12px;

                background:
                    rgba(2,6,23,.88);

                border:
                    1px solid #facc15;

                border-radius:999px;

                color:#facc15;

                font-size:11px;
                font-weight:900;

                text-align:center;

                white-space:nowrap;

                box-shadow:
                    0 0 16px
                    rgba(0,0,0,.7);
            }


            #guerra-sprite-a,
            #guerra-sprite-b {
                position:absolute;

                bottom:22px;

                z-index:10;

                height:108px;
                max-width:130px;

                object-fit:contain;

                filter:
                    drop-shadow(
                        0 10px 8px
                        rgba(0,0,0,.9)
                    );
            }


            #guerra-sprite-a {
                left:18px;
            }


            #guerra-sprite-b {
                right:18px;

                transform:
                    scaleX(-1);
            }


            .guerra-vs {
                position:absolute;

                left:50%;
                top:51%;

                transform:
                    translate(-50%,-50%);

                z-index:8;

                color:#facc15;

                font-family:
                    Cinzel,
                    serif;

                font-size:25px;
                font-weight:900;

                text-shadow:
                    0 3px 5px #000;

                opacity:.85;
            }


            .guerra-nome-palco {
                position:absolute;

                bottom:7px;

                z-index:20;

                max-width:43%;

                overflow:hidden;

                padding:4px 7px;

                background:
                    rgba(2,6,23,.82);

                border-radius:7px;

                font-size:10px;
                font-weight:900;

                white-space:nowrap;
                text-overflow:ellipsis;
            }


            #guerra-nome-a {
                left:7px;

                color:#60a5fa;

                border:
                    1px solid
                    rgba(96,165,250,.45);
            }


            #guerra-nome-b {
                right:7px;

                color:#f87171;

                border:
                    1px solid
                    rgba(248,113,113,.45);
            }


            .guerra-times {
                flex:0 0 auto;

                display:grid;

                grid-template-columns:
                    1fr 1fr;

                gap:7px;

                min-height:130px;

                padding:
                    0 8px;
            }


            .guerra-time {
                min-width:0;

                overflow:hidden;

                padding:7px;

                background:
                    rgba(15,23,42,.74);

                border:
                    1px solid #24334d;

                border-radius:12px;
            }


            .guerra-time-titulo {
                margin-bottom:5px;

                overflow:hidden;

                font-family:
                    Cinzel,
                    serif;

                font-size:10px;
                font-weight:900;

                white-space:nowrap;
                text-overflow:ellipsis;
            }


            .guerra-time-a {
                color:#60a5fa;
            }


            .guerra-time-b {
                color:#f87171;
            }


            .guerra-lista {
                display:flex;

                flex-direction:column;

                gap:4px;

                max-height:106px;

                overflow-y:auto;
            }


            .guerra-card {
                padding:5px;

                background:
                    rgba(8,15,30,.96);

                border:
                    1px solid #24334d;

                border-radius:8px;
            }


            .guerra-card.turno {
                border-color:#facc15;

                box-shadow:
                    0 0 8px
                    rgba(250,204,21,.25);
            }


            .guerra-card.eu {
                border-color:#38bdf8;
            }


            .guerra-card.morto {
                opacity:.45;

                background:
                    rgba(69,10,10,.72);
            }

            .guerra-card.alvo-disponivel {
                cursor:pointer;

                transition:
                    border-color .15s,
                    transform .15s,
                    box-shadow .15s;
            }


            .guerra-card.alvo-disponivel:active {
                transform:
                    scale(.97);
            }


            .guerra-card.alvo-selecionado {
                border-color:#ef4444 !important;

                background:
                    rgba(127,29,29,.32);

                box-shadow:
                    0 0 12px
                    rgba(239,68,68,.35);
            }

            .guerra-card-topo {
                display:flex;

                justify-content:space-between;

                gap:5px;

                color:#e2e8f0;

                font-size:9px;
                font-weight:900;
            }


            .guerra-card-status {
                display:flex;

                align-items:center;
                justify-content:space-between;

                gap:5px;

                margin-top:4px;

                font-size:7px;
                font-weight:900;

                line-height:1;

                white-space:nowrap;
            }


            .guerra-card-hp-texto {
                color:#86efac;
            }


            .guerra-card-hp-texto.baixo {
                color:#f87171;
            }


            .guerra-card-mp-texto {
                color:#93c5fd;
            }


            .guerra-card-mp-texto.baixo {
                color:#c4b5fd;
            }


            .guerra-mini-bar {
            
                height:5px;

                margin-top:3px;

                overflow:hidden;

                background:#020617;

                border-radius:999px;
            }


            .guerra-hp {
                height:100%;

                background:#22c55e;
            }


            .guerra-mp {
                height:100%;

                background:#3b82f6;
            }


            .guerra-log {
                flex:1 1 auto;

                min-height:65px;
                max-height:105px;

                margin:8px;

                padding:7px;

                overflow-y:auto;

                color:#cbd5e1;

                background:
                    rgba(2,6,23,.94);

                border:
                    1px solid #24334d;

                border-radius:11px;

                font-size:11px;
                line-height:1.35;
            }


            .guerra-acoes {
                flex:0 0 auto;

                display:grid;

                grid-template-columns:
                    1fr 1fr;

                gap:8px;

                padding:
                    0 8px 8px;
            }


            .guerra-btn {
                padding:10px 8px;

                color:#fff;

                background:
                    linear-gradient(
                        180deg,
                        rgba(30,41,59,.96),
                        rgba(15,23,42,.96)
                    );

                border:
                    1px solid #475569;

                border-radius:10px;

                font-family:
                    Cinzel,
                    Arial,
                    sans-serif;

                font-weight:900;
            }


            .guerra-btn-atacar {
                border-color:#ef4444;
            }


            .guerra-btn-skill {
                border-color:#8b5cf6;
            }


            .guerra-btn:disabled {
                opacity:.42;
            }


            @media (
                max-width:430px
            ) {

                .guerra-box {
                    width:100vw;

                    height:
                        calc(100vh - 28px);

                    border-left:0;
                    border-right:0;

                    border-radius:0;
                }
            }
        `;


        document.head.appendChild(
            estilo
        );


        tela =
            document.createElement(
                "div"
            );


        tela.id =
            "tela-guerra-clans";


        tela.innerHTML = `

            <div class="guerra-box">

                <div class="guerra-topo">

                    <div>

                        <div
                            id="guerra-titulo"
                            class="guerra-titulo"
                        >
                            ⚔️ GUERRA DE CLÃS
                        </div>

                        <div
                            id="guerra-subtitulo"
                            class="guerra-subtitulo"
                        >
                            Frente
                        </div>

                    </div>


                    <button
                        type="button"
                        class="guerra-sair"
                        onclick="
                            window.fecharBatalhaGuerraCla()
                        "
                    >
                        SAIR
                    </button>

                </div>


                <div class="guerra-palco">

                    <div
                        id="guerra-aviso-turno"
                    >
                        Aguardando...
                    </div>


                    <img
                        id="guerra-sprite-a"
                        src=""
                        alt=""
                    >


                    <div class="guerra-vs">
                        VS
                    </div>


                    <img
                        id="guerra-sprite-b"
                        src=""
                        alt=""
                    >


                    <div
                        id="guerra-nome-a"
                        class="guerra-nome-palco"
                    >
                    </div>


                    <div
                        id="guerra-nome-b"
                        class="guerra-nome-palco"
                    >
                    </div>

                </div>


                <div class="guerra-times">

                    <div class="guerra-time">

                        <div
                            id="guerra-time-a-titulo"
                            class="
                                guerra-time-titulo
                                guerra-time-a
                            "
                        >
                            🛡️ CLÃ A
                        </div>

                        <div
                            id="guerra-lista-a"
                            class="guerra-lista"
                        >
                        </div>

                    </div>


                    <div class="guerra-time">

                        <div
                            id="guerra-time-b-titulo"
                            class="
                                guerra-time-titulo
                                guerra-time-b
                            "
                        >
                            ⚔️ CLÃ B
                        </div>

                        <div
                            id="guerra-lista-b"
                            class="guerra-lista"
                        >
                        </div>

                    </div>

                </div>


                <div
                    id="guerra-log"
                    class="guerra-log"
                >
                    ⚔️ A Frente está pronta.
                    Aguarde o comando de batalha.
                </div>


                <div class="guerra-acoes">

                    <button
                        id="guerra-btn-atacar"
                        type="button"
                        class="
                            guerra-btn
                            guerra-btn-atacar
                        "
                        disabled
                    >
                        ⚔️ ATACAR
                    </button>


                    <button
                        id="guerra-btn-skill"
                        type="button"
                        class="
                            guerra-btn
                            guerra-btn-skill
                        "
                        disabled
                    >
                        ✨ SKILL
                    </button>

                </div>

            </div>
        `;


        document.body.appendChild(
            tela
        );


        const btnAtacar =
            document.getElementById(
                "guerra-btn-atacar"
            );


        if (btnAtacar) {

            btnAtacar.addEventListener(
                "click",
                executarAtaqueBasicoGuerra
            );
        }


        const btnSkill =
            document.getElementById(
                "guerra-btn-skill"
            );


        if (btnSkill) {

            btnSkill.addEventListener(
                "click",
                abrirMenuSkillsGuerra
            );
        }


        return tela;
    }


    function criarCard(
        combatente,
        turnoId,
        meuLado,
        meuTurno
    ) {

        const id =
            String(
                combatente.user_id ||
                ""
            );


        const lado =
            String(
                combatente.lado ||
                ""
            ).toLowerCase();


        const stats =
            combatente.stats ||
            {};


        const hp =
            Number(
                combatente.hp_atual ||
                0
            );


        const hpMax =
            Math.max(
                1,
                Number(
                    stats.max_hp ||
                    1
                )
            );


        const mp =
            Number(
                combatente.mp_atual ||
                0
            );


        const mpMax =
            Math.max(
                1,
                Number(
                    stats.max_mana ||
                    1
                )
            );


        const vivo =
            combatenteVivo(
                combatente
            );


        const alvoDisponivel =
            Boolean(
                meuTurno
                &&
                vivo
                &&
                lado
                &&
                lado !==
                    meuLado
            );


        const selecionado =
            (
                alvoDisponivel
                &&
                id ===
                    alvoSelecionadoId
            );


        return `

            <div
                class="
                    guerra-card
                    ${
                        id === turnoId
                            ? "turno"
                            : ""
                    }
                    ${
                        id === meuId()
                            ? "eu"
                            : ""
                    }
                    ${
                        vivo
                            ? ""
                            : "morto"
                    }
                    ${
                        alvoDisponivel
                            ? "alvo-disponivel"
                            : ""
                    }
                    ${
                        selecionado
                            ? "alvo-selecionado"
                            : ""
                    }
                "

                data-guerra-user-id="${
                    esc(
                        id
                    )
                }"
            >

                <div class="guerra-card-topo">

                    <span>
                        ${
                            vivo
                                ? (
                                    selecionado
                                        ? "🎯"
                                        : "⚔️"
                                )
                                : "💀"
                        }

                        ${
                            esc(
                                combatente.nome ||
                                "Aventureiro"
                            )
                        }
                    </span>


                    <span>
                        ${
                            selecionado
                                ? "ALVO"
                                : (
                                    id === turnoId
                                        ? "▶"
                                        : ""
                                )
                        }
                    </span>

                </div>


                <div
                    class="guerra-card-status"
                >

                    <span
                        class="
                            guerra-card-hp-texto
                            ${
                                pct(
                                    hp,
                                    hpMax
                                ) <= 30
                                    ? "baixo"
                                    : ""
                            }
                        "
                    >
                        ❤️ ${Math.max(0, hp)}/${hpMax}
                    </span>


                    <span
                        class="
                            guerra-card-mp-texto
                            ${
                                pct(
                                    mp,
                                    mpMax
                                ) <= 25
                                    ? "baixo"
                                    : ""
                            }
                        "
                    >
                        💧 ${Math.max(0, mp)}/${mpMax}
                    </span>

                </div>


                <div class="guerra-mini-bar">

                    <div
                        class="guerra-hp"
                        style="
                            width:${
                                pct(
                                    hp,
                                    hpMax
                                )
                            }%;
                        "
                    >
                    </div>

                </div>


                <div class="guerra-mini-bar">

                    <div
                        class="guerra-mp"
                        style="
                            width:${
                                pct(
                                    mp,
                                    mpMax
                                )
                            }%;
                        "
                    >
                    </div>

                </div>

            </div>
        `;
    }

    function selecionarAlvoGuerra(
        alvoId
    ) {

        const batalha =
            estadoAtual
                ?.minha_frente
                ?.batalha
                ||
                {};


        const turnoId =
            String(
                batalha.turno_user_id ||
                ""
            );


        if (
            turnoId !==
            meuId()
        ) {

            return;
        }


        const eu =
            localizarCombatente(
                meuId()
            );


        const alvo =
            localizarCombatente(
                alvoId
            );


        if (
            !eu
            ||
            !alvo
            ||
            !combatenteVivo(
                eu
            )
            ||
            !combatenteVivo(
                alvo
            )
        ) {

            return;
        }


        if (
            String(
                eu.lado ||
                ""
            ).toLowerCase()
            ===
            String(
                alvo.lado ||
                ""
            ).toLowerCase()
        ) {

            return;
        }


        alvoSelecionadoId =
            String(
                alvo.user_id
            );


        renderizar();
    }

    function animarCorteGuerra(
        spriteAlvo,
        critico = false
    ) {

        if (
            !spriteAlvo
            ||
            !spriteAlvo.parentElement
        ) {

            return;
        }


        const palco =
            spriteAlvo.parentElement;


        const rectAlvo =
            spriteAlvo.getBoundingClientRect();


        const rectPalco =
            palco.getBoundingClientRect();


        const centroX =
            (
                rectAlvo.left
                -
                rectPalco.left
            )
            +
            (
                rectAlvo.width /
                2
            );


        const centroY =
            (
                rectAlvo.top
                -
                rectPalco.top
            )
            +
            (
                rectAlvo.height /
                2
            );


        const corte =
            document.createElement(
                "div"
            );


        corte.style.cssText =
            `
                position:absolute;

                left:${centroX}px;
                top:${centroY}px;

                width:82px;
                height:7px;

                z-index:60;

                pointer-events:none;

                border-radius:999px;

                background:
                    linear-gradient(
                        90deg,
                        transparent 0%,
                        ${
                            critico
                                ? "#fde047"
                                : "#ffffff"
                        } 25%,
                        ${
                            critico
                                ? "#f59e0b"
                                : "#ef4444"
                        } 65%,
                        transparent 100%
                    );

                box-shadow:
                    0 0 7px #ffffff,
                    0 0 15px ${
                        critico
                            ? "#facc15"
                            : "#ef4444"
                    },
                    0 0 25px ${
                        critico
                            ? "#f59e0b"
                            : "#7f1d1d"
                    };

                transform:
                    translate(-50%,-50%)
                    rotate(-38deg)
                    scaleX(.15);

                opacity:0;
            `;


        palco.appendChild(
            corte
        );


        corte.animate(
            [
                {
                    opacity:
                        0,

                    transform:
                        (
                            "translate(-50%,-50%) "
                            + "rotate(-38deg) "
                            + "scaleX(.15)"
                        )
                },

                {
                    opacity:
                        1,

                    transform:
                        (
                            "translate(-50%,-50%) "
                            + "rotate(-38deg) "
                            + "scaleX(1.25)"
                        )
                },

                {
                    opacity:
                        1,

                    transform:
                        (
                            "translate(-50%,-50%) "
                            + "rotate(-38deg) "
                            + "scaleX(.9)"
                        )
                },

                {
                    opacity:
                        0,

                    transform:
                        (
                            "translate(-50%,-50%) "
                            + "rotate(-38deg) "
                            + "scaleX(1.45)"
                        )
                }
            ],
            {
                duration:
                    420,

                easing:
                    "cubic-bezier(.2,.8,.2,1)",

                fill:
                    "forwards"
            }
        );


        // Segundo corte cruzado
        const corte2 =
            corte.cloneNode(
                true
            );


        corte2.style.transform =
            (
                "translate(-50%,-50%) "
                + "rotate(38deg) "
                + "scaleX(.15)"
            );


        palco.appendChild(
            corte2
        );


        setTimeout(
            function () {

                corte2.animate(
                    [
                        {
                            opacity:0,

                            transform:
                                (
                                    "translate(-50%,-50%) "
                                    + "rotate(38deg) "
                                    + "scaleX(.15)"
                                )
                        },

                        {
                            opacity:1,

                            transform:
                                (
                                    "translate(-50%,-50%) "
                                    + "rotate(38deg) "
                                    + "scaleX(1.05)"
                                )
                        },

                        {
                            opacity:0,

                            transform:
                                (
                                    "translate(-50%,-50%) "
                                    + "rotate(38deg) "
                                    + "scaleX(1.35)"
                                )
                        }
                    ],
                    {
                        duration:
                            340,

                        easing:
                            "ease-out",

                        fill:
                            "forwards"
                    }
                );

            },
            70
        );


        setTimeout(
            function () {

                corte.remove();
                corte2.remove();

            },
            650
        );
    }

    async function animarAtaqueBasicoGuerra(
        acao
    ) {

        const atacante =
            localizarCombatente(
                acao?.atacante_id
            );


        const alvo =
            localizarCombatente(
                acao?.alvo_id
            );


        if (
            !atacante
            ||
            !alvo
        ) {

            return;
        }


        const ladoAtacante =
            String(
                atacante.lado ||
                ""
            ).toLowerCase();


        const ladoAlvo =
            String(
                alvo.lado ||
                ""
            ).toLowerCase();


        const spriteAtacante =
            document.getElementById(
                ladoAtacante === "a"
                    ? "guerra-sprite-a"
                    : "guerra-sprite-b"
            );


        const spriteAlvo =
            document.getElementById(
                ladoAlvo === "a"
                    ? "guerra-sprite-a"
                    : "guerra-sprite-b"
            );


        if (spriteAtacante) {

            const frames =
                ladoAtacante === "a"
                    ? [
                        { left:"18px" },
                        { left:"68px" },
                        { left:"68px" },
                        { left:"18px" }
                    ]
                    : [
                        { right:"18px" },
                        { right:"68px" },
                        { right:"68px" },
                        { right:"18px" }
                    ];


            try {

                await spriteAtacante
                    .animate(
                        frames,
                        {
                            duration:
                                430,

                            easing:
                                "ease-in-out"
                        }
                    )
                    .finished;

            } catch (
                erro
            ) {
                // animação interrompida
            }
        }


        if (spriteAlvo) {

            const mensagens =
                Array.isArray(
                    acao?.mensagens
                )
                    ? acao.mensagens
                    : [];


            const textoResultado =
                mensagens
                    .join(" ")
                    .toLowerCase();


            const critico =
                (
                    textoResultado.includes(
                        "crítico"
                    )
                    ||
                    textoResultado.includes(
                        "critico"
                    )
                );


            // =================================================
            // ⚔️ EFEITO VISUAL DO GOLPE
            // Mesmo conceito do combate normal.
            // =================================================

            animarCorteGuerra(
                spriteAlvo,
                critico
            );


            if (
                window.AudioManager
            ) {

                window.AudioManager
                    .tocarSFX(
                        critico
                            ? "som_critico"
                            : "som_espada"
                    );
            }


            try {

                spriteAlvo.animate(
                    [
                        {
                            transform:
                                (
                                    ladoAlvo === "b"
                                        ? "scaleX(-1) translate(0,0)"
                                        : "translate(0,0)"
                                ),

                            filter:
                                "brightness(1)"
                        },

                        {
                            transform:
                                (
                                    ladoAlvo === "b"
                                        ? "scaleX(-1) translate(-7px,3px)"
                                        : "translate(-7px,3px)"
                                ),

                            filter:
                                "brightness(2.8) saturate(1.8)"
                        },

                        {
                            transform:
                                (
                                    ladoAlvo === "b"
                                        ? "scaleX(-1) translate(7px,-3px)"
                                        : "translate(7px,-3px)"
                                ),

                            filter:
                                "brightness(.55)"
                        },

                        {
                            transform:
                                (
                                    ladoAlvo === "b"
                                        ? "scaleX(-1) translate(0,0)"
                                        : "translate(0,0)"
                                ),

                            filter:
                                "brightness(1)"
                        }
                    ],
                    {
                        duration:
                            360,

                        easing:
                            "ease-out"
                    }
                );


            } catch (
                erro
            ) {

                // Efeito visual nunca pode
                // interromper a batalha.
            }
        }


        const palco =
            document.querySelector(
                ".guerra-palco"
            );


        if (palco) {

            const numero =
                document.createElement(
                    "div"
                );


            numero.textContent =
                (
                    Number(
                        acao?.dano ||
                        0
                    ) > 0
                        ? `-${Number(acao.dano)}`
                        : "ESQUIVOU"
                );


            numero.style.cssText =
                `
                    position:absolute;
                    top:74px;
                    z-index:50;
                    ${
                        ladoAlvo === "a"
                            ? "left:82px;"
                            : "right:82px;"
                    }
                    color:${
                        Number(
                            acao?.dano ||
                            0
                        ) > 0
                            ? "#f87171"
                            : "#e2e8f0"
                    };
                    font-size:21px;
                    font-weight:1000;
                    text-shadow:
                        0 2px 4px #000;
                    pointer-events:none;
                `;


            palco.appendChild(
                numero
            );


            try {

                await numero
                    .animate(
                        [
                            {
                                opacity:0,
                                transform:
                                    "translateY(8px) scale(.7)"
                            },
                            {
                                opacity:1,
                                transform:
                                    "translateY(0) scale(1.15)"
                            },
                            {
                                opacity:0,
                                transform:
                                    "translateY(-32px) scale(1)"
                            }
                        ],
                        {
                            duration:
                                700,

                            easing:
                                "ease-out"
                        }
                    )
                    .finished;

            } catch (
                erro
            ) {
                // segue normalmente
            }


            numero.remove();
        }
    }


    async function executarAtaqueBasicoGuerra() {

        if (
            window.AudioManager
        ) {

            window.AudioManager
                .desbloquearAudio();
        }

        if (
            enviandoAtaque
        ) {

            return;
        }


        if (
            !alvoSelecionadoId
        ) {

            return;
        }


        const userId =
            meuId();


        if (!userId) {

            return;
        }


        const batalha =
            estadoAtual
                ?.minha_frente
                ?.batalha
                ||
                {};


        if (
            String(
                batalha.turno_user_id ||
                ""
            )
            !==
            userId
        ) {

            renderizar();

            return;
        }


        enviandoAtaque =
            true;


        renderizar();


        try {

            const resposta =
                await fetch(
                    "/api/clan/guerra/batalha/ataque",
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

                                alvo_id:
                                    alvoSelecionadoId,
                            })
                    }
                );


            const dados =
                await resposta.json();


            if (
                !resposta.ok
                ||
                dados.success ===
                    false
            ) {

                throw new Error(
                    dados.error ||
                    "O ataque não foi executado."
                );
            }


            await animarAtaqueBasicoGuerra(
                dados.acao ||
                {}
            );


            alvoSelecionadoId =
                null;


            if (
                dados.estado_guerra
                ?.success
            ) {

                estadoAtual =
                    dados.estado_guerra;
            }


            renderizar();


        } catch (
            erro
        ) {

            console.error(
                "❌ [GUERRA] Ataque:",
                erro
            );

            await atualizarEstadoOficialGuerra();

            const log =
                document.getElementById(
                    "guerra-log"
                );


            if (log) {

                log.innerHTML =
                    `
                        <span
                            style="
                                color:#f87171;
                                font-weight:900;
                            "
                        >
                            ⚠️ ${
                                esc(
                                    erro.message ||
                                    "Ataque inválido."
                                )
                            }
                        </span>
                    `;
            }


        } finally {

            enviandoAtaque =
                false;


            renderizar();
        }
    }

    function obterDadosSkillGuerra(
        skillId
    ) {

        const perfil =
            window.perfilDadosGlobais ||
            {};


        const database =
            perfil.database_skills ||
            perfil.skills_database ||
            {};


        const base =
            database[
                skillId
            ]
            ||
            {};


        const minhasSkills =
            perfil.skills_desbloqueadas
            ||
            perfil.skills
            ||
            {};


        const instancia =
            minhasSkills[
                skillId
            ]
            ||
            {};


        const raridade =
            instancia.rarity ||
            "comum";


        const rarityData =
            base.rarity_effects
                ?.[raridade]
            ||
            base.rarity_effects
                ?.comum
            ||
            {};


        return {
            ...base,
            ...rarityData,

            effects:
                rarityData.effects
                ||
                base.effects
                ||
                {},

            rarity:
                raridade
        };
    }


    function skillEhSuporteGuerra(
        skillId
    ) {

        const skill =
            obterDadosSkillGuerra(
                skillId
            );


        const effects =
            skill.effects ||
            {};


        return (
            String(
                skill.type ||
                ""
            ).toLowerCase()
                ===
                "support"

            ||
            effects.party_heal

            ||
            effects.party_mana

            ||
            effects.party_buff

            ||
            effects.self_heal_percent

            ||
            effects.target ===
                "ally"

            ||
            effects.target ===
                "party"

            ||
            effects.target ===
                "grupo"
        );
    }


    function fecharMenuSkillsGuerra() {

        const menu =
            document.getElementById(
                "guerra-menu-skills"
            );


        if (menu) {

            menu.remove();
        }
    }


    function abrirMenuSkillsGuerra() {

        if (
            window.AudioManager
        ) {

            window.AudioManager
                .desbloquearAudio();
        }        
        if (
            enviandoAtaque
            ||
            enviandoSkill
        ) {

            return;
        }


        const batalha =
            estadoAtual
                ?.minha_frente
                ?.batalha
            ||
            {};


        if (
            String(
                batalha.turno_user_id ||
                ""
            )
            !==
            meuId()
        ) {

            return;
        }


        if (
            !alvoSelecionadoId
        ) {

            const log =
                document.getElementById(
                    "guerra-log"
                );


            if (log) {

                log.innerHTML =
                    `
                        <span
                            style="
                                color:#facc15;
                                font-weight:900;
                            "
                        >
                            🎯 Escolha primeiro
                            um inimigo.
                        </span>
                    `;
            }


            return;
        }


        fecharMenuSkillsGuerra();


        const perfil =
            window.perfilDadosGlobais ||
            {};


        const equipadas =
            perfil.skills_equipadas
            ||
            perfil.equipped_skills
            ||
            {};


        const meuCombatente =
            localizarCombatente(
                meuId()
            )
            ||
            {};


        const mpAtual =
            Number(
                meuCombatente.mp_atual ||
                0
            );


        const cooldowns =
            meuCombatente.cooldowns ||
            {};


        const overlay =
            document.createElement(
                "div"
            );


        overlay.id =
            "guerra-menu-skills";


        overlay.style.cssText =
            `
                position:fixed;
                inset:0;

                z-index:1000100;

                display:flex;
                align-items:center;
                justify-content:center;

                padding:12px;

                background:
                    rgba(2,6,23,.82);

                backdrop-filter:
                    blur(5px);
            `;


        let html =
            `
                <div
                    style="
                        width:min(92vw,350px);

                        padding:14px;

                        background:
                            linear-gradient(
                                180deg,
                                #111827,
                                #020617
                            );

                        border:
                            1px solid #8b5cf6;

                        border-radius:14px;

                        box-shadow:
                            0 20px 55px
                            rgba(0,0,0,.85);

                        color:#fff;
                    "
                >

                    <div
                        style="
                            margin-bottom:4px;

                            color:#c4b5fd;

                            font-family:
                                Cinzel,
                                serif;

                            font-weight:900;

                            text-align:center;
                        "
                    >
                        ✨ SKILLS
                    </div>

                    <div
                        style="
                            margin-bottom:12px;

                            color:#60a5fa;

                            font-size:11px;

                            text-align:center;
                        "
                    >
                        💧 MP ${mpAtual}
                    </div>

                    <div
                        id="guerra-skills-grid"

                        style="
                            display:grid;

                            grid-template-columns:
                                1fr 1fr;

                            gap:8px;
                        "
                    >
            `;


        let encontrou =
            false;


        [1, 2, 3, 4, 5]
            .forEach(
                function (
                    slot
                ) {

                    const skillId =
                        equipadas[
                            `slot_${slot}`
                        ];


                    if (!skillId) {

                        return;
                    }


                    encontrou =
                        true;


                    const skill =
                        obterDadosSkillGuerra(
                            skillId
                        );


                    const nome =
                        skill.display_name
                        ||
                        skill.name
                        ||
                        String(
                            skillId
                        )
                        .replaceAll(
                            "_",
                            " "
                        );


                    // =========================================
                    // 🖼️ ÍCONE OFICIAL DA SKILL
                    //
                    // Mesmo padrão usado pelo combate/Raid.
                    // =========================================

                    const icone =
                        skill.icon
                        ||
                        "default_skill";


                    const imagemSkill =
                        (
                            "https://raw.githubusercontent.com/"
                            +
                            "Eldorabotpy/static-img/main/"
                            +
                            "assets/sprites/skills/"
                            +
                            icone
                            +
                            ".png"
                        );


                    const custo =
                        Number(
                            skill.mana_cost
                            ||
                            skill.mp_cost
                            ||
                            0
                        );


                    const cd =
                        Number(
                            cooldowns[
                                skillId
                            ]
                            ||
                            0
                        );


                    const suporte =
                        skillEhSuporteGuerra(
                            skillId
                        );


                    const passiva =
                        String(
                            skill.type ||
                            ""
                        ).toLowerCase()
                            ===
                            "passive";


                    const semMana =
                        mpAtual <
                        custo;


                    const bloqueada =
                        (
                            cd > 0
                            ||
                            semMana
                            ||
                            suporte
                            ||
                            passiva
                        );


                    let motivo =
                        "";


                    if (cd > 0) {

                        motivo =
                            `⏳ CD ${cd}`;

                    } else if (
                        semMana
                    ) {

                        motivo =
                            "💧 SEM MP";

                    } else if (
                        suporte
                    ) {

                        motivo =
                            "💚 SUPORTE";

                    } else if (
                        passiva
                    ) {

                        motivo =
                            "🔒 PASSIVA";
                    }


                    html +=
                        `
                            <button
                                type="button"

                                data-skill-id="${
                                    esc(
                                        skillId
                                    )
                                }"

                                ${
                                    bloqueada
                                        ? "disabled"
                                        : ""
                                }

                                style="
                                    min-height:78px;

                                    padding:8px;

                                    color:#fff;

                                    background:
                                        rgba(30,41,59,.96);

                                    border:
                                        1px solid ${
                                            bloqueada
                                                ? "#475569"
                                                : "#8b5cf6"
                                        };

                                    border-radius:10px;

                                    font-weight:900;

                                    opacity:${
                                        bloqueada
                                            ? ".5"
                                            : "1"
                                    };
                                "
                            >

                                <img
                                    src="${
                                        esc(
                                            imagemSkill
                                        )
                                    }"

                                    alt="${
                                        esc(
                                            nome
                                        )
                                    }"

                                    onerror="
                                        this.onerror=null;
                                        this.src='https://raw.githubusercontent.com/Eldorabotpy/static-img/main/assets/sprites/skills/default_skill.png';
                                    "

                                    style="
                                        width:44px;
                                        height:44px;

                                        display:block;

                                        margin:
                                            0 auto 6px;

                                        object-fit:cover;

                                        background:#020617;

                                        border:
                                            1px solid #475569;

                                        border-radius:8px;

                                        box-shadow:
                                            0 3px 8px
                                            rgba(0,0,0,.45);
                                    "
                                >


                                <div
                                    style="
                                        font-size:10px;

                                        line-height:1.15;

                                        text-align:center;
                                    "
                                >
                                    ${
                                        esc(
                                            nome
                                        )
                                    }
                                </div>


                                <div
                                    style="
                                        margin-top:6px;

                                        color:#60a5fa;

                                        font-size:10px;
                                    "
                                >
                                    💧 ${custo} MP
                                </div>

                                ${
                                    motivo
                                        ? (
                                            `
                                                <div
                                                    style="
                                                        margin-top:3px;

                                                        color:#fca5a5;

                                                        font-size:9px;
                                                    "
                                                >
                                                    ${motivo}
                                                </div>
                                            `
                                        )
                                        : ""
                                }

                            </button>
                        `;
                }
            );


        if (!encontrou) {

            html +=
                `
                    <div
                        style="
                            grid-column:1/-1;

                            padding:20px 5px;

                            color:#94a3b8;

                            text-align:center;
                        "
                    >
                        Nenhuma skill equipada.
                    </div>
                `;
        }


        html +=
            `
                    </div>


                    <button
                        id="guerra-fechar-skills"

                        type="button"

                        style="
                            width:100%;

                            margin-top:12px;
                            padding:8px;

                            color:#cbd5e1;

                            background:
                                transparent;

                            border:
                                1px solid #475569;

                            border-radius:9px;
                        "
                    >
                        Fechar
                    </button>

                </div>
            `;


        overlay.innerHTML =
            html;


        document.body.appendChild(
            overlay
        );


        overlay
            .querySelectorAll(
                "button[data-skill-id]:not(:disabled)"
            )
            .forEach(
                function (
                    botao
                ) {

                    botao.addEventListener(
                        "click",
                        function () {

                            executarSkillOfensivaGuerra(
                                botao.dataset
                                    .skillId
                            );
                        }
                    );
                }
            );


        const fechar =
            document.getElementById(
                "guerra-fechar-skills"
            );


        if (fechar) {

            fechar.addEventListener(
                "click",
                fecharMenuSkillsGuerra
            );
        }
    }


    async function animarSkillOfensivaGuerra(
        acao
    ) {

        const ladoAlvo =
            String(
                acao?.alvo_lado ||
                ""
            ).toLowerCase();


        const alvoSpriteId =
            ladoAlvo === "a"
                ? "guerra-sprite-a"
                : "guerra-sprite-b";


        const spriteAlvo =
            document.getElementById(
                alvoSpriteId
            );


        const mensagens =
            Array.isArray(
                acao?.mensagens
            )
                ? acao.mensagens
                : [];


        const texto =
            mensagens
                .join(" ")
                .toLowerCase();


        const critico =
            (
                texto.includes(
                    "crítico"
                )
                ||
                texto.includes(
                    "critico"
                )
            );


        const efeito =
            String(
                acao?.anim_effect ||
                ""
            );


        if (
            window.AudioManager
        ) {

            let som =
                "som_magia";


            if (
                efeito.includes(
                    "fogo"
                )
                ||
                efeito.includes(
                    "bola_de_fogo"
                )
            ) {

                som =
                    "som_fogo";
            }


            window.AudioManager
                .tocarSFX(
                    critico
                        ? "som_critico"
                        : som
                );
        }


        if (
            efeito
            &&
            typeof window
                .animarMagiaSpriteGrid
                ===
                "function"
        ) {

            window
                .animarMagiaSpriteGrid(
                    alvoSpriteId,
                    efeito
                );


        } else if (
            spriteAlvo
        ) {

            // Fallback visual se a skill
            // ainda não possuir anim_effect.
            animarCorteGuerra(
                spriteAlvo,
                critico
            );
        }


        if (spriteAlvo) {

            try {

                spriteAlvo.animate(
                    [
                        {
                            filter:
                                "brightness(1)"
                        },

                        {
                            filter:
                                "brightness(2.5)"
                        },

                        {
                            filter:
                                "brightness(.55)"
                        },

                        {
                            filter:
                                "brightness(1)"
                        }
                    ],
                    {
                        duration:
                            450
                    }
                );

            } catch (
                erro
            ) {
            }
        }


        const palco =
            document.querySelector(
                ".guerra-palco"
            );


        if (palco) {

            const numero =
                document.createElement(
                    "div"
                );


            const dano =
                Number(
                    acao?.dano ||
                    0
                );


            numero.textContent =
                dano > 0
                    ? `-${dano}`
                    : "ESQUIVOU";


            numero.style.cssText =
                `
                    position:absolute;

                    top:70px;

                    ${
                        ladoAlvo === "a"
                            ? "left:82px;"
                            : "right:82px;"
                    }

                    z-index:70;

                    color:${
                        critico
                            ? "#fde047"
                            : "#f87171"
                    };

                    font-size:22px;
                    font-weight:1000;

                    text-shadow:
                        0 2px 4px #000;

                    pointer-events:none;
                `;


            palco.appendChild(
                numero
            );


            try {

                await numero
                    .animate(
                        [
                            {
                                opacity:0,
                                transform:
                                    "translateY(8px) scale(.7)"
                            },

                            {
                                opacity:1,
                                transform:
                                    "translateY(0) scale(1.2)"
                            },

                            {
                                opacity:0,
                                transform:
                                    "translateY(-34px) scale(1)"
                            }
                        ],
                        {
                            duration:
                                850,

                            easing:
                                "ease-out"
                        }
                    )
                    .finished;

            } catch (
                erro
            ) {
            }


            numero.remove();
        }
    }


    async function executarSkillOfensivaGuerra(
        skillId
    ) {

        if (
            window.AudioManager
        ) {

            window.AudioManager
                .desbloquearAudio();
        }        

        if (
            enviandoAtaque
            ||
            enviandoSkill
        ) {

            return;
        }


        if (
            !alvoSelecionadoId
        ) {

            return;
        }


        fecharMenuSkillsGuerra();


        enviandoSkill =
            true;


        renderizar();


        try {

            const resposta =
                await fetch(
                    "/api/clan/guerra/batalha/skill",
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
                                    meuId(),

                                alvo_id:
                                    alvoSelecionadoId,

                                skill_id:
                                    skillId,
                            })
                    }
                );


            const dados =
                await resposta.json();


            if (
                !resposta.ok
                ||
                dados.success ===
                    false
            ) {

                throw new Error(
                    dados.error
                    ||
                    "A skill não pôde ser usada."
                );
            }


            await animarSkillOfensivaGuerra(
                dados.acao ||
                {}
            );


            alvoSelecionadoId =
                null;


            if (
                dados.estado_guerra
                    ?.success
            ) {

                estadoAtual =
                    dados.estado_guerra;
            }


            renderizar();


        } catch (
            erro
        ) {

            console.error(
                "❌ [GUERRA SKILL]",
                erro
            );


            const log =
                document.getElementById(
                    "guerra-log"
                );


            if (log) {

                log.innerHTML =
                    `
                        <span
                            style="
                                color:#f87171;
                                font-weight:900;
                            "
                        >
                            ⚠️ ${
                                esc(
                                    erro.message ||
                                    "Skill inválida."
                                )
                            }
                        </span>
                    `;
            }


        } finally {

            enviandoSkill =
                false;


            renderizar();
        }
    }

    async function atualizarEstadoOficialGuerra() {

        const userId =
            meuId();


        if (!userId) {

            return false;
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
                !resposta.ok
                ||
                dados.success === false
            ) {

                return false;
            }


            estadoAtual =
                dados;


            return true;


        } catch (
            erro
        ) {

            console.warn(
                "⚠️ [GUERRA] "
                + "Falha ao atualizar estado oficial:",
                erro
            );


            return false;
        }
    }

    async function sincronizarBatalhaGuerra() {

        if (
            enviandoAtaque
            ||
            enviandoSkill
        ) {

            return;
        }


        const tela =
            document.getElementById(
                "tela-guerra-clans"
            );


        if (
            !tela
            ||
            tela.style.display !==
                "block"
        ) {

            return;
        }


        const userId =
            meuId();


        if (!userId) {

            return;
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
                resposta.ok
                &&
                dados.success !==
                    false
            ) {

                estadoAtual =
                    dados;


                renderizar();
            }


        } catch (
            erro
        ) {

            console.warn(
                "⚠️ [GUERRA] "
                + "Falha temporária ao sincronizar:",
                erro
            );
        }
    }


    function iniciarSincronizacaoGuerra() {

        if (
            intervaloSincronizacao
        ) {

            clearInterval(
                intervaloSincronizacao
            );
        }


        intervaloSincronizacao =
            setInterval(
                sincronizarBatalhaGuerra,
                2000
            );
    }


    function pararSincronizacaoGuerra() {

        if (
            intervaloSincronizacao
        ) {

            clearInterval(
                intervaloSincronizacao
            );


            intervaloSincronizacao =
                null;
        }
    }

    function renderizar() {

        if (!estadoAtual) {
            return;
        }


        const frente =
            estadoAtual.minha_frente ||
            {};


        const batalha =
            frente.batalha ||
            {};


        const batalhaFinalizada =
            String(
                batalha.estado ||
                ""
            )
            ===
            "finalizada";


        const ladoVencedor =
            batalhaFinalizada
                ? obterLadoVencedorFrente(
                    frente,
                    batalha
                )
                : null;


        const lista =
            combatentes();


        const turnoId =
            String(
                batalha.turno_user_id ||
                ""
            );


        const atacante =
            localizarCombatente(
                turnoId
            );


        const meuCombatente =
            localizarCombatente(
                meuId()
            );


        const meuLado =
            String(
                meuCombatente?.lado ||
                ""
            ).toLowerCase();


        const meuTurno =
            Boolean(
                turnoId
                &&
                turnoId ===
                    meuId()
                &&
                combatenteVivo(
                    meuCombatente
                )
            );


        let alvoSelecionado =
            localizarCombatente(
                alvoSelecionadoId
            );


        if (
            !meuTurno
            ||
            !alvoSelecionado
            ||
            !combatenteVivo(
                alvoSelecionado
            )
            ||
            String(
                alvoSelecionado.lado ||
                ""
            ).toLowerCase()
                ===
                meuLado
        ) {

            alvoSelecionadoId =
                null;


            alvoSelecionado =
                null;
        }


        const alvoVisual =
            (
                alvoSelecionado
                ||
                encontrarAlvoVisual(
                    atacante
                )
            );


        const ladoA =
            lista.filter(
                jogador =>
                    String(
                        jogador.lado ||
                        ""
                    ).toLowerCase()
                    === "a"
            );


        const ladoB =
            lista.filter(
                jogador =>
                    String(
                        jogador.lado ||
                        ""
                    ).toLowerCase()
                    === "b"
            );


        const titulo =
            document.getElementById(
                "guerra-subtitulo"
            );


        if (titulo) {

            titulo.textContent =
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


        const aviso =
            document.getElementById(
                "guerra-aviso-turno"
            );


        if (aviso) {

            if (
                batalhaFinalizada
            ) {

                if (
                    ladoVencedor
                ) {

                    aviso.textContent =
                        (
                            "🏆 "
                            +
                            obterNomeCla(
                                ladoVencedor
                            )
                            +
                            " VENCEU A FRENTE!"
                        );


                } else {

                    aviso.textContent =
                        "🏁 FRENTE FINALIZADA";
                }


                aviso.style.color =
                    "#fde047";


                aviso.style.borderColor =
                    "#facc15";


            } else if (
                turnoId
                &&
                turnoId ===
                    meuId()
            ) {

                aviso.textContent =
                    "✅ SUA VEZ DE AGIR!";


                aviso.style.color =
                    "#22c55e";


                aviso.style.borderColor =
                    "#22c55e";


            } else {

                aviso.textContent =
                    (
                        "⏳ Turno de "
                        +
                        (
                            atacante?.nome ||
                            "Aventureiro"
                        )
                    );


                aviso.style.color =
                    "#facc15";


                aviso.style.borderColor =
                    "#facc15";
            }
        }


        const timeATitulo =
            document.getElementById(
                "guerra-time-a-titulo"
            );


        const timeBTitulo =
            document.getElementById(
                "guerra-time-b-titulo"
            );


        if (timeATitulo) {

            timeATitulo.textContent =
                "🛡️ "
                +
                obterNomeCla(
                    "a"
                );
        }


        if (timeBTitulo) {

            timeBTitulo.textContent =
                "⚔️ "
                +
                obterNomeCla(
                    "b"
                );
        }


        const listaA =
            document.getElementById(
                "guerra-lista-a"
            );


        const listaB =
            document.getElementById(
                "guerra-lista-b"
            );


        if (listaA) {

            listaA.innerHTML =
                ladoA
                    .map(
                        jogador =>
                            criarCard(
                                jogador,
                                turnoId,
                                meuLado,
                                meuTurno
                            )
                    )
                    .join("");
        }


        if (listaB) {

            listaB.innerHTML =
                ladoB
                    .map(
                        jogador =>
                            criarCard(
                                jogador,
                                turnoId,
                                meuLado,
                                meuTurno
                            )
                    )
                    .join("");
        }

        document
            .querySelectorAll(
                "#tela-guerra-clans "
                + ".guerra-card.alvo-disponivel"
            )
            .forEach(
                function (
                    card
                ) {

                    card.addEventListener(
                        "click",
                        function () {

                            selecionarAlvoGuerra(
                                card.dataset
                                    .guerraUserId
                            );
                        }
                    );
                }
            );

        const spriteA =
            document.getElementById(
                "guerra-sprite-a"
            );


        const spriteB =
            document.getElementById(
                "guerra-sprite-b"
            );


        const nomeA =
            document.getElementById(
                "guerra-nome-a"
            );


        const nomeB =
            document.getElementById(
                "guerra-nome-b"
            );


        let visualA =
            null;

        let visualB =
            null;


        if (atacante) {

            if (
                String(
                    atacante.lado ||
                    ""
                ).toLowerCase()
                === "a"
            ) {

                visualA =
                    atacante;

                visualB =
                    alvoVisual;


            } else {

                visualB =
                    atacante;

                visualA =
                    alvoVisual;
            }
        }


        if (
            spriteA
            &&
            visualA
        ) {

            spriteA.src =
                urlSkinCombatente(
                    visualA
                );


            spriteA.onerror =
                function () {

                    this.onerror =
                        null;

                    this.src =
                        (
                            BASE_SKINS
                            +
                            "aventureiro_m.png?v=3"
                        );
                };
        }


        if (
            spriteB
            &&
            visualB
        ) {

            spriteB.src =
                urlSkinCombatente(
                    visualB
                );


            spriteB.onerror =
                function () {

                    this.onerror =
                        null;

                    this.src =
                        (
                            BASE_SKINS
                            +
                            "aventureiro_m.png?v=3"
                        );
                };
        }


        if (nomeA) {

            nomeA.textContent =
                visualA
                    ? `⚔️ ${visualA.nome}`
                    : "";
        }


        if (nomeB) {

            nomeB.textContent =
                visualB
                    ? `⚔️ ${visualB.nome}`
                    : "";
        }

        const btnAtacar =
            document.getElementById(
                "guerra-btn-atacar"
            );


        const btnSkill =
            document.getElementById(
                "guerra-btn-skill"
            );


        if (btnAtacar) {

            btnAtacar.disabled =
                !(
                    meuTurno
                    &&
                    alvoSelecionado
                    &&
                    !enviandoAtaque
                    &&
                    !enviandoSkill
                );


            btnAtacar.textContent =
                batalhaFinalizada
                    ? "🏁 ENCERRADA"
                    : (
                        enviandoAtaque
                            ? "⏳ ATACANDO..."
                            : "⚔️ ATACAR"
                    );
        }


        if (btnSkill) {

            btnSkill.disabled =
                !(
                    meuTurno
                    &&
                    alvoSelecionado
                    &&
                    !enviandoAtaque
                    &&
                    !enviandoSkill
                );


            btnSkill.textContent =
                batalhaFinalizada
                    ? "🏆 RESULTADO"
                    : (
                        enviandoSkill
                            ? "⏳ CONJURANDO..."
                            : "✨ SKILL"
                    );
        }

        const log =
            document.getElementById(
                "guerra-log"
            );


        if (log) {

            const historico =
                Array.isArray(
                    batalha.log
                )
                    ? batalha.log
                    : [];


            const ultimo =
                historico.length
                    ? historico[
                        historico.length - 1
                    ]
                    : null;


            let htmlLog =
                "";


            if (
                ultimo
                &&
                typeof ultimo ===
                    "object"
                &&
                ultimo.tipo ===
                    "ataque_basico"
            ) {

                htmlLog +=
                    `
                        <div
                            style="
                                margin-bottom:7px;
                                padding-bottom:7px;
                                border-bottom:
                                    1px solid #1e293b;
                            "
                        >
                            ⚔️
                            <strong>
                                ${
                                    esc(
                                        ultimo.atacante_nome ||
                                        "Aventureiro"
                                    )
                                }
                            </strong>

                            atacou

                            <strong>
                                ${
                                    esc(
                                        ultimo.alvo_nome ||
                                        "Aventureiro"
                                    )
                                }
                            </strong>

                            e causou

                            <strong
                                style="
                                    color:#f87171;
                                "
                            >
                                ${
                                    Number(
                                        ultimo.dano ||
                                        0
                                    )
                                } de dano
                            </strong>.

                            ${
                                ultimo.alvo_derrotado
                                    ? (
                                        "<br>"
                                        + "💀 Alvo derrotado!"
                                    )
                                    : ""
                            }
                        </div>
                    `;
            }

            if (
                ultimo
                &&
                typeof ultimo ===
                    "object"
                &&
                ultimo.tipo ===
                    "skill_ofensiva"
            ) {

                htmlLog +=
                    `
                        <div
                            style="
                                margin-bottom:7px;
                                padding-bottom:7px;

                                border-bottom:
                                    1px solid #1e293b;
                            "
                        >
                            ✨

                            <strong>
                                ${
                                    esc(
                                        ultimo.atacante_nome
                                        ||
                                        "Aventureiro"
                                    )
                                }
                            </strong>

                            usou

                            <strong
                                style="
                                    color:#c4b5fd;
                                "
                            >
                                ${
                                    esc(
                                        ultimo.skill_nome
                                        ||
                                        "Skill"
                                    )
                                }
                            </strong>

                            em

                            <strong>
                                ${
                                    esc(
                                        ultimo.alvo_nome
                                        ||
                                        "Aventureiro"
                                    )
                                }
                            </strong>

                            e causou

                            <strong
                                style="
                                    color:#f87171;
                                "
                            >
                                ${
                                    Number(
                                        ultimo.dano ||
                                        0
                                    )
                                } de dano
                            </strong>.

                            ${
                                ultimo.alvo_derrotado
                                    ? (
                                        "<br>"
                                        + "💀 Alvo derrotado!"
                                    )
                                    : ""
                            }
                        </div>
                    `;
            }

            if (
                batalhaFinalizada
            ) {

                htmlLog +=
                    `
                        <div
                            style="
                                margin-top:6px;

                                color:#fde047;

                                font-weight:900;

                                text-align:center;
                            "
                        >
                            🏆 FRENTE ${
                                Number(
                                    frente.numero ||
                                    0
                                )
                            } FINALIZADA
                        </div>


                        <div
                            style="
                                margin-top:4px;

                                color:#e2e8f0;

                                text-align:center;
                            "
                        >
                            ${
                                ladoVencedor
                                    ? (
                                        esc(
                                            obterNomeCla(
                                                ladoVencedor
                                            )
                                        )
                                        +
                                        " venceu esta batalha!"
                                    )
                                    : "A batalha foi encerrada."
                            }
                        </div>
                    `;


            } else if (
                meuTurno
            ) {

                htmlLog +=
                    `
                        <span
                            style="
                                color:#22c55e;
                                font-weight:900;
                            "
                        >
                            ✅ É o seu turno.
                        </span>

                        ${
                            alvoSelecionado
                                ? (
                                    " Alvo selecionado: "
                                    +
                                    "<strong>"
                                    +
                                    esc(
                                        alvoSelecionado.nome ||
                                        "Aventureiro"
                                    )
                                    +
                                    "</strong>."
                                )
                                : (
                                    " Toque em um inimigo "
                                    + "para escolher o alvo."
                                )
                        }
                    `;


            } else {

                htmlLog +=
                    `
                        <span
                            style="
                                color:#facc15;
                                font-weight:900;
                            "
                        >
                            ⏳ ${
                                esc(
                                    atacante?.nome ||
                                    "Aventureiro"
                                )
                            }
                        </span>

                        está escolhendo uma ação.
                    `;
            }


            log.innerHTML =
                htmlLog;
        }
    }


    window.abrirBatalhaGuerraCla =
        async function (
            dados
        ) {

            estadoAtual =
                dados;

            // =============================================
            // 🔊 DESBLOQUEIA ÁUDIO NO CLIQUE QUE ABRIU
            // A BATALHA, ANTES DE QUALQUER await.
            // =============================================

            if (
                window.AudioManager
                &&
                typeof window.AudioManager
                    .desbloquearAudio ===
                    "function"
            ) {

                window.AudioManager
                    .desbloquearAudio();
            }

            // =================================================
            // ✨ CARREGA O GRIMÓRIO REAL DO PERSONAGEM
            //
            // Mesma rota usada pelo combate normal e pela Raid.
            // Ela fornece:
            // - skills_equipadas
            // - skills_desbloqueadas
            // - database_skills
            // =================================================

            try {

                const charId =
                    meuId();


                if (charId) {

                    const respostaPerfil =
                        await fetch(
                            (
                                "/api/personagem/"
                                +
                                encodeURIComponent(
                                    charId
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


                    const perfil =
                        await respostaPerfil.json();


                    if (
                        respostaPerfil.ok
                        &&
                        !perfil.erro
                    ) {

                        window.perfilDadosGlobais =
                            perfil;


                        console.log(
                            "✨ [GUERRA] Grimório carregado:",
                            {
                                skills_equipadas:
                                    perfil.skills_equipadas,

                                skills_desbloqueadas:
                                    perfil.skills_desbloqueadas
                            }
                        );


                    } else {

                        console.warn(
                            "⚠️ [GUERRA] "
                            + "Perfil de combate não carregado:",
                            perfil
                        );
                    }
                }


            } catch (
                erro
            ) {

                console.warn(
                    "⚠️ [GUERRA] "
                    + "Falha ao carregar o Grimório:",
                    erro
                );
            }

            // =================================================
            // 🎭 CARREGA AS SKINS REAIS DOS 10 COMBATENTES
            // =================================================

            await carregarSkinsCombatentesGuerra();
            
            const frente =
                dados
                    ?.minha_frente;


            if (
                !frente
                ||
                frente
                    ?.batalha
                    ?.estado !==
                    "preparada"
            ) {

                console.warn(
                    "⚠️ Batalha da Guerra "
                    + "ainda não preparada."
                );

                return;
            }


            const tela =
                garantirTela();


            // =================================================
            // 📡 CONFIRMA O TURNO DIRETAMENTE NO BACKEND
            // ANTES DE LIBERAR QUALQUER AÇÃO.
            // =================================================

            await atualizarEstadoOficialGuerra();


            renderizar();


            tela.style.display =
                "block";


            iniciarSincronizacaoGuerra();


            tela.setAttribute(
                "aria-hidden",
                "false"
            );


            /*
             * Mesma ideia usada pelas outras
             * interfaces de combate.
             */
            document.body.classList.add(
                "combate-aberto"
            );
        };


    window.fecharBatalhaGuerraCla =
        function () {

            const tela =
                document.getElementById(
                    "tela-guerra-clans"
                );


            if (tela) {

                tela.style.display =
                    "none";

                tela.setAttribute(
                    "aria-hidden",
                    "true"
                );
            }

            pararSincronizacaoGuerra();


            alvoSelecionadoId =
                null;

            document.body.classList.remove(
                "combate-aberto"
            );
        };


})();