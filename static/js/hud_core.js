// ==========================================
// MUNDO DE ELDORA - MOTOR CENTRAL DO HUD (hud_core.js)
// ==========================================
window.injetarMenuStatusFlutuante = function() {

    if (
        document.getElementById(
            'hud-status-flutuante'
        )
    ) {
        return;
    }

    // ======================================================
    // 🛡️ OVERLAY
    // Bloqueia totalmente os cliques no mapa enquanto
    // o painel estiver aberto.
    // ======================================================

    const htmlMenu = `

        <div
            id="hud-status-overlay"
            style="
                display:none;

                position:fixed;
                inset:0;

                width:100vw;
                height:100vh;

                background:
                    rgba(2, 6, 23, 0.18);

                z-index:19990;

                pointer-events:auto;
            "
        >

            <div
                id="hud-status-flutuante"
                style="
                    display:none;

                    position:absolute;

                    top:120px;
                    left:15px;

                    width:235px;

                    padding:0;

                    overflow:hidden;

                    background:
                        linear-gradient(
                            180deg,
                            rgba(13, 24, 42, .99) 0%,
                            rgba(6, 14, 26, .99) 100%
                        );

                    border:
                        1px solid
                        rgba(212, 175, 55, .55);

                    border-radius:16px;

                    box-shadow:
                        0 12px 35px
                        rgba(0,0,0,.72),

                        0 0 0 1px
                        rgba(40,120,180,.15),

                        inset 0 1px 0
                        rgba(255,255,255,.04);

                    z-index:19991;

                    color:#f8fafc;

                    font-family:
                        Arial,
                        sans-serif;
                "
            >

                <!-- ====================================== -->
                <!-- 👑 CABEÇALHO -->
                <!-- ====================================== -->

                <div
                    style="
                        position:relative;

                        padding:
                            14px
                            40px
                            12px
                            14px;

                        background:
                            linear-gradient(
                                135deg,
                                rgba(22,39,65,.98),
                                rgba(9,20,36,.98)
                            );

                        border-bottom:
                            1px solid
                            rgba(212,175,55,.28);
                    "
                >

                    <!-- detalhe dourado -->
                    <div
                        style="
                            position:absolute;
                            left:0;
                            top:0;
                            bottom:0;

                            width:4px;

                            background:
                                linear-gradient(
                                    180deg,
                                    #fff1a8,
                                    #d4af37,
                                    #8a6500
                                );

                            box-shadow:
                                2px 0 8px
                                rgba(212,175,55,.25);
                        "
                    ></div>


                    <div
                        style="
                            display:flex;
                            align-items:center;
                            gap:10px;
                        "
                    >

                        <!-- NÍVEL -->
                        <div
                            id="hud-status-level"
                            style="
                                min-width:48px;

                                padding:
                                    6px
                                    7px;

                                border-radius:9px;

                                background:
                                    linear-gradient(
                                        180deg,
                                        #ffe58b,
                                        #d9a923
                                    );

                                color:#1d1605;

                                border:
                                    1px solid
                                    #fff1a8;

                                box-shadow:
                                    0 3px 8px
                                    rgba(0,0,0,.45),

                                    0 0 12px
                                    rgba(212,175,55,.16);

                                font-family:
                                    'Cinzel',
                                    serif;

                                font-size:11px;

                                font-weight:900;

                                text-align:center;

                                white-space:nowrap;

                                text-shadow:
                                    0 1px
                                    rgba(255,255,255,.3);
                            "
                        >
                            NV. 1
                        </div>


                        <!-- NOME / CLASSE -->
                        <div
                            style="
                                min-width:0;
                                flex:1;
                            "
                        >

                            <div
                                id="hud-status-nome"
                                style="
                                    color:#fde68a;

                                    font-family:
                                        'Cinzel',
                                        serif;

                                    font-size:15px;

                                    font-weight:900;

                                    line-height:1.1;

                                    letter-spacing:.5px;

                                    text-transform:uppercase;

                                    overflow:hidden;
                                    text-overflow:ellipsis;
                                    white-space:nowrap;

                                    text-shadow:
                                        0 2px 3px
                                        rgba(0,0,0,.9),

                                        0 0 10px
                                        rgba(250,204,21,.14);
                                "
                            >
                                HERÓI
                            </div>


                            <div
                                id="hud-status-classe"
                                style="
                                    margin-top:4px;

                                    color:#7dd3fc;

                                    font-size:9px;

                                    font-weight:800;

                                    letter-spacing:1px;

                                    text-transform:uppercase;
                                "
                            >
                                AVENTUREIRO
                            </div>

                        </div>

                    </div>


                    <!-- FECHAR -->

                    <button
                        onclick="
                            window.toggleMenuStatus(false)
                        "
                        style="
                            position:absolute;

                            top:10px;
                            right:10px;

                            width:26px;
                            height:26px;

                            padding:0;

                            border:
                                1px solid
                                rgba(239,68,68,.28);

                            border-radius:7px;

                            background:
                                rgba(127,29,29,.18);

                            color:#fb7185;

                            font-size:17px;

                            font-weight:900;

                            cursor:pointer;

                            line-height:23px;
                        "
                    >
                        ×
                    </button>

                </div>


                <!-- ====================================== -->
                <!-- 📊 CORPO -->
                <!-- ====================================== -->

                <div
                    style="
                        padding:
                            14px
                            14px
                            16px;
                    "
                >

                    <!-- ❤️ HP -->

                    <div
                        style="
                            margin-bottom:11px;
                        "
                    >

                        <div
                            style="
                                display:flex;
                                justify-content:
                                    space-between;
                                align-items:center;

                                margin-bottom:4px;

                                font-size:10px;
                                font-weight:900;
                            "
                        >

                            <span
                                style="
                                    color:#fb7185;
                                    letter-spacing:.6px;
                                "
                            >
                                ❤️ HP
                            </span>

                            <span
                                id="hud-txt-hp"
                                style="
                                    color:#fecaca;
                                "
                            >
                                0/0
                            </span>

                        </div>


                        <div
                            style="
                                width:100%;
                                height:8px;

                                background:#020617;

                                border:
                                    1px solid
                                    #1e293b;

                                border-radius:
                                    999px;

                                overflow:hidden;

                                box-shadow:
                                    inset 0 2px 4px
                                    rgba(0,0,0,.7);
                            "
                        >

                            <div
                                id="hud-bar-hp"
                                style="
                                    width:0%;
                                    height:100%;

                                    background:
                                        linear-gradient(
                                            90deg,
                                            #dc2626,
                                            #fb7185
                                        );

                                    border-radius:
                                        999px;

                                    box-shadow:
                                        0 0 7px
                                        rgba(239,68,68,.45);

                                    transition:
                                        width .3s;
                                "
                            ></div>

                        </div>

                    </div>


                    <!-- 💧 MP -->

                    <div
                        style="
                            margin-bottom:11px;
                        "
                    >

                        <div
                            style="
                                display:flex;
                                justify-content:
                                    space-between;
                                align-items:center;

                                margin-bottom:4px;

                                font-size:10px;
                                font-weight:900;
                            "
                        >

                            <span
                                style="
                                    color:#38bdf8;
                                    letter-spacing:.6px;
                                "
                            >
                                💧 MP
                            </span>

                            <span
                                id="hud-txt-mp"
                                style="
                                    color:#bae6fd;
                                "
                            >
                                0/0
                            </span>

                        </div>


                        <div
                            style="
                                width:100%;
                                height:8px;

                                background:#020617;

                                border:
                                    1px solid
                                    #1e293b;

                                border-radius:
                                    999px;

                                overflow:hidden;

                                box-shadow:
                                    inset 0 2px 4px
                                    rgba(0,0,0,.7);
                            "
                        >

                            <div
                                id="hud-bar-mp"
                                style="
                                    width:0%;
                                    height:100%;

                                    background:
                                        linear-gradient(
                                            90deg,
                                            #0369a1,
                                            #38bdf8
                                        );

                                    border-radius:
                                        999px;

                                    box-shadow:
                                        0 0 7px
                                        rgba(56,189,248,.4);

                                    transition:
                                        width .3s;
                                "
                            ></div>

                        </div>

                    </div>


                    <!-- ✨ XP -->

                    <div
                        style="
                            margin-bottom:16px;
                        "
                    >

                        <div
                            style="
                                display:flex;
                                justify-content:
                                    space-between;
                                align-items:center;

                                margin-bottom:4px;

                                font-size:10px;
                                font-weight:900;
                            "
                        >

                            <span
                                style="
                                    color:#c084fc;
                                    letter-spacing:.6px;
                                "
                            >
                                ✨ XP
                            </span>

                            <span
                                id="hud-txt-xp"
                                style="
                                    color:#e9d5ff;
                                "
                            >
                                0/0
                            </span>

                        </div>


                        <div
                            style="
                                width:100%;
                                height:6px;

                                background:#020617;

                                border:
                                    1px solid
                                    #1e293b;

                                border-radius:
                                    999px;

                                overflow:hidden;
                            "
                        >

                            <div
                                id="hud-bar-xp"
                                style="
                                    width:0%;
                                    height:100%;

                                    background:
                                        linear-gradient(
                                            90deg,
                                            #7e22ce,
                                            #c084fc
                                        );

                                    border-radius:
                                        999px;

                                    box-shadow:
                                        0 0 7px
                                        rgba(192,132,252,.38);

                                    transition:
                                        width .3s;
                                "
                            ></div>

                        </div>

                    </div>


                    <!-- ====================================== -->
                    <!-- 🧪 CONSUMÍVEIS -->
                    <!-- ====================================== -->

                    <div
                        style="
                            color:#94a3b8;

                            font-size:9px;

                            text-align:center;

                            margin-bottom:9px;

                            font-weight:900;

                            text-transform:
                                uppercase;

                            letter-spacing:1.2px;
                        "
                    >
                        Consumíveis rápidos
                    </div>


                    <div
                        style="
                            display:flex;

                            gap:18px;

                            justify-content:
                                center;

                            margin-bottom:17px;
                        "
                    >

                        <!-- HP -->

                        <div
                            onclick="
                                if(
                                    window.usarPocaoRapida
                                ) {
                                    window.usarPocaoRapida(
                                        'hp'
                                    );
                                }
                            "

                            title="
                                Usar Poção de Vida
                            "

                            class="hud-slot"

                            style="
                                position:relative;

                                width:50px;
                                height:50px;

                                background:
                                    radial-gradient(
                                        circle at 50% 35%,
                                        rgba(127,29,29,.30),
                                        rgba(4,10,20,.96)
                                    );

                                border:
                                    2px solid
                                    #ef4444;

                                border-radius:11px;

                                display:flex;

                                justify-content:center;
                                align-items:center;

                                cursor:pointer;

                                box-shadow:
                                    inset 0 0 14px
                                    rgba(239,68,68,.16),

                                    0 5px 10px
                                    rgba(0,0,0,.45);

                                transition:
                                    transform .1s;
                            "

                            onmousedown="
                                this.style.transform=
                                'scale(.92)'
                            "

                            onmouseup="
                                this.style.transform=
                                'scale(1)'
                            "

                            onmouseleave="
                                this.style.transform=
                                'scale(1)'
                            "
                        >

                            <img
                                id="hud-img-pocao-hp"

                                src=""

                                style="
                                    display:none;

                                    max-width:80%;
                                    max-height:80%;

                                    filter:
                                        drop-shadow(
                                            0 3px 4px
                                            rgba(0,0,0,.9)
                                        );
                                "
                            >


                            <span
                                style="
                                    display:inline;

                                    font-size:1.3em;
                                "
                            >
                                ❤️
                            </span>


                            <div
                                id="hud-qtd-pocao-hp"

                                style="
                                    display:none;

                                    position:absolute;

                                    right:-7px;
                                    bottom:-7px;

                                    min-width:24px;
                                    height:19px;

                                    padding:
                                        0 4px;

                                    border-radius:
                                        999px;

                                    background:
                                        linear-gradient(
                                            180deg,
                                            #f43f5e,
                                            #b91c1c
                                        );

                                    border:
                                        2px solid
                                        #07111f;

                                    color:#fff;

                                    font-size:9px;

                                    font-weight:900;

                                    line-height:15px;

                                    text-align:center;

                                    box-shadow:
                                        0 3px 7px
                                        rgba(0,0,0,.75);

                                    z-index:5;
                                "
                            >
                                x0
                            </div>

                        </div>


                        <!-- MP -->

                        <div
                            onclick="
                                if(
                                    window.usarPocaoRapida
                                ) {
                                    window.usarPocaoRapida(
                                        'mp'
                                    );
                                }
                            "

                            title="
                                Usar Poção de Mana
                            "

                            class="hud-slot"

                            style="
                                position:relative;

                                width:50px;
                                height:50px;

                                background:
                                    radial-gradient(
                                        circle at 50% 35%,
                                        rgba(3,105,161,.30),
                                        rgba(4,10,20,.96)
                                    );

                                border:
                                    2px solid
                                    #38bdf8;

                                border-radius:11px;

                                display:flex;

                                justify-content:center;
                                align-items:center;

                                cursor:pointer;

                                box-shadow:
                                    inset 0 0 14px
                                    rgba(56,189,248,.16),

                                    0 5px 10px
                                    rgba(0,0,0,.45);

                                transition:
                                    transform .1s;
                            "

                            onmousedown="
                                this.style.transform=
                                'scale(.92)'
                            "

                            onmouseup="
                                this.style.transform=
                                'scale(1)'
                            "

                            onmouseleave="
                                this.style.transform=
                                'scale(1)'
                            "
                        >

                            <img
                                id="hud-img-pocao-mp"

                                src=""

                                style="
                                    display:none;

                                    max-width:80%;
                                    max-height:80%;

                                    filter:
                                        drop-shadow(
                                            0 3px 4px
                                            rgba(0,0,0,.9)
                                        );
                                "
                            >


                            <span
                                style="
                                    display:inline;

                                    font-size:1.3em;
                                "
                            >
                                💧
                            </span>


                            <div
                                id="hud-qtd-pocao-mp"

                                style="
                                    display:none;

                                    position:absolute;

                                    right:-7px;
                                    bottom:-7px;

                                    min-width:24px;
                                    height:19px;

                                    padding:
                                        0 4px;

                                    border-radius:
                                        999px;

                                    background:
                                        linear-gradient(
                                            180deg,
                                            #38bdf8,
                                            #0369a1
                                        );

                                    border:
                                        2px solid
                                        #07111f;

                                    color:#fff;

                                    font-size:9px;

                                    font-weight:900;

                                    line-height:15px;

                                    text-align:center;

                                    box-shadow:
                                        0 3px 7px
                                        rgba(0,0,0,.75);

                                    z-index:5;
                                "
                            >
                                x0
                            </div>

                        </div>

                    </div>


                    <!-- ====================================== -->
                    <!-- 🛡️ EQUIPAMENTOS -->
                    <!-- ====================================== -->

                    <div
                        style="
                            display:flex;
                            align-items:center;
                            gap:8px;

                            margin-bottom:9px;
                        "
                    >

                        <div
                            style="
                                flex:1;
                                height:1px;
                                background:
                                    linear-gradient(
                                        90deg,
                                        transparent,
                                        #334155
                                    );
                            "
                        ></div>


                        <div
                            style="
                                color:#94a3b8;

                                font-size:9px;

                                font-weight:900;

                                text-transform:
                                    uppercase;

                                letter-spacing:1.2px;
                            "
                        >
                            Equipamentos
                        </div>


                        <div
                            style="
                                flex:1;
                                height:1px;
                                background:
                                    linear-gradient(
                                        90deg,
                                        #334155,
                                        transparent
                                    );
                            "
                        ></div>

                    </div>


                    <div
                        id="hud-equips-grid"

                        style="
                            display:grid;

                            grid-template-columns:
                                repeat(4, 1fr);

                            gap:6px;
                        "
                    ></div>

                </div>

            </div>

        </div>
    `;


    document.body.insertAdjacentHTML(
        'beforeend',
        htmlMenu
    );


    // ======================================================
    // 🛡️ BLOQUEIA EVENTOS DO PAINEL
    // ======================================================

    const overlay =
        document.getElementById(
            'hud-status-overlay'
        );

    const painel =
        document.getElementById(
            'hud-status-flutuante'
        );


    const bloquearEventoPainel = (
        evento
    ) => {

        evento.stopPropagation();
    };


    [
        'pointerdown',
        'pointerup',
        'mousedown',
        'mouseup',
        'touchstart',
        'touchend',
        'click'
    ].forEach(
        nomeEvento => {

            painel.addEventListener(
                nomeEvento,
                bloquearEventoPainel,
                {
                    passive:false
                }
            );
        }
    );


    // ======================================================
    // 👆 CLICOU FORA = FECHA
    //
    // Importante:
    // fecha o menu mas NÃO movimenta o personagem.
    // ======================================================

    overlay.addEventListener(
        'pointerdown',
        (
            evento
        ) => {

            if (
                evento.target !==
                overlay
            ) {
                return;
            }


            evento.preventDefault();
            evento.stopPropagation();


            window.toggleMenuStatus(
                false
            );
        },
        {
            passive:false
        }
    );
};
// Executa a injeção assim que o script carregar
window.injetarMenuStatusFlutuante();

