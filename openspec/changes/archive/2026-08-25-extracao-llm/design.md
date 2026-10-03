## Context

Continuação da pipeline iniciada em `pipeline-bulas-medicamentos`. As seções 3 e 4 das bulas já estão extraídas e normalizadas em markdown (`__secoes.md`); o markdown bruto completo também está disponível (`__bruto.md`). O banco de dados com as tabelas base já existe. O sistema roda em máquina única, sem requisitos de escala.

## Goals / Non-Goals

**Goals:**
- Definir o schema de saída do LLM para a etapa única de extração clínica
- Estabelecer como o agente Pydantic AI conecta a diferentes providers (Ollama local e APIs externas)
- Definir o fluxo de gravação no banco e tratamento de falhas de validação
- Definir o fluxo de benchmarking para seleção do modelo

**Non-Goals:**
- Fine-tuning de modelos
- Retentativas automáticas com backoff para erros de inferência
- Cache de respostas do modelo
- Extração de classes farmacológicas e substâncias ativas por LLM — movido para pós-TCC (ver D9)
- Validação quantitativa da classificação farmacológica

## Decisions

### D1 — Framework do agente: Pydantic AI

**Decisão**: Pydantic AI como framework do agente LLM, com schema de saída definido por modelos Pydantic.

**Rationale**: Suporta múltiplos providers com interface unificada, valida a saída do modelo automaticamente contra o schema, e é alinhado ao restante do ecossistema do projeto. Decisão herdada de `pipeline-bulas-medicamentos/design.md#D1`.

---

### D2 — Schema de saída: etapa única de extração clínica

**Decisão**:

Etapa única — `ExtracacaoClinica`:
```python
class ContraIndicacao(BaseModel):
    id: int
    descricao: str

class InteracaoMedicamentosa(BaseModel):
    id: int
    tipo: Literal["NOME_DIRETO", "CLASSE", "ALIMENTO"]
    referencia: str   # NOT NULL — nome da substância, classe ou alimento
    efeito: str | None = None  # nullable

class ExtracacaoClinica(BaseModel):
    contraindicacoes: list[ContraIndicacao]
    interacoes: list[InteracaoMedicamentosa]
```

**Rationale**: Etapa única de extração; a classificação farmacológica por LLM foi movida para pós-TCC (D9). O campo `id` é ordinal dentro da resposta do modelo — facilita correlação entre o JSONB bruto armazenado em `bulas` e os registros inseridos no banco, sem se confundir com o ID gerado pelo banco. `descricao` foi preferido a `texto` por ser mais expressivo no contexto clínico. `efeito` é nullable porque nem toda interação vem acompanhada de descrição do efeito na bula. O tipo `ALIMENTO` foi adicionado para cobrir interações com alimentos e bebidas (ex: alendronato vs café, suco), que aparecem em bulas da RENAME e têm relevância clínica distinta das interações medicamentosas.

---

### D3 — Estratégia de prompt: few-shot inline no arquivo de prompt

**Decisão**: O arquivo `prompts/extracao_v1.md` concentra todo o system prompt — instruções, os 4 exemplos few-shot e a sentença de fechamento — em sequência, como texto estático. A pasta `prompts/exemplos/` é mantida como repositório de referência dos pares (markdown de entrada, JSON anotado), mas não é lida pelo agente em runtime.

| Pasta | Medicamento | Conteúdo de referência |
|---|---|---|
| `exemplo_1/` | azitromicina | `__secoes.md` + JSON |
| `exemplo_2/` | amoxicilina | `__secoes.md` + JSON |
| `exemplo_3/` | amoxicilina + clavulanato | `__secoes.md` + JSON |
| `exemplo_4/` | alendronato de sódio | `__secoes.md` + `__secoes_adicionais.md` + JSON |

**Histórico**: Em uma revisão anterior (D3-R1), os exemplos foram movidos para `prompts/exemplos/` e carregados dinamicamente por `_montar_contexto_fewshot()`. A abordagem foi revertida: o número de exemplos é fixo, o prompt está sob controle do desenvolvedor e a montagem dinâmica adicionou complexidade de código — glob com filtro de sufixo, concatenação condicional para o exemplo 4 — sem ganho tangível para o escopo do TCC.

**Rationale**: Com exemplos inline, o conteúdo exato enviado ao modelo é legível diretamente no arquivo de prompt, sem lógica de carregamento no código. Editar um exemplo é editar o arquivo. A pasta `prompts/exemplos/` permanece útil para revisão e auditoria manual dos pares de anotação.

**Adendo — delimitador de fechamento**: O arquivo `prompts/extracao_v1.md` deve encerrar com sentença explícita instruindo o modelo a processar a bula recebida na mensagem do usuário. Modelos menores tendem a ancorar na recência e podem copiar a saída do último exemplo sem essa instrução.

---

### D4 — Provider padrão: Ollama local

**Decisão**: Ollama local como provider padrão. APIs externas (Anthropic, OpenAI, Gemini) configuráveis via `LLM_PROVIDER` no `.env`. A seleção do modelo Ollama é feita por benchmarks empíricos na tarefa.

**Rationale**: Herdado de `pipeline-bulas-medicamentos/design.md#D2`. Custo zero e sem dependência de conexão para o fluxo padrão.

---

### D5 — Tratamento de falha de validação

**Decisão**: Se a saída do modelo falhar na validação Pydantic, preservar a resposta bruta no campo JSONB de `bulas` e marcar o registro com status `ERRO`. Não relançar a inferência automaticamente.

