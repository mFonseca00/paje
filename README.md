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
| Validação quantitativa (Jaccard / F2) | ⬜ Não iniciado |
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
│   ├── utils/           # normalização de texto
│   └── scripts/         # scripts de execução e diagnóstico
├── docs/
│   ├── bulas/           # PDFs baixados da ANVISA
│   ├── markdown_bulas/  # markdowns gerados (bruto + seções)
│   └── medicamentos_referencia_anvisa/  # listas A e B da ANVISA
├── prompts/
│   ├── extracao_v1.md   # prompt few-shot do agente
│   └── exemplos/        # 4 bulas reais com extrações anotadas
├── frontend/            # SPA React (não iniciado)
├── docker-compose.yml   # PostgreSQL 16 na porta 5433
└── pyproject.toml
```
