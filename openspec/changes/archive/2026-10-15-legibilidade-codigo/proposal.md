## Why

O projeto Pajé será apresentado ao avaliador do TCC com o código-fonte aberto para inspeção. O código atual funciona, mas acumula inconsistências e decisões implícitas que dificultam a leitura e a explicação oral: funções longas, duplicação de utilidades, sessões de banco sem gestão explícita, efeitos colaterais de importação e convenções mistas de SQLAlchemy 1.x e 2.x. O objetivo desta change é elevar a clareza sem alterar nenhum comportamento observável.

## What Changes

- Extrair função `_normalizar` duplicada (`rename.py` e `referencia.py`) para `backend/utils/texto.py`
- Decompor `_adquirir` em `fluxo.py` (200+ linhas) em funções nomeadas por cenário
- Substituir `session.query()` por `select()` em `repositorio.py` (alinhamento SQLAlchemy 2.x)
- Converter inicialização do agente LLM em `agente.py` de eager (import-time) para lazy (primeira chamada)
- Mover `_MARKDOWN_DIR` de hardcoded em `pipeline.py` para `settings` em `config.py`
- Padronizar gestão de sessão de banco com context manager (`with SessionLocal() as session`)
- Remover `sys.path.insert` dos scripts em `backend/scripts/` (redundante dado `pyproject.toml`)
- Renomear `id` id em `extracao/schemas.py` para `id` para distinguir de PKs do banco
- Padronizar declarações de campo em `config.py` (remover `Field()` redundante)

## Capabilities

### New Capabilities

Nenhuma. Esta change é um refactor puro — nenhum comportamento observável muda.

### Modified Capabilities

Nenhuma. Nenhum requisito de sistema muda.

## Impact

- Arquivos afetados: `backend/utils/texto.py` (novo), `backend/aquisicao/rename.py`, `backend/aquisicao/referencia.py`, `backend/aquisicao/fluxo.py`, `backend/armazenamento/repositorio.py`, `backend/extracao/agente.py`, `backend/extracao/schemas.py`, `backend/extracao/pipeline.py`, `backend/config.py`, `backend/scripts/*.py`
- Nenhuma alteração de API, banco ou comportamento externo
- Testes existentes devem passar sem modificação após o refactor
