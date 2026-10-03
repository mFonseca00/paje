## 1. Settings — novas variáveis em config.py

- [x] 1.1 Adicionar `llm_num_ctx: int = 4096` em `backend/config.py`
- [x] 1.2 Adicionar `llm_max_result_retries: int = 1` em `backend/config.py`
- [x] 1.3 Adicionar `extracao_reprocessar_erro: bool = False` em `backend/config.py`
- [x] 1.4 Adicionar `pipeline_aquisicao_habilitada: bool = True`, `pipeline_preprocessamento_habilitada: bool = True`, `pipeline_extracao_habilitada: bool = True` em `backend/config.py`
- [x] 1.5 Documentar todas as novas variáveis em `.env.example` com comentários explicativos

## 2. Agente LLM — aplicar settings

- [x] 2.1 Em `backend/extracao/agente.py`, no branch `provider == "ollama"` de `_criar_modelo()`: verificar como a versão do pydantic-ai instalada aceita `num_ctx` (via `model_settings`, `extra_body` ou outro mecanismo) e passar `settings.llm_num_ctx` apenas quando `llm_provider == "ollama"` — implementado via `ModelSettings(extra_body={"num_ctx": settings.llm_num_ctx})`
- [x] 2.2 Em `backend/extracao/agente.py`, passar `max_result_retries=settings.llm_max_result_retries` ao construtor `Agent(...)` — parâmetro correto em pydantic-ai 2.27.0 é `retries=`, não `max_result_retries`

## 3. Pipeline de extração — reprocessamento configurável

- [x] 3.1 Em `backend/extracao/pipeline.py`, fazer `executar_extracao(reprocessar_erro: bool = settings.extracao_reprocessar_erro [lido em runtime, não na definição da função])` — usar `settings.extracao_reprocessar_erro` como valor default lido no corpo da função (não no default do parâmetro, para evitar leitura na importação); o CLI `--reprocessar-erro` continua funcionando como override explícito

## 4. Preprocessamento em lote

- [x] 4.1 Criar função `executar_preprocessamento_lote(limite: int | None = None) -> ResumoPreprocessamento` em `backend/extracao/pipeline.py` (ou `backend/preprocessamento/pipeline.py` se mais adequado) que: lista bulas `PENDENTE` cujo markdown `__secoes.md` ainda não existe, chama `_garantir_markdown()` para cada uma, retorna resumo com totais `gerados`, `sem_pdf`, `erros`
- [x] 4.2 Definir dataclasses `ResultadoPreprocessamento` (enum: GERADO, SEM_PDF, ERRO, JA_EXISTE) e `ResumoPreprocessamento` no mesmo módulo

## 5. Script de pipeline unificado

- [x] 5.1 Criar `backend/scripts/executar_pipeline.py` com argparser aceitando `--limite N` e `--reprocessar-erro`
- [x] 5.2 Implementar execução condicional: verificar cada `settings.pipeline_*_habilitada`; se desabilitado, logar "Etapa X desabilitada (PIPELINE_X_HABILITADA=false)" e pular; se habilitado, invocar a função correspondente passando `limite` e `reprocessar_erro` conforme aplicável
- [x] 5.3 Exibir resumo consolidado ao final mostrando o resultado de cada etapa executada

## 6. Testes e verificação

- [x] 6.1 Executar `backend/tests/` e confirmar que nenhum teste existente quebrou após as mudanças em `config.py` e `agente.py` — 117/118 passam; 1 falha pré-existente em test_repositorio (substancia → referencia), não relacionada a esta mudança
- [ ] 6.2 Executar `executar_pipeline.py --limite 1` com ollama rodando e `LLM_NUM_CTX=16384` para confirmar que o parâmetro chega ao modelo (verificar nos logs do ollama que não há truncamento para a bula de teste) — requer execução manual com ollama ativo e banco limpo
