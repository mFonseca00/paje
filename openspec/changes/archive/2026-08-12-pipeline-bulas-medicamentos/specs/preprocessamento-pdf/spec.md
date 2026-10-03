## Purpose

Responsável por converter PDFs de bulas em markdown via Docling e extrair apenas as seções de contra-indicações e interações medicamentosas, entregando o texto íntegro dessas seções à pipeline de extração LLM sem chunking adicional.

## ADDED Requirements

### Requirement: Conversão de PDF para markdown via Docling

O sistema SHALL converter cada PDF de bula em markdown usando pymupdf4llm, preservando a hierarquia de seções e títulos do documento original.

#### Scenario: PDF com texto embutido convertido com sucesso
- **WHEN** o Docling processa um PDF com texto embutido e seções nomeadas
- **THEN** o markdown produzido preserva os cabeçalhos de seção e o conteúdo associado a cada uma

#### Scenario: Conversão produz markdown sem seções reconhecíveis
- **WHEN** o Docling não consegue identificar estrutura de seções no documento
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

### Requirement: Log de rastreabilidade do pré-processamento

O sistema SHALL registrar em log, para cada bula processada, qual estratégia foi utilizada (estrutural ou fallback size-based) e quais seções foram ou não encontradas.

#### Scenario: Estratégia estrutural bem-sucedida registrada
- **WHEN** as seções são extraídas via estratégia estrutural
- **THEN** o log indica as seções encontradas e o volume de texto extraído

#### Scenario: Ausência de estrutura registrada
- **WHEN** nenhuma seção relevante é identificada no markdown
- **THEN** o log indica que nenhuma seção foi encontrada e que o markdown bruto completo foi encaminhado ao LLM
