## Purpose

Define o módulo de avaliação da qualidade das extrações da pipeline, comparando as saídas do LLM com um gabarito anotado manualmente e calculando métricas de precisão, revocação e F2-score por micro-média. Cobre contra-indicações e interações medicamentosas tipadas — a classificação farmacológica por LLM foi considerada e descartada para o TCC (ver `extracao-llm/design.md#D9`), portanto não é avaliada quantitativamente.

## ADDED Requirements

### Requirement: Comparação com gabarito manual

O sistema SHALL comparar as entidades extraídas pela etapa de extração clínica com um gabarito construído manualmente (JSONs anotados por revisão humana), usando o nome do arquivo da bula como chave de correspondência.

#### Scenario: Bula encontrada no gabarito
- **WHEN** o sistema avalia uma bula processada
- **THEN** as entidades extraídas são comparadas com as entidades do gabarito correspondentes à mesma chave (nome do arquivo)

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

O sistema SHALL, para cada entidade extraída, identificar a entidade do gabarito com maior score como melhor correspondência, sem restrição de exclusividade entre entidades.

#### Scenario: Entidade extraída encontra correspondência no gabarito
- **WHEN** o score da melhor correspondência é maior ou igual ao limiar configurado
- **THEN** a entidade é considerada verdadeiro positivo

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

### Requirement: Tabela de referência do gabarito

O sistema SHALL manter uma tabela de referência (gabarito) em formato estruturado que permita adicionar, consultar e atualizar as anotações manuais usadas na avaliação. O formato espelha o schema da etapa única de extração: cada contra-indicação tem o campo `descricao`; cada interação tem os campos `tipo` (`NOME_DIRETO`, `CLASSE` ou `ALIMENTO`), `referencia` e `efeito` (nullable).

#### Scenario: Gabarito carregado para avaliação
- **WHEN** o processo de validação é iniciado
- **THEN** o sistema carrega a tabela de referência e a usa como fonte de verdade para comparação
