## 1. Dependências

- [x] 1.1 Adicionar `google-genai>=1.0` às dependências em `pyproject.toml`
- [x] 1.2 Executar `pip install -e .` para confirmar instalação limpa

## 2. Configuração

- [x] 2.1 Atualizar `.env`: definir `LLM_PROVIDER=gemini` e `LLM_MODEL=gemini-2.0-flash`
- [x] 2.2 Preencher `GEMINI_API_KEY` com chave obtida em aistudio.google.com
- [x] 2.3 Comentar `OLLAMA_BASE_URL` e `LLM_NUM_CTX` no `.env` (manter para dev, não são usados com Gemini)

## 3. Verificação Funcional

- [x] 3.1 Executar `backend/scripts/testar_extracao.py` com uma bula real e confirmar saída JSON válida
- [x] 3.2 Verificar no log que nenhum warmup Ollama é tentado quando `LLM_PROVIDER=gemini`
- [x] 3.3 Confirmar que o banco registra `status_processamento_ia=PROCESSADO` após extração bem-sucedida
- [x] 3.4 Confirmar que `contraindicacoes` e `interacoes` são gravadas corretamente no banco
