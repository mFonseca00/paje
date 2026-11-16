<!-- INSTRUÇÕES DE APPLY: implemente uma tarefa por vez quando solicitado.
     Pare ao final de cada grupo e aguarde validação antes de continuar. -->
<!-- PAUSA ao final do grupo 4: revisar relatorio.json; se metas não atingidas, iterar o prompt na change extracao-llm antes de avançar -->

## 1. Gabarito

- [ ] 1.1 Criar pasta `docs/validacao/pdfs/` e copiar manualmente os PDFs selecionados para validação (mínimo 10 bulas distintas)
- [ ] 1.2 Criar `docs/validacao/planilha.xlsx` com colunas `arquivo` e `json_esperado`; preencher manualmente pelo menos 10 linhas com o JSON esperado seguindo o schema da extração — incluir exemplos de interações `NOME_DIRETO`, `CLASSE` e `ALIMENTO`, e contra-indicações variadas

## 2. Script standalone de validação

- [ ] 2.1 Criar `backend/scripts/executar_validacao.py` que lê os PDFs de `docs/validacao/pdfs/`, aplica `converter_pdf_para_markdown` e `extrair_secoes_relevantes`, chama `extrair_bula` e coleta as saídas sem gravar no banco
- [ ] 2.2 Implementar loader da planilha XLSX: lê `docs/validacao/planilha.xlsx`, parseia `json_esperado` via `json.loads`, reporta erros de parse com nome do arquivo e número de linha

## 3. Engine de comparação

- [ ] 3.1 Implementar função de normalização de texto (minúsculas, remoção de acentos, não-alfanuméricos → espaço, remoção de espaços duplicados e bordas)
- [ ] 3.2 Implementar cálculo do índice de Jaccard sobre conjuntos de palavras
- [ ] 3.3 Implementar score de similaridade para contra-indicações: `s_CI = J(descricao_extraída, descricao_gabarito)`
- [ ] 3.4 Implementar score de similaridade para interações: `s_IN = 0,65 × J(referencia) + 0,35 × J(efeito)` quando efeito disponível em ambos os lados; `s_IN = J(referencia)` quando efeito é nulo em qualquer lado
- [ ] 3.5 Implementar matching por melhor score (sem exclusividade) e classificação TP/FP/FN usando limiares configuráveis (0,45 CI / 0,40 IM)

## 4. Output versionado

- [ ] 4.1 Implementar geração da pasta de execução `docs/validacao/resultados/{data}_{prompt_versao}_{modelo}/` com data/hora local, `settings.prompt_version` e identificador do modelo
- [ ] 4.2 Implementar geração do JSON por bula com campos `arquivo`, `contraindicacoes` (tp, fp, fn, matches com gabarito/extraida/score/classificacao) e `interacoes` (mesma estrutura)
- [ ] 4.3 Implementar cálculo de precisão, revocação e F2 por micro-média para CI e IM separadamente (`F2 = 5 × (P × R) / (4P + R)`)
- [ ] 4.4 Implementar geração do `relatorio.json` com `execucao` (data, prompt_versao, modelo), métricas de CI e IM (precisao, revocacao, f2, aprovado, tp, fp, fn) e `aprovado_geral` — indica aprovação se revocação ≥ 0,90 e F2 ≥ 0,80 para ambas as categorias

## 5. Execução e iteração

- [ ] 5.1 Executar validação com o gabarito e registrar resultado do prompt v1 em `docs/validacao/resultados/`
- [ ] 5.2 Se metas não atingidas: criar prompt v2 na change extracao-llm, re-executar e repetir tarefa 5.1 até atingir as metas
