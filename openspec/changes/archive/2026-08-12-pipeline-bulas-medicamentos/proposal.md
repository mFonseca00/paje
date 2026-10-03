## Why

Profissionais de saúde e pacientes carecem de uma ferramenta confiável para consultar interações medicamentosas e contra-indicações de medicamentos da RENAME de forma estruturada e cruzada. O bulário eletrônico da ANVISA fornece as bulas em PDF, mas não oferece uma API para extração programática das informações clínicas relevantes. Este projeto automatiza a coleta, extração via LLM e armazenamento dessas informações, viabilizando consultas rápidas e cruzadas entre múltiplos medicamentos.

## What Changes

- **Nova capacidade** de aquisição automatizada de bulas PDF a partir do bulário eletrônico da ANVISA via endpoints identificados, com base na lista de medicamentos da RENAME
- **Nova capacidade** de pré-processamento e parsing de PDFs de bulas para extração estruturada de texto (seções de contra-indicações e interações medicamentosas)
- **Nova capacidade** de extração de dados clínicos via LLM (few-shot prompting) com saída normalizada em JSON e armazenamento em PostgreSQL
- **Nova capacidade** de validação automatizada das extrações por comparação com gabarito manual usando F2-score e índice de Jaccard
- **Nova capacidade** de interface web responsiva para consulta cruzada de interações e contra-indicações entre múltiplos medicamentos

## Capabilities

### New Capabilities

- `aquisicao-bulas`: Coleta automatizada de PDFs de bulas do bulário ANVISA para medicamentos da RENAME, incluindo resolução de CAPTCHA e controle de fluxo por fila
- `preprocessamento-pdf`: Conversão e estruturação de PDFs de bulas em representação textual segmentada por seções (contra-indicações e interações medicamentosas)
- `extracao-llm`: Pipeline de extração de dados clínicos das bulas via LLM com few-shot prompting, saída em JSON e suporte a modelos locais (Ollama) e APIs externas
- `armazenamento-dados`: Esquema PostgreSQL para persistência de medicamentos, bulas, contra-indicações e interações medicamentosas com controle de estado de processamento
- `validacao-extracao`: Módulo de avaliação da qualidade da extração por comparação com gabarito anotado manualmente, usando Jaccard, F2-score e micro-média
- `interface-consulta`: Interface web responsiva para seleção de múltiplos medicamentos e visualização cruzada de interações e contra-indicações

### Modified Capabilities

*(Projeto novo — nenhuma capability existente modificada)*

## Impact

- **Dependências externas**: bulário eletrônico da ANVISA (endpoints HTTP), lista RENAME, PostgreSQL, Python com Pydantic AI, Ollama (execução local de LLM)
- **Armazenamento**: banco de dados PostgreSQL local; PDFs de bulas armazenados em disco com referência no banco
- **APIs consumidas**: `GET /api/consulta/bulario` e `GET /api/consulta/medicamentos/arquivo/bula/parecer/{id}/` da ANVISA (autenticação via token Guest)
- **Interface exposta**: aplicação web (a definir tecnologia) acessível na rede local e opcionalmente via exposição externa (ngrok, VPN, proxy reverso)
- **Risco de captcha**: a ANVISA pode exigir CAPTCHA nas requisições; será necessário investigar e mitigar (delays, rotação de headers, ou solução manual)
