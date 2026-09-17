(() => {
    'use strict';
    const api = window.BruxaPocoes = { aberta: false, criarNPC };
    let selecionada = null;
    let entradaAnterior = null;
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
        identidade.append(texto('span', 'BANCADA DE ALQUIMIA', 'bruxa-sobretitulo'));
        const titulo = texto('h2', 'Bruxa das Poções');
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
        modal.append(cabecalho, lista, aviso);
        modal.addEventListener('cancel', e => { e.preventDefault(); fechar(); });
        // Os eventos do diálogo não devem alcançar os controles globais do mapa.
        for (const evento of ['pointerdown', 'pointerup', 'pointermove', 'mousedown', 'mouseup', 'click', 'dblclick', 'touchstart', 'touchmove', 'touchend', 'wheel']) {
            modal.addEventListener(evento, e => e.stopPropagation());
        }
        document.body.append(modal);
    }

    async function abrir(scene) {
        prepararModal();
        cena = scene;
        entradaAnterior = { mouse: scene.input?.enabled, teclado: scene.input?.keyboard?.enabled };
        if (scene.input) scene.input.enabled = false;
        if (scene.input?.keyboard) scene.input.keyboard.enabled = false;
        api.aberta = true;
        focoAnterior = document.activeElement;
        modal.showModal();
        await carregar(++versao);
    }

    function fechar() {
        ++versao;
        api.aberta = false;
        if (cena?.input && entradaAnterior) {
            cena.input.enabled = entradaAnterior.mouse;
            if (cena.input.keyboard) {
                cena.input.keyboard.resetKeys?.();
                cena.input.keyboard.enabled = entradaAnterior.teclado;
            }
        }
        entradaAnterior = null;
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


    const ASSETS = 'https://raw.githubusercontent.com/Eldorabotpy/static-img/main/assets/';
    function imagemItem(id, nome, consumivel = false) {
        const img = document.createElement('img');
        img.alt = nome;
        img.draggable = false;
        const pasta = consumivel || id === 'frasco_com_agua' ? 'consumiveis' : 'materiais';
        const urls = [ASSETS + 'itens/' + pasta + '/' + id + '.png?v=5'];
        urls.push('/static/assets/box.png');
        let indice = 0;
        img.onerror = () => {
            indice++;
            if (indice < urls.length) img.src = urls[indice];
            else img.onerror = null;
        };
        img.src = urls[0];
        return img;
    }

    function renderizar(receitas) {
        lista.replaceChildren();
        if (!receitas.length) { lista.append(texto('p', 'Nenhuma receita disponível.')); return; }
        const atual = receitas.find(r => r.receita_id === selecionada) || receitas[0];
        selecionada = atual.receita_id;
        const selecao = document.createElement('div');
        selecao.className = 'bruxa-selecao';
        selecao.append(texto('h3', 'RECEITUÁRIO'));
        const slots = document.createElement('div');
        slots.className = 'bruxa-slots';
        for (const receita of receitas) {
            const slot = document.createElement('button');
            slot.className = 'bruxa-slot' + (receita.receita_id === selecionada ? ' selecionado' : '');
            slot.type = 'button';
            slot.setAttribute('aria-label', receita.nome);
            slot.setAttribute('aria-pressed', String(receita.receita_id === selecionada));
            slot.disabled = ocupado;
            slot.append(imagemItem(receita.resultado, receita.nome, true));
            slot.append(texto('span', receita.tier === 2 ? 'II' : 'I', 'bruxa-tier'));
            slot.append(texto('small', receita.nome.replace('Poção de ', '').replace('Elixir Superior de Experiência', 'XP · 30 min').replace('Elixir de Experiência', 'XP · 10 min')));
            slot.onclick = () => { selecionada = receita.receita_id; renderizar(receitas); };
            slots.append(slot);
        }
        selecao.append(slots);
        const painel = document.createElement('div');
        painel.className = 'bruxa-preparo';
        const vitrine = document.createElement('div');
        vitrine.className = 'bruxa-vitrine';
        const retrato = document.createElement('div');
        retrato.className = 'bruxa-retrato';
        retrato.setAttribute('aria-hidden', 'true');
        const resultado = document.createElement('div');
        resultado.className = 'bruxa-resultado';
        resultado.append(imagemItem(atual.resultado, atual.nome, true), texto('span', '×1'));
        vitrine.append(retrato, texto('span', '✦', 'bruxa-runa'), resultado);
        const efeitos = {
            pocao_cura_leve: 'Restaura 100 HP', pocao_mana_leve: 'Restaura 100 MP',
            pocao_cura_media: 'Restaura 300 HP', pocao_mana_media: 'Restaura 300 MP',
            elixir_xp_dobrado_10m: 'XP de combate ×2 · 10 minutos',
            elixir_xp_dobrado_30m: 'XP de combate ×2 · 30 minutos'
        };
        painel.append(vitrine, texto('h4', atual.nome), texto('p', efeitos[atual.resultado] || '', 'bruxa-efeito'));
        painel.append(texto('h3', 'INGREDIENTES'));
        const ingredientes = document.createElement('div');
        ingredientes.className = 'bruxa-ingredientes';
        for (const item of atual.ingredientes) {
            const material = document.createElement('div');
            material.className = 'bruxa-material ' + (item.possui >= item.necessario ? 'bruxa-tem' : 'bruxa-falta');
            const quadro = document.createElement('div');
            quadro.className = 'bruxa-material-slot';
            quadro.append(imagemItem(item.item_id, item.nome), texto('strong', item.possui + '/' + item.necessario));
            material.append(quadro, texto('span', item.nome));
            ingredientes.append(material);
        }
        const custo = Number(atual.custo_ouro || 0);
        const saldo = Number(atual.ouro_disponivel || 0);
        const ouroInsuficiente = saldo < custo;
        const custoEl = texto('p', custo ? 'Custo: ' + custo.toLocaleString('pt-BR') + ' ouro · Seu ouro: ' + saldo.toLocaleString('pt-BR') : 'Sem custo em ouro', 'bruxa-custo');
        if (ouroInsuficiente) custoEl.className += ' insuficiente';
        const botao = texto('button', ocupado ? 'PREPARANDO…' : ouroInsuficiente ? 'Ouro insuficiente' : atual.pode_criar ? 'Preparar poção' : 'Faltam ingredientes', 'bruxa-fabricar');
        botao.disabled = ocupado || !atual.pode_criar;
        botao.onclick = () => fabricar(atual.receita_id);
        painel.append(ingredientes, custoEl, botao);
        lista.append(selecao, painel);
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
