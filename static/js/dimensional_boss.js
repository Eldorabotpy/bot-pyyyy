// static/js/dimensional_boss.js

(function () {
    window.eventoDimensionalAtual = null;
    const DIMENSIONAL_COMBATE_ASSETS_FIXO = {
        boss_combate: "https://raw.githubusercontent.com/Eldorabotpy/static-img/refs/heads/main/assets/mob/combate/fenda/Arauto%20do%20Vazio%20st.png",
        lacaio_guardiao_combate: "https://raw.githubusercontent.com/Eldorabotpy/static-img/refs/heads/main/assets/mob/combate/fenda/Guardi%C3%A3o%20da%20Fenda%20st.png",
        lacaio_sacerdote_combate: "https://raw.githubusercontent.com/Eldorabotpy/static-img/refs/heads/main/assets/mob/combate/fenda/Sacerdote%20da%20Fenda%20st.png"
    };

    const DIMENSIONAL_HEROI_FALLBACK = "https://raw.githubusercontent.com/Eldorabotpy/static-img/main/assets/classes_costa/aventureiro_m.png?v=3";
    window.dimensionalAlvoSelecionado = null;

    function dimensionalEscapeHtml(txt) {
        return String(txt ?? "")
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }

    function dimensionalPct(atual, max) {
        atual = Number(atual || 0);
        max = Number(max || 1);
        return Math.max(0, Math.min(100, max > 0 ? (atual / max) * 100 : 0));
    }
    
    function dimensionalMontarAnimacoesFallbackPelosLogs(evento) {
        const logs = Array.isArray(evento?.logs) ? evento.logs.slice(-8) : [];
        const animacoes = [];

        const meuId = getMeuCharId();
        const alvoAtual = dimensionalAlvoAtual(evento);

        logs.forEach(log => {
            const texto = String(log?.texto || "");
            const textoLower = texto.toLowerCase();

            if (!texto) return;

            // Herói causando dano
            if (
                textoLower.includes("causou") &&
                textoLower.includes("dano") &&
                !textoLower.includes("atacou")
            ) {
                const match = texto.match(/(?:causou|crítico de)\s+(\d+)/i);
                const dano = match ? Number(match[1]) : 0;

                animacoes.push({
                    ator_tipo: "jogador",
                    ator_id: meuId,
                    autor_id: meuId,
                    autor_nome: "Herói",
                    acao: "atacar",
                    alvo_tipo: "inimigo",
                    alvo_id: alvoAtual?.id || window.dimensionalAlvoSelecionado || "",
                    alvo_nome: alvoAtual?.nome || "Inimigo",
                    dano: dano,
                    critico: textoLower.includes("crítico") || textoLower.includes("critico"),
                    texto: texto,
                    is_inimigo: false
                });
            }

            // Inimigo atacando jogador
            if (
                textoLower.includes("atacou") &&
                textoLower.includes("causou") &&
                textoLower.includes("dano")
            ) {
                const match = texto.match(/causou\s+(\d+)\s+de dano/i);
                const dano = match ? Number(match[1]) : 0;

                const inimigo = inimigosComoLista(evento).find(i => {
                    const nome = String(i.nome || i.name || "").toLowerCase();
                    return nome && textoLower.includes(nome.toLowerCase());
                });

                animacoes.push({
                    ator_tipo: "inimigo",
                    ator_id: inimigo?.id || window.dimensionalAlvoSelecionado || "",
                    autor_id: inimigo?.id || "",
                    autor_nome: inimigo?.nome || "Inimigo",
                    acao: "ataque_inimigo",
                    alvo_tipo: "jogador",
                    alvo_id: meuId,
                    alvo_nome: "Herói",
                    dano: dano,
                    critico: false,
                    texto: texto,
                    is_inimigo: true
                });
            }

            // Sacerdote curando
            if (
                textoLower.includes("curou") &&
                textoLower.includes("hp")
            ) {
                const match = texto.match(/em\s+(\d+)\s+de HP/i);
                const cura = match ? Number(match[1]) : 0;

                const sacerdote = inimigosComoLista(evento).find(i =>
                    String(i.nome || "").toLowerCase().includes("sacerdote")
                );

                animacoes.push({
                    ator_tipo: "inimigo",
                    ator_id: sacerdote?.id || "",
                    autor_id: sacerdote?.id || "",
                    autor_nome: sacerdote?.nome || "Sacerdote",
                    acao: "cura_inimigo",
                    alvo_tipo: "inimigo",
                    alvo_id: sacerdote?.id || "",
                    alvo_nome: "Aliado",
                    cura: cura,
                    dano: 0,
                    critico: false,
                    texto: texto,
                    is_inimigo: true
                });
            }
        });

        return animacoes.slice(-5);
    }

    function dimensionalDanoDoLog(log) {
        if (log.dano !== undefined && log.dano !== null) {
            return Math.max(0, Number(log.dano) || 0);
        }

        const texto = String(log.texto || "");
        const match = texto.match(/(?:causou|dano|crítico|critico)\D*(\d+)/i);

        return match ? Number(match[1]) : 0;
    }

    function dimensionalAnimarNumero(alvoId, valor, critico = false) {
        const alvo = document.getElementById(alvoId);
        const container = alvo ? alvo.parentElement : null;

        if (!alvo || !container || !valor) return;

        const num = document.createElement("div");
        num.innerText = valor;

        num.style.cssText = `
            position:absolute;
            z-index:99999;
            pointer-events:none;
            font-family:'Cinzel', Impact, sans-serif;
            font-weight:900;
            font-size:${critico ? "30px" : "23px"};
            color:${critico ? "#facc15" : "#ffffff"};
            text-shadow:2px 2px 0 #000, -2px -2px 0 #000, 0 6px 12px rgba(0,0,0,.9);
        `;

        const a = alvo.getBoundingClientRect();
        const c = container.getBoundingClientRect();

        num.style.left = `${a.left - c.left + a.width / 2}px`;
        num.style.top = `${a.top - c.top + a.height / 2}px`;

        container.appendChild(num);

        num.animate(
            [
                { transform: "translate(-50%, -50%) scale(.4)", opacity: 0 },
                { transform: "translate(-50%, -80%) scale(1.25)", opacity: 1 },
                { transform: "translate(-50%, -155%) scale(1)", opacity: 0 }
            ],
            {
                duration: critico ? 1000 : 850,
                easing: "cubic-bezier(.2,1,.3,1)",
                fill: "forwards"
            }
        );

        setTimeout(() => {
            try { num.remove(); } catch (e) {}
        }, critico ? 1050 : 900);
    }

    function dimensionalTremerSprite(alvoId) {
        const el = document.getElementById(alvoId);
        if (!el) return;

        const baseTransform = alvoId === "dimensional-sprite-inimigo" ? "scaleX(-1)" : "translate(0,0)";

        el.animate(
            [
                { transform: `${baseTransform} translate(0,0)` },
                { transform: `${baseTransform} translate(-8px,4px)` },
                { transform: `${baseTransform} translate(8px,-4px)` },
                { transform: `${baseTransform} translate(0,0)` }
            ],
            { duration: 280 }
        );

        el.animate(
            [
                { filter: "brightness(1)" },
                { filter: "brightness(2.4) saturate(2)" },
                { filter: "brightness(1)" }
            ],
            { duration: 280 }
        );
    }

    function dimensionalAnimarInvestida(atacanteId) {
        const el = document.getElementById(atacanteId);
        if (!el) return;

        if (atacanteId === "dimensional-sprite-heroi") {
            el.animate(
                [
                    { transform: "translate(0,0) scale(1)" },
                    { transform: "translate(58px,-24px) scale(1.08)" },
                    { transform: "translate(0,0) scale(1)" }
                ],
                { duration: 520, easing: "cubic-bezier(.2,1,.3,1)" }
            );
        } else {
            el.animate(
                [
                    { transform: "scaleX(-1) translate(0,0)" },
                    { transform: "scaleX(-1) translate(48px,-16px)" },
                    { transform: "scaleX(-1) translate(0,0)" }
                ],
                { duration: 520, easing: "cubic-bezier(.2,1,.3,1)" }
            );
        }
    }

        const DIMENSIONAL_URL_EFEITOS_SKILLS = "https://raw.githubusercontent.com/Eldorabotpy/static-img/refs/heads/main/assets/efeitos/";

    const DIMENSIONAL_CONFIG_EFEITOS_SKILLS = {
        default: {
            frameWidth: 128,
            frameHeight: 128,
            frameRate: 14,
            scale: 1.5,
            maxFrames: 16
        },

        // Ajustes conhecidos. Se algum efeito ficar cortado,
        // adicionamos o nome dele aqui com o tamanho certo.
        corte_perfurante: {
            frameRate: 16,
            maxFrames: 12
        },        

        pilar_luz_sagrada: {
            frameWidth: 64,
            frameHeight: 64,
            frameRate: 14,
            scale: 2.35,
            maxFrames: 48
        },

        brilho_dourado_escudo: {
            frameWidth: 64,
            frameHeight: 64,
            frameRate: 14,
            scale: 2.1,
            maxFrames: 48
        }
    };

    function dimensionalNormalizarNomeEfeitoSkill(valor) {
        let nome = String(valor || "").trim();

        if (!nome) return "";

        if (nome.startsWith("http://") || nome.startsWith("https://")) {
            return nome;
        }

        nome = nome.split("/").pop();
        nome = nome.replace(".png", "");

        return nome;
    }

    function dimensionalUrlEfeitoSkill(valor) {
        const nome = dimensionalNormalizarNomeEfeitoSkill(valor);

        if (!nome) return "";

        if (nome.startsWith("http://") || nome.startsWith("https://")) {
            return nome;
        }

        return `${DIMENSIONAL_URL_EFEITOS_SKILLS}${encodeURIComponent(nome)}.png`;
    }

    function dimensionalConfigEfeitoSkill(nomeEfeito) {
        const nome = dimensionalNormalizarNomeEfeitoSkill(nomeEfeito);
        const configDireta = DIMENSIONAL_CONFIG_EFEITOS_SKILLS[nome];

        return {
            ...(configDireta || DIMENSIONAL_CONFIG_EFEITOS_SKILLS.default || {}),
            _nomeEfeito: nome,
            _usouDefault: !configDireta
        };
    }

    function dimensionalDetectarFrameSpritesheetSkill(img, cfg = {}, log = {}) {
        const largura = Number(img.naturalWidth || img.width || 0);
        const altura = Number(img.naturalHeight || img.height || 0);

        const frameLogW = Number(log.anim_frame_width || log.frame_width || 0);
        const frameLogH = Number(log.anim_frame_height || log.frame_height || 0);

        // Se o backend mandar tamanho explícito, respeita.
        if (frameLogW > 0 && frameLogH > 0) {
            const colsLog = Math.max(1, Math.floor(largura / frameLogW));
            const rowsLog = Math.max(1, Math.floor(altura / frameLogH));

            return {
                frameW: frameLogW,
                frameH: frameLogH,
                cols: colsLog,
                rows: rowsLog,
                totalFrames: colsLog * rowsLog
            };
        }

        // Se alguma skill precisar travar manualmente, use autoDetect:false no config.
        if (
            cfg &&
            cfg.autoDetect === false &&
            Number(cfg.frameWidth || 0) > 0 &&
            Number(cfg.frameHeight || 0) > 0
        ) {
            const frameW = Number(cfg.frameWidth);
            const frameH = Number(cfg.frameHeight);
            const cols = Math.max(1, Math.floor(largura / frameW));
            const rows = Math.max(1, Math.floor(altura / frameH));

            return {
                frameW,
                frameH,
                cols,
                rows,
                totalFrames: cols * rows
            };
        }

        const tamanhosPossiveis = [256, 192, 160, 128, 96, 80, 64, 48, 32];

        let melhor = null;

        tamanhosPossiveis.forEach(tamanho => {
            if (largura % tamanho !== 0 || altura % tamanho !== 0) return;

            const cols = largura / tamanho;
            const rows = altura / tamanho;
            const total = cols * rows;

            if (cols < 1 || rows < 1) return;
            if (cols > 10 || rows > 10) return;
            if (total < 2 || total > 80) return;

            let score = 0;

            // Preferência para spritesheets comuns de efeitos.
            if (total >= 8 && total <= 16) score += 100;
            else if (total >= 6 && total <= 24) score += 80;
            else if (total >= 4 && total <= 32) score += 55;
            else score += 20;

            // Grades comuns.
            if (cols === 3 && rows === 4) score += 45; // 12 frames, igual corte_perfurante
            if (cols === 4 && rows === 4) score += 35; // 16 frames
            if (cols === 4 && rows === 2) score += 25; // 8 frames
            if (cols === 5 && rows === 4) score += 15; // 20 frames

            // Evita escolher frames minúsculos quando existe grade melhor.
            score += tamanho / 1000;

            if (!melhor || score > melhor.score) {
                melhor = {
                    frameW: tamanho,
                    frameH: tamanho,
                    cols,
                    rows,
                    totalFrames: total,
                    score
                };
            }
        });

        if (melhor) {
            return melhor;
        }

        // Fallback final.
        const fallback = Number(cfg.frameWidth || 64);

        return {
            frameW: fallback,
            frameH: Number(cfg.frameHeight || fallback),
            cols: Math.max(1, Math.floor(largura / fallback)),
            rows: Math.max(1, Math.floor(altura / fallback)),
            totalFrames: Math.max(1, Math.floor(largura / fallback) * Math.floor(altura / fallback))
        };
    }

    function dimensionalEscalaAutomaticaEfeitoSkill(cfg, frameW, frameH) {
        // Se alguma skill precisar escala manual, use autoScale:false no config.
        if (cfg && cfg.autoScale === false && Number(cfg.scale || 0) > 0) {
            return Number(cfg.scale);
        }

        const base = Math.max(Number(frameW || 64), Number(frameH || 64));

        if (base >= 256) return 0.9;
        if (base >= 192) return 1.1;
        if (base >= 160) return 1.25;
        if (base >= 128) return 1.45;
        if (base >= 96) return 1.75;

        return 2.15;
    }

    function dimensionalResolverEfeitoDaSkill(log) {
        let efeito =
            log.anim_effect ||
            log.animacao ||
            log.efeito ||
            "";

        if (efeito) return efeito;

        // Fallback: se por algum motivo o backend não mandar anim_effect,
        // tenta usar o ID da skill sem o prefixo da classe.
        let skillId = String(log.skill_id || "").trim();

        skillId = skillId
            .replace(/^guerreiro_/, "")
            .replace(/^mago_/, "")
            .replace(/^arqueiro_/, "")
            .replace(/^assassino_/, "")
            .replace(/^monge_/, "")
            .replace(/^bardo_/, "")
            .replace(/^berserker_/, "")
            .replace(/^samurai_/, "");

        return skillId || "corte_perfurante";
    }

    function dimensionalCentroDoElementoNoPalco(elementoId) {
        const palco = document.getElementById("dimensional-palco");
        const alvo = document.getElementById(elementoId);

        if (!palco || !alvo) return null;

        const rectPalco = palco.getBoundingClientRect();
        const rectAlvo = alvo.getBoundingClientRect();

        return {
            palco,
            x: rectAlvo.left - rectPalco.left + rectAlvo.width / 2,
            y: rectAlvo.top - rectPalco.top + rectAlvo.height / 2
        };
    }

    function dimensionalAnimarSpritesheetSkill(log, alvoElementoId = "dimensional-sprite-inimigo") {
        const nomeEfeito = dimensionalResolverEfeitoDaSkill(log);
        const url = dimensionalUrlEfeitoSkill(nomeEfeito);

        if (!url) return false;

        const centro = dimensionalCentroDoElementoNoPalco(alvoElementoId);

        if (!centro || !centro.palco) return false;

        const cfg = dimensionalConfigEfeitoSkill(nomeEfeito);

        const img = new Image();

        img.onload = function() {
            const detectado = dimensionalDetectarFrameSpritesheetSkill(img, cfg, log);

            const frameW = Number(detectado.frameW || 64);
            const frameH = Number(detectado.frameH || 64);
            const cols = Math.max(1, Number(detectado.cols || 1));
            const rows = Math.max(1, Number(detectado.rows || 1));

            let totalFrames = Math.max(1, Number(detectado.totalFrames || cols * rows));

            const limiteConfig = Number(cfg.maxFrames || 0);
            const limiteLog = Number(log.anim_frames || log.total_frames || 0);
            const limiteFinal = limiteLog || limiteConfig;

            if (limiteFinal > 0) {
                totalFrames = Math.min(totalFrames, limiteFinal);
            }

            const escalaFinal = dimensionalEscalaAutomaticaEfeitoSkill(cfg, frameW, frameH);

            console.log("✨ [DIMENSIONAL SKILL FRAME DETECTADO]", {
                efeito: nomeEfeito,
                imagem: `${img.naturalWidth}x${img.naturalHeight}`,
                frame: `${frameW}x${frameH}`,
                grade: `${cols}x${rows}`,
                totalFrames,
                escalaFinal
            });

            const efeito = document.createElement("div");

            efeito.className = "dimensional-skill-spritesheet";
            efeito.style.cssText = `
                position:absolute;
                left:${centro.x}px;
                top:${centro.y}px;
                width:${frameW}px;
                height:${frameH}px;
                z-index:99998;
                pointer-events:none;
                background-image:url("${url}");
                background-repeat:no-repeat;
                background-position:0 0;
                background-size:${img.naturalWidth}px ${img.naturalHeight}px;
                transform:translate(-50%, -50%) scale(${escalaFinal});
                transform-origin:center center;
                image-rendering:auto;
                filter:drop-shadow(0 0 12px rgba(124,58,237,.75));
            `;

            centro.palco.appendChild(efeito);

            let frame = 0;
            const delay = Math.max(25, Math.floor(1000 / Number(cfg.frameRate || 14)));

            const timer = setInterval(() => {
                const col = frame % cols;
                const row = Math.floor(frame / cols);

                efeito.style.backgroundPosition = `-${col * frameW}px -${row * frameH}px`;

                frame += 1;

                if (frame >= totalFrames) {
                    clearInterval(timer);

                    efeito.animate(
                        [
                            {
                                opacity: 1,
                                transform: `translate(-50%, -50%) scale(${escalaFinal})`
                            },
                            {
                                opacity: 0,
                                transform: `translate(-50%, -50%) scale(${escalaFinal * 1.12})`
                            }
                        ],
                        {
                            duration: 160,
                            easing: "ease-out",
                            fill: "forwards"
                        }
                    );

                    setTimeout(() => {
                        try { efeito.remove(); } catch (e) {}
                    }, 180);
                }
            }, delay);
        };

        img.onerror = function() {
            console.warn("❌ [DIMENSIONAL SKILL] Efeito não encontrado:", url, log);

            if (typeof animarEfeitoVisual === "function") {
                animarEfeitoVisual(alvoElementoId, "skill", "#8b5cf6");
            }
        };

        img.src = `${url}?v=2`;

        return true;
    }

    function dimensionalAnimarSkillProjetil(tipoEfeito = "skill") {
        const palco = document.getElementById("dimensional-palco");
        const heroi = document.getElementById("dimensional-sprite-heroi");
        const inimigo = document.getElementById("dimensional-sprite-inimigo");

        if (!palco || !heroi || !inimigo) return;

        const rectPalco = palco.getBoundingClientRect();
        const rectHeroi = heroi.getBoundingClientRect();
        const rectInimigo = inimigo.getBoundingClientRect();

        const startX = rectHeroi.left - rectPalco.left + rectHeroi.width * 0.72;
        const startY = rectHeroi.top - rectPalco.top + rectHeroi.height * 0.42;

        const endX = rectInimigo.left - rectPalco.left + rectInimigo.width * 0.48;
        const endY = rectInimigo.top - rectPalco.top + rectInimigo.height * 0.48;

        const orb = document.createElement("div");

        const tipo = String(tipoEfeito || "").toLowerCase();

        let cor1 = "#60a5fa";
        let cor2 = "#a78bfa";
        let simbolo = "✦";

        if (tipo.includes("fogo") || tipo.includes("fire")) {
            cor1 = "#f97316";
            cor2 = "#facc15";
            simbolo = "🔥";
        } else if (tipo.includes("cura") || tipo.includes("heal")) {
            cor1 = "#22c55e";
            cor2 = "#bbf7d0";
            simbolo = "✚";
        } else if (tipo.includes("corte") || tipo.includes("perfurante")) {
            cor1 = "#93c5fd";
            cor2 = "#e0f2fe";
            simbolo = "◈";
        } else if (tipo.includes("void") || tipo.includes("vazio") || tipo.includes("dark")) {
            cor1 = "#8b5cf6";
            cor2 = "#d946ef";
            simbolo = "✹";
        }

        orb.innerHTML = simbolo;
        orb.style.cssText = `
            position:absolute;
            left:${startX}px;
            top:${startY}px;
            width:34px;
            height:34px;
            z-index:99998;
            pointer-events:none;
            border-radius:999px;
            display:flex;
            align-items:center;
            justify-content:center;
            font-size:18px;
            font-weight:900;
            color:#ffffff;
            background:
                radial-gradient(circle, ${cor2} 0%, ${cor1} 45%, rgba(15,23,42,.05) 72%);
            box-shadow:
                0 0 12px ${cor1},
                0 0 26px ${cor2},
                0 0 42px rgba(124,58,237,.65);
            transform:translate(-50%, -50%) scale(.45);
            text-shadow:0 2px 4px #000;
        `;

        palco.appendChild(orb);

        orb.animate(
            [
                {
                    left: `${startX}px`,
                    top: `${startY}px`,
                    transform: "translate(-50%, -50%) scale(.45) rotate(0deg)",
                    opacity: 0
                },
                {
                    left: `${(startX + endX) / 2}px`,
                    top: `${Math.min(startY, endY) - 45}px`,
                    transform: "translate(-50%, -50%) scale(1.25) rotate(160deg)",
                    opacity: 1
                },
                {
                    left: `${endX}px`,
                    top: `${endY}px`,
                    transform: "translate(-50%, -50%) scale(.65) rotate(360deg)",
                    opacity: 0
                }
            ],
            {
                duration: 520,
                easing: "cubic-bezier(.2,.9,.2,1)",
                fill: "forwards"
            }
        );

        setTimeout(() => {
            try { orb.remove(); } catch (e) {}
        }, 560);

        const flash = document.createElement("div");
        flash.style.cssText = `
            position:absolute;
            left:${endX}px;
            top:${endY}px;
            width:80px;
            height:80px;
            z-index:99997;
            pointer-events:none;
            border-radius:999px;
            transform:translate(-50%, -50%) scale(.3);
            background:radial-gradient(circle, ${cor2} 0%, ${cor1} 35%, transparent 70%);
            box-shadow:0 0 22px ${cor1};
            opacity:.9;
        `;

        palco.appendChild(flash);

        flash.animate(
            [
                { transform: "translate(-50%, -50%) scale(.25)", opacity: .95 },
                { transform: "translate(-50%, -50%) scale(1.35)", opacity: 0 }
            ],
            {
                duration: 480,
                easing: "ease-out",
                fill: "forwards"
            }
        );

        setTimeout(() => {
            try { flash.remove(); } catch (e) {}
        }, 520);
    }
        
    function dimensionalLogPertoDoFim(box) {
        if (!box) return true;

        const distanciaDoFim = box.scrollHeight - box.scrollTop - box.clientHeight;

        return distanciaDoFim < 45;
    }

    function instalarControleScrollLogDimensional() {
        const box = document.getElementById("dimensional-log");

        if (!box || box.dataset.scrollDimensionalInstalado === "1") return;

        box.dataset.scrollDimensionalInstalado = "1";
        box.dataset.usuarioScrollManual = "0";

        box.addEventListener("scroll", () => {
            if (dimensionalLogPertoDoFim(box)) {
                box.dataset.usuarioScrollManual = "0";
            } else {
                box.dataset.usuarioScrollManual = "1";
            }
        });
    }

    function dimensionalAdicionarLogVisual(html) {
        const box = document.getElementById("dimensional-log");
        if (!box) return;

        instalarControleScrollLogDimensional();

        const deveIrParaFim =
            box.dataset.usuarioScrollManual !== "1" ||
            dimensionalLogPertoDoFim(box);

        const linha = document.createElement("div");
        linha.className = "dimensional-log-line";
        linha.innerHTML = html;

        linha.animate(
            [
                { opacity: 0, transform: "translateX(-6px)" },
                { opacity: 1, transform: "translateX(0)" }
            ],
            { duration: 180 }
        );

        box.appendChild(linha);

        if (deveIrParaFim) {
            box.scrollTop = box.scrollHeight;
        }
    }

    function dimensionalFormatarLogVisual(log) {
        const textoOriginal = dimensionalEscapeHtml(log.texto || "");
        const autor = dimensionalEscapeHtml(log.autor_nome || log.autor_id || "");
        const inimigo = !!log.is_inimigo;
        const dano = dimensionalDanoDoLog(log);
        const cura = Number(log.cura || 0);
        const critico = !!log.critico || String(log.texto || "").toLowerCase().includes("crítico");

        const ehSkill =
            log.acao === "magia" ||
            log.acao === "skill" ||
            log.acao === "skill_suporte" ||
            log.skill_id ||
            log.skill_nome ||
            log.anim_effect;

        let icone = "•";
        let titulo = "Sistema";
        let cor = "#94a3b8";
        let detalhe = textoOriginal;

        if (log.acao === "cura_inimigo") {
            icone = "✚";
            titulo = autor || "Sacerdote";
            cor = "#a78bfa";
            detalhe = `curou aliado${cura ? ` em <b style="color:#22c55e;">${cura} HP</b>` : ""}`;
        } else if (inimigo) {
            icone = "👹";
            titulo = autor || "Inimigo";
            cor = "#f87171";
            detalhe = `atacou${dano ? ` e causou <b style="color:#facc15;">${dano}</b> de dano` : ""}`;
        } else if (ehSkill) {
            icone = "✨";
            titulo = autor || "Herói";
            cor = "#a78bfa";
            detalhe = textoOriginal;
        } else if (log.acao === "ataque_basico" || log.acao === "atacar") {
            icone = "⚔️";
            titulo = autor || "Herói";
            cor = "#93c5fd";
            detalhe = textoOriginal;
        }

        return `
            <div style="
                display:flex;
                gap:7px;
                align-items:flex-start;
                padding:6px 7px;
                border:1px solid rgba(148,163,184,.14);
                border-left:3px solid ${cor};
                border-radius:9px;
                background:rgba(15,23,42,.62);
                box-shadow:0 2px 6px rgba(0,0,0,.25);
                margin-bottom:5px;
            ">
                <div style="
                    flex:0 0 auto;
                    width:22px;
                    height:22px;
                    border-radius:999px;
                    display:flex;
                    align-items:center;
                    justify-content:center;
                    background:rgba(2,6,23,.82);
                    border:1px solid ${cor};
                    font-size:12px;
                ">${icone}</div>

                <div style="min-width:0;flex:1;">
                    <div style="
                        color:${cor};
                        font-weight:900;
                        font-size:11px;
                        line-height:1.1;
                        font-family:'Cinzel', Arial, sans-serif;
                    ">${titulo}</div>

                    <div style="
                        color:#e2e8f0;
                        font-size:11px;
                        line-height:1.25;
                        margin-top:2px;
                    ">${detalhe}</div>
                </div>
            </div>
        `;
    }

    function dimensionalAnimarLogVisual(log) {
        const inimigo = !!log.is_inimigo;
        const dano = dimensionalDanoDoLog(log);
        const cura = Number(log.cura || 0);
        const critico = !!log.critico || String(log.texto || "").toLowerCase().includes("crítico");

        if (log.acao === "cura_inimigo") {
            const evento = window.eventoDimensionalAtual;
            const curador = inimigosComoLista(evento).find(i => String(i.id) === String(log.ator_id));

            if (curador) {
                dimensionalAplicarSpriteInimigo(evento, curador);
            }

            dimensionalAnimarSpritesheetSkill(
                {
                    ...log,
                    anim_effect: log.anim_effect || log.efeito || "pilar_luz_sagrada"
                },
                "dimensional-sprite-inimigo"
            );

            if (cura) {
                setTimeout(() => {
                    dimensionalAnimarNumero("dimensional-sprite-inimigo", `+${cura}`, false);
                }, 260);
            }

            if (window.AudioManager) {
                window.AudioManager.tocarSFX("som_cura");
            }

            return;
        }

        if (inimigo) {
            const evento = window.eventoDimensionalAtual;
            const atacante = inimigosComoLista(evento).find(i => String(i.id) === String(log.ator_id));

            if (atacante) {
                window.dimensionalAlvoSelecionado = atacante.id;
                dimensionalAplicarSpriteInimigo(evento, atacante);
            }

            if (window.AudioManager) {
                window.AudioManager.tocarSFX("som_monstro");
            }

            dimensionalAnimarInvestida("dimensional-sprite-inimigo");

            setTimeout(() => {
                dimensionalTremerSprite("dimensional-sprite-heroi");
                dimensionalAnimarNumero("dimensional-sprite-heroi", dano ? `-${dano}` : "", false);

                if (typeof animarEfeitoVisual === "function") {
                    animarEfeitoVisual("dimensional-sprite-heroi", "corte", "#9b59b6");
                }
            }, 240);

            return;
        }

        const ehSkillHeroi =
            log.acao === "magia" ||
            log.acao === "skill" ||
            log.acao === "skill_suporte" ||
            !!log.skill_id ||
            !!log.skill_nome ||
            !!log.anim_effect;

        if (ehSkillHeroi) {
            if (log.alvo_id) {
                window.dimensionalAlvoSelecionado = String(log.alvo_id);

                const alvoSkill = inimigosComoLista(window.eventoDimensionalAtual).find(i =>
                    String(i.id) === String(log.alvo_id)
                );

                if (alvoSkill) {
                    dimensionalAplicarSpriteInimigo(window.eventoDimensionalAtual, alvoSkill);
                }
            }

            if (window.AudioManager) {
                window.AudioManager.tocarSFX(critico ? "som_critico" : "som_magia");
            }

            if (log.acao === "skill_suporte") {
                dimensionalAnimarSpritesheetSkill(log, "dimensional-sprite-heroi");

                if (log.cura) {
                    setTimeout(() => {
                        dimensionalAnimarNumero("dimensional-sprite-heroi", `+${log.cura}`, false);
                    }, 260);
                }

                return;
            }

            dimensionalAnimarSpritesheetSkill(log, "dimensional-sprite-inimigo");

            setTimeout(() => {
                dimensionalTremerSprite("dimensional-sprite-inimigo");
                dimensionalAnimarNumero(
                    "dimensional-sprite-inimigo",
                    dano ? `-${dano}` : "",
                    critico
                );
            }, 320);

            return;
        }

        if (log.alvo_id) {
            window.dimensionalAlvoSelecionado = String(log.alvo_id);

            const alvo = inimigosComoLista(window.eventoDimensionalAtual).find(i =>
                String(i.id) === String(log.alvo_id)
            );

            if (alvo) {
                dimensionalAplicarSpriteInimigo(window.eventoDimensionalAtual, alvo);
            }
        }

        if (window.AudioManager) {
            window.AudioManager.tocarSFX(critico ? "som_critico" : "som_espada");
        }

        dimensionalAnimarInvestida("dimensional-sprite-heroi");

        setTimeout(() => {
            if (typeof animarEfeitoVisual === "function") {
                animarEfeitoVisual("dimensional-sprite-inimigo", "corte", "#ef4444");
            }

            dimensionalTremerSprite("dimensional-sprite-inimigo");
            dimensionalAnimarNumero("dimensional-sprite-inimigo", dano ? `-${dano}` : "", critico);
        }, 230);
    }

    function dimensionalProcessarAnimacoesRodada(animacoes) {
        const logs = Array.isArray(animacoes) ? animacoes : [];

        console.log("🎬 [DIMENSIONAL ANIMAÇÕES]", logs);

        if (!logs.length) {
            window.bloqueioTurnoDimensional = false;
            renderizarTelaBossDimensional(window.eventoDimensionalAtual);
            return;
        }

        logs.forEach((log, index) => {
            setTimeout(() => {
                dimensionalAdicionarLogVisual(dimensionalFormatarLogVisual(log));
                dimensionalAnimarLogVisual(log);
            }, index * 520);
        });

        const tempoFinal = Math.max(650, logs.length * 520 + 350);

        setTimeout(() => {
            window.bloqueioTurnoDimensional = false;
            renderizarTelaBossDimensional(window.eventoDimensionalAtual);
        }, tempoFinal);
    }

    function dimensionalValor(entidade, chaves) {
        for (const chave of chaves) {
            if (
                entidade &&
                entidade[chave] !== undefined &&
                entidade[chave] !== null &&
                entidade[chave] !== ""
            ) {
                return entidade[chave];
            }
        }

        return null;
    }

    function dimensionalNumeroPrimeiro(entidade, chaves, padrao = 0) {
        const valor = dimensionalValor(entidade, chaves);

        if (valor === null) return padrao;

        const n = Number(valor);
        return Number.isFinite(n) ? n : padrao;
    }

    function dimensionalHpMax(entidade) {
        return Math.max(1, dimensionalNumeroPrimeiro(entidade, [
            "hp_max",
            "hpMax",
            "max_hp",
            "hp_total",
            "vida_max",
            "vidaMax",
            "vida_total",
            "vidaTotal",
            "vida_maxima",
            "vidaMaxima"
        ], 1));
    }

    function dimensionalHpAtual(entidade) {
        const valor = dimensionalValor(entidade, [
            "hp",
            "hp_atual",
            "hpAtual",
            "vida",
            "vida_atual",
            "vidaAtual"
        ]);

        if (valor !== null) {
            const n = Number(valor);
            return Number.isFinite(n) ? n : 0;
        }

        const max = dimensionalHpMax(entidade);
        return max > 1 ? max : 0;
    }

    function dimensionalVivo(entidade) {
        if (!entidade) return false;
        if (entidade.vivo === false) return false;
        if (entidade.morto === true) return false;

        return dimensionalHpAtual(entidade) > 0;
    }

    function dimensionalTipoInimigo(mob, chave = "") {
        const texto = String(
            `${chave} ${mob?.id || ""} ${mob?.tipo || ""} ${mob?.nome || ""} ${mob?.name || ""}`
        ).toLowerCase();

        if (
            texto.includes("boss") ||
            texto.includes("arauto") ||
            texto.includes("vazio")
        ) {
            return "boss";
        }

        return "lacaio";
    }

    function dimensionalIdSeguro(mob, chave = "", index = 0) {
        return String(
            mob?.id ||
            mob?.monster_id ||
            mob?.mob_id ||
            mob?.base_id ||
            mob?.chave ||
            chave ||
            `inimigo_${index}`
        );
    }

    function dimensionalNormalizarSkinHeroi(skinBruta) {
        let skin = skinBruta;

        if (skin && typeof skin === "object") {
            skin =
                skin.id ||
                skin.skin_id ||
                skin.nome ||
                skin.name ||
                skin.arquivo ||
                skin.file ||
                "";
        }

        skin = String(skin || "").trim();

        if (skin.includes("/")) {
            skin = skin.split("/").pop();
        }

        skin = skin.replace(".png", "");

        skin = skin
            .toLowerCase()
            .normalize("NFD")
            .replace(/[\u0300-\u036f]/g, "")
            .replace(/\s+/g, "_")
            .replace("_masculino", "_m")
            .replace("_feminino", "_f");

        if (
            !skin ||
            skin === "player" ||
            skin === "padrao" ||
            skin === "undefined" ||
            skin === "null" ||
            skin === "[object_object]"
        ) {
            skin = "aventureiro_m";
        }

        return skin;
    }

    function dimensionalUrlHeroi(jogador = null) {
        const LINK_BASE = "https://raw.githubusercontent.com/Eldorabotpy/static-img/main/assets/classes_costa/";

        let skinBruta =
            jogador?.equipped_skin ||
            jogador?.skin_equipped ||
            jogador?.skin_equipada ||
            jogador?.skinEquipada ||
            jogador?.skin ||
            jogador?.sprite ||
            jogador?.classe_skin ||
            "";

        if (!skinBruta) {
            skinBruta = localStorage.getItem("skinEquipada") || "";
        }

        const skin = dimensionalNormalizarSkinHeroi(skinBruta);

        return `${LINK_BASE}${skin}.png?v=4`;
    }

    function dimensionalBgArena(evento) {
        const mapa = String(evento?.mapa || evento?.regiao || "floresta_sombria");

        if (typeof FUNDOS_ARENAS !== "undefined" && FUNDOS_ARENAS[mapa]) {
            return FUNDOS_ARENAS[mapa];
        }

        return "https://raw.githubusercontent.com/Eldorabotpy/static-img/main/assets/fundos/floresta.png";
    }

    function dimensionalAssetInimigo(evento, inimigo) {
        const assets = evento?.assets || {};

        const direto =
            inimigo?.asset_combate ||
            inimigo?.sprite_combate ||
            inimigo?.imagem_combate ||
            inimigo?.img_combate ||
            inimigo?.url_combate ||
            "";

        if (direto) {
            return String(direto);
        }

        const id = String(inimigo?.id || "").toLowerCase();
        const nome = String(inimigo?.nome || inimigo?.name || "").toLowerCase();
        const texto = `${id} ${nome}`;

        if (
            inimigo?.tipo === "boss" ||
            texto.includes("boss") ||
            texto.includes("arauto") ||
            texto.includes("vazio")
        ) {
            return (
                assets.boss_combate ||
                DIMENSIONAL_COMBATE_ASSETS_FIXO.boss_combate
            );
        }

        if (
            texto.includes("guardiao") ||
            texto.includes("guardião") ||
            texto.includes("guardiao_da_fenda") ||
            texto.includes("guardião da fenda")
        ) {
            return (
                assets.lacaio_guardiao_combate ||
                DIMENSIONAL_COMBATE_ASSETS_FIXO.lacaio_guardiao_combate
            );
        }

        if (
            texto.includes("sacerdote") ||
            texto.includes("sacerdote_da_fenda")
        ) {
            return (
                assets.lacaio_sacerdote_combate ||
                DIMENSIONAL_COMBATE_ASSETS_FIXO.lacaio_sacerdote_combate
            );
        }

        return (
            assets.lacaio_sacerdote_combate ||
            DIMENSIONAL_COMBATE_ASSETS_FIXO.lacaio_sacerdote_combate
        );
    }

    function dimensionalInimigosVivos(evento) {
        return inimigosComoLista(evento).filter(i => dimensionalVivo(i));
    }

    function dimensionalAlvoAtual(evento) {
        const vivos = dimensionalInimigosVivos(evento);

        if (!vivos.length) return null;

        if (
            window.dimensionalAlvoSelecionado &&
            vivos.some(i => String(i.id) === String(window.dimensionalAlvoSelecionado))
        ) {
            return vivos.find(i => String(i.id) === String(window.dimensionalAlvoSelecionado));
        }

        const primeiroLacaio = vivos.find(i => i.tipo === "lacaio");
        const alvo = primeiroLacaio || vivos[0];

        window.dimensionalAlvoSelecionado = alvo.id;

        return alvo;
    }

    function dimensionalAplicarSpriteInimigo(evento, inimigo) {
        const sprite = document.getElementById("dimensional-sprite-inimigo");
        const nome = document.getElementById("dimensional-alvo-nome");

        if (!sprite) return;

        if (!inimigo) {
            sprite.removeAttribute("src");
            sprite.removeAttribute("data-src-atual");
            sprite.style.display = "none";

            if (nome) nome.innerText = "Sem alvo";
            return;
        }

        const urlBase = dimensionalAssetInimigo(evento, inimigo);
        const urlFinal = urlBase.includes("?") ? `${urlBase}&v=5` : `${urlBase}?v=5`;

        sprite.style.display = "block";
        sprite.style.objectFit = "contain";

        if (sprite.getAttribute("data-src-atual") !== urlFinal) {
            sprite.src = urlFinal;
            sprite.setAttribute("data-src-atual", urlFinal);
        }

        sprite.onerror = function() {
            this.onerror = null;

            const texto = dimensionalEscapeHtml(inimigo?.nome || inimigo?.name || "Inimigo");

            const svg = `
                <svg xmlns="http://www.w3.org/2000/svg" width="180" height="180" viewBox="0 0 180 180">
                    <rect width="180" height="180" rx="18" fill="#0f172a"/>
                    <circle cx="90" cy="70" r="36" fill="#334155"/>
                    <path d="M35 155c8-34 28-52 55-52s47 18 55 52" fill="#334155"/>
                    <text x="90" y="82" text-anchor="middle" font-size="36" fill="#94a3b8" font-family="Arial" font-weight="bold">?</text>
                    <text x="90" y="168" text-anchor="middle" font-size="12" fill="#facc15" font-family="Arial" font-weight="bold">${texto}</text>
                </svg>
            `;

            this.src = `data:image/svg+xml;charset=utf-8,${encodeURIComponent(svg)}`;
        };

        if (inimigo.tipo === "boss") {
            sprite.style.height = "148px";
            sprite.style.maxWidth = "175px";
        } else {
            sprite.style.height = "124px";
            sprite.style.maxWidth = "150px";
        }

        sprite.style.transform = "scaleX(-1)";

        if (nome) {
            nome.innerText = inimigo.nome || inimigo.name || "Inimigo";
        }
    }

    window.selecionarAlvoDimensional = function(alvoId) {
        const evento = window.eventoDimensionalAtual;
        const inimigos = inimigosComoLista(evento);

        const alvo = inimigos.find(i =>
            String(i.id) === String(alvoId) &&
            dimensionalVivo(i)
        );

        if (!alvo) return;

        window.dimensionalAlvoSelecionado = String(alvo.id);
        window.renderizarTelaBossDimensional(window.eventoDimensionalAtual);
    };
    
    async function carregarPerfilDimensionalSePreciso() {
        const charId = getMeuCharId();

        if (!charId) return null;

        if (
            window.perfilDadosGlobais &&
            (
                window.perfilDadosGlobais.skills_equipadas ||
                window.perfilDadosGlobais.equipped_skills
            )
        ) {
            return window.perfilDadosGlobais;
        }

        try {
            const res = await fetch(`/api/personagem/${charId}?t=${Date.now()}`, {
                cache: "no-store"
            });

            window.perfilDadosGlobais = await res.json();

            if (window.perfilDadosGlobais && !window.perfilDadosGlobais.cooldowns) {
                window.perfilDadosGlobais.cooldowns = {};
            }

            return window.perfilDadosGlobais;
        } catch (e) {
            console.warn("Não foi possível carregar perfil para skills da Fenda:", e);
            return window.perfilDadosGlobais || {};
        }
    }

    function dimensionalMeuJogadorAtual() {
        return getMeuJogadorDimensional(window.eventoDimensionalAtual);
    }

    function dimensionalManaAtualDoMeuJogador() {
        const meu = dimensionalMeuJogadorAtual();

        if (meu) {
            const mp = meu.mp ?? meu.current_mp ?? meu.mana ?? meu.current_mana;

            if (mp !== undefined && mp !== null && !Number.isNaN(Number(mp))) {
                return Number(mp);
            }
        }

        if (window.perfilDadosGlobais) {
            return Number(
                window.perfilDadosGlobais.mp_atual ??
                window.perfilDadosGlobais.current_mp ??
                window.perfilDadosGlobais.mp ??
                window.perfilDadosGlobais.mana ??
                0
            );
        }

        return 0;
    }

    function dimensionalCooldownSkill(skillId) {
        const meu = dimensionalMeuJogadorAtual();
        const cdEvento = meu?.cooldowns || {};
        const cdPerfil = window.perfilDadosGlobais?.cooldowns || {};

        return Number(cdEvento[skillId] ?? cdPerfil[skillId] ?? 0);
    }

    function dimensionalRaridadeSkill(skillId) {
        const p = window.perfilDadosGlobais || {};
        const minhasSkills = p.skills || p.skills_desbloqueadas || {};
        const inst = minhasSkills[skillId] || {};

        return inst.rarity || inst.raridade || "comum";
    }

    function dimensionalInfoSkillMesclada(skillId) {
        const p = window.perfilDadosGlobais || {};
        const dbSkills = p.database_skills || p.skills_database || {};
        const base = dbSkills[skillId] || {};

        const raridade = dimensionalRaridadeSkill(skillId);
        const raridadeInfo =
            base.rarity_effects?.[raridade] ||
            base.rarity_effects?.comum ||
            {};

        return {
            ...base,
            ...raridadeInfo,
            effects: raridadeInfo.effects || base.effects || {},
            rarity: raridade,
            skill_id_real: base.skill_id || base.id || skillId
        };
    }

    function dimensionalCustoManaSkill(skillId) {
        const info = dimensionalInfoSkillMesclada(skillId);

        return Number(
            info.mana_cost ||
            info.mp_cost ||
            0
        );
    }

    window.abrirMenuSkillsDimensional = async function() {
        const perfil = await carregarPerfilDimensionalSePreciso();

        if (!perfil) {
            alert("Não foi possível carregar suas skills.");
            return;
        }

        const skillsEquipadas =
           perfil.skills_equipadas ||
            perfil.equipped_skills ||
            {};

        let modal = document.getElementById("modal-skills-dimensional");

        if (!modal) {
            modal = document.createElement("div");
            modal.id = "modal-skills-dimensional";
            modal.style.cssText = `
                position:fixed;
                inset:0;
                z-index:400000;
                background:rgba(2,6,23,.78);
                backdrop-filter:blur(5px);
                display:flex;
                align-items:center;
                justify-content:center;
                padding:12px;
                box-sizing:border-box;
            `;

            document.body.appendChild(modal);
        }

        const manaAtual = dimensionalManaAtualDoMeuJogador();

        let htmlSkills = "";

        [1, 2, 3, 4, 5].forEach(slot => {
            const skillId = skillsEquipadas[`slot_${slot}`];

            if (!skillId) return;

            const info = dimensionalInfoSkillMesclada(skillId);
            const nome = info.display_name || info.name || String(skillId).replace(/_/g, " ");
            const icone = info.icon || "default_skill";
            const custoMana = dimensionalCustoManaSkill(skillId);
            const cd = dimensionalCooldownSkill(skillId);

            const semMana = Number(manaAtual) < Number(custoMana);
            const travada = cd > 0 || semMana || info.type === "passive";

            const motivo =
                info.type === "passive" ? "PASSIVA" :
                cd > 0 ? `⏳ ${cd}` :
                semMana ? `Falta MP (${manaAtual}/${custoMana})` :
                "USAR";

            const img = `https://raw.githubusercontent.com/Eldorabotpy/static-img/main/assets/sprites/skills/${icone}.png`;

            htmlSkills += `
                <button
                    ${travada ? "disabled" : ""}
                    onclick="window.usarSkillDimensional('${String(skillId).replace(/'/g, "\\'")}')"
                    style="
                        background:${travada ? "rgba(30,41,59,.55)" : "rgba(30,41,59,.95)"};
                        border:1px solid ${travada ? "#ef4444" : "#8b5cf6"};
                        border-radius:10px;
                        padding:8px;
                        color:#fff;
                        cursor:${travada ? "not-allowed" : "pointer"};
                        opacity:${travada ? ".55" : "1"};
                        display:flex;
                        flex-direction:column;
                        align-items:center;
                        gap:5px;
                        min-height:96px;
                    "
                >
                    <img src="${img}" onerror="this.src='https://raw.githubusercontent.com/Eldorabotpy/static-img/main/assets/sprites/skills/default_skill.png'" style="
                        width:42px;
                        height:42px;
                        border-radius:7px;
                        object-fit:cover;
                        background:#020617;
                    ">
                    <b style="font-size:10px;line-height:1.1;text-align:center;color:#e2e8f0;">
                        ${dimensionalEscapeHtml(nome)}
                    </b>
                    <span style="font-size:10px;color:${semMana ? "#ef4444" : "#60a5fa"};">
                        💧${custoMana} — ${motivo}
                    </span>
                </button>
            `;
        });

        if (!htmlSkills) {
            htmlSkills = `
                <div style="grid-column:1/-1;color:#94a3b8;text-align:center;padding:16px;">
                    Nenhuma skill equipada.
                </div>
            `;
        }

        modal.innerHTML = `
            <div style="
                width:min(92vw,360px);
                background:linear-gradient(180deg, rgba(15,23,42,.98), rgba(2,6,23,.98));
                border:1px solid #8b5cf6;
                border-top:3px solid #facc15;
                border-radius:14px;
                padding:14px;
                box-shadow:0 18px 45px rgba(0,0,0,.85);
                color:#fff;
            ">
                <div style="
                    font-family:'Cinzel',serif;
                    color:#facc15;
                    font-weight:900;
                    text-align:center;
                    margin-bottom:10px;
                ">
                    ✨ Skills da Fenda
                </div>

                <div style="
                    display:grid;
                    grid-template-columns:repeat(2, minmax(0, 1fr));
                    gap:8px;
                    max-height:58vh;
                    overflow-y:auto;
                ">
                    ${htmlSkills}
                </div>

                <button onclick="window.fecharMenuSkillsDimensional()" style="
                    margin-top:12px;
                    width:100%;
                    background:transparent;
                    color:#94a3b8;
                    border:1px solid #475569;
                    border-radius:9px;
                    padding:9px;
                    font-weight:900;
                    cursor:pointer;
                ">Fechar</button>
            </div>
        `;

        modal.style.display = "flex";
    };

    window.fecharMenuSkillsDimensional = function() {
        const modal = document.getElementById("modal-skills-dimensional");
        if (modal) modal.style.display = "none";
    };

    window.usarSkillDimensional = async function(skillId) {
        window.fecharMenuSkillsDimensional();

        const evento = window.eventoDimensionalAtual;
        const alvo = dimensionalAlvoAtual(evento);

        const info = dimensionalInfoSkillMesclada(skillId);
        const ehSuporte =
            info.type === "support" ||
            info.effects?.party_heal ||
            info.effects?.party_mana ||
            info.effects?.party_buff ||
            info.effects?.target === "party" ||
            info.effects?.target === "ally";

        if (!ehSuporte) {
            if (!alvo) {
                alert("Nenhum alvo válido.");
                return;
            }

            if (alvo.tipo === "boss" && bossProtegidoDimensional(evento)) {
                alert("O Arauto está protegido. Derrote os lacaios primeiro.");
                return;
            }
        }

        await window.executarSkillDimensionalSelecionada(
            info.skill_id_real || skillId,
            ehSuporte ? null : alvo.id
        );
    };

    window.executarSkillDimensionalSelecionada = async function(skillId, alvoId = null) {
        if (window.bloqueioTurnoDimensional) return;
        window.bloqueioTurnoDimensional = true;

        const userId = getMeuCharId();

        if (!userId) {
            window.bloqueioTurnoDimensional = false;
            alert("ID do jogador não encontrado.");
            return;
        }

        try {
            const res = await fetch("/api/dimensional/acao", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    user_id: userId,
                    tipo: "magia",
                    skill_id: skillId,
                    alvo_id: alvoId || window.dimensionalAlvoSelecionado || ""
                })
            });

            const dados = await res.json();

            console.log("🌌 [DIMENSIONAL SKILL RESPOSTA]", dados);

            if (!dados.success) {
                window.bloqueioTurnoDimensional = false;
                alert(dados.error || "Não foi possível usar a skill.");
                return;
            }

            if (window.perfilDadosGlobais && dados.cooldowns) {
                window.perfilDadosGlobais.cooldowns = dados.cooldowns;
            }

            window.eventoDimensionalAtual = dados.evento;

            const alvoAtual = dimensionalAlvoAtual(window.eventoDimensionalAtual);

            if (!alvoAtual) {
                window.dimensionalAlvoSelecionado = null;
            }

            renderizarTelaBossDimensional(window.eventoDimensionalAtual);

            const animacoesAcao = dados.animacoes_acao || [];

            if (Array.isArray(animacoesAcao) && animacoesAcao.length > 0) {
                setTimeout(() => {
                    dimensionalProcessarAnimacoesRodada(animacoesAcao);
                }, 120);
            } else {
                window.bloqueioTurnoDimensional = false;
            }

            if (dados.processou_rodada) {
                const animacoesRodada = dados.animacoes_rodada || [];

                if (Array.isArray(animacoesRodada) && animacoesRodada.length > 0) {
                    setTimeout(() => {
                        dimensionalProcessarAnimacoesRodada(animacoesRodada);
                    }, 950);
                }

                if (typeof window.mostrarNotificacaoRPG === "function") {
                    window.mostrarNotificacaoRPG("Rodada dos inimigos resolvida!", "⚔️");
                }
            } else {
                if (dados.message && typeof window.mostrarNotificacaoRPG === "function") {
                    window.mostrarNotificacaoRPG(dados.message, "⏳");
                }
            }

        } catch (e) {
            window.bloqueioTurnoDimensional = false;
            alert("Erro ao usar skill: " + e.message);
        }
    };

    window.executarAtaqueDimensionalSelecionado = function() {
        const evento = window.eventoDimensionalAtual;
        const alvo = dimensionalAlvoAtual(evento);

        if (!alvo) {
            alert("Nenhum alvo válido.");
            return;
        }

        if (alvo.tipo === "boss" && bossProtegidoDimensional(evento)) {
            alert("O Arauto está protegido. Derrote os lacaios primeiro.");
            return;
        }

        window.atacarDimensional(alvo.id);
    };

    window.objetosDimensionalMapa = window.objetosDimensionalMapa || [];
    window.eventoDimensionalMapaId = null;

    function obterCenaMapaDimensional() {
        try {
            if (!window.jogoEldora) return null;

            const cena = window.jogoEldora.scene.getScene("MapaScene");

            if (!cena || !cena.scene || !cena.add) return null;

            return cena;
        } catch (e) {
            return null;
        }
    }

    function limparDimensionalDoMapa(motivo = "limpeza") {
        const lista = window.objetosDimensionalMapa || [];

        lista.forEach(obj => {
            try {
                if (obj && typeof obj.destroy === "function") {
                    obj.destroy();
                }
            } catch (e) {}
        });

        window.objetosDimensionalMapa = [];
        window.eventoDimensionalMapaId = null;

        console.log("🧹 [DIMENSIONAL MAPA] Limpou visuais:", motivo);
    }

    function criarAnimacaoDimensionalSeNaoExiste(cena, key, frameInicio, frameFim, frameRate) {
        const animKey = `${key}_anim`;

        if (!cena || !cena.anims) return animKey;

        if (!cena.anims.exists(animKey)) {
            cena.anims.create({
                key: animKey,
                frames: cena.anims.generateFrameNumbers(key, {
                    start: frameInicio,
                    end: frameFim
                }),
                frameRate: frameRate,
                repeat: -1
            });
        }

        return animKey;
    }

    function carregarSpritesheetDimensional(cena, key, url, frameWidth, frameHeight, callback) {
        if (!cena || !key || !url) return;

        if (cena.textures.exists(key)) {
            callback();
            return;
        }

        cena.load.spritesheet(key, url, {
            frameWidth: frameWidth,
            frameHeight: frameHeight
        });

        cena.load.once(`filecomplete-spritesheet-${key}`, () => {
            callback();
        });

        cena.load.once("loaderror", (fileObj) => {
            if (fileObj && fileObj.key === key) {
                console.warn("❌ [DIMENSIONAL MAPA] Falha ao carregar:", fileObj.url);
            }
        });

        cena.load.start();
    }

    function desenharDimensionalNoMapa(evento) {
        const cena = obterCenaMapaDimensional();

        if (!cena || !evento || !evento.evento_id) return;

        const regiaoCena = String(cena.regiaoAtual || localStorage.getItem("eldora_lastRegiao") || "");
        const regiaoEvento = String(evento.mapa || evento.regiao || "");

        if (regiaoCena !== regiaoEvento) {
            limparDimensionalDoMapa("evento em outro mapa");
            return;
        }

        if (window.eventoDimensionalMapaId === evento.evento_id && window.objetosDimensionalMapa.length > 0) {
            return;
        }

        limparDimensionalDoMapa("redesenhar evento");

        const assets = evento.assets || {};
        const sheet = evento.spritesheet || {};
        const pos = evento.posicoes_mapa || {};

        const portalSheet = sheet.portal || {};
        const mobSheet = sheet.mobs || {};

        const framePortalW = Number(portalSheet.frame_width || 128);
        const framePortalH = Number(portalSheet.frame_height || 128);

        const frameMobW = Number(mobSheet.frame_width || 128);
        const frameMobH = Number(mobSheet.frame_height || 128);

        const keyPortal = "ss_dimensional_portal";
        const keyBoss = "ss_dimensional_arauto_vazio";
        const keyGuardiao = "ss_dimensional_guardiao_fenda";
        const keySacerdote = "ss_dimensional_sacerdote_fenda";

        window.eventoDimensionalMapaId = evento.evento_id;

        function addNomeMapa(texto, x, y, cor = "#facc15") {
            const label = cena.add.text(x, y, texto, {
                fontSize: "11px",
                fontFamily: "Cinzel, Arial",
                color: cor,
                stroke: "#000000",
                strokeThickness: 4,
                align: "center"
            }).setOrigin(0.5).setDepth(40);

            window.objetosDimensionalMapa.push(label);
            return label;
        }

        function addPortal() {
            const p = pos.portal || { x: 30 * 32, y: 27 * 32 };

            carregarSpritesheetDimensional(cena, keyPortal, assets.portal, framePortalW, framePortalH, () => {
                const portal = cena.add.sprite(p.x, p.y, keyPortal, 0)
                    .setDepth(12)
                    .setScale(1.25);

                const animKey = criarAnimacaoDimensionalSeNaoExiste(cena, keyPortal, 0, 7, 8);
                portal.play(animKey);

                portal.setInteractive({
                    useHandCursor: true,
                    pixelPerfect: false
                });

                portal.on("pointerdown", (pointer, localX, localY, event) => {
                    if (event) event.stopPropagation();

                    if (typeof window.abrirTelaBossDimensional === "function") {
                        window.abrirTelaBossDimensional();
                    }
                });

                cena.tweens.add({
                    targets: portal,
                    alpha: 0.75,
                    duration: 700,
                    yoyo: true,
                    repeat: -1,
                    ease: "Sine.easeInOut"
                });

                addNomeMapa("Fenda Dimensional", p.x, p.y - 82, "#a78bfa");

                window.objetosDimensionalMapa.push(portal);
            });
        }

        function addMobVisual(tipo, key, url, posicao, nome, escala, corNome) {
            const p = posicao || { x: 30 * 32, y: 24 * 32 };

            carregarSpritesheetDimensional(cena, key, url, frameMobW, frameMobH, () => {
                const sprite = cena.add.sprite(p.x, p.y, key, 1)
                    .setDepth(15)
                    .setScale(escala);

                // Linha 1 da spritesheet 3x4: frente/baixo, frames 0,1,2
                const animKey = criarAnimacaoDimensionalSeNaoExiste(cena, key, 0, 2, 4);
                sprite.play(animKey);

                sprite.tipoDimensional = tipo;
                sprite.eventoDimensionalId = evento.evento_id;

                cena.tweens.add({
                    targets: sprite,
                    y: p.y - 6,
                    duration: 900,
                    yoyo: true,
                    repeat: -1,
                    ease: "Sine.easeInOut"
                });

                addNomeMapa(nome, p.x, p.y - (tipo === "boss" ? 78 : 58), corNome);

                window.objetosDimensionalMapa.push(sprite);
            });
        }

        addPortal();

        addMobVisual(
            "boss",
            keyBoss,
            assets.boss,
            pos.boss,
            "Arauto do Vazio",
            0.95,
            "#ef4444"
        );

        addMobVisual(
            "lacaio",
            keyGuardiao,
            assets.lacaio_guardiao,
            pos.lacaio_guardiao,
            "Guardião da Fenda",
            0.72,
            "#facc15"
        );

        addMobVisual(
            "lacaio",
            keySacerdote,
            assets.lacaio_sacerdote,
            pos.lacaio_sacerdote,
            "Sacerdote da Fenda",
            0.72,
            "#93c5fd"
        );

        console.log("🌌 [DIMENSIONAL MAPA] Evento desenhado no mapa:", evento.evento_id);
    }

    function sincronizarDimensionalNoMapa() {
        const evento = window.eventoDimensionalAtual;

        if (!evento || !evento.evento_id) {
            limparDimensionalDoMapa("sem evento ativo");
            return;
        }

        desenharDimensionalNoMapa(evento);
    }

    function dimensionalNomeMapa(mapaId) {
        const nomes = {
            capital_eldora: "Capital de Eldora",
            pradaria_inicial: "Pradaria Inicial",
            floresta_sombria: "Floresta Sombria",
            pedreira_granito: "Pedreira de Granito"
        };

        return nomes[mapaId] || String(mapaId || "mapa desconhecido").replace(/_/g, " ");
    }

    function dimensionalSocketAtual() {
        try {
            if (window.eldoraSocket) return window.eldoraSocket;
        } catch (e) {}

        try {
            if (typeof socket !== "undefined" && socket) return socket;
        } catch (e) {}

        return null;
    }

    function dimensionalNotificar(titulo, mensagem, icone = "🌌") {
        const texto = String(mensagem || titulo || "Fenda Dimensional");

        // Remove aviso anterior da Fenda para não empilhar.
        const antigo = document.getElementById("toast-dimensional-fenda");
        if (antigo) {
            try { antigo.remove(); } catch (e) {}
        }

        const toast = document.createElement("div");
        toast.id = "toast-dimensional-fenda";

        toast.innerHTML = `
            <div style="
                width:22px;
                height:22px;
                flex:0 0 auto;
                border-radius:999px;
                display:flex;
                align-items:center;
                justify-content:center;
                background:rgba(76,29,149,.85);
                border:1px solid rgba(250,204,21,.55);
                font-size:13px;
                box-shadow:0 0 10px rgba(124,58,237,.55);
            ">${dimensionalEscapeHtml(icone)}</div>

            <div style="
                min-width:0;
                flex:1;
                display:flex;
                flex-direction:column;
                gap:1px;
            ">
                <div style="
                    color:#facc15;
                    font-size:10px;
                    font-weight:900;
                    font-family:'Cinzel', Arial, sans-serif;
                    line-height:1;
                ">
                    ${dimensionalEscapeHtml(titulo || "Fenda Dimensional")}
                </div>

                <div style="
                    color:#e2e8f0;
                    font-size:10px;
                    font-weight:800;
                    line-height:1.15;
                    white-space:nowrap;
                    overflow:hidden;
                    text-overflow:ellipsis;
                ">
                    ${dimensionalEscapeHtml(texto)}
                </div>
            </div>
        `;

        toast.style.cssText = `
            position:fixed;
            left:50%;
            top:74px;
            transform:translateX(-50%);
            z-index:350000;
            width:min(270px, calc(100vw - 28px));
            min-height:38px;
            padding:6px 8px;
            box-sizing:border-box;
            display:flex;
            align-items:center;
            gap:7px;
            background:linear-gradient(180deg, rgba(15,23,42,.96), rgba(2,6,23,.96));
            border:1px solid rgba(139,92,246,.75);
            border-left:3px solid #a78bfa;
            border-radius:10px;
            box-shadow:0 8px 22px rgba(0,0,0,.65), 0 0 14px rgba(124,58,237,.35);
            pointer-events:none;
            opacity:0;
        `;

        document.body.appendChild(toast);

        toast.animate(
            [
                { opacity: 0, transform: "translateX(-50%) translateY(-10px) scale(.96)" },
                { opacity: 1, transform: "translateX(-50%) translateY(0) scale(1)" }
            ],
            {
                duration: 180,
                easing: "ease-out",
                fill: "forwards"
            }
        );

        setTimeout(() => {
            try {
                toast.animate(
                    [
                        { opacity: 1, transform: "translateX(-50%) translateY(0) scale(1)" },
                        { opacity: 0, transform: "translateX(-50%) translateY(-8px) scale(.96)" }
                    ],
                    {
                        duration: 180,
                        easing: "ease-in",
                        fill: "forwards"
                    }
                );

                setTimeout(() => {
                    try { toast.remove(); } catch (e) {}
                }, 200);
            } catch (e) {
                try { toast.remove(); } catch (err) {}
            }
        }, 2800);

        console.log(`[DIMENSIONAL] ${titulo}: ${mensagem}`);
    }

    function instalarSocketDimensional() {
        if (window.__socketDimensionalInstalado) return;

        const s = dimensionalSocketAtual();

        if (!s) {
            console.warn("🌌 [DIMENSIONAL SOCKET] Socket ainda não disponível.");
            return;
        }

        window.__socketDimensionalInstalado = true;

        s.off("fendaDimensionalSurgiu");
        s.off("fendaDimensionalAtualizada");
        s.off("fendaDimensionalIniciada");
        s.off("fendaDimensionalEncerrada");

        s.on("fendaDimensionalSurgiu", (payload = {}) => {
            const evento = payload.evento || payload;

            if (!evento || !evento.evento_id) return;

            window.eventoDimensionalAtual = evento;

            const mapaId = payload.mapa || evento.mapa || evento.regiao;
            const mapaNome = payload.mapa_nome || dimensionalNomeMapa(mapaId);

            atualizarBotaoDimensional();
            sincronizarDimensionalNoMapa();

            dimensionalNotificar(
                "Fenda Dimensional",
                payload.mensagem || `Uma Fenda Dimensional surgiu em ${mapaNome}!`,
                "🌌"
            );

            console.log("🌌 [DIMENSIONAL SOCKET] Fenda surgiu:", payload);
        });

        s.on("fendaDimensionalAtualizada", (payload = {}) => {
            const evento = payload.evento || payload;

            if (!evento || !evento.evento_id) return;

            window.eventoDimensionalAtual = evento;

            atualizarBotaoDimensional();
            sincronizarDimensionalNoMapa();

            const tela = document.getElementById("tela-dimensional-boss");
            const telaAberta =
                tela &&
                tela.style.display !== "none" &&
                getComputedStyle(tela).display !== "none";

            if (telaAberta) {
                renderizarTelaBossDimensional(window.eventoDimensionalAtual);
            }
        });

        s.on("fendaDimensionalIniciada", (payload = {}) => {
            const evento = payload.evento || payload;

            if (evento && evento.evento_id) {
                window.eventoDimensionalAtual = evento;
                atualizarBotaoDimensional();
                sincronizarDimensionalNoMapa();

                const tela = document.getElementById("tela-dimensional-boss");
                const telaAberta =
                    tela &&
                    tela.style.display !== "none" &&
                    getComputedStyle(tela).display !== "none";

                if (telaAberta) {
                    renderizarTelaBossDimensional(window.eventoDimensionalAtual);
                }
            }

            dimensionalNotificar(
                "Fenda Dimensional",
                payload.mensagem || "A batalha da Fenda Dimensional começou!",
                "⚔️"
            );
        });

        s.on("fendaDimensionalEncerrada", (payload = {}) => {
            const eventoId = payload.evento_id;

            if (
                !eventoId ||
                !window.eventoDimensionalAtual ||
                String(window.eventoDimensionalAtual.evento_id) === String(eventoId)
            ) {
                window.eventoDimensionalAtual = null;
            }

            limparDimensionalDoMapa("socket encerramento");
            atualizarBotaoDimensional();

            const tela = document.getElementById("tela-dimensional-boss");
            const telaAberta =
                tela &&
                tela.style.display !== "none" &&
                getComputedStyle(tela).display !== "none";

            if (telaAberta) {
                renderizarTelaBossDimensional(window.eventoDimensionalAtual);
            }

            if (payload.mensagem) {
                dimensionalNotificar("Fenda Dimensional", payload.mensagem, "🌌");
            }

            console.log("🌌 [DIMENSIONAL SOCKET] Fenda encerrada:", payload);
        });

        console.log("🌌 [DIMENSIONAL SOCKET] Escutas instaladas.");
    }

    window.__dimensionalElementosOcultos = [];
    
    function instalarCssBloqueioDimensional() {
        if (document.getElementById("style-bloqueio-dimensional")) return;

        const style = document.createElement("style");
        style.id = "style-bloqueio-dimensional";

        style.innerHTML = `
            body.dimensional-aberto #btn-teste-auto-cacada,
            body.dimensional-aberto .auto-cacada-icone,
            body.dimensional-aberto [id*="auto-cacada"],
            body.dimensional-aberto [class*="auto-cacada"],
            body.dimensional-aberto #btn-dimensional-boss,
            body.dimensional-aberto #btn-dimensional-debug,
            body.dimensional-aberto .btn-passe-mapa,
            body.dimensional-aberto .btn-social-mapa,
            body.dimensional-aberto #eldora-party-hud,
            body.dimensional-aberto #hud-moderno,
            body.dimensional-aberto #online-counter,
            body.dimensional-aberto #btn-chat-mapa,
            body.dimensional-aberto #btn-abrir-menu {
                display: none !important;
                pointer-events: none !important;
                visibility: hidden !important;
            }
        `;

        document.head.appendChild(style);
    }

    function esconderUiMapaDuranteDimensional() {
        const seletores = [
            '#btn-abrir-menu',
            '#hud-moderno',
            '#online-counter',
            '#btn-chat-mapa',
            '#eldora-party-hud',
            '#btn-teste-auto-cacada',
            '#btn-dimensional-boss',
            '#btn-dimensional-debug',
            '.btn-passe-mapa',
            '.btn-social-mapa',
            '.btn-gm',
            '.gm-button',
            '[data-gm-button]'
        ];

        window.__dimensionalElementosOcultos = [];

        seletores.forEach(seletor => {
            document.querySelectorAll(seletor).forEach(el => {
                if (!el) return;

                window.__dimensionalElementosOcultos.push({
                    el: el,
                    display: el.style.display || '',
                    pointerEvents: el.style.pointerEvents || ''
                });

                el.style.display = 'none';
                el.style.pointerEvents = 'none';
            });
        });

        // Segurança extra: esconde botões flutuantes de GM/debug que tenham texto "GM"
        document.querySelectorAll('button, div').forEach(el => {
            const texto = String(el.innerText || '').trim().toUpperCase();

            if (texto === 'GM' || texto.includes(' GM')) {
                const pos = getComputedStyle(el).position;
                const z = Number(getComputedStyle(el).zIndex || 0);

                if (pos === 'fixed' || z >= 80) {
                    window.__dimensionalElementosOcultos.push({
                        el: el,
                        display: el.style.display || '',
                        pointerEvents: el.style.pointerEvents || ''
                    });

                    el.style.display = 'none';
                    el.style.pointerEvents = 'none';
                }
            }
        });

        document.body.classList.add('dimensional-aberto');
    }

    function restaurarUiMapaDepoisDimensional() {
        const lista = window.__dimensionalElementosOcultos || [];

        lista.forEach(item => {
            if (!item || !item.el) return;

            item.el.style.display = item.display;
            item.el.style.pointerEvents = item.pointerEvents;
        });

        window.__dimensionalElementosOcultos = [];
        document.body.classList.remove('dimensional-aberto');
    }

    function getMeuCharId() {
        return String(localStorage.getItem("jogadorEldoraID") || "");
    }

    function formatarTempo(segundos) {
        segundos = Math.max(0, Number(segundos || 0));
        const m = Math.floor(segundos / 60).toString().padStart(2, "0");
        const s = Math.floor(segundos % 60).toString().padStart(2, "0");
        return `${m}:${s}`;
    }
    
        function dimensionalTempoEntradaRestante(evento) {
        if (!evento) return 0;

        const status = String(evento.status || "");

        if (status !== "aguardando_jogadores") {
            return 0;
        }

        const fim = Number(evento.entrada_encerra_em || 0);

        if (fim > 0) {
            return Math.max(0, Math.floor(fim - (Date.now() / 1000)));
        }

        return Math.max(0, Number(evento.tempo_entrada_restante || 0));
    }

    function telaDimensionalEstaAberta() {
        const tela = document.getElementById("tela-dimensional-boss");

        return Boolean(
            tela &&
            tela.style.display !== "none" &&
            getComputedStyle(tela).display !== "none"
        );
    }

    function inimigosComoLista(evento) {
        if (!evento) return [];

        const lista = [];

    function nomePadraoInimigo(mob, chave, tipo) {
        const texto = String(`${chave} ${mob?.id || ""} ${mob?.nome || ""} ${mob?.name || ""}`).toLowerCase();

        if (tipo === "boss" || texto.includes("arauto")) return "Arauto do Vazio";
        if (texto.includes("guardiao") || texto.includes("guardião")) return "Guardião da Fenda";
        if (texto.includes("sacerdote")) return "Sacerdote da Fenda";

        return tipo === "boss" ? "Boss" : "Lacaio";
    }

    function adicionar(mob, chave, index) {
        if (!mob || typeof mob !== "object") return;

        const tipo = dimensionalTipoInimigo(mob, chave);
        const id = dimensionalIdSeguro(mob, chave, index);

        const normalizado = {
                ...mob,
                id: id,
                tipo: tipo,
                nome: mob.nome || mob.name || mob.nome_exibicao || nomePadraoInimigo(mob, chave, tipo),
                hp: dimensionalHpAtual(mob),
                hp_max: dimensionalHpMax(mob),
                vivo: dimensionalVivo(mob)
            };

            lista.push(normalizado);
        }

        if (Array.isArray(evento.inimigos)) {
            evento.inimigos.forEach((mob, index) => adicionar(mob, mob?.id || `inimigo_${index}`, index));
        } else if (evento.inimigos && typeof evento.inimigos === "object") {
            Object.entries(evento.inimigos).forEach(([chave, mob], index) => adicionar(mob, chave, index));
        }

        if (evento.boss) {
            adicionar(evento.boss, "boss", lista.length);
        }

        if (Array.isArray(evento.lacaios)) {
            evento.lacaios.forEach((mob, index) => adicionar(mob, mob?.id || `lacaio_${index + 1}`, lista.length));
        } else if (evento.lacaios && typeof evento.lacaios === "object") {
            Object.entries(evento.lacaios).forEach(([chave, mob]) => adicionar(mob, chave, lista.length));
        }

        [
            "lacaio_1",
            "lacaio_2",
            "lacaio1",
            "lacaio2",
            "guardiao",
            "sacerdote",
            "lacaio_guardiao",
            "lacaio_sacerdote"
        ].forEach(chave => {
            if (evento[chave]) {
                adicionar(evento[chave], chave, lista.length);
           }
        });

        const vistos = new Set();

        const semDuplicados = lista.filter(i => {
            const id = String(i.id || "");
            if (!id || vistos.has(id)) return false;

            vistos.add(id);
            return true;
        });

        function pesoInimigo(i) {
            const texto = String(`${i.id || ""} ${i.nome || ""}`).toLowerCase();

            if (i.tipo === "boss") return 3;
            if (texto.includes("guardiao") || texto.includes("guardião")) return 1;
            if (texto.includes("sacerdote")) return 2;

            return 2;
        }

        return semDuplicados.sort((a, b) => pesoInimigo(a) - pesoInimigo(b));
    }
    
    function meuJogadorEstaNaFenda(evento) {
        const meuId = getMeuCharId();

        if (!evento || !meuId) return false;

        const jogadores = evento.jogadores || {};

        return Boolean(jogadores[meuId]);
    }

    function getMeuJogadorDimensional(evento) {
        const meuId = getMeuCharId();

        if (!evento || !meuId) return null;

        const jogadores = evento.jogadores || {};

        return jogadores[meuId] || null;
    }


    function meuJogadorJaEnviouAcao(evento) {
        const meu = getMeuJogadorDimensional(evento);

        return Boolean(meu && meu.acao_enviada);
    }


    function contarAcoesPendentesDimensional(evento) {
        const jogadores = evento && evento.jogadores ? evento.jogadores : {};

        const vivos = Object.values(jogadores).filter(j =>
            Number(j.hp || 0) > 0 &&
            j.vivo !== false
        );

        const enviados = vivos.filter(j => j.acao_enviada === true).length;

        return {
            pendentes: enviados,
            vivos: vivos.length
        };
    }

    function bossProtegidoDimensional(evento) {
        const inimigos = inimigosComoLista(evento);

        return inimigos.some(i =>
            i.tipo === "lacaio" &&
            dimensionalVivo(i)
        );
    }

    function renderizarAcoesBossDimensional(evento) {
        const box = document.getElementById("dimensional-acoes");

        if (!box) return;

        if (!evento) {
            box.innerHTML = `
                <button onclick="window.fecharTelaBossDimensional()" class="dimensional-btn" style="grid-column:1/-1;">
                    ⬅️ Voltar ao Mapa
                </button>
            `;
            return;
        }

        const estouNaFenda = meuJogadorEstaNaFenda(evento);
        const status = String(evento.status || "aguardando_jogadores");
        const alvo = dimensionalAlvoAtual(evento);
        const protegido = bossProtegidoDimensional(evento);
        const alvoBloqueado = alvo && alvo.tipo === "boss" && protegido;

        if (!estouNaFenda) {
            box.innerHTML = `
                <button onclick="window.entrarBossDimensional()" class="dimensional-btn" style="
                    grid-column:1/-1;
                    border-color:#8b5cf6;
                    background:linear-gradient(180deg, #7c3aed, #4c1d95);
                ">
                    🌌 ENTRAR NA FENDA
                </button>
            `;
            return;
        }

        const meu = getMeuJogadorDimensional(evento);

        if (meu && Number(meu.hp || 0) <= 0) {
            box.innerHTML = `
                <div style="
                    grid-column:1/-1;
                    color:#ef4444;
                    font-weight:900;
                    text-align:center;
                    border:1px solid #7f1d1d;
                    border-radius:10px;
                    padding:10px;
                    background:rgba(69,10,10,.55);
                ">
                    💀 Você foi derrotado e está aguardando o fim da Fenda.
                </div>
            `;
            return;
        }

        if (status === "aguardando_jogadores") {
            const tempoRestante = dimensionalTempoEntradaRestante(evento);
            const qtdJogadores = Number(evento.qtd_jogadores || Object.keys(evento.jogadores || {}).length || 0);
            const maxJogadores = Number(evento.max_jogadores || 20);

            box.innerHTML = `
                <div style="
                    grid-column:1/-1;
                    color:#facc15;
                    font-weight:900;
                    text-align:center;
                    border:1px solid #475569;
                    border-radius:10px;
                    padding:10px;
                    background:rgba(15,23,42,.82);
                    font-family:'Cinzel', Arial, sans-serif;
                    line-height:1.35;
                ">
                    ⏳ Aguardando entrada dos heróis<br>
                    <span style="font-size:12px;color:#93c5fd;font-family:Arial,sans-serif;">
                        Inicia automaticamente em ${formatarTempo(tempoRestante)}
                    </span><br>
                    <span style="font-size:11px;color:#94a3b8;font-family:Arial,sans-serif;">
                        Heróis na Fenda: ${qtdJogadores}/${maxJogadores}
                    </span>
                </div>

                <button onclick="window.sairBossDimensional()" class="dimensional-btn" style="
                    grid-column:1/-1;
                ">
                    🚪 SAIR DA FILA
                </button>
            `;
            return;
        }

        if (status === "vitoria" || status === "derrota") {
            box.innerHTML = `
                <button onclick="window.fecharTelaBossDimensional()" class="dimensional-btn" style="
                    grid-column:1/-1;
                    border-color:${status === "vitoria" ? "#22c55e" : "#ef4444"};
                ">
                    ⬅️ Voltar ao Mapa
                </button>
            `;
            return;
        }

        if (status !== "em_combate") {
            box.innerHTML = `
                <div style="grid-column:1/-1;color:#94a3b8;text-align:center;">
                    Status atual: ${dimensionalEscapeHtml(status)}
                </div>
            `;
            return;
        }

        if (meuJogadorJaEnviouAcao(evento)) {
            const contagem = contarAcoesPendentesDimensional(evento);

            box.innerHTML = `
                <div style="
                    grid-column:1/-1;
                    color:#facc15;
                    font-weight:900;
                    text-align:center;
                    border:1px solid #475569;
                    border-radius:10px;
                    padding:10px;
                    background:rgba(15,23,42,.82);
                ">
                    ⏳ Sua ação já foi enviada<br>
                    <span style="font-size:12px;color:#93c5fd;">
                        Aguardando heróis: ${contagem.pendentes}/${contagem.vivos}
                    </span>
                </div>
            `;
            return;
        }

        box.innerHTML = `
            <button
                onclick="window.executarAtaqueDimensionalSelecionado()"
                ${!alvo || alvoBloqueado ? "disabled" : ""}
                class="dimensional-btn dimensional-btn-atacar"
                style="
                    opacity:${!alvo || alvoBloqueado ? ".45" : "1"};
                    cursor:${!alvo || alvoBloqueado ? "not-allowed" : "pointer"};
                "
            >
                ${alvoBloqueado ? "🔒 Boss Protegido" : "⚔️ Atacar"}
            </button>

            <button
                onclick="window.abrirMenuSkillsDimensional()"
                class="dimensional-btn dimensional-btn-skill"
            >
                ✨ Skill
            </button>

            ${alvoBloqueado ? `
                <div style="grid-column:1/-1;color:#f87171;font-size:12px;text-align:center;">
                    O Arauto está protegido. Derrote os lacaios primeiro.
                </div>
            ` : `
                <div style="grid-column:1/-1;color:#94a3b8;font-size:12px;text-align:center;">
                    Alvo: <b style="color:#facc15;">${dimensionalEscapeHtml(alvo?.nome || "Nenhum")}</b>
                </div>
            `}
        `;
    }

    function obterRegiaoAtualDimensional() {
        try {
            if (window.jogoEldora) {
                const cena = window.jogoEldora.scene.getScene("MapaScene");
                if (cena && cena.regiaoAtual) return cena.regiaoAtual;
            }
        } catch (e) {}

        return (
            window.regiaoAtual ||
            localStorage.getItem("regiaoAtual") ||
            localStorage.getItem("eldora_lastRegiao") ||
            "capital_eldora"
        );
    }

    function usuarioEhAdminDimensional() {
        const MEU_ID_ADMIN = 7262799478;
        const meuTelegram = window.Telegram?.WebApp?.initDataUnsafe?.user?.id;

        return (
            Number(meuTelegram) === MEU_ID_ADMIN ||
            localStorage.getItem("souGM") === "sim"
        );
    }

    function criarBotaoTesteDimensional() {
        const btn = document.getElementById("btn-dimensional-debug");

        if (btn) {
            try { btn.remove(); } catch (e) {}
        }

        // Produção: botão de teste removido.
        return null;
    }

    function criarBotaoDimensional() {
        const btn = document.getElementById("btn-dimensional-boss");

        if (btn) {
            try { btn.remove(); } catch (e) {}
        }

        // Produção: não existe mais botão flutuante da Fenda.
        // A entrada será feita clicando diretamente no portal do mapa.
        return null;
    }

    function mapaEstaVisivelDimensional() {
        const telaCombate = document.getElementById("tela-combate-global");
        const telaDimensional = document.getElementById("tela-dimensional-boss");

        const combateAberto =
            telaCombate &&
            telaCombate.style.display !== "none" &&
            getComputedStyle(telaCombate).display !== "none";

        const dimensionalAberta =
            telaDimensional &&
            telaDimensional.style.display !== "none" &&
            getComputedStyle(telaDimensional).display !== "none";

        if (combateAberto || dimensionalAberta) return false;

        const canvas = document.querySelector("canvas");
        const gameContainer =
            document.getElementById("game-container") ||
            document.getElementById("phaser-game");

        const canvasVisivel =
            canvas &&
            getComputedStyle(canvas).display !== "none" &&
            canvas.offsetParent !== null;

        const containerVisivel =
            gameContainer &&
            getComputedStyle(gameContainer).display !== "none" &&
            gameContainer.offsetParent !== null;

        return !!(canvasVisivel || containerVisivel);
    }


    function atualizarBotaoDimensional() {
        // Remove qualquer botão antigo que tenha ficado no DOM/cache.
        const btnPortal = document.getElementById("btn-dimensional-boss");
        const btnDebug = document.getElementById("btn-dimensional-debug");

        if (btnPortal) {
            try { btnPortal.remove(); } catch (e) {}
        }

        if (btnDebug) {
            try { btnDebug.remove(); } catch (e) {}
        }

        // A Fenda agora só abre pelo portal desenhado no mapa.
        // Não cria, não mostra e não mantém botão flutuante.
    }

    async function buscarStatusDimensional() {
        try {
            const res = await fetch(`/api/dimensional/status?t=${Date.now()}`);
            const dados = await res.json();

            if (dados && dados.success && dados.ativo && dados.evento) {
                window.eventoDimensionalAtual = dados.evento;
            } else {
                window.eventoDimensionalAtual = null;
            }

            atualizarBotaoDimensional();
            sincronizarDimensionalNoMapa();

            const tela = document.getElementById("tela-dimensional-boss");

            const telaAberta =
                tela &&
                tela.style.display !== "none" &&
                getComputedStyle(tela).display !== "none";

            if (telaAberta) {
                renderizarTelaBossDimensional(window.eventoDimensionalAtual);
            }

        } catch (e) {
            console.warn("Erro ao buscar status dimensional:", e);
        }
    }

    window.abrirTelaBossDimensional = async function () {
        const tela = document.getElementById("tela-dimensional-boss");

        if (!tela) {
            alert("Tela dimensional não encontrada. Verifique o include dimensional_boss.html.");
            return;
        }

        tela.style.display = "flex";
        tela.style.zIndex = "300000";

        setTimeout(instalarControleScrollLogDimensional, 100);

        instalarCssBloqueioDimensional();
        esconderUiMapaDuranteDimensional();

        try {
            await buscarStatusDimensional();
        } catch (e) {
            console.warn("Erro ao atualizar status antes de abrir a Fenda:", e);
        }

        renderizarTelaBossDimensional(window.eventoDimensionalAtual);
    };

    window.fecharTelaBossDimensional = function () {
        const tela = document.getElementById("tela-dimensional-boss");
        if (tela) tela.style.display = "none";

        restaurarUiMapaDepoisDimensional();

        atualizarBotaoDimensional();
    };

    window.renderizarTelaBossDimensional = function (evento) {
        const titulo = document.getElementById("dimensional-titulo");
        const subtitulo = document.getElementById("dimensional-subtitulo");
        const contador = document.getElementById("dimensional-contador");
        const listaHerois = document.getElementById("dimensional-lista-jogadores");
        const listaInimigos = document.getElementById("dimensional-lista-inimigos");
        const logBox = document.getElementById("dimensional-log");
        const palco = document.getElementById("dimensional-palco");
        const aviso = document.getElementById("dimensional-aviso-turno");
        const spriteHeroi = document.getElementById("dimensional-sprite-heroi");

        if (!evento) {
            if (titulo) titulo.innerText = "Nenhuma Fenda ativa";
            if (subtitulo) subtitulo.innerText = "Aguarde uma Fenda Dimensional aparecer.";
            if (contador) contador.innerText = "0/20";
            if (listaHerois) listaHerois.innerHTML = `<div style="color:#94a3b8;">Nenhum jogador.</div>`;
            if (listaInimigos) listaInimigos.innerHTML = `<div style="color:#94a3b8;">Nenhum inimigo.</div>`;
            if (logBox) logBox.innerHTML = "";
            if (aviso) aviso.innerText = "Aguardando...";
            dimensionalAplicarSpriteInimigo(null, null);
            renderizarAcoesBossDimensional(null);
            return;
        }

        const status = String(evento.status || "aguardando_jogadores");
        const rodada = Number(evento.rodada || 0);
        const tempoEntradaRestante = dimensionalTempoEntradaRestante(evento);

        if (titulo) {
            titulo.innerText = evento.nome_evento || "Fenda Dimensional";
        }

        if (subtitulo) {
            const textoTempo = status === "aguardando_jogadores"
                ? formatarTempo(tempoEntradaRestante)
                : "00:00";

            subtitulo.innerText =
                `${evento.nome_boss || "Arauto do Vazio"} apareceu em ${evento.mapa || "mapa"} | Entrada: ${textoTempo}`;
        }

        if (palco) {
            palco.style.backgroundImage = `url('${dimensionalBgArena(evento)}')`;
        }

        let jogadores = [];

        if (Array.isArray(evento.jogadores_lista)) {
            jogadores = evento.jogadores_lista;
        } else if (evento.jogadores_lista && typeof evento.jogadores_lista === "object") {
            jogadores = Object.values(evento.jogadores_lista);
        } else if (Array.isArray(evento.jogadores)) {
            jogadores = evento.jogadores;
        } else {
            jogadores = Object.values(evento.jogadores || {});
        }

        const qtd = Number(evento.qtd_jogadores || jogadores.length || 0);
        const max = Number(evento.max_jogadores || 20);

        if (contador) {
            contador.innerText = `${qtd}/${max}`;
        }

        const meuId = getMeuCharId();

        const meuJogador =
            getMeuJogadorDimensional(evento) ||
            jogadores.find(j => String(j.user_id || j.id || j.char_id || j._id || "") === meuId) ||
            jogadores[0] ||
            null;

        if (spriteHeroi) {
            const urlHeroi = dimensionalUrlHeroi(meuJogador);

            spriteHeroi.style.display = "block";
            spriteHeroi.style.objectFit = "contain";

            if (spriteHeroi.getAttribute("data-src-atual") !== urlHeroi) {
                spriteHeroi.src = urlHeroi;
                spriteHeroi.setAttribute("data-src-atual", urlHeroi);
            }

            spriteHeroi.onerror = function() {
                this.onerror = null;
                this.src = DIMENSIONAL_HEROI_FALLBACK;
            };
        }

        const alvo = dimensionalAlvoAtual(evento);
        dimensionalAplicarSpriteInimigo(evento, alvo);

        if (aviso) {
            if (status === "aguardando_jogadores") {
                if (tempoEntradaRestante <= 0) {
                    aviso.innerText = "⚔️ Iniciando batalha...";
                    aviso.style.color = "#fb7185";
                    aviso.style.borderColor = "#fb7185";
                } else {
                    aviso.innerText = `⏳ Aguardando heróis ${formatarTempo(tempoEntradaRestante)}`;
                    aviso.style.color = "#facc15";
                    aviso.style.borderColor = "#facc15";
                }
            } else if (status === "em_combate") {
                const contagem = contarAcoesPendentesDimensional(evento);
                const jaEnviou = meuJogadorJaEnviouAcao(evento);

                aviso.innerText = jaEnviou
                    ? `⏳ Rodada ${rodada} — ${contagem.pendentes}/${contagem.vivos}`
                    : `✅ Rodada ${rodada} — escolha sua ação`;

                aviso.style.color = jaEnviou ? "#facc15" : "#22c55e";
                aviso.style.borderColor = jaEnviou ? "#facc15" : "#22c55e";
            } else if (status === "vitoria") {
                aviso.innerText = "🏆 Vitória!";
                aviso.style.color = "#22c55e";
                aviso.style.borderColor = "#22c55e";
            } else if (status === "derrota") {
                aviso.innerText = "💀 Derrota!";
                aviso.style.color = "#ef4444";
                aviso.style.borderColor = "#ef4444";
            } else {
                aviso.innerText = status;
                aviso.style.color = "#facc15";
                aviso.style.borderColor = "#facc15";
            }
        }

        if (listaHerois) {
            if (!jogadores.length) {
                listaHerois.innerHTML = `<div style="color:#94a3b8;">Nenhum jogador.</div>`;
            } else {
                listaHerois.innerHTML = jogadores.map(j => {
                    const id = String(j.user_id || j.id || j.char_id || j._id || "");
                    const souEu = id === meuId;
                    const hp = dimensionalHpAtual(j);
                    const hpMax = dimensionalHpMax(j);
                    const mp = Number(j.mp || j.mana || 0);
                    const mpMax = Number(j.mp_max || j.mana_max || j.manaMax || 1);
                    const morto = !dimensionalVivo(j);
                    const nome = dimensionalEscapeHtml(j.nome || "Herói");
                    const nomeCurto = nome.length > 10 ? nome.slice(0, 10) + "…" : nome;

                    return `
                        <div class="dimensional-card ${souEu ? "dimensional-card-eu" : ""}" style="opacity:${morto ? ".55" : "1"};">
                            <div style="display:flex;justify-content:space-between;gap:5px;align-items:center;">
                                <b style="
                                    color:${souEu ? "#38bdf8" : "#e2e8f0"};
                                    font-size:11px;
                                    white-space:nowrap;
                                    overflow:hidden;
                                    text-overflow:ellipsis;
                                ">
                                    ${morto ? "💀" : "🛡️"} ${nomeCurto}
                                </b>

                                <span style="font-size:9px;color:#94a3b8;white-space:nowrap;">
                                    ${souEu ? "VOCÊ" : ""}
                                </span>
                            </div>

                            <div class="dimensional-mini-bar">
                                <div style="height:100%;width:${dimensionalPct(hp, hpMax)}%;background:#22c55e;"></div>
                            </div>

                            <div class="dimensional-mini-bar" style="height:5px;">
                                <div style="height:100%;width:${dimensionalPct(mp, mpMax)}%;background:#3b82f6;"></div>
                            </div>

                            <div style="display:flex;justify-content:space-between;font-size:9px;color:#94a3b8;margin-top:3px;">
                                <span>HP ${Math.floor(hp)}/${hpMax}</span>
                                <span>MP ${Math.floor(mp)}/${mpMax}</span>
                            </div>

                            ${j.acao_enviada ? `
                                <div style="font-size:9px;color:#facc15;margin-top:2px;font-weight:900;">
                                    ação pronta
                                </div>
                            ` : ""}
                        </div>
                    `;
                }).join("");
            }
        }

        if (listaInimigos) {
            const inimigos = inimigosComoLista(evento);

            if (!inimigos.length) {
                listaInimigos.innerHTML = `<div style="color:#94a3b8;">Nenhum inimigo.</div>`;
            } else {
                listaInimigos.innerHTML = inimigos.map(i => {
                    const hp = dimensionalHpAtual(i);
                    const hpMax = dimensionalHpMax(i);
                    const morto = !dimensionalVivo(i);
                    const selecionado = String(window.dimensionalAlvoSelecionado || "") === String(i.id);
                    const bossBloqueado = i.tipo === "boss" && bossProtegidoDimensional(evento);

                    const nome = dimensionalEscapeHtml(i.nome || i.name || "Inimigo");
                    const nomeCurto = nome.length > 12 ? nome.slice(0, 12) + "…" : nome;

                    return `
                        <button
                            ${morto ? "disabled" : ""}
                            onclick="window.selecionarAlvoDimensional('${String(i.id).replace(/'/g, "\\'")}')"
                            class="dimensional-card ${selecionado ? "dimensional-card-alvo" : ""}"
                            style="
                                width:100%;
                                text-align:left;
                                color:#fff;
                                cursor:${morto ? "not-allowed" : "pointer"};
                                opacity:${morto ? ".45" : "1"};
                            "
                        >
                            <div style="display:flex;justify-content:space-between;gap:5px;align-items:center;">
                                <b style="
                                    color:${i.tipo === "boss" ? "#facc15" : "#fca5a5"};
                                    font-size:11px;
                                    white-space:nowrap;
                                    overflow:hidden;
                                    text-overflow:ellipsis;
                                ">
                                    ${i.tipo === "boss" ? "👑" : "👹"} ${nomeCurto}
                                </b>

                                <span style="font-size:9px;color:${selecionado ? "#facc15" : "#94a3b8"};white-space:nowrap;">
                                    ${bossBloqueado ? "🔒" : selecionado ? "ALVO" : ""}
                                </span>
                            </div>

                            <div class="dimensional-mini-bar">
                                <div style="height:100%;width:${dimensionalPct(hp, hpMax)}%;background:#ef4444;"></div>
                            </div>

                            <div style="font-size:9px;color:#94a3b8;margin-top:3px;">
                                HP ${Math.floor(hp)}/${hpMax}
                            </div>
                        </button>
                    `;
                }).join("");
            }
        }

        if (logBox) {
            instalarControleScrollLogDimensional();

            const estavaNoFim = dimensionalLogPertoDoFim(logBox);
            const scrollAnterior = logBox.scrollTop;
            const usuarioLendoHistorico = logBox.dataset.usuarioScrollManual === "1";

            const logs = evento.logs || [];

            const logsLimpos = logs
                .filter(l => {
                    const txt = String(l.texto || "").toLowerCase();

                    if (txt.includes("preparou ataque contra")) return false;
                    if (txt.includes("rodada") && txt.includes("começou")) return false;

                    return true;
                })
                .slice(-40);

            logBox.innerHTML = logsLimpos.map(l => {
                const txt = String(l.texto || "").toLowerCase();

                if (txt.includes("rodada") && txt.includes("terminou")) {
                    return `
                        <div style="
                            text-align:center;
                            color:#94a3b8;
                            font-size:10px;
                            font-weight:900;
                            margin:4px 0;
                            opacity:.85;
                        ">
                            ${dimensionalEscapeHtml(l.texto || "")}
                        </div>
                    `;
                }

                const pacote = {
                    ...l,
                    texto: l.texto || "",
                    autor_nome: "",
                    is_inimigo: false
                };

                if (txt.includes(" usou ")) {
                    pacote.acao = "magia";
                    pacote.autor_nome = String(l.texto || "").split(" usou ")[0] || "Herói";
                    pacote.skill_nome = "Skill";
                } else if (txt.includes("atacou") && txt.includes("causou")) {
                    pacote.acao = "ataque_inimigo";
                    pacote.is_inimigo = true;
                    pacote.autor_nome = String(l.texto || "").split(" atacou ")[0] || "Inimigo";
                } else if (txt.includes("curou")) {
                    pacote.acao = "cura_inimigo";
                    pacote.is_inimigo = true;
                    pacote.autor_nome = String(l.texto || "").split(" curou ")[0] || "Sacerdote";
                } else if (txt.includes("crítico") || txt.includes("causou")) {
                    pacote.acao = "ataque_basico";
                    pacote.autor_nome = String(l.texto || "").split(" causou ")[0] || "Herói";
                }

                return dimensionalFormatarLogVisual(pacote);
            }).join("");

            if (usuarioLendoHistorico && !estavaNoFim) {
                logBox.scrollTop = scrollAnterior;
            } else {
                logBox.scrollTop = logBox.scrollHeight;
            }
        }

        renderizarAcoesBossDimensional(evento);
    };

    window.entrarBossDimensional = async function () {
        const userId = getMeuCharId();

        if (!userId) {
            alert("ID do jogador não encontrado.");
            return;
        }

        try {
            const res = await fetch("/api/dimensional/entrar", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ user_id: userId })
            });

            const dados = await res.json();

            if (!dados.success) {
                alert(dados.error || "Não foi possível entrar na Fenda.");
                return;
            }

            window.eventoDimensionalAtual = dados.evento;
            renderizarTelaBossDimensional(window.eventoDimensionalAtual);

            if (typeof window.mostrarNotificacaoRPG === "function") {
                window.mostrarNotificacaoRPG(dados.message || "Você entrou na Fenda Dimensional!", "🌌");
            }

        } catch (e) {
            alert("Erro ao entrar na Fenda: " + e.message);
        }
    };

    window.sairBossDimensional = async function () {
        const userId = getMeuCharId();

        if (!userId) return;

        try {
            const res = await fetch("/api/dimensional/sair", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ user_id: userId })
            });

            const dados = await res.json();

            if (dados && dados.evento) {
                window.eventoDimensionalAtual = dados.evento;
                renderizarTelaBossDimensional(window.eventoDimensionalAtual);
            }

        } catch (e) {
            console.warn("Erro ao sair da Fenda:", e);
        }
    };
    
    window.iniciarBatalhaDimensional = async function () {
        const evento = window.eventoDimensionalAtual;

        const tempoRestante = dimensionalTempoEntradaRestante(evento);
        const qtdJogadores = Number(evento?.qtd_jogadores || Object.keys(evento?.jogadores || {}).length || 0);
        const maxJogadores = Number(evento?.max_jogadores || 20);

        if (tempoRestante > 0 && qtdJogadores < maxJogadores) {
            if (typeof dimensionalNotificar === "function") {
                dimensionalNotificar(
                    "Fenda Dimensional",
                    `A batalha começa automaticamente em ${formatarTempo(tempoRestante)} ou ao completar ${maxJogadores}/${maxJogadores} heróis.`,
                    "⏳"
                );
            } else {
                alert(`A batalha começa automaticamente em ${formatarTempo(tempoRestante)} ou ao completar ${maxJogadores}/${maxJogadores} heróis.`);
            }

            return;
        }

        // Se o tempo já acabou ou lotou, não força manualmente.
        // O backend/status automático vai iniciar a batalha.
        await buscarStatusDimensional();
    };


    window.atacarDimensional = async function (alvoId) {
        if (window.bloqueioTurnoDimensional) return;
        window.bloqueioTurnoDimensional = true;

        const userId = getMeuCharId();

        if (!userId) {
            window.bloqueioTurnoDimensional = false;
            alert("ID do jogador não encontrado.");
            return;
        }

        try {
            const res = await fetch("/api/dimensional/acao", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    user_id: userId,
                    tipo: "ataque_basico",
                    alvo_id: alvoId
                })
            });

            const dados = await res.json();

            console.log("🌌 [DIMENSIONAL AÇÃO RESPOSTA]", dados);

            if (!dados.success) {
                window.bloqueioTurnoDimensional = false;
                alert(dados.error || "Não foi possível atacar.");
                return;
            }

            window.eventoDimensionalAtual = dados.evento;

            const alvoAtual = dimensionalAlvoAtual(window.eventoDimensionalAtual);

            if (!alvoAtual) {
                window.dimensionalAlvoSelecionado = null;
            }

            renderizarTelaBossDimensional(window.eventoDimensionalAtual);

            const animacoesAcao = dados.animacoes_acao || [];

            if (Array.isArray(animacoesAcao) && animacoesAcao.length > 0) {
                setTimeout(() => {
                    dimensionalProcessarAnimacoesRodada(animacoesAcao);
                }, 120);
            }

            if (dados.processou_rodada) {
                const animacoesRodada = dados.animacoes_rodada || [];

                if (Array.isArray(animacoesRodada) && animacoesRodada.length > 0) {
                    setTimeout(() => {
                        dimensionalProcessarAnimacoesRodada(animacoesRodada);
                    }, 900);
                }

                if (typeof window.mostrarNotificacaoRPG === "function") {
                    window.mostrarNotificacaoRPG("Rodada dos inimigos resolvida!", "⚔️");
                }
            } else {

                window.bloqueioTurnoDimensional = false;

                if (dados.message && typeof window.mostrarNotificacaoRPG === "function") {
                    window.mostrarNotificacaoRPG(dados.message, "⏳");
                }
            }

        } catch (e) {
            window.bloqueioTurnoDimensional = false;
            alert("Erro ao atacar: " + e.message);
        }
    };
    window.criarBossDimensionalDebug = async function (mapa = null) {
        const body = mapa ? { mapa } : {};

        const res = await fetch("/api/dimensional/criar_debug", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(body)
        });

        const dados = await res.json();

        if (dados.success) {
            window.eventoDimensionalAtual = dados.evento;
            atualizarBotaoDimensional();

            if (typeof window.mostrarNotificacaoRPG === "function") {
                window.mostrarNotificacaoRPG("Fenda Dimensional criada para teste.", "🌌");
            }
        }
    
        console.log("DEBUG DIMENSIONAL:", dados);
        return dados;
    };

    document.addEventListener("DOMContentLoaded", () => {
        criarBotaoDimensional();
        criarBotaoTesteDimensional();

        setTimeout(instalarSocketDimensional, 250);
        setTimeout(instalarSocketDimensional, 1000);

        buscarStatusDimensional();

        setInterval(() => {
            buscarStatusDimensional();
            atualizarBotaoDimensional();
            sincronizarDimensionalNoMapa();
        }, 5000);

        setInterval(() => {
            atualizarBotaoDimensional();
            sincronizarDimensionalNoMapa();

            if (telaDimensionalEstaAberta()) {
                renderizarTelaBossDimensional(window.eventoDimensionalAtual);
            }

            const evento = window.eventoDimensionalAtual;

            if (
                evento &&
                evento.status === "aguardando_jogadores" &&
                dimensionalTempoEntradaRestante(evento) <= 0 &&
                !window.__dimensionalForcandoStatusFimEntrada
            ) {
                window.__dimensionalForcandoStatusFimEntrada = true;

                buscarStatusDimensional().finally(() => {
                    setTimeout(() => {
                        window.__dimensionalForcandoStatusFimEntrada = false;
                    }, 2000);
                });
            }
        }, 500);
    });
})();