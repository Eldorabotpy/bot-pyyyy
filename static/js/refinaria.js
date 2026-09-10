// /static/js/refinaria.js

const RefinariaEngine = {
    receitas: {},
    profSelecionada: null,
    receitaSelecionada: null,
    quantidadeAtual: 1,
    quantidadeMaxima: 1,

    async iniciar() {
        try {
            // Rota no seu app.py que retorna REFINING_RECIPES do backend
            const res = await fetch('/api/refining/recipes'); 
            this.receitas = await res.json();
            this.definirAbaInicial();
            RefinariaUI.renderizarTudo();
        } catch (e) { console.error("Erro na Refinaria:", e); }
    },

    definirAbaInicial() {
        const profs = this.getProfissoesJogador();
        if (profs.length > 0 && !this.profSelecionada) {
            this.profSelecionada = profs[0];
        }
    },

    getProfissoesJogador() {
        const p = window.perfilDadosGlobais;
        if (!p) return [];
        // Profissões focadas em refino
        const permitidas = ['fundidor', 'curtidor', 'joalheiro', 'alfaiate', 'ferreiro', 'armeiro']; 
        let conhecidas = p.learned_professions || {};
        if (p.profession?.key) conhecidas[p.profession.key] = p.profession;
        
        return Object.keys(conhecidas)
            .filter(k => permitidas.includes(k.toLowerCase()))
            // Remove duplicatas se necessário e retorna array limpo
            .map(k => k.toLowerCase()); 
    },

    getReceitasDaAbaAtual() {
        let filtradas = {};
        for (let id in this.receitas) {
            const profsPermitidas = this.receitas[id].profession;
            if (profsPermitidas && profsPermitidas.includes(this.profSelecionada)) {
                filtradas[id] = this.receitas[id];
            }
        }
        return filtradas;
    },

    calcularMaximoPossivel(receita) {
        const p = window.perfilDadosGlobais;
        const inv = p.inventario || p.inventory || [];
        let max_qty = 9999;

        for (const [mat_id, req_qty] of Object.entries(receita.inputs || {})) {
            const itemInv = inv.find(i => {
                const base = i.base_id || i.item_id || i.id;
                return String(base) === String(mat_id);
            });

            const held = itemInv
                ? Number(itemInv.qtd || itemInv.quantity || itemInv.quantidade || 0)
                : 0;
            const can_make = Math.floor(held / req_qty);
            if (can_make < max_qty) max_qty = can_make;
        }
        
        let invMax = max_qty === 9999 ? 0 : max_qty;
        if (invMax === 0) return 0;

        // 🔴 NOVA REGRA VISUAL: Limita o botão "MAX" ao nível da profissão!
        const profKey = (this.profSelecionada || 'ferreiro').toLowerCase();
        const learned = p.learned_professions || {};
        let profData = learned[profKey] || {};
        if (!profData.level && p.profession?.key === profKey) {
            profData = p.profession;
        }
        const myLvl = parseInt(profData.level || 1);

        return Math.min(invMax, myLvl);
    },

    selecionarReceita(id) {
        this.receitaSelecionada = id;
        const rec = this.receitas[id];
        
        this.quantidadeMaxima = this.calcularMaximoPossivel(rec);
        this.quantidadeAtual = this.quantidadeMaxima > 0 ? 1 : 0; // Começa em 1 se der, ou 0 se faltar tudo

        RefinariaUI.atualizarDetalhes(id, rec);
    },

    mudarAba(prof) {
        this.profSelecionada = prof;
        this.receitaSelecionada = null;
        RefinariaUI.renderizarTudo();
    }
};

window.abrirUIRefinaria = async function() {
    const container = document.getElementById('refinaria-container');
    if (!container) return;
    container.style.display = 'flex';
    
    // 💥 A MÁGICA: Esconde os botões do Passe e do Chat para não sobrepor a Refinaria!
    document.querySelectorAll('.btn-passe-mapa, .btn-social-mapa').forEach(btn => btn.style.display = 'none');
    
    await RefinariaEngine.iniciar();
};

