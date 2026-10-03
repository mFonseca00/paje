## Purpose

Responsável pela coleta automatizada de PDFs de bulas de medicamentos a partir do bulário eletrônico da ANVISA, com escopo restrito aos medicamentos presentes na RENAME, controlando fluxo, erros e possíveis barreiras de acesso.

## Requirements

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

O sistema SHALL verificar se a bula já foi baixada anteriormente antes de realizar um novo download, considerando tanto o `id_bula_anvisa` armazenado quanto a existência do arquivo PDF em disco.

**Cenário A — mesmo JWT, arquivo presente (comportamento existente):**
O sistema verifica o `id_bula_anvisa` no banco. Se encontrado com status ≠ ERRO e o arquivo `caminho_pdf` existe em disco, pula o download.

**Cenário B — mesmo JWT, arquivo ausente:**
O sistema verifica o `id_bula_anvisa` no banco. Se encontrado com status ≠ ERRO mas o arquivo `caminho_pdf` não existe em disco, realiza novo download, atualiza `caminho_pdf` no banco e retorna `RECUPERADO`.

**Cenário C — JWT novo, mas medicamento já tem PDF válido em disco:**
Quando `id_bula_anvisa` não é encontrado no banco (JWT rotacionado pela ANVISA), o sistema SHALL verificar se o medicamento já possui algum registro de bula com arquivo presente em disco. Se existir, pula o download e retorna `SKIP`.

**Cenário D — JWT novo, sem PDF válido em disco:**
Quando `id_bula_anvisa` não é encontrado no banco e nenhum registro do medicamento possui arquivo em disco, o sistema SHALL deletar os registros de bula fantasma do medicamento antes de realizar o download e criar novo registro.

#### Scenario: Bula já existe no banco com arquivo em disco presente

- **WHEN** o `id_bula_anvisa` já está registrado no banco com status diferente de ERRO e o arquivo `caminho_pdf` existe em disco
- **THEN** o sistema retorna `SKIP` sem realizar download

#### Scenario: Bula existe no banco mas arquivo em disco ausente

- **WHEN** o `id_bula_anvisa` já está registrado no banco com status diferente de ERRO e o arquivo `caminho_pdf` não existe em disco
- **THEN** o sistema realiza novo download, atualiza `caminho_pdf` no banco com o novo caminho e retorna `RECUPERADO`

#### Scenario: JWT rotacionado com PDF válido existente em disco

- **WHEN** o `id_bula_anvisa` retornado pela ANVISA não existe no banco e o medicamento já possui ao menos um registro com `caminho_pdf` apontando para arquivo existente em disco
- **THEN** o sistema retorna `SKIP` sem realizar download

#### Scenario: JWT rotacionado sem PDF válido em disco

- **WHEN** o `id_bula_anvisa` retornado pela ANVISA não existe no banco e nenhum registro do medicamento possui arquivo em disco
- **THEN** o sistema deleta os registros fantasma do medicamento, realiza o download e cria novo registro com `caminho_pdf` atualizado

#### Scenario: Bula está marcada como ERRO

- **WHEN** o ID de bula está registrado com status ERRO e `reprocessar_erro=True`
- **THEN** o sistema realiza nova tentativa de download

### Requirement: Parâmetros de retry configuráveis

O sistema SHALL expor via variáveis de ambiente o número máximo de tentativas e o tempo de espera inicial do backoff, de modo que o operador possa ajustar o comportamento sem alterar código.

#### Scenario: Configuração padrão aplicada quando variáveis ausentes

- **WHEN** `ANVISA_RETRY_TENTATIVAS` e `ANVISA_RETRY_ESPERA_SEGUNDOS` não estão definidas no `.env`
- **THEN** o sistema usa 3 tentativas e 5 segundos de espera inicial

#### Scenario: Configuração personalizada respeitada

- **WHEN** `ANVISA_RETRY_TENTATIVAS=5` e `ANVISA_RETRY_ESPERA_SEGUNDOS=10.0` estão definidas
- **THEN** o sistema realiza até 5 tentativas com espera inicial de 10 segundos antes de desistir

### Requirement: Nomenclatura identificável do arquivo PDF

