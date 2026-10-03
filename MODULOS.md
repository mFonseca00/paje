# Módulos do Pajé — Documentação Técnica Detalhada

Situação atual de cada módulo implementado: o que faz, como faz, fluxo interno, tecnologias e comandos relevantes.

---

## Visão geral do fluxo

```
docs/RENAME_10-08-2026.xlsx
        │  carregar_nomes_rename()
        ▼
  lista de DCBs (nomes normalizados)
        │
        ▼ para cada DCB:
┌─────────────────────────────────────┐
│  módulo: aquisicao                  │
│  buscar_bulas() → ANVISA API        │
│  fallback: nomes comerciais A/B     │
│  baixar_pdf() → bytes               │
│  salvar em docs/bulas/              │
│  registrar em DB: medicamentos+bulas│
│  status: PENDENTE                   │
└────────────────┬────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────┐
│  módulo: preprocessamento           │
│  converter_pdf_para_markdown()      │
│  extrair_secoes_relevantes()        │
│  → docs/markdown_bulas/            │
│    __bruto.md    (markdown completo)│
│    __secoes.md   (seções 3 e 4)    │
└────────────────┬────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────┐
│  módulo: extracao                   │
│  agente pydantic-ai lê __secoes.md  │
│  tool consultar_secao_bula          │
│  → ExtracacaoClinica (Pydantic)     │
│  gravar: contraindicacoes           │
│          interacoes_medicamentosas  │
│  status: PROCESSADO ou ERRO         │
└─────────────────────────────────────┘
```

---

## 1. `backend/config.py`

Centraliza toda a configuração via variáveis de ambiente usando **pydantic-settings**.

Lê `.env` na raiz do projeto. Expõe `settings` como singleton importado pelos demais módulos.

**Principais grupos de configuração:**

| Grupo | Variáveis-chave | Padrão |
|---|---|---|
| Banco | `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD` | localhost:5433/paje |
| ANVISA | `ANVISA_BASE_URL`, `ANVISA_DELAY_SEGUNDOS`, `ANVISA_TIPO_BULA` | paciente, delay 1.5s |
| LLM | `LLM_PROVIDER`, `LLM_MODEL`, `OLLAMA_BASE_URL`, `LLM_NUM_CTX` | ollama / llama3.2 / 4096 |
| Pipeline | `PIPELINE_AQUISICAO_HABILITADA`, `PIPELINE_PREPROCESSAMENTO_HABILITADA`, `PIPELINE_EXTRACAO_HABILITADA` | todas true |
| Paths | `BULAS_DIR`, `MARKDOWN_DIR`, `RENAME_PATH` | docs/bulas, docs/markdown_bulas |

**Propriedade calculada:**
```python
settings.database_url  # → postgresql://user:senha@host:port/db
```

---

## 2. `backend/aquisicao/`

### 2.1 `cliente.py` — HTTP com a ANVISA

Usa **curl_cffi** com `impersonate="chrome"` para replicar o TLS fingerprint de um navegador Chrome real, evitando bloqueios anti-bot.

**Endpoints consumidos:**

```
GET https://consultas.anvisa.gov.br/api/consulta/bulario
    ?count=10&filter[nomeProduto]=<nome>&page=1
    → retorna lista de registros com idBulaPacienteProtegido e idBulaProfissionalProtegido

GET https://consultas.anvisa.gov.br/api/consulta/medicamentos/arquivo/bula/parecer/<id>/?Authorization=
    → retorna bytes do PDF
```

**Hierarquia de erros:**

| Erro | Condição | Comportamento |
|---|---|---|
| `BloqueioAnvisaError` | HTTP 429 ou HTML inesperado (CAPTCHA) | Para toda a aquisição |
| `AcessoNegadoError` | HTTP 403 | Registra ERRO para a bula, continua |
| `ErroTransitorioAnvisaError` | HTTP 5xx | Retry com backoff exponencial |

**Dataclass de resultado:**
```python
@dataclass
class ResultadoBusca:
    id_bula_paciente: str | None
    id_bula_profissional: str | None
    nome_produto: str
    expediente: str | None
```

