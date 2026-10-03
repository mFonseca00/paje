## 1. Implementação

- [x] 1.1 Adicionar parâmetro `nome_dcb: str | None = None` à função `_nome_arquivo` em `fluxo.py` e montar o slug como `{slug_dcb}__{slug_comercial}` quando `nome_dcb` for fornecido e diferente de `nome_medicamento`
- [x] 1.2 Remover o truncamento `[:60]` do slug em `_nome_arquivo`
- [x] 1.3 Atualizar a chamada de `_nome_arquivo` na linha 230 para passar `nome_dcb=nome_dcb if nome_dcb != nome else None`

## 2. Testes

- [x] 2.1 Atualizar/adicionar teste unitário para `_nome_arquivo` cobrindo o caso sem fallback (apenas slug DCB, sem truncamento)
- [x] 2.2 Adicionar teste unitário para `_nome_arquivo` cobrindo o caso com fallback (slug DCB + slug comercial no nome do arquivo)
- [x] 2.3 Verificar que o teste de integração existente de aquisição ainda passa com a nova assinatura
