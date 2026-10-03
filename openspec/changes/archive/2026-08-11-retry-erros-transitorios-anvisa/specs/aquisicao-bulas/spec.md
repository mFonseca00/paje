## MODIFIED Requirements

### Requirement: Controle de CAPTCHA e acesso

O sistema SHALL detectar respostas que indiquem bloqueio por CAPTCHA ou rate-limiting e agir de forma a não resultar em dados corrompidos. O sistema SHALL adicionalmente classificar respostas de erro HTTP em **transitórias** (5xx) e **permanentes** (4xx que não sejam 429/403), aplicando retentativa automática apenas para erros transitórios.

#### Scenario: Resposta indica CAPTCHA ou bloqueio por rate-limit

- **WHEN** a resposta do endpoint retorna status 429 ou HTML inesperado (possível CAPTCHA)
- **THEN** o sistema interrompe imediatamente todas as requisições do lote, registra o evento e aguarda intervenção

#### Scenario: Resposta indica acesso negado por requisição

- **WHEN** a resposta do endpoint retorna status 403
- **THEN** o sistema registra o evento em log, marca o medicamento como ERRO e avança para o próximo sem interromper o lote

#### Scenario: Resposta indica erro transitório do servidor

- **WHEN** a resposta do endpoint retorna status 5xx (e.g., 500 Internal Server Error, 502, 503)
- **THEN** o sistema aguarda um intervalo de backoff crescente e repete a requisição, até o limite de tentativas configurado

#### Scenario: Retentativa bem-sucedida após erro transitório

- **WHEN** uma tentativa subsequente ao erro 5xx retorna status 200 com conteúdo válido
- **THEN** o sistema prossegue normalmente, registrando em log qual tentativa teve sucesso

#### Scenario: Esgotamento das tentativas após erros transitórios

- **WHEN** todas as tentativas configuradas resultam em erro 5xx
- **THEN** o sistema registra a falha em log, marca o medicamento como ERRO e avança para o próximo sem interromper o lote

#### Scenario: Requisições realizadas com sucesso sem bloqueio

- **WHEN** as respostas retornam status 200 com conteúdo esperado
- **THEN** o sistema prossegue o fluxo normalmente

## ADDED Requirements

### Requirement: Parâmetros de retry configuráveis

O sistema SHALL expor via variáveis de ambiente o número máximo de tentativas e o tempo de espera inicial do backoff, de modo que o operador possa ajustar o comportamento sem alterar código.

#### Scenario: Configuração padrão aplicada quando variáveis ausentes

- **WHEN** `ANVISA_RETRY_TENTATIVAS` e `ANVISA_RETRY_ESPERA_SEGUNDOS` não estão definidas no `.env`
- **THEN** o sistema usa 3 tentativas e 5 segundos de espera inicial

#### Scenario: Configuração personalizada respeitada

- **WHEN** `ANVISA_RETRY_TENTATIVAS=5` e `ANVISA_RETRY_ESPERA_SEGUNDOS=10.0` estão definidas
- **THEN** o sistema realiza até 5 tentativas com espera inicial de 10 segundos antes de desistir