window.fecharUIRefinaria = function() {
    document.getElementById('refinaria-container').style.display = 'none';
    
    // 💥 A MÁGICA: Traz os botões de volta quando o herói terminar de refinar!
    document.querySelectorAll('.btn-passe-mapa, .btn-social-mapa').forEach(btn => btn.style.display = 'flex');
};

window.tentarIniciarRefino = async function() {
    if (!RefinariaEngine.receitaSelecionada || RefinariaEngine.quantidadeAtual < 1) return;
    
    const charId = localStorage.getItem("jogadorEldoraID");
    // GARANTIA: usamos parseInt para ter certeza que é um número, não texto!
    const qtdFinal = parseInt(RefinariaEngine.quantidadeAtual, 10);
    
    // 👇 AQUI ENTRA A MUDANÇA! Adicionamos a profissão no payload enviado ao Python
    const payload = { 
        user_id: charId, 
        recipe_id: RefinariaEngine.receitaSelecionada,
        quantity: qtdFinal,
        profession: RefinariaEngine.profSelecionada.toLowerCase() // 👈 AVISA O PYTHON DE QUAL ABA VOCÊ ESTÁ A USAR!
    };
    
    document.getElementById('btn-iniciar-refino').disabled = true;
    document.getElementById('btn-iniciar-refino').innerText = "AQUECENDO FORNALHA...";

    try {
        const res = await fetch('/api/refining/start_batch', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const data = await res.json();
        
        if (data.success) {
            fecharUIRefinaria();
            window.iniciarAnimacaoRefinaria(data.duration_seconds, RefinariaEngine.receitaSelecionada, qtdFinal);
        } else {
            if (window.alertaEldora) window.alertaEldora("Aviso", data.error || "Erro ao refinar.", "erro");
            document.getElementById('btn-iniciar-refino').disabled = false;
            document.getElementById('btn-iniciar-refino').innerText = "INICIAR REFINO";
        }
    } catch (e) { 
        console.error(e); 
        document.getElementById('btn-iniciar-refino').disabled = false;
        document.getElementById('btn-iniciar-refino').innerText = "INICIAR REFINO";
    }
};

// =====================================================================
// ⏳ MÁGICA VISUAL: BARRA DE PROGRESSO E LOOT FLUTUANTE
// =====================================================================
window.iniciarAnimacaoRefinaria = function(duracaoSegundos, receitaId, quantidade) {
    const cena = window.jogoEldora.scene.getScene('MapaScene');
    if (!cena || !cena.player) return;

    // Trava o jogador para ele não fugir da fornalha
    cena.player.isGathering = true;
    cena.pararPersonagem();

    const rec = RefinariaEngine.receitas[receitaId];
    
    // Cria a UI da Barra em cima do personagem
    let uiContainer = cena.add.container(cena.player.x, cena.player.y - 65).setDepth(200);
    
    let textoRefino = cena.add.text(0, -16, `🔥 ${quantidade}x Lotes 🔥`, {
        fontSize: '11px', fontFamily: 'Arial', color: '#ea580c', stroke: '#000', strokeThickness: 3, fontStyle: 'bold'
    }).setOrigin(0.5);

    // Fundo da barra
    let bgBar = cena.add.graphics();
    bgBar.fillStyle(0x0f0502, 0.8);
    bgBar.lineStyle(1.5, 0xea580c, 1);
    bgBar.fillRoundedRect(-30, -4, 60, 8, 4);
    bgBar.strokeRoundedRect(-30, -4, 60, 8, 4);

    let fillBar = cena.add.graphics();
    let timerTexto = cena.add.text(0, 10, `${duracaoSegundos}s`, {
         fontSize: '10px', fontFamily: 'Arial', color: '#fff', stroke: '#000', strokeThickness: 2
    }).setOrigin(0.5);

    uiContainer.add([bgBar, fillBar, textoRefino, timerTexto]);

    // Animação de impacto do Ferreiro batendo
    let animBatida = cena.tweens.add({ targets: cena.player, y: cena.player.y - 2, angle: 3, yoyo: true, duration: 400, repeat: -1 });

    let progresso = { valor: 0 };
    cena.tweens.add({
        targets: progresso,
        valor: 56,
        duration: duracaoSegundos * 1000,
        onUpdate: () => {
            fillBar.clear();
            if (progresso.valor > 0) {
                fillBar.fillStyle(0xea580c, 1);
                fillBar.fillRoundedRect(-28, -2, progresso.valor, 4, 2);
            }
            let tempoAtual = Math.ceil(duracaoSegundos - (progresso.valor / 56) * duracaoSegundos);
            timerTexto.setText(`${tempoAtual}s`);
        },
        onComplete: async () => {
            // Fim do tempo: Libera o jogador!
            animBatida.stop();
            cena.player.angle = 0;
            uiContainer.destroy();
            cena.player.isGathering = false;

            const charId = localStorage.getItem("jogadorEldoraID");
            try {
                const res = await fetch('/api/refining/finish', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ user_id: charId })
                });
                const data = await res.json();

                if (data.success) {
                    // 1. Atualiza o perfil pela rota oficial PRIMEIRO (para formatar o inventário como Array)
                    if (typeof window.carregarMeuPerfil === 'function') {
                        await window.carregarMeuPerfil(); 
                    }

                    // 2. Agora com os dados 100% seguros, manda a UI desenhar o novo XP ao vivo!
                    if (RefinariaEngine.receitaSelecionada) {
                        RefinariaUI.atualizarDetalhes(RefinariaEngine.receitaSelecionada, RefinariaEngine.receitas[RefinariaEngine.receitaSelecionada]);
                    }

                    // 3. Destrava visualmente o botão para futuros usos
                    const btnRefino = document.getElementById('btn-iniciar-refino');
                    if (btnRefino) {
                        btnRefino.disabled = false;
                        btnRefino.innerText = "INICIAR REFINO";
                    }

                    // Notificação suave global
                    if (window.mostrarNotificacaoSuave) {
                        window.mostrarNotificacaoSuave("Refino Concluído!", `Você ganhou ${data.data.xp_reward || 0} XP!`);
                    }

                    // ✨ A MÁGICA: LOOT E XP FLUTUANDO NO MAPA ✨
                    if (data.data && data.data.outputs) {
                        let delayOffset = 0;
                        for (const [outputId, qtdObtida] of Object.entries(data.data.outputs)) {
                            setTimeout(() => {
                                if (!cena.scene.isActive()) return;
                                
                                let imgUrl = `${GITHUB_BASE_ITENS}materiais/${outputId}.png`;
                                let textureKey = 'loot_' + outputId;

                                let spawnLoot = () => {
                                    let lootContainer = cena.add.container(cena.player.x, cena.player.y - 30).setDepth(300);
                                    
                                    let bgBox = cena.add.graphics();
                                    bgBox.fillStyle(0x0f172a, 0.9);
                                    bgBox.lineStyle(1.5, 0xea580c, 1);
                                    bgBox.fillRoundedRect(-16, -16, 32, 32, 6);
                                    bgBox.strokeRoundedRect(-16, -16, 32, 32, 6);

                                    let icone = cena.add.sprite(0, 0, cena.textures.exists(textureKey) ? textureKey : 'box').setDisplaySize(24, 24);
                                    let txtQtd = cena.add.text(22, 0, `+${qtdObtida}`, {
                                        fontFamily: 'Arial', fontSize: '16px', color: '#4ade80', stroke: '#000', strokeThickness: 4, fontStyle: 'bold'
                                    }).setOrigin(0, 0.5);

                                    lootContainer.add([bgBox, icone, txtQtd]);
                                    if (typeof window.AudioManager !== 'undefined') window.AudioManager.tocarSFX('som_coleta');

                                    cena.tweens.add({
                                        targets: lootContainer,
                                        y: lootContainer.y - 70,
                                        alpha: 0,
                                        duration: 2500,
                                        ease: 'Power2',
                                        onComplete: () => lootContainer.destroy()
                                    });
                                };

                                if (!cena.textures.exists(textureKey)) {
                                    cena.load.image(textureKey, imgUrl);
                                    cena.load.once('complete', spawnLoot);
                                    cena.load.start();
                                } else {
                                    spawnLoot();
                                }
                            }, delayOffset);
                            delayOffset += 600;
                        }
                    }
                } else {
                    if (window.alertaEldora) window.alertaEldora("Aviso da Fornalha", data.error || "O refino falhou.", "erro");
                }
            } catch (e) {
                console.error(e);
            }
        }
    }); 
};
const RefinariaUI = {
    desenharAbas() {
        const container = document.getElementById('abas-profissoes-refinaria');
        if (!container) return;
        container.innerHTML = '';
        
        const profs = RefinariaEngine.getProfissoesJogador();
        profs.forEach(prof => {
            const btn = document.createElement('button');
            btn.className = `aba-forja-btn ${RefinariaEngine.profSelecionada === prof ? 'active' : ''}`;
            btn.innerText = prof.toUpperCase();
            btn.onclick = () => RefinariaEngine.mudarAba(prof);
            container.appendChild(btn);
        });
    },
    // 👇 SUBSTITUA A FUNÇÃO AQUI 👇
    renderizarTudo() {
        const profs = RefinariaEngine.getProfissoesJogador();
        
        // 🔴 TRAVA PARA COLETORES
        if (profs.length === 0) {
            document.getElementById('abas-profissoes-refinaria').innerHTML = `
                <div style="color: #ea580c; padding: 15px; text-align: center; font-weight: bold; width: 100%;">
                    Apenas artesãos (Ferreiro, Alfaiate, etc.) podem operar as fornalhas!
                </div>
            `;
            document.getElementById('lista-receitas-refinaria').innerHTML = '';
            document.getElementById('detalhe-receita-refinaria').style.display = 'none';
            document.getElementById('detalhe-vazio-refinaria').style.display = 'block';
            return;
        }

        this.desenharAbas();
        this.desenharLista();
        
        // Garante que fica em 100% quando não tem nada selecionado
        const painelLista = document.getElementById('painel-lista-forja');
        const painelDetalhes = document.getElementById('painel-detalhes-forja');
        if (painelLista && painelDetalhes) {
            painelDetalhes.style.setProperty('display', 'none', 'important');
            painelLista.style.setProperty('height', '100%', 'important');
            painelLista.style.setProperty('max-width', '100%', 'important');
            painelLista.style.setProperty('border', 'none', 'important');
        }
    },
    desenharLista() {
        const lista = document.getElementById('lista-receitas-refinaria');
        lista.innerHTML = '';
        const receitas = RefinariaEngine.getReceitasDaAbaAtual();

        Object.keys(receitas).forEach(id => {
            const r = receitas[id];
            // Para refino, a maioria vai pra pasta de materiais, mas verifica a chave principal
            const outputId = Object.keys(r.outputs || {})[0] || id; 
            const imgPath = `${GITHUB_BASE_ITENS}materiais/${outputId}.png`;

            const card = document.createElement('div');
            card.className = `recipe-card ${RefinariaEngine.receitaSelecionada === id ? 'active' : ''}`;
            card.innerHTML = `
                <img src="${imgPath}" class="card-icon" onerror="this.src='/static/assets/box.png'">
                <span class="recipe-name" title="${r.display_name}">${r.display_name}</span>
            `;
            
            card.onclick = () => {
                document.querySelectorAll('#lista-receitas-refinaria .recipe-card').forEach(el => el.classList.remove('active'));
                card.classList.add('active');
                RefinariaEngine.selecionarReceita(id);
            };
            lista.appendChild(card);
        });
    },

    atualizarDetalhes(id, receita) {
        if (!receita) return; 

        // Restaura a divisão de tela
        const painelLista = document.getElementById('painel-lista-forja');
        const painelDetalhes = document.getElementById('painel-detalhes-forja');
        if (painelLista && painelDetalhes) {
            painelDetalhes.style.setProperty('display', 'flex', 'important');
            painelLista.style.removeProperty('height');
            painelLista.style.removeProperty('max-width');
            painelLista.style.removeProperty('border');
        }

        document.getElementById('detalhe-vazio-refinaria').style.display = 'none';
        document.getElementById('detalhe-receita-refinaria').style.display = 'flex';
        
        // Trava de segurança caso a aba não tenha carregado a tempo
        const profKey = (RefinariaEngine.profSelecionada || 'ferreiro').toLowerCase();

        // Busca dados no perfil global
        const learned = window.perfilDadosGlobais.learned_professions || {};
        let profData = learned[profKey] || {};
    
        // Fallback para legado
        if (!profData.level && window.perfilDadosGlobais.profession?.key === profKey) {
            profData = window.perfilDadosGlobais.profession;
        }

        const myLvl = parseInt(profData.level || 1);
        const profXp = parseInt(profData.xp || 0);

        // Calcula o XP necessário para o próximo nível
        let xpNecessario = 40 + (25 * (myLvl - 1)) + (8 * Math.pow(myLvl - 1, 2));
        let displayXp = myLvl >= 50 ? "MÁX" : `${profXp} / ${xpNecessario}`;

        // Atualiza Nome, Nível e o XP visível na interface
        document.getElementById('nome-resultado-refinaria').innerHTML = `
            ${receita.display_name} 
            <small style="font-size:0.7em; color:#ea580c; display:block; margin-top: 3px;">
                ${profKey.toUpperCase()} Nível: ${myLvl} | XP: ${displayXp}
            </small>
        `;

        const reqEl = document.getElementById('nvl-req-refinaria');
        if (reqEl) reqEl.innerText = receita.level_req || 1;

        // Cálculo de Tempo
        const reduction = Math.min(0.5, (myLvl * 0.01));
        const baseTime = receita.time_seconds || 60;
        const estimatedTime = Math.max(1, Math.floor(baseTime * (1.0 - reduction)));

        const tempoEl = document.getElementById('tempo-unitario');
        if (tempoEl) {
            tempoEl.innerText = `${estimatedTime}s`;
            tempoEl.dataset.time = estimatedTime;
            tempoEl.dataset.profLevel = myLvl; 
        }

        // Imagem do item
        const outputId = Object.keys(receita.outputs || {})[0] || id;
        const imgElement = document.getElementById('img-resultado-refinaria');
        if (imgElement) {
            imgElement.src = `${GITHUB_BASE_ITENS}materiais/${outputId}.png`;
            imgElement.onerror = function() { this.src = '/static/assets/box.png'; };
        }

        this.renderizarInputs();
    },

    alterarQtd(delta) {
        let novaQtd = RefinariaEngine.quantidadeAtual + delta;
        this.aplicarNovaQtd(novaQtd);
    },

    setQtdMax() {
        this.aplicarNovaQtd(RefinariaEngine.quantidadeMaxima);
    },

    atualizarPorInput() {
        const val = parseInt(document.getElementById('input-qtd-refino').value) || 0;
        this.aplicarNovaQtd(val);
    },

    aplicarNovaQtd(valor) {
        let v = valor;
        if (v > RefinariaEngine.quantidadeMaxima) v = RefinariaEngine.quantidadeMaxima;
        if (v < 1 && RefinariaEngine.quantidadeMaxima > 0) v = 1;
        if (RefinariaEngine.quantidadeMaxima === 0) v = 0;

        RefinariaEngine.quantidadeAtual = v;
        this.renderizarInputs();
    },

    renderizarInputs() {
        const id = RefinariaEngine.receitaSelecionada;
        if (!id) return;
        const receita = RefinariaEngine.receitas[id];
        const qtd = RefinariaEngine.quantidadeAtual;
        
        document.getElementById('input-qtd-refino').value = qtd;
        
        const tempoUni = parseInt(document.getElementById('tempo-unitario').dataset.time);
        this.formatarTempoTotal(tempoUni * qtd);

        const p = window.perfilDadosGlobais;
        const inv = p.inventario || p.inventory || [];
        const grid = document.getElementById('lista-materiais-refinaria');
        grid.innerHTML = '';

        let podeCriar = qtd > 0;

        for (const [mat_id, req_unitario] of Object.entries(receita.inputs || {})) {
            // Se a quantidade estiver 0, mostramos o custo de 1 unidade.
            // Isso evita aparecer 4/0 na tela.
            const qtdVisual = qtd > 0 ? qtd : 1;
            const req_total = req_unitario * qtdVisual;

            const itemInv = inv.find(i => {
                const base = i.base_id || i.item_id || i.id;
                return String(base) === String(mat_id);
            });

            const tenho = itemInv
                ? Number(itemInv.qtd || itemInv.quantity || itemInv.quantidade || 0)
                : 0;
            
            if (tenho < req_total) podeCriar = false;

            const pill = document.createElement('div');
            pill.className = `mat-pill ${tenho < req_total ? 'missing' : ''}`;
            pill.innerHTML = `
                <div class="mat-info">
                    <img src="${GITHUB_BASE_ITENS}materiais/${mat_id}.png" style="width:24px; flex-shrink:0;" onerror="this.src='/static/assets/box.png'">
                    <span title="${mat_id.replace(/_/g, ' ')}">${mat_id.replace(/_/g, ' ')}</span>
                </div>
                <b style="flex-shrink:0;">${tenho}/${req_total}</b>
            `;
            grid.appendChild(pill);
        }

        document.getElementById('btn-iniciar-refino').disabled = !podeCriar;
    },

    formatarTempoTotal(segundos) {
        if (segundos === 0) {
            document.getElementById('tempo-total-refino').innerText = "0s";
            return;
        }
        let txt = "";
        const h = Math.floor(segundos / 3600);
        const m = Math.floor((segundos % 3600) / 60);
        const s = segundos % 60;
        
        if (h > 0) txt += `${h}h `;
        if (m > 0) txt += `${m}m `;
        if (s > 0 && h === 0) txt += `${s}s`; // Mostra segundos apenas se for menor que 1h
        
        document.getElementById('tempo-total-refino').innerText = txt.trim();
    }
};

