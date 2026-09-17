// /static/js/npc_missoes_ui.js

class MotorDeMissoesNPC {
    constructor() {
        this.criarModal();
    }

    criarModal() {
        const estilo = document.createElement('style');
        estilo.innerHTML = `
            .modal-missao-overlay {
                display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%;
                background: rgba(0,0,0,0.85); z-index: 10000; justify-content: center; align-items: center;
                backdrop-filter: blur(3px);
            }
            .modal-missao-box {
                background: linear-gradient(to bottom, #1e293b, #0f172a);
                border: 3px solid #d4af37; border-radius: 12px; width: 90%; max-width: 420px;
                padding: 20px; color: #fff; font-family: 'Cinzel', serif; 
                box-shadow: 0 0 30px rgba(212, 175, 55, 0.3);
            }
            .npc-header { 
                display: flex; align-items: center; border-bottom: 2px solid #d4af37; 
                padding-bottom: 15px; margin-bottom: 20px; 
            }
            .npc-portrait { 
                width: 70px; height: 70px; border: 2px solid #d4af37; border-radius: 50%; 
                margin-right: 15px; background: #000; object-fit: cover;
                box-shadow: 0 0 10px #d4af37;
            }
            .npc-nome { font-size: 22px; font-weight: 900; color: #facc15; margin: 0; text-shadow: 2px 2px 4px #000; }
            .missao-titulo { font-size: 19px; color: #60a5fa; margin-bottom: 10px; font-weight: bold; }
            .missao-desc { 
                font-size: 15px; color: #e2e8f0; margin-bottom: 20px; 
                font-family: Arial, sans-serif; line-height: 1.5; 
            }
            .btn-missao { 
                display: block; width: 100%; padding: 12px; margin-top: 10px; 
                background: linear-gradient(to bottom, #d4af37, #b48608); 
                color: #000; border: none; font-weight: 900; cursor: pointer; 
                border-radius: 6px; font-family: 'Cinzel', serif; font-size: 16px;
                text-transform: uppercase; transition: 0.2s;
            }
            .btn-missao:hover { filter: brightness(1.2); }
            .btn-fechar-missao { background: linear-gradient(to bottom, #ef4444, #b91c1c); color: #fff; }
            .recompensas-box { 
                background: rgba(0,0,0,0.6); padding: 12px; border-radius: 6px; 
                font-family: Arial, sans-serif; font-size: 14px; color: #a7f3d0; 
                margin-bottom: 20px; border-left: 3px solid #34d399;
            }
            .loader-magico { text-align: center; color: #a855f7; font-weight: bold; padding: 20px; }
        `;
        document.head.appendChild(estilo);

        const div = document.createElement('div');
        div.id = 'modal-missao-npc';
        div.className = 'modal-missao-overlay';
        div.innerHTML = `
            <div class="modal-missao-box">
                <div class="npc-header">
                    <img id="npc-img-missao" class="npc-portrait" src="">
                    <h2 id="npc-nome-missao" class="npc-nome">Nome</h2>
                </div>
                <div id="missao-conteudo">
                </div>
            </div>
        `;
        document.body.appendChild(div);
    }

    async interagir(npc_id, nome_npc, url_imagem) {
        const modal = document.getElementById('modal-missao-npc');
        document.getElementById('npc-img-missao').src = url_imagem;
        document.getElementById('npc-nome-missao').innerText = nome_npc;
        const conteudo = document.getElementById('missao-conteudo');
        
        conteudo.innerHTML = `<div class="loader-magico">Consultando os astros... ⏳</div>`;
        modal.style.display = 'flex';

        const userId = localStorage.getItem("jogadorEldoraID");
        
        try {
            const res = await fetch(`/api/npc/${npc_id}/status?user_id=${userId}`);
            const data = await res.json();
            
            if (data.success) {
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

        // 🚨 O BYPASS DA MISSÃO DE CLASSE (COM A INTERFACE ÉPICA) 🚨
        let missaoClasse = status.prontas_para_entrega.find(m => m.id === 'q4_selene_classe') 
                        || status.disponiveis.find(m => m.id === 'q4_selene_classe');

        if (missaoClasse) {
            conteudo.innerHTML = `
                <h3 class="missao-titulo" style="color: #c084fc; text-align: center;">✨ O DESPERTAR DA MANA</h3>
                <p class="missao-desc" style="text-align: center;">Seu corpo suportou a provação. Fale com a Arquimaga para escolher o caminho que guiará seu destino em Eldora.</p>
                
                <button class="btn-missao" style="background: linear-gradient(to bottom, #a855f7, #7e22ce); color: white;" onclick="document.getElementById('modal-missao-npc').style.display='none'; window.abrirModalClasses();">
                    VER CAMINHOS DO DESPERTAR
                </button>
                <button class="btn-missao btn-fechar-missao" onclick="document.getElementById('modal-missao-npc').style.display='none'">
                    AINDA NÃO ESTOU PRONTO
                </button>
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
                <button class="btn-missao" onclick="window.motorMissoesNPC.entregar('${m.id}', '${npc_id}', '${nome_npc}', '${url_imagem}')">ENTREGAR ITENS</button>
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

                <button
                    class="btn-missao"
                    onclick="
                        window.motorMissoesNPC.aceitar(
                            '${m.id}',
                            '${npc_id}',
                            '${nome_npc}',
                            '${url_imagem}'
                        )
                    "
                >
                    ACEITAR MISSÃO
                </button>

                <button
                    class="btn-missao btn-fechar-missao"
                    onclick="
                        document
                            .getElementById('modal-missao-npc')
                            .style.display='none'
                    "
                >
                    RECUSAR
                </button>
            `;

            return;
        }

        // Prioridade 3: Sem missões no momento
        conteudo.innerHTML = `
            <p class="missao-desc" style="text-align:center;">
                "O firmamento está calmo hoje. Continue sua jornada, retorne quando estiver mais experiente."
            </p>
            <button class="btn-missao btn-fechar-missao" onclick="document.getElementById('modal-missao-npc').style.display='none'">DESPEDIR-SE</button>
        `;
    }

    async aceitar(quest_id, npc_id, nome_npc, url_imagem) {
        const userId = localStorage.getItem("jogadorEldoraID");
        
        const res = await fetch('/api/npc/missao/aceitar', {
            method: 'POST', 
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: userId, quest_id: quest_id })
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
                alert(data.message);
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
            else alert(data.error);
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
                alert(data.message);
            }
            
            if (typeof window.carregarMeuPerfil === 'function') {
                window.carregarMeuPerfil();
            }

            this.interagir(npc_id, nome_npc, url_imagem);
        } else {
            if (typeof window.alertaEldora === 'function') {
                window.alertaEldora("Aviso", data.error, "erro");
            } else {
                alert(data.error);
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
            alert("Falha mágica: " + data.error);
        }
    }
}

window.motorMissoesNPC = new MotorDeMissoesNPC();