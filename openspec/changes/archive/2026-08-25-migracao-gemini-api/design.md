## Context

O código em `backend/extracao/agente.py` já implementa o branch `gemini` em `_criar_modelo()` usando `pydantic_ai.models.google.GoogleModel` e `pydantic_ai.providers.google.GoogleProvider`. O `google-genai` 2.7.0 está instalado (dependência transitiva via `pydantic-ai`). O `config.py` já mapeia `GEMINI_API_KEY`. Nenhuma mudança de código de produção é necessária — a mudança é de configuração e verificação.

## Approach

**1. Adicionar `google-genai` ao `pyproject.toml`**

Elevar de dependência transitiva para declarada explicitamente, com versão mínima compatível:

```toml
"google-genai>=1.0",
```

Isso garante que um `pip install -e .` limpo instale o SDK sem depender de que `pydantic-ai` o puxe transitivamente.

**2. Atualizar `.env`**

Trocar provider/modelo e adicionar a chave:

```env
LLM_PROVIDER=gemini
LLM_MODEL=gemini-2.0-flash
GEMINI_API_KEY=<chave obtida em aistudio.google.com>
```

Comentar (não remover) as variáveis específicas de Ollama (`OLLAMA_BASE_URL`, `LLM_NUM_CTX`) para retrocompatibilidade do dev environment.

**3. Verificação funcional**

Executar `backend/scripts/testar_extracao.py` apontado para uma bula real com `LLM_PROVIDER=gemini`. Validar:

- Saída JSON válida com `contraindicacoes` e `interacoes`.
- Tool `consultar_secao_bula` invocada quando há referência cruzada.
- Status da bula atualizado para `PROCESSADO` no banco.

Se o script de teste não suportar override de provider via argumento, executar diretamente via `.env`.

## Key Decisions

- **Modelo padrão: `gemini-2.0-flash`** — boa relação custo/qualidade para extração clínica em PT-BR. Outros modelos Gemini (Flash 1.5, Pro) funcionam mas são mais caros ou mais lentos.
- **Sem warmup para Gemini** — o branch Ollama em `_criar_modelo()` chama `_aquecer_ollama()`. Para Gemini isso não existe nem é necessário; o código já contorna corretamente.
- **`LLM_NUM_CTX` ignorado para Gemini** — o `config.py` lê o valor mas `_criar_modelo()` só passa `num_ctx` no branch Ollama. Nenhuma mudança necessária.
- **Prompt sem alteração** — o prompt `prompts/extracao_v1.md` é agnóstico de modelo. Gemini interpreta few-shot corretamente.
