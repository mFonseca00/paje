## Purpose

Define o esquema de persistência em PostgreSQL para medicamentos, bulas, contra-indicações e interações medicamentosas, incluindo o controle de estado de processamento e preservação da resposta bruta do modelo.

## Requirements

### Requirement: Tabela de medicamentos

O sistema SHALL manter uma tabela `medicamentos` com informações básicas de identificação dos medicamentos.

#### Scenario: Registro de medicamento criado
- **WHEN** um medicamento da RENAME é processado pela primeira vez
- **THEN** um registro com ao menos nome comercial e substância ativa é inserido na tabela `medicamentos`

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

### Requirement: Tabela de contra-indicações

O sistema SHALL manter uma tabela `contraindicacoes` com os dados extraídos pelo agente de forma normalizada, associados à bula de origem via chave estrangeira.

#### Scenario: Contra-indicação inserida após extração
- **WHEN** a extração LLM produz ao menos uma contra-indicação válida
- **THEN** cada contra-indicação é inserida em `contraindicacoes` com referência à bula de origem

### Requirement: Tabela de interações medicamentosas com tipagem

O sistema SHALL manter uma tabela `interacoes_medicamentosas` com os dados extraídos pelo agente de forma normalizada, distinguindo interações por nome direto de substância, por classe farmacológica e por alimento ou bebida.

Cada registro SHALL conter:
- `tipo`: `NOME_DIRETO` quando a interação menciona um medicamento ou substância específica pelo nome; `CLASSE` quando menciona uma categoria farmacológica (ex: "antibióticos", "anticoagulantes cumarínicos"); `ALIMENTO` quando menciona um alimento ou bebida (ex: "café", "suco de laranja", "leite")
- `referencia`: o nome da substância, classe ou alimento mencionado na bula — NOT NULL
- `efeito`: descrição do efeito esperado da interação — nullable, pois nem toda interação inclui descrição de efeito na bula

#### Scenario: Interação por nome direto inserida
- **WHEN** a extração identifica uma substância específica pelo nome (ex: "varfarina", "probenecida")
- **THEN** um registro com `tipo=NOME_DIRETO` e `referencia` preenchido com o nome da substância é inserido; `efeito` é preenchido se disponível na bula

#### Scenario: Interação por classe inserida
- **WHEN** a extração identifica uma classe farmacológica (ex: "outros antibióticos", "anticoagulantes orais")
- **THEN** um registro com `tipo=CLASSE` e `referencia` preenchido com o nome da classe é inserido; `efeito` é preenchido se disponível

#### Scenario: Interação com alimento ou bebida inserida
- **WHEN** a extração identifica um alimento ou bebida como fonte de interação (ex: "café", "suco de frutas cítricas")
- **THEN** um registro com `tipo=ALIMENTO` e `referencia` preenchido com o nome do alimento ou bebida é inserido; `efeito` é preenchido se disponível na bula

#### Scenario: Lista mista separada em registros distintos
- **WHEN** a bula menciona nomes específicos, classes e alimentos em contextos relacionados
- **THEN** cada nome específico gera um registro `NOME_DIRETO`, cada referência a classe gera um registro `CLASSE` e cada alimento ou bebida gera um registro `ALIMENTO`, todos separados

### Requirement: Tabela de substâncias ativas do medicamento

O sistema SHALL manter uma tabela `substancias_medicamento` que registra as substâncias ativas de cada medicamento conforme derivadas do `nome_dcb` da RENAME na etapa de aquisição, por split no separador `+`.

Esta tabela é populada **na etapa de aquisição**, não pela extração LLM. A extração de substâncias por LLM é trabalho futuro pós-TCC.

#### Scenario: Substâncias inseridas na aquisição — medicamento simples
- **WHEN** o sistema adquire a bula de um medicamento cujo `nome_dcb` não contém `+`
- **THEN** um único registro é inserido em `substancias_medicamento` com o próprio `nome_dcb` como nome da substância

#### Scenario: Substâncias inseridas na aquisição — medicamento composto
- **WHEN** o sistema adquire a bula de um medicamento cujo `nome_dcb` contém `+` (ex: `amoxicilina + clavulanato de potassio`)
- **THEN** cada segmento após split por `+` (trimado) é inserido como registro independente em `substancias_medicamento`

### Requirement: Suporte a JSONB para resposta bruta do modelo

O sistema SHALL usar o tipo JSONB do PostgreSQL para armazenar a resposta completa retornada pelo modelo na tabela `bulas`.

#### Scenario: Consulta à resposta bruta para auditoria
- **WHEN** o usuário ou o sistema precisa auditar ou reprocessar a extração de uma bula
- **THEN** a resposta JSON completa do modelo está disponível no campo JSONB sem necessidade de nova chamada ao modelo

### Requirement: Reprocessamento de bulas com status ERRO

O sistema SHALL permitir reprocessar bulas marcadas com status ERRO sem necessidade de novo download do PDF.

#### Scenario: Reprocessamento acionado para bula com ERRO
- **WHEN** o processo de extração é acionado para uma bula com `status_processamento_ia = ERRO`
- **THEN** o sistema reutiliza o PDF existente em disco e tenta novamente a extração, atualizando o status conforme o resultado

### Requirement: Remoção de PDF substituído

O sistema SHALL remover o PDF em disco de uma bula ao baixar uma versão mais recente do mesmo medicamento — NÃO ao concluir o processamento.

#### Scenario: Novo PDF baixado para medicamento já cadastrado
- **WHEN** o processo de aquisição baixa um novo PDF para um `id_bula_anvisa` diferente do registrado, mas para o mesmo medicamento
- **THEN** o PDF anterior é removido de `docs/bulas/` antes de salvar o novo, e o campo `caminho_pdf` é atualizado no banco
