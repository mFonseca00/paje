<!-- INSTRUÇÕES DE APPLY: implemente uma tarefa por vez. Rode os testes existentes após cada grupo.
     Nenhum comportamento observável deve mudar. -->

## 1. Utilitário de texto compartilhado (D1)

- [x] 1.1 Criar `backend/utils/__init__.py` (vazio) e `backend/utils/texto.py` com a função `_normalizar` extraída de `rename.py`
- [x] 1.2 Em `backend/aquisicao/rename.py`: remover definição local de `_normalizar` e importar de `backend.utils.texto`
- [x] 1.3 Em `backend/aquisicao/referencia.py`: remover definição local de `_normalizar` e importar de `backend.utils.texto`
- [x] 1.4 Verificar que `carregar_nomes_rename()` e `carregar_nomes_comerciais()` retornam os mesmos valores de antes

## 2. Renomear `id` → `id` nos schemas de extração (D8)

- [x] 2.1 Em `backend/extracao/schemas.py`: renomear campo `id` para `id` em `ContraIndicacao` e `InteracaoMedicamentosa`
- [x] 2.2 Em `backend/extracao/pipeline.py`: ajustar qualquer referência a `.id` dos schemas de extração (se existir)
- [x] 2.3 Em `prompts/extracao_v1.md`: atualizar exemplos JSON que referenciam o campo `id` id para usar `id`
- [x] 2.4 Rodar extração em amostra de 1 bula e confirmar output JSON usa `id`

## 3. Repositório SQLAlchemy 2.x (D3)

- [x] 3.1 Em `backend/armazenamento/repositorio.py`: adicionar import `from sqlalchemy import select`
- [x] 3.2 Converter `buscar_medicamento_por_nome` de `session.query().filter()` para `session.scalars(select(...).where(...)).first()`
- [x] 3.3 Converter `buscar_bula_por_id_anvisa` da mesma forma
- [x] 3.4 Converter `listar_bulas_por_status`, `listar_contraindicacoes_por_bula`, `listar_interacoes_por_bula`, `listar_substancias_por_medicamento` e `listar_medicamentos`
- [x] 3.5 Rodar `backend/tests/test_repositorio.py` e confirmar zero falhas

## 4. Inicialização lazy do agente LLM (D4)

- [x] 4.1 Em `backend/extracao/agente.py`: remover as linhas de nível de módulo `_sistema = _carregar_prompt(...)` e `_modelo = _criar_modelo()` e a declaração de `agente` no topo do arquivo
- [x] 4.2 Criar função `_get_agente() -> Agent` com variável global `_agente: Agent | None = None` que inicializa na primeira chamada (padrão singleton)
- [x] 4.3 Em `extrair_bula()`: substituir uso direto de `agente` por `_get_agente()`
- [x] 4.4 Adicionar comentário breve em `_get_agente` explicando por que não é thread-safe (ver design.md D4)
- [x] 4.5 Confirmar que importar `backend.extracao.agente` sem chamar `extrair_bula` não inicia nenhum modelo

## 5. `markdown_dir` via settings (D5)

- [x] 5.1 Em `backend/config.py`: adicionar campo `markdown_dir: str = "docs/markdown_bulas"`
- [x] 5.2 Em `backend/extracao/pipeline.py`: substituir `_MARKDOWN_DIR = Path("docs/markdown_bulas")` por `_MARKDOWN_DIR = Path(settings.markdown_dir)` (ou inlinar diretamente onde usado)

## 6. Padronização de config.py (D9)

- [x] 6.1 Em `backend/config.py`: remover `Field(default=...)` de `rename_path`, `referencia_lista_a_path` e `referencia_lista_b_path`, deixando apenas o valor literal como default
- [x] 6.2 Remover import de `Field` de `pydantic` se não for mais usado em nenhum campo

## 7. Decomposição de `_adquirir` em `fluxo.py` (D2)

- [x] 7.1 Extrair lógica de pré-checagem local (antes da busca ANVISA) para `_skip_por_pre_checagem_local(session, nome, reprocessar_erro) -> LogAquisicao | None`
- [x] 7.2 Extrair cenário "arquivo ausente, mesmo JWT" para `_recuperar_arquivo_ausente(session, bula_existente, nome, nome_dcb, client) -> LogAquisicao`
- [x] 7.3 Extrair cenário "bula com ERRO, reprocessar solicitado" para `_reprocessar_bula_com_erro(session, bula_existente, nome) -> LogAquisicao`
- [x] 7.4 Extrair cenário "JWT rotacionado, PDF válido em disco" para `_skip_jwt_rotacionado(session, med, nome, id_bula) -> LogAquisicao | None`
- [x] 7.5 Reescrever `_adquirir` como dispatcher que chama cada helper em ordem e retorna o primeiro resultado não-None; download real permanece inline no dispatcher
- [x] 7.6 Rodar `backend/tests/test_aquisicao.py` e confirmar zero falhas

## 8. Context manager para sessões (D6)

- [x] 8.1 Em `backend/aquisicao/fluxo.py`: substituir padrão `session = get_session(); try: ...; finally: session.close()` por `with SessionLocal() as session:` nos pontos onde `_adquirir` cria sessão
- [x] 8.2 Em `backend/extracao/pipeline.py`: mesma substituição em `processar_bula` e `executar_preprocessamento_lote`
- [x] 8.3 Confirmar que `get_session()` ainda existe para compatibilidade com `backend/scripts/testar_banco.py`

## 9. Remoção de sys.path.insert nos scripts (D7)

- [x] 9.1 Em cada arquivo de `backend/scripts/`: remover o bloco `sys.path.insert(0, ...)` e imports de `sys` e `Path` usados apenas por ele
- [x] 9.2 Confirmar que `python backend/scripts/executar_pipeline.py --ajuda` funciona com o pacote instalado via `pip install -e .`