**Rationale**: Retentar automaticamente pode consumir recursos sem garantia de melhoria. O operador inspeciona os ERROs e decide se reprocessa com prompt ajustado.

---

### ~~D6 — Matching de classes sem vocabulário controlado~~ — OBSOLETO

**Status**: Decisão obsoleta. A extração de classes farmacológicas por LLM e o matching de pertinência foram removidos do escopo do TCC (ver D9 e D10). Interações do tipo `CLASSE` geram alerta genérico na interface, sem verificação de pertinência.

---

### ~~D7 — Tabela de classes: flat sem nível hierárquico explícito~~ — OBSOLETO

**Status**: Decisão obsoleta. A tabela `classes_farmacologicas` foi removida do escopo do TCC junto com a extração de classes por LLM (ver D9).

---

### D8 — Migração Alembic

**Decisão**: Criar migration Alembic para: (a) renomear coluna `substancia` para `referencia` em `interacoes_medicamentosas`; (b) adicionar coluna `tipo VARCHAR NOT NULL`; (c) tornar coluna `efeito` nullable.

As tabelas `classes_farmacologicas` e `substancias_medicamento` foram removidas do escopo desta migration. `substancias_medicamento` é criada e populada na etapa de aquisição via split determinístico (ver D9).

**Rationale**: Banco existente precisa de migration controlada para não perder dados já adquiridos. Escopo reduzido em relação à versão original após remoção da extração de classes.

---

### D9 — Substâncias ativas: split determinístico no nome_dcb; classificação farmacológica pós-TCC

**Decisão**: A tabela `substancias_medicamento` é criada e populada na etapa de aquisição por split do `nome_dcb` no separador `+`, sem chamada ao LLM. Para medicamentos simples (sem `+` no nome), o nome_dcb é registrado como única substância. A extração de classes farmacológicas por LLM fica como trabalho futuro pós-TCC.

**Rationale**: O nome DCB da RENAME já contém os princípios ativos separados por `+` (ex: `amoxicilina + clavulanato de potassio`). O split determinístico cobre a maioria dos casos de cross-matching de interações `NOME_DIRETO` em medicamentos compostos sem custo de inferência. Classificação farmacológica por LLM demandaria prompt adicional, tabela de classes e lógica de matching — complexidade incompatível com o prazo disponível para o TCC.

---

### D10 — Interações por classe: alerta genérico sem verificação de pertinência

**Decisão**: Interações do tipo `CLASSE` são exibidas na interface como alerta genérico informando que a bula menciona uma categoria farmacológica e recomendando consulta a um profissional de saúde. O sistema não verifica se algum medicamento selecionado pertence à classe mencionada.

**Rationale**: A verificação de pertinência de classe dependia de `classes_farmacologicas` e do matching ILIKE — ambos removidos do escopo. O alerta genérico é informativo, honesto sobre a limitação e suficiente para o propósito do TCC.

---

### D11 — Tool para consulta de seções adicionais do markdown bruto

**Decisão**: O agente Pydantic AI dispõe de uma tool `consultar_secao_bula(referencia: str) -> str` que, quando invocada, retorna o conteúdo da seção referenciada a partir do arquivo `__bruto.md` da bula em processamento. O agente invoca a tool quando, ao processar as seções 3 e 4, identifica referência explícita a outra seção (ex: "ver item 4.3", "conforme seção 7").

O prompt few-shot instrui o modelo a invocar a tool quando perceber que informação clínica relevante está em seção não fornecida diretamente.

**Rationale**: Algumas bulas da RENAME registram interações medicamentosas em seções fora do escopo inicial do preprocessamento (ex: alendronato de sódio). Entregar o markdown bruto completo sempre consumiria tokens desnecessariamente e reduziria a qualidade da extração por excesso de contexto. A tool permite acesso sob demanda, mantendo o contexto enxuto no caso típico.

**Consequência conhecida**: Se o modelo não perceber a referência cruzada, a informação da seção extra é silenciosamente perdida. Para o TCC, esse risco é aceitável — o operador pode identificar casos problemáticos via auditoria do JSONB.

## Risks / Trade-offs

- **[Risco] Modelo local não atinge F2 ≥ 0,80 na extração clínica** → Mitigação: suporte a APIs externas sem mudança de arquitetura (D4).
- **[Trade-off] Sem retentativa automática** → ERROs precisam de intervenção manual, mas evita consumo descontrolado de recursos locais.
- **[Trade-off] Substâncias por split, não por LLM** → Nomes na forma completa (ex: "amoxicilina tri-hidratada") usados em `referencia` de interações podem não casar com o split do nome_dcb (ex: "amoxicilina"). Mitigável por matching bidirecional (`nome ILIKE '%ref%' OR ref ILIKE '%nome%'`). Aceitável para o escopo do TCC.
- **[Trade-off] Interações CLASSE sem verificação de pertinência** → Usuário vê o alerta mas não sabe se o medicamento que está usando pertence à classe. Funcionalidade completa é pós-TCC (D9).
- **[Risco] Ancoramento do modelo no último exemplo few-shot** → Modelos menores podem copiar a saída do Exemplo 4 em vez de processar o input real. Mitigação: sentença de fechamento explícita após os exemplos (D3-adendo).

## Open Questions

*(Sem questões abertas — benchmarking de modelos tratado como tarefa na pipeline.)*
