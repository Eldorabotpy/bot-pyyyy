// /static/js/profissao_ui.js

class ProfissaoUI {
    constructor() {
        // Dados sincronizados com seu professions.py
        this.profissoes = {
            // Coleta (Gathering)
            'lenhador':  { nome: 'Lenhador', cat: 'gathering', icone: '🪓', desc: 'Mestre no corte de madeiras e troncos ancestrais.', npc: 'sylas' },
            'minerador': { nome: 'Minerador', cat: 'gathering', icone: '⛏️', desc: 'Especialista em extrair minérios e pedras das profundezas.', npc: 'borin' },
            'colhedor':  { nome: 'Colhedor', cat: 'gathering', icone: '🌿', desc: 'Coleta fibras vegetais e plantas para tecelagem.', npc: 'elara' },
            'esfolador': { nome: 'Esfolador', cat: 'gathering', icone: '🔪', desc: 'Extrai couros e penas de criaturas abatidas.', npc: 'grom' },
            'alquimista':{ nome: 'Alquimista', cat: 'gathering', icone: '🧪', desc: 'Coleta essências e sangues mágicos para preparos.', npc: 'paracelso' },

            // Produção (Crafting)
            'ferreiro':  { nome: 'Ferreiro', cat: 'crafting', icone: '🔨', desc: 'Forja barras de metal e ferramentas resistentes.', npc: 'thorek' },
            'armeiro':   { nome: 'Armeiro', cat: 'crafting', icone: '⚔️', desc: 'Especialista em criar armas e lâminas letais.', npc: 'thorek' },
            'alfaiate':  { nome: 'Alfaiate', cat: 'crafting', icone: '🧵', desc: 'Tece tecidos mágicos e vestes de poder.', npc: 'elara' },
            'joalheiro': { nome: 'Joalheiro', cat: 'crafting', icone: '💎', desc: 'Lapida gemas e cria adornos de alto valor.', npc: 'paracelso' },
            'curtidor':  { nome: 'Curtidor', cat: 'crafting', icone: '👞', desc: 'Trabalha couros brutos para criar armaduras leves.', npc: 'grom' }
        };

        this.criarEstruturaModal();
    }

