# Pajé

Pipeline de TCC para extração automatizada de **contra-indicações e interações medicamentosas** de bulas da ANVISA, com foco nos medicamentos da RENAME (Relação Nacional de Medicamentos Essenciais).

## O que faz

1. **Aquisição** — busca bulas no bulário eletrônico da ANVISA e baixa os PDFs
2. **Preprocessamento** — converte PDFs para markdown e extrai as seções 3 e 4 (contra-indicações e interações)
3. **Extração LLM** — envia o texto ao modelo e persiste as entidades estruturadas no banco
4. **Interface web** _(não implementada)_ — SPA para o usuário cruzar medicamentos e ver interações

## Status atual

| Etapa | Situação |
|---|---|
| Aquisição (ANVISA API + download PDF) | ✅ Completo |
| Preprocessamento (PDF → markdown → seções) | ✅ Completo |
| Extração LLM com pydantic-ai | ✅ Completo |
| Banco de dados (PostgreSQL + Alembic) | ✅ Completo |
| Prompt few-shot v1 | ✅ Completo |
| Validação quantitativa (Jaccard / F2) | ✅ Completo |
| Interface web (React + FastAPI) | ⬜ Não iniciado |
| Execução sobre RENAME completa + exposição | ⬜ Não iniciado |

## Pré-requisitos