### 2.2 `rename.py` — Leitura da RENAME

Lê o Excel da RENAME (`docs/RENAME_10-08-2026.xlsx`), coluna A a partir da linha 4 (DCBs), normaliza os nomes via `utils.texto.normalizar()` e retorna lista deduplicada.

**Normalização:** minúsculas + remoção de acentos + espaços duplicados.

### 2.3 `referencia.py` — Listas A e B de referência ANVISA

Lê os dois Excels de medicamentos de referência da ANVISA (listas A e B). Constrói mapeamento:
```
{ farmaco_normalizado: [nome_comercial_1, nome_comercial_2, ...] }
```

Usado como fallback quando a busca pelo DCB não retorna resultado.

### 2.4 `fluxo.py` — Orquestrador da aquisição

**Ponto de entrada:** `executar_aquisicao(limite, reprocessar_erro, nomes)`

**Estados possíveis por medicamento:**

| Resultado | Situação |
|---|---|
| `BAIXADO` | PDF novo baixado e registrado |
| `SKIP` | PDF válido já existe em disco |
| `RECUPERADO` | Mesmo JWT, PDF sumiu do disco — re-baixou |
| `REPROCESSADO` | Bula com ERRO redefinida para PENDENTE |
| `SUBSTITUIDO` | JWT novo substituindo entrada anterior |
| `NAO_ENCONTRADO` | Não achou no DCB nem nos nomes comerciais |
| `ERRO` | Falha de download ou acesso negado |

**Fluxo de decisão por medicamento:**

```
1. Pré-checagem local: PDF válido em disco? → SKIP (sem request ANVISA)
2. Busca ANVISA pelo DCB
   └─ sem resultado → fallback pelos nomes comerciais das listas A/B
   └─ sem resultado → NAO_ENCONTRADO
3. id_bula encontrado no banco?
   ├─ sim, status != ERRO, PDF em disco → SKIP (atualiza ultima_verificacao_anvisa)
   ├─ sim, status != ERRO, PDF sumiu → RECUPERADO (re-baixa)
   ├─ sim, status == ERRO, sem flag → SKIP
   └─ sim, status == ERRO, com flag → REPROCESSADO (status → PENDENTE)
4. Medicamento no banco com outro JWT?
   ├─ PDF válido em disco → SKIP (JWT rotacionado)
   └─ sem PDF → deleta registros fantasma
5. Download do PDF → BAIXADO
```

**Retry com backoff exponencial** para `ErroTransitorioAnvisaError`:
- Padrão: 3 tentativas, espera inicial 5s, dobra a cada tentativa

---

## 3. `backend/preprocessamento/`

### 3.1 `conversor.py`

Converte PDF para markdown usando **pymupdf4llm**:
```python
import pymupdf4llm
markdown = pymupdf4llm.to_markdown(str(pdf_path))
```

Preserva estrutura de headings, negrito e tabelas do PDF.

### 3.2 `extrator.py`

Extrai as **seções 3 e 4** do template de bula paciente da ANVISA:
- Seção 3: "QUANDO NÃO DEVO USAR?" (contra-indicações)
- Seção 4: "O QUE DEVO SABER ANTES?" (precauções + interações)

**Problema que resolve:** o agente LLM recebe apenas as seções relevantes (~2–10 KB) em vez do markdown completo da bula (às vezes 50+ KB), reduzindo custo de tokens e aumentando precisão.

**Formatos reconhecidos como heading de seção:**
- `# 3. TÍTULO` ou `## 3. TÍTULO` (heading markdown com `#`)
- `**3. TÍTULO**` (bold sem `#` — gerado por alguns PDFs)

**O que faz com o bloco extraído:**
- Headings numerados → `##`
- Headings não-numerados → `###`
- Linhas `**texto**` sem pontuação final → promovidas a `###` (subheadings)

**Fallback:** se nenhuma seção-alvo for encontrada, retorna o markdown bruto completo e sinaliza `markdown_bruto_usado=True`.

