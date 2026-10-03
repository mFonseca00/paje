## Context

O sistema é um projeto de TCC com escopo de prova de conceito, executado em uma única máquina (possivelmente um notebook ou desktop pessoal). Não há requisitos de escalabilidade horizontal, SLA ou multiusuário. A ANVISA não oferece API pública documentada para download de bulas — os endpoints são obtidos por engenharia reversa do bulário eletrônico. O volume de bulas a processar é limitado ao escopo da RENAME (centenas de medicamentos, não milhares). Ver `proposal.md` para motivação.

## Goals / Non-Goals

**Goals:**
- Definir a arquitetura de módulos e o fluxo de dados entre as etapas da pipeline
- Estabelecer decisões de tecnologia com base nos critérios do projeto (execução local, custo zero ou baixo, suporte a JSON estruturado)
- Documentar os pontos de investigação em aberto que serão resolvidos durante o desenvolvimento
- Definir a estratégia de exposição da aplicação para acesso externo

**Non-Goals:**
- Escalabilidade horizontal ou multi-tenant
- Alta disponibilidade ou failover automático
- Otimização de throughput para grandes volumes (> 1.000 bulas/dia)
- Interface administrativa de monitoramento em tempo real

## Decisions

### D1 — Linguagem e framework base: Python com Pydantic AI

**Decisão**: Python como linguagem principal; Pydantic AI como framework de agente LLM.

**Rationale**: Pydantic AI suporta múltiplos providers de modelo (local e remoto) com uma interface unificada, tem suporte nativo a saída estruturada com validação via Pydantic models, e é alinhado ao ecossistema Python de ML/NLP. Alternativas como LangChain foram descartadas pela complexidade adicional desnecessária para um agente single-step.

---

### D2 — Modelo LLM: Ollama local como primeira opção, API externa como fallback

**Decisão**: A pipeline será construída para rodar primeiro com um modelo local via Ollama. O modelo específico (candidatos: `llama3`, `mistral`, `phi3`, `gemma2`) será definido por testes empíricos durante o desenvolvimento, priorizando: janela de contexto ≥ 8k tokens, suporte a saída JSON estruturada e qualidade de extração aceitável.

**Rationale**: Execução local elimina custo de API e dependência de conexão. O suporte a Docker para Ollama será avaliado — se o overhead for aceitável na máquina de desenvolvimento, facilita portabilidade; caso contrário, Ollama será instalado diretamente no host.

**Alternativas consideradas**: GPT-4o mini (custo por token, boa qualidade), Claude Haiku (custo por token), Gemini Flash (tier gratuito com limites). Serão testados se o modelo local não atingir as metas de F2 ≥ 0,80.

---

### D3 — Pré-processamento: extração estrutural de seções via pymupdf4llm (chunkless)

**Decisão**: pymupdf4llm converte o PDF da bula em markdown. O módulo de pré-processamento então identifica as seções de contra-indicações e interações medicamentosas nesse markdown e passa o conteúdo íntegro ao LLM — sem chunking, sem retrieval, sem embeddings (abordagem "chunkless"). Se nenhuma seção relevante for identificada, o markdown bruto completo é encaminhado ao LLM com registro em log.

**Hierarquia plana e inferência por conteúdo**: pymupdf4llm não preserva hierarquia via nível markdown — o nível varia por documento (`#` a `######`) sem relação com a estrutura real. A hierarquia é inferida pelo conteúdo: headings cujo texto normalizado (sem `**` e `<mark>`) começa com `dígito + ponto` são seções numeradas principais; demais são subseções da numerada anterior.

**Formato bula paciente** (adotado como padrão inicial): inspeção de 12 bulas confirmou que as seções-alvo são **invariavelmente a 3 e a 4** do template ANVISA. A extração localiza headings cujo texto começa com `3.` ou `4.` e coleta tudo até o próximo heading numerado com número maior — capturando automaticamente subseções como `Interações medicamentosas`. Identificação por número de seção é mais robusta que matching por título, pois o título pode ter sufixos variáveis entre fabricantes. Busca por string é preferida sobre regex.

A estratégia semântica via embeddings foi descartada para não aumentar a complexidade do sistema desnecessariamente. A segmentação por tamanho (size-based) também foi descartada por não oferecer controle adequado sobre qual segmento é relevante. A decisão de adotar uma abordagem diferente caso a estrutural se mostre insuficiente parte do usuário após validação empírica.

**Rationale**: A maioria das bulas da ANVISA segue um template padronizado com seções nomeadas e numeradas, tornando a extração estrutural direta eficaz. Se funcionar, é a solução mais simples possível. Quando a estrutura não é reconhecida, o texto bruto preserva ao menos o conteúdo textual para o LLM.

---

### D4 — Ferramenta de conversão de PDF: pymupdf4llm

**Decisão**: pymupdf4llm converte PDF → markdown estruturado usando pymupdf como base, mas com lógica dedicada de detecção de títulos por tamanho e estilo de fonte — produzindo headings markdown reais sem modelos de ML nem compilador C++. Se a qualidade de extração for insuficiente para bulas específicas (ex: PDFs escaneados), OCR (`pytesseract` + `pdf2image`) será avaliado como alternativa — a decisão parte do usuário após inspeção manual dos resultados.

