## Context

O banco de dados contém contra-indicações e interações medicamentosas extraídas e validadas. Esta fase expõe esses dados via uma API FastAPI e uma SPA React que permite ao usuário selecionar medicamentos e visualizar cruzamentos clínicos.

## Goals / Non-Goals

**Goals:**
- Definir os endpoints FastAPI necessários para a interface
- Definir os componentes React e o fluxo de interação
- Definir o layout visual antes da implementação (aprovação do usuário)

**Non-Goals:**
- Autenticação de usuários
- Histórico de consultas
- Export de resultados
- PWA ou app nativo

## Decisions

### D1 — Stack frontend: React + TypeScript com Vite

**Decisão**: React com TypeScript, bundler Vite, sem framework CSS externo — estilização em arquivos CSS por componente. Herdado de `pipeline-bulas-medicamentos/design.md#D7`.

**Rationale**: Setup mínimo, sem dependências de UI library que possam conflitar com o design específico desejado.

---

### D2 — Backend: FastAPI com dois endpoints

**Decisão**: Dois endpoints:
- `GET /api/medicamentos?q=` — busca por nome, retorna lista de `{id, nome}` para autocomplete
- `POST /api/consulta` — recebe lista de IDs, retorna pares com interações tipadas e CI com referência à bula de origem

Cada interação na resposta inclui `tipo` (`NOME_DIRETO`, `CLASSE` ou `ALIMENTO`), `referencia` e `efeito` (nullable). Interações do tipo `CLASSE` são exibidas como alerta genérico recomendando consulta profissional (ver D5). Interações do tipo `ALIMENTO` seguem a mesma lógica de alerta genérico das interações por `CLASSE`, mas com orientação direcionada ao paciente para evitar o(s) alimento(s) ou bebida(s) mencionados em `referencia`; o efeito é exibido quando disponível.

**Rationale**: Mínimo necessário para o fluxo de busca e cruzamento. Separar busca de consulta permite ao frontend fazer autocomplete incremental sem custo da query de cruzamento. A lógica de pertinência de classe foi removida do escopo (ver D5).

---

### D3 — UX: seleção múltipla com autocomplete, resultados por par

**Decisão**: Campo único de busca com autocomplete para seleção de múltiplos medicamentos. Resultados exibidos por par (A × B), ocultando pares sem ocorrências. Layout de página única.

**Rationale**: Fluxo mais direto para o caso de uso principal: "quero saber se esses medicamentos interagem".

---

### D4 — Visual: proposta apresentada antes da implementação

**Decisão**: A paleta (azul e branca, minimalista) e o layout serão propostos ao usuário na tarefa 1 antes de qualquer código de UI ser escrito.

**Rationale**: Evita retrabalho de estilização — mais eficiente alinhar visualmente antes de implementar.

---

### ~~D5 — Lógica de pertinência de classe no servidor~~ — OBSOLETO

**Status**: Decisão obsoleta. A verificação de quais medicamentos selecionados pertencem à classe mencionada em uma interação foi removida do escopo do TCC. Interações do tipo `CLASSE` são exibidas como alerta genérico recomendando consulta a um profissional de saúde, sem matching contra `classes_farmacologicas` (tabela removida). Ver `extracao-llm/design.md#D10`.

## Risks / Trade-offs

- **[Risco] Cruzamentos combinatórios** → Com muitos medicamentos selecionados, o número de pares cresce quadraticamente. Para o escopo do TCC (uso manual, poucos medicamentos por consulta) não é um problema.
- **[Trade-off] Interações CLASSE sem pertinência** → Usuário vê o alerta de classe mas não sabe se o medicamento que está usando pertence à classe mencionada. Funcionalidade completa é pós-TCC.
