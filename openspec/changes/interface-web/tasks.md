<!-- INSTRUÇÕES DE APPLY: implemente uma tarefa por vez quando solicitado.
     Pare ao final da fase e aguarde validação manual antes de continuar. -->
<!-- PAUSA ao final: testar a interface com dados reais do banco em desktop e em smartphone (DevTools ou dispositivo real); verificar exibição de interações diretas e por classe -->

- [ ] 1 Propor ao usuário o layout visual (paleta azul/branca, minimalista, incluindo distinção visual entre interações diretas e por classe) — aguardar aprovação
- [ ] 2 Configurar projeto React + TypeScript com Vite em `frontend/`; criar `.env` do frontend para URL base da API
- [ ] 3 Implementar endpoint FastAPI de busca de medicamentos por nome (`GET /api/medicamentos?q=`)
- [ ] 4 Implementar endpoint FastAPI de consulta cruzada (`POST /api/consulta`) que recebe lista de IDs e retorna pares com interações tipadas (`tipo`, `referencia`, `efeito`) e CI com referência à bula de origem
- [ ] 5 Criar componente `MedicamentoSelector` — campo de busca com autocomplete para seleção múltipla
- [ ] 6 Criar componente `InteracaoDireta` — exibe interação do tipo `NOME_DIRETO` com destaque visual (ícone de alerta, cor de ênfase) e efeito quando disponível
- [ ] 7 Criar componente `InteracaoClasse` — exibe interação do tipo `CLASSE` com tratamento visual distinto; mostra a classe mencionada (`referencia`) e mensagem recomendando consulta a um profissional de saúde
- [ ] 8 Criar componente `InteracaoAlimento` — exibe interação do tipo `ALIMENTO` com tratamento visual similar ao de `InteracaoClasse`; mostra o alimento ou bebida (`referencia`), o efeito quando disponível e uma orientação para o paciente evitar aquele(s) alimento(s)
- [ ] 9 Criar componente `ResultadoPar` — agrupa `InteracaoDireta`, `InteracaoClasse`, `InteracaoAlimento` e contra-indicações de um par com bula de origem; interações diretas aparecem antes das por classe e alimento
- [ ] 10 Criar componente `PaginaConsulta` — orquestra selector e resultados em layout de página única
- [ ] 11 Criar arquivo CSS por componente com paleta azul/branca e layout responsivo (CSS Grid/Flexbox)
- [ ] 12 Implementar lógica de omissão de pares sem ocorrências na renderização
- [ ] 13 Criar testes de componente (`tests/` no frontend) para `MedicamentoSelector`, `InteracaoDireta`, `InteracaoClasse`, `InteracaoAlimento` e `ResultadoPar`
- [ ] 14 Testar interface em smartphone (Chrome DevTools mobile view ou dispositivo real)
