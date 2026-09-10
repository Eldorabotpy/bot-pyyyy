// static/js/season_pass.js

async function carregarPasse() {
    let userId = localStorage.getItem('jogadorEldoraID');
    if (!userId) {
        userId = window.Telegram?.WebApp?.initDataUnsafe?.user?.id || "123456789";
    }

    try {
        const response = await fetch(`/api/passe/status/${userId}`);
        const data = await response.json();

        if (data.erro) {
            console.error("Erro ao carregar passe:", data.erro);
            return;
        }

        const passe = data.status;
        const catalogo = data.catalogo;

        // Atualiza cabeçalho e XP
        document.getElementById('display-nivel-atual').innerText = `NÍVEL ${passe.level}`;
        const xpNecessario = 100;
        const porcentagem = (passe.xp / xpNecessario) * 100;
        document.getElementById('barra-progresso').style.width = `${porcentagem}%`;
        document.getElementById('texto-xp').innerText = `${passe.xp} / ${xpNecessario} XP`;

        // Atualiza Status Premium
        const statusTxt = document.getElementById('status-premium');
        const btnPremium = document.getElementById('btn-comprar-premium');
        
        if (passe.is_premium) {
            statusTxt.innerHTML = 'Status: <b style="color: #f1c40f;">PREMIUM 👑</b>';
            btnPremium.style.display = 'none';
        } else {
            btnPremium.style.display = 'inline-block';
            btnPremium.onclick = comprarPassePremium; // 👈 Liga o botão à nossa nova função!
        }

        // Listas de resgatados (Para saber o que já foi pego)
        const resgatadosFree = passe.resgatados_free || [];
        const resgatadosPremium = passe.resgatados_premium || [];

        // Desenha a lista de recompensas
        const lista = document.getElementById('lista-recompensas');
        lista.innerHTML = ''; 

        Object.keys(catalogo).forEach(nivelStr => {
            const nivel = parseInt(nivelStr);
            const recompensa = catalogo[nivel];
            
            const isPremiumLocked = !passe.is_premium;
            const isNivelAlcancado = passe.level >= nivel;
            
            const jaResgatouFree = resgatadosFree.includes(nivel);
            const jaResgatouPremium = resgatadosPremium.includes(nivel);

            // Classes CSS inteligentes
            const classFree = jaResgatouFree ? "resgatado" : (isNivelAlcancado ? "disponivel" : "bloqueado");
            const classPremium = jaResgatouPremium ? "resgatado" : (isPremiumLocked ? "locked" : (isNivelAlcancado ? "disponivel" : "bloqueado"));

            const row = document.createElement('div');
            row.className = `reward-row ${isNivelAlcancado ? 'completed' : ''}`;
            
            row.innerHTML = `
                <div class="reward-box reward-free ${classFree}" onclick="resgatarPremio(${nivel}, 'free')">
                    <small>GRÁTIS</small>
                    ${jaResgatouFree ? "✔️ Resgatado" : recompensa.free.label}
                </div>

                <div class="reward-level-center">
                    <div class="level-diamond">
                        <span>${nivel}</span>
                    </div>
                </div>

                <div class="reward-box reward-premium ${classPremium}" onclick="resgatarPremio(${nivel}, 'premium')">
                    <small>PREMIUM</small>
                    ${jaResgatouPremium ? "✔️ Resgatado" : recompensa.premium.label}
                </div>
            `;
            lista.appendChild(row);
        });

    } catch (err) {
        console.error("Falha na conexão com a API do Passe:", err);
    }
}

// 🔥 A NOVA FUNÇÃO DE RESGATE (Clica na caixa e envia pro Python) 🔥
async function resgatarPremio(nivel, tipo) {
    let userId = localStorage.getItem('jogadorEldoraID') || window.Telegram?.WebApp?.initDataUnsafe?.user?.id || "123456789";

    try {
        const response = await fetch('/api/passe/resgatar', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: userId, nivel: nivel, tipo: tipo })
        });

        const data = await response.json();

        if (data.status === "success") {
            // ✨ AQUI ESTÁ A MUDANÇA: Trocámos o alert pela tela dourada de sucesso!
            alertaPasseEldora("Recompensa Resgatada!", data.message, true);
            carregarPasse(); 
        } else {
            // ✨ E AQUI TAMBÉM: Tela vermelha para os bloqueios do anti-cheat
            alertaPasseEldora("Acesso Negado", data.message, false);
        }
    } catch (err) {
        // ✨ ATÉ NO ERRO: Para nunca mais ver a caixa cinzenta!
        alertaPasseEldora("Falha Mágica", "Erro de comunicação com o servidor.", false);
    }
}

window.onload = carregarPasse;

