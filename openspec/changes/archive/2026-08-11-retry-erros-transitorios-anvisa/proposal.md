## Why

Erros HTTP 500 (Internal Server Error) retornados pela ANVISA são transitórios — o servidor falhou momentaneamente, não o sistema local — e hoje são tratados da mesma forma que erros permanentes: o medicamento é imediatamente marcado como `ERRO` sem nenhuma nova tentativa, desperdiçando a oportunidade de sucesso numa segunda chamada. A mudança é necessária agora porque a aquisição em lote da RENAME pode gerar dezenas de `ERRO` desnecessários se o servidor da ANVISA estiver instável.

## What Changes

- O cliente HTTP (`cliente.py`) passa a classificar respostas em **erros transitórios** (5xx, timeout de rede) e **erros permanentes** (4xx exceto 429 e 403 já tratados, body inválido).
- Erros transitórios disparam uma nova exceção `ErroTransitorioAnvisaError` que sinaliza ao chamador que a operação pode ser repetida.
- A função `_adquirir` em `fluxo.py` implementa lógica de **retry com backoff exponencial** para `ErroTransitorioAnvisaError`: número de tentativas e tempo de espera inicial configuráveis via `.env`.
- Após esgotar as tentativas, o medicamento é marcado como `ERRO` normalmente (comportamento atual preservado).
- O log de cada tentativa indica o número da tentativa, o código HTTP recebido e o tempo de espera até a próxima.

## Capabilities

### New Capabilities

_(nenhuma nova capability — a aquisição de bulas já existe como capability)_

### Modified Capabilities

- `aquisicao-bulas`: O requisito de tratamento de erros HTTP passa a distinguir erros transitórios (5xx) de permanentes; erros transitórios devem gerar retentativa automática com backoff antes de ser considerados falha definitiva.

## Impact

- `backend/aquisicao/cliente.py`: nova exceção `ErroTransitorioAnvisaError`; `_verificar_bloqueio` passa a levantar essa exceção para status 5xx.
- `backend/aquisicao/fluxo.py`: loop de retry em `_adquirir` para `ErroTransitorioAnvisaError`.
- `backend/config.py`: dois novos parâmetros — `ANVISA_RETRY_TENTATIVAS` (padrão: 3) e `ANVISA_RETRY_ESPERA_SEGUNDOS` (padrão: 5.0).
- `.env` e `.env.example`: novas variáveis de retry.
- `backend/tests/test_aquisicao.py`: novos testes cobrindo retry bem-sucedido, esgotamento de tentativas e ausência de retry para erros permanentes.
