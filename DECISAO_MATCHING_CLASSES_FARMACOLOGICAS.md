# Decisão em aberto: matching de interações por classe farmacológica

## Contexto

Interações medicamentosas extraídas das bulas são armazenadas com três tipos:
- `NOME_DIRETO` — substância específica (ex: "varfarina")
- `CLASSE` — categoria farmacológica (ex: "anticoagulantes orais")
- `ALIMENTO`

Para que a interface consiga detectar conflitos entre medicamentos selecionados,
interações `NOME_DIRETO` já funcionam com matching por texto normalizado.

Interações `CLASSE` exigem saber a qual classe cada medicamento pertence —
dado que não está no banco atualmente.

Exemplo do problema:
```
Bula de azitromicina registra:
  tipo=CLASSE, referencia="anticoagulantes cumarínicos"

Usuário seleciona [azitromicina, varfarina].

Para detectar o conflito, o sistema precisaria saber:
  varfarina ∈ classe "anticoagulantes cumarínicos"  ← não está no banco
```

---

## Opção 1 — Extrair classe da bula (seção 1)

A seção 1 das bulas paciente ("O QUE É ESTE MEDICAMENTO?") quase sempre descreve
a classe farmacológica do próprio medicamento:

> *"Azitromicina é um antibiótico da classe dos macrolídeos..."*
> *"Varfarina é um anticoagulante oral do grupo das cumarinas..."*

### Como funcionaria

- Estender a etapa de preprocessamento para extrair também a seção 1
- Armazenar as classes numa nova tabela `classes_medicamento`
- No matching da interface: verificar se alguma classe do medicamento selecionado
  aparece (fuzzy) na `referencia` da interação

Há dois caminhos para a chamada ao LLM:

#### Caminho A — mesma chamada, prompt estendido

Adicionar a extração de classe ao prompt e schema já existentes. O agente recebe
seções 1 + 3 + 4 numa única chamada e retorna classes + contra-indicações + interações.

```
Entrada: seção 1 + seção 3 + seção 4
Prompt:  extracao_v1.md ampliado com instruções de classe
Schema:  ExtracacaoClinica + classes_farmacologicas: list[str]
Calls:   1 por bula
```

**A favor:** uma chamada por bula, sem nova etapa na pipeline.

**Contra:** contexto maior sem necessidade — o prompt atual já tem ~370 linhas com 4 exemplos. Extrair classe é uma tarefa muito mais simples do que tipificar interações e acionar tools; misturar as duas no mesmo prompt cresce o contexto para resolver uma pergunta factual simples. Qualquer iteração no prompt afeta as duas tarefas.

#### Caminho B — etapa separada, prompt dedicado

Nova etapa na pipeline com prompt próprio, voltada exclusivamente para metadados do medicamento (classe farmacológica). A extração clínica (seções 3 e 4) permanece inalterada.

```
Etapa nova:   seção 1 → prompt_metadados_v1.md → classes_farmacologicas
Etapa atual:  seção 3 + 4 → extracao_v1.md → contraindicacoes + interacoes
Calls:        2 por bula (sequenciais ou paralelas)
Schema novo:  MetadadosMedicamento { classes_farmacologicas: list[str] }
```

**A favor:** separação de responsabilidades — prompts focados, schemas enxutos,
falhas isoladas. Contexto menor por chamada. Permite usar modelo mais leve/barato
para a etapa de metadados, já que a tarefa é factual e sem ambiguidade de tipagem.
Iterações no prompt de classe não afetam a extração clínica.

**Contra:** duas chamadas ao LLM por bula; nova etapa na pipeline.

#### Comparativo

```
                      Caminho A          Caminho B
                      ──────────         ──────────
Chamadas por bula     1                  2
Contexto por call     maior              menor (cada uma)
Manutenção prompt     1 arquivo cresce   2 arquivos focados
Modelo da etapa       = clínico          pode ser mais leve
Falhas isoladas?      não                sim
Iteração independente não                sim
```

### Prós (ambos os caminhos)
- Permanece dentro da arquitetura atual (mesma pipeline, mesmo LLM)
- Fonte primária: a bula oficial da ANVISA
- Sem nova integração de dados externa

### Contras (ambos os caminhos)
- Matching ainda é fuzzy (texto varia entre bulas)
- A classe extraída depende da qualidade do texto da seção 1
- Cobertura incompleta: algumas bulas descrevem a classe de forma vaga

---

## Opção 2 — CMED com código ATC

A CMED (Câmara de Regulação do Mercado de Medicamentos, órgão da ANVISA) publica
lista de preços de medicamentos com código ATC da OMS — pública, atualizada, em
Excel/CSV.

O código ATC é hierárquico:
```
B 01 AA 03    ← warfarina
│  │  │
│  │  └──── subgrupo: antagonistas vitamina K (= "anticoagulantes cumarínicos")
│  └──────── subgrupo terapêutico: antitrombóticos
└─────────── grupo: sangue e órgãos hematopoiéticos

J 01 FA 10    ← azitromicina
      └──── macrolídeos
```

### Como funcionaria

- Baixar a lista CMED e cruzar com a RENAME para mapear DCB → código ATC
- Criar tabela `atc_medicamento` com o código e descrição de cada nível
- Criar dicionário manual (ou via LLM offline) mapeando `referencia` de interações
  para prefixos ATC (ex: "anticoagulantes cumarínicos" → `B01AA`)
- No matching: comparar prefixo ATC do medicamento selecionado com o prefixo
  mapeado da referência

### Prós
- Classificação padronizada e citável (OMS/ANVISA)
- Matching exato por código em vez de texto
- Academicamente mais robusto para o TCC

### Contras
- Nova integração de dados (CMED)
- Exige construir/manter mapeamento referencia → código ATC
- Dependência de atualização da lista CMED

---

## Opção 3 — LLM on-demand na interface (descartada)

Chamada ao LLM no momento da query para verificar se o medicamento pertence
à classe referenciada.

**Descartada.** Chamadas ao LLM não serão feitas durante a interface —
apenas na etapa de extração de dados da pipeline.

---

## Status

Explorando opções 1 e 2. Decisão pendente. Pode ser viável uma combinação das duas opções.
