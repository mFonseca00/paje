# Validação da Extração

## Problema

Após a extração LLM das entidades clínicas, é necessário medir objetivamente a qualidade dos resultados para decidir se o prompt está pronto para o conjunto completo ou precisa de iterações.

## Solução Proposta

Criar um gabarito anotado manualmente em planilha XLSX e um script standalone de validação que reutiliza as funções internas do pipeline de extração (mesmo prompt, mesmo pré-processamento). Os PDFs usados na validação ficam em pasta isolada (`docs/validacao/pdfs/`), garantindo que o arquivo analisado manualmente é exatamente o mesmo processado pelo extrator. Cada execução grava seus resultados em uma pasta versionada (`docs/validacao/resultados/{data}_{prompt}_{modelo}/`), com um JSON por bula e um `relatorio.json` com as métricas agregadas. Métricas de precisão, revocação e F2 baseadas em similaridade de Jaccard indicam aprovação ou reprovação por meta (revocação ≥ 0,90 e F2 ≥ 0,80). Se reprovado, o ciclo retorna à fase de extração para refinamento do prompt.

## Motivação

Sem validação quantitativa, não é possível afirmar com rigor acadêmico que a extração é satisfatória — o que é central para o TCC. O reaproveitamento das funções internas garante que qualquer melhoria no prompt ou no pré-processamento seja imediatamente mensurável sem configuração adicional.