// Atualiza o HUD Circular (Anéis de HP, MP e XP)
// Atualiza o HUD Circular (Anéis de HP, MP e XP)
window.atualizarHudCircular = async function() {
    const charId = localStorage.getItem("jogadorEldoraID");
    if (!charId) return;

    try {
        // 👇 CORREÇÃO 1: Puxando da mesma rota confiável do Menu Flutuante (/perfil/)
        const res = await fetch(`/perfil/${charId}?t=${new Date().getTime()}`);
        const p = await res.json();
        if (!p || p.erro) return;

        // 1. 🔥 O TRADUTOR DO AVATAR NO HUD 🔥
        const imgElement = document.getElementById('hud-img-avatar');
        if (imgElement) {
            let avatarCaminho = p.avatar_customizado;
            if (typeof avatarCaminho === 'object' && avatarCaminho !== null) avatarCaminho = avatarCaminho.path;
            
            let imagemFinal = 'https://raw.githubusercontent.com/Eldorabotpy/static-img/main/assets/avatares/avatar_padrao_m.png';
            
            if (avatarCaminho && avatarCaminho !== 'padrao' && avatarCaminho !== '') {
                if (window.CATALOGO_SISTEMA && window.CATALOGO_SISTEMA.avatares[avatarCaminho]) {
                    imagemFinal = window.CATALOGO_SISTEMA.avatares[avatarCaminho].path;
                } else if (avatarCaminho.startsWith('http')) {
                    imagemFinal = avatarCaminho;
                } else {
                    // 👇 A CORREÇÃO DO 404: Monta o link do GitHub se for apenas o ID da classe (ex: guerreiro_m)
                    let nomePuro = avatarCaminho;
                    if (!nomePuro.startsWith('avatar_')) nomePuro = `avatar_${nomePuro}`;
                    imagemFinal = `https://raw.githubusercontent.com/Eldorabotpy/static-img/main/assets/avatares/${nomePuro}.png`;
                }
            } else if (p.avatar && p.avatar !== '') {
                imagemFinal = p.avatar;
            }

            // Só atualiza se a imagem for realmente diferente para não piscar
            if (!imgElement.src.includes(imagemFinal)) {
                imgElement.src = imagemFinal;
                imgElement.onerror = function() { this.src = 'https://raw.githubusercontent.com/Eldorabotpy/static-img/main/assets/avatares/avatar_padrao_m.png'; };
            }
        }

        // 2. 👇 CORREÇÃO 2: Usando as variáveis exatas do /perfil/ para ficar 100% igual
        let valHp = p.hp_atual !== undefined ? p.hp_atual : 0;
        let maxHp = p.hp_max !== undefined ? p.hp_max : 100;
        
        let valMp = p.mp_atual !== undefined ? p.mp_atual : 0;
        let maxMp = p.mp_max !== undefined ? p.mp_max : 50;
        
        let valXp = p.xp !== undefined ? p.xp : 0;
        let maxXp = p.xp_max !== undefined ? p.xp_max : 100;

        let percHp = Math.min(1, Math.max(0, valHp / maxHp));
        let percMp = Math.min(1, Math.max(0, valMp / maxMp));
        let percXp = Math.min(1, Math.max(0, valXp / maxXp));
        
        // 3. Atualiza os Textos (Labels)
        if(document.getElementById('label-hp')) document.getElementById('label-hp').innerText = `HP: ${Math.round(percHp * 100)}%`;
        if(document.getElementById('label-mp')) document.getElementById('label-mp').innerText = `MP: ${Math.round(percMp * 100)}%`;
        if(document.getElementById('label-xp')) document.getElementById('label-xp').innerText = `XP: ${Math.round(percXp * 100)}%`;

        // 4. Animação dos Anéis SVG (strokeDashoffset)
        const barraHp = document.getElementById('barra-hp-css');
        const barraMp = document.getElementById('barra-mp-css');
        const barraXp = document.getElementById('barra-xp-css');
        
        if(barraHp) barraHp.style.strokeDashoffset = 390 - (390 * percHp * 0.95); 
        if(barraMp) barraMp.style.strokeDashoffset = 326 - (326 * percMp * 0.85); 
        if(barraXp) barraXp.style.strokeDashoffset = 465 - (465 * percXp * 1);

    } catch (e) { 
        console.warn("Falha na sincronização do HUD Circular:", e); 
    }
};