O sistema SHALL salvar o PDF com nome no formato `{tipo}__{slug}__{sufixo}.pdf`, onde `tipo` é `paciente` ou `profissional` conforme configuração, `slug` é o nome do medicamento normalizado (apenas alfanuméricos substituindo caracteres especiais por `_`, sem truncamento), e `sufixo` são os últimos 8 caracteres do ID da bula.

Quando a bula for localizada via fallback de nome comercial, `slug` SHALL ser composto pelo nome DCB seguido de `__` e pelo nome comercial, no formato `{dcb}__{comercial}`, resultando no nome de arquivo `{tipo}__{dcb}__{comercial}__{sufixo}.pdf`.

#### Scenario: Arquivo salvo sem fallback (nome DCB encontrado diretamente)

- **WHEN** o PDF é baixado com `ANVISA_TIPO_BULA=paciente` e a bula foi encontrada diretamente pelo nome DCB
- **THEN** o arquivo é salvo com nome no formato `paciente__<slug_dcb>__<sufixo>.pdf`, sem truncamento do nome

#### Scenario: Arquivo salvo via fallback de nome comercial

- **WHEN** a busca pelo nome DCB retorna vazio e a bula é localizada via nome comercial
- **THEN** o arquivo é salvo com nome no formato `{tipo}__{slug_dcb}__{slug_comercial}__{sufixo}.pdf`, contendo o nome DCB antes do nome comercial

#### Scenario: Arquivo salvo com prefixo de tipo profissional

- **WHEN** o PDF é baixado com `ANVISA_TIPO_BULA=profissional`
- **THEN** o arquivo é salvo com nome iniciando com `profissional__`

### Requirement: Fallback por nome comercial quando DCB não encontrado

O sistema SHALL, quando a busca pelo nome DCB retornar lista vazia, consultar as listas de referência A e B da ANVISA para obter nomes comerciais associados ao DCB e tentar a busca com cada um deles, usando o primeiro que retornar resultado.

#### Scenario: DCB não encontrado, nome comercial localizado e usado
- **WHEN** `buscar_bulas(nome_dcb)` retorna lista vazia e as listas A/B contêm nomes comerciais para o DCB
- **THEN** o sistema tenta `buscar_bulas(nome_comercial)` para cada nome comercial e usa o primeiro resultado não-vazio

#### Scenario: DCB não encontrado e sem correspondência nas listas
- **WHEN** `buscar_bulas(nome_dcb)` retorna lista vazia e nenhum nome comercial é encontrado nas listas A/B
- **THEN** o sistema registra o medicamento como `NAO_ENCONTRADO` sem tentar download

### Requirement: Preservação do nome DCB original

O sistema SHALL preservar o nome original da lista RENAME (`nome_dcb`) independentemente de qual nome foi efetivamente usado na busca, de forma a rastrear a origem do medicamento.

#### Scenario: Bula encontrada diretamente pelo DCB
- **WHEN** a busca pelo nome DCB retorna resultado
- **THEN** o registro no banco armazena `nome_dcb = nome_da_rename` e `nome_comercial = nome_da_rename`

#### Scenario: Bula encontrada via fallback de nome comercial
- **WHEN** a busca bem-sucedida ocorre via fallback com nome comercial
- **THEN** o registro no banco armazena `nome_dcb = nome_original_rename` e `nome_comercial = nome_comercial_usado`

### Requirement: Preferência por resultado de princípio ativo único na seleção de bula

Quando a busca ao endpoint ANVISA retornar múltiplos resultados e o nome buscado **não** contiver "+", o sistema SHALL preferir resultados cujo `nome_produto` também não contenha "+", descartando combinações de princípios ativos da seleção primária.

Quando o nome buscado **contiver** "+", o sistema SHALL selecionar o resultado normalmente entre todos os retornados, sem filtro adicional.

Se, após aplicar o filtro, nenhum candidato restar (i.e., todos os resultados contêm "+"), o sistema SHALL usar os resultados originais como fallback, garantindo que alguma bula seja baixada.

#### Scenario: Busca de princípio ativo único retorna combinações e simples