// 🔥 FUNÇÃO DE COMPRA DO PASSE PREMIUM 🔥
// ==========================================
// SISTEMA DE COMPRA E ALERTAS CUSTOMIZADOS
// ==========================================

// 1. Abre a janela de confirmação (Agora usando o CSS)
function comprarPassePremium() {
    let modal = document.getElementById('modal-confirmar-premium');
    
    if (!modal) {
        const html = `
            <div id="modal-confirmar-premium" class="modal-passe-overlay">
                <div class="modal-passe-box">
                    <div class="modal-passe-icon" style="text-shadow: 0 0 15px rgba(52, 152, 219, 0.6);">💎</div>
                    <h3 class="modal-passe-title" style="color: #3498db;">Ativar Premium</h3>
                    <p class="modal-passe-msg">Desejas ativar o Passe Premium por <b>500 Gemas</b>? <br><br>Todos os prémios bloqueados ficarão imediatamente disponíveis!</p>
                    <div class="modal-passe-botoes">
                        <button onclick="executarCompraPremium()" class="btn-passe-comprar">Comprar</button>
                        <button onclick="document.getElementById('modal-confirmar-premium').style.display='none'" class="btn-passe-cancelar">Cancelar</button>
                    </div>
                </div>
            </div>`;
        document.body.insertAdjacentHTML('beforeend', html);
        modal = document.getElementById('modal-confirmar-premium');
    }
    modal.style.display = 'flex';
}

// 2. Executa a compra e mostra o resultado
async function executarCompraPremium() {
    document.getElementById('modal-confirmar-premium').style.display = 'none';
    let userId = localStorage.getItem('jogadorEldoraID') || window.Telegram?.WebApp?.initDataUnsafe?.user?.id || "123456789";

    try {
        const response = await fetch('/api/passe/comprar_premium', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: userId })
        });
        const data = await response.json();

        if (data.sucesso) {
            alertaPasseEldora("Bem-vindo à Elite!", data.message, true);
            carregarPasse(); 
        } else {
            alertaPasseEldora("Erro na Transação", data.message, false);
        }
    } catch (err) {
        alertaPasseEldora("Falha Mágica", "Erro de comunicação com o servidor.", false);
    }
}

// 3. Janela de Alerta Bonita (Totalmente limpa)
function alertaPasseEldora(titulo, mensagem, sucesso = true) {
    let modal = document.getElementById('modal-alerta-passe');
    let cor = sucesso ? '#f1c40f' : '#e74c3c'; 
    let icone = sucesso ? '👑' : '❌';

    if (!modal) {
        const html = `
            <div id="modal-alerta-passe" class="modal-passe-overlay">
                <div id="alerta-passe-box" class="modal-passe-box" style="border-color: ${cor};">
                    <div id="alerta-passe-icone" class="modal-passe-icon" style="text-shadow: 0 0 15px ${cor}88;">${icone}</div>
                    <h3 id="alerta-passe-titulo" class="modal-passe-title" style="color: ${cor};">${titulo}</h3>
                    <p id="alerta-passe-msg" class="modal-passe-msg">${mensagem}</p>
                    <button onclick="document.getElementById('modal-alerta-passe').style.display='none'" class="btn-passe-continuar">CONTINUAR</button>
                </div>
            </div>`;
        document.body.insertAdjacentHTML('beforeend', html);
        modal = document.getElementById('modal-alerta-passe');
    } else {
        document.getElementById('alerta-passe-icone').innerText = icone;
        document.getElementById('alerta-passe-icone').style.textShadow = `0 0 15px ${cor}88`;
        document.getElementById('alerta-passe-titulo').innerText = titulo;
        document.getElementById('alerta-passe-titulo').style.color = cor;
        document.getElementById('alerta-passe-box').style.borderColor = cor;
        document.getElementById('alerta-passe-msg').innerHTML = mensagem;
    }
    modal.style.display = 'flex';
}

async function coletarTudoLiberado() {
    let userId = localStorage.getItem('jogadorEldoraID') || window.Telegram?.WebApp?.initDataUnsafe?.user?.id;
    
    // Mostra um "Carregando..." básico ou troca o texto do botão
    try {
        const response = await fetch('/api/passe/coletar_tudo', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: userId })
        });

        const data = await response.json();

        if (data.status === "success") {
            alertaPasseEldora("Baú de Tesouros!", data.message, true);
            carregarPasse(); // Atualiza a tela para mostrar os itens como coletados
        } else if (data.status === "info") {
            alertaPasseEldora("Tudo em dia", data.message, false);
        } else {
            alertaPasseEldora("Erro", data.message, false);
        }
    } catch (err) {
        alertaPasseEldora("Erro Mágico", "Falha ao conectar ao servidor.", false);
    }
}

