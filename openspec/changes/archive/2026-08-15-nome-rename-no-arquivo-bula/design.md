## Context

Ver `proposal.md — Why` para motivação. A lógica de nomenclatura está concentrada em `backend/aquisicao/fluxo.py`, na função `_nome_arquivo` (linha 63) e no único ponto onde ela é chamada (linha 230).

Variáveis relevantes no momento da chamada:
- `nome` — após o fallback, contém o nome comercial usado na busca
- `nome_dcb` — sempre o nome original da RENAME, preservado desde a linha 155

## Goals / Non-Goals

**Goals:**
- Incluir o nome DCB no arquivo quando o fallback foi usado
- Remover o truncamento em 60 chars do slug

**Non-Goals:**
- Renomear arquivos já baixados
- Alterar o banco de dados ou qualquer outra parte do sistema

## Decisions

### Decisão: adicionar parâmetro `nome_dcb` a `_nome_arquivo`

`_nome_arquivo` recebe um `nome_dcb: str | None = None`. Quando fornecido e diferente de `nome_medicamento`, o slug é montado como `{slug_dcb}__{slug_comercial}`. Caso contrário, comportamento idêntico ao atual (apenas um nome).

A condição na chamada é `nome_dcb if nome_dcb != nome else None` — verdadeira exatamente quando o fallback ocorreu.

**Alternativa descartada:** passar um booleano `foi_fallback`. Mais frágil — não carrega as informações em si, apenas sinaliza que ocorreu. O nome DCB já está disponível, então passá-lo diretamente é mais expressivo e testável.

### Decisão: remover truncamento

O slug passa a usar o nome completo sem `[:N]`. O overhead fixo do formato (`profissional__` + `__` + `__` + 8 chars + `.pdf`) ocupa no máximo ~30 chars; mesmo nomes longos ficam bem dentro do limite de 255 chars do sistema de arquivos.

## Risks / Trade-offs

- **Arquivos existentes não são renomeados** → sem risco de perda de dados; o `id_bula_anvisa` é a chave de deduplicação no banco, não o nome do arquivo.
- **Nomes muito longos** → teoricamente possível, mas os nomes DCB e comerciais da RENAME/ANVISA são curtos na prática (< 60 chars cada).
