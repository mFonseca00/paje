## 1. Implementação

- [x] 1.1 Extrair função `_selecionar_resultado(nome: str, resultados: list[ResultadoBusca]) -> ResultadoBusca | None` em `backend/aquisicao/fluxo.py` que aplica o filtro de "+" e retorna o primeiro candidato válido (com fallback para lista original se o filtro esvaziar)
- [x] 1.2 Substituir o `next(...)` inline em `_adquirir` pela chamada a `_selecionar_resultado`

## 2. Testes

- [x] 2.1 Adicionar testes unitários para `_selecionar_resultado` cobrindo os três cenários da spec: (a) lista mista retorna o simples, (b) lista só com "+" usa fallback, (c) busca com "+" não filtra
