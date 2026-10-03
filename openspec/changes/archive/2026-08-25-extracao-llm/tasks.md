<!-- INSTRUÇÕES DE APPLY: implemente uma tarefa por vez quando solicitado.
     Pare ao final da fase e aguarde validação manual antes de continuar. -->
<!-- PAUSA ao final: verificar tabelas substancias_medicamento, contraindicacoes e interacoes_medicamentosas com dados reais; inspecionar visualmente a qualidade das extrações -->

## Banco de dados

- [x] 1 Criar migration Alembic para: (a) renomear coluna `substancia` para `referencia` em `interacoes_medicamentosas`; (b) adicionar coluna `tipo VARCHAR NOT NULL` em `interacoes_medicamentosas`; (c) tornar coluna `efeito` nullable em `interacoes_medicamentosas`
- [x] 2 Criar migration Alembic para criar tabela `substancias_medicamento(id, medicamento_id, nome)` e implementar lógica de preenchimento via split do `nome_dcb` por `+` na etapa de aquisição

## Extração clínica (etapa única)

- [x] 3 Definir schema Pydantic para saída: `ContraIndicacao(id: int, descricao: str)` e `InteracaoMedicamentosa(id: int, tipo: Literal["NOME_DIRETO","CLASSE","ALIMENTO"], referencia: str, efeito: str | None)`
- [x] 4 Criar prompt few-shot em `prompts/extracao_v1.md`, incluindo instrução para invocar a tool quando o texto referenciar seções fora das seções 3 e 4
- [x] 5 Implementar tool `consultar_secao_bula(referencia: str) -> str` que retorna o conteúdo da seção referenciada a partir do `__bruto.md` da bula em processamento
- [x] 6 Implementar agente Pydantic AI para extração clínica com a tool registrada (Ollama local; suporte a providers externos via `.env`)
- [x] 7 Implementar suporte a providers de API externos (Anthropic, OpenAI, Gemini) como alternativa ao Ollama, configurável via `LLM_PROVIDER`
- [x] 8 Criar script CLI `scripts/testar_extracao.py` que processa uma única bula e salva o JSON extraído em `output/<nome_bula>_extracao.json`
- [x] 9 Documentar em `docs/benchmark_modelos.md`: modelos Ollama candidatos sugeridos (ex.: llama3.2, mistral, qwen2.5) e passo a passo para benchmark manual — como rodar cada modelo com `testar_extracao.py` e comparar os JSONs gerados visualmente
- [x] 10 Implementar validação da saída JSON do modelo contra o schema Pydantic; em falha, preservar resposta bruta e marcar bula como `ERRO`
- [x] 11 Implementar versionamento de prompt: salvar identificador da versão em cada registro de bula
- [x] 12 Implementar gravação no banco: resposta bruta em JSONB, entidades normalizadas em `contraindicacoes` e `interacoes_medicamentosas`, atualização de status para `PROCESSADO` ou `ERRO`
- [x] 13 Implementar runner da pipeline de extração em lote para todas as bulas com status `PENDENTE`
- [x] 14 Criar script CLI `scripts/executar_extracao.py` que roda o batch (com flag `--limite N` para testes parciais)
- [x] 15 Criar testes unitários para o módulo de extração (`tests/test_extracao.py`) com mock do agente LLM

## ~~Few-shot com exemplos externos (ajuste de D3)~~ — REVERTIDO

- [x] ~~16 Remover exemplos inline de `prompts/extracao_v1.md` — manter apenas as instruções do sistema~~
- [x] ~~17 Implementar `_montar_contexto_fewshot()` em `agente.py`~~
- [x] ~~18 Integrar o contexto few-shot na chamada ao agente~~
- [x] ~~19 Atualizar testes unitários em `tests/test_extracao.py` para cobrir a montagem do contexto few-shot~~

## ~~Correção do delimitador few-shot (D3-adendo)~~ — REVERTIDO

- [x] ~~20 Adicionar sentença de fechamento ao final de `_montar_contexto_fewshot()`~~
- [x] ~~21 Atualizar teste `test_contexto_nao_vazio` em `test_extracao.py`~~

## Retorno a exemplos inline no prompt (revisão de D3)

- [x] 22 Reescrever `prompts/extracao_v1.md` incluindo as instruções + os 4 exemplos few-shot + sentença de fechamento diretamente no arquivo — manter `prompts/exemplos/` intacta como repositório de referência
- [x] 23 Remover `_montar_contexto_fewshot()` de `agente.py` e simplificar a inicialização do singleton: `_sistema = _carregar_prompt(settings.prompt_version)`
- [x] 24 Atualizar `test_extracao.py`: remover a classe `TestFewshot` (6 testes dependiam de `_montar_contexto_fewshot`); remover import da função removida

## Simplificações de código

- [x] 25 `pipeline.py` — substituir `except (ValidationError, Exception)` por `except Exception` (`ValidationError` é subclasse de `Exception`; a tupla é redundante e induz leitura errada)
- [x] 26 `pipeline.py` — remover bloco `try/except` interno que envolve `resposta_bruta = {"erro": str(e)}` (`str(e)` nunca levanta exceção; defesa sem alvo)
- [x] 27 `pipeline.py` — remover verificação morta `if not bula.caminho_pdf:` dentro de `_garantir_markdown` após `_caminhos_markdown` retornar não-None (condição nunca é verdadeira nesse ponto)
- [x] 28 `pipeline.py` — inlinear `_caminhos_markdown()` dentro de `_garantir_markdown()` (5 linhas, único chamador, nível de abstração não se justifica)
- [x] 29 `pipeline.py` — remover comentários `# Task N:` (artefatos do processo de desenvolvimento)
- [x] 30 `agente.py` — mover cálculo de `ref_texto` para fora do loop em `_buscar_secao()` (valor não varia entre iterações; posição atual implica dependência que não existe)
- [x] 31 `agente.py` — encurtar docstring de `extrair_bula()` para uma linha (4 linhas de corpo; Args/Returns/Raises é desproporcional)
