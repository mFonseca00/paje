## ADDED Requirements

### Requirement: Preferência por resultado de princípio ativo único na seleção de bula

Quando a busca ao endpoint ANVISA retornar múltiplos resultados e o nome buscado **não** contiver "+", o sistema SHALL preferir resultados cujo `nome_produto` também não contenha "+", descartando combinações de princípios ativos da seleção primária.

Quando o nome buscado **contiver** "+", o sistema SHALL selecionar o resultado normalmente entre todos os retornados, sem filtro adicional.

Se, após aplicar o filtro, nenhum candidato restar (i.e., todos os resultados contêm "+"), o sistema SHALL usar os resultados originais como fallback, garantindo que alguma bula seja baixada.

#### Scenario: Busca de princípio ativo único retorna combinações e simples

- **WHEN** o sistema busca "amoxicilina" (sem "+") e a lista de resultados inclui "amoxicilina + clavulanato de potássio" e "amoxicilina"
- **THEN** o sistema seleciona "amoxicilina" e ignora "amoxicilina + clavulanato de potássio" na escolha do resultado principal

#### Scenario: Busca de princípio ativo único retorna apenas combinações

- **WHEN** o sistema busca um nome sem "+" e todos os resultados retornados contêm "+" em `nome_produto`
- **THEN** o sistema usa os resultados originais (incluindo combinações) como fallback e seleciona o primeiro disponível com ID de bula válido

#### Scenario: Busca de combinação não sofre filtro

- **WHEN** o sistema busca "amoxicilina + clavulanato de potassio" (com "+")
- **THEN** o sistema não aplica filtro de exclusão e seleciona normalmente entre todos os resultados retornados
