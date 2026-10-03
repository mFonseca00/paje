## Purpose

Orquestra a execução sequencial das etapas de aquisição, preprocessamento e extração como um pipeline configurável por variáveis de ambiente, eliminando a necessidade de invocar cada script manualmente.

## Requirements

### Requirement: Controle de contexto LLM via configuração

O sistema SHALL expor a variável `LLM_NUM_CTX` em `.env` para definir o tamanho da janela de contexto do modelo LLM. Quando o provider for `ollama`, esse valor SHALL ser passado ao modelo no momento da criação. Providers externos (anthropic, openai, gemini) SHALL ignorar essa configuração. O valor default SHALL ser `4096`.

#### Scenario: Ollama usa num_ctx configurado

- **WHEN** `LLM_PROVIDER=ollama` e `LLM_NUM_CTX=16384`
- **THEN** o modelo ollama é criado com `num_ctx=16384`, expandindo a janela de contexto disponível para o prompt

#### Scenario: Provider externo ignora num_ctx

- **WHEN** `LLM_PROVIDER=anthropic` (ou openai ou gemini) e `LLM_NUM_CTX=16384`
- **THEN** o sistema inicializa normalmente sem passar `num_ctx`, pois providers externos gerenciam contexto internamente

### Requirement: Retries de validação estrutural configuráveis

O sistema SHALL expor a variável `LLM_MAX_RESULT_RETRIES` em `.env` para controlar quantas vezes o agente pydantic-ai tenta obter uma resposta estruturalmente válida do modelo. O valor SHALL ser passado ao `Agent(max_result_retries=...)`. O valor default SHALL ser `1`.

#### Scenario: Modelo retorna JSON inválido e agente retenta

- **WHEN** o modelo retorna resposta que não passa na validação Pydantic e `LLM_MAX_RESULT_RETRIES=3`
- **THEN** o agente retenta até 3 vezes antes de lançar exceção

#### Scenario: Sem retries configurados

- **WHEN** `LLM_MAX_RESULT_RETRIES=0`
- **THEN** o agente lança exceção imediatamente na primeira falha de validação, sem retentativas

### Requirement: Reprocessamento automático de ERROs na extração

O sistema SHALL expor a variável `EXTRACAO_REPROCESSAR_ERRO` em `.env` (booleano). Quando `true`, o pipeline de extração SHALL incluir automaticamente bulas com status `ERRO` na fila de processamento, sem necessidade de flag `--reprocessar-erro` no CLI. O valor default SHALL ser `false`.

#### Scenario: Pipeline reprocessa ERROs automaticamente

- **WHEN** `EXTRACAO_REPROCESSAR_ERRO=true` e existem bulas com status `ERRO`
- **THEN** essas bulas são incluídas na fila de extração juntamente com as `PENDENTE`

#### Scenario: Comportamento padrão preserva ERROs

- **WHEN** `EXTRACAO_REPROCESSAR_ERRO=false` (default)
- **THEN** somente bulas `PENDENTE` são processadas; bulas `ERRO` permanecem intocadas

### Requirement: Script de pipeline unificado

O sistema SHALL prover o script `backend/scripts/executar_pipeline.py` que executa as etapas na ordem: aquisição → preprocessamento → extração. Cada etapa SHALL ser controlada por variável booleana em `.env`:

- `PIPELINE_AQUISICAO_HABILITADA` (default `true`)
- `PIPELINE_PREPROCESSAMENTO_HABILITADA` (default `true`)
- `PIPELINE_EXTRACAO_HABILITADA` (default `true`)

Etapas desabilitadas SHALL ser puladas silenciosamente com log informativo. O script SHALL aceitar os mesmos argumentos CLI das etapas individuais (`--limite`, `--reprocessar-erro`) e passá-los para cada etapa habilitada.

#### Scenario: Pipeline completo executa todas as etapas

- **WHEN** todas as flags estão `true` e o script é executado sem argumentos
- **THEN** aquisição é executada primeiro, depois preprocessamento, depois extração; cada etapa reporta seu próprio resumo

#### Scenario: Etapa desabilitada é pulada

- **WHEN** `PIPELINE_AQUISICAO_HABILITADA=false`
- **THEN** o script pula aquisição, loga "Etapa aquisição desabilitada", e prossegue para preprocessamento

#### Scenario: Limite propagado para todas as etapas habilitadas

- **WHEN** `executar_pipeline.py --limite 10`
- **THEN** cada etapa habilitada processa no máximo 10 itens

### Requirement: Preprocessamento como etapa explícita com fallback

O script `executar_pipeline.py` SHALL invocar o preprocessamento (conversão PDF → markdown) como etapa separada antes da extração. A extração SHALL continuar a gerar markdown inline para bulas sem arquivo markdown (fallback), sem quebrar o comportamento atual.

#### Scenario: Pipeline pré-converte markdowns

- **WHEN** etapa de preprocessamento está habilitada
- **THEN** todos os PDFs com status `PENDENTE` sem markdown correspondente são convertidos antes da extração iniciar

#### Scenario: Extração gera markdown como fallback

- **WHEN** etapa de preprocessamento está desabilitada mas extração está habilitada, e uma bula não tem markdown
- **THEN** a extração gera o markdown inline, mantendo o comportamento atual