**Saída:** dois arquivos por bula em `docs/markdown_bulas/`:
- `<stem>__bruto.md` — markdown completo do PDF
- `<stem>__secoes.md` — apenas seções 3 e 4 normalizadas

**Convenção de nomenclatura dos PDFs:**
```
<tipo_bula>__<nome_dcb>__<nome_comercial>__<ultimos_8_chars_id>.pdf
```

---

## 4. `backend/extracao/`

### 4.1 `schemas.py` — Estrutura da saída

```python
class ContraIndicacao(BaseModel):
    ordinal: int
    descricao: str

class InteracaoMedicamentosa(BaseModel):
    ordinal: int
    tipo: Literal["NOME_DIRETO", "CLASSE", "ALIMENTO"]
    referencia: str
    efeito: str | None = None

class ExtracacaoClinica(BaseModel):
    contraindicacoes: list[ContraIndicacao]
    interacoes: list[InteracaoMedicamentosa]
```

**Tipos de interação:**
- `NOME_DIRETO` — substância específica (ex: "varfarina", "digoxina")
- `CLASSE` — categoria farmacológica (ex: "anticoagulantes orais", "diuréticos")
- `ALIMENTO` — alimento ou bebida (ex: "leite", "álcool", "suco de laranja")

### 4.2 `agente.py` — Agente pydantic-ai

Usa **pydantic-ai** para orquestrar a chamada ao LLM com output tipado.

**Seleção de provider** via `LLM_PROVIDER`:

| Provider | Biblioteca | Nota |
|---|---|---|
| `ollama` | pydantic-ai + OpenAIProvider (compat) | Warmup via API nativa `/api/chat` para garantir `num_ctx` correto |
| `anthropic` | pydantic-ai AnthropicModel | Requer `ANTHROPIC_API_KEY` |
| `openai` | pydantic-ai OpenAIChatModel | Requer `OPENAI_API_KEY` |
| `gemini` | pydantic-ai GoogleModel | Requer `GEMINI_API_KEY` |

**Warmup do Ollama:** o endpoint OpenAI-compat (`/v1/chat/completions`) do Ollama ignora `num_ctx` no carregamento do modelo. O agente faz um request prévio via API nativa (`/api/chat`) com `options.num_ctx` para garantir a janela de contexto correta antes da inferência.

**Tool disponível ao agente:**
```python
def consultar_secao_bula(ctx: RunContext[ContextoBula], referencia: str) -> str:
    """Retorna o conteúdo da seção referenciada a partir do markdown bruto.
    
    Usado quando __secoes.md menciona 'ver item 4.5', 'conforme seção 7', etc.
    """
```

O agente invoca essa tool quando o texto das seções 3 e 4 faz referência cruzada a outra seção da bula. A tool lê o `__bruto.md` e retorna o conteúdo da seção solicitada.

**Prompt:** carregado de `prompts/extracao_v1.md` — few-shot com 4 bulas reais anotadas:
- azitromicina (interações mistas, referência cruzada)
- amoxicilina (penicilínico simples)
- amoxicilina + clavulanato (associação)
- alendronato de sódio (referência cruzada → tool obrigatória)

**Singleton:** o agente é inicializado uma vez por processo (`_agente` global) e reutilizado em todas as bulas do lote.

### 4.3 `pipeline.py` — Extração em lote

**Preprocessamento sob demanda:** `_garantir_markdown(bula)` verifica se `__secoes.md` e `__bruto.md` já existem. Se não, gera a partir do PDF em tempo real antes da extração. Isso é fallback — a etapa de preprocessamento do pipeline já os gera antes.

**Fluxo por bula:**
```
bula (status=PENDENTE)
    │
    ▼
_garantir_markdown() → (caminho_secoes, caminho_bruto)
    │
    ▼
extrair_bula(caminho_secoes, caminho_bruto) → ExtracacaoClinica
    │
    ├─ sucesso:
    │    atualizar_status_bula(PROCESSADO, resposta_bruta, versao_prompt)
    │    criar_contraindicacao() × N
    │    criar_interacao() × M
    │
    └─ exceção:
         atualizar_status_bula(ERRO, {"erro": str(e)}, versao_prompt)
```

