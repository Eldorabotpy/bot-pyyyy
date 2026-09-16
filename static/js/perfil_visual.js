const GITHUB_BASE = "https://raw.githubusercontent.com/Eldorabotpy/static-img/refs/heads/main/assets/";

window.CATALOGO_SISTEMA = {
    avatares: {
        'aventureiro_masculino': { nome: 'Aventureiro M', path: `${GITHUB_BASE}avatares/avatar_padrao_m.png` }, 
        'aventureiro_feminino':  { nome: 'Aventureiro F', path: `${GITHUB_BASE}avatares/avatar_padrao_f.png` },
        'ninja_lendario':        { nome: 'Shadow Ninja',  path: `${GITHUB_BASE}avatares/ninja_unlocked.png` },
        'avatar_xiongmaoren_s1_m': { nome: 'Mestre Panda (M)', path: `${GITHUB_BASE}avatares/avatar_xiongmaoren_s1_m.png` },
        'avatar_xiongmaoren_s1_f': { nome: 'Mestre Panda (F)', path: `${GITHUB_BASE}avatares/avatar_xiongmaoren_s1_f.png` },
    },    
    
    skins: {
        'aventureiro_masculino': { nome: 'Corpo Aventureiro', path: `${GITHUB_BASE}corpo_completo/aventureiro_m_full.png` },
        'aventureiro_feminino':  { nome: 'Corpo Aventureira', path: `${GITHUB_BASE}corpo_completo/aventureiro_f_full.png` },
        'skin_xiongmaoren_s1_m': { nome: 'Corpo Panda M', path: `${GITHUB_BASE}corpo_completo/skin_xiongmaoren_s1_m_full.png` },
        'skin_xiongmaoren_s1_f': { nome: 'Corpo Panda F', path: `${GITHUB_BASE}corpo_completo/skin_xiongmaoren_s1_f_full.png` }
    },
    
    banners: {
        'padrao':   { nome: 'Padrão', path: `${GITHUB_BASE}banners/padrao.png` },
        'paisagem': { nome: 'Vale Épico', path: `${GITHUB_BASE}banners/paisagem.png` },
        'azul':     { nome: 'Azul Arcano', path: `${GITHUB_BASE}banners/azul.png` },
        'verde':    { nome: 'Floresta', path: `${GITHUB_BASE}banners/verde.png` },
        'banner_xiongmaoren_s1': { nome: 'Banner Panda', path: `${GITHUB_BASE}banners/banner_xiongmaoren_s1.png` },
    }
};

// ==========================================
// 🧙‍♂️ GERADOR AUTOMÁTICO DE CLASSES NO CATÁLOGO
// ==========================================
const classesRPG = ['guerreiro', 'mago', 'assassino', 'cacador', 'curandeiro', 'berserker', 'samurai', 'monge', 'bardo'];

classesRPG.forEach(c => {
    ['m', 'f'].forEach(g => {
        let idCosmetico = `${c}_${g}`; // Ex: guerreiro_m
        let nomeFormatado = c.charAt(0).toUpperCase() + c.slice(1) + (g === 'm' ? ' (M)' : ' (F)');
        
        window.CATALOGO_SISTEMA.avatares[idCosmetico] = { 
            nome: nomeFormatado, 
            path: `${GITHUB_BASE}avatares/avatar_${idCosmetico}.png` 
        };
        
        window.CATALOGO_SISTEMA.skins[idCosmetico] = { 
            nome: 'Corpo ' + nomeFormatado, 
            path: `${GITHUB_BASE}corpo_completo/${idCosmetico}_full.png` 
        };
    });
});

class PerfilVisual {
    constructor() {
        this.containerId = 'modal-editar-perfil';
    }