- Python 3.11+
- Docker (para o PostgreSQL)
- [Ollama](https://ollama.com) instalado e rodando (para extração local)

## Instalação

```bash
# 1. Clonar e criar ambiente virtual
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # Linux/macOS

# 2. Instalar dependências
pip install -e .

# 3. Subir o banco
docker compose up -d

# 4. Criar arquivo .env na raiz do projeto
# (copie o template .env.example e preencha )

## Migrações do banco

```bash
cd backend
alembic upgrade head
```

## Como executar

### Pipeline completa (aquisição + preprocessamento + extração)

```bash
python backend/scripts/executar_pipeline.py
python backend/scripts/executar_pipeline.py --limite 10          # apenas 10 medicamentos
python backend/scripts/executar_pipeline.py --reprocessar-erro   # inclui bulas com ERRO
```

### Etapas individuais

```bash
# Só aquisição
python backend/scripts/executar_aquisicao.py
python backend/scripts/executar_aquisicao.py --limite 5

# Só extração LLM
python backend/scripts/executar_extracao.py
python backend/scripts/executar_extracao.py --limite 5 --reprocessar-erro
```

### Validação quantitativa

Executa o pipeline sobre 10 bulas da RENAME, compara a extração com o gabarito anotado e gera métricas de precisão, revocação e F2.

```bash
python backend/scripts/executar_validacao.py
```

Saída no terminal:

```
Provider: gemini  |  Modelo: gemini-3.5-flash-lite
Prompt: v1

============================================================
Validação concluída — 10 bulas
============================================================

Contra-indicações:
  Precisão:  0.7586
  Revocação: 0.7213
  F2:        0.7285
  TP/FP/FN:  44/14/17
  Aprovado:  NÃO 

Interações medicamentosas:
  Precisão:  0.9486
  Revocação: 0.8877
  F2:        0.8992
  TP/FP/FN:  166/9/21
  Aprovado:  NÃO 

Aprovado geral: NÃO 
```

Os resultados detalhados por bula são gravados em `docs/validacao/resultados/{data}_{prompt_versao}_{modelo}/`.

#### Como funciona

**1. Gabarito**

`docs/validacao/referencia_validacao.xlsx` contém 10 bulas anotadas manualmente. Cada linha tem o nome do PDF e um JSON com as contra-indicações e interações esperadas, usando o **texto exato da bula** — sem reformulação. Frases que citam mais de uma CI (contraindicação) ou IM(interação medicamentosa) foram divididas em itens separados, pois isso é o comportamento esperado do pipeline.

**2. Extração**

Para cada PDF, o pipeline completo é executado (PDF → markdown → seções 3 e 4 → LLM). O resultado é uma lista de CIs e IMs extraídas pelo modelo.

**3. Comparação por similaridade (Jaccard)**

Como o LLM pode parafrasear o texto da bula, a comparação não exige correspondência exata. Usa-se o índice de Jaccard sobre conjuntos de palavras (após remoção de acentos e normalização para minúsculas):

```
J(A, B) = |A ∩ B| / |A ∪ B|
```

Cada item extraído é comparado com todos os itens do gabarito e emparelhado com o de maior score.

- **Score CI:** `J(descrição_extraída, descrição_gabarito)`
- **Score IM:** `0,65 × J(referência) + 0,35 × J(efeito)` — se efeito ausente em qualquer lado, usa só `J(referência)`

**4. Classificação TP / FP / FN**

| Caso | Classificação |
|---|---|
| Item do gabarito tem match com score ≥ limiar | TP (verdadeiro positivo) |
| Item do gabarito sem match acima do limiar | FN (falso negativo — pipeline não extraiu) |
| Item extraído sem correspondência no gabarito | FP (falso positivo — pipeline extraiu algo que não existe) |

Limiares: CI ≥ 0,45 · IM ≥ 0,40.

**5. Métricas**

TP/FP/FN são acumulados sobre todas as 10 bulas (micro-média) e então:

```
Precisão  = TP / (TP + FP)
Revocação = TP / (TP + FN)
F2        = 5 × (Precisão × Revocação) / (4 × Precisão + Revocação)
```

F2 pesa revocação duas vezes mais que precisão — perder uma CI real é pior do que um falso positivo. Critério de aprovação: **revocação ≥ 0,90** e **F2 ≥ 0,80**, avaliados separadamente para CI e IM.

#### Estrutura dos arquivos de validação

```
docs/validacao/
├── pdfs/                          # 10 PDFs de bulas para pacientes (ANVISA)
├── referencia_validacao.xlsx      # gabarito anotado (arquivo + json_esperado)
└── resultados/
    └── {data}_{versao}_{modelo}/
        ├── relatorio.json         # métricas agregadas (CI + IM)
        ├── paciente__alendronato_de_sodio.json
        ├── paciente__amoxicilina.json
        └── ...                    # um JSON por bula com matches TP/FP/FN
```

Cada JSON de bula lista todos os itens do gabarito e da extração com `classificacao` (TP/FP/FN) e `score`.

#### Schemas esperados no gabarito

```json
{
  "contraindicacoes": [
    { "id": 1, "descricao": "texto exato da bula" }
  ],
  "interacoes": [
    {
      "id": 1,
      "tipo": "NOME_DIRETO | CLASSE | ALIMENTO",
      "referencia": "nome do medicamento ou classe",
      "efeito": "descrição do efeito (opcional)"
    }
  ]
}
```

### Scripts de diagnóstico

```bash
python backend/scripts/testar_banco.py                                # testa conexão com DB
python backend/scripts/testar_busca.py <nome>                        # testa busca na ANVISA
python backend/scripts/testar_preprocessamento.py docs/bulas/<bula>.pdf
python backend/scripts/testar_extracao.py docs/bulas/<bula>.pdf
```

### Testes automatizados

```bash
pip install -e ".[dev]"
pytest
pytest --cov=backend
```

## Trocar o modelo LLM

No `.env`, ajuste `LLM_PROVIDER` e `LLM_MODEL`:

```env
# Ollama local
LLM_PROVIDER=ollama
LLM_MODEL=deepseek-r1:14b

# Anthropic
LLM_PROVIDER=anthropic
LLM_MODEL=claude-haiku-4-5-20251001
ANTHROPIC_API_KEY=sk-ant-...

# OpenAI
LLM_PROVIDER=openai
LLM_MODEL=gpt-4o-mini
OPENAI_API_KEY=sk-...

# Google Gemini
LLM_PROVIDER=gemini
LLM_MODEL=gemini-2.0-flash
GEMINI_API_KEY=...
```

## Estrutura de diretórios

```
paje/
├── backend/
│   ├── aquisicao/       # coleta de bulas da ANVISA
│   ├── preprocessamento/# PDF → markdown → seções relevantes
│   ├── extracao/        # agente LLM + pipeline em lote
│   ├── armazenamento/   # modelos SQLAlchemy + repositório + migrações
│   ├── validacao/       # comparador Jaccard, loader do gabarito, runner
│   ├── utils/           # normalização de texto
│   └── scripts/         # scripts de execução e diagnóstico
├── docs/
│   ├── bulas/           # PDFs baixados da ANVISA
│   ├── markdown_bulas/  # markdowns gerados (bruto + seções)
│   ├── validacao/       # gabarito XLSX, PDFs de teste e resultados
│   └── medicamentos_referencia_anvisa/  # listas A e B da ANVISA
├── prompts/
│   ├── extracao_v1.md   # prompt few-shot do agente
│   └── exemplos/        # 4 bulas reais com extrações anotadas
├── frontend/            # SPA React (não iniciado)
├── docker-compose.yml   # PostgreSQL 16 na porta 5433
└── pyproject.toml
```
