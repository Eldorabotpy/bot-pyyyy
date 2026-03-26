from PIL import Image
import os

# 1. Defina as pastas (crie a pasta 'icones_baixados' e coloque suas imagens lá)
pasta_origem = "icones_baixados"
pasta_destino = "icones_webp"

# 2. Defina o tamanho ideal para o miniapp (128x128 costuma ser perfeito)
tamanho_alvo = (128, 128)

# Cria a pasta de destino automaticamente se ela não existir
if not os.path.exists(pasta_destino):
    os.makedirs(pasta_destino)

# 3. Percorre todos os arquivos na pasta de origem
for nome_arquivo in os.listdir(pasta_origem):
    # Filtra apenas arquivos de imagem
    if nome_arquivo.lower().endswith(('.png', '.jpg', '.jpeg')):
        caminho_antigo = os.path.join(pasta_origem, nome_arquivo)
        
        try:
            # Abre a imagem
            img = Image.open(caminho_antigo)
            
            # Redimensiona mantendo a melhor qualidade possível (LANCZOS)
            img = img.resize(tamanho_alvo, Image.Resampling.LANCZOS)
            
            # Troca a extensão final para .webp
            nome_sem_extensao = os.path.splitext(nome_arquivo)[0]
            caminho_novo = os.path.join(pasta_destino, f"{nome_sem_extensao}.webp")
            
            # Salva no formato WebP com fundo transparente e boa compressão
            img.save(caminho_novo, "webp", quality=85)
            
            print(f"Sucesso: {nome_arquivo} -> {nome_sem_extensao}.webp")
            
        except Exception as e:
            print(f"Erro ao converter {nome_arquivo}: {e}")

print("Conversão finalizada! Seus ícones estão prontos para o miniapp.")