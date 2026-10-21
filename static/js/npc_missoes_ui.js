// /static/js/npc_missoes_ui.js

class MotorDeMissoesNPC {
    constructor() {
        this.criarModal();
    }

    criarModal() {
        const estilo = document.createElement('style');
        estilo.innerHTML = `
            #modal-missao-npc {
                --missao-panel: #0b1b20;
                --missao-raised: #12252b;
                --missao-interactive: #183139;
                --missao-gold: #c9a45c;
                --missao-text: #f4ead2;
                --missao-muted: #b8c4c2;
                display: none; position: fixed; inset: 0; z-index: 10000;
                justify-content: center; align-items: center; padding: 14px;
                background: rgba(2, 9, 12, .76); backdrop-filter: blur(4px);
                font-family: Arial, sans-serif;
            }
            #modal-missao-npc * { box-sizing: border-box; }
            #modal-missao-npc .modal-missao-box {
                display: flex; flex-direction: column; width: min(100%, 470px);
                max-height: min(86dvh, 740px); overflow: hidden;
                background: var(--missao-panel); border: 1px solid rgba(201,164,92,.55);
                border-radius: 16px; color: var(--missao-text);
                box-shadow: 0 18px 54px rgba(0,0,0,.62), 0 0 0 1px rgba(255,255,255,.025) inset;
            }
            #modal-missao-npc .npc-header {
                display: flex; align-items: center; gap: 12px; flex: 0 0 auto;
                min-height: 82px; padding: 14px 16px;
                background: linear-gradient(110deg, #14243b, #10252b 72%);
                border-bottom: 1px solid rgba(201,164,92,.4);
            }
            #modal-missao-npc .npc-portrait {
                width: 52px; height: 52px; flex: 0 0 52px; margin: 0;
                object-fit: cover; border-radius: 50%; background: #091317;
                border: 1px solid var(--missao-gold); box-shadow: 0 3px 12px rgba(0,0,0,.35);
            }
            #modal-missao-npc .npc-identidade { min-width: 0; flex: 1; }
            #modal-missao-npc .npc-contexto {
                margin: 0 0 3px; color: var(--missao-muted); font: 700 10px/1.2 Arial,sans-serif;
                letter-spacing: 1.3px; text-transform: uppercase;
            }
            #modal-missao-npc .npc-nome {
                margin: 0; color: var(--missao-text); font: 700 clamp(17px, 5vw, 21px)/1.2 'Cinzel', Georgia, serif;
                text-shadow: 0 2px 4px rgba(0,0,0,.4);
            }
            #modal-missao-npc .npc-fechar {
                display: grid; place-items: center; width: 44px; height: 44px; flex: 0 0 44px;
                padding: 0; border: 1px solid rgba(211,190,132,.3); border-radius: 10px;
                background: rgba(11,27,32,.72); color: var(--missao-text); font: 24px/1 Arial,sans-serif;
                cursor: pointer; transition: background .16s ease, border-color .16s ease;
            }
            #modal-missao-npc .npc-fechar:hover, #modal-missao-npc .npc-fechar:focus-visible {
                background: var(--missao-interactive); border-color: var(--missao-gold); outline: 2px solid transparent;
            }
            #modal-missao-npc #missao-conteudo {
                min-height: 0; overflow-y: auto; overscroll-behavior: contain; padding: 18px 18px 20px;
                scrollbar-color: rgba(201,164,92,.65) transparent; scrollbar-width: thin;
            }
            #modal-missao-npc .missao-titulo {
                margin: 0 0 8px; color: var(--missao-text); font: 700 19px/1.25 'Cinzel', Georgia, serif;
            }
            #modal-missao-npc .missao-desc {
                margin: 0 0 16px; color: #d6dfdc; font: 15px/1.5 Arial,sans-serif;
            }
            #modal-missao-npc .missao-escolhas {
                margin: 0 0 12px; padding: 10px; border: 1px solid rgba(211,190,132,.24);
                border-radius: 12px; background: rgba(7,18,22,.62);
            }
            #modal-missao-npc .missao-escolhas legend {
                padding: 0 7px; color: var(--missao-gold); font: 700 11px/1.2 Arial,sans-serif;
                letter-spacing: 1.1px; text-transform: uppercase;
            }
            #modal-missao-npc .missao-escolha {
                display: flex; align-items: center; gap: 11px; min-height: 58px; width: 100%;
                margin: 5px 0; padding: 10px 11px; border: 1px solid rgba(211,190,132,.2);
                border-radius: 9px; background: var(--missao-raised); color: var(--missao-text);
                cursor: pointer; text-align: left; font: inherit; transition: background .15s ease, border-color .15s ease;
            }
            #modal-missao-npc .missao-escolha:hover { background: var(--missao-interactive); border-color: rgba(201,164,92,.58); }
            #modal-missao-npc .missao-escolha:focus-within { border-color: var(--missao-gold); outline: 2px solid rgba(201,164,92,.25); }
            #modal-missao-npc .missao-escolha:has(input:checked) {
                background: #1b3538; border-color: var(--missao-gold); box-shadow: inset 3px 0 var(--missao-gold);
            }
            #modal-missao-npc .missao-escolha input {
                appearance: none; display: grid; place-items: center; width: 20px; height: 20px; flex: 0 0 20px;
                margin: 0; border: 1px solid #8f9a96; border-radius: 50%; background: #091317; cursor: pointer;
            }
            #modal-missao-npc .missao-escolha input::before {
                content: ''; width: 9px; height: 9px; border-radius: 50%; background: var(--missao-gold);
                transform: scale(0); transition: transform .12s ease;
            }
            #modal-missao-npc .missao-escolha input:checked { border-color: var(--missao-gold); }
            #modal-missao-npc .missao-escolha input:checked::before { transform: scale(1); }
            #modal-missao-npc .missao-escolha span { display: grid; gap: 3px; }
            #modal-missao-npc .missao-escolha strong { color: var(--missao-text); font: 700 14px/1.25 Arial,sans-serif; }
            #modal-missao-npc .missao-escolha small { color: var(--missao-muted); font: 12px/1.35 Arial,sans-serif; }
            #modal-missao-npc .missao-escolha-nota { margin: 8px 2px 14px; color: var(--missao-muted); font: 12px/1.4 Arial,sans-serif; }
            #modal-missao-npc .missao-acoes { display: grid; gap: 8px; margin-top: 14px; }
            #modal-missao-npc .btn-missao {
                display: block; width: 100%; min-height: 46px; margin: 0; padding: 11px 14px;
                border: 1px solid transparent; border-radius: 9px; background: linear-gradient(180deg,#d3b16a,#b68b3d);
                color: #172126; font: 700 13px/1.2 'Cinzel', Georgia, serif; letter-spacing: .35px;
                cursor: pointer; transition: filter .15s ease, transform .15s ease;
            }
            #modal-missao-npc .btn-missao:hover:not(:disabled) { filter: brightness(1.08); }
            #modal-missao-npc .btn-missao:active:not(:disabled) { transform: translateY(1px); }
            #modal-missao-npc .btn-missao:focus-visible { outline: 2px solid #f4ead2; outline-offset: 2px; }
            #modal-missao-npc .btn-missao:disabled { opacity: .48; cursor: not-allowed; filter: saturate(.55); }
            #modal-missao-npc .btn-fechar-missao {
                background: #12252b; color: var(--missao-muted); border-color: rgba(211,190,132,.24);
            }
            #modal-missao-npc .btn-fechar-missao:hover { background: var(--missao-interactive); color: var(--missao-text); }
            #modal-missao-npc .recompensas-box {
                margin: 0 0 14px; padding: 12px; border: 1px solid rgba(211,190,132,.2);
                border-left: 3px solid #65cf72; border-radius: 8px; background: var(--missao-raised);
                color: #d7ead8; font: 13px/1.5 Arial,sans-serif;
            }
            #modal-missao-npc .loader-magico { padding: 24px 10px; color: var(--missao-muted); text-align: center; font: 700 14px Arial,sans-serif; }
            @media (max-height: 620px) {
                #modal-missao-npc { padding: 8px; }
                #modal-missao-npc .modal-missao-box { max-height: 94dvh; }
                #modal-missao-npc .npc-header { min-height: 68px; padding: 9px 12px; }
                #modal-missao-npc .npc-portrait { width: 46px; height: 46px; flex-basis: 46px; }
                #modal-missao-npc #missao-conteudo { padding: 13px 14px 16px; }
            }
        `;
        document.head.appendChild(estilo);

        const div = document.createElement('div');
        div.id = 'modal-missao-npc';
        div.className = 'modal-missao-overlay';
        div.innerHTML = `
            <div class="modal-missao-box" role="dialog" aria-modal="true" aria-labelledby="npc-nome-missao">
                <div class="npc-header">
                    <img id="npc-img-missao" class="npc-portrait" src="">
                    <div class="npc-identidade">
                        <p class="npc-contexto">Jornada de Eldora</p>
                        <h2 id="npc-nome-missao" class="npc-nome">Nome</h2>
                    </div>
                    <button class="npc-fechar" type="button" aria-label="Fechar missões" title="Fechar"
                        onclick="window.motorMissoesNPC.fecharModal()">×</button>
                </div>
                <div id="missao-conteudo" tabindex="0">
                </div>
            </div>
        `;
        document.body.appendChild(div);
        div.addEventListener('click', event => {
            if (event.target === div) this.fecharModal();
        });
        document.addEventListener('keydown', event => {
            if (event.key === 'Escape' && div.style.display === 'flex') this.fecharModal();
        });
    }

