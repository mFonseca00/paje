## 1. Classificação de erros transitórios no cliente HTTP

- [x] 1.1 Criar exceção `ErroTransitorioAnvisaError` em `backend/aquisicao/cliente.py` (análoga a `BloqueioAnvisaError` e `AcessoNegadoError`)
- [x] 1.2 Atualizar `_verificar_bloqueio` para levantar `ErroTransitorioAnvisaError` quando `response.status_code >= 500`, com mensagem indicando o código HTTP e a URL

## 2. Configuração de retry

- [x] 2.1 Adicionar `anvisa_retry_tentativas: int = 3` e `anvisa_retry_espera_segundos: float = 5.0` em `backend/config.py`
- [x] 2.2 Adicionar `ANVISA_RETRY_TENTATIVAS=3` e `ANVISA_RETRY_ESPERA_SEGUNDOS=5.0` com comentários explicativos em `.env` e `.env.example`

## 3. Lógica de retry no fluxo de aquisição

- [x] 3.1 Implementar função auxiliar `_com_retry(fn, *args, **kwargs)` em `backend/aquisicao/fluxo.py` que executa `fn` com backoff exponencial para `ErroTransitorioAnvisaError`, registrando em log cada tentativa (número, código HTTP, tempo de espera); após esgotar tentativas propaga o erro normalmente
- [x] 3.2 Envolver a chamada a `buscar_bulas` em `_adquirir` com `_com_retry`
- [x] 3.3 Envolver a chamada a `baixar_pdf` em `_adquirir` com `_com_retry`

## 4. Testes

- [x] 4.1 Adicionar testes em `backend/tests/test_aquisicao.py` para `ErroTransitorioAnvisaError`: status 500 levanta a exceção; status 200 não levanta; status 503 levanta
- [x] 4.2 Adicionar testes para `_com_retry`: sucesso na primeira tentativa (sem retry); sucesso na segunda tentativa após falha transitória; esgotamento de tentativas resulta em `ResultadoAquisicao.ERRO`; erros permanentes (4xx) não disparam retry
