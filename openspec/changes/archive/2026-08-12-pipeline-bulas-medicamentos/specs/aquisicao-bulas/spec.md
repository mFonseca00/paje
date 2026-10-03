## Purpose

Responsável pela coleta automatizada de PDFs de bulas de medicamentos a partir do bulário eletrônico da ANVISA, com escopo restrito aos medicamentos presentes na RENAME, controlando fluxo, erros e possíveis barreiras de acesso.

## ADDED Requirements

### Requirement: Busca de bula por nome de produto

O sistema SHALL consultar o endpoint de busca da ANVISA (`GET /api/consulta/bulario`) passando o nome do medicamento como filtro e obter os identificadores de bula (`idBulaPacienteProtegido` e/ou `idBulaProfissionalProtegido`) retornados na resposta.

#### Scenario: Medicamento encontrado com IDs de bula disponíveis
- **WHEN** o sistema consulta o endpoint com um nome de medicamento válido presente na RENAME
- **THEN** o sistema recebe ao menos um registro com `idBulaPacienteProtegido` ou `idBulaProfissionalProtegido` preenchido

#### Scenario: Medicamento não encontrado
- **WHEN** o endpoint retorna `totalElements = 0` para o nome consultado
- **THEN** o sistema registra o ocorrido em log, não tenta download e avança para o próximo medicamento da lista

### Requirement: Download de PDF de bula

O sistema SHALL baixar o PDF da bula via endpoint `GET /api/consulta/medicamentos/arquivo/bula/parecer/{id}/` e salvar em disco, usando o ID obtido na etapa de busca.

#### Scenario: Download bem-sucedido
- **WHEN** o endpoint retorna um PDF válido (Content-Type application/pdf)
- **THEN** o arquivo é salvo em disco com nome identificável (baseado no nome do produto e/ou ID) e o caminho é registrado no banco

#### Scenario: Resposta não é um PDF válido
- **WHEN** o endpoint retorna um status de erro HTTP ou corpo não PDF
- **THEN** o sistema registra o erro, não salva arquivo corrompido e marca o medicamento para reprocessamento

### Requirement: Escopo restrito à RENAME

O sistema SHALL processar apenas medicamentos cujo nome conste na base de nomes derivada da RENAME.

#### Scenario: Medicamento está na RENAME
- **WHEN** o nome do medicamento consta na lista RENAME carregada pelo sistema
- **THEN** o sistema inclui o medicamento na fila de aquisição

#### Scenario: Medicamento não está na RENAME
- **WHEN** o nome do medicamento não consta na lista RENAME
- **THEN** o sistema ignora o medicamento e não realiza nenhuma requisição para ele

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

### Requirement: Controle de duplicatas

O sistema SHALL verificar se a bula já foi baixada anteriormente antes de realizar um novo download.

#### Scenario: Bula já existe no banco
- **WHEN** o ID de bula consultado já está registrado no banco com status diferente de ERRO
- **THEN** o sistema pula o download e não sobrescreve o arquivo existente

#### Scenario: Bula está marcada como ERRO
- **WHEN** o ID de bula está registrado com status ERRO
- **THEN** o sistema realiza nova tentativa de download

### Requirement: Parâmetros de retry configuráveis

O sistema SHALL expor via variáveis de ambiente o número máximo de tentativas e o tempo de espera inicial do backoff, de modo que o operador possa ajustar o comportamento sem alterar código.

#### Scenario: Configuração padrão aplicada quando variáveis ausentes

- **WHEN** `ANVISA_RETRY_TENTATIVAS` e `ANVISA_RETRY_ESPERA_SEGUNDOS` não estão definidas no `.env`
- **THEN** o sistema usa 3 tentativas e 5 segundos de espera inicial

#### Scenario: Configuração personalizada respeitada

- **WHEN** `ANVISA_RETRY_TENTATIVAS=5` e `ANVISA_RETRY_ESPERA_SEGUNDOS=10.0` estão definidas
- **THEN** o sistema realiza até 5 tentativas com espera inicial de 10 segundos antes de desistir

### Requirement: Log e rastreabilidade da aquisição

O sistema SHALL registrar em log cada etapa da aquisição (busca, download, erro, skip) de forma que seja possível auditar o processo e identificar falhas.

#### Scenario: Ciclo completo de aquisição registrado
- **WHEN** o sistema conclui a aquisição de um medicamento (com ou sem sucesso)
- **THEN** um registro de log contém: nome do medicamento, ID da bula, resultado (sucesso/erro/skip) e timestamp