    criarEstruturaModal() {
        if (document.getElementById('modal-profissao')) return;

        const html = `
            <div id="modal-profissao" class="modal-rpg-overlay" style="display:none;">
                <div class="modal-rpg-box">
                    <div class="modal-rpg-header">
                        <h2 id="titulo-profissao">Ofícios de Eldora</h2>
                        <button class="btn-fechar" onclick="window.motorProfissao.fechar()">×</button>
                    </div>
                    <div id="msg-tratado" class="alerta-tratado"></div>
                    <div id="lista-profissoes" class="grid-profissoes"></div>
                    <div id="detalhe-profissao" class="detalhe-box" style="display:none;">
                        <h3 id="detalhe-nome"></h3>
                        <p id="detalhe-desc"></p>
                        <button id="btn-aprender" class="btn-confirmar">ABRAÇAR OFÍCIO</button>
                    </div>
                </div>
            </div>

            <style>
                .modal-rpg-overlay {
                    position: fixed; top:0; left:0; width:100%; height:100%;
                    background: rgba(0,0,0,0.85); z-index: 100010;
                    display: flex; justify-content: center; align-items: center;
                    backdrop-filter: blur(4px);
                }
                .modal-rpg-box {
                    background: linear-gradient(145deg, #1e293b, #0f172a);
                    border: 2px solid #ca8a04; border-radius: 12px;
                    width: 90%; max-width: 400px; padding: 15px; color: #fff;
                    box-shadow: 0 0 30px rgba(202, 138, 4, 0.3);
                    max-height: 85vh; /* 👈 Impede que a caixa fique maior que a tela */
                    display: flex; flex-direction: column;
                }
                .modal-rpg-header { display: flex; justify-content: space-between; border-bottom: 1px solid #ca8a04; padding-bottom: 10px; margin-bottom: 10px; }
                .modal-rpg-header h2 { margin: 0; font-size: 1.3em; }
                
                .grid-profissoes { 
                    display: grid; grid-template-columns: repeat(2, 1fr); gap: 8px; 
                    margin-bottom: 10px; 
                    overflow-y: auto; /* 👈 Adiciona rolagem vertical */
                    max-height: 45vh; /* 👈 Limita a altura só da lista */
                    padding-right: 5px;
                }
                
                /* Barra de rolagem com tema RPG */
                .grid-profissoes::-webkit-scrollbar { width: 6px; }
                .grid-profissoes::-webkit-scrollbar-track { background: rgba(0,0,0,0.3); border-radius: 4px; }
                .grid-profissoes::-webkit-scrollbar-thumb { background: #ca8a04; border-radius: 4px; }

                .card-prof {
                    background: rgba(255,255,255,0.05); border: 1px solid #334155;
                    border-radius: 8px; padding: 10px; cursor: pointer; text-align: center;
                    transition: 0.2s; font-size: 0.85em; /* Fonte menor */
                }
                .card-prof div:first-child { font-size: 1.8em !important; margin-bottom: 2px; } /* Ícone ligeiramente menor */
                .card-prof:hover { border-color: #ca8a04; background: rgba(202, 138, 4, 0.1); }
                .card-prof.selecionado { border-color: #facc15; background: rgba(250, 204, 21, 0.2); box-shadow: 0 0 10px #facc15; }
                .card-prof.bloqueado { opacity: 0.4; cursor: not-allowed; filter: grayscale(1); }
                
                .alerta-tratado { font-size: 0.8em; color: #f87171; text-align: center; margin-bottom: 10px; font-style: italic; }
                .detalhe-box { 
                    background: rgba(0,0,0,0.3); padding: 10px; border-radius: 8px; 
                    border-left: 4px solid #facc15; animation: fadeIn 0.3s;
                    margin-top: auto; /* Empurra pra baixo */
                }
                .detalhe-box h3 { margin: 0 0 5px 0; font-size: 1.1em; }
                .detalhe-box p { margin: 0; font-size: 0.85em; color: #cbd5e1; }
                
                .btn-confirmar {
                    width: 100%; padding: 10px; background: linear-gradient(to bottom, #ca8a04, #a16207);
                    border: none; border-radius: 6px; color: #000; font-weight: bold; margin-top: 10px; cursor: pointer;
                }
                .btn-fechar { background: transparent; border: none; color: #ca8a04; font-size: 1.5em; cursor: pointer; padding: 0; line-height: 1; }
                @keyframes fadeIn { from { opacity: 0; transform: translateY(5px); } to { opacity: 1; transform: translateY(0); } }
            </style>
        `;
        document.body.insertAdjacentHTML('beforeend', html);
    }

