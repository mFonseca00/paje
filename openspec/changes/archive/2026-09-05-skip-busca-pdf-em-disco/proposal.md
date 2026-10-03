## Why

A etapa de aquisição faz uma requisição HTTP à ANVISA para cada medicamento da RENAME, mesmo quando o PDF já existe em disco — situação em que o resultado sempre seria SKIP. Com ~800 medicamentos e 600+ já baixados, isso gera centenas de requests desnecessários por rodada, aumentando tempo de execução e risco de rate limiting.

## What Changes

- O sistema verifica se o medicamento já possui PDF válido em disco **antes** de chamar o endpoint de busca da ANVISA.
- Se PDF válido em disco: retorna SKIP imediatamente, sem request HTTP.
- Se sem PDF válido: comportamento atual preservado.
- A tabela `bulas` recebe o campo `ultima_verificacao_anvisa` (timestamp nullable) para registrar quando o JWT foi confirmado pela última vez — habilitando futura verificação periódica sem alterar o comportamento atual.

## Capabilities

### New Capabilities

Nenhuma.

### Modified Capabilities

- `aquisicao-bulas`: novo requisito de pre-checagem local antes da busca; novo campo `ultima_verificacao_anvisa` no esquema de persistência.
- `armazenamento-dados`: novo campo `ultima_verificacao_anvisa` na tabela `bulas`.

## Impact

- `backend/aquisicao/fluxo.py`: lógica de `_adquirir` recebe pre-checagem no início.
- `backend/armazenamento/modelos.py`: nova coluna `ultima_verificacao_anvisa` em `Bula`.
- `backend/armazenamento/repositorio.py`: atualização do campo ao confirmar JWT.
- Nova migration Alembic.
- Sem breaking changes no comportamento externo.
