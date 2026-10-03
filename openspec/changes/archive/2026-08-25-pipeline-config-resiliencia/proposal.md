## Why

O sistema carece de configurabilidade operacional: o limite de contexto do modelo LLM está fixo em 4096 tokens (causando truncamento silencioso e extração incorreta), os retries de validação são hardcoded, bulas com ERRO de extração não são reprocessadas automaticamente, e não existe um script que encadeie as etapas (aquisição → preprocessamento → extração) em pipeline. Isso torna inviável a execução autônoma do sistema como previsto para o TCC.

## What Changes

- **Nova variável `.env` `LLM_NUM_CTX`**: configura o contexto do modelo ollama (outros providers ignoram). Default `4096`, recomendado `16384` para o qwen2.5:7b.
- **Nova variável `.env` `LLM_MAX_RESULT_RETRIES`**: número de retentativas de validação estrutural do pydantic-ai. Default `1`.
- **Nova variável `.env` `EXTRACAO_REPROCESSAR_ERRO`**: se `true`, o pipeline de extração reprocessa automaticamente bulas com status `ERRO`. Default `false`.
- **Novas variáveis `.env` de controle de pipeline**: `PIPELINE_AQUISICAO_HABILITADA`, `PIPELINE_PREPROCESSAMENTO_HABILITADA`, `PIPELINE_EXTRACAO_HABILITADA` (todas `true` por default).
- **Novo script `backend/scripts/executar_pipeline.py`**: orquestra as etapas na ordem correta conforme flags do `.env`. Pode ser invocado standalone.
- **Preprocessamento como etapa explícita no pipeline**: `executar_pipeline.py` invoca preprocessamento separadamente; a extração mantém geração inline como fallback (opção b — sem quebra de comportamento atual).
- **Passagem de `num_ctx` ao modelo ollama**: `agente.py` lê `settings.llm_num_ctx` e passa `num_ctx` ao criar o `OpenAIChatModel` ollama.
- **Passagem de `max_result_retries` ao agente**: `Agent(...)` recebe `max_result_retries=settings.llm_max_result_retries`.

## Capabilities

### New Capabilities

- `pipeline-unificada`: script que encadeia aquisição, preprocessamento e extração como etapas habilitáveis via `.env`

### Modified Capabilities

- `aquisicao-bulas`: nenhuma mudança de requisito de comportamento — sem delta spec
- `preprocessamento-pdf`: nenhuma mudança de requisito de comportamento — sem delta spec

## Impact

- `backend/config.py`: 5 novos campos (`llm_num_ctx`, `llm_max_result_retries`, `extracao_reprocessar_erro`, `pipeline_*`)
- `backend/extracao/agente.py`: `_criar_modelo()` e `Agent(...)` usam novas settings
- `backend/scripts/executar_pipeline.py`: novo arquivo
- `.env` / `.env.example`: novas variáveis documentadas
- Sem mudanças de schema de banco, sem breaking changes na API pública
