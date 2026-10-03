## Why

Quando a busca por nome DCB falha e o sistema usa o fallback de nome comercial, o PDF da bula é salvo com nome contendo apenas o nome comercial — descartando a informação do DCB no arquivo. Isso dificulta rastrear visualmente quais medicamentos da RENAME cada arquivo representa. Além disso, o limite de 60 chars no slug pode truncar nomes legítimos sem necessidade, já que o sistema de arquivos suporta nomes muito maiores.

## What Changes

- O nome do arquivo PDF passa a incluir o nome DCB (RENAME) como prefixo quando o fallback de nome comercial é usado, no formato `{tipo}__{dcb}__{comercial}__{sufixo}.pdf`.
- O limite de truncamento do slug é removido (era 60 chars); o nome completo é preservado, pois o limite real do sistema de arquivos permite nomes muito maiores.
- A spec do requirement **Nomenclatura identificável do arquivo PDF** é atualizada para refletir o novo formato e a remoção do truncamento.

## Capabilities

### New Capabilities

_(nenhuma)_

### Modified Capabilities

- `aquisicao-bulas`: o requirement de nomenclatura do arquivo PDF muda — novo formato inclui DCB quando o fallback é usado, e o truncamento de slug é removido.

## Impact

- `backend/aquisicao/fluxo.py`: função `_nome_arquivo` e a chamada na linha 230.
- Arquivos de bula já baixados **não são renomeados** — a mudança afeta apenas novos downloads.
- Nenhuma alteração de banco de dados, API ou dependências externas.