window.mostrarLootFlutuante = function(cena, outputs, xpGanho) {
    let yOffset = 0;
    // Anima XP
    if (xpGanho > 0) {
        let txtXp = cena.add.text(cena.player.x, cena.player.y - 40, `+${xpGanho} XP`, {
            fontSize: '14px', fontFamily: 'Arial', color: '#fbbf24', stroke: '#000', strokeThickness: 3
        }).setOrigin(0.5).setDepth(300);
        cena.tweens.add({ targets: txtXp, y: txtXp.y - 60, alpha: 0, duration: 2000, onComplete: () => txtXp.destroy() });
        yOffset += 30;
    }
    // Anima Itens
    for (const [outputId, qtdObtida] of Object.entries(outputs)) {
        let lootContainer = cena.add.container(cena.player.x, cena.player.y - 40 + yOffset).setDepth(300);
        let bgBox = cena.add.graphics();
        bgBox.fillStyle(0x0f172a, 0.9);
        bgBox.lineStyle(1.5, 0xea580c, 1);
        bgBox.fillRoundedRect(-16, -16, 32, 32, 6);
        bgBox.strokeRoundedRect(-16, -16, 32, 32, 6);
        let icone = cena.add.sprite(0, 0, cena.textures.exists('loot_'+outputId) ? 'loot_'+outputId : 'box').setDisplaySize(24, 24);
        let txtQtd = cena.add.text(22, 0, `+${qtdObtida}`, { fontSize: '16px', color: '#4ade80', stroke: '#000', strokeThickness: 4 }).setOrigin(0, 0.5);
        lootContainer.add([bgBox, icone, txtQtd]);
        cena.tweens.add({ targets: lootContainer, y: lootContainer.y - 70, alpha: 0, duration: 2500, onComplete: () => lootContainer.destroy() });
        yOffset += 40;
    }
};