**Rationale**: As bulas da ANVISA são PDFs digitais com texto embutido. Docling foi descartado por exigir compilador C++ no Windows. pymupdf puro foi descartado porque a heurística manual de detecção de títulos produziu falsos positivos. MarkItDown foi descartado porque usa pdfminer internamente e não produz headings markdown para PDFs. pymupdf4llm é desenvolvido pela equipe do pymupdf especificamente para produzir markdown adequado para LLMs, detecta headings via análise de fonte e funciona com `pip install pymupdf4llm`.

---

### D5 — Embeddings: descartados

**Decisão**: Embeddings não serão implementados. A abordagem chunkless com extração estrutural de seções elimina a necessidade de retrieval semântico. Caso a estratégia estrutural se mostre insuficiente, a decisão de introduzir embeddings parte do usuário.

---

### D6 — Banco de dados: PostgreSQL com JSONB

**Decisão**: PostgreSQL instalado localmente (ou via Docker). Schema com quatro tabelas principais: `medicamentos`, `bulas`, `contraindicacoes`, `interacoes_medicamentosas`. A coluna JSONB em `bulas` armazena a resposta completa do modelo para auditoria.

**Rationale**: PostgreSQL é o único banco relacional maduro com suporte nativo a JSONB, permitindo tanto queries relacionais quanto consultas diretas ao JSON bruto do modelo. Alternativas como SQLite não oferecem JSONB e são menos adequadas para queries relacionais complexas (cruzamento de medicamentos).

---

### D7 — Interface web: React + TypeScript (SPA) com backend FastAPI

**Decisão**: Frontend em React com TypeScript, organizado em componentes com estilização em arquivos CSS separados. Design minimalista com paleta azul e branca. Backend em FastAPI (Python), servindo uma API REST consumida pelo frontend. Uma única página na versão inicial.

**Rationale**: React + TypeScript garante componentes bem delimitados e tipagem que facilita manutenção. A separação frontend/backend via API é mais limpa para um projeto de TCC que pode evoluir. A proposta visual concreta (azul/branca, minimalista) será feita na Fase 6 para aprovação do usuário antes da implementação.

---

### D8 — Exposição externa: proxy reverso ou túnel como estratégia

**Decisão**: Para acesso fora da máquina local, a aplicação será exposta via uma das seguintes estratégias (em ordem de preferência): (1) ngrok ou cloudflared para exposição temporária via túnel, (2) configuração de port forwarding no roteador + IP fixo/DDNS, (3) deploy em VPS mínima se necessário para avaliação do TCC.

**Rationale**: ngrok/cloudflared são zero-config e adequados para demonstrações e avaliações pontuais. Não há requisito de alta disponibilidade contínua.

---

### D9 — Controle de CAPTCHA na aquisição ANVISA

**Decisão**: A pipeline incluirá delays configuráveis entre requisições e rotação de headers para reduzir a probabilidade de bloqueio. Se CAPTCHA for detectado, a pipeline pausará e notificará o operador. Não será implementada solução automática de CAPTCHA (ethical boundary).

**Rationale**: A ANVISA é um serviço público e a coleta é para fins acadêmicos. Respeitar rate limits e não automatizar bypass de CAPTCHA é o posicionamento ético adequado.

## Risks / Trade-offs

- **[Risco] Instabilidade dos endpoints da ANVISA** → Os endpoints são obtidos por engenharia reversa e podem mudar sem aviso. Mitigação: abstrair as URLs em configuração e documentar como redescobri-las usando o repositório `bulario-api` como referência.

- **[Risco] Qualidade do modelo local insuficiente** → O modelo Ollama pode não atingir F2 ≥ 0,80 nas metas de validação. Mitigação: a pipeline suporta troca para API externa (Claude Haiku, GPT-4o mini) sem mudança de arquitetura.

- **[Risco] PDFs de bulas com baixa qualidade de texto (escaneados)** → Docling falha em PDFs baseados em imagem. Mitigação: o fallback OCR será avaliado pelo usuário após inspeção dos resultados do Docling.

- **[Trade-off] Sem exclusividade na correspondência do gabarito** → Uma entidade do gabarito pode ser capturada por múltiplas entidades extraídas, inflando a revocação. Decisão do planejamento original — manter para consistência com a métrica definida.

## Open Questions

- **OQ1**: O Docling consegue extrair estrutura de seções de forma confiável nas bulas da ANVISA em PDF? Resposta depende de inspeção manual dos resultados pelo usuário (Fase 3). Quando a estrutura não é reconhecida, o markdown bruto é encaminhado ao LLM.

- **OQ2**: Qual modelo Ollama oferece melhor relação qualidade/velocidade para extração de JSON de bulas em português? Definir por benchmarks durante o desenvolvimento; a decisão final parte do usuário com base nas métricas de F2.

- **OQ3**: O Ollama via Docker tem overhead aceitável na máquina de desenvolvimento? Testar no início da implementação; se não, instalar diretamente no host.

- **OQ4**: A ANVISA apresenta CAPTCHA regularmente nas requisições automatizadas? Responder com um teste de coleta controlado (pequena amostra, com delays) no início da Fase 2.
