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

                if (
                    objectClass(obj)
                    !==
                    "dungeon_light_visual"
                ) {
                    continue;
                }


                const props =
                    propsToObject(
                        obj
                    );


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

            if (
                typeof window.avisoEldora
                === "function"
            ) {

                window.avisoEldora(

                    titulo,

                    mensagem,

                    tipo

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

                    data.puzzle

                );

            }

            catch (
                err
            ) {

                this.aplicarEstado(
                    this.estado
                );


                this._aviso(

                    "Pedra Rúnica",

                    err.message
                    ||
                    "Não foi possível ativar a pedra.",

                    "erro"

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

                    chest.puzzle

                );

            }

            catch (
                err
            ) {

                this._aviso(

                    "Baú Misterioso",

                    err.message
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
        // 🎮 RESULTADO
        // ====================================================

        async _processarResultado(
            result,
            puzzleId
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
            // ✅ PEDRA CORRETA
            // ================================================

            if (
                acao
                === "luz_correta"
            ) {

                this._aviso(

                    "Pedra Rúnica",

                    "A pedra começou a brilhar.",

                    "sucesso"

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

                    "As três pedras permanecem acesas. O baú foi destravado!",

                    "sucesso"

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
                                    `📦 ${i.quantity}x ${i.item_id}`
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

                this._aviso(

                    "Mímico!",

                    result.mensagem
                    ||
                    "O baú revelou sua verdadeira forma!",

                    "erro"

                );


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