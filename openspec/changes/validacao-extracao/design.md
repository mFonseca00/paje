## Context

O pipeline de extração LLM é capaz de processar bulas PDF e extrair entidades clínicas (contra-indicações e interações medicamentosas). Esta fase cria uma infraestrutura de avaliação quantitativa separada do banco de produção: um script standalone roda o pré-processamento e a extração sobre uma amostra de bulas anotadas manualmente, compara os resultados com o gabarito e reporta métricas de qualidade. A validação é executada sob demanda — não faz parte do fluxo de produção e não grava no banco.

## Goals / Non-Goals

**Goals:**
- Definir o formato do gabarito e o processo de anotação manual
- Definir as métricas de avaliação e os limiares de aprovação
- Implementar o pipeline de avaliação de forma reproduzível
- Garantir que mudanças no prompt e no código de extração impactem automaticamente a validação

**Non-Goals:**
- Avaliação contínua ou integração com CI
- Interface visual para o gabarito
- Anotação automatizada
- Validação do pipeline de aquisição ou da interface web (escopo separado)

## Decisions

### D1 — Formato do gabarito: planilha XLSX com JSON esperado

**Decisão**: Planilha XLSX (`docs/validacao/referencia_validacao.xlsx`) com duas colunas: `arquivo` (nome do arquivo PDF, sem caminho) e `json_esperado` (string JSON com a saída esperada da extração). O JSON segue exatamente o schema Pydantic de saída da extração — lista de `contraindicacoes` (campo `descricao`) e lista de `interacoes` (campos `tipo`, `referencia`, `efeito` nullable).

**Rationale**: Planilha facilita preenchimento manual e análise geral. Armazenar o JSON esperado em uma coluna preserva o schema exato sem criar múltiplos arquivos. O formato XLSX permite validação visual linha a linha e pode ser incluído como apêndice no TCC. O loader parseia o campo `json_esperado` via `json.loads` para produzir a mesma estrutura que a extração retorna.

---

### D2 — Métrica de similaridade: Jaccard sobre conjuntos de palavras

**Decisão**: Similaridade calculada pelo índice de Jaccard entre conjuntos de palavras normalizadas (minúsculas, sem acentos, sem não-alfanuméricos). Para contra-indicações: `s_CI = J(descricao_extraída, descricao_gabarito)`. Para interações: `s_IN = 0,65 × J(referencia) + 0,35 × J(efeito)`. Quando `efeito` é nulo em qualquer lado, o componente de efeito é desconsiderado e `s_IN = J(referencia)`.

**Rationale**: Jaccard é robusto a variações de formulação sem exigir embeddings. Os pesos de interação refletem que `referencia` é mais discriminante que o efeito. O tratamento de `efeito` nullable evita penalizar o modelo por interações de classe onde o efeito não é descrito na bula.

---

### D3 — Matching: melhor score sem exclusividade

**Decisão**: Cada entidade do gabarito é pareada com a entidade extraída de maior similaridade, sem exclusividade (a mesma extração pode capturar múltiplas entidades do gabarito). TP se score ≥ limiar; FN se score < limiar ou entidade ausente; FP se extração não emparelha com nenhuma do gabarito acima do limiar. Limiares: 0,45 para CI, 0,40 para IM.

**Rationale**: Sem exclusividade favorece a revocação, que é a métrica mais crítica para uso clínico. Limiares distintos refletem que textos de CI tendem a ser mais longos e com maior sobreposição léxica.

---

### D4 — Métrica de avaliação: F2 por micro-média

**Decisão**: Precisão, revocação e F2 calculados por micro-média sobre todas as bulas do gabarito. Meta de aprovação: revocação ≥ 0,90 e F2 ≥ 0,80 para CI e IM separadamente.

**Rationale**: F2 pondera revocação duas vezes mais que precisão — adequado para contexto clínico onde falsos negativos (entidades não encontradas) são mais custosos que falsos positivos. Micro-média trata cada entidade com igual peso independentemente da bula.

---

### D5 — Pasta isolada para PDFs de validação

**Decisão**: Os PDFs usados na validação ficam em `docs/validacao/pdfs/`, copiados manualmente. O pipeline de aquisição (ANVISA) não escreve nessa pasta.

**Rationale**: Garantia de que o PDF analisado manualmente é exatamente o mesmo processado pela extração. Sem isolamento, uma re-aquisição poderia substituir o arquivo e invalidar o gabarito. A cópia manual é intencional — garante que o analista verificou o arquivo antes de anotar.

---

### D6 — Script standalone com acoplamento via importação

**Decisão**: A validação roda em `backend/scripts/executar_validacao.py` (ou `backend/validacao/runner.py`), que importa diretamente as funções internas do pipeline de extração: `extrair_bula` (agente + prompt), `converter_pdf_para_markdown` e `extrair_secoes_relevantes`. Não grava no banco de produção.

**Rationale**: Acoplamento implícito via importação Python garante que qualquer mudança no prompt, no schema ou no pré-processamento seja refletida automaticamente na validação — sem sincronização manual. Alternativa (duplicar a lógica) foi descartada porque criaria divergência silenciosa entre validação e produção.

### D7 — Output versionado por execução

**Decisão**: Cada execução do script de validação grava seus resultados em uma subpasta de `docs/validacao/resultados/` nomeada `{data}_{prompt_versao}_{modelo}` (ex: `2026-11-15_prompt-v1_claude-sonnet-4-6`). Dentro da pasta: um JSON por bula avaliada (`{nome_arquivo}.json`) com os matches, scores e classificações TP/FP/FN; e um `relatorio.json` com a metadata da execução e as métricas agregadas.

Estrutura do `relatorio.json`:
```json
{
  "execucao": { "data": "2026-11-15T14:30:22", "prompt_versao": "v1", "modelo": "claude-sonnet-4-6" },
  "total_bulas": 10,
  "contraindicacoes": { "precisao": 0.92, "revocacao": 0.91, "f2": 0.91, "aprovado": true, "tp": 48, "fp": 4, "fn": 5 },
  "interacoes": { "precisao": 0.88, "revocacao": 0.90, "f2": 0.89, "aprovado": true, "tp": 30, "fp": 4, "fn": 3 },
  "aprovado_geral": true
}
```

**Rationale**: Versionamento implícito pelo nome da pasta permite comparar execuções sem ferramentas adicionais. `prompt_versao` e `modelo` no nome da pasta tornam a evolução legível no explorador de arquivos. Os JSONs por bula preservam o detalhe de cada match para análise qualitativa posterior.

---

## Risks / Trade-offs

- **[Trade-off] Gabarito pequeno (≥ 10 bulas)** → Suficiente para validação de conceito no TCC; não representa cobertura estatística ampla.
- **[Trade-off] Matching sem exclusividade** → Pode inflar a revocação em casos de duplicatas na extração.
- **[Trade-off] JSON em célula XLSX** → Edição manual propensa a erros de sintaxe JSON; mitigação: validar o JSON ao carregar a planilha e reportar erros de parse linha a linha.
