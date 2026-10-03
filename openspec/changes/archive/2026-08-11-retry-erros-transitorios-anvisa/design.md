## Context

O cliente HTTP (`cliente.py`) hoje tem `_verificar_bloqueio` que trata apenas 429 (`BloqueioAnvisaError`) e 403 (`AcessoNegadoError`). Qualquer outro status de erro chega ao `raise_for_status()` como exceção genérica de HTTP, que `fluxo.py` captura e converte imediatamente em `ResultadoAquisicao.ERRO` — sem distinção de causa e sem retentativa. Ver proposal.md para motivação.

## Goals / Non-Goals

**Goals:**
- Classificar 5xx como transitórios e aplicar retry com backoff exponencial
- Manter o comportamento atual para 4xx permanentes (sem retry)
- Retry configurável via `.env` sem alterar código
- Log claro indicando número de tentativa e tempo de espera

**Non-Goals:**
- Retry para erros de rede/timeout (poderia ser adicionado futuramente, mas não agora)
- Retry para 429 ou 403 (já têm semântica própria e comportamento definido)
- Circuit breaker ou jitter no backoff (desnecessário para o volume atual)

## Decisions

### Decisão 1: Nova exceção `ErroTransitorioAnvisaError` em `cliente.py`

`_verificar_bloqueio` levanta `ErroTransitorioAnvisaError` para qualquer status 5xx **antes** de `raise_for_status()`. Isso mantém a camada de transporte ignorante de lógica de retry — a exceção é apenas um sinal tipado.

Alternativa considerada: tratar 5xx diretamente em `fluxo.py` verificando o código HTTP. Descartado porque duplicaria a inspeção de resposta fora da função responsável por interpretá-la.

### Decisão 2: Loop de retry em `_adquirir` (fluxo.py), não em `cliente.py`

O retry fica em `_adquirir` porque ele precisa de acesso ao contexto do medicamento (nome, log estruturado, sessão de banco) para registrar cada tentativa adequadamente. `cliente.py` é stateless por design.

Alternativa considerada: decorator `@retry` em `buscar_bulas` e `baixar_pdf`. Descartado porque obscurece o fluxo de controle e impede log contextualizado por medicamento.

### Decisão 3: Backoff exponencial simples (sem jitter)

Espera = `espera_inicial × 2^(tentativa - 1)`. Com padrão de 5 s e 3 tentativas: 5 s → 10 s. O volume de requisições simultâneas é 1 (fluxo sequencial), então jitter não traz benefício.

### Decisão 4: Parâmetros via `Settings` (pydantic-settings)

`ANVISA_RETRY_TENTATIVAS: int = 3` e `ANVISA_RETRY_ESPERA_SEGUNDOS: float = 5.0` seguem o padrão já estabelecido no projeto para todas as variáveis de configuração.

## Risks / Trade-offs

- **Tempo total de aquisição aumenta** em caso de falhas 5xx: com 3 tentativas e 5 s iniciais, cada medicamento pode demorar até 15 s extras. Com 627 medicamentos e 10% com falha transitória, o acréscimo seria ~940 s (~16 min). Aceitável para um processo batch que roda sem supervisão ativa.
- **Falso positivo de transitório**: a ANVISA poderia retornar 500 para um ID de bula inválido (erro permanente mascarado como 5xx). O retry tentaria 3 vezes antes de desistir — overhead pequeno e sem consequência de dados.