    renderizarEdicao() {
        let modal = document.getElementById(this.containerId);
        
        if (!modal) {
            modal = document.createElement('div');
            modal.id = this.containerId;
            document.body.appendChild(modal);
        }

        modal.className = 'modal-moderno';

        const p = window.perfilDadosGlobais; 
        if (!p) return;

        // 1. Descobre Gênero e Classe base
        const generoCurto = (p.gender && p.gender.toLowerCase() === 'feminino') ? 'f' : 'm';
        const classeDoBanco = (p.class || p.classe || "aventureiro").toLowerCase(); 
        const minhaClasseId = `${classeDoBanco}_${generoCurto}`;
        const baseAventureiroId = generoCurto === 'f' ? 'aventureiro_feminino' : 'aventureiro_masculino';

        // 2. Filtro Anti-Crash (Impede a quebra do botão se a variável vier vazia/corrompida do banco)
        const filtroGenero = (id) => {
            if (!id || typeof id !== 'string') return false;
            if (generoCurto === 'm') return !id.endsWith('_f') && !id.endsWith('_feminino');
            if (generoCurto === 'f') return !id.endsWith('_m') && !id.endsWith('_masculino');
            return true;
        };

        // 3. Montar Avatares
        let htmlAvatares = '';
        let listaAvataresBruta = [
            baseAventureiroId,
            minhaClasseId,
            ...(p.unlocked_skins || []), 
            ...(p.unlocked_avatars || [])
        ];
        
        // Remove duplicatas e aplica o filtro de gênero
        const avataresParaExibir = [...new Set(listaAvataresBruta)].filter(filtroGenero);
    
        avataresParaExibir.forEach(id => {
            const info = CATALOGO_SISTEMA.avatares[id];
            if (!info) return; 
            const isSel = (p.avatar_customizado === id || (id === baseAventureiroId && (!p.avatar_customizado || p.avatar_customizado === 'padrao'))) ? 'selecionado' : '';
            
            htmlAvatares += `
                <div class="card-opcao ${isSel}" id="av-${id}" onclick="perfilVisual.selecionar('avatar', '${id}')">
                    <img src="${info.path}" alt="${info.nome}" onerror="this.src='https://placehold.co/45x45/111/f39c12?text=?'">
                    <span>${info.nome}</span>
                </div>`;
        });

        // 4. Montar Skins de Corpo
        let htmlSkins = '';

        const classeEhInicial =
            classeDoBanco === 'aprendiz' ||
            classeDoBanco === 'aventureiro';

        const skinsAventureiro = [
            'aventureiro_m',
            'aventureiro_f',
            'aventureiro_masculino',
            'aventureiro_feminino'
        ];

        let listaSkinsBruta = [
            ...(classeEhInicial ? [baseAventureiroId] : []),
            minhaClasseId,
            ...(p.unlocked_skins || [])
        ];

        const skinsParaExibir = [...new Set(listaSkinsBruta)]
            .filter(filtroGenero)
            .filter(id =>
                classeEhInicial ||
                !skinsAventureiro.includes(id)
            );
    
        skinsParaExibir.forEach(id => {
            const info = CATALOGO_SISTEMA.skins[id];
            if (!info) return; 
            const isSel = (p.equipped_skin === id || (id === baseAventureiroId && (!p.equipped_skin || p.equipped_skin === 'padrao'))) ? 'selecionado' : '';
            
            htmlSkins += `
                <div class="card-opcao ${isSel}" id="sk-${id}" onclick="perfilVisual.selecionar('skin', '${id}')">
                    <img src="${info.path}" alt="${info.nome}" onerror="this.src='https://placehold.co/45x85/111/f39c12?text=?'">
                    <span>${info.nome}</span>
                </div>`;
        });

        // 5. Montar Banners
        let htmlBanners = '';
        const bannersParaExibir = ['padrao', 'azul', 'verde', 'paisagem', ...(p.unlocked_banners || [])];
    
        bannersParaExibir.forEach(id => {
            const info = CATALOGO_SISTEMA.banners[id];
            if (!info) return;
            const isSel = (p.banner_customizado === id || (id === 'padrao' && !p.banner_customizado)) ? 'selecionado' : '';
            const bgImagem = info.path ? `url('${info.path}') center/cover` : '#1e293b';

            htmlBanners += `
                <div class="card-opcao-banner ${isSel}" id="bn-${id}" onclick="perfilVisual.selecionar('banner', '${id}')" style="background: ${bgImagem};">
                    ${info.nome}
                </div>`;
        });

        // 6. Desenhar Modal na Tela
        modal.innerHTML = `
            <div class="perfil-container-moderno">
                <div class="perfil-header">
                    <h2>⚙️ CUSTOMIZAR PERFIL</h2>
                    <p style="font-size: 0.7em; color: #94a3b8; margin-top: 5px;">Crie seu próprio estilo!</p>
                </div>
            
                <div class="secao-cosmetico">
                    <label>🖼️ ROSTO NO PERFIL (Avatar)</label>
                    <div class="grid-selecao">${htmlAvatares}</div>
                </div>

                <div class="secao-cosmetico">
                    <label>🧍‍♂️ CORPO NO MAPA (Skin)</label>
                    <div class="grid-selecao">${htmlSkins}</div>
                </div>

                <div class="secao-cosmetico">
                    <label>🌌 FUNDO (Banner)</label>
                    <div class="grid-selecao">${htmlBanners}</div>
                </div>

                <input type="hidden" id="input-edit-avatar" value="${p.avatar_customizado || 'padrao'}">
                <input type="hidden" id="input-edit-skin" value="${p.equipped_skin || 'padrao'}">
                <input type="hidden" id="input-edit-banner" value="${p.banner_customizado || 'padrao'}">

                <div style="display: flex; margin-top: 10px;">
                    <button onclick="salvarCustomizacaoPerfil()" class="btn-salvar-moderno" style="border-radius: 0 0 0 16px;">SALVAR</button>
                    <button onclick="perfilVisual.fechar()" class="btn-salvar-moderno" style="background: linear-gradient(to bottom, #475569, #1e293b); color: white; border-radius: 0 0 16px 0;">CANCELAR</button>
                </div>
            </div>
        `;
        
        modal.style.display = 'flex';
    }

