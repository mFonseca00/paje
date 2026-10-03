## Why

O endpoint de busca da ANVISA faz correspondência por substring: ao buscar "amoxicilina", ele retorna também "amoxicilina + clavulanato de potássio" e a ordem dos resultados não garante que o medicamento de princípio ativo único venha primeiro. Como o código atual seleciona sempre o primeiro resultado com ID de bula válido, bulas de medicamentos combinados estão sendo salvas no lugar de bulas de medicamentos simples.

## What Changes

- O fluxo de seleção de resultado (`_adquirir` em `fluxo.py`) passará a filtrar resultados cujo `nome_produto` contenha "+" quando o nome buscado **não** contém "+", preferindo medicamentos de princípio ativo único.
- Se após o filtro nenhum candidato restar (todos os resultados são combinações), o sistema usa os resultados originais como fallback — sem perder cobertura.
- Não há alteração na API HTTP, na estrutura do banco de dados, no formato dos arquivos PDF salvos, nem nos critérios de busca (a chamada ao endpoint ANVISA permanece idêntica).

## Capabilities

### New Capabilities

_(nenhuma)_

### Modified Capabilities

- `aquisicao-bulas`: adição de requisito de seleção inteligente de resultado de busca — ao receber múltiplos resultados, o sistema deve preferir aqueles sem indicativo de combinação de princípios ativos quando o nome buscado é de princípio ativo único.

## Impact

- **Arquivo afetado**: `backend/aquisicao/fluxo.py` — apenas a lógica de seleção do resultado (`escolhido = next(...)`)
- **Sem impacto em**: banco de dados, schema ANVISA, testes de repositório, pipeline de extração/validação
