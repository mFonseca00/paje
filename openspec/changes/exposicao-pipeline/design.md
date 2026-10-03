## Context

O sistema está completamente funcional localmente com dados reais. Esta fase finaliza o TCC: expõe a aplicação para acesso externo e executa a pipeline completa sobre o conjunto total da RENAME.

## Goals / Non-Goals

**Goals:**
- Expor a aplicação para acesso fora da máquina local (demonstração para a banca)
- Executar aquisição e extração sobre o conjunto completo da RENAME
- Verificar que a interface funciona com o volume real de dados

**Non-Goals:**
- Alta disponibilidade ou uptime contínuo
- Deploy em produção com domínio próprio
- Monitoramento de infraestrutura

## Decisions

### D1 — Exposição externa: ngrok ou cloudflared

**Decisão**: Exposição via túnel (ngrok ou cloudflared) como primeira opção. Fallback: port forwarding no roteador + DDNS. Decisão final na tarefa 7.1 após teste. Herdado de `pipeline-bulas-medicamentos/design.md#D8`.

**Rationale**: Zero configuração de infraestrutura, adequado para demonstrações pontuais como apresentação de TCC.

---

### D2 — Execução completa: após metas de validação atingidas

**Decisão**: A execução do conjunto completo da RENAME (tarefa 7.2) só ocorre após as metas de F2 e revocação serem atingidas na fase de validação. Não há sentido em processar o conjunto completo com um prompt que não atingiu as metas.

**Rationale**: Evita reprocessamento desnecessário do conjunto completo se o prompt precisar de ajuste.

## Risks / Trade-offs

- **[Risco] Túnel instável durante apresentação** → Mitigação: testar o dia anterior; ter fallback de port forwarding documentado.
- **[Risco] Volume completo da RENAME pode levar horas no Ollama local** → Deixar rodando overnight antes da apresentação.
