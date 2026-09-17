(() => {
    'use strict';
    const api = window.BruxaPocoes = { aberta: false, criarNPC };
    let modal, lista, aviso, cena, ocupado = false, versao = 0, focoAnterior;
    const texto = (tag, valor, classe) => {
        const el = document.createElement(tag);
        el.textContent = valor;
        if (classe) el.className = classe;
        return el;
    };

    function criarNPC(scene) {
        if (!scene.textures.exists('npc_bruxa_pocoes')) {
            console.error('A cartela da bruxa não carregou.');
            return;
        }
        if (!scene.anims.exists('bruxa_caldeirao')) {
            scene.anims.create({ key: 'bruxa_caldeirao', frames: scene.anims.generateFrameNumbers('npc_bruxa_pocoes', { start: 0, end: 5 }), frameRate: 6, repeat: -1 });
        }
        const POS_X = (32 * 32) + 6;
        const POS_Y = (9 * 32) + 28;   // desce a bruxa para frente da árvore
        const DEPTH_BRUXA = 25;        // acima do player e das camadas altas

        const npc = scene.add.sprite(POS_X, POS_Y, 'npc_bruxa_pocoes')
            .setOrigin(0.5, 1)
            .setDisplaySize(64, 64)
            .setDepth(DEPTH_BRUXA)
            .setInteractive({ useHandCursor: true })
            .play('bruxa_caldeirao');

        scene.add.text(npc.x, npc.y - 65, 'Bruxa das Poções', {
            fontSize: '10px',
            color: '#e9d5ff',
            stroke: '#120c1c',
            strokeThickness: 3
        }).setOrigin(0.5, 1).setDepth(DEPTH_BRUXA + 1);
        npc.on('pointerdown', (pointer, x, y, event) => {
            event?.stopPropagation();
            if (scene.isDead || scene.travadoNoPortal || scene.player?.isGathering || api.aberta) return;
            if (!scene.player || Phaser.Math.Distance.Between(scene.player.x, scene.player.y, npc.x, npc.y) > 96) {
                window.mostrarDialogoRPG('Bruxa das Poções', 'Chegue mais perto do meu caldeirão para preparar suas poções.');
                return;
            }
            scene.motorCacada?.pararAutoCacada?.('alquimia', false);
            scene.isMoving = false;
            scene.player.body?.stop();
            scene.player.anims?.stop();
            abrir(scene);
        });
        scene.events.once('shutdown', () => { if (cena === scene) fechar(); });
    }

    function prepararModal() {
        if (modal) return;
        modal = document.createElement('dialog');
        modal.id = 'bruxa-pocoes-modal';
        modal.setAttribute('aria-labelledby', 'bruxa-pocoes-titulo');
        const cabecalho = document.createElement('div');
        cabecalho.className = 'bruxa-cabecalho';
        const identidade = document.createElement('div');
        identidade.append(texto('span', 'FLORESTA SOMBRIA · ALQUIMIA', 'bruxa-sobretitulo'));
        const titulo = texto('h2', 'O Caldeirão');
        titulo.id = 'bruxa-pocoes-titulo';
        const sair = texto('button', '×', 'bruxa-fechar');
        sair.type = 'button';
        sair.setAttribute('aria-label', 'Fechar caldeirão');
        sair.onclick = fechar;
        identidade.append(titulo);
        cabecalho.append(identidade, sair);
        aviso = texto('p', '', 'bruxa-aviso');
        aviso.setAttribute('role', 'status');
        aviso.setAttribute('aria-live', 'polite');
        lista = document.createElement('div');
        lista.className = 'bruxa-receitas';
        modal.append(cabecalho, texto('p', 'Das dádivas da floresta, uma gota de magia.', 'bruxa-intro'), aviso, lista);
        modal.addEventListener('cancel', e => { e.preventDefault(); fechar(); });
        document.body.append(modal);
    }

    async function abrir(scene) {
        prepararModal();
        cena = scene;
        api.aberta = true;
        focoAnterior = document.activeElement;
        modal.showModal();
        await carregar(++versao);
    }

    function fechar() {
        ++versao;
        api.aberta = false;
        cena = null;
        modal?.close();
        focoAnterior?.focus();
    }

    async function requisitar(url, options = {}) {
        const resposta = await fetch(url, { cache: 'no-store', ...options });
        const dados = await resposta.json();
        if (!resposta.ok || !dados.success) throw new Error(dados.error || 'Não foi possível consultar o caldeirão.');
        return dados;
    }

    async function carregar(atual, mensagem = '') {
        lista.replaceChildren();
        aviso.textContent = 'Consultando ingredientes…';
        try {
            const id = localStorage.getItem('jogadorEldoraID');
            if (!id) throw new Error('Selecione seu herói para preparar poções.');
            const dados = await requisitar(`/api/bruxa/receitas/${encodeURIComponent(id)}`);
            if (!api.aberta || atual !== versao) return;
            renderizar(dados.receitas);
            aviso.textContent = mensagem || (ocupado ? 'Preparando poção…' : 'Cada preparo produz 1 poção.');
        } catch (erro) {
            if (!api.aberta || atual !== versao) return;
            aviso.textContent = mensagem ? `${mensagem} Não foi possível atualizar as receitas: ${erro.message}` : erro.message;
            const tentar = texto('button', 'Atualizar receitas');
            tentar.onclick = () => carregar(versao);
            lista.append(tentar);
        }
    }

    function renderizar(receitas) {
        lista.replaceChildren();
        let grupo;
        for (const receita of receitas) {
            if (grupo !== receita.grupo) {
                grupo = receita.grupo;
                lista.append(texto('h3', grupo));
            }
            const card = document.createElement('article');
            const resumo = document.createElement('div');
            resumo.className = 'bruxa-resumo';
            const simbolo = texto('span', receita.emoji, 'bruxa-simbolo');
            simbolo.setAttribute('aria-hidden', 'true');
            const detalhes = document.createElement('div');
            detalhes.append(texto('h4', receita.nome));
            resumo.append(simbolo, detalhes);
            card.append(resumo);
            const efeitos = {
                pocao_cura_leve: 'Recupera 100 HP', pocao_mana_leve: 'Recupera 100 MP',
                pocao_cura_media: 'Recupera 300 HP', pocao_mana_media: 'Recupera 300 MP',
                elixir_xp_dobrado_10m: 'XP pessoal de combate em dobro por 10 minutos',
                elixir_xp_dobrado_30m: 'XP pessoal de combate em dobro por 30 minutos'
            };
            detalhes.append(texto('p', efeitos[receita.resultado] || ''));
            const ingredientes = document.createElement('ul');
            for (const item of receita.ingredientes) {
                const linha = document.createElement('li');
                linha.className = item.possui >= item.necessario ? 'bruxa-tem' : 'bruxa-falta';
                linha.append(texto('span', item.nome), texto('strong', `${item.possui} / ${item.necessario}`));
                ingredientes.append(linha);
            }
            const botao = texto('button', receita.pode_criar ? 'Preparar poção' : 'Faltam ingredientes');
            botao.disabled = ocupado || !receita.pode_criar;
            botao.onclick = () => fabricar(receita.receita_id);
            card.append(ingredientes, botao);
            lista.append(card);
        }
    }

    async function fabricar(receitaId) {
        if (ocupado || !api.aberta) return;
        ocupado = true;
        lista.querySelectorAll('button').forEach(b => { b.disabled = true; });
        aviso.textContent = 'Preparando poção…';
        let mensagem;
        try {
            const dados = await requisitar('/api/bruxa/fabricar', {
                method: 'POST', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ user_id: localStorage.getItem('jogadorEldoraID'), receita_id: receitaId })
            });
            mensagem = `${dados.nome} preparada! Adicionada à sua mochila.`;
            if (typeof window.carregarMeuPerfil === 'function') await window.carregarMeuPerfil();
        } catch (erro) {
            mensagem = `Não foi possível confirmar o preparo: ${erro.message} Confira a mochila antes de tentar novamente.`;
        } finally {
            ocupado = false;
            if (api.aberta) await carregar(versao, mensagem);
        }
    }
})();
