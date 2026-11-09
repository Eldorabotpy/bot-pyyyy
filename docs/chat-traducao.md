# Tradução automática do chat da taverna

O chat global mantém a mensagem original e solicita traduções ao MyMemory somente quando há destinatários conectados com idioma diferente do remetente. Mensagens repetidas podem ser reutilizadas do cache; a fila tem limite para evitar rajadas de chamadas.

## Serviço e limites

Não requer chave ou cartão. O limite anônimo documentado pelo MyMemory é de 5.000 caracteres por dia; o código limita o uso a 4.500 caracteres por processo/dia como margem e cada texto enviado respeita o máximo de 500 bytes da API. O contador local reinicia junto com o processo do jogo; a API aplica o limite do próprio serviço.

O MyMemory exige par de idiomas na solicitação. O servidor estima a origem de cada mensagem em português (`pt`), espanhol (`es`) ou inglês (`en`) usando palavras comuns e caracteres próprios desses idiomas. Se a mensagem for curta ou ambígua, usa-se como alternativa o idioma escolhido no seletor, que define o idioma em que o jogador quer ler o chat. O serviço recebe o texto de cada mensagem que precise de tradução, e seus termos descrevem armazenamento de segmentos enviados. Não enviar mensagens privadas, credenciais ou outros dados sensíveis pelo chat.

Se o serviço estiver indisponível ou a cota for atingida, a mensagem original continua visível e a tradução não aparece.
