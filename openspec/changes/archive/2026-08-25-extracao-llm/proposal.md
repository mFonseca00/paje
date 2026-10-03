# Extração LLM + Armazenamento

## Problema

Com as bulas convertidas em markdown e as seções relevantes extraídas (fase anterior), é necessário submeter esse texto a um LLM para identificar e estruturar as entidades clínicas — contra-indicações e interações medicamentosas — e persistir os resultados no banco de dados para consulta posterior.

## Solução Proposta

Implementar uma etapa única de extração por LLM via Pydantic AI:

**Extração clínica**: o LLM recebe o texto das seções 3 e 4 da bula (via markdown segmentado) e extrai contra-indicações e interações medicamentosas. Interações são tipadas como `NOME_DIRETO` (substância específica nomeada), `CLASSE` (classe farmacológica mencionada) ou `ALIMENTO` (alimento ou bebida mencionado). Cada interação armazena `tipo`, `referencia` (nome, classe ou alimento) e `efeito` (nullable). A resposta bruta do modelo é preservada em JSONB para auditoria. O modelo padrão é Ollama local; providers de API externos são suportados via variável de ambiente.

Quando o LLM identifica referência a seções fora do escopo inicial, invoca a tool `consultar_secao_bula` para acessar o conteúdo dessas seções sob demanda a partir do `__bruto.md`, mantendo o contexto enxuto no caso típico.

A tabela `substancias_medicamento` é populada na etapa de aquisição por split determinístico do `nome_dcb` (separador `+`), sem chamada ao LLM. A extração de classes farmacológicas fica como trabalho futuro pós-TCC.

## Motivação

Automatizar a extração que, feita manualmente, demandaria horas por bula — e fazê-lo de forma auditável (resposta bruta preservada) e reproduzível (prompt versionado).
