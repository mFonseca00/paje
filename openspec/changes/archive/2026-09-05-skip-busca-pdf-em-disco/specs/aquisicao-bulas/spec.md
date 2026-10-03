## ADDED Requirements

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
