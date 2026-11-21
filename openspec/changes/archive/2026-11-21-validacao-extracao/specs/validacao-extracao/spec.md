## Purpose

Define o módulo de avaliação da qualidade das extrações da pipeline, comparando as saídas do LLM com um gabarito anotado manualmente e calculando métricas de precisão, revocação e F2-score por micro-média. Cobre contra-indicações e interações medicamentosas tipadas — a classificação farmacológica por LLM foi considerada e descartada para o TCC (ver `extracao-llm/design.md#D9`), portanto não é avaliada quantitativamente.

## ADDED Requirements

### Requirement: Comparação com gabarito manual

O sistema SHALL comparar as entidades extraídas pela etapa de extração clínica com um gabarito construído manualmente, usando o nome do arquivo PDF como chave de correspondência.

#### Scenario: Bula encontrada no gabarito
- **WHEN** o sistema avalia uma bula processada
- **THEN** as entidades extraídas são comparadas com as entidades do gabarito correspondentes ao mesmo nome de arquivo

#### Scenario: Bula não encontrada no gabarito
- **WHEN** o nome do arquivo da bula não consta no gabarito
- **THEN** o sistema registra a ausência e exclui essa bula do cálculo das métricas

### Requirement: Normalização de texto antes da comparação

O sistema SHALL aplicar normalização de texto em ambos os lados da comparação (extraído e gabarito) antes de calcular similaridade, seguindo as etapas: conversão para minúsculas, remoção de acentos e diacríticos, substituição de caracteres não alfanuméricos por espaço, remoção de espaços duplicados e remoção de espaços nas bordas.

#### Scenario: Texto normalizado corretamente
- **WHEN** dois textos semanticamente equivalentes diferem apenas em capitalização, acentos ou pontuação
- **THEN** após normalização, os tokens são idênticos e o índice de Jaccard resultante é 1,0

### Requirement: Cálculo de similaridade por índice de Jaccard

O sistema SHALL calcular a similaridade entre entidades usando o índice de Jaccard sobre conjuntos de palavras após normalização.

Para contra-indicações: `s_CI = J(descricao_extraída, descricao_gabarito)`

Para interações medicamentosas: `s_IN = 0,65 × J(referencia_e, referencia_r) + 0,35 × J(efeito_e, efeito_r)`

Quando `efeito` for nulo em qualquer um dos lados da comparação, o score de interação SHALL desconsiderar o componente de efeito e usar apenas `s_IN = J(referencia_e, referencia_r)`.

#### Scenario: Cálculo de similaridade para contra-indicação
- **WHEN** o sistema compara uma contra-indicação extraída com uma do gabarito
- **THEN** o score é o índice de Jaccard direto sobre o campo `descricao` de ambas, após normalização

#### Scenario: Cálculo de similaridade para interação com efeito disponível
- **WHEN** o sistema compara uma interação extraída com uma do gabarito e ambas têm `efeito` preenchido
- **THEN** o score é `0,65 × J(referencia) + 0,35 × J(efeito)` após normalização

#### Scenario: Cálculo de similaridade para interação sem efeito
- **WHEN** `efeito` é nulo em qualquer um dos lados da comparação de uma interação
- **THEN** o score é `J(referencia)` apenas, sem penalizar pela ausência do efeito

### Requirement: Correspondência por melhor score sem exclusividade

O sistema SHALL, para cada entidade do gabarito, identificar a entidade extraída com maior score como melhor correspondência, sem restrição de exclusividade entre entidades.

#### Scenario: Entidade extraída encontra correspondência no gabarito
- **WHEN** o score da melhor correspondência é maior ou igual ao limiar configurado
- **THEN** a entidade do gabarito é considerada verdadeiro positivo

#### Scenario: Entidade extraída não encontra correspondência adequada
- **WHEN** nenhuma entidade do gabarito atinge o score mínimo (0,45 para contra-indicações, 0,40 para interações)
- **THEN** a entidade extraída é considerada falso positivo

### Requirement: Limiares de correspondência configuráveis

O sistema SHALL usar limiares de correspondência distintos para contra-indicações (0,45) e interações medicamentosas (0,40), ambos configuráveis.

#### Scenario: Limiar para contra-indicações aplicado
- **WHEN** o score de uma contra-indicação extraída é exatamente 0,45
- **THEN** a entidade é considerada correspondência válida (verdadeiro positivo)

#### Scenario: Limiar para interações aplicado
- **WHEN** o score de uma interação medicamentosa extraída é exatamente 0,40
- **THEN** a entidade é considerada correspondência válida (verdadeiro positivo)

### Requirement: Cálculo de métricas por micro-média

O sistema SHALL calcular precisão, revocação e F2-score de forma global usando micro-média — somando os contadores de verdadeiros positivos, falsos positivos e falsos negativos de todas as bulas antes de calcular as métricas — para contra-indicações e interações de forma independente.

F2-score: `F2 = 5 × (P × R) / (4P + R)`

