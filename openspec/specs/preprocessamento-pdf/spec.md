## Purpose

Responsável por converter PDFs de bulas em markdown via pymupdf4llm e extrair apenas as seções de contra-indicações e interações medicamentosas, entregando o texto íntegro dessas seções à pipeline de extração LLM sem chunking adicional.

## Requirements

### Requirement: Conversão de PDF para markdown via pymupdf4llm

O sistema SHALL converter cada PDF de bula em markdown usando pymupdf4llm, preservando a hierarquia de seções e títulos do documento original.

#### Scenario: PDF com texto embutido convertido com sucesso
- **WHEN** o pymupdf4llm processa um PDF com texto embutido e seções nomeadas
- **THEN** o markdown produzido preserva os cabeçalhos de seção e o conteúdo associado a cada uma

#### Scenario: Conversão produz markdown sem seções reconhecíveis
- **WHEN** o pymupdf4llm não consegue identificar estrutura de seções no documento
- **THEN** o sistema registra o evento em log e encaminha o markdown bruto completo à etapa de extração LLM

### Requirement: Extração seletiva de seções relevantes (chunkless)

O sistema SHALL identificar no markdown convertido as seções de contra-indicações e de interações medicamentosas e retornar o conteúdo íntegro dessas seções, sem aplicar chunking ou retrieval adicional.

O markdown produzido pelo pymupdf4llm apresenta hierarquia plana: o nível dos headings varia por documento (`#` a `######`) e não reflete a hierarquia real. A hierarquia deve ser inferida pelo conteúdo: headings cujo texto normalizado (sem `**` e `<mark>`) começa com `dígito + ponto` (ex: `3.`) são seções numeradas principais; demais headings são subseções da seção numerada anterior.

Inspeção de 12 bulas da ANVISA confirmou que as seções-alvo são **invariavelmente as seções numeradas 3 e 4**:
- Seção 3 — contraindicações: sempre `3. QUANDO NÃO DEVO USAR ESTE MEDICAMENTO?` (podendo ter sufixo variável no título)
- Seção 4 — precauções e interações: sempre `4. O QUE DEVO SABER ANTES DE USAR ESTE MEDICAMENTO?` (idem)

O extrator SHALL capturar as seções 3 e 4 por inteiro: localiza os headings cujo texto começa com `3.` ou `4.` e coleta todo o conteúdo até o próximo heading com número `5.` ou superior. Subseções não-numeradas (como `Interações medicamentosas`) são capturadas automaticamente por fazerem parte desse intervalo.

#### Scenario: Seções 3 e 4 encontradas
- **WHEN** o markdown contém headings cujo texto começa com `3.` e `4.`
- **THEN** o conteúdo completo de ambas as seções — incluindo subseções não-numeradas — é retornado para a etapa de extração LLM, sem fragmentação

#### Scenario: Seção ausente na bula
- **WHEN** o heading de número `3.` ou `4.` não é encontrado no markdown
- **THEN** o sistema registra a ausência em log e retorna apenas a(s) seção(ões) encontrada(s), sem erro fatal

### Requirement: Detecção de seções numeradas em formato bold puro

O sistema SHALL reconhecer marcadores de seção numerada no formato `**N. TÍTULO**` (sem prefixo `#`) como fronteiras de seção, além do formato padrão de heading markdown.

Alguns PDFs produzem seções como `**5. ONDE DEVO GUARDAR...` sem marcador `#`. O extrator SHALL detectar esse padrão e usá-lo como fronteira de fim do bloco extraído, evitando incluir conteúdo de seções posteriores às seções-alvo.

#### Scenario: Seção posterior em bold puro delimita fim do bloco
- **WHEN** após as seções 3 e 4, uma linha no formato `**5. TÍTULO**` (sem `#`) é encontrada
- **THEN** o extrator usa essa linha como fronteira e não inclui o conteúdo subsequente no resultado

#### Scenario: Seção-alvo em bold puro é reconhecida como início
- **WHEN** a seção 3 ou 4 aparece no formato bold puro em vez de heading markdown
- **THEN** o extrator reconhece o início da seção e inclui o conteúdo no bloco extraído

### Requirement: Normalização de níveis de heading no bloco extraído

O sistema SHALL normalizar os níveis de heading no texto extraído antes de entregá-lo ao LLM, independentemente do nível original produzido pelo pymupdf4llm.

#### Scenario: Heading numerado normalizado para ##
- **WHEN** o heading extraído tem texto que começa com `dígito + ponto` (ex: `3. QUANDO...`)
- **THEN** o heading é reescrito com nível `##`, independentemente do nível original

#### Scenario: Heading não-numerado normalizado para ###
- **WHEN** o heading extraído não começa com `dígito + ponto` (ex: `Interações medicamentosas`)
- **THEN** o heading é reescrito com nível `###`, independentemente do nível original

### Requirement: Promoção de subheadings bold puro dentro do bloco extraído

O sistema SHALL promover linhas inteiramente em negrito (`**texto**`) sem pontuação de fim de frase a subheadings `###`, dentro do bloco extraído.

Linhas bold que terminam com `.`, `:`, `!` ou `?` são tratadas como parágrafos de corpo e não promovidas. Linhas bold que representam seções numeradas (ex: `**5. TÍTULO**`) também não são promovidas.

#### Scenario: Linha bold sem pontuação final promovida a subheading
- **WHEN** dentro do bloco extraído existe uma linha no formato `**Interações com medicamentos...**` sem pontuação de fim de frase
- **THEN** a linha é reescrita como `### Interações com medicamentos...`

#### Scenario: Linha bold com pontuação final mantida como parágrafo
- **WHEN** dentro do bloco extraído existe uma linha no formato `**Este medicamento não deve ser utilizado por grávidas.**`
- **THEN** a linha permanece como corpo de texto, sem ser promovida a heading

### Requirement: Log de rastreabilidade do pré-processamento

O sistema SHALL registrar em log, para cada bula processada, quais seções foram ou não encontradas.

#### Scenario: Extração bem-sucedida registrada
- **WHEN** as seções são extraídas com sucesso
- **THEN** o log indica as seções encontradas e o volume de texto extraído em KB

#### Scenario: Ausência de estrutura registrada
- **WHEN** nenhuma seção relevante é identificada no markdown
- **THEN** o log indica que nenhuma seção foi encontrada e que o markdown bruto completo foi encaminhado ao LLM
