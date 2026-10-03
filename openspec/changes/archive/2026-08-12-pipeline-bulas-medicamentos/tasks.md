<!-- INSTRUÇÕES DE APPLY: implemente uma fase por vez. Pare ao final de cada fase
     e aguarde validação manual antes de iniciar a próxima. -->

## Fase 1 — Infraestrutura Base
<!-- PAUSA após esta fase: verificar tabelas no banco, executar script CLI de smoke-test do DAL -->

- [x] 1.1 Criar estrutura de diretórios do projeto Python (`backend/` com módulos: `aquisicao`, `preprocessamento`, `extracao`, `armazenamento`, `validacao`; `frontend/` para React; `docs/` já existente com RENAME e pasta `bulas/`)
- [x] 1.2 Configurar ambiente virtual Python e `pyproject.toml` com dependências iniciais (pydantic-ai, psycopg2-binary, httpx, python-dotenv, alembic, pytest)
- [x] 1.3 Criar `.env` com variáveis: credenciais do banco, URL base da ANVISA, modelo LLM, path do diretório de bulas (`docs/bulas/`)
- [x] 1.4 Criar `.env.example` documentando todas as variáveis sem valores sensíveis
- [x] 1.5 Criar `.gitignore` cobrindo: `.env`, `docs/bulas/`, `__pycache__`, `.venv`, `node_modules`, arquivos de build do frontend
- [x] 1.6 Criar módulo de settings (`config.py`) com classe Pydantic que carrega o `.env`
- [x] 1.7 Configurar PostgreSQL (local ou Docker) e verificar conectividade a partir da aplicação
- [x] 1.8 Criar migrations Alembic para as tabelas `medicamentos`, `bulas`, `contraindicacoes` e `interacoes_medicamentosas`
- [x] 1.9 Criar módulo DAL (`armazenamento/repositorio.py`) com funções CRUD para cada tabela
- [x] 1.10 Criar script CLI `scripts/testar_banco.py` que insere e consulta um registro em cada tabela — permite validação manual da Fase 1
- [x] 1.11 Criar testes unitários para o DAL (`tests/test_repositorio.py`) usando banco de teste isolado
- [x] 1.12 Instalar Ollama e testar inferência manual com um modelo candidato (`llama3.2` ou `phi3`) — avaliar Docker vs instalação direta e registrar decisão (resolve OQ3)

## Fase 2 — Aquisição de Bulas
<!-- PAUSA após esta fase: inspecionar PDFs em docs/bulas/, conferir registros no banco com status PENDENTE e revisar logs do CLI -->

