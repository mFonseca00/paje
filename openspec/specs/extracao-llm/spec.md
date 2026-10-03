## Purpose

Responsável por submeter as bulas a um LLM via few-shot prompting em etapa única: extrai contra-indicações e interações medicamentosas tipadas (por nome direto ou por classe) a partir das seções relevantes da bula.

## Requirements

### Requirement: Extração de entidades clínicas com tipagem de interações

O sistema SHALL submeter o texto das seções relevantes da bula (seções 3 e 4, via markdown segmentado) ao LLM acompanhado de exemplos few-shot, produzindo uma saída JSON com contra-indicações e interações medicamentosas tipadas.

Cada interação SHALL ser classificada como `NOME_DIRETO` (substância específica nomeada), `CLASSE` (categoria farmacológica) ou `ALIMENTO` (alimento ou bebida que interfere na absorção ou segurança do medicamento). Quando uma frase mistura nomes específicos e classes, o LLM SHALL produzir registros separados para cada item.

#### Scenario: Extração bem-sucedida com interações mistas
- **WHEN** o modelo recebe o texto das seções relevantes e os exemplos few-shot
- **THEN** retorna JSON válido com listas de contra-indicações e interações; cada item contém `id` (ordinal dentro da resposta); cada interação contém `tipo` (`NOME_DIRETO`, `CLASSE` ou `ALIMENTO`), `referencia` (NOT NULL) e `efeito` (nullable)

#### Scenario: Modelo retorna JSON inválido ou malformado
- **WHEN** a resposta do modelo não está em JSON válido
- **THEN** o sistema registra o erro, preserva a resposta bruta para auditoria e marca a bula com status ERRO

### Requirement: Saída JSON normalizada

O sistema SHALL garantir que a saída do LLM para cada bula siga o esquema JSON abaixo:

```json
{
  "contraindicacoes": [
    {"id": 1, "descricao": "..."}
  ],
  "interacoes": [
    {"id": 1, "tipo": "NOME_DIRETO", "referencia": "...", "efeito": null},
    {"id": 2, "tipo": "CLASSE", "referencia": "...", "efeito": null},
    {"id": 3, "tipo": "ALIMENTO", "referencia": "...", "efeito": "..."}
  ]
}
```

O campo `id` é ordinal dentro da resposta do modelo (1, 2, 3…) e não se relaciona com o ID gerado pelo banco ao inserir os registros.

#### Scenario: Saída segue o esquema definido
- **WHEN** o modelo retorna o JSON
- **THEN** cada item de contra-indicação contém `id` (inteiro) e `descricao`; cada item de interação contém `id`, `tipo` e `referencia` (todos NOT NULL); `efeito` pode ser nulo

#### Scenario: Campo obrigatório ausente na saída
- **WHEN** a saída do modelo está faltando `tipo` ou `referencia` em um item de interação
- **THEN** o sistema valida a estrutura, registra o campo ausente e marca a bula com status ERRO

### Requirement: Suporte a modelos locais via Ollama

O sistema SHALL suportar execução da inferência usando modelos locais via Ollama como alternativa ao uso de APIs externas. O sistema SHALL também suportar Gemini como provider de produção via `google-genai` SDK, declarado como dependência explícita no `pyproject.toml`. Quando `LLM_PROVIDER=gemini`, o sistema SHALL funcionar corretamente incluindo tool calling e saída estruturada JSON validada via Pydantic.

O modelo Gemini recomendado é `gemini-2.0-flash`. A chave de acesso SHALL ser lida de `GEMINI_API_KEY` no arquivo `.env`.

#### Scenario: Modelo local configurado
- **WHEN** a configuração aponta para um endpoint Ollama local
- **THEN** o sistema envia as requisições de inferência ao Ollama sem necessitar de chave de API externa

#### Scenario: Modelo remoto via API configurado
- **WHEN** a configuração define `LLM_PROVIDER` como `anthropic`, `openai` ou `gemini`
- **THEN** o sistema usa a chave de API correspondente (`ANTHROPIC_API_KEY`, `OPENAI_API_KEY` ou `GEMINI_API_KEY`) e envia as requisições ao provider configurado

#### Scenario: Gemini executa extração com tool calling
- **WHEN** `LLM_PROVIDER=gemini` e o texto das seções referencia outra seção da bula
- **THEN** o agente invoca `consultar_secao_bula` corretamente via Gemini function calling e incorpora o conteúdo na extração antes de retornar o JSON

#### Scenario: Gemini retorna saída estruturada válida
- **WHEN** `LLM_PROVIDER=gemini` e a extração é executada para uma bula
- **THEN** o modelo retorna JSON validado pelo schema Pydantic com `contraindicacoes` e `interacoes` corretamente tipadas

### Requirement: Versionamento de prompt

O sistema SHALL manter o prompt em arquivo versionável e registrar qual versão de prompt foi usada em cada extração.

#### Scenario: Extração realizada com prompt versionado
- **WHEN** a pipeline executa a extração de uma bula
- **THEN** o registro da bula no banco armazena o identificador da versão do prompt utilizado

### Requirement: Preservação da resposta bruta do modelo

O sistema SHALL armazenar a resposta JSON completa retornada pelo modelo no banco de dados para fins de auditoria e reprocessamento sem nova chamada ao modelo.

#### Scenario: Resposta preservada após extração
- **WHEN** a extração de uma bula é concluída (com ou sem sucesso na validação do esquema)
- **THEN** a resposta bruta do modelo é salva no campo JSONB da tabela `bulas`

### Requirement: Controle de contexto

O sistema SHALL submeter ao modelo apenas as seções de contra-indicações e interações medicamentosas (markdown segmentado `__secoes.md`) para a extração clínica.

#### Scenario: Extração recebe apenas seções relevantes
- **WHEN** a pipeline executa a extração para uma bula
- **THEN** o corpo do prompt contém apenas o texto das seções relevantes pré-extraídas do arquivo `__secoes.md`

### Requirement: Tool para consulta de seções adicionais

O sistema SHALL disponibilizar ao agente uma tool `consultar_secao_bula(referencia: str) -> str` que retorna o conteúdo da seção referenciada a partir do arquivo `__bruto.md` da bula em processamento. O prompt SHALL instruir o agente a invocar a tool quando identificar referência explícita a seção não fornecida diretamente.

#### Scenario: Agente invoca tool por referência cruzada
- **WHEN** o texto das seções 3 e 4 menciona outra seção como fonte de informação clínica (ex: "ver item 4.3", "conforme descrito na seção 7")
- **THEN** o agente invoca `consultar_secao_bula` com a referência identificada e incorpora o conteúdo retornado na extração antes de produzir o JSON final

#### Scenario: Nenhuma referência cruzada identificada
- **WHEN** as seções 3 e 4 não contêm referência explícita a outras seções
- **THEN** o agente conclui a extração sem invocar a tool, usando apenas o conteúdo do `__secoes.md`
