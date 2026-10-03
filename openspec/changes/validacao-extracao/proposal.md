# Validação da Extração

## Problema

Após a extração LLM das entidades clínicas, é necessário medir objetivamente a qualidade dos resultados para decidir se o prompt está pronto para o conjunto completo ou precisa de iterações.

## Solução Proposta

Criar um gabarito anotado manualmente para uma amostra de bulas e implementar métricas de precisão, revocação e F2 baseadas em similaridade de Jaccard (por palavra). O relatório indica aprovação ou reprovação por meta (revocação ≥ 0,90 e F2 ≥ 0,80). Se reprovado, o ciclo retorna à fase de extração para refinamento do prompt.

## Motivação

Sem validação quantitativa, não é possível afirmar com rigor acadêmico que a extração é satisfatória — o que é central para o TCC.