// Gerencia o Menu Flutuante de Status
window.toggleMenuStatus = function(
    forcarEstado = null
) {

    if (
        !document.getElementById(
            'hud-status-flutuante'
        )
    ) {
        window.injetarMenuStatusFlutuante();
    }


    const hud =
        document.getElementById(
            'hud-status-flutuante'
        );

    const overlay =
        document.getElementById(
            'hud-status-overlay'
        );


    if (
        !hud ||
        !overlay
    ) {
        return;
    }


    const estaAberto =
        hud.style.display === 'block';


    const deveAbrir =
        forcarEstado === true
            ? true
            : forcarEstado === false
                ? false
                : !estaAberto;


    // ======================================================
    // ✅ ABRIR
    // ======================================================

    if (deveAbrir) {

        overlay.style.display =
            'block';

        hud.style.display =
            'block';


        // Trava extra usada pelo Phaser
        window.__painelStatusAberto =
            true;


        window.carregarDadosDoHUD();

        return;
    }


    // ======================================================
    // ❌ FECHAR
    // ======================================================

    hud.style.display =
        'none';

    overlay.style.display =
        'none';


    window.__painelStatusAberto =
        false;
};

function hudNormalizarIdItem(valor) {
    if (!valor) return "";

    let id = String(valor).trim();

    if (id.includes("/")) {
        id = id.split("/").pop();
    }

    id = id.split("?")[0];
    id = id.replace(".png", "");
    id = id.toLowerCase();
    id = id.normalize("NFD").replace(/[\u0300-\u036f]/g, "");
    id = id.replace(/\s+/g, "_");

    return id;
}

function hudMontarCandidatosImagemEquipamento(eq, slotNome) {
    if (!eq || eq.vazio) return [];

    // ✅ Usa o mesmo tradutor de imagem do perfil normal.
    // Ele já tenta work_, equipamentos, ferramentas, materiais e box.
    if (typeof window.getCaminhosImagemItemEldora === "function") {
        try {
            const caminhosPerfil = window.getCaminhosImagemItemEldora(eq) || [];
            if (caminhosPerfil.length) {
                return [...new Set(caminhosPerfil.filter(Boolean))];
            }
        } catch (e) {
            console.warn("HUD: falha ao usar getCaminhosImagemItemEldora:", e);
        }
    }

    const candidatos = [];

    const imagensDiretas = [
        eq.img,
        eq.image,
        eq.imagem,
        eq.icon,
        eq.icone,
        eq.sprite,
        eq.image_url,
        eq.img_url,
        eq.url,
        eq.path
    ].filter(Boolean);

    imagensDiretas.forEach(url => {
        url = String(url).trim();

        if (url.startsWith("http") || url.startsWith("/static/")) {
            candidatos.push(url);
        }
    });

    const idsPossiveis = [
        eq.base_id,
        eq.item_id,
        eq.uid,
        eq.id,
        eq.equipment_id,
        eq.slug,
        eq.key,
        eq.codigo
    ]
        .filter(Boolean)
        .map(hudNormalizarIdItem)
        .filter(Boolean);

    const linkBase = "https://raw.githubusercontent.com/Eldorabotpy/static-img/main/assets/";

    idsPossiveis.forEach(baseId => {
        candidatos.push(`${linkBase}itens/equipamentos/work_${baseId}.png?v=5`);
        candidatos.push(`${linkBase}itens/equipamentos/${baseId}.png?v=5`);
        candidatos.push(`${linkBase}itens/ferramentas/work_${baseId}.png?v=5`);
        candidatos.push(`${linkBase}itens/ferramentas/${baseId}.png?v=5`);
        candidatos.push(`${linkBase}itens/materiais/${baseId}.png?v=5`);
    });

    candidatos.push("/static/assets/box.png");

    return [...new Set(candidatos)];
}

