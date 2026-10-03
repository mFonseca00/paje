# Benchmark de modelos Ollama para extração clínica

Este documento descreve os modelos candidatos e o passo a passo para benchmark manual da etapa de extração LLM.

## Modelos candidatos

| Modelo | Tamanho | Ponto forte | Observação |
|---|---|---|---|
| `llama3.2` | 3B | Velocidade | Baseline rápido; qualidade inferior em tarefas estruturadas |
| `llama3.1:8b` | 8B | Equilíbrio qualidade/custo | Boa seguimento de instruções |
| `mistral:7b` | 7B | Instruções estruturadas | Forte em JSON; testado amplamente |
| `qwen2.5:7b` | 7B | Português/multilíngue | Bom desempenho em textos médicos em português |
| `qwen2.5:14b` | 14B | Qualidade | Melhor qualidade; mais lento |
| `deepseek-r1:14b` | 14B | Raciocínio | Modelo padrão configurado no `.env` |
| `phi4:14b` | 14B | Instruções complexas | Boa aderência a schemas JSON |

## Pré-requisitos

1. Ollama instalado e rodando: `ollama serve`
2. Modelos baixados: `ollama pull <modelo>`
3. Pelo menos uma bula com markdown gerado em `docs/markdown_bulas/`
4. Dependências do projeto instaladas: `pip install -e .`

## Passo a passo para benchmark manual

### 1. Escolher bulas de referência

Selecione 3–5 bulas representativas, preferencialmente com:
- Interações mistas (NOME_DIRETO + CLASSE + ALIMENTO)
- Referências cruzadas a outras seções
- Contra-indicações variadas

Certifique-se de que os arquivos `__secoes.md` e `__bruto.md` existam em `docs/markdown_bulas/`. Se não existirem, gere-os:

```bash
python backend/scripts/testar_preprocessamento.py docs/bulas/<nome>.pdf
```

### 2. Executar extração com cada modelo

Para cada modelo candidato, execute o script de teste passando a variável de ambiente `LLM_MODEL`:

```bash
# Windows (PowerShell)
$env:LLM_MODEL = "mistral:7b"; python backend/scripts/testar_extracao.py `
    docs/bulas/paciente__dipirona__abc12345.pdf `
    --saida output/benchmark/mistral_7b

$env:LLM_MODEL = "qwen2.5:7b"; python backend/scripts/testar_extracao.py `
    docs/bulas/paciente__dipirona__abc12345.pdf `
    --saida output/benchmark/qwen25_7b

$env:LLM_MODEL = "deepseek-r1:14b"; python backend/scripts/testar_extracao.py `
    docs/bulas/paciente__dipirona__abc12345.pdf `
    --saida output/benchmark/deepseek_r1_14b
```

```bash
# Linux/macOS
LLM_MODEL=mistral:7b python backend/scripts/testar_extracao.py \
    docs/bulas/paciente__dipirona__abc12345.pdf \
    --saida output/benchmark/mistral_7b
```

Repita para todas as bulas de referência.

### 3. Comparar os JSONs gerados

Cada execução salva um arquivo `<nome_bula>_extracao.json` no diretório de saída. Compare visualmente:

```bash
# Ver o JSON formatado de um modelo
cat output/benchmark/mistral_7b/paciente__dipirona__abc12345_extracao.json

# Comparar dois modelos lado a lado (Unix)
diff <(cat output/benchmark/mistral_7b/*.json) \
     <(cat output/benchmark/qwen25_7b/*.json)
```

### 4. Critérios de avaliação

Para cada bula, avalie manualmente:

| Critério | O que verificar |
|---|---|
| **Completude** | Todas as contra-indicações relevantes foram extraídas? |
| **Tipagem correta** | NOME_DIRETO / CLASSE / ALIMENTO classificados corretamente? |
| **Ausência de alucinação** | O modelo inventou informações não presentes na bula? |
| **Uso da tool** | O modelo invocou `consultar_secao_bula` quando havia referência cruzada? |
| **Campo `efeito`** | Preenchido quando presente na bula; `null` quando ausente? |
| **Formato JSON** | JSON válido e aderente ao schema? |

### 5. Registrar resultados

Crie uma tabela comparativa simples:

```
Bula: paciente__dipirona

| Critério          | mistral:7b | qwen2.5:7b | deepseek-r1:14b |
|-------------------|------------|------------|-----------------|
| Completude (CI)   | 3/4        | 4/4        | 4/4             |
| Tipagem correta   | sim        | sim        | sim             |
| Alucinações       | 1          | 0          | 0               |
| Uso da tool       | não        | sim        | sim             |
| Tempo (aprox.)    | 8s         | 15s        | 45s             |
```

### 6. Selecionar o modelo

Escolha o modelo que melhor equilibra qualidade e velocidade para o contexto do TCC. Atualize o `.env`:

```
LLM_MODEL=<modelo-escolhido>
```

## Notas

- O campo `resposta_bruta_modelo` preserva a saída JSON do modelo no banco para auditoria.
- Bulas marcadas como `ERRO` (JSON inválido) podem ser reprocessadas após ajuste de prompt.
- Para benchmark com APIs externas (Anthropic/OpenAI/Gemini), defina `LLM_PROVIDER` e a chave correspondente no `.env` antes de rodar `testar_extracao.py`.