- **WHEN** o sistema busca "amoxicilina" (sem "+") e a lista de resultados inclui "amoxicilina + clavulanato de potássio" e "amoxicilina"
- **THEN** o sistema seleciona "amoxicilina" e ignora "amoxicilina + clavulanato de potássio" na escolha do resultado principal

#### Scenario: Busca de princípio ativo único retorna apenas combinações

- **WHEN** o sistema busca um nome sem "+" e todos os resultados retornados contêm "+" em `nome_produto`
- **THEN** o sistema usa os resultados originais (incluindo combinações) como fallback e seleciona o primeiro disponível com ID de bula válido

#### Scenario: Busca de combinação não sofre filtro

- **WHEN** o sistema busca "amoxicilina + clavulanato de potassio" (com "+")
- **THEN** o sistema não aplica filtro de exclusão e seleciona normalmente entre todos os resultados retornados

### Requirement: Log e rastreabilidade da aquisição

O sistema SHALL registrar em log cada etapa da aquisição (busca, download, erro, skip) de forma que seja possível auditar o processo e identificar falhas.

#### Scenario: Ciclo completo de aquisição registrado
- **WHEN** o sistema conclui a aquisição de um medicamento (com ou sem sucesso)
- **THEN** um registro de log contém: nome do medicamento, ID da bula, resultado (sucesso/erro/skip) e timestamp

### Requirement: Pre-checagem local antes da busca ANVISA

O sistema SHALL verificar, antes de realizar qualquer requisição ao endpoint de busca da ANVISA, se o medicamento já possui ao menos uma bula com PDF válido em disco e status diferente de ERRO. Se existir, o sistema SHALL retornar SKIP imediatamente, sem consumir nenhuma requisição HTTP.

Esta verificação elimina requests desnecessários para medicamentos já baixados, reduzindo tempo de execução e risco de rate limiting em rodadas subsequentes.

#### Scenario: Medicamento com PDF válido em disco é pulado antes da busca

- **WHEN** a aquisição é iniciada para um medicamento que já possui registro no banco com `caminho_pdf` apontando para arquivo existente em disco e `status_processamento_ia ≠ ERRO`
- **THEN** o sistema retorna SKIP sem realizar nenhuma requisição ao endpoint ANVISA

#### Scenario: Medicamento sem PDF válido prossegue para busca normal

- **WHEN** a aquisição é iniciada para um medicamento que não possui nenhum registro com PDF válido em disco (ou não existe no banco)
- **THEN** o sistema prossegue normalmente com a busca ANVISA e o fluxo de duplicata existente

#### Scenario: Medicamento com bula em ERRO não é pulado na pre-checagem

- **WHEN** o único registro de bula do medicamento possui `status_processamento_ia = ERRO`
- **THEN** a pre-checagem não considera esse registro como PDF válido e prossegue com a busca ANVISA

### Requirement: Registro de data de verificação do JWT

O sistema SHALL persistir em `ultima_verificacao_anvisa` a data e hora (UTC) em que o `id_bula_anvisa` de uma bula foi confirmado pela última vez junto à ANVISA — seja em um download bem-sucedido, seja em um SKIP após verificação online do JWT. O campo SHALL ser nullable; bulas inseridas antes desta funcionalidade ou puladas pela pre-checagem local manterão o valor NULL.

Este campo não altera o comportamento de aquisição atual, mas habilita futura implementação de verificação periódica de JWTs (fora do escopo desta change).

#### Scenario: Campo atualizado após download bem-sucedido

- **WHEN** um PDF é baixado com sucesso (resultado BAIXADO, RECUPERADO ou SUBSTITUIDO)
- **THEN** `ultima_verificacao_anvisa` é gravado com o timestamp UTC do momento do download

#### Scenario: Campo atualizado após SKIP com verificação online

- **WHEN** o sistema consulta a ANVISA, obtém o JWT atual e decide fazer SKIP (Cenários A ou C do controle de duplicatas)
- **THEN** `ultima_verificacao_anvisa` é atualizado com o timestamp UTC da verificação

#### Scenario: Campo permanece NULL em SKIP por pre-checagem local

- **WHEN** o sistema retorna SKIP via pre-checagem local (sem consultar a ANVISA)
- **THEN** `ultima_verificacao_anvisa` permanece com o valor que já tinha (NULL ou timestamp anterior)
