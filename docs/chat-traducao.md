# Tradução automática do chat da taverna

O chat global mantém a mensagem original e solicita traduções ao Azure Translator apenas quando há destinatários conectados com idioma diferente do remetente. Mensagens repetidas podem ser reutilizadas do cache; a fila tem limite para evitar rajadas de chamadas.

## Configuração

Crie um recurso Azure Translator no plano **F0 (Free)** e mantenha-o nesse plano. Configure a chave no serviço Eldora, sem colocá-la no repositório:

- `ELDORA_AZURE_TRANSLATOR_KEY`: chave do recurso.
- `ELDORA_AZURE_TRANSLATOR_REGION`: região do recurso, necessária para recursos regionais ou multi-serviço. Para o recurso global de serviço único, pode ficar vazia.

O processo do jogo envia textos de até 500 caracteres para `api.cognitive.microsofttranslator.com`. O endpoint detecta automaticamente o idioma de origem. Idiomas de destino aceitos pela interface: português (`pt`), espanhol (`es`) e inglês (`en`).

Configure alertas ou acompanhe o uso no portal Azure e não altere o recurso para uma camada paga. Sem a chave, a integração permanece desativada e o chat continua exibindo as mensagens originais.
