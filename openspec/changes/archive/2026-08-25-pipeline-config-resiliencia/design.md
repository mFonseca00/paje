## Context

Ver `proposal.md — Why` para motivação. Estado atual relevante:

- `backend/config.py` usa `pydantic-settings` com `.env`. Todos os parâmetros operacionais ficam em `Settings`.
- `backend/extracao/agente.py` instancia `Agent` e `_criar_modelo()` como singletons de módulo (executados na importação). Isso limita quando e como as settings são lidas.
- `_criar_modelo()` para ollama cria `OpenAIChatModel(settings.llm_model, provider=ollama_provider)` — sem `num_ctx`.
- `Agent(...)` não passa `max_result_retries` — usa default pydantic-ai de `1`.
- Preprocessamento (conversão PDF → markdown) existe em `backend/preprocessamento/` mas só é invocado inline por `_garantir_markdown()` dentro do pipeline de extração.
- Não existe script de orquestração; cada etapa tem seu próprio script `executar_*.py`.

## Goals / Non-Goals

**Goals:**
- `LLM_NUM_CTX` aplicado ao model ollama via extra args da API
- `LLM_MAX_RESULT_RETRIES` passado ao `Agent()`
- `EXTRACAO_REPROCESSAR_ERRO` como default configurável (CLI `--reprocessar-erro` ainda funciona como override explícito)
- `executar_pipeline.py` sequencial com flags de etapa
- Preprocessamento como etapa nomeada no pipeline (sem remover fallback inline da extração)

**Non-Goals:**
- Paralelismo entre etapas ou execução concorrente de bulas
- Monitoramento, healthcheck ou retry automático de falhas de rede
- Alteração do schema do banco
- Modificar os scripts individuais `executar_aquisicao.py` / `executar_extracao.py` além do mínimo necessário

## Decisions

### D1: `num_ctx` via `model_kwargs` / `extra_body` na chamada OpenAI-compat

**Decisão:** Passar `num_ctx` como parâmetro de opções do provider ollama.

O `OpenAIChatModel` do pydantic-ai aceita `model_settings` que são repassados à chamada HTTP. Para ollama, o endpoint `/v1/chat/completions` aceita `options.num_ctx` no body. Isso pode ser feito via `OpenAIChatModel(..., model_settings={'options': {'num_ctx': N}})` ou equivalente conforme a versão do pydantic-ai.

**Alternativa descartada:** Usar `Modelfile` do ollama para fixar `num_ctx` — requer intervenção manual fora do `.env` e não é portável entre máquinas.

**Alternativa descartada:** Chamar `ollama.Client` diretamente em vez de via pydantic-ai — quebraria a abstração de provider e dificultaria troca futura.

### D2: `EXTRACAO_REPROCESSAR_ERRO` como default, flag CLI como override

**Decisão:** `executar_extracao()` usa `settings.extracao_reprocessar_erro` como default para o parâmetro `reprocessar_erro`, mas o flag `--reprocessar-erro` no CLI ainda pode sobrescrever para `true`. Não há override para `false` via CLI (não é necessário: o default já é `false`).

**Alternativa descartada:** Remover o flag CLI e deixar só o `.env` — perde flexibilidade de execução manual pontual sem editar `.env`.

### D3: `executar_pipeline.py` chama funções Python diretamente (não subprocess)

**Decisão:** Importar e chamar `executar_aquisicao()`, `executar_preprocessamento_lote()` e `executar_extracao()` como funções Python, não via `subprocess.run(["python", "executar_aquisicao.py", ...])`.

**Motivo:** Evita overhead de processo, compartilha contexto de log, permite capturar o `ResumoAquisicao`/`ResumoExtracao` para exibir resumo consolidado ao final.

### D4: Preprocessamento em lote como função separada

**Decisão:** Extrair a lógica de `_garantir_markdown()` para uma função `executar_preprocessamento_lote(limite)` em `backend/extracao/pipeline.py` (ou em `backend/preprocessamento/pipeline.py`). Essa função itera sobre bulas `PENDENTE` sem markdown e pré-gera os arquivos. A extração mantém o fallback inline (`_garantir_markdown` continua existindo).

**Motivação:** Evitar criar um novo módulo desnecessário. O preprocessamento já usa código de `backend/preprocessamento/`; centralizá-lo em `pipeline.py` é mais coeso que um quarto script pipeline isolado.

### D5: Flags `PIPELINE_*_HABILITADA` lidas do settings

**Decisão:** Adicionar `pipeline_aquisicao_habilitada: bool = True`, `pipeline_preprocessamento_habilitada: bool = True`, `pipeline_extracao_habilitada: bool = True` em `Settings`. `executar_pipeline.py` verifica cada flag antes de invocar a etapa.

## Risks / Trade-offs

- **`num_ctx` via `model_settings` pode mudar entre versões do pydantic-ai** → Mitigação: verificar a versão instalada e documentar no `.env.example` que requer pydantic-ai ≥ versão X (a verificar na implementação).
- **Singletons de módulo em `agente.py`** (`_sistema`, `_modelo`, `agente`) são criados na importação. Se `settings` mudar em runtime (ex: testes que sobrescrevem env vars), o agente não reflete as mudanças → Isso já era uma limitação; não piora com esta mudança.
- **Falha em etapa do pipeline não aborta as seguintes** → Decisão de design: cada etapa reporta erros no resumo mas o pipeline continua. Etapas são independentes — uma falha de aquisição não deve impedir extração de bulas já baixadas.

## Migration Plan

1. Adicionar novas variáveis em `Settings` com defaults que preservam o comportamento atual (sem mudança para quem não alterar o `.env`).
2. Atualizar `agente.py` para ler `settings.llm_num_ctx` e `settings.llm_max_result_retries`.
3. Criar `executar_preprocessamento_lote()` sem remover `_garantir_markdown`.
4. Criar `executar_pipeline.py`.
5. Documentar as novas variáveis no `.env.example`.

Rollback: remover as novas variáveis de `Settings` e reverter `agente.py` — sem impacto em banco ou dados.
