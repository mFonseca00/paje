## Context

Ver proposal.md — Why. Dois pontos de falha em `_adquirir()` em `backend/aquisicao/fluxo.py`:

1. Branch `bula_existente is not None and status != ERRO`: retorna SKIP sem checar `Path(caminho_pdf).exists()`.
2. Branch de download (bula_existente is None): não verifica se o medicamento já tem PDF válido em disco antes de baixar; após baixar, não remove registros fantasma do banco.

## Goals / Non-Goals

**Goals:**
- Garantir que nenhum re-download ocorra quando PDF válido já existe em disco
- Garantir que registros com `caminho_pdf` inválido sejam resolvidos (re-download ou remoção)
- Manter o banco consistente: exatamente um registro ativo por medicamento após cada aquisição

**Non-Goals:**
- Detectar atualização de conteúdo da bula (re-download forçado por conteúdo novo)
- Consolidar medicamentos duplicados por outros critérios (fora do escopo)

## Decisions

**D1 — Verificação de arquivo no branch de SKIP (mesmo JWT)**

Antes de retornar SKIP, checar `Path(bula_existente.caminho_pdf).exists()`. Se ausente, prosseguir para re-download e atualizar `caminho_pdf` via `atualizar_status_bula(..., caminho_pdf=str(destino))`.

**D2 — Verificação de medicamento com PDF válido antes do download (JWT novo)**

Imediatamente após `buscar_bula_por_id_anvisa` retornar None, buscar o medicamento e checar se alguma bula já tem arquivo em disco:

```python
med = buscar_medicamento_por_nome(session, nome)
if med:
    bulas_validas = [b for b in med.bulas if b.caminho_pdf and Path(b.caminho_pdf).exists()]
    if bulas_validas:
        return LogAquisicao(resultado=ResultadoAquisicao.SKIP, ...)
```

Isso evita o download e mantém o registro existente intacto.

**D3 — Remoção de registros fantasma antes de criar novo (JWT novo, sem arquivo)**

Quando nenhuma bula do medicamento tem arquivo em disco, deletar os registros existentes antes de `criar_bula()`. Requer nova função `deletar_bulas_por_medicamento(session, medicamento_id)` no repositório, ou deleção inline via `session.delete(b)` no loop.

Alternativa descartada: marcar como `SUBSTITUIDO` em vez de deletar — adiciona complexidade de estado sem benefício observável para este projeto.

**D4 — Novo enum `RECUPERADO` em `ResultadoAquisicao`**

Distingue re-downloads por arquivo ausente (cenário B) de downloads normais (`BAIXADO`). Facilita auditoria.

**D5 — `med` buscado uma única vez antes do download**

O bloco "Remoção do PDF anterior" (linha 254) já busca `med`. Com D2, essa busca precisa acontecer antes da decisão de download. Consolidar para evitar duas queries ao banco.

## Risks / Trade-offs

- [Risco] Se ANVISA rotacionar JWT mas o arquivo existente estiver corrompido, o SKIP do cenário C impedirá re-download → aceito: detecção de corrupção fora do escopo
- [Trade-off] Deleção de registros fantasma é irreversível → mitigado por log antes da deleção
- [Trade-off] `med` buscado antes do download muda a ordem de operações → sem impacto funcional, lógica equivalente
