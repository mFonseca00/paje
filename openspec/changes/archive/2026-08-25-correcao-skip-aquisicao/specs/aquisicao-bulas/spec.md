## MODIFIED Requirements

### Requirement: Controle de duplicatas

O sistema SHALL verificar se a bula já foi baixada anteriormente antes de realizar um novo download, considerando tanto o `id_bula_anvisa` armazenado quanto a existência do arquivo PDF em disco.

**Cenário A — mesmo JWT, arquivo presente (comportamento existente):**
O sistema verifica o `id_bula_anvisa` no banco. Se encontrado com status ≠ ERRO e o arquivo `caminho_pdf` existe em disco, pula o download.

**Cenário B — mesmo JWT, arquivo ausente:**
O sistema verifica o `id_bula_anvisa` no banco. Se encontrado com status ≠ ERRO mas o arquivo `caminho_pdf` não existe em disco, realiza novo download, atualiza `caminho_pdf` no banco e retorna `RECUPERADO`.

**Cenário C — JWT novo, mas medicamento já tem PDF válido em disco:**
Quando `id_bula_anvisa` não é encontrado no banco (JWT rotacionado pela ANVISA), o sistema SHALL verificar se o medicamento já possui algum registro de bula com arquivo presente em disco. Se existir, pula o download e retorna `SKIP`.

**Cenário D — JWT novo, sem PDF válido em disco:**
Quando `id_bula_anvisa` não é encontrado no banco e nenhum registro do medicamento possui arquivo em disco, o sistema SHALL deletar os registros de bula fantasma do medicamento antes de realizar o download e criar novo registro.

#### Scenario: Bula já existe no banco com arquivo em disco presente

- **WHEN** o `id_bula_anvisa` já está registrado no banco com status diferente de ERRO e o arquivo `caminho_pdf` existe em disco
- **THEN** o sistema retorna `SKIP` sem realizar download

#### Scenario: Bula existe no banco mas arquivo em disco ausente

- **WHEN** o `id_bula_anvisa` já está registrado no banco com status diferente de ERRO e o arquivo `caminho_pdf` não existe em disco
- **THEN** o sistema realiza novo download, atualiza `caminho_pdf` no banco com o novo caminho e retorna `RECUPERADO`

#### Scenario: JWT rotacionado com PDF válido existente em disco

- **WHEN** o `id_bula_anvisa` retornado pela ANVISA não existe no banco e o medicamento já possui ao menos um registro com `caminho_pdf` apontando para arquivo existente em disco
- **THEN** o sistema retorna `SKIP` sem realizar download

#### Scenario: JWT rotacionado sem PDF válido em disco

- **WHEN** o `id_bula_anvisa` retornado pela ANVISA não existe no banco e nenhum registro do medicamento possui arquivo em disco
- **THEN** o sistema deleta os registros fantasma do medicamento, realiza o download e cria novo registro com `caminho_pdf` atualizado

#### Scenario: Bula está marcada como ERRO

- **WHEN** o ID de bula está registrado com status ERRO e `reprocessar_erro=True`
- **THEN** o sistema realiza nova tentativa de download
