// ==========================================
// MÍDIAS PADRÃO (Apenas as classes base e o aprendiz)
// ==========================================
const MIDIA_PERFIL_BASE = {
    "guerreiro": "LINK_GITHUB_GUERREIRO.mp4",
    "berserker": "LINK_GITHUB_BERSERKER.mp4",
    "cacador": "LINK_GITHUB_CACADOR.mp4",
    "monge": "LINK_GITHUB_MONGE.mp4",
    "mago": "LINK_GITHUB_MAGO.mp4",
    "bardo": "LINK_GITHUB_BARDO.mp4",
    "assassino": "https://github.com/user-attachments/assets/cbc6a4a3-26c6-46fe-b03f-4b594b5c3b47",
    "samurai": "LINK_GITHUB_SAMURAI.mp4",
    "curandeiro": "LINK_GITHUB_CURANDEIRO.mp4",
    "aprendiz": "LINK_GITHUB_APRENDIZ.mp4",
    "aventureiro": "https://github.com/user-attachments/assets/b0f8f158-3d54-46ef-b1df-9bbd9300609f"
};

// ==========================================
// DICIONÁRIO DE CLASSES COM SUAS BASES
// ==========================================
const CLASSES_INFO = {
    // SEM CLASSE
    'aprendiz': { nome: 'Aventureiro', emoji: '🎒', base: 'aprendiz' },
    'aventureiro': { nome: 'Aventureiro', emoji: '🎒', base: 'aprendiz' },

    // GUERREIRO
    'guerreiro': { nome: 'Guerreiro', emoji: '⚔️', base: 'guerreiro' },
    'cavaleiro': { nome: 'Cavaleiro', emoji: '🛡️', base: 'guerreiro' },
    'gladiador': { nome: 'Gladiador', emoji: '🔱', base: 'guerreiro' },
    'templario': { nome: 'Templário', emoji: '⚜️', base: 'guerreiro' },
    'guardiao_divino': { nome: 'Guardião Divino', emoji: '🛡️', base: 'guerreiro' },
    
    // BERSERKER
    'berserker': { nome: 'Berserker', emoji: '🪓', base: 'berserker' },
    'barbaro': { nome: 'Bárbaro', emoji: '🗿', base: 'berserker' },
    'juggernaut': { nome: 'Juggernaut', emoji: '🐗', base: 'berserker' },
    'ira_primordial': { nome: 'Ira Primordial', emoji: '👹', base: 'berserker' },
    
    // CAÇADOR
    'cacador': { nome: 'Caçador', emoji: '🏹', base: 'cacador' },
    'patrulheiro': { nome: 'Patrulheiro', emoji: '🐾', base: 'cacador' },
    'franco_atirador': { nome: 'Franco-Atirador', emoji: '🎯', base: 'cacador' },
    'olho_de_aguia': { nome: 'Olho de Águia', emoji: '🦅', base: 'cacador' },
    
    // MONGE
    'monge': { nome: 'Monge', emoji: '🧘', base: 'monge' },
    'guardiao_do_templo': { nome: 'Guardião do Templo', emoji: '🏯', base: 'monge' },
    'punho_elemental': { nome: 'Punho Elemental', emoji: '🔥', base: 'monge' },
    'ascendente': { nome: 'Ascendente', emoji: '🕊️', base: 'monge' },
    
    // MAGO
    'mago': { nome: 'Mago', emoji: '🧙', base: 'mago' },
    'feiticeiro': { nome: 'Feiticeiro', emoji: '🔮', base: 'mago' },
    'elementalista': { nome: 'Elementalista', emoji: '☄️', base: 'mago' },
    'arquimago': { nome: 'Arquimago', emoji: '🌌', base: 'mago' },
    
    // BARDO
    'bardo': { nome: 'Bardo', emoji: '🎶', base: 'bardo' },
    'menestrel': { nome: 'Menestrel', emoji: '📜', base: 'bardo' },
    'encantador': { nome: 'Encantador', emoji: '✨', base: 'bardo' },
    'maestro': { nome: 'Maestro', emoji: '🎼', base: 'bardo' },
    
    // ASSASSINO
    'assassino': { nome: 'Assassino', emoji: '🔪', base: 'assassino' },
    'ladrao_de_sombras': { nome: 'Ladrão de Sombras', emoji: '💨', base: 'assassino' },
    'ninja': { nome: 'Ninja', emoji: '🥷', base: 'assassino' },
    'mestre_das_laminas': { nome: 'Mestre das Lâminas', emoji: '⚔️', base: 'assassino' },
    
    // SAMURAI
    'samurai': { nome: 'Samurai', emoji: '🥷', base: 'samurai' },
    'kensei': { nome: 'Kensei', emoji: '🗡️', base: 'samurai' },
    'ronin': { nome: 'Ronin', emoji: '🧧', base: 'samurai' },
    'shogun': { nome: 'Shogun', emoji: '🏯', base: 'samurai' },
    
    // CURANDEIRO
    'curandeiro': { nome: 'Curandeiro', emoji: '🩹', base: 'curandeiro' },
    'clerigo': { nome: 'Clérigo', emoji: '✝️', base: 'curandeiro' },
    'druida': { nome: 'Druida', emoji: '🌳', base: 'curandeiro' },
    'sacerdote': { nome: 'Sacerdote', emoji: '⛪', base: 'curandeiro' }
};

