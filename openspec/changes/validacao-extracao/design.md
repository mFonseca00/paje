## Context

As entidades clínicas (contra-indicações e interações medicamentosas) já estão extraídas pelo agente LLM e gravadas no banco. Esta fase cria a infraestrutura de avaliação quantitativa para medir a qualidade da extração e decidir se o prompt está pronto para o conjunto completo.

## Goals / Non-Goals

**Goals:**
- Definir o formato do gabarito e o processo de anotação manual
- Definir as métricas de avaliação e os limiares de aprovação
- Implementar o pipeline de avaliação de forma reproduzível

**Non-Goals:**
- Avaliação contínua ou integração com CI
- Interface visual para o gabarito
- Anotação automatizada

## Decisions

### D1 — Formato do gabarito: JSON por bula

**Decisão**: Um arquivo JSON por bula anotada, com chave pelo nome do arquivo de bula. Estrutura espelha o schema de saída da etapa única de extração: lista de `contraindicacoes` (campo `descricao`) e lista de `interacoes_medicamentosas` (campos `tipo`, `referencia`, `efeito` nullable). O gabarito cobre contra-indicações e interações medicamentosas — a classificação farmacológica por LLM (considerada e descartada para o TCC, ver `extracao-llm/design.md#D9`) não é avaliada.

**Rationale**: Formato direto, facilmente comparável com a saída do modelo sem transformação. A inclusão de `tipo` no gabarito permite avaliar se o modelo está tipando corretamente as interações (`NOME_DIRETO`, `CLASSE` e `ALIMENTO`), mas o cálculo de similaridade usa apenas `referencia` e `efeito` — `tipo` é informativo para análise qualitativa.

---

### D2 — Métrica de similaridade: Jaccard sobre conjuntos de palavras

**Decisão**: Similaridade calculada pelo índice de Jaccard entre conjuntos de palavras normalizadas (minúsculas, sem acentos, sem não-alfanuméricos). Para contra-indicações: `s_CI = J(descricao_extraída, descricao_gabarito)`. Para interações: `s_IN = 0,65 × J(referencia) + 0,35 × J(efeito)`. Quando `efeito` é nulo em qualquer lado, o componente de efeito é desconsiderado e `s_IN = J(referencia)`.

**Rationale**: Jaccard é robusto a variações de formulação sem exigir embeddings. Os pesos de interação refletem que `referencia` (anteriormente `substancia`) é mais discriminante que o efeito. O tratamento de `efeito` nullable evita penalizar o modelo por interações de classe onde o efeito não é descrito na bula.

---

### D3 — Matching: melhor score sem exclusividade

**Decisão**: Cada entidade do gabarito é pareada com a entidade extraída de maior similaridade, sem exclusividade (a mesma extração pode capturar múltiplas entidades do gabarito). TP se score ≥ limiar; FN se score < limiar ou entidade ausente; FP se extração não emparelha com nenhuma do gabarito acima do limiar. Limiares: 0,45 para CI, 0,40 para IM.

**Rationale**: Sem exclusividade favorece a revocação, que é a métrica mais crítica para uso clínico. Limiares distintos refletem que textos de CI tendem a ser mais longos e com maior sobreposição léxica.

---

### D4 — Métrica de avaliação: F2 por micro-média

**Decisão**: Precisão, revocação e F2 calculados por micro-média sobre todas as bulas do gabarito. Meta de aprovação: revocação ≥ 0,90 e F2 ≥ 0,80 para CI e IM separadamente.

**Rationale**: F2 pondera revocação duas vezes mais que precisão — adequado para contexto clínico onde falsos negativos (entidades não encontradas) são mais custosos que falsos positivos. Micro-média trata cada entidade com igual peso independentemente da bula.

## Risks / Trade-offs

- **[Trade-off] Gabarito pequeno (≥ 10 bulas)** → Suficiente para validação de conceito no TCC; não representa cobertura estatística ampla.
- **[Trade-off] Matching sem exclusividade** → Pode inflar a revocação em casos de duplicatas na extração.
