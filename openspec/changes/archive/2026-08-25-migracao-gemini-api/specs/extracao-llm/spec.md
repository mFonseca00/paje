## MODIFIED Requirements

### Requirement: Suporte a modelos locais via Ollama

O sistema SHALL suportar execução da inferência usando modelos locais via Ollama como alternativa ao uso de APIs externas. O sistema SHALL também suportar Gemini como provider de produção via `google-genai` SDK, declarado como dependência explícita no `pyproject.toml`. Quando `LLM_PROVIDER=gemini`, o sistema SHALL funcionar corretamente incluindo tool calling e saída estruturada JSON validada via Pydantic.

O modelo Gemini recomendado é `gemini-2.0-flash`. A chave de acesso SHALL ser lida de `GEMINI_API_KEY` no arquivo `.env`.

#### Scenario: Modelo local configurado

- **WHEN** a configuração aponta para um endpoint Ollama local
- **THEN** o sistema envia as requisições de inferência ao Ollama sem necessitar de chave de API externa

#### Scenario: Modelo remoto via API configurado

- **WHEN** a configuração define `LLM_PROVIDER` como `anthropic`, `openai` ou `gemini`
- **THEN** o sistema usa a chave de API correspondente (`ANTHROPIC_API_KEY`, `OPENAI_API_KEY` ou `GEMINI_API_KEY`) e envia as requisições ao provider configurado

#### Scenario: Gemini executa extração com tool calling

- **WHEN** `LLM_PROVIDER=gemini` e o texto das seções referencia outra seção da bula
- **THEN** o agente invoca `consultar_secao_bula` corretamente via Gemini function calling e incorpora o conteúdo na extração antes de retornar o JSON

#### Scenario: Gemini retorna saída estruturada válida

- **WHEN** `LLM_PROVIDER=gemini` e a extração é executada para uma bula
- **THEN** o modelo retorna JSON validado pelo schema Pydantic com `contraindicacoes` e `interacoes` corretamente tipadas