    fecharModal() {
        const modal = document.getElementById('modal-missao-npc');
        if (modal) modal.style.display = 'none';
    }

    async interagir(npc_id, nome_npc, url_imagem) {
        this.escolhaSelecionada = null;
        const modal = document.getElementById('modal-missao-npc');
        document.getElementById('npc-img-missao').src = url_imagem;
        document.getElementById('npc-nome-missao').innerText = nome_npc;
        const conteudo = document.getElementById('missao-conteudo');
        
        conteudo.innerHTML = `<div class="loader-magico">Consultando os astros... ⏳</div>`;
        modal.style.display = 'flex';
        requestAnimationFrame(() => document.querySelector('#modal-missao-npc .npc-fechar')?.focus());

        const userId = localStorage.getItem("jogadorEldoraID");
        
        try {
            const res = await fetch(`/api/npc/${npc_id}/status?user_id=${userId}`);
            const data = await res.json();
            
            if (data.success) {
                this.notificarMissoesProntas(data.status);
                this.renderizarMissao(data.status, npc_id, nome_npc, url_imagem);
            } else {
                conteudo.innerHTML = `
                    <p style="color:#ef4444; font-family: Arial;">${data.error}</p>
                    <button class="btn-missao btn-fechar-missao" onclick="document.getElementById('modal-missao-npc').style.display='none'">FECHAR</button>
                `;
            }
        } catch (e) {
            conteudo.innerHTML = `
                <p style="color:#ef4444; font-family: Arial;">Os ventos de mana falharam. Erro de conexão com o servidor.</p>
                <button class="btn-missao btn-fechar-missao" onclick="document.getElementById('modal-missao-npc').style.display='none'">FECHAR</button>
            `;
        }
    }

