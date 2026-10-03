## Why

O fluxo de aquisição tem dois problemas relacionados à consistência entre banco e disco:

1. **SKIP sem checar arquivo**: quando o mesmo `id_bula_anvisa` já existe no banco (status ≠ ERRO), o sistema pula o download sem verificar se o arquivo PDF ainda existe em disco. Se o arquivo foi apagado, a bula fica PENDENTE no banco com `caminho_pdf` inválido.

2. **JWT rotacionado sem verificar arquivo existente**: quando a ANVISA retorna um JWT diferente para o mesmo medicamento, `buscar_bula_por_id_anvisa` retorna None e o sistema vai direto ao download — sem checar se o medicamento já tem PDF válido em disco. Isso causa re-downloads desnecessários e deixa registros fantasma no banco (ID antigo, arquivo já apagado).

## What Changes

- **Cenário B** — mesmo JWT, arquivo ausente: re-baixar e atualizar `caminho_pdf` no banco (resultado `RECUPERADO`)
- **Cenário C** — JWT novo, mas medicamento já tem PDF válido em disco: SKIP sem download
- **Cenário D** — JWT novo, medicamento sem PDF válido em disco: download + deletar registros fantasma do banco antes de criar novo registro
- Novo valor de enum `RECUPERADO` em `ResultadoAquisicao` e contador em `ResumoAquisicao`
- Testes cobrindo os três novos cenários

## Capabilities

### New Capabilities

_(nenhuma — correção de comportamento existente)_

### Modified Capabilities

- `aquisicao-bulas`: atualizar requisito "Controle de duplicatas" com os quatro cenários completos (arquivo presente/ausente × mesmo JWT/JWT novo)

## Impact

- `backend/aquisicao/fluxo.py`: `_adquirir()`, `ResultadoAquisicao`, `ResumoAquisicao`
- `backend/armazenamento/repositorio.py`: nova função para deletar registro de bula (se não existir)
- `backend/scripts/executar_aquisicao.py`: exibir contador `recuperados` no resumo
- `backend/tests/test_aquisicao.py`: novos casos de teste
- `openspec/specs/aquisicao-bulas/spec.md`: delta com os quatro cenários