window.hudTentarProximaImagemEquipamento = function(img) {
    try {
        const raw = img.getAttribute("data-fallbacks") || "[]";
        const lista = JSON.parse(decodeURIComponent(raw));

        if (lista.length > 0) {
            const proxima = lista.shift();
            img.setAttribute("data-fallbacks", encodeURIComponent(JSON.stringify(lista)));
            img.src = proxima;
            return;
        }
    } catch (e) {
        console.warn("Falha ao tentar fallback de imagem do equipamento:", e);
    }

    img.style.display = "none";

    const fallback = img.nextElementSibling;
    if (fallback) {
        fallback.style.display = "flex";
    }
};

function hudRenderImagemEquipamento(eq, slotNome, quebrado, temDurabilidade) {
    const candidatos = hudMontarCandidatosImagemEquipamento(eq, slotNome);

    if (!candidatos.length) {
        return `
            <div style="
                display:flex;
                width:100%;
                height:100%;
                align-items:center;
                justify-content:center;
                color:#64748b;
                font-size:9px;
                font-weight:900;
                text-align:center;
                padding:2px;
            ">${String(slotNome || "").toUpperCase()}</div>
        `;
    }

    const primeira = candidatos[0];
    const restantes = candidatos.slice(1);

    return `
        <img
            src="${primeira}"
            data-fallbacks="${encodeURIComponent(JSON.stringify(restantes))}"
            onerror="window.hudTentarProximaImagemEquipamento(this)"
            style="
                max-width:82%;
                max-height:82%;
                object-fit:contain;
                margin-bottom:${temDurabilidade ? '6px' : '0'};
                filter:${quebrado ? 'grayscale(100%) brightness(.55)' : 'drop-shadow(0 2px 2px rgba(0,0,0,.8))'};
            "
        >

        <div style="
            display:none;
            width:100%;
            height:100%;
            align-items:center;
            justify-content:center;
            color:#64748b;
            font-size:9px;
            font-weight:900;
            text-align:center;
            padding:2px;
        ">${String(slotNome || "").toUpperCase()}</div>
    `;
}

function hudNumeroSeguro(valor) {
    if (valor === null || valor === undefined) return null;

    if (typeof valor === "number") {
        return Number.isFinite(valor) ? valor : null;
    }

    const txt = String(valor).trim();

    if (!txt) return null;

    // Aceita formatos tipo "20/35", "20 de 35", "Dur: 20"
    const match = txt.match(/-?\d+/);

    if (!match) return null;

    const n = Number(match[0]);

    return Number.isFinite(n) ? n : null;
}

function hudNumeroSeguro(valor) {
    if (valor === null || valor === undefined) return null;

    if (typeof valor === "number") {
        return Number.isFinite(valor) ? valor : null;
    }

    const txt = String(valor).trim();
    if (!txt) return null;

    const match = txt.match(/-?\d+/);
    if (!match) return null;

    const n = Number(match[0]);
    return Number.isFinite(n) ? n : null;
}

function hudLerDurabilidade(eq) {
    if (!eq) return null;

    // ✅ Formato real usado pelo combate/backend:
    // durability: [atual, max]
    const arraysPossiveis = [
        eq.durability,
        eq.durabilidade,
        eq.durability_array,
        eq.durabilidade_array
    ];

    for (const raw of arraysPossiveis) {
        if (Array.isArray(raw) && raw.length >= 2) {
            const atualArr = hudNumeroSeguro(raw[0]);
            const maxArr = hudNumeroSeguro(raw[1]);

            if (atualArr !== null && maxArr !== null) {
                return {
                    atual: Math.max(0, atualArr),
                    max: Math.max(1, maxArr)
                };
            }
        }

        if (raw && typeof raw === "object" && !Array.isArray(raw)) {
            const atualObj = hudNumeroSeguro(
                raw.current ??
                raw.cur ??
                raw.atual ??
                raw.value
            );

            const maxObj = hudNumeroSeguro(
                raw.max ??
                raw.mx ??
                raw.maximo ??
                raw.maximum
            );

            if (atualObj !== null) {
                return {
                    atual: Math.max(0, atualObj),
                    max: Math.max(1, maxObj ?? atualObj ?? 1)
                };
            }
        }

        // ✅ Formato texto: "20/20"
        if (typeof raw === "string" && raw.includes("/")) {
            const partes = raw.split("/");
            const atualTxt = hudNumeroSeguro(partes[0]);
            const maxTxt = hudNumeroSeguro(partes[1]);

            if (atualTxt !== null) {
                return {
                    atual: Math.max(0, atualTxt),
                    max: Math.max(1, maxTxt ?? atualTxt ?? 1)
                };
            }
        }
    }

    // ✅ Campos separados
    const brutoAtual =
        eq.durabilidade_atual ??
        eq.current_durability ??
        eq.currentDurability ??
        eq.dur_atual ??
        eq.dur ??
        null;

    if (brutoAtual === null || brutoAtual === undefined) return null;

    const atual = hudNumeroSeguro(brutoAtual);
    if (atual === null) return null;

    const brutoMax =
        eq.durabilidade_max ??
        eq.max_durability ??
        eq.maxDurability ??
        eq.durability_max ??
        eq.dur_max ??
        eq.max_dur ??
        null;

    const maxLido = hudNumeroSeguro(brutoMax);

    // ✅ Se o backend só mandou "20" sem max, não inventa 100.
    // Mostra como 20/20 para não ficar barra vermelha falsa.
    return {
        atual: Math.max(0, atual),
        max: Math.max(1, maxLido ?? atual ?? 1)
    };
}

