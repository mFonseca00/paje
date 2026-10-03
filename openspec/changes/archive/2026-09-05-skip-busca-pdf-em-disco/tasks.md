## 1. Modelo e Migration

- [x] 1.1 Adicionar coluna `ultima_verificacao_anvisa` (`DateTime(timezone=True)`, nullable) ao modelo `Bula` em `backend/armazenamento/modelos.py`
- [x] 1.2 Gerar migration Alembic: `alembic revision --autogenerate -m "adicionar_ultima_verificacao_anvisa_a_bulas"`
- [x] 1.3 Revisar o SQL gerado na migration e confirmar que é `ALTER TABLE bulas ADD COLUMN ultima_verificacao_anvisa TIMESTAMP WITH TIME ZONE NULL`
- [x] 1.4 Aplicar migration: `alembic upgrade head`

## 2. Repositório

- [x] 2.1 Adicionar parâmetro opcional `ultima_verificacao_anvisa: datetime | None = None` a `criar_bula` em `backend/armazenamento/repositorio.py`
- [x] 2.2 Adicionar parâmetro opcional `ultima_verificacao_anvisa: datetime | None = None` a `atualizar_status_bula` em `backend/armazenamento/repositorio.py`

## 3. Fluxo de Aquisição

- [x] 3.1 No início de `_adquirir` em `backend/aquisicao/fluxo.py`, após abrir sessão DB, buscar o medicamento por nome e checar se há bula com `caminho_pdf` válido em disco e `status ≠ ERRO` — se sim, retornar `LogAquisicao(SKIP)` imediatamente
- [x] 3.2 Passar `ultima_verificacao_anvisa=datetime.utcnow()` para `criar_bula` no caminho de download bem-sucedido (resultado BAIXADO)
- [x] 3.3 Passar `ultima_verificacao_anvisa=datetime.utcnow()` para `atualizar_status_bula` nos caminhos de SKIP online (Cenários A e C) e RECUPERADO (Cenário B)

## 4. Verificação

- [x] 4.1 Rodar `backend/scripts/executar_aquisicao.py --limite 5` e confirmar nos logs que medicamentos com PDF em disco retornam SKIP sem log de busca ANVISA
- [x] 4.2 Confirmar no banco que `ultima_verificacao_anvisa` está preenchido para bulas baixadas/recuperadas e NULL para bulas puladas via pre-checagem local

