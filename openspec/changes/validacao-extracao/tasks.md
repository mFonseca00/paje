<!-- INSTRUÇÕES DE APPLY: implemente uma tarefa por vez quando solicitado.
     Pare ao final da fase e aguarde validação manual antes de continuar. -->
<!-- PAUSA ao final: revisar relatório de avaliação; se metas não atingidas, iterar o prompt na change extracao-llm antes de avançar -->

- [ ] 1 Definir formato do gabarito (JSON por bula) com campo `descricao` para contra-indicações e campos `tipo`, `referencia` e `efeito` (nullable) para interações; criar ao menos 10 entradas anotadas manualmente a partir das bulas extraídas — incluir exemplos de interações `NOME_DIRETO`, `CLASSE` e `ALIMENTO`
- [ ] 2 Implementar loader do gabarito com chave por nome de arquivo de bula
- [ ] 3 Implementar função de normalização de texto (minúsculas, remoção de acentos, não-alfanuméricos → espaço, remoção de espaços duplicados e bordas)
- [ ] 4 Implementar cálculo do índice de Jaccard sobre conjuntos de palavras
- [ ] 5 Implementar score de similaridade para contra-indicações: `s_CI = J(texto_extraído, texto_gabarito)`
- [ ] 6 Implementar score de similaridade para interações: `s_IN = 0,65 × J(referencia) + 0,35 × J(efeito)` quando efeito disponível em ambos os lados; `s_IN = J(referencia)` quando efeito é nulo em qualquer lado
- [ ] 7 Implementar matching por melhor score (sem exclusividade) e classificação TP/FP/FN usando limiares configuráveis (0,45 CI / 0,40 IM)
- [ ] 8 Implementar cálculo de precisão, revocação e F2 por micro-média para CI e IM separadamente
- [ ] 9 Implementar relatório de avaliação com indicação de aprovação/reprovação por meta (revocação ≥ 0,90 e F2 ≥ 0,80)
- [ ] 10 Executar avaliação com o gabarito e registrar resultado do prompt v1
- [ ] 11 Se metas não atingidas: criar prompt v2 na change extracao-llm e repetir a partir da tarefa 11 de lá + tarefa 10 desta change até atingir as metas
