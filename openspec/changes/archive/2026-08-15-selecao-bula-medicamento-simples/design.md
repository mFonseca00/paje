## Context

Veja `proposal.md – Why` para a motivação.

A seleção do resultado de busca ocorre em `backend/aquisicao/fluxo.py`, função `_adquirir`, linha 179:

```python
escolhido = next((r for r in resultados if _escolher_id_bula(r)), None)
```

`resultados` é uma `list[ResultadoBusca]` já populada pela chamada `buscar_bulas`. Cada item expõe `nome_produto` (string com o nome retornado pelo campo `nomeProduto` da API ANVISA) e os IDs de bula. O `nome` local nesse ponto pode ser o DCB original ou o nome comercial usado no fallback.

## Goals / Non-Goals

**Goals:**
- Substituir o `next(...)` atual por uma função de seleção que filtre candidatos contendo "+" quando o nome buscado não os contém.
- Manter fallback transparente: se o filtro esvaziar os candidatos, usar a lista original.

**Non-Goals:**
- Não alterar a chamada HTTP ao endpoint ANVISA nem os parâmetros de busca.
- Não introduzir similaridade de string (scope futuro, se necessário).
- Não modificar banco de dados, modelos ou qualquer outro módulo.

## Decisions

### Decisão: comparação por presença de "+" no nome_produto

**Escolhido:** verificar `"+" in nome_produto` como critério de exclusão para buscas sem "+".

**Alternativas consideradas:**
- *Similaridade com difflib*: mais robusta mas adiciona complexidade desnecessária para o problema imediato; pode ser adicionada depois como refinamento.
- *Regex de word-boundary*: overkill para o problema; "+" é um separador universal de combinações no nomenclador ANVISA.

**Rationale:** "+" é o único indicador confiável de combinação no campo `nomeProduto` da ANVISA, e a regra é diretamente legível e testável.

### Decisão: extrair função `_selecionar_resultado`

Em vez de embutir o filtro inline no `_adquirir`, extrair para uma função auxiliar `_selecionar_resultado(nome: str, resultados: list[ResultadoBusca]) -> ResultadoBusca | None`. Isso mantém `_adquirir` legível e facilita testes unitários isolados da lógica de seleção.

## Risks / Trade-offs

- **Risco: `nome_produto` com "+" por razão não-combinação** (improvável, mas possível ex: nome de marca com "+"). Mitigação: o fallback garante que nenhum medicamento fique sem bula — no pior caso o sistema volta ao comportamento anterior.
- **Trade-off: não resolve casos onde o primeiro resultado sem "+" ainda não é o mais relevante** (ex: "amoxicilina triidratada" vs "amoxicilina"). Aceitável para o escopo atual; similaridade pode ser adicionada depois.
