## Context

Ver `proposal.md — Why` para motivação.

`_adquirir` em `backend/aquisicao/fluxo.py` executa sempre: busca ANVISA → seleciona resultado → obtém JWT → verifica duplicata no banco. A verificação de disco só ocorre dentro do bloco de duplicata, após o HTTP call.

O banco já possui a relação `medicamento → bulas` com `caminho_pdf` e `status_processamento_ia`. A informação necessária para a pre-checagem está disponível localmente sem nenhum schema change além do novo campo de timestamp.

## Goals / Non-Goals

**Goals:**
- Eliminar requests ANVISA para medicamentos com PDF válido em disco.
- Adicionar `ultima_verificacao_anvisa` no modelo e na migration sem alterar comportamento atual.

**Non-Goals:**
- Implementar verificação periódica baseada em data (futuro).
- Alterar qualquer outro fluxo (extração, preprocessamento).

## Decisions

**D1 — Inserir pre-checagem no início de `_adquirir`, antes de qualquer request HTTP.**

A lógica reutiliza `buscar_medicamento_por_nome` já existente. Se o medicamento tem ao menos uma bula com `caminho_pdf` válido em disco e `status ≠ ERRO`, retorna SKIP imediatamente.

Alternativa descartada: checar antes de chamar `adquirir_medicamento` no loop de `executar_aquisicao`. Rejeitada porque polui o nível errado de abstração — a decisão de skip pertence à lógica de aquisição individual, não ao orquestrador.

**D2 — `ultima_verificacao_anvisa` como `DateTime(timezone=True)` nullable em `Bula`.**

Nullable porque: (a) bulas existentes no banco não têm histórico de verificação, (b) bulas puladas pela pre-checagem local nunca passaram por verificação online. O campo só é preenchido quando a ANVISA é efetivamente consultada e a bula é criada ou confirmada.

Alternativa descartada: campo na tabela `medicamentos`. Rejeitada porque a granularidade correta é por bula (cada JWT tem sua própria data de validade implícita).

**D3 — Atualizar `ultima_verificacao_anvisa` em `criar_bula` e em `atualizar_status_bula` ao confirmar SKIP online.**

`criar_bula` recebe `ultima_verificacao_anvisa=datetime.utcnow()` no download. Para SKIP online (Cenários A/C), `atualizar_status_bula` recebe o campo opcionalmente. Pre-checagem local não toca o campo.

## Risks / Trade-offs

**[Risco] Medicamento adquirido com PDF antigo que a ANVISA substituiu silenciosamente.**
→ O comportamento atual (Cenário C) já aceita isso: JWT novo + PDF em disco = SKIP. Esta change não piora o risco existente; apenas evita o request que confirmaria o skip. `ultima_verificacao_anvisa` futuro permitirá detectar bulas não verificadas há N dias.

**[Risco] `buscar_medicamento_por_nome` carrega todas as bulas do medicamento via `med.bulas`.**
→ Risco baixo: um medicamento tem tipicamente 1-2 bulas. Não justifica query especializada.

## Migration Plan

1. Adicionar coluna `ultima_verificacao_anvisa TIMESTAMP WITH TIME ZONE NULL` à tabela `bulas` via migration Alembic.
2. Bulas existentes ficam com `NULL` — sem backfill necessário.
3. Deploy sem downtime: coluna nullable, sem constraint NOT NULL, código antigo ignora o campo.
4. Rollback: remover coluna (sem perda de dados funcionais).

## Open Questions

Nenhuma.