**Reprocessamento:** se `reprocessar_erro=True`, inclui bulas com status ERRO além das PENDENTES.

---

## 5. `backend/armazenamento/`

### 5.1 `modelos.py` — Schema SQLAlchemy

**Tabelas:**

```
medicamentos
  id, nome_comercial, nome_dcb, substancia_ativa, criado_em

bulas
  id, medicamento_id (FK), id_bula_anvisa (UNIQUE), caminho_pdf
  status_processamento_ia (PENDENTE|PROCESSADO|ERRO)
  resposta_bruta_modelo (JSONB)   ← saída completa do modelo, para auditoria
  versao_prompt, ultima_verificacao_anvisa, criado_em, atualizado_em

contraindicacoes
  id, bula_id (FK), texto

interacoes_medicamentosas
  id, bula_id (FK), tipo, referencia, efeito

substancias_medicamento
  id, medicamento_id (FK), nome
  (gerado via split por '+' do nome_dcb — suporta medicamentos compostos)
```

**Campo `resposta_bruta_modelo` (JSONB):** preserva o JSON completo do modelo para:
- Auditoria e rastreabilidade
- Reprocessamento sem nova chamada ao modelo
- Comparação de desempenho entre versões do prompt

**Campo `id_bula_anvisa`:** JWT longo gerado pela ANVISA. Rotaciona periodicamente — o sistema detecta isso e trata adequadamente no módulo de aquisição.

### 5.2 `repositorio.py` — Acesso a dados

Funções puras que recebem `Session` como primeiro argumento (sem gerenciamento de contexto interno):

```python
# Medicamentos
criar_medicamento(session, nome_comercial, substancia_ativa, nome_dcb)
buscar_medicamento_por_nome(session, nome)   # busca por nome_comercial OU nome_dcb
listar_medicamentos(session)

# Bulas
criar_bula(session, medicamento_id, id_bula_anvisa, caminho_pdf, ultima_verificacao_anvisa)
buscar_bula_por_id_anvisa(session, id_bula_anvisa)
atualizar_status_bula(session, bula_id, status, resposta_bruta, versao_prompt, ...)
listar_bulas_por_status(session, status)

# Entidades extraídas
criar_contraindicacao(session, bula_id, texto)
criar_interacao(session, bula_id, tipo, referencia, efeito)

# Substâncias (geradas no momento da aquisição)
criar_substancias_medicamento(session, medicamento_id, nome_dcb)
listar_substancias_por_medicamento(session, medicamento_id)
```

### 5.3 Migrações Alembic

5 versões aplicadas em sequência:

| Revisão | O que faz |
|---|---|
| `275a6b9832bb` | Cria tabelas iniciais: medicamentos, bulas, contraindicacoes, interacoes_medicamentosas |
| `46693402bb00` | Amplia `id_bula_anvisa` de 100 para 500 chars (IDs JWT são longos) |
| `ec401c233308` | Adiciona coluna `nome_dcb` em medicamentos |
| `b2c3d4e5f6a1` | Cria tabela `substancias_medicamento` |
| `a1b2c3d4e5f6` | Ajusta interações medicamentosas (tipo + referencia em vez de substancia+efeito) |
| `c3d4e5f6a1b2` | Adiciona `ultima_verificacao_anvisa` em bulas |

**Comandos:**
```bash
cd backend
alembic upgrade head        # aplica todas as migrações
alembic current             # versão atual do schema
alembic history             # histórico de revisões
alembic downgrade -1        # volta uma versão
```

---

## 6. `backend/scripts/`

### `executar_pipeline.py`

Script principal. Executa as 3 etapas em sequência. Cada etapa pode ser desabilitada via `.env`.