    renderizarMissao(status, npc_id, nome_npc, url_imagem) {
        const conteudo = document.getElementById('missao-conteudo');
        conteudo.innerHTML = '';

        // A alma e o foco espiritual só surgem depois dos três abates da caravana.
        const decisaoCaravana = [...(status.prontas_para_entrega || []), ...(status.em_andamento || [])]
            .find(m => m.id === 'q3_varek_provacao' && m.data?.decisao_ativa)?.data?.decisao_ativa;
        if (decisaoCaravana) {
            conteudo.innerHTML = `
                <h3 class="missao-titulo" style="color:#c084fc">✦ ${decisaoCaravana.etapa === 'alma_guardiao' ? 'A VOZ NA ESTRADA' : 'O FOCO ESPIRITUAL'}</h3>
                <p class="missao-desc">${decisaoCaravana.pergunta}</p>
                <fieldset class="missao-escolhas">
                    <legend>Como você responde?</legend>
                    ${decisaoCaravana.escolhas.map(escolha => `
                        <button class="missao-escolha" type="button" style="width:100%;text-align:left;color:#f4ead2"
                            onclick="window.motorMissoesNPC.registrarDecisao('${decisaoCaravana.etapa}','${escolha.id}','${npc_id}','${nome_npc}','${url_imagem}')">
                            <span><strong>${escolha.titulo}</strong><small>${escolha.descricao}</small></span>
                        </button>
                    `).join('')}
                </fieldset>
                <p class="missao-escolha-nota">A estrada guardará sua resposta para o encontro com Selene.</p>
            `;
            return;
        }

        // 🚨 O BYPASS DA MISSÃO DE CLASSE (COM A INTERFACE ÉPICA) 🚨
        let missaoClasse = status.prontas_para_entrega.find(m => m.id === 'q4_selene_classe') 
                        || status.disponiveis.find(m => m.id === 'q4_selene_classe');

        if (missaoClasse) {
            const necromanteRevelado = status.jornada?.necromante_revelado === true;
            conteudo.innerHTML = `
                <h3 class="missao-titulo" style="color: #c084fc; text-align: center;">✨ O DESPERTAR DA CENTELHA</h3>
                <p class="missao-desc" style="text-align: center;">${necromanteRevelado
                    ? 'A voz que acompanhou sua jornada finalmente se revela. Selene sente em você a Centelha do Necromante: um vínculo raro com as almas que ainda não encontraram descanso. As outras classes continuam disponíveis; essa descoberta não escolhe por você.'
                    : 'Sua Centelha despertou. Fale com a Arquimaga para escolher um caminho. A presença ouvida na estrada silencia, mas Selene percebe que algo ainda espera por você.'}</p>
                ${necromanteRevelado ? '<div class="recompensas-box" style="border-left-color:#a855f7;color:#e9d5ff"><strong>CAMINHO REVELADO: NECROMANTE</strong><br><br>Você escutou a alma do guardião e acolheu as vozes sem abandonar os sobreviventes. Selene reconhece essa afinidade.</div>' : ''}
                
                <button class="btn-missao" style="background: linear-gradient(to bottom, #a855f7, #7e22ce); color: white;" onclick="document.getElementById('modal-missao-npc').style.display='none'; window.abrirModalClasses(${necromanteRevelado});">
                    VER CAMINHOS DO DESPERTAR
                </button>
                <button class="btn-missao btn-fechar-missao" onclick="document.getElementById('modal-missao-npc').style.display='none'">
                    AINDA NÃO ESTOU PRONTO
                </button>
            `;
            return; 
        }

        const classeAtual = String(
            window.perfilDadosGlobais?.class_key
            || window.perfilDadosGlobais?.class
            || window.perfilDadosGlobais?.classe
            || ''
        ).toLowerCase();
        if (npc_id === 'selene_arquimaga' && status.jornada?.necromante_desbloqueado === true && classeAtual !== 'necromante') {
            conteudo.innerHTML = `
                <h3 class="missao-titulo" style="color:#c084fc;text-align:center">✦ O RITUAL DAS ALMAS</h3>
                <p class="missao-desc" style="text-align:center">O eco das Catacumbas encontrou você. Selene pode conduzir o despertar do Necromante; seu caminho atual será preservado até você aceitar a mudança.</p>
                <div class="recompensas-box" style="border-left-color:#a855f7;color:#e9d5ff"><strong>RITUAL CONCLUÍDO</strong><br><br>A Centelha do Necromante está disponível para você.</div>
                <button class="btn-missao" style="background:linear-gradient(to bottom,#a855f7,#7e22ce);color:white" onclick="document.getElementById('modal-missao-npc').style.display='none';window.abrirModalClasses(true)">ESCOLHER O NECROMANTE</button>
                <button class="btn-missao btn-fechar-missao" onclick="document.getElementById('modal-missao-npc').style.display='none'">CONTINUAR MEU CAMINHO</button>
            `;
            return;
        }

        // Prioridade 1: Missões prontas para entrega
        if (status.prontas_para_entrega.length > 0) {
            const m = status.prontas_para_entrega[0];
            let htmlRecompensas = '';
            
            if (m.data.recompensas) {
                htmlRecompensas = '<div class="recompensas-box"><strong>RECOMPENSAS:</strong><br><br>';
                if (m.data.recompensas.xp) htmlRecompensas += `✨ ${m.data.recompensas.xp} Experiência<br>`;
                if (m.data.recompensas.gold) htmlRecompensas += `🪙 ${m.data.recompensas.gold} Ouro<br>`;
                if (m.data.recompensas.itens) {
                    for (const [item, qtd] of Object.entries(m.data.recompensas.itens)) {
                        const nomeBonito = item.replace(/_/g, ' ').toUpperCase();
                        htmlRecompensas += `📦 ${nomeBonito} x${qtd}<br>`;
                    }
                }
                htmlRecompensas += '</div>';
            }

            conteudo.innerHTML = `
                <h3 class="missao-titulo">✅ ${m.data.titulo}</h3>
                <p class="missao-desc">Excelente trabalho. Você trouxe o que eu pedi?</p>
                ${htmlRecompensas}
                <button class="btn-missao" onclick="window.motorMissoesNPC.entregar('${m.id}', '${npc_id}', '${nome_npc}', '${url_imagem}')">PRESTAR CONTAS</button>
                <button class="btn-missao btn-fechar-missao" onclick="document.getElementById('modal-missao-npc').style.display='none'">VOLTAR DEPOIS</button>
            `;
            return;
        }

        // =========================================================
        // PRIORIDADE 2: MISSÃO EM ANDAMENTO
        // =========================================================

        const missoesEmAndamento =
            Array.isArray(status.em_andamento)
                ? status.em_andamento
                : [];

        if (missoesEmAndamento.length > 0) {

            const m = missoesEmAndamento[0];

            let htmlProgresso = '';

            if (m.progresso_nivel) {
                htmlProgresso += `
                    <div class="recompensas-box">
                        <strong>🌟 PREPARAÇÃO DO HERÓI</strong><br><br>
                        Nível ${m.progresso_nivel.atual}/${m.progresso_nivel.necessario}
                    </div>
                `;
            }

            if (m.progresso_profissao && !m.progresso_profissao.concluido) {
                htmlProgresso += `
                    <div class="recompensas-box" style="border-left-color:#c9a45c">
                        <strong>🛠️ ESCOLHA SEU OFÍCIO</strong><br><br>
                        Fale com Mestre Thorek e escolha uma profissão. Depois, volte aqui para concluir esta etapa.
                    </div>
                `;
            }

            if (m.progresso_evento) {
                htmlProgresso += `
                    <div class="recompensas-box">
                        <strong>🛡️ ${m.progresso_evento.nome.toUpperCase()}</strong><br><br>
                        ${m.progresso_evento.atual}/${m.progresso_evento.necessario} derrotados
                    </div>
                `;
            }

            // =====================================================
            // ⚔️ PROGRESSO DE ABATES
            // =====================================================

            const progressoAbates =
                m.progresso_abates || {};

            const listaAbates =
                Object.values(progressoAbates);

            if (listaAbates.length > 0) {

                htmlProgresso += `
                    <div class="recompensas-box">
                        <strong>⚔️ PROGRESSO DA PROVAÇÃO</strong>
                        <br><br>
                `;

                for (const alvo of listaAbates) {

                    const concluido =
                        alvo.concluido === true;

                    const icone =
                        concluido
                            ? '✅'
                            : '⚔️';

                    const cor =
                        concluido
                            ? '#34d399'
                            : '#facc15';

                    htmlProgresso += `
                        <div style="
                            display:flex;
                            justify-content:space-between;
                            align-items:center;
                            gap:10px;
                            margin:7px 0;
                            color:${cor};
                        ">
                            <span>
                                ${icone}
                                ${alvo.nome}
                            </span>

                            <strong>
                                ${alvo.atual}/${alvo.necessario}
                            </strong>
                        </div>
                    `;
                }

                htmlProgresso += `
                    </div>
                `;
            }

            // =====================================================
            // 📦 PROGRESSO DE ITENS
            // =====================================================

            const progressoItens =
                m.progresso_itens || {};

            const listaItens =
                Object.entries(progressoItens);

            if (listaItens.length > 0) {

                htmlProgresso += `
                    <div class="recompensas-box">
                        <strong>📦 MATERIAIS</strong>
                        <br><br>
                `;

                for (const [itemId, item] of listaItens) {

                    const concluido =
                        item.concluido === true;

                    const nomeBonito =
                        itemId
                            .replace(/_/g, ' ')
                            .replace(/\b\w/g, letra =>
                                letra.toUpperCase()
                            );

                    const icone =
                        concluido
                            ? '✅'
                            : '📦';

                    const cor =
                        concluido
                            ? '#34d399'
                            : '#facc15';

                    htmlProgresso += `
                        <div style="
                            display:flex;
                            justify-content:space-between;
                            align-items:center;
                            gap:10px;
                            margin:7px 0;
                            color:${cor};
                        ">
                            <span>
                                ${icone}
                                ${nomeBonito}
                            </span>

                            <strong>
                                ${item.atual}/${item.necessario}
                            </strong>
                        </div>
                    `;
                }

                htmlProgresso += `
                    </div>
                `;
            }

            conteudo.innerHTML = `
                <h3 class="missao-titulo">
                    ⚔️ ${m.data.titulo}
                </h3>

                <p class="missao-desc">
                    ${m.data.objetivo}
                </p>

                ${m.data.regiao_nome ? `
                    <div style="
                        text-align:center;
                        padding:8px;
                        margin-bottom:12px;
                        border:1px solid #475569;
                        border-radius:6px;
                        background:rgba(15,23,42,0.7);
                        color:#93c5fd;
                        font-family:Arial,sans-serif;
                        font-size:14px;
                    ">
                        🗺️ Destino:
                        <strong>${m.data.regiao_nome}</strong>
                    </div>
                ` : ''}

                ${htmlProgresso}

                ${m.id === 'q5_thorek_profissao' && m.progresso_profissao?.concluido !== true ? `
                    <button class="btn-missao" onclick="window.abrirModalProfissoes?.('thorek')">ESCOLHER OFÍCIO COM THOREK</button>
                ` : ''}

                <p style="
                    color:#94a3b8;
                    font-family:Arial,sans-serif;
                    font-size:13px;
                    text-align:center;
                    line-height:1.4;
                ">
                    Complete todos os objetivos e depois retorne.
                </p>

                <button
                    class="btn-missao btn-fechar-missao"
                    onclick="
                        document
                            .getElementById('modal-missao-npc')
                            .style.display='none'
                    "
                >
                    CONTINUAR A JORNADA
                </button>
            `;

            return;
        }

        // =========================================================
        // PRIORIDADE 3: MISSÕES NOVAS PARA ACEITAR
        // =========================================================

        const missoesDisponiveis =
            Array.isArray(status.disponiveis)
                ? status.disponiveis
                : [];

        if (missoesDisponiveis.length > 0) {

            const m =
                missoesDisponiveis[0];

            const escolhas = Array.isArray(m.data.escolhas)
                ? m.data.escolhas
                : [];
            this.escolhaSelecionada = null;
            const htmlEscolhas = escolhas.length
                ? `<fieldset class="missao-escolhas">
                    <legend>Como você responde?</legend>
                    ${escolhas.map(escolha => `
                        <label class="missao-escolha">
                            <input type="radio" name="escolha-missao" value="${escolha.id}"
                                onchange="window.motorMissoesNPC.selecionarEscolha('${escolha.id}')">
                            <span><strong>${escolha.titulo}</strong><small>${escolha.descricao}</small></span>
                        </label>
                    `).join('')}
                    <p class="missao-escolha-nota">Sua resposta fica registrada na jornada. Ela não escolhe uma classe por você.</p>
                </fieldset>`
                : '';

            const aceiteDesabilitado = escolhas.length ? 'disabled' : '';

            conteudo.innerHTML = `
                <h3 class="missao-titulo">
                    📜 ${m.data.titulo}
                </h3>

                <p class="missao-desc">
                    ${m.data.objetivo}
                </p>

                ${m.data.regiao_nome ? `
                    <div style="
                        text-align:center;
                        padding:8px;
                        margin-bottom:12px;
                        border:1px solid #475569;
                        border-radius:6px;
                        background:rgba(15,23,42,0.7);
                        color:#93c5fd;
                        font-family:Arial,sans-serif;
                        font-size:14px;
                    ">
                        🗺️ Destino:
                        <strong>${m.data.regiao_nome}</strong>
                    </div>
                ` : ''}

                ${htmlEscolhas}

                <div class="missao-acoes">
                    <button
                        class="btn-missao"
                        id="btn-aceitar-missao"
                        ${aceiteDesabilitado}
                        onclick="
                            window.motorMissoesNPC.aceitar(
                                '${m.id}',
                                '${npc_id}',
                                '${nome_npc}',
                                '${url_imagem}',
                                window.motorMissoesNPC.escolhaSelecionada
                            )
                        "
                    >
                        ${escolhas.length ? 'ESCOLHA UMA RESPOSTA' : 'ACEITAR MISSÃO'}
                    </button>

                    <button
                        class="btn-missao btn-fechar-missao"
                        onclick="window.motorMissoesNPC.fecharModal()"
                    >
                        VOLTAR AO MAPA
                    </button>
                </div>
            `;

            return;
        }

        const missaoBloqueada = Array.isArray(status.bloqueadas)
            ? status.bloqueadas[0]
            : null;
        if (missaoBloqueada) {
            if (missaoBloqueada.tipo === 'profissao') {
                conteudo.innerHTML = `
                    <h3 class="missao-titulo">📜 ${missaoBloqueada.data.titulo}</h3>
                    <p class="missao-desc">Antes de romper os selos do Grimório, escolha um ofício com Mestre Thorek e retorne à Arquimaga Selene.</p>
                    <button class="btn-missao btn-fechar-missao" onclick="document.getElementById('modal-missao-npc').style.display='none'">VOLTAR À JORNADA</button>
                `;
                return;
            }
            conteudo.innerHTML = `
                <h3 class="missao-titulo">📜 ${missaoBloqueada.data.titulo}</h3>
                <p class="missao-desc">${missaoBloqueada.data.objetivo}</p>
                <div class="recompensas-box">Seu nível: <strong>${missaoBloqueada.nivel_atual}</strong><br>Necessário: <strong>Nível ${missaoBloqueada.nivel_necessario}</strong></div>
                <button class="btn-missao btn-fechar-missao" onclick="document.getElementById('modal-missao-npc').style.display='none'">VOLTAR À JORNADA</button>
            `;
            return;
        }

        // Selene só orienta a etapa seguinte quando a etapa anterior foi
        // realmente concluída no servidor. Isso evita o diálogo antigo que
        // encaminhava o jogador à próxima missão apenas por atingir o nível.
        let falaSemMissao = '"O firmamento está calmo hoje. Continue sua jornada, retorne quando estiver mais experiente."';
        if (npc_id === 'selene_arquimaga') {
            if (status.jornada?.caravana_concluida !== true) {
                falaSemMissao = '"O Capitão Varek ainda precisa concluir seu relato da caravana. Volte a falar com ele quando a estrada estiver segura."';
            } else if (status.jornada?.classe_desperta === true && status.jornada?.profissao_concluida !== true) {
                falaSemMissao = '"Sua Centelha já despertou. Agora procure Mestre Thorek; a próxima etapa começa quando ele registrar seu ofício."';
            } else if (status.jornada?.profissao_concluida === true) {
                falaSemMissao = '"Seu caminho continua aberto. Quando houver um novo selo para romper, eu chamarei você."';
            }
        }

        // Prioridade 4: Sem missões no momento
        conteudo.innerHTML = `
            <p class="missao-desc" style="text-align:center;">
                ${falaSemMissao}
            </p>
            <button class="btn-missao btn-fechar-missao" onclick="document.getElementById('modal-missao-npc').style.display='none'">DESPEDIR-SE</button>
        `;
    }