    selecionar(tipo, valor) {
        document.getElementById('input-edit-' + tipo).value = valor;

        let classeBusca = '.card-opcao';
        if (tipo === 'banner') classeBusca = '.card-opcao-banner';
        
        document.querySelectorAll(classeBusca).forEach(el => {
            if(el.id.startsWith(tipo.substring(0, 2))) {
                el.classList.remove('selecionado');
            }
        });
        
        const prefixo = tipo === 'avatar' ? 'av-' : (tipo === 'skin' ? 'sk-' : 'bn-');
        const idAlvo = prefixo + valor;
        const elemento = document.getElementById(idAlvo);
        if (elemento) elemento.classList.add('selecionado');
    }

    fechar() {
        const modal = document.getElementById(this.containerId);
        if (modal) modal.style.display = 'none';
    }
}

window.perfilVisual = new PerfilVisual();

// ==========================================
// FUNÇÃO QUE SALVA NO BANCO DE DADOS
// ==========================================
window.salvarCustomizacaoPerfil = async function() {
    const idAvatar = document.getElementById('input-edit-avatar').value;
    const idBanner = document.getElementById('input-edit-banner').value;
    const idSkin = document.getElementById('input-edit-skin').value; 
    const userId = localStorage.getItem("jogadorEldoraID");

    const btnSalvar = document.querySelector('.btn-salvar-moderno');
    if (btnSalvar) btnSalvar.innerText = "A GUARDAR... ⏳";

    try {
        const resposta = await fetch('/api/perfil/atualizar', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                user_id: userId,
                avatar: idAvatar,
                banner: idBanner,
                skin: idSkin 
            })
        });

        if (resposta.ok) {
            window.perfilVisual.fechar();
            
            if (typeof carregarMeuPerfil === 'function') {
                carregarMeuPerfil(); 
            }
            
            if (window.eldoraSocket) {
                window.eldoraSocket.emit('atualizarVisual', { skin: idSkin });
                localStorage.setItem("skinEquipada", idSkin); 
            }
            
            const cena = window.jogoEldora?.scene?.getScene('MapaScene');
            if (cena && cena.player) {
                cena.skinAtiva = idSkin;
                const linkNuvem = "https://raw.githubusercontent.com/Eldorabotpy/static-img/refs/heads/main/assets/classes/";

                if (!cena.textures.exists(idSkin)) {
                    const urlCompleta = `${linkNuvem}${idSkin}.png`;
                    
                    cena.load.once('loaderror', (fileObj) => {
                        if (fileObj.key === idSkin) {
                            if (typeof window.alertaEldora === 'function') {
                                window.alertaEldora("Imagem Não Encontrada", `O GitHub falhou ao carregar a skin.\n\nLink buscado:\n${urlCompleta}\n\nVerifique se o nome do arquivo lá é exatamente "${idSkin}.png".`, "erro");
                            } else {
                                alert(`Imagem não encontrada no GitHub:\n${urlCompleta}`);
                            }
                        }
                    });

                    cena.load.spritesheet(idSkin, urlCompleta, {
                        frameWidth: 128,
                        frameHeight: 128
                    });
                    
                    cena.load.once(`filecomplete-spritesheet-${idSkin}`, () => {
                        cena.player.setTexture(idSkin);
                        cena.player.setFrame(1);

                        // Mantém o mesmo tamanho visual usado pelo mapa
                        cena.player.setDisplaySize(48, 48);

                        if (typeof cena.gerarAnimacoes === 'function') {
                            cena.gerarAnimacoes(idSkin);
                        }
                        
                        if (typeof window.alertaEldora === 'function') {
                            window.alertaEldora("Novo Visual", "Aparência guardada com sucesso no pergaminho!", "sucesso");
                        }
                    });
                    
                    cena.load.start();
                } else {
                    cena.player.setTexture(idSkin);
                    cena.player.setFrame(1);
                    cena.player.setDisplaySize(48, 48);

                    if (typeof cena.gerarAnimacoes === 'function') {
                        cena.gerarAnimacoes(idSkin);
                    }
                    
                    if (typeof window.alertaEldora === 'function') {
                        window.alertaEldora("Novo Visual", "Aparência guardada com sucesso no pergaminho!", "sucesso");
                    }
                }
            } else {
                if (typeof window.alertaEldora === 'function') {
                    window.alertaEldora("Novo Visual", "Aparência guardada com sucesso no pergaminho!", "sucesso");
                }
            }
            
        } else {
            if (typeof window.alertaEldora === 'function') {
                window.alertaEldora("Falha Mágica", "Erro ao guardar visual nas lendas.", "erro");
            }
        }
    } catch(e) {
        console.error(e);
        if (typeof window.alertaEldora === 'function') {
            window.alertaEldora("Conexão Perdida", "Os ventos mágicos estão fracos. Erro de conexão com o Reino.", "erro");
        }
    } finally {
        if (btnSalvar) btnSalvar.innerText = "SALVAR";
    }
};