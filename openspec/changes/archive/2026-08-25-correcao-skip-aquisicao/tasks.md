## 1. Repositório

- [x] 1.1 Verificar se `atualizar_status_bula` em `repositorio.py` aceita `caminho_pdf` como parâmetro — se não, adicionar
- [x] 1.2 Adicionar função `deletar_bula(session, bula_id)` em `repositorio.py` (ou validar que deleção via `session.delete()` inline é suficiente)

## 2. Fluxo de aquisição (fluxo.py)

- [x] 2.1 Adicionar `RECUPERADO = "RECUPERADO"` em `ResultadoAquisicao` e campo `recuperados: int = 0` em `ResumoAquisicao`
- [x] 2.2 **Cenário B** — no branch `bula_existente is not None and status != ERRO`: verificar `Path(bula_existente.caminho_pdf).exists()` antes de retornar SKIP; se ausente, prosseguir para download e retornar `RECUPERADO` com `caminho_pdf` atualizado no banco
- [x] 2.3 **Cenários C e D** — mover a busca de `med = buscar_medicamento_por_nome()` para antes do bloco de download (atualmente está depois); verificar se alguma bula do medicamento tem arquivo em disco: se sim, retornar SKIP (cenário C); se não, deletar registros fantasma do banco antes de `criar_bula()` (cenário D)
- [x] 2.4 Em `executar_aquisicao()`: contabilizar `ResultadoAquisicao.RECUPERADO` no `match` incrementando `resumo.recuperados`

## 3. Script CLI

- [x] 3.1 Em `backend/scripts/executar_aquisicao.py`: exibir linha `Recuperados: {resumo.recuperados}` no resumo final

## 4. Testes

- [x] 4.1 Cenário A (regressão): mesmo JWT, arquivo presente → SKIP, sem download
- [x] 4.2 Cenário B: mesmo JWT, arquivo ausente → RECUPERADO, download executado, `caminho_pdf` atualizado
- [x] 4.3 Cenário C: JWT novo, arquivo existente em disco → SKIP, sem download, registro antigo intacto
- [x] 4.4 Cenário D: JWT novo, sem arquivo em disco → BAIXADO, registros fantasma deletados, novo registro criado
