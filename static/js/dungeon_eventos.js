// /static/js/dungeon_eventos.js

(function () {

    "use strict";


    // ========================================================
    // 🖼️ TEXTURAS
    // ========================================================

    const TEXTURES = {

        amarelo: {

            off:
                "dungeon_pedra_amarela_off",

            on:
                "dungeon_pedra_amarela_on",
        },

        azul: {

            off:
                "dungeon_pedra_azul_off",

            on:
                "dungeon_pedra_azul_on",
        },

    };

    // ========================================================
    // 🔮 SÍMBOLOS DAS RUNAS
    // ========================================================

    const RUNE_INFO = {

        1: {
            emoji: "🌙",
            nome: "Lua",
        },

        2: {
            emoji: "🌊",
            nome: "Mar",
        },

        3: {
            emoji: "❄️",
            nome: "Gelo",
        },

        4: {
            emoji: "☀️",
            nome: "Sol",
        },

        5: {
            emoji: "👑",
            nome: "Ouro",
        },

        6: {
            emoji: "🔥",
            nome: "Chama",
        },

    };

    // ========================================================
    // 📦 PROPRIEDADES DO TILED
    // ========================================================

    function propsToObject(obj) {

        const out = {};

        const props =
            Array.isArray(obj?.properties)
                ? obj.properties
                : [];

        for (const p of props) {

            if (
                !p
                || !p.name
            ) {
                continue;
            }

            out[p.name] =
                p.value;
        }

        return out;
    }


    function objectClass(obj) {

        return String(
            obj?.class
            || obj?.type
            || ""
        ).trim();
    }


    // ========================================================
    // 🏰 MANAGER
    // ========================================================

    class DungeonEventManager {


        // ====================================================
        // 📥 PRELOAD
        // ====================================================

        static preload(scene) {

            if (
                !scene
                || scene.regiaoAtual
                !== "dungeon_01"
            ) {
                return;
            }


            const base =
                "/static/images/tilesets/";


            if (
                !scene.textures.exists(
                    "dungeon_pedra_amarela_off"
                )
            ) {

                scene.load.image(

                    "dungeon_pedra_amarela_off",

                    base
                    + "pedra_amarela_off.png"

                );

            }


            if (
                !scene.textures.exists(
                    "dungeon_pedra_amarela_on"
                )
            ) {

                scene.load.image(

                    "dungeon_pedra_amarela_on",

                    base
                    + "pedra_amarela_on.png"

                );

            }


            if (
                !scene.textures.exists(
                    "dungeon_pedra_azul_off"
                )
            ) {

                scene.load.image(

                    "dungeon_pedra_azul_off",

                    base
                    + "pedra_azul_off.png"

                );

            }


            if (
                !scene.textures.exists(
                    "dungeon_pedra_azul_on"
                )
            ) {

                scene.load.image(

                    "dungeon_pedra_azul_on",

                    base
                    + "pedra_azul_on.png"

                );

            }
            // ================================================
            // 📦 BAÚ 01 — FECHADO
            // ================================================

            if (
                !scene.textures.exists(
                    "dungeon_bau_01_fechado"
                )
            ) {

                scene.load.image(

                    "dungeon_bau_01_fechado",

                    base
                    + "bau_dungeon_01_fechado.png"

                );

            }


            // ================================================
            // 💰 BAÚ 01 — ABERTO
            // ================================================

            if (
                !scene.textures.exists(
                    "dungeon_bau_01_aberto"
                )
            ) {

                scene.load.image(

                    "dungeon_bau_01_aberto",

                    base
                    + "bau_dungeon_01_aberto.png"

                );

            }
            // ================================================
            // 👹 MÍMICO — ANIMAÇÃO DO BAÚ
            // ================================================

            if (
                !scene.textures.exists(
                    "dungeon_mimico_01_evento"
                )
            ) {

                scene.load.spritesheet(

                    "dungeon_mimico_01_evento",

                    "https://raw.githubusercontent.com/Eldorabotpy/static-img/main/assets/mob/mapa/dungeon_01/mimico_dungeon_01_spritesheet.png",

                    {
                        frameWidth: 128,
                        frameHeight: 128,
                    }

                );

            }            

        }


        // ====================================================
        // 🔧 CONSTRUTOR
        // ====================================================

        constructor(
            scene,
            map
        ) {

            this.scene =
                scene;

            this.map =
                map;

            this.dungeonId =
                String(
                    scene?.regiaoAtual
                    || ""
                );

            this.ativo =
                this.dungeonId
                === "dungeon_01";


            this.visuais =
                new Map();

            this.logicos =
                new Map();

            this.chests =
                new Map();

            this.chestVisuals =
                new Map();


            this.puzzleId =
                "bau_01";


            // Distância máxima para interação.
            this.interactionRadius =
                80;


            this.busy =
                false;


            this.estado =
                null;


            this.keyE =
                null;


            this._combatListener =
                null;
        }


        // ====================================================
        // 🚀 INICIAR
        // ====================================================

        async iniciar() {

            if (
                !this.ativo
            ) {
                return;
            }


            this._criarVisuais();

            this._criarInteracoes();

            this._instalarTeclaE();

            this._instalarRetornoCombate();


            await this.carregarEstado();
        }


        // ====================================================
        // 🧹 DESTRUIR
        // ====================================================

        destruir() {

            if (
                this._combatListener
            ) {

                document.removeEventListener(

                    "dungeonEventoCombateEncerrado",

                    this._combatListener

                );

            }


            this._combatListener =
                null;


            this.visuais.clear();

            this.logicos.clear();

            this.chests.clear();

            this.chestVisuals.clear();
        }


        // ====================================================
        // 🖼️ CRIAR VISUAIS
        // ====================================================

        _criarVisuais() {

            const layer =
                this.map.getObjectLayer(
                    "eventos_visuais"
                );


            if (
                !layer
                || !Array.isArray(
                    layer.objects
                )
            ) {

                console.warn(
                    "[DUNGEON EVENT] camada eventos_visuais não encontrada."
                );

                return;
            }


            for (
                const obj
                of layer.objects
            ) {

                const classe =
                    objectClass(
                        obj
                    );


                const props =
                    propsToObject(
                        obj
                    );


                // ============================================
                // 📦 VISUAL DO BAÚ
                // ============================================

                if (
                    classe
                    ===
                    "dungeon_chest_visual"
                ) {

                    const chestId =
                        String(

                            props.chest_id
                            || ""

                        );


                    const puzzle =
                        String(

                            props.puzzle
                            || chestId

                        );


                    if (
                        !chestId
                    ) {

                        console.warn(
                            "[DUNGEON EVENT] visual de baú sem chest_id:",
                            obj
                        );

                        continue;
                    }


                    const sprite =
                        this.scene.add
                            .image(

                                Number(
                                    obj.x
                                    || 0
                                ),

                                Number(
                                    obj.y
                                    || 0
                                ),

                                "dungeon_bau_01_fechado"

                            )

                            .setOrigin(
                                0,
                                1
                            )

                            .setDisplaySize(

                                Number(
                                    obj.width
                                    || 52
                                ),

                                Number(
                                    obj.height
                                    || 61
                                )

                            )

                            .setDepth(
                                9
                            );


                    this.chestVisuals.set(

                        chestId,

                        {

                            chestId,

                            puzzle,

                            sprite,

                            fechadoTexture:
                                "dungeon_bau_01_fechado",

                            abertoTexture:
                                "dungeon_bau_01_aberto",

                        }

                    );


                    continue;
                }


                // ============================================
                // 💡 VISUAL DAS PEDRAS
                // ============================================

                if (
                    classe
                    !==
                    "dungeon_light_visual"
                ) {
                    continue;
                }


                const lightId =
                    String(

                        props.light_id
                        || obj.name
                        || ""

                    );


                const cor =
                    String(

                        props.cor
                        || ""

                    ).toLowerCase();


                const indice =
                    Number(

                        props.indice
                        || 0

                    );


                if (
                    !lightId
                    || !TEXTURES[cor]
                    || !indice
                ) {

                    console.warn(
                        "[DUNGEON EVENT] visual inválido:",
                        obj
                    );

                    continue;
                }


                // Tile Object do Tiled.
                // Y corresponde à base.

                const sprite =
                    this.scene.add
                        .image(

                            Number(
                                obj.x
                                || 0
                            ),

                            Number(
                                obj.y
                                || 0
                            ),

                            TEXTURES[
                                cor
                            ].off

                        )

                        .setOrigin(
                            0,
                            1
                        )

                        .setDisplaySize(

                            Number(
                                obj.width
                                || 48
                            ),

                            Number(
                                obj.height
                                || 61
                            )

                        )

                        .setDepth(
                            8
                        );

                // ============================================
                // 🔮 SÍMBOLO DA RUNA ACIMA DA PEDRA
                // ============================================

                const runeInfo =
                    RUNE_INFO[
                        indice
                    ]
                    || null;


                let runeLabel =
                    null;


                if (
                    runeInfo
                ) {

                    runeLabel =
                        this.scene.add
                            .text(

                                Number(
                                    obj.x
                                    || 0
                                )
                                +
                                Number(
                                    obj.width
                                    || 48
                                )
                                / 2,

                                Number(
                                    obj.y
                                    || 0
                                )
                                -
                                Number(
                                    obj.height
                                    || 61
                                )
                                -
                                4,

                                runeInfo.emoji,

                                {

                                    fontSize:
                                        "18px",

                                    fontFamily:
                                        "Arial",

                                    stroke:
                                        "#000000",

                                    strokeThickness:
                                        3,

                                }

                            )

                            .setOrigin(
                                0.5,
                                1
                            )

                            .setDepth(
                                100
                            );

                }

                this.visuais.set(

                    lightId,

                    {

                        lightId,

                        indice,

                        cor,

                        puzzle:
                            String(

                                props.puzzle
                                || this.puzzleId

                            ),

                        sprite,

                        runeLabel,

                        offTexture:
                            TEXTURES[
                                cor
                            ].off,

                        onTexture:
                            TEXTURES[
                                cor
                            ].on,

                    }

                );

            }


            console.log(

                "[DUNGEON EVENT]",

                this.visuais.size,

                "visuais carregados."

            );

        }


        // ====================================================
        // 👆 INTERAÇÕES
        // ====================================================

        _criarInteracoes() {

            const layer =
                this.map.getObjectLayer(
                    "objetos_mapa"
                );


            if (
                !layer
                || !Array.isArray(
                    layer.objects
                )
            ) {

                console.warn(
                    "[DUNGEON EVENT] camada objetos_mapa não encontrada."
                );

                return;
            }


            for (
                const obj
                of layer.objects
            ) {

                const classe =
                    objectClass(
                        obj
                    );


                const props =
                    propsToObject(
                        obj
                    );


                // ============================================
                // 💡 PEDRA
                // ============================================

                if (
                    classe
                    ===
                    "dungeon_light"
                ) {

                    const lightId =
                        String(
                            obj.name
                            || ""
                        );


                    const indice =
                        Number(
                            props.indice
                            || 0
                        );


                    const puzzle =
                        String(
                            props.puzzle
                            || ""
                        );


                    if (
                        !lightId
                        || !indice
                        || !puzzle
                    ) {
                        continue;
                    }


                    const hitbox =
                        this.scene.add

                            .rectangle(

                                Number(
                                    obj.x
                                    || 0
                                )
                                +
                                Number(
                                    obj.width
                                    || 0
                                )
                                / 2,

                                Number(
                                    obj.y
                                    || 0
                                )
                                +
                                Number(
                                    obj.height
                                    || 0
                                )
                                / 2,

                                Math.max(

                                    24,

                                    Number(
                                        obj.width
                                        || 32
                                    )

                                ),

                                Math.max(

                                    32,

                                    Number(
                                        obj.height
                                        || 64
                                    )

                                ),

                                0xffffff,

                                0.001

                            )

                            .setDepth(
                                60
                            )

                            .setInteractive({

                                useHandCursor:
                                    true

                            });


                    hitbox.on(

                        "pointerdown",

                        (
                            pointer,
                            localX,
                            localY,
                            event
                        ) => {

                            if (
                                event?.stopPropagation
                            ) {
                                event.stopPropagation();
                            }


                            this.interagirComLuz(
                                lightId
                            );

                        }

                    );


                    this.logicos.set(

                        lightId,

                        {

                            obj,

                            hitbox,

                            indice,

                            puzzle,

                            x:
                                hitbox.x,

                            y:
                                hitbox.y,

                        }

                    );

                }


                // ============================================
                // 📦 BAÚ
                // ============================================

                if (
                    classe
                    ===
                    "dungeon_chest"
                ) {

                    const chestId =
                        String(
                            obj.name
                            || ""
                        );


                    const puzzle =
                        String(
                            props.puzzle
                            || ""
                        );


                    if (
                        !chestId
                        || !puzzle
                    ) {
                        continue;
                    }


                    const hitbox =
                        this.scene.add

                            .rectangle(

                                Number(
                                    obj.x
                                    || 0
                                )
                                +
                                Number(
                                    obj.width
                                    || 0
                                )
                                / 2,

                                Number(
                                    obj.y
                                    || 0
                                )
                                +
                                Number(
                                    obj.height
                                    || 0
                                )
                                / 2,

                                Math.max(

                                    32,

                                    Number(
                                        obj.width
                                        || 40
                                    )

                                ),

                                Math.max(

                                    40,

                                    Number(
                                        obj.height
                                        || 52
                                    )

                                ),

                                0xffd700,

                                0.001

                            )

                            .setDepth(
                                60
                            )

                            .setInteractive({

                                useHandCursor:
                                    true

                            });


                    hitbox.on(

                        "pointerdown",

                        (
                            pointer,
                            localX,
                            localY,
                            event
                        ) => {

                            if (
                                event?.stopPropagation
                            ) {
                                event.stopPropagation();
                            }


                            this.interagirComBau(
                                chestId
                            );

                        }

                    );


                    this.chests.set(

                        chestId,

                        {

                            obj,

                            hitbox,

                            puzzle,

                            lootId:
                                props.loot_id
                                || null,

                            mimicId:
                                props.mimico_id
                                || null,

                            x:
                                hitbox.x,

                            y:
                                hitbox.y,

                        }

                    );

                }

            }


            console.log(

                "[DUNGEON EVENT]",

                this.logicos.size,

                "pedras e",

                this.chests.size,

                "baús carregados."

            );

        }


        // ====================================================
        // ⌨️ TECLA E
        // ====================================================

        _instalarTeclaE() {

            if (
                !this.scene.input?.keyboard
            ) {
                return;
            }


            this.keyE =
                this.scene.input.keyboard.addKey(

                    Phaser.Input.Keyboard
                        .KeyCodes.E

                );


            this.keyE.on(

                "down",

                () => {

                    if (
                        window.combateAbertoBloqueandoMapa
                    ) {
                        return;
                    }


                    this.interagirMaisProximo();

                }

            );


            this.scene.events.once(

                "shutdown",

                () =>
                    this.destruir()

            );


            this.scene.events.once(

                "destroy",

                () =>
                    this.destruir()

            );

        }


        // ====================================================
        // ⚔️ RETORNO DO COMBATE
        // ====================================================

        _instalarRetornoCombate() {

            this._combatListener =
                async (
                    evt
                ) => {

                    const detail =
                        evt?.detail
                        || {};


                    if (

                        String(
                            detail.dungeon_id
                            || ""
                        )
                        !==
                        this.dungeonId

                        ||

                        String(
                            detail.puzzle_id
                            || ""
                        )
                        !==
                        this.puzzleId

                    ) {
                        return;
                    }


                    await this.carregarEstado();

                };


            document.addEventListener(

                "dungeonEventoCombateEncerrado",

                this._combatListener

            );

        }


        // ====================================================
        // 📏 DISTÂNCIA
        // ====================================================

        _distanciaAte(
            x,
            y
        ) {

            const player =
                this.scene.player;


            if (
                !player
            ) {
                return Infinity;
            }


            return Phaser.Math
                .Distance
                .Between(

                    Number(
                        player.x
                        || 0
                    ),

                    Number(
                        player.y
                        || 0
                    ),

                    Number(
                        x
                        || 0
                    ),

                    Number(
                        y
                        || 0
                    )

                );

        }


        _estaPerto(
            x,
            y
        ) {

            return (
                this._distanciaAte(
                    x,
                    y
                )
                <=
                this.interactionRadius
            );

        }


        // ====================================================
        // 💬 AVISO
        // ====================================================

        _aviso(
            titulo,
            mensagem,
            tipo = "aviso"
        ) {

            // ================================================
            // 🏰 ALERTA COMPLETO DO ELDORA
            // ================================================

            if (
                typeof window.alertaEldora
                === "function"
            ) {

                window.alertaEldora(

                    titulo,

                    mensagem,

                    tipo

                );

                return;
            }


            // ================================================
            // ⚠️ FALLBACK ANTIGO
            // ================================================

            if (
                typeof window.avisoEldora
                === "function"
            ) {

                window.avisoEldora(
                    `${titulo}: ${mensagem}`
                );

                return;
            }


            const player =
                this.scene.player;


            if (
                !player
            ) {
                return;
            }


            const txt =
                this.scene.add

                    .text(

                        player.x,

                        player.y - 45,

                        mensagem,

                        {

                            fontSize:
                                "12px",

                            fontFamily:
                                "Arial",

                            color:
                                "#ffffff",

                            stroke:
                                "#000000",

                            strokeThickness:
                                3,

                            align:
                                "center",

                            wordWrap: {

                                width:
                                    240

                            },

                        }

                    )

                    .setOrigin(
                        0.5,
                        1
                    )

                    .setDepth(
                        1000
                    );


            this.scene.tweens.add({

                targets:
                    txt,

                y:
                    txt.y - 20,

                alpha:
                    0,

                duration:
                    1800,

                onComplete:
                    () =>
                        txt.destroy(),

            });

        }

        // ====================================================
        // 💡 TEXTO FLUTUANTE DA PEDRA
        // ====================================================

        _mostrarStatusLuz(
            indice,
            ligada
        ) {

            indice =
                Number(
                    indice
                    || 0
                );


            let alvo =
                null;


            for (
                const data
                of this.logicos.values()
            ) {

                if (
                    Number(
                        data.indice
                    )
                    === indice
                ) {

                    alvo =
                        data;

                    break;
                }

            }


            if (
                !alvo
            ) {
                return;
            }


            const runeInfo =
                RUNE_INFO[
                    indice
                ]
                || {
                    emoji: "🔹",
                    nome: "Runa",
                };


            const texto =
                `${runeInfo.emoji} Luz ${indice} ${ligada ? "ON" : "OFF"}`;


            const txt =
                this.scene.add
                    .text(

                        alvo.x,

                        alvo.y - 30,

                        texto,

                        {

                            fontSize:
                                "13px",

                            fontFamily:
                                "Arial",

                            fontStyle:
                                "bold",

                            color:
                                "#ffffff",

                            stroke:
                                "#000000",

                            strokeThickness:
                                4,

                        }

                    )

                    .setOrigin(
                        0.5
                    )

                    .setDepth(
                        99999
                    );


            this.scene.tweens.add({

                targets:
                    txt,

                y:
                    txt.y - 35,

                alpha:
                    0,

                duration:
                    900,

                ease:
                    "Power2",

                onComplete:
                    () => {

                        if (
                            txt
                            && txt.active
                        ) {

                            txt.destroy();

                        }

                    },

            });

        }

        // ====================================================
        // 💡 TROCAR OFF / ON
        // ====================================================

        _setVisual(
            lightId,
            on
        ) {

            const visual =
                this.visuais.get(
                    String(
                        lightId
                    )
                );


            if (
                !visual?.sprite
            ) {
                return;
            }


            visual.sprite.setTexture(

                on
                    ? visual.onTexture
                    : visual.offTexture

            );

        }


        // ====================================================
        // 🔄 APLICAR ESTADO DO SERVIDOR
        // ====================================================

        aplicarEstado(
            estado
        ) {

            if (
                !estado
            ) {
                return;
            }


            this.estado =
                estado;


            const ativas =
                new Set(

                    (
                        estado.luzes_ativas
                        || []
                    ).map(
                        Number
                    )

                );


            for (
                const visual
                of this.visuais.values()
            ) {

                this._setVisual(

                    visual.lightId,

                    ativas.has(
                        Number(
                            visual.indice
                        )
                    )

                );

            }
            // ================================================
            // 📦 ESTADO VISUAL DOS BAÚS
            // ================================================

            const bauAberto =
                Boolean(
                    estado.bau_aberto
                );


            for (
                const visual
                of this.chestVisuals.values()
            ) {

                if (
                    !visual.sprite
                ) {
                    continue;
                }


                visual.sprite.setTexture(

                    bauAberto
                        ? visual.abertoTexture
                        : visual.fechadoTexture

                );

            }

        }


        // ====================================================
        // 🌐 CARREGAR ESTADO
        // ====================================================

        async carregarEstado() {

            if (
                !this.ativo
            ) {
                return;
            }


            const userId =
                localStorage.getItem(
                    "jogadorEldoraID"
                );


            if (
                !userId
            ) {
                return;
            }


            try {

                const params =
                    new URLSearchParams({

                        user_id:
                            userId,

                        dungeon_id:
                            this.dungeonId,

                        puzzle_id:
                            this.puzzleId,

                        _:
                            String(
                                Date.now()
                            ),

                    });


                const res =
                    await fetch(

                        "/api/dungeon/evento/status?"
                        +
                        params.toString()

                    );


                const data =
                    await res.json();


                if (
                    !res.ok
                    || !data.success
                ) {

                    throw new Error(

                        data.error
                        || "Falha ao carregar evento."

                    );

                }


                this.aplicarEstado(
                    data.estado
                );

            }

            catch (
                err
            ) {

                console.error(
                    "[DUNGEON EVENT] carregarEstado:",
                    err
                );

            }

        }


        // ====================================================
        // 🔎 INTERAÇÃO MAIS PRÓXIMA
        // ====================================================

        async interagirMaisProximo() {

            let best =
                null;


            for (
                const [
                    lightId,
                    data
                ]
                of
                this.logicos.entries()
            ) {

                const d =
                    this._distanciaAte(
                        data.x,
                        data.y
                    );


                if (
                    !best
                    || d < best.dist
                ) {

                    best = {

                        tipo:
                            "luz",

                        id:
                            lightId,

                        dist:
                            d,

                    };

                }

            }


            for (
                const [
                    chestId,
                    data
                ]
                of
                this.chests.entries()
            ) {

                const d =
                    this._distanciaAte(
                        data.x,
                        data.y
                    );


                if (
                    !best
                    || d < best.dist
                ) {

                    best = {

                        tipo:
                            "bau",

                        id:
                            chestId,

                        dist:
                            d,

                    };

                }

            }


            if (
                !best
                ||
                best.dist
                >
                this.interactionRadius
            ) {

                this._aviso(

                    "Interação",

                    "Aproxime-se de uma pedra ou do baú.",

                    "aviso"

                );

                return;
            }


            if (
                best.tipo
                === "luz"
            ) {

                await this.interagirComLuz(
                    best.id
                );

            }

            else {

                await this.interagirComBau(
                    best.id
                );

            }

        }


        // ====================================================
        // 💡 CLICAR NA PEDRA
        // ====================================================

        async interagirComLuz(
            lightId
        ) {

            if (
                this.busy
                ||
                window.combateAbertoBloqueandoMapa
            ) {
                return;
            }


            const data =
                this.logicos.get(
                    String(
                        lightId
                    )
                );


            if (
                !data
            ) {
                return;
            }


            if (
                !this._estaPerto(
                    data.x,
                    data.y
                )
            ) {

                this._aviso(

                    "Pedra Rúnica",

                    "Você precisa se aproximar da pedra.",

                    "aviso"

                );

                return;
            }


            this.busy =
                true;


            // Feedback imediato.
            this._setVisual(
                lightId,
                true
            );


            try {

                const result =
                    await this._post(

                        "/api/dungeon/evento/luz",

                        {

                            user_id:
                                localStorage.getItem(
                                    "jogadorEldoraID"
                                ),

                            dungeon_id:
                                this.dungeonId,

                            puzzle_id:
                                data.puzzle,

                            indice:
                                data.indice,

                        }

                    );


                this.aplicarEstado(
                    result.estado
                );


                await this._processarResultado(

                    result,

                    data.puzzle,

                    null,

                    data.indice

                );

            }

            catch (
                err
            ) {

                this.aplicarEstado(
                    this.estado
                );

                console.error(
                    "[DUNGEON EVENT] Erro ao interagir com pedra:",
                    err
                );

            }

            finally {

                this.busy =
                    false;

            }

        }


        // ====================================================
        // 📦 CLICAR NO BAÚ
        // ====================================================

        async interagirComBau(
            chestId
        ) {

            if (
                this.busy
                ||
                window.combateAbertoBloqueandoMapa
            ) {
                return;
            }


            const chest =
                this.chests.get(
                    String(
                        chestId
                    )
                );


            if (
                !chest
            ) {
                return;
            }


            if (
                !this._estaPerto(
                    chest.x,
                    chest.y
                )
            ) {

                this._aviso(

                    "Baú Misterioso",

                    "Você precisa se aproximar do baú.",

                    "aviso"

                );

                return;
            }


            this.busy =
                true;


            try {

                const result =
                    await this._post(

                        "/api/dungeon/evento/bau",

                        {

                            user_id:
                                localStorage.getItem(
                                    "jogadorEldoraID"
                                ),

                            dungeon_id:
                                this.dungeonId,

                            puzzle_id:
                                chest.puzzle,

                        },

                        true

                    );


                if (
                    result.estado
                ) {

                    this.aplicarEstado(
                        result.estado
                    );

                }


                await this._processarResultado(

                    result,

                    chest.puzzle,

                    chestId

                );

            }

            catch (
                err
            ) {

                console.error(
                    "[DUNGEON EVENT] ERRO AO CLICAR NO BAÚ:",
                    err
                );


                this._aviso(

                    "Baú Misterioso",

                    err?.message
                    ||
                    "Não foi possível interagir com o baú.",

                    "erro"

                );

            }

            finally {

                this.busy =
                    false;

            }

        }


        // ====================================================
        // 🌐 POST
        // ====================================================

        async _post(
            url,
            body,
            allow409 = false
        ) {

            const res =
                await fetch(

                    url,

                    {

                        method:
                            "POST",

                        headers: {

                            "Content-Type":
                                "application/json"

                        },

                        body:
                            JSON.stringify(
                                body
                            ),

                    }

                );


            const data =
                await res
                    .json()
                    .catch(
                        () => ({})
                    );


            if (
                !res.ok
                &&
                !(
                    allow409
                    &&
                    res.status
                    === 409
                )
            ) {

                throw new Error(

                    data.error
                    ||
                    data.mensagem
                    ||
                    `Erro HTTP ${res.status}`

                );

            }


            return data;
        }

        // ====================================================
        // 👹 ANIMAÇÃO: BAÚ → MÍMICO
        // ====================================================

        async _animarMimicoNoBau(
            chestId
        ) {

            const chest =
                this.chests.get(
                    String(
                        chestId
                        || ""
                    )
                );

            if (
                !chest
            ) {

                console.error(
                    "[DUNGEON EVENT] Baú não encontrado para animação:",
                    chestId
                );

                await new Promise(
                    resolve =>
                        setTimeout(
                            resolve,
                            1200
                        )
                );

                return;
            }


            const textureKey =
                "dungeon_mimico_01_evento";

            const animKey =
                "dungeon_mimico_01_transformar";


            if (
                !this.scene.textures.exists(
                    textureKey
                )
            ) {

                console.error(
                    "[DUNGEON EVENT] Textura do Mímico não foi carregada:",
                    textureKey
                );

                await new Promise(
                    resolve =>
                        setTimeout(
                            resolve,
                            1200
                        )
                );

                return;
            }


            // ================================================
            // 🔒 BLOQUEIA MOVIMENTO DURANTE A TRANSFORMAÇÃO
            // ================================================

            try {

                this.scene.player
                    ?.body
                    ?.stop();

            } catch (
                e
            ) {}


            // ================================================
            // 🎞️ CRIA A ANIMAÇÃO
            // ================================================

            if (
                !this.scene.anims.exists(
                    animKey
                )
            ) {

                this.scene.anims.create({

                    key:
                        animKey,

                    frames:
                        this.scene.anims
                            .generateFrameNumbers(

                                textureKey,

                                {
                                    start: 0,
                                    end: 11,
                                }

                            ),

                    frameRate:
                        7,

                    repeat:
                        0,

                });

            }


            // ================================================
            // 👹 COLOCA O MÍMICO SOBRE O BAÚ
            // ================================================

            const mimic =
                this.scene.add.sprite(

                    chest.x,

                    chest.y,

                    textureKey,

                    0

                )

                    .setOrigin(
                        0.5,
                        0.65
                    )

                    .setDepth(
                        99999
                    );


            // Ajusta para o tamanho visual da dungeon.
            mimic.setDisplaySize(
                96,
                96
            );


            // Pequeno aparecimento.
            mimic.setAlpha(
                0
            );

            this.scene.tweens.add({

                targets:
                    mimic,

                alpha:
                    1,

                duration:
                    180,

            });


            // ================================================
            // 📸 CÂMERA DÁ FOCO NA TRANSFORMAÇÃO
            // ================================================

            try {

                this.scene.cameras.main
                    .shake(
                        120,
                        0.002
                    );

            } catch (
                e
            ) {}


            // ================================================
            // ▶️ TOCA A ANIMAÇÃO
            // ================================================

            mimic.play(
                animKey
            );


            // ================================================
            // ⏱️ ESPERA A ANIMAÇÃO TERMINAR
            // ================================================

            await new Promise(
                resolve => {

                    let terminou =
                        false;


                    const finalizar =
                        () => {

                            if (
                                terminou
                            ) {
                                return;
                            }

                            terminou =
                                true;


                            // Mantém o último frame
                            // por um instante para o jogador ver.
                            this.scene.time.delayedCall(

                                450,

                                () => {

                                    if (
                                        mimic
                                        &&
                                        mimic.active
                                    ) {

                                        mimic.destroy();

                                    }

                                    resolve();

                                }

                            );

                        };


                    mimic.once(

                        Phaser.Animations.Events
                            .ANIMATION_COMPLETE,

                        () => {

                            try {

                                this.scene.cameras.main
                                    .shake(
                                        250,
                                        0.008
                                    );

                            } catch (
                                e
                            ) {}

                            finalizar();

                        }

                    );


                    // Segurança.
                    //
                    // Mesmo se Phaser não disparar
                    // ANIMATION_COMPLETE, o combate continua.
                    this.scene.time.delayedCall(

                        2600,

                        finalizar

                    );

                }
            );

        }

        // ====================================================
        // 🎮 RESULTADO
        // ====================================================

        async _processarResultado(
            result,
            puzzleId,
            chestId = null,
            lightIndex = null
        ) {

            if (
                !result
            ) {
                return;
            }


            const acao =
                String(
                    result.acao
                    || ""
                );


            // ================================================
            // 💡 PEDRA SELECIONADA
            // ================================================

            if (
                acao === "luz_selecionada"
                || acao === "luz_correta"
            ) {

                this._mostrarStatusLuz(

                    lightIndex,

                    true

                );

                return;
            }

                        // ================================================
            // 💡 PEDRA DESATIVADA
            // ================================================

            if (
                acao
                === "luz_desativada"
            ) {

                this._mostrarStatusLuz(

                    lightIndex,

                    false

                );

                return;
            }

            // ================================================
            // 🔮 TRÊS RUNAS ESCOLHIDAS
            // ================================================

            if (
                acao
                === "sequencia_pronta"
            ) {

                const ativa =
                    (
                        result.estado
                            ?.luzes_ativas
                        || []
                    )
                        .map(
                            Number
                        )
                        .includes(
                            Number(
                                lightIndex
                            )
                        );


                if (
                    ativa
                ) {

                    this._mostrarStatusLuz(

                        lightIndex,

                        true

                    );

                }

                return;
            }

            // ================================================
            // 💡 PEDRA JÁ ACESA
            // ================================================

            if (
                acao
                === "luz_ja_ativa"
            ) {

                this._mostrarStatusLuz(

                    lightIndex,

                    true

                );

                return;
            }


            // ================================================
            // 📜 CHARADA DO BAÚ
            // ================================================

            if (
                acao
                === "bau_charada"
            ) {

                const texto =
                    String(
                        result.charada
                        || "As runas permanecem silenciosas..."
                    );

                if (
                    typeof window.mostrarDialogoRPG
                    === "function"
                ) {

                    const textoLimpo =
                        texto
                            .replace(
                                /\n+/g,
                                " "
                            )
                            .replace(
                                /\s+/g,
                                " "
                            )
                            .trim();

                    window.mostrarDialogoRPG(

                        "🧰 Baú Ancestral",

                        textoLimpo

                    );

                } else {

                    this._aviso(

                        "O Sussurro do Baú",

                        texto,

                        "aviso"

                    );

                }

                return;
            }


            // ================================================
            // 👹 MÍMICO JÁ ESTÁ EM COMBATE
            // ================================================

            if (
                acao
                === "mimico_em_andamento"
            ) {

                this._aviso(

                    "Mímico",

                    result.mensagem
                    ||
                    "O Mímico já despertou.",

                    "aviso"

                );

                return;
            }


            // ================================================
            // 🔓 PUZZLE RESOLVIDO
            // ================================================

            if (
                acao
                === "puzzle_resolvido"
            ) {

                this._aviso(

                    "Enigma Resolvido",

                    result.mensagem
                    ||
                    "As três pedras permanecem acesas. O baú foi destravado!",

                    "sucesso"

                );

                return;
            }


            // ================================================
            // 🔒 PUZZLE JÁ RESOLVIDO / EVENTO CONCLUÍDO
            // ================================================

            if (
                acao === "puzzle_ja_resolvido"
                || acao === "evento_concluido"
                || acao === "bau_ja_aberto"
            ) {

                this._aviso(

                    "Baú Ancestral",

                    result.mensagem
                    ||
                    "Nada mais acontece.",

                    "aviso"

                );

                return;
            }


            // ================================================
            // 🎁 BAÚ ABERTO
            // ================================================

            if (
                acao
                === "bau_aberto"
            ) {

                const gold =
                    Number(
                        result.recompensas?.gold
                        || 0
                    );


                const itens =
                    result.recompensas?.items
                    || [];


                const partes =
                    [];


                if (
                    gold > 0
                ) {

                    partes.push(
                        `💰 ${gold} ouro`
                    );

                }


                if (
                    itens.length
                ) {

                    partes.push(

                        itens

                            .map(
                                i =>
                                    `📦 ${i.quantity}x ${i.nome || i.item_id}`
                            )

                            .join(
                                ", "
                            )

                    );

                }


                this._aviso(

                    "Tesouro Encontrado",

                    partes.length
                        ? partes.join(" • ")
                        : "O baú foi aberto.",

                    "sucesso"

                );


                if (
                    typeof window.carregarMeuPerfil
                    === "function"
                ) {

                    window.carregarMeuPerfil();

                }


                return;
            }


            // ================================================
            // ⚠️ LOOT AINDA NÃO DEFINIDO
            // ================================================

            if (
                acao
                === "loot_nao_configurado"
            ) {

                this._aviso(

                    "Baú Destravado",

                    result.mensagem
                    ||
                    "A recompensa ainda não foi configurada.",

                    "aviso"

                );

                return;
            }


            // ================================================
            // 👹 MÍMICO
            // ================================================

            if (

                result.invocar_mimico

                &&

                result.spawn_id

            ) {

                // Para auto caça.
                try {

                    this.scene.motorCacada
                        ?.pararAutoCacada(

                            "evento do mímico",

                            true

                        );

                }

                catch (
                    e
                ) {}


                const contexto = {

                    dungeon_id:
                        this.dungeonId,

                    puzzle_id:
                        String(
                            puzzleId
                            || this.puzzleId
                        ),

                    spawn_id:
                        String(
                            result.spawn_id
                        ),

                    monster_id:
                        result.monster_id
                        ||
                        "mimico_dungeon_01",

                };


                window.__eldoraDungeonEventCombat =
                    contexto;


                if (
                    typeof window.iniciarCacadaApp
                    !== "function"
                ) {

                    throw new Error(
                        "Sistema de combate não está disponível."
                    );

                }


                // ============================================
                // 👹 PRIMEIRO O BAÚ SE TRANSFORMA
                // ============================================

                await this._animarMimicoNoBau(
                    chestId
                );


                // ============================================
                // ⚔️ DEPOIS ABRE A BATALHA
                // ============================================

                await window.iniciarCacadaApp(

                    result.spawn_id,

                    {

                        eventoDungeon:
                            true,

                        dungeonEventoContexto:
                            contexto,

                    }

                );

            }

        }

    }


    // ========================================================
    // 🌐 EXPORT
    // ========================================================

    window.DungeonEventManager =
        DungeonEventManager;

})();