#### Scenario: Métricas globais calculadas por micro-média
- **WHEN** o sistema avalia o conjunto completo de bulas processadas
- **THEN** são produzidos valores globais de precisão, revocação e F2-score para contra-indicações e para interações, calculados por micro-média

### Requirement: Metas mínimas de desempenho verificáveis

O sistema SHALL indicar claramente no relatório de avaliação se as metas mínimas foram atingidas: revocação ≥ 0,90 e F2-score ≥ 0,80 para cada categoria.

#### Scenario: Meta atingida
- **WHEN** as métricas calculadas satisfazem os limiares mínimos
- **THEN** o relatório indica aprovação para a categoria correspondente

#### Scenario: Meta não atingida
- **WHEN** revocação < 0,90 ou F2-score < 0,80 para alguma categoria
- **THEN** o relatório indica falha na categoria, com os valores obtidos exibidos

### Requirement: Gabarito em planilha XLSX com JSON esperado

O sistema SHALL ler o gabarito de uma planilha XLSX (`docs/validacao/referencia_validacao.xlsx`) com as colunas `arquivo` e `json_esperado`. A coluna `arquivo` contém o nome do arquivo PDF (sem caminho). A coluna `json_esperado` contém uma string JSON com a saída esperada da extração, seguindo o mesmo schema Pydantic da etapa de extração: lista de `contraindicacoes` (campo `descricao`) e lista de `interacoes` (campos `tipo`, `referencia` e `efeito` nullable).

#### Scenario: Gabarito carregado para avaliação
- **WHEN** o processo de validação é iniciado
- **THEN** o sistema carrega a planilha, parseia o campo `json_esperado` de cada linha e usa as entidades resultantes como fonte de verdade para comparação

#### Scenario: JSON inválido em linha do gabarito
- **WHEN** o campo `json_esperado` de uma linha não é JSON válido
- **THEN** o sistema reporta o erro com o nome do arquivo e a linha, e exclui essa bula do cálculo

### Requirement: Pasta isolada para PDFs de validação

O sistema SHALL processar os PDFs de validação a partir de `docs/validacao/pdfs/`. Esta pasta é preenchida manualmente e não é escrita pelo pipeline de aquisição.

#### Scenario: PDF de validação localizado
- **WHEN** o script de validação é executado
- **THEN** processa todos os PDFs presentes em `data/validacao/pdfs/` cujos nomes constam na planilha de gabarito

#### Scenario: PDF presente na planilha mas ausente na pasta
- **WHEN** o nome do arquivo consta no gabarito mas o PDF não está em `docs/validacao/pdfs/`
- **THEN** o sistema reporta a ausência e exclui essa bula do cálculo

### Requirement: Output versionado por execução

O sistema SHALL gravar os resultados de cada execução em `docs/validacao/resultados/{data}_{prompt_versao}_{modelo}/`, onde `data` é a data/hora local no formato `YYYY-MM-DDTHH-MM-SS`, `prompt_versao` é o valor de `settings.prompt_version` e `modelo` é o identificador do modelo LLM utilizado. Dentro dessa pasta, SHALL existir um arquivo JSON por bula avaliada e um arquivo `relatorio.json` com as métricas agregadas e a metadata da execução.

#### Scenario: Resultado por bula gravado
- **WHEN** o script de validação conclui a avaliação de uma bula
- **THEN** grava `{nome_arquivo}.json` na pasta da execução com os campos: `arquivo`, `contraindicacoes` (tp, fp, fn, matches com gabarito, extraida, score e classificacao) e `interacoes` (mesma estrutura)

#### Scenario: Relatório geral gravado
- **WHEN** o script de validação conclui todas as bulas
- **THEN** grava `relatorio.json` na pasta da execução contendo: `execucao` (data, prompt_versao, modelo), `total_bulas`, métricas de `contraindicacoes` (precisao, revocacao, f2, aprovado, tp, fp, fn), métricas de `interacoes` (mesma estrutura) e `aprovado_geral`

#### Scenario: Execuções anteriores preservadas
- **WHEN** o script de validação é executado mais de uma vez
- **THEN** cada execução cria uma pasta separada sem sobrescrever resultados anteriores

### Requirement: Extração usando as mesmas funções do pipeline de produção

O sistema de validação SHALL reutilizar diretamente as funções internas do pipeline de extração (`extrair_bula`, `converter_pdf_para_markdown`, `extrair_secoes_relevantes`) sem duplicar lógica. Não SHALL gravar resultados no banco de dados de produção.

#### Scenario: Mudança no prompt refletida na validação
- **WHEN** o prompt de extração é alterado
- **THEN** a próxima execução do script de validação usa automaticamente o novo prompt, sem nenhuma alteração no código de validação

#### Scenario: Mudança no pré-processamento refletida na validação
- **WHEN** a lógica de conversão PDF→markdown ou extração de seções é alterada
- **THEN** a próxima execução do script de validação usa automaticamente o novo pré-processamento
