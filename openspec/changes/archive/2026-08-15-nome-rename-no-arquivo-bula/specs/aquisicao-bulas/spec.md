## MODIFIED Requirements

### Requirement: Nomenclatura identificável do arquivo PDF

O sistema SHALL salvar o PDF com nome no formato `{tipo}__{slug}__{sufixo}.pdf`, onde `tipo` é `paciente` ou `profissional` conforme configuração, `slug` é o nome do medicamento normalizado (apenas alfanuméricos substituindo caracteres especiais por `_`, sem truncamento), e `sufixo` são os últimos 8 caracteres do ID da bula.

Quando a bula for localizada via fallback de nome comercial, `slug` SHALL ser composto pelo nome DCB seguido de `__` e pelo nome comercial, no formato `{dcb}__{comercial}`, resultando no nome de arquivo `{tipo}__{dcb}__{comercial}__{sufixo}.pdf`.

#### Scenario: Arquivo salvo sem fallback (nome DCB encontrado diretamente)

- **WHEN** o PDF é baixado com `ANVISA_TIPO_BULA=paciente` e a bula foi encontrada diretamente pelo nome DCB
- **THEN** o arquivo é salvo com nome no formato `paciente__<slug_dcb>__<sufixo>.pdf`, sem truncamento do nome

#### Scenario: Arquivo salvo via fallback de nome comercial

- **WHEN** a busca pelo nome DCB retorna vazio e a bula é localizada via nome comercial
- **THEN** o arquivo é salvo com nome no formato `{tipo}__{slug_dcb}__{slug_comercial}__{sufixo}.pdf`, contendo o nome DCB antes do nome comercial

#### Scenario: Arquivo salvo com prefixo de tipo profissional

- **WHEN** o PDF é baixado com `ANVISA_TIPO_BULA=profissional`
- **THEN** o arquivo é salvo com nome iniciando com `profissional__`
