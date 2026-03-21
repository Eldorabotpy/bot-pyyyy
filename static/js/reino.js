// ==========================================
// FUNÇÃO DA ABA: O REINO DE ELDORA
// ==========================================
function carregarReino() {
    const conteudo = document.getElementById('aba-reino');
    
    conteudo.innerHTML = `
        <div class="home-banner" style="border-color: #f39c12; margin-bottom: 15px;">
            <img src="/static/regions/reino_eldora.jpg" onerror="this.src='https://placehold.co/600x200/111/333?text=A+Capital+de+Eldora'">
        </div>
        
        <div style="text-align: center; margin-bottom: 20px;">
            <h2 style="color: #f8fafc; margin: 0 0 5px 0; font-size: 1.4em;">Capital do Reino</h2>
            <p style="color: #94a3b8; font-size: 0.85em; margin: 0;">O coração econômico e militar do mundo.</p>
        </div>

        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 20px;">
            
            <button onclick="alert('Sistema de Viagem em desenvolvimento!')" style="background: #1e293b; border: 1px solid #334155; border-bottom: 3px solid #22c55e; padding: 15px; border-radius: 10px; cursor: pointer; display: flex; flex-direction: column; align-items: center; transition: 0.2s;">
                <span style="font-size: 2em; margin-bottom: 5px;">🗺️</span>
                <strong style="color: #f8fafc; font-size: 0.95em;">Viajar / Mapa</strong>
            </button>
            
            <button onclick="alert('Mercado em desenvolvimento!')" style="background: #1e293b; border: 1px solid #334155; border-bottom: 3px solid #f59e0b; padding: 15px; border-radius: 10px; cursor: pointer; display: flex; flex-direction: column; align-items: center; transition: 0.2s;">
                <span style="font-size: 2em; margin-bottom: 5px;">🏪</span>
                <strong style="color: #f8fafc; font-size: 0.95em;">Mercado Livre</strong>
            </button>
            
            <button onclick="alert('Forja em desenvolvimento!')" style="background: #1e293b; border: 1px solid #334155; border-bottom: 3px solid #64748b; padding: 15px; border-radius: 10px; cursor: pointer; display: flex; flex-direction: column; align-items: center; transition: 0.2s;">
                <span style="font-size: 2em; margin-bottom: 5px;">⚒️</span>
                <strong style="color: #f8fafc; font-size: 0.95em;">Forja Real</strong>
            </button>
            
            <button onclick="alert('Refino em desenvolvimento!')" style="background: #1e293b; border: 1px solid #334155; border-bottom: 3px solid #06b6d4; padding: 15px; border-radius: 10px; cursor: pointer; display: flex; flex-direction: column; align-items: center; transition: 0.2s;">
                <span style="font-size: 2em; margin-bottom: 5px;">🧪</span>
                <strong style="color: #f8fafc; font-size: 0.95em;">Laboratório</strong>
            </button>

            <button onclick="alert('Guildas em desenvolvimento!')" style="background: #1e293b; border: 1px solid #334155; border-bottom: 3px solid #eab308; padding: 15px; border-radius: 10px; cursor: pointer; display: flex; flex-direction: column; align-items: center; transition: 0.2s;">
                <span style="font-size: 2em; margin-bottom: 5px;">🏰</span>
                <strong style="color: #f8fafc; font-size: 0.95em;">Saguão da Guilda</strong>
            </button>
            
            <button onclick="alert('Arena em desenvolvimento!')" style="background: #1e293b; border: 1px solid #334155; border-bottom: 3px solid #ef4444; padding: 15px; border-radius: 10px; cursor: pointer; display: flex; flex-direction: column; align-items: center; transition: 0.2s;">
                <span style="font-size: 2em; margin-bottom: 5px;">⚔️</span>
                <strong style="color: #f8fafc; font-size: 0.95em;">Arena PvP</strong>
            </button>

        </div>

        <button onclick="alert('Central de Eventos em desenvolvimento!')" style="width: 100%; background: linear-gradient(90deg, #7e22ce, #a855f7); border: 1px solid #c084fc; border-bottom: 4px solid #581c87; padding: 15px; border-radius: 10px; cursor: pointer; display: flex; justify-content: center; align-items: center; gap: 10px; transition: 0.2s;">
            <span style="font-size: 1.5em;">💀</span>
            <strong style="color: #ffffff; font-size: 1.1em; letter-spacing: 1px;">CENTRAL DE EVENTOS</strong>
        </button>
    `;
}