window.carregarDadosDoHUD = async function() {
    const charId = localStorage.getItem("jogadorEldoraID");
    if (!charId) return;
    try {
        const res = await fetch(`/perfil/${charId}?t=${new Date().getTime()}`);
        const p = await res.json();
        if (p.erro) return;
        
        // ==========================================================
        // 👑 CABEÇALHO DO HUD
        // ==========================================================

        const nomeHud =
            document.getElementById(
                'hud-status-nome'
            );

        const nivelHud =
            document.getElementById(
                'hud-status-level'
            );

        const classeHud =
            document.getElementById(
                'hud-status-classe'
            );

        if (nomeHud) {

            nomeHud.innerText =
                p.nome ||
                'Herói';
        }

        if (nivelHud) {

            nivelHud.innerText =
                `NV. ${p.level || 1}`;
        }

        if (classeHud) {

            let classeTexto =
                p.classe ||
                p.class ||
                'Aventureiro';

            classeTexto =
                String(
                    classeTexto
                )
                .replace(
                    /_/g,
                    ' '
                );

            classeHud.innerText =
                classeTexto;
        }
        
        // 🛡️ A TRAVA VISUAL AQUI: Garante que a vida e a mana exibidas nunca sejam maiores que o máximo!
        let hpSeguro = Math.min(p.hp_atual, p.hp_max);
        let mpSeguro = Math.min(p.mp_atual, p.mp_max);

        document.getElementById('hud-bar-hp').style.width = Math.min((hpSeguro / p.hp_max) * 100, 100) + '%';
        document.getElementById('hud-txt-hp').innerText = `HP: ${hpSeguro}/${p.hp_max}`;
        
        document.getElementById('hud-bar-mp').style.width = Math.min((mpSeguro / p.mp_max) * 100, 100) + '%';
        document.getElementById('hud-txt-mp').innerText = `MP: ${mpSeguro}/${p.mp_max}`;
        
        document.getElementById('hud-bar-xp').style.width = Math.min((p.xp / p.xp_max) * 100, 100) + '%';
        document.getElementById('hud-txt-xp').innerText = `XP: ${(p.xp||0).toLocaleString('pt-BR')} / ${(p.xp_max||1).toLocaleString('pt-BR')}`;

        const grid = document.getElementById('hud-equips-grid');
        let equipsHtml = '';

        const slots = [
            { id: 'arma', label: 'ARMA' },
            { id: 'armadura', label: 'ARM.' },
            { id: 'elmo', label: 'ELMO' },
            { id: 'botas', label: 'BOTA' },
            { id: 'colar', label: 'COL.' },
            { id: 'anel', label: 'ANEL' },
            { id: 'brinco', label: 'BRIN.' },
            { id: 'luvas', label: 'LUVA' }
        ];

        const equipamentosLista = Array.isArray(p.equipamentos) ? p.equipamentos : [];

        slots.forEach(slotInfo => {
            const slotNome = slotInfo.id;
            const eq = equipamentosLista.find(e => String(e.slot || "") === slotNome);

            if (eq && !eq.vazio) {
                const dur = hudLerDurabilidade(eq);
                let durabilidadeHtml = '';
                let quebrado = false;

                if (dur) {
                    const percDur = Math.max(0, Math.min(100, (dur.atual / dur.max) * 100));
                    quebrado = dur.atual <= 0;

                    const corDur = quebrado
                        ? '#ef4444'
                        : (percDur > 50 ? '#2ecc71' : (percDur > 20 ? '#f1c40f' : '#e74c3c'));

                    durabilidadeHtml = `
                        <div style="
                            position:absolute;
                            left:4px;
                            right:4px;
                            bottom:4px;
                            height:5px;
                            background:#020617;
                            border-radius:4px;
                            border:1px solid #111827;
                            overflow:hidden;
                        ">
                            <div style="
                                width:${percDur}%;
                                height:100%;
                                background:${corDur};
                                border-radius:4px;
                                transition:width .25s ease;
                            "></div>
                        </div>

                        <div style="
                            position:absolute;
                            right:3px;
                            top:3px;
                            min-width:16px;
                            height:14px;
                            padding:0 3px;
                            border-radius:5px;
                            background:${quebrado ? 'rgba(127,29,29,.95)' : 'rgba(2,6,23,.82)'};
                            border:1px solid ${quebrado ? '#ef4444' : '#475569'};
                            color:${quebrado ? '#fecaca' : '#cbd5e1'};
                            font-size:9px;
                            font-weight:900;
                            line-height:14px;
                            text-align:center;
                            box-shadow:0 2px 5px rgba(0,0,0,.65);
                        ">${dur.atual}</div>

                        ${quebrado ? `
                            <div style="
                                position:absolute;
                                inset:0;
                                display:flex;
                                align-items:center;
                                justify-content:center;
                                background:rgba(127,29,29,.35);
                                color:#fecaca;
                                font-size:9px;
                                font-weight:900;
                                text-shadow:1px 1px 2px #000;
                                pointer-events:none;
                            ">0 DUR</div>
                        ` : ''}
                    `;
                }

                equipsHtml += `
                    <div
                        class="hud-slot"
                        title="${eq.nome || eq.name || slotNome}${dur ? ` | Durabilidade: ${dur.atual}/${dur.max}` : ''}"
                        style="
                            position:relative;
                            overflow:hidden;
                            border:${quebrado ? '1px solid #ef4444' : '1px solid #334155'};
                            box-shadow:${quebrado ? '0 0 10px rgba(239,68,68,.55)' : 'inset 0 0 10px rgba(0,0,0,.65)'};
                            background:rgba(2,6,23,.85);
                        "
                    >
                        ${hudRenderImagemEquipamento(eq, slotNome, quebrado, !!dur)}

                        ${durabilidadeHtml}
                    </div>
                `;
            } else {
                equipsHtml += `
                    <div
                        class="hud-slot"
                        title="${slotInfo.label} vazio"
                        style="
                            opacity:.35;
                            background:rgba(0,0,0,.8);
                            color:#64748b;
                            font-size:9px;
                            font-weight:900;
                            display:flex;
                            align-items:center;
                            justify-content:center;
                            text-align:center;
                        "
                    >${slotInfo.label}</div>
                `;
            }
        });

        grid.innerHTML = equipsHtml;

        // ==========================================================
        // 🧪 POÇÕES EQUIPADAS + QUANTIDADE REAL NO INVENTÁRIO
        // ==========================================================
        try {

            const charId =
                localStorage.getItem("jogadorEldoraID");

            if (!charId) return;

            // ======================================================
            // 📡 BUSCA DADOS MAIS ATUAIS
            //
            // Essa rota traz:
            // - pocao_equipada_hp
            // - pocao_equipada_mp
            // - inventory
            // ======================================================

            const resPocao = await fetch(
                `/api/personagem/${charId}?t=${new Date().getTime()}`
            );

            const dataPocao =
                await resPocao.json();

            let hpId =
                dataPocao.pocao_equipada_hp ||
                p.pocao_equipada_hp;

            let mpId =
                dataPocao.pocao_equipada_mp ||
                p.pocao_equipada_mp;

            // ======================================================
            // 🛡️ NORMALIZA ID DA POÇÃO
            // ======================================================

            if (
                hpId &&
                typeof hpId === "object"
            ) {
                hpId =
                    hpId.base_id ||
                    hpId.item_id ||
                    hpId.id;
            }

            if (
                mpId &&
                typeof mpId === "object"
            ) {
                mpId =
                    mpId.base_id ||
                    mpId.item_id ||
                    mpId.id;
            }

            hpId = hpId ? String(hpId) : "";
            mpId = mpId ? String(mpId) : "";

            // ======================================================
            // 🎒 INVENTÁRIO
            // ======================================================

            const inventario =
                dataPocao.inventory ||
                p.inventory ||
                {};

            // ======================================================
            // 🔢 DESCOBRE QUANTIDADE DE UM ITEM
            //
            // Aceita os formatos usados no Eldora:
            //
            // "pocao": 5
            //
            // ou
            //
            // "pocao": {
            //     quantity: 5
            // }
            //
            // e também Array.
           // ======================================================

            function quantidadeItemInventario(itemId) {

                if (!itemId) {
                    return 0;
                }

                // --------------------------------------
                // INVENTÁRIO EM ARRAY
                // --------------------------------------

                if (Array.isArray(inventario)) {

                    const item =
                        inventario.find(i => {

                            if (!i) return false;

                            const idEncontrado =
                                i.base_id ||
                                i.item_id ||
                                i.id ||
                                "";

                            return (
                                String(idEncontrado) ===
                                String(itemId)
                            );
                        });

                    if (!item) {
                        return 0;
                    }

                    return Math.max(
                        0,
                        Number(
                            item.quantity ??
                            item.qtd ??
                            item.quantidade ??
                            item.amount ??
                            0
                        ) || 0
                    );
                }

                // --------------------------------------
                // INVENTÁRIO EM OBJETO
                // --------------------------------------

                if (
                    inventario &&
                    typeof inventario === "object"
                ) {

                    let item =
                        inventario[itemId];

                    // Procura também pelo base_id,
                    // caso a chave do inventário seja diferente.
                    if (item === undefined) {

                        for (
                            const [chave, valor]
                            of Object.entries(inventario)
                        ) {

                            if (
                                valor &&
                                typeof valor === "object"
                            ) {

                                const idEncontrado =
                                    valor.base_id ||
                                    valor.item_id ||
                                    valor.id ||
                                    chave;

                                if (
                                    String(idEncontrado) ===
                                    String(itemId)
                                ) {

                                    item = valor;
                                    break;
                                }
                            }
                        }
                    }

                    if (item === undefined) {
                        return 0;
                    }

                    // Formato:
                    // "pocao_cura": 5
                    if (
                        typeof item === "number" ||
                        typeof item === "string"
                    ) {

                        return Math.max(
                            0,
                            Number(item) || 0
                        );
                    }

                    // Formato:
                    // "pocao_cura": {"quantity": 5}
                    if (
                        item &&
                        typeof item === "object"
                    ) {

                        return Math.max(
                            0,
                            Number(
                                item.quantity ??
                                item.qtd ??
                                item.quantidade ??
                                item.amount ??
                                0
                            ) || 0
                        );
                    }
                }

                return 0;
            }

            const qtdHp =
                quantidadeItemInventario(hpId);

            const qtdMp =
                quantidadeItemInventario(mpId);

            // ======================================================
            // 🌐 IMAGENS
            // ======================================================

            const linkBaseNuvem =
                "https://raw.githubusercontent.com/Eldorabotpy/static-img/main/assets/itens/consumiveis/";

            const v =
                `?v=${new Date().getTime()}`;

            // ======================================================
            // ❤️ POÇÃO HP
            // ======================================================

            const imgHp =
                document.getElementById(
                    "hud-img-pocao-hp"
                );

            const qtdHpEl =
                document.getElementById(
                    "hud-qtd-pocao-hp"
                );

            if (imgHp) {

                if (
                    hpId &&
                    hpId !== "nenhuma"
                ) {

                    imgHp.onload = function() {
 
                        this.style.display =
                            "block";

                        if (
                            this.nextElementSibling
                        ) {
                            this.nextElementSibling
                                .style.display = "none";
                        }
                    };

                    imgHp.onerror = function() {

                        this.style.display =
                            "none";

                        if (
                            this.nextElementSibling
                        ) {
                            this.nextElementSibling
                                .style.display = "inline";
                        }
                    };

                    imgHp.src =
                        `${linkBaseNuvem}${hpId}.png${v}`;

                    if (qtdHpEl) {
  
                        qtdHpEl.innerText =
                            `x${qtdHp}`;

                        qtdHpEl.style.display =
                            "block";
                    }

                } else {

                    imgHp.style.display =
                        "none";

                    if (
                        imgHp.nextElementSibling
                    ) {
                        imgHp.nextElementSibling
                            .style.display = "inline";
                    }

                    if (qtdHpEl) {
                        qtdHpEl.style.display =
                            "none";
                    }
                }
            }

            // ======================================================
            // 💧 POÇÃO MP
            // ======================================================

            const imgMp =
                document.getElementById(
                    "hud-img-pocao-mp"
                );

            const qtdMpEl =
                document.getElementById(
                    "hud-qtd-pocao-mp"
                );

            if (imgMp) {

                if (
                    mpId &&
                    mpId !== "nenhuma"
                ) {

                    imgMp.onload = function() {

                        this.style.display =
                            "block";

                        if (
                            this.nextElementSibling
                        ) {
                            this.nextElementSibling
                                .style.display = "none";
                        }
                    };

                    imgMp.onerror = function() {

                        this.style.display =
                            "none";

                        if (
                            this.nextElementSibling
                        ) {
                            this.nextElementSibling
                                .style.display = "inline";
                        }
                    };

                    imgMp.src =
                        `${linkBaseNuvem}${mpId}.png${v}`;

                    if (qtdMpEl) {

                        qtdMpEl.innerText =
                            `x${qtdMp}`;

                        qtdMpEl.style.display =
                            "block";
                    }

                } else {

                    imgMp.style.display =
                        "none";

                    if (
                        imgMp.nextElementSibling
                    ) {
                        imgMp.nextElementSibling
                            .style.display = "inline";
                    }

                    if (qtdMpEl) {
                        qtdMpEl.style.display =
                            "none";
                    }
                }
            }

        } catch(e) {

            console.warn(
                "Erro ao atualizar poções do HUD:",
                e
            );
        }

    } catch (e) { 
        console.warn("Erro HUD Flutuante:", e); 
    }
}; // 👈 ESTA É A CHAVE QUE FECHA A window.atualizarHudCircular