async function carregarMeuPerfil() {
    const charId = localStorage.getItem("jogadorEldoraID");

    if (!charId) {
        const msg = document.getElementById('perfil-msg-carregando');
        if(msg) msg.innerHTML = "<span style='color: #e74c3c;'>Nenhum herói selecionado. Volte ao portal.</span>";
        return;
    }

    try {
        const resposta = await fetch(`/perfil/${charId}`);
        const p = await resposta.json();

        if (p.erro) {
            const msg = document.getElementById('perfil-msg-carregando');
            if(msg) msg.innerText = "⚠️ " + p.erro;
            return;
        }

        // 1. Dados Básicos e formatação de texto
        const nome = p.nome || "Aventureiro";
        const classeKey = (p.classe || "aprendiz").toLowerCase();
        
        // Pega as infos da classe (se não achar, usa a estrutura de aprendiz)
        const infoClasse = CLASSES_INFO[classeKey] || CLASSES_INFO['aprendiz'];
        
        // 2. SISTEMA DE SKIN: Se tiver skin equipada usa ela, senão usa a mídia da classe Base!
        const linkMidia = p.skin_equipada || MIDIA_PERFIL_BASE[infoClasse.base] || MIDIA_PERFIL_BASE["aprendiz"];

        // Preenche os textos no HTML
        document.getElementById('perf-nome').innerText = nome;
        document.getElementById('perf-classe').innerText = `${infoClasse.emoji} ${infoClasse.nome}`;
        document.getElementById('perf-lvl').innerText = p.level || 1;
        
        document.getElementById('perf-ouro').innerText = (p.gold || 0).toLocaleString('pt-BR');
        document.getElementById('perf-gems').innerText = (p.gems || 0).toLocaleString('pt-BR');
        
        document.getElementById('perf-hp-texto').innerText = `${p.hp_atual || 0} / ${p.hp_max || 0}`;
        document.getElementById('perf-energia').innerText = p.energy || 0;
        document.getElementById('perf-pontos').innerText = p.pontos_livres || 0;

        // Barra de XP
        const xpAtual = p.xp || 0;
        const xpMaximo = p.xp_max || 1; 
        let percentagem = (xpAtual / xpMaximo) * 100;
        if (percentagem > 100) percentagem = 100;

        document.getElementById('perf-xp-barra').style.width = percentagem + "%";
        document.getElementById('perf-xp-texto').innerText = `${xpAtual.toLocaleString('pt-BR')} / ${xpMaximo.toLocaleString('pt-BR')}`;
        
        // 3. RENDERIZADOR INTELIGENTE (Vídeo vs Imagem)
        const elementoMediaAntigo = document.getElementById('perf-avatar');
        if (elementoMediaAntigo) {
            const isVideo = linkMidia.toLowerCase().endsWith('.mp4');
            const container = elementoMediaAntigo.parentElement;
            
            // Se o elemento atual for diferente do que precisamos (ex: tem img mas precisa de video)
            if (isVideo && elementoMediaAntigo.tagName !== 'VIDEO') {
                const novoVideo = document.createElement('video');
                novoVideo.id = 'perf-avatar';
                novoVideo.autoplay = true;
                novoVideo.loop = true;
                novoVideo.muted = true;
                novoVideo.playsInline = true;
                novoVideo.style.width = '100%';
                novoVideo.style.borderRadius = '10px';
                novoVideo.style.border = '2px solid #f39c12';
                novoVideo.src = linkMidia;
                container.replaceChild(novoVideo, elementoMediaAntigo);
            } 
            else if (!isVideo && elementoMediaAntigo.tagName !== 'IMG') {
                const novaImg = document.createElement('img');
                novaImg.id = 'perf-avatar';
                novaImg.style.width = '100%';
                novaImg.style.borderRadius = '10px';
                novaImg.style.border = '2px solid #f39c12';
                novaImg.src = linkMidia;
                container.replaceChild(novaImg, elementoMediaAntigo);
            } 
            else {
                // Se a tag já for a correta, só atualiza o src para não piscar a tela
                if (elementoMediaAntigo.src !== linkMidia) {
                    elementoMediaAntigo.src = linkMidia;
                }
            }
        }

        // Alterna as telas
        document.getElementById('perfil-carregando').style.display = 'none';
        document.getElementById('perfil-dados').style.display = 'block';

    } catch (erro) {
        console.error("Erro na aba perfil:", erro);
        const msg = document.getElementById('perfil-msg-carregando');
        if (msg) msg.innerText = "⚠️ Erro ao conjurar o feitiço do perfil. Tente novamente.";
    }
}