```bash
python backend/scripts/executar_pipeline.py
python backend/scripts/executar_pipeline.py --limite 10
python backend/scripts/executar_pipeline.py --limite 5 --reprocessar-erro
```

### `executar_aquisicao.py`

Executa só a etapa de aquisição. Imprime resumo com contadores por resultado.

```bash
python backend/scripts/executar_aquisicao.py
python backend/scripts/executar_aquisicao.py --limite 10
python backend/scripts/executar_aquisicao.py --reprocessar-erro
```

### `executar_extracao.py`

Executa só a extração LLM sobre bulas PENDENTES (ou ERRO com a flag).

```bash
python backend/scripts/executar_extracao.py
python backend/scripts/executar_extracao.py --limite 5
python backend/scripts/executar_extracao.py --reprocessar-erro
```

### Scripts de diagnóstico

| Script | Uso |
|---|---|
| `testar_banco.py` | Verifica conexão com PostgreSQL |
| `testar_busca.py <nome>` | Testa busca de um medicamento na ANVISA e imprime resultado |
| `testar_preprocessamento.py <pdf>` | Converte um PDF e mostra as seções extraídas |
| `testar_extracao.py <pdf> [--saida dir]` | Extrai uma bula e salva JSON; útil para benchmark de modelos |

---

## 7. `prompts/extracao_v1.md`

Prompt do sistema carregado pelo agente. Técnica **few-shot**: 4 bulas reais com extrações corretas embutidas nas instruções.

**Regras obrigatórias que o prompt define:**
- Extrair só o que está explícito no texto
- `tipo` da interação deve ser exatamente `NOME_DIRETO`, `CLASSE` ou `ALIMENTO`
- Quando há mistura de nomes e classes numa frase → gerar registros separados
- `efeito` preenchido quando descrito na bula, `null` quando ausente
- Invocar a tool `consultar_secao_bula` quando o texto faz referência cruzada

**Exemplos embutidos:**
1. Azitromicina — interações mistas (NOME_DIRETO + CLASSE), sem referência cruzada
2. Amoxicilina — penicilínico simples
3. Amoxicilina + clavulanato — associação com interações com efeito descrito
4. Alendronato de sódio — interações com ALIMENTO, tool obrigatória (seção 6 referenciada)

---

## 8. `backend/utils/texto.py`

Função única de normalização de texto usada em todo o projeto:

```python
def normalizar(texto: str) -> str:
    """Minúsculas, sem acentos, sem espaços duplicados."""
    sem_acento = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return " ".join(sem_acento.lower().split())
```

Usado para: nomes de medicamentos na RENAME, nomes de fármacos nas listas A/B, e previsto para normalização nas métricas de validação.

---

## 9. `docker-compose.yml`

PostgreSQL 16-alpine na porta **5433** (não 5432, para não conflitar com instalações locais).

```bash
docker compose up -d      # sobe o banco em background
docker compose down       # para e remove containers (dados persistem no volume)
docker compose down -v    # para e remove containers E apaga o volume
```

Volume: `paje_pgdata` — persiste entre restarts.

---

## Pendências abertas

### Validação da extração (`validacao-extracao`)

Criar gabarito anotado manualmente para amostra de bulas e implementar métricas:
- **Similaridade:** Jaccard por palavra sobre campos normalizados
- **Score de interação:** `0,65 × J(referencia) + 0,35 × J(efeito)`
- **Métricas:** precisão, revocação, **F2** (penaliza revocação baixa 2×)
- **Metas mínimas:** revocação ≥ 0,90 e F2 ≥ 0,80 (CI e interações separados)
- **Limiares de match:** 0,45 para CI, 0,40 para interações

### Interface web (`interface-web`)

- Backend: FastAPI com endpoint de busca e cruzamento de medicamentos
- Frontend: SPA React + TypeScript com autocomplete para seleção múltipla
- Pasta `frontend/` existe mas está vazia

### Exposição e execução completa (`exposicao-pipeline`)

- Executar aquisição + extração sobre toda a RENAME
- Expor via ngrok ou cloudflared para apresentação da banca