    notificarMissoesProntas(status) {
        const prontas = Array.isArray(status?.prontas_para_entrega)
            ? status.prontas_para_entrega
            : [];
        if (!prontas.length || typeof window.alertaEldora !== 'function') return;

        const missao = prontas[0];
        const usuario = localStorage.getItem('jogadorEldoraID') || 'anonimo';
        const chave = `eldora-missao-pronta-${usuario}-${missao.id}`;
        if (localStorage.getItem(chave) === '1') return;
        localStorage.setItem(chave, '1');
        window.alertaEldora(
            'Objetivo concluído',
            `Você cumpriu os requisitos de “${missao.data.titulo}”. Fale com ${document.getElementById('npc-nome-missao')?.textContent || 'o NPC'} para prestar contas.`,
            'sucesso'
        );
    }

    selecionarEscolha(escolhaId) {
        this.escolhaSelecionada = escolhaId;
        const botao = document.getElementById('btn-aceitar-missao');
        if (botao) {
            botao.disabled = false;
            botao.textContent = 'ACEITAR MISSÃO';
        }
    }

    async registrarDecisao(etapa, escolha_id, npc_id, nome_npc, url_imagem) {
        const userId = localStorage.getItem('jogadorEldoraID');
        const botoes = document.querySelectorAll('.missao-escolha');
        botoes.forEach(botao => botao.disabled = true);
        try {
            const res = await fetch('/api/npc/missao/decidir', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ user_id: userId, etapa, escolha_id })
            });
            const data = await res.json();
            if (!data.success) throw new Error(data.error || 'Não foi possível registrar a escolha.');
            if (typeof window.alertaEldora === 'function') window.alertaEldora('A estrada se lembra', data.message, 'sucesso');
            if (typeof window.carregarMeuPerfil === 'function') await window.carregarMeuPerfil();
            await this.interagir(npc_id, nome_npc, url_imagem);
        } catch (error) {
            if (typeof window.alertaEldora === 'function') window.alertaEldora('A presença resiste', error.message, 'erro');
            else window.avisoEldora(error.message);
            botoes.forEach(botao => botao.disabled = false);
        }
    }

    async aceitar(quest_id, npc_id, nome_npc, url_imagem, escolha_id = null) {
        const userId = localStorage.getItem("jogadorEldoraID");
        
        const res = await fetch('/api/npc/missao/aceitar', {
            method: 'POST', 
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: userId, quest_id: quest_id, escolha_id })
        });
        const data = await res.json();
        
        if (data.success) {
            if (typeof window.alertaEldora === 'function') {
                window.alertaEldora(
                    "Missão Aceita!",
                    data.message,
                    "sucesso"
                );
            } else {
                window.avisoEldora(data.message);
            }

            // =====================================================
            // 🔄 SINCRONIZA A CAMPANHA COM O PERFIL GLOBAL
            // =====================================================
            //
            // A missão acabou de ser criada no MongoDB.
            // O Diário e os NPCs usam perfilDadosGlobais,
            // portanto precisamos atualizar essa memória.
            // =====================================================

            if (
                typeof window.carregarMeuPerfil
                === 'function'
            ) {
                await window.carregarMeuPerfil();
            }

            await this.interagir(
                npc_id,
                nome_npc,
                url_imagem
            );

        } else {
            if (typeof window.alertaEldora === 'function') window.alertaEldora("Erro", data.error, "erro");
            else window.avisoEldora(data.error);
        }
    }

    async entregar(quest_id, npc_id, nome_npc, url_imagem) {
        const userId = localStorage.getItem("jogadorEldoraID");
        const botoes = document.querySelectorAll('.btn-missao');
        botoes.forEach(b => b.style.pointerEvents = 'none');

        const res = await fetch('/api/npc/missao/entregar', {
            method: 'POST', 
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: userId, quest_id: quest_id })
        });
        const data = await res.json();
        
        if (data.success) {
            if (typeof window.alertaEldora === 'function') {
                window.alertaEldora("Sucesso!", data.message, "sucesso");
            } else {
                window.avisoEldora(data.message);
            }
            
            if (typeof window.carregarMeuPerfil === 'function') {
                await window.carregarMeuPerfil();
            }

            const usuario = localStorage.getItem('jogadorEldoraID') || 'anonimo';
            localStorage.removeItem(`eldora-missao-pronta-${usuario}-${quest_id}`);

            this.interagir(npc_id, nome_npc, url_imagem);
        } else {
            if (typeof window.alertaEldora === 'function') {
                window.alertaEldora("Aviso", data.error, "erro");
            } else {
                window.avisoEldora(data.error);
            }
            botoes.forEach(b => b.style.pointerEvents = 'auto');
        }
    }

    async escolherClasseDespertar(quest_id, npc_id, nome_npc, url_imagem) {
        const userId = localStorage.getItem("jogadorEldoraID");
        const classeEscolhida = document.getElementById('select-nova-classe').value;
        const nomeClasseTexto = document.getElementById('select-nova-classe').options[document.getElementById('select-nova-classe').selectedIndex].text.split(' ')[0];

        document.getElementById('modal-missao-npc').style.display = 'none';

        const res = await fetch('/api/npc/missao/despertar', {
            method: 'POST', 
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: userId, quest_id: quest_id, nova_classe: classeEscolhida })
        });
        
        const data = await res.json();
        
        if (data.success) {
            if (typeof window.animarDespertarClasse === 'function') {
                window.animarDespertarClasse(nomeClasseTexto, () => {
                    if (typeof window.carregarMeuPerfil === 'function') window.carregarMeuPerfil();
                    if (window.eldoraSocket) window.eldoraSocket.emit('efeito_global', { tipo: 'despertar', jogador: localStorage.getItem("jogadorEldoraNome"), classe: nomeClasseTexto });
                });
            }
        } else {
            window.avisoEldora("Falha mágica: " + data.error);
        }
    }
}

window.motorMissoesNPC = new MotorDeMissoesNPC();
