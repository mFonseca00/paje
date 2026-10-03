## MODIFIED Requirements

### Requirement: Tabela de bulas com controle de estado

O sistema SHALL manter uma tabela `bulas` com metadados de cada bula coletada, incluindo referência ao arquivo em disco, a resposta JSON bruta do modelo e o campo `status_processamento_ia` com os valores PENDENTE, PROCESSADO ou ERRO.

A tabela SHALL incluir também o campo `ultima_verificacao_anvisa` (timestamp with time zone, nullable) para registrar quando o `id_bula_anvisa` foi confirmado pela última vez junto à ANVISA. Bulas inseridas antes desta funcionalidade ou puladas via pre-checagem local mantêm `ultima_verificacao_anvisa = NULL`.

#### Scenario: Bula inserida como PENDENTE
- **WHEN** o PDF de uma bula é baixado com sucesso
- **THEN** um registro é inserido na tabela `bulas` com `status_processamento_ia = PENDENTE`, o caminho do arquivo em disco e `ultima_verificacao_anvisa` preenchido com o timestamp UTC do download

#### Scenario: Bula avança para PROCESSADO
- **WHEN** a extração LLM é concluída com sucesso e o JSON é validado
- **THEN** o status da bula é atualizado para PROCESSADO e a resposta JSON do modelo é armazenada no campo JSONB

#### Scenario: Bula marcada como ERRO
- **WHEN** a extração falha ou o JSON retornado é inválido
- **THEN** o status da bula é atualizado para ERRO e a resposta bruta (se existir) é preservada no campo JSONB

#### Scenario: Campo ultima_verificacao_anvisa atualizado sem re-download
- **WHEN** o sistema consulta a ANVISA online e decide SKIP (JWT confirmado, PDF válido)
- **THEN** `ultima_verificacao_anvisa` é atualizado com o timestamp UTC da consulta, sem alterar os demais campos