    abrir(npc_id_input) {
        const p = window.perfilDadosGlobais;
        if (!p) return;

        const modal = document.getElementById('modal-profissao');
        const lista = document.getElementById('lista-profissoes');
        const alerta = document.getElementById('msg-tratado');
        const detalhe = document.getElementById('detalhe-profissao');
        
        detalhe.style.display = 'none';
        lista.innerHTML = '';
        alerta.innerText = '';
        modal.style.display = 'flex';

        // ⚖️ LÓGICA DO TRATADO E DA MAESTRIA ⚖️
        const profAtual = p.profession || null;
        
        // 👇 1. BUSCA BLINDADA: Procura tanto por "inventario" quanto por "inventory"
        const inv = p.inventario || p.inventory || {};
        
        let qtdSelo = 0;

        // 👇 2. PROCURA O SELO NÃO IMPORTA O FORMATO (Lista ou Dicionário)
        if (inv['selo_de_maestria']) {
            let s = inv['selo_de_maestria'];
            // Se for um objeto, pega a quantidade. Se for um número direto, usa ele. Se existir, assume no mínimo 1.
            qtdSelo = typeof s === 'object' ? (s.quantity || s.qtd || s.quantidade || 1) : Number(s);
        } else {
            // Se o inventário for uma lista (Array), varre item por item procurando o selo
            Object.values(inv).forEach(item => {
                if (item && (item.base_id === 'selo_de_maestria' || item.id === 'selo_de_maestria')) {
                    qtdSelo = item.quantity || item.qtd || item.quantidade || 1;
                }
            });
        }

        let catPermitida = null;
        let bloqueioTotal = false;

        if (profAtual) {
            // Se já tem profissão e NÃO tem o selo, bloqueia totalmente aprender coisas novas
            if (qtdSelo < 1) {
                bloqueioTotal = true;
                alerta.innerText = `⚠️ Você já é um ${profAtual.display_name}. Atinja a maestria para liberar um novo ofício!`;
                alerta.style.color = "#facc15"; // Amarelo Eldora
            } else {
                // Tem o selo! Aplica o Tratado das Guildas
                if (profAtual.category === 'crafting') {
                    catPermitida = 'gathering';
                    alerta.innerText = "⚖️ O Tratado das Guildas exige que sua próxima escolha seja de COLETA.";
                    alerta.style.color = "#60a5fa"; // Azul
                } else if (profAtual.category === 'gathering') {
                    catPermitida = 'crafting';
                    alerta.innerText = "⚖️ O Tratado das Guildas exige que sua próxima escolha seja de PRODUÇÃO.";
                    alerta.style.color = "#60a5fa"; // Azul
                }
            }
        }

        // Filtra e constrói os botões
        Object.entries(this.profissoes).forEach(([id, dados]) => {
            // 👇 CORREÇÃO: Removemos a exceção do Thorek. Agora cada um mostra SÓ o seu! 👇
            if (dados.npc !== npc_id_input) return; 

            const ehAMesma = profAtual && profAtual.key === id;
            const ehBloqueada = bloqueioTotal || (catPermitida && dados.cat !== catPermitida) || ehAMesma;

            const card = document.createElement('div');
            card.className = `card-prof ${ehBloqueada && !ehAMesma ? 'bloqueado' : ''}`;
            
            // Design especial se for a profissão atual do jogador
            if (ehAMesma) {
                card.style.borderColor = "#2ecc71";
                card.style.background = "rgba(46, 204, 113, 0.1)";
                card.innerHTML = `<div style="font-size: 1.8em; margin-bottom: 2px;">${dados.icone}</div><div style="color:#2ecc71; font-weight:bold;">${dados.nome} (Sua)</div>`;
            } else {
                card.innerHTML = `<div style="font-size: 1.8em; margin-bottom: 2px;">${dados.icone}</div><div>${dados.nome}</div>`;
            }
            
            // Lógica de clique blindada
            card.onclick = () => {
                if (ehAMesma) {
                    window.alertaEldora("Sua Profissão", "Você já domina esta arte! Vá coletar recursos.", "sucesso");
                } else if (bloqueioTotal) {
                    window.alertaEldora("Falta Maestria", "Você precisa atingir o Nível Máximo na sua profissão e obter o Selo da Maestria antes de aprender um novo ofício.", "erro");
                } else if (ehBloqueada) {
                    window.alertaEldora("Tratado das Guildas", `A lei exige que você escolha uma profissão de ${catPermitida === 'gathering' ? 'Coleta' : 'Produção'}.`, "erro");
                } else {
                    this.selecionar(id);
                }
            };
            
            lista.appendChild(card);
        });
    }

    selecionar(id) {
        // Remove seleção anterior
        document.querySelectorAll('.card-prof').forEach(c => c.classList.remove('selecionado'));
        // Marca o novo
        const cards = document.querySelectorAll('.card-prof');
        for(let c of cards) { if(c.innerText.includes(this.profissoes[id].nome)) c.classList.add('selecionado'); }

        const dados = this.profissoes[id];
        document.getElementById('detalhe-nome').innerText = `${dados.icone} ${dados.nome}`;
        document.getElementById('detalhe-desc').innerText = dados.desc;
        document.getElementById('detalhe-profissao').style.display = 'block';

        document.getElementById('btn-aprender').onclick = () => this.confirmarAprender(id);
    }

    async confirmarAprender(id) {
        const userId = localStorage.getItem("jogadorEldoraID");
        const res = await fetch('/api/personagem/aprender_profissao', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: userId, profession_key: id })
        });
        const data = await res.json();

        if (data.success) {
            window.alertaEldora("Sucesso!", `Parabéns! Agora você é um ${this.profissoes[id].nome}.`, "sucesso");
            this.fechar();
            if (typeof window.carregarMeuPerfil === 'function') window.carregarMeuPerfil();
        } else {
            window.alertaEldora("Erro", data.error, "erro");
        }
    }

    fechar() { document.getElementById('modal-profissao').style.display = 'none'; }
}

window.motorProfissao = new ProfissaoUI();
// Alias para manter compatibilidade com npcs_engine.js
window.abrirModalProfissoes = (npc) => window.motorProfissao.abrir(npc);