// Inicia o loop de atualização a cada 2 segundos
setInterval(window.atualizarHudCircular, 2000);

// ==========================================
// BOTÃO SECRETO DE GM (SÓ APARECE PARA O ADMIN)
// ==========================================
setTimeout(() => {
    // 1. O seu ID numérico do Telegram
    const MEU_ID_ADMIN = 7262799478; 
    
    // 2. Tenta pegar a identidade direto do aplicativo do Telegram
    const meuTelegram = window.Telegram?.WebApp?.initDataUnsafe?.user?.id;

    // 3. Se for você no Telegram (ou se já tiver salvo no PC), ele libera!
    if (meuTelegram === MEU_ID_ADMIN || localStorage.getItem("souGM") === "sim") {
        if (!document.getElementById("btn-painel-gm")) {
            let btnGM = document.createElement("button");
            btnGM.id = "btn-painel-gm";
            btnGM.innerHTML = "👑GM";
            
            // Estilo do botão GM
            btnGM.style.cssText = `
                position: fixed; 
                bottom: 5px; 
                right: 10px; 
                background: linear-gradient(135deg, #f1c40f, #d35400); 
                color: white; 
                border: 2px solid #fff; 
                padding: 5px 5px; 
                border-radius: 8px; 
                z-index: 10; 
                font-family: 'Cinzel', serif;
                font-weight: bold; 
                cursor: pointer;
                box-shadow: 0 0 15px rgba(241, 196, 15, 0.6);
            `;

            // O clique mágico que dispensa aquele link enorme do Cloudflare
            btnGM.onclick = () => {
                window.location.href = "/admin/painel";
            };

            document.body.appendChild(btnGM);
            
            // Salva na memória para quando você for testar pelo navegador do PC
            localStorage.setItem("souGM", "sim"); 
        }
    }
}, 2000);


// ==========================================
// 📜 DIÁRIO DE AVENTURAS
// História + Missões da Guilda
// ==========================================

