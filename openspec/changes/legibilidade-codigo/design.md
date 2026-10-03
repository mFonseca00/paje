## Context

Ver `proposal.md — Why` para motivação.

O backend é um pacote Python instalável via `pyproject.toml`, com SQLAlchemy 2.x (mapped columns) nos modelos mas ainda usando `session.query()` (1.x) no repositório. O agente LLM é inicializado no nível de módulo, acoplando o import ao carregamento do modelo. Dois módulos definem `_normalizar` identicamente. A função `_adquirir` em `fluxo.py` trata cinco cenários distintos em sequência linear, sem divisão por responsabilidade.

## Goals / Non-Goals

**Goals:**
- Cada arquivo Python explicável em ≤ 2 minutos de apresentação oral
- Nenhuma lógica duplicada entre módulos irmãos
- Convenções SQLAlchemy 2.x consistentes em todo o repositório
- Inicialização lazy do agente LLM (import não carrega modelo)
- Sessões de banco com context manager explícito
- Scripts executáveis sem manipulação de `sys.path`

**Non-Goals:**
- Alterar qualquer comportamento observável (resultados, banco, API)
- Adicionar cobertura de testes além do que já existe
- Refatorar o frontend (ainda não implementado)
- Otimizar desempenho

## Decisions

### D1 — Utilitário de texto em `backend/utils/texto.py`

`_normalizar` é idêntica em `rename.py` e `referencia.py`. Mover para `backend/utils/texto.py` e importar nos dois lugares.

*Alternativa considerada*: inline com comentário "ver referencia.py". Rejeitada — DRY é mais fácil de explicar que "intencionalmente duplicado".

### D2 — Decomposição de `_adquirir` em `fluxo.py`

Extrair cada cenário em função privada nomeada:
- `_skip_por_pre_checagem_local()` — PDF válido já em disco antes de qualquer request
- `_recuperar_arquivo_ausente()` — mesmo JWT, arquivo sumiu
- `_reprocessar_bula_com_erro()` — bula ERRO + flag ativada
- `_skip_jwt_rotacionado()` — JWT novo, PDF válido em outra entrada
- `_baixar_novo()` — caminho feliz, download real

`_adquirir` vira um dispatcher: chama cada helper em ordem e retorna o primeiro resultado não-None.

*Alternativa considerada*: manter monolítico com blocos de comentário separadores. Rejeitada — comentário não substitui nome de função para apresentação.

### D3 — `repositorio.py` para SQLAlchemy 2.x select()

Substituir `session.query(Model).filter(...)` por `session.scalars(select(Model).where(...)).all()` (ou `.first()`).

*Alternativa considerada*: manter 1.x e adicionar `# type: ignore`. Rejeitada — inconsistência com os modelos é a primeira coisa que um avaliador técnico notaria.

### D4 — Inicialização lazy do agente em `agente.py`

Transformar `_sistema` e `_modelo` em variáveis de módulo inicializadas por `_get_agente()`:

```python
_agente: Agent | None = None

def _get_agente() -> Agent:
    global _agente
    if _agente is None:
        _agente = _construir_agente()
    return _agente
```

`extrair_bula` chama `_get_agente()` em vez de usar `agente` diretamente.

*Alternativa considerada*: mover inicialização para `extrair_bula`. Rejeitada — múltiplas chamadas construiriam múltiplos modelos.

### D5 — `markdown_dir` em `config.py`

Adicionar `markdown_dir: str = "docs/markdown_bulas"` em `Settings`. `pipeline.py` usa `Path(settings.markdown_dir)`.

### D6 — Context manager para sessões de banco

`get_session()` permanece para compatibilidade, mas os chamadores em `fluxo.py` e `pipeline.py` passam a usar `with SessionLocal() as session:` diretamente onde é mais legível.

### D7 — Remoção de `sys.path.insert` nos scripts

O pacote está instalado via `pip install -e .` (pyproject.toml). Os scripts já funcionam sem a manipulação de path. Remover o bloco `sys.path.insert`.

### D8 — `ordinal` em `extracao/schemas.py`

Renomear `ContraIndicacao.id` e `InteracaoMedicamentosa.id` para `ordinal` no schema de extração. Isso evita confusão com PKs do banco durante explicações.

### D9 — Padronização de `config.py`

`Field(default=...)` sem validadores customizados é equivalente a atribuição direta em `pydantic-settings`. Remover `Field()` de `rename_path`, `referencia_lista_a_path`, `referencia_lista_b_path`.

## Risks / Trade-offs

- **D8 (renomear `id` → `ordinal`)** afeta `resposta_bruta_modelo` já gravada no banco (campo JSONB). Dados históricos conterão `"id"`, novos conterão `"ordinal"`. Risco baixo: o campo é auditoria, não lido pela aplicação. Mitigação: documentar na task.

- **D4 (lazy agente)** usa variável global mutável. Não é thread-safe. Aceitável: o projeto roda em modo síncrono com um processo. Mitigação: comentário explicando a limitação.

- **D3 (select() 2.x)** requer importação de `sqlalchemy.select`. Nenhuma quebra de API; mudança sintática apenas.

## Migration Plan

Cada decisão é independente — podem ser aplicadas em qualquer ordem. A ordem recomendada nas tasks segue dependências de importação: D1 (utils) primeiro, pois outros módulos o importam; D8 (schemas) antes de D3 (repositório) para evitar confusão nos testes.

Nenhum rollback de banco necessário.
