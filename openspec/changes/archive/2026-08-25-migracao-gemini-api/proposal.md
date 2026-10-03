## Why

A abordagem de rodar LLM localmente via Ollama se provou impraticável para o prazo do TCC: modelos locais geram saídas JSON malformadas com frequência, exigem warmup complexo para ajuste de `num_ctx`, e dependem de hardware disponível. A mudança para Gemini via API elimina esses problemas com ganho imediato de qualidade e confiabilidade de extração.

## What Changes

- `LLM_PROVIDER` passa de `ollama` (default) para `gemini` como provider de produção.
- `LLM_MODEL` passa de `qwen2.5:7b` para um modelo Gemini (recomendado: `gemini-2.0-flash`).
- `google-genai` é adicionado explicitamente ao `pyproject.toml` (atualmente dependência transitiva não declarada).
- `.env` é atualizado com as configurações corretas para Gemini; variáveis específicas de Ollama (`LLM_NUM_CTX`, `OLLAMA_BASE_URL`) ficam comentadas como legado.
- Verificação funcional end-to-end confirma que tool calling (`consultar_secao_bula`) e saída estruturada (JSON schema via pydantic-ai) funcionam com Gemini.

## Capabilities

### New Capabilities

_Nenhuma._

### Modified Capabilities

- `extracao-llm`: Adicionar requisito de compatibilidade com Gemini API — model name, dependência explícita `google-genai`, e comportamento de provider Gemini verificado (tool calling + saída estruturada).

## Impact

- `pyproject.toml` — nova dependência explícita `google-genai`.
- `.env` — alteração de valores de `LLM_PROVIDER` e `LLM_MODEL`; usuário deve preencher `GEMINI_API_KEY`.
- `backend/extracao/agente.py` — nenhuma mudança de código necessária; suporte Gemini já implementado.
- `backend/config.py` — nenhuma mudança necessária; `gemini_api_key` já está mapeado.
- Variáveis de Ollama (`OLLAMA_BASE_URL`, `LLM_NUM_CTX`) tornam-se irrelevantes para produção mas permanecem no código para retrocompatibilidade.