window.toggleDiarioQuests = async function() {

    const modal =
        document.getElementById(
            'modal-diario-quests'
        );

    const lista =
        document.getElementById(
            'lista-de-quests'
        );

    if (!modal || !lista) {

        console.warn(
            "Modal do diário não encontrado no HTML."
        );

        return;
    }


    // ==========================================
    // 🔴 ESCONDE NOTIFICAÇÃO
    // ==========================================

    const badge =
        document.getElementById(
            'quest-badge'
        );

    if (badge) {
        badge.style.display = 'none';
    }


    // ==========================================
    // ❌ SE JÁ ESTÁ ABERTO, FECHA
    // ==========================================

    if (
        modal.style.display !== 'none' &&
        modal.style.display !== ''
    ) {

        modal.style.display = 'none';

        return;
    }


    // ==========================================
    // 📖 ABRE O DIÁRIO
    // ==========================================

    modal.style.display = 'flex';


    lista.innerHTML = `
        <p style="
            color:#94a3b8;
            text-align:center;
            font-size:12px;
            padding:15px 0;
        ">
            📜 Consultando seu Diário...
        </p>
    `;


    // ==========================================
    // 🔧 PROTEÇÃO DE TEXTO
    // ==========================================

    const escaparHTML = (valor) => {

        return String(
            valor ?? ""
        )
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
    };


    let htmlHistoria = "";
    let htmlGuilda = "";
    let htmlGuildaCla = "";

    let temHistoria = false;
    let temGuilda = false;
    let temGuildaCla = false;

    // ========================================================
    // 📖 MISSÕES DE HISTÓRIA / CLASSE
    // ========================================================

    try {

        const p =
            window.perfilDadosGlobais || {};


        // Lista oficial para impedir
        // quests antigas/fantasmas no Diário.
        const missoesHistoriaOficiais = [

            "q0_boas_vindas",

            "q1_varek_recruta",

            "q2_varek_defesas",

            "q3_varek_provacao",

            "q4_selene_classe",

            "q5_thorek_profissao",

            "q6_selene_grimorio",

            "q7_selene_guildas"
        ];


        if (
            p.quests &&
            typeof p.quests === "object"
        ) {

            Object.entries(
                p.quests
            ).forEach(
                ([id, q]) => {

                    // ==================================
                    // FILTRO ANTI-FANTASMA
                    // ==================================

                    if (
                        !missoesHistoriaOficiais
                            .includes(id)
                    ) {
                        return;
                    }


                    if (!q) {
                        return;
                    }


                    // Missões antigas já resgatadas
                    // não aparecem mais.
                    if (
                        q.status ===
                        "resgatada"
                    ) {
                        return;
                    }


                    temHistoria = true;


                    const titulo =
                        escaparHTML(
                            q.titulo ||
                            "Missão"
                        );


                    const objetivo =
                        escaparHTML(
                            q.objetivo ||
                            q.desc ||
                            ""
                        );


                    const status =
                        escaparHTML(
                            String(
                                q.status ||
                                "em_andamento"
                            )
                            .replace(
                                /_/g,
                                " "
                            )
                        );


                    htmlHistoria += `
                        <div style="
                            background:
                                rgba(0,0,0,0.4);

                            border:
                                1px solid #334155;

                            padding:10px;

                            border-radius:8px;

                            margin-bottom:10px;

                            text-align:left;
                        ">

                            <strong style="
                                color:#facc15;

                                display:block;

                                font-size:0.9em;
                            ">
                                📖 ${titulo}
                            </strong>


                            <p style="
                                color:#cbd5e1;

                                font-size:0.8em;

                                margin:6px 0;

                                line-height:1.4;
                            ">
                                ${objetivo}
                            </p>


                            <span style="
                                color:#2ecc71;

                                font-size:0.7em;

                                font-weight:bold;

                                text-transform:uppercase;
                            ">
                                Status: ${status}
                            </span>

                        </div>
                    `;
                }
            );
        }

    } catch (erro) {

        console.warn(
            "📖 Erro ao montar missões de história:",
            erro
        );
    }


    // ========================================================
    // ⚔️ MISSÕES DA GUILDA
    // ========================================================

    try {

        const userId =
            localStorage.getItem(
                "jogadorEldoraID"
            );


        if (userId) {

            const resposta =
                await fetch(
                    `/api/guild/missoes/${encodeURIComponent(userId)}?t=${Date.now()}`,
                    {
                        method: "GET",
                        cache: "no-store"
                    }
                );


            const dados =
                await resposta.json();


            if (
                dados.success &&
                Array.isArray(
                    dados.ativas
                )
            ) {

                dados.ativas.forEach(
                    missao => {

                        if (!missao) {
                            return;
                        }


                        temGuilda = true;


                        // ==================================
                        // DADOS
                        // ==================================

                        const progresso =
                            Number(
                                missao.progresso ||
                                0
                            );


                        const total =
                            Math.max(
                                1,

                                Number(
                                    missao
                                        .progresso_total
                                    ||
                                    missao
                                        .objetivo
                                        ?.quantidade
                                    ||
                                    1
                                )
                            );


                        const percentual =
                            Math.max(
                                0,

                                Math.min(
                                    100,

                                    Math.round(
                                        (
                                            progresso /
                                            total
                                        ) * 100
                                    )
                                )
                            );


                        const pronta =
                            missao.status ===
                            "pronta_entrega";


                        // ==================================
                        // TIPO
                        // ==================================

                        const tipoTexto =
                            missao.tipo ===
                            "cla"

                            ? "🛡️ Clã"

                            : "👤 Pessoal";


                        // ==================================
                        // MODO
                        // ==================================

                        const modoTexto =
                            missao.modo ===
                            "grupo"

                            ? "👥 Grupo"

                            : "⚔️ Solo";


                        // ==================================
                        // TEXTOS
                        // ==================================

                        const nome =
                            escaparHTML(
                                missao.nome ||
                                "Contrato da Guilda"
                            );


                        const regiao =
                            escaparHTML(
                                missao.regiao_nome
                                ||
                                missao
                                    .objetivo
                                    ?.regiao
                                ||
                                "Eldora"
                            );


                        const objetivo =
                            escaparHTML(
                                missao
                                    .objetivo
                                    ?.texto
                                ||
                                missao.descricao
                                ||
                                ""
                            );


                        // ==================================
                        // CARTÃO
                        // ==================================

                        htmlGuilda += `
                            <div style="
                                background:
                                    linear-gradient(
                                        135deg,
                                        rgba(30,41,59,.96),
                                        rgba(10,16,29,.98)
                                    );

                                border:
                                    1px solid
                                    ${
                                        pronta
                                            ? "#d4af37"
                                            :
                                            (
                                                missao.tipo === "cla"
                                                    ? "#7c3aed"
                                                    : "#334155"
                                            )
                                    };

                                padding:10px;

                                border-radius:8px;

                                margin-bottom:10px;

                                text-align:left;

                                box-shadow:
                                    0 3px 8px
                                    rgba(0,0,0,.35);
                            ">


                                <!-- NOME -->

                                <strong style="
                                    color:#facc15;

                                    display:block;

                                    font-size:0.9em;
                                ">
                                    ⚔️ ${nome}
                                </strong>


                                <!-- TIPO / MODO -->

                                <div style="
                                    color:#94a3b8;

                                    font-size:0.68em;

                                    margin-top:5px;
                                ">

                                    ${tipoTexto}

                                    &nbsp;•&nbsp;

                                    ${modoTexto}

                                </div>


                                <!-- REGIÃO -->

                                <div style="
                                    color:#94a3b8;

                                    font-size:0.68em;

                                    margin-top:3px;
                                ">

                                    📍 ${regiao}

                                </div>


                                <!-- OBJETIVO -->

                                <p style="
                                    color:#cbd5e1;

                                    font-size:0.78em;

                                    margin:8px 0;

                                    line-height:1.4;
                                ">

                                    🎯 ${objetivo}

                                </p>


                                <!-- PROGRESSO -->

                                <div style="
                                    display:flex;

                                    justify-content:
                                        space-between;

                                    align-items:center;

                                    color:#e2e8f0;

                                    font-size:0.7em;

                                    margin-bottom:4px;
                                ">

                                    <span>
                                        Progresso
                                    </span>


                                    <strong style="
                                        color:#fde68a;
                                    ">

                                        ${progresso}/${total}

                                    </strong>

                                </div>


                                <!-- BARRA -->

                                <div style="
                                    width:100%;

                                    height:8px;

                                    background:#020617;

                                    border:
                                        1px solid
                                        #334155;

                                    border-radius:
                                        999px;

                                    overflow:hidden;
                                ">

                                    <div style="
                                        width:
                                            ${percentual}%;

                                        height:100%;

                                        background:
                                            linear-gradient(
                                                90deg,
                                                #a16207,
                                                #facc15
                                            );

                                        border-radius:
                                            999px;

                                        transition:
                                            width .25s ease;
                                    ">
                                    </div>

                                </div>


                                <!-- STATUS -->

                                ${
                                    pronta

                                    ? `

                                        <div style="
                                            margin-top:9px;

                                            padding:8px;

                                            border-radius:6px;

                                            background:
                                                rgba(
                                                    113,
                                                    63,
                                                    18,
                                                    .45
                                                );

                                            border:
                                                1px solid
                                                #d4af37;

                                            color:#fde68a;

                                            font-size:
                                                0.7em;

                                            text-align:center;

                                            line-height:1.45;
                                        ">

                                            ✅ OBJETIVO CONCLUÍDO

                                            <br><br>

                                            🏰 Volte à Guilda dos
                                            Aventureiros e fale com
                                            <strong>Lyria</strong>
                                            para receber sua recompensa.

                                        </div>

                                    `

                                    : `

                                        <div style="
                                            margin-top:7px;

                                            color:#2ecc71;

                                            font-size:0.68em;

                                            font-weight:bold;
                                        ">

                                            ⚔️ Missão em andamento

                                        </div>

                                    `
                                }

                            </div>
                        `;
                    }
                );
            }

        }

    } catch (erro) {

        console.warn(
            "⚔️ Erro ao carregar missões da Guilda:",
            erro
        );
    }

    // ========================================================
    // 🏰 MISSÕES COLETIVAS DO CLÃ
    // ========================================================

    try {

        const userIdCla =
            localStorage.getItem(
                "jogadorEldoraID"
            );


        if (userIdCla) {

            const respostaCla =
                await fetch(
                    `/api/guild/cla/missoes/${encodeURIComponent(userIdCla)}?t=${Date.now()}`,
                    {
                        method: "GET",
                        cache: "no-store"
                    }
                );


            const dadosCla =
                await respostaCla.json();


            // Jogador sem clã simplesmente
            // não terá missões coletivas no Diário.
            if (
                dadosCla.success &&
                Array.isArray(
                    dadosCla.ativas
                )
            ) {

                dadosCla.ativas.forEach(
                    missao => {
  
                        if (!missao) {
                            return;
                        }


                        temGuildaCla = true;


                        // ==================================
                        // PROGRESSO
                        // ==================================

                        const progresso =
                            Number(
                                missao.progresso ||
                                0
                            );


                        const total =
                            Math.max(
                                1,

                                Number(
                                    missao
                                        .progresso_total
                                    ||
                                    missao
                                        .objetivo
                                        ?.quantidade
                                    ||
                                    1
                                )
                            );


                        const percentual =
                            Math.max(
                                0,

                                Math.min(
                                    100,

                                    Math.round(
                                        (
                                            progresso /
                                            total
                                        ) * 100
                                    )
                                )
                            );


                        const pronta =
                            missao.status ===
                            "pronta_entrega";
 

                        // ==================================
                        // MODO
                        // ==================================
  
                        let modoTexto =
                            "⚔️ Solo";
 

                        if (
                            missao.modo ===
                            "grupo"
                        ) {

                            modoTexto =
                                "👥 Grupo";
                        }


                        else if (
                            missao.modo ===
                            "qualquer"
                        ) {

                            modoTexto =
                                "⚔️ Solo ou Grupo";
                        }


                        // ==================================
                        // FREQUÊNCIA
                        // ==================================

                        let frequenciaTexto =
                            "📜 Única";


                        if (
                            missao.frequencia ===
                            "diaria"
                        ) {

                            frequenciaTexto =
                                "☀️ Diária";
                        }


                        else if (
                            missao.frequencia ===
                            "semanal"
                        ) {

                            frequenciaTexto =
                                "🌙 Semanal";
                        }

 
                        // ==================================
                        // TEXTOS
                        // ==================================

                        const nome =
                            escaparHTML(
                                missao.nome ||
                                "Missão Coletiva"
                            );


                        const regiao =
                            escaparHTML(
                                missao.regiao_nome
                                ||
                                missao
                                    .objetivo
                                    ?.regiao
                                ||
                                "Eldora"
                            );


                        const objetivo =
                            escaparHTML(
                                missao
                                    .objetivo
                                    ?.texto
                                ||
                                missao.descricao
                                ||
                                ""
                            );


                        // ==================================
                        // RANKING
                        // ==================================
  
                        const ranking =
                            Array.isArray(
                                missao.ranking
                            )

                            ? missao.ranking
   
                            : [];


                        let rankingHtml =
                            "";


                        if (
                            ranking.length > 0
                        ) {
  
                            rankingHtml = `
  
                                <div style="
                                    margin-top:9px;
  
                                    padding-top:7px;

                                    border-top:
                                        1px solid
                                        #4c1d95;
                                ">

                                    <div style="
                                        color:#facc15;

                                        font-size:0.68em;

                                        font-weight:900;
 
                                        margin-bottom:5px;
                                    ">

                                        🏆 Contribuições
 
                                    </div>


                                    ${
                                        ranking
                                            .slice(0, 3)
                                            .map(
                                                (
                                                    membro,
                                                    indice
                                                ) => `

                                                    <div style="
                                                        display:flex;
    
                                                        justify-content:
                                                           space-between;

                                                        gap:8px;

                                                        color:#cbd5e1;

                                                        font-size:0.68em;

                                                        margin-top:3px;
                                                    ">

                                                        <span>
 
                                                            ${indice + 1}º
    
                                                            ${escaparHTML(
                                                                membro.nome ||
                                                                "Aventureiro"
                                                            )}
    
                                                        </span>
    
    
                                                        <strong style="
                                                            color:#fde68a;
                                                        ">
    
                                                            ${Number(
                                                                membro.quantidade ||
                                                                0
                                                            )}
    
                                                        </strong>
    
                                                    </div>
    
                                                `
                                            )
                                            .join("")
                                    }
    
                                </div>
                            `;
                        }
     
    
                        // ==================================
                        // CARTÃO COLETIVO
                        // ==================================
 
                        htmlGuildaCla += `

                            <div style="
                                background:
                                    linear-gradient(
                                        135deg,
                                        rgba(46,16,101,.38),
                                        rgba(10,16,29,.98)
                                    );

                                border:
                                    1px solid
                                    ${
                                        pronta
                                            ? "#d4af37"
                                            : "#7c3aed"
                                    };

                                padding:10px;
  
                                border-radius:8px;
  
                                margin-bottom:10px;
  
                                text-align:left;
 
                                box-shadow:
                                    0 3px 8px
                                    rgba(0,0,0,.35);
                            ">


                                <strong style="
                                    color:#facc15;
    
                                    display:block;
    
                                    font-size:0.9em;
                                ">

                                    🏰 ${nome}
 
                                </strong>


                                <div style="
                                    color:#c4b5fd;
  
                                    font-size:0.68em;
 
                                    margin-top:5px;
                                ">

                                    🏰 Coletiva

                                    &nbsp;•&nbsp;
  
                                    ${modoTexto}

                                    &nbsp;•&nbsp;

                                    ${frequenciaTexto}

                                </div>


                                <div style="
                                    color:#94a3b8;

                                    font-size:0.68em;

                                    margin-top:4px;
                                ">

                                    📍 ${regiao}

                                </div>


                                <p style="
                                    color:#cbd5e1;
  
                                    font-size:0.78em;
 
                                    margin:8px 0;

                                    line-height:1.4;
                                ">

                                    🎯 ${objetivo}

                                </p>


                                <div style="
                                    display:flex;

                                    justify-content:
                                        space-between;

                                    align-items:center;
 
                                    color:#e2e8f0;

                                    font-size:0.7em;

                                    margin-bottom:4px;
                                ">

                                    <span>
                                        Progresso do Clã
                                    </span>


                                    <strong style="
                                        color:#fde68a;
                                    ">

                                        ${progresso}/${total}

                                    </strong>

                                </div>


                                <div style="
                                    width:100%;

                                    height:8px;

                                    background:#020617;

                                    border:
                                        1px solid
                                        #334155;

                                    border-radius:999px;

                                    overflow:hidden;
                                ">

                                    <div style="
                                        width:${percentual}%;

                                        height:100%;

                                        background:
                                            linear-gradient(
                                                90deg,
                                                #7e22ce,
                                                #facc15
                                            );

                                        border-radius:999px;
                                    ">
                                    </div>

                                </div>


                                ${rankingHtml}


                                ${
                                    pronta
 
                                    ? `

                                        <div style="
                                            margin-top:9px;

                                            padding:8px;

                                            border-radius:6px;

                                            background:
                                                rgba(
                                                    113,
                                                    63,
                                                    18,
                                                .45
                                                );

                                            border:
                                                1px solid
                                                #d4af37;

                                            color:#fde68a;

                                            font-size:0.7em;
 
                                            text-align:center;

                                            line-height:1.45;
                                        ">

                                            ✅ MISSÃO DO CLÃ CONCLUÍDA

                                            <br><br>

                                            🏰 Volte à Guilda
                                            e fale com
                                            <strong>Lyria</strong>
                                            para registrar
                                            a recompensa.

                                        </div>

                                    `

                                    : `

                                        <div style="
                                            margin-top:7px;
 
                                            color:#c084fc;

                                            font-size:0.68em;

                                            font-weight:bold;
                                        ">

                                            🏰 Missão coletiva em andamento

                                        </div>

                                    `
                                }

                            </div>
                        `;
                    }
                );
            }

        }

    } catch (erro) {

        console.warn(
            "🏰 Erro ao carregar missões coletivas do clã:",
            erro
        );
    }

    // ========================================================
    // 📚 MONTA O DIÁRIO FINAL
    // ========================================================

    let htmlFinal = "";


    // ==========================================
    // 📖 HISTÓRIA
    // ==========================================

    if (temHistoria) {

        htmlFinal += `
            <div style="
                color:#60a5fa;

                font-size:0.72em;

                font-weight:900;

                margin:
                    4px
                    0
                    8px;

                text-align:left;

                border-bottom:
                    1px solid
                    #334155;

                padding-bottom:5px;

                letter-spacing:.5px;
            ">

                📖 JORNADA DE ELDORA

            </div>


            ${htmlHistoria}
        `;
    }


    // ==========================================
    // ⚔️ GUILDA
    // ==========================================

    if (temGuilda) {

        htmlFinal += `
            <div style="
                color:#f59e0b;

                font-size:0.72em;

                font-weight:900;

                margin:
                    ${
                        temHistoria
                            ? "16px"
                            : "4px"
                    }
                    0
                    8px;

                text-align:left;

                border-bottom:
                    1px solid
                    #4b3a10;

                padding-bottom:5px;

                letter-spacing:.5px;
            ">

                ⚔️ CONTRATOS DA GUILDA

            </div>


            ${htmlGuilda}
        `;
    }

    // ==========================================
    // 🏰 MISSÕES COLETIVAS DO CLÃ
    // ==========================================

    if (temGuildaCla) {

        htmlFinal += `
            <div style="
                color:#c084fc;

                font-size:0.72em;

                font-weight:900;

                margin:
                    ${
                        (
                            temHistoria ||
                            temGuilda
                        )
                            ? "16px"
                            : "4px"
                    }
                    0
                    8px;

                text-align:left;

                border-bottom:
                    1px solid
                    #4c1d95;

                padding-bottom:5px;

                letter-spacing:.5px;
            ">

                🏰 MISSÕES COLETIVAS DO CLÃ

            </div>


            ${htmlGuildaCla}
        `;
    }

    // ==========================================
    // NENHUMA MISSÃO
    // ==========================================

    if (
        !temHistoria &&
        !temGuilda &&
        !temGuildaCla
    ) {

        htmlFinal = `
            <p style="
                color:#64748b;

                text-align:center;

                line-height:1.5;

                padding:15px 5px;
            ">

                Todas as missões ativas
                foram concluídas!

            </p>
        `;
    }


    // ==========================================
    // MOSTRA
    // ==========================================

    lista.innerHTML =
        htmlFinal;
};