- [x] 2.1 Implementar loader da lista RENAME a partir do arquivo em `docs/` (normalizar nomes para uso no filtro da API)
- [x] 2.2 Implementar cliente HTTP para o endpoint de busca (`GET /api/consulta/bulario`) com headers necessários e delay configurável entre requisições
- [x] 2.3 Criar script CLI `scripts/testar_busca.py` que busca 3 medicamentos e exibe a resposta — permite validar o endpoint antes de implementar o fluxo completo (resolve OQ4 parcialmente)
- [ ] 2.4 Documentar se CAPTCHA ocorre ou não com base no teste acima — **PENDENTE: executar `python backend/scripts/testar_busca.py` e registrar aqui o resultado**
- [x] 2.5 Implementar detecção de CAPTCHA/bloqueio (status 403/429) com pausa e log de notificação
- [x] 2.6 Implementar cliente HTTP para download de PDF (`GET /api/consulta/medicamentos/arquivo/bula/parecer/{id}/`)
- [x] 2.7 Implementar verificação de duplicata antes do download (consulta ao banco por `id_bula_anvisa`)
- [x] 2.8 Implementar salvamento do PDF em `docs/bulas/` com nome identificável e registro no banco com status `PENDENTE`
- [x] 2.9 Implementar log estruturado por etapa (busca, download, skip, erro) para cada medicamento processado
- [x] 2.10 Implementar fluxo completo de aquisição: iterar lista RENAME → buscar → baixar → registrar
- [x] 2.11 Criar script CLI `scripts/executar_aquisicao.py` que roda o fluxo completo (ou parcial com flag `--limite N`)
- [x] 2.12 Criar testes unitários para o módulo de aquisição (`tests/test_aquisicao.py`) com mock do cliente HTTP
- [x] 2.13 Implementar remoção do PDF anterior de `docs/bulas/` quando um novo PDF for baixado para o mesmo medicamento (não ao processar — apenas ao substituir)
- [x] 2.14 Implementar reprocessamento de bulas com status `ERRO` (reuso do PDF existente em disco)
- [x] 2.15 Implementar loader das listas de referência A e B (`docs/medicamentos_referencia_anvisa/lista_referencia_a_11-08-2026.xlsx` e `lista_referencia_b_11-08-2026.xlsx`): ler col A (`FÁRMACO`/`ASSOCIAÇÃO`) e col C (`MEDICAMENTO`), cabeçalho na linha 3, dados a partir da linha 4; retornar dicionário `{fármaco_normalizado: [nome_comercial, ...]}` consolidando as duas listas; paths configuráveis via `.env` (`REFERENCIA_LISTA_A_PATH`, `REFERENCIA_LISTA_B_PATH`)
- [x] 2.16 Implementar fallback por nome comercial no fluxo de aquisição: quando `buscar_bulas(nome_dcb)` retornar lista vazia, consultar o dicionário da tarefa 2.15 pelo DCB normalizado; para cada nome comercial encontrado, tentar `buscar_bulas(nome_comercial)` com delay entre tentativas; usar o primeiro resultado não-vazio; registrar no log qual estratégia foi usada (DCB direto ou fallback + qual nome comercial)
- [x] 2.17 Atualizar `tests/test_aquisicao.py` para cobrir o fallback: DCB não encontrado → nome comercial localizado e usado com sucesso; DCB não encontrado e sem correspondência nas listas (continua como `NAO_ENCONTRADO`); múltiplos nomes comerciais na lista (usar o primeiro que retornar resultado)
- [x] 2.18 Adicionar coluna `nome_dcb` (`VARCHAR(500), nullable=True`) à tabela `medicamentos` para armazenar o nome original da lista RENAME independentemente do nome usado na busca; gerar e aplicar migration Alembic
- [x] 2.19 Atualizar o fluxo de aquisição (`fluxo.py`) para passar `nome_dcb` ao criar ou recuperar o registro em `medicamentos`: quando a bula for encontrada pelo DCB, `nome_dcb = nome` e `nome_comercial = nome`; quando encontrada via fallback, `nome_dcb = nome_original_rename` e `nome_comercial = nome_usado_no_fallback`; quando o medicamento já existir no banco e `nome_dcb` estiver vazio, preencher retroativamente
- [x] 2.20 Atualizar `repositorio.py`: função `criar_medicamento` aceita parâmetro opcional `nome_dcb`; função `buscar_medicamento_por_nome` passa a buscar tanto por `nome_comercial` quanto por `nome_dcb` para evitar duplicatas
- [x] 2.21 Atualizar `tests/test_aquisicao.py` e `tests/test_repositorio.py` para cobrir o novo campo: criação com e sem `nome_dcb`; fluxo com fallback registra ambos os nomes corretamente

## Fase 3 — Pré-processamento de PDF
<!-- PAUSA após esta fase: inspecionar manualmente a saída markdown de 5 bulas — confirmar se as seções corretas foram extraídas antes de avançar -->

- [x] 3.1 Instalar pymupdf4llm e criar script CLI `scripts/testar_preprocessamento.py` que converte um PDF e salva o markdown em disco — permite inspeção manual imediata
- [x] 3.2 Implementar conversor PDF → markdown via pymupdf4llm no módulo `preprocessamento` (entrega o markdown completo com estrutura de seções preservada, sem filtragem)
- [x] 3.3 Implementar identificação e extração das seções de contra-indicações e interações medicamentosas do markdown produzido (chunkless — retorna o texto íntegro dessas seções); quando nenhuma seção for identificada, retorna o markdown bruto completo
- [x] 3.4 Implementar log por bula: seções encontradas e volume de texto extraído; quando nenhuma seção identificada, registrar que o markdown bruto foi encaminhado
- [x] 3.5 Criar testes unitários para o módulo de pré-processamento (`tests/test_preprocessamento.py`) com fixtures de markdown sintético
- [x] 3.6 Revisar extrator para formato **bula paciente**: inspeção de 12 bulas confirmou que as seções 3 (`QUANDO NÃO DEVO USAR?`) e 4 (`O QUE DEVO SABER ANTES?`) são invariáveis e devem ser capturadas por inteiro; o nível markdown do heading varia por documento (`#` a `######`); extrair pelo número da seção — localizar headings cujo texto (após remover `**` e `<mark>`) começa com `3.` ou `4.` e coletar todo o conteúdo até o próximo heading numerado (`5.`), capturando automaticamente subseções não-numeradas (como `Interações medicamentosas`); identificar "heading numerado" por busca de string simples, sem regex; atualizar testes unitários para cobrir o agrupamento e a variação de nível markdown
- [x] 3.7 Normalizar níveis de heading no texto extraído antes de entregá-lo ao LLM: varredura linha a linha sobre o resultado das seções 3 e 4; headings cujo texto começa com `dígito + ponto` recebem nível `##`; demais headings recebem nível `###`; implementado sem biblioteca adicional (~10 linhas); atualizar testes unitários para cobrir a normalização
