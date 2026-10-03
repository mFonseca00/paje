## Purpose

Define a interface web responsiva para consulta cruzada de interações medicamentosas e contra-indicações entre múltiplos medicamentos selecionados pelo usuário, com apresentação clara da origem de cada informação e distinção entre interações por nome direto e por classe farmacológica. Implementada como SPA em React + TypeScript com estilização em arquivos CSS separados e design minimalista em azul e branco.

## ADDED Requirements

### Requirement: Seleção de múltiplos medicamentos

O sistema SHALL permitir que o usuário selecione um conjunto de medicamentos pelo nome para consulta cruzada.

#### Scenario: Usuário seleciona dois ou mais medicamentos
- **WHEN** o usuário informa dois ou mais nomes de medicamentos
- **THEN** o sistema aceita a seleção e procede para o cruzamento

#### Scenario: Usuário seleciona apenas um medicamento
- **WHEN** o usuário informa apenas um medicamento
- **THEN** o sistema exibe as contra-indicações e interações conhecidas para aquele medicamento individualmente, ou uma mensagem indicando a necessidade de ao menos dois medicamentos para cruzamento entre pares

### Requirement: Cruzamento de combinações par a par

O sistema SHALL calcular todas as combinações possíveis entre os medicamentos selecionados e apresentar, para cada par, as interações medicamentosas e contra-indicações identificadas.

#### Scenario: Combinações com ocorrências exibidas
- **WHEN** o sistema encontra interações ou contra-indicações para um par de medicamentos
- **THEN** o resultado é exibido agrupado por par, com as informações identificadas

#### Scenario: Combinação sem ocorrências omitida
- **WHEN** nenhuma interação ou contra-indicação é encontrada para um par
- **THEN** o par é omitido dos resultados sem exibição de mensagem de erro

### Requirement: Exibição destacada de interações por nome direto

O sistema SHALL exibir interações do tipo `NOME_DIRETO` de forma destacada, indicando explicitamente que há uma interação documentada entre os medicamentos envolvidos.

#### Scenario: Interação direta encontrada no par
- **WHEN** a bula de um medicamento do par lista o outro pelo nome como substância de interação
- **THEN** a interação é exibida com destaque visual diferenciado (ex: ícone de alerta, cor de ênfase) e o efeito é apresentado se disponível

### Requirement: Exibição diferenciada de interações por classe farmacológica

O sistema SHALL exibir interações do tipo `CLASSE` de forma visualmente distinta das interações diretas, comunicando que a bula menciona uma categoria farmacológica e não um medicamento específico, e recomendando consulta a um profissional de saúde.

#### Scenario: Interação por classe exibida como alerta genérico
- **WHEN** a bula de um medicamento menciona uma classe farmacológica como interação
- **THEN** a interação é listada com indicação visual de que é uma referência a categoria farmacológica, exibindo a classe mencionada (`referencia`) e uma mensagem recomendando consulta a um profissional de saúde; o sistema não verifica se algum medicamento selecionado pertence à classe

### Requirement: Exibição de interações com alimentos

O sistema SHALL exibir interações do tipo `ALIMENTO` com a mesma lógica de alerta genérico das interações por classe farmacológica, comunicando que a bula menciona restrição ou precaução relacionada a alimento ou bebida e orientando o paciente a evitar o(s) item(ns) mencionado(s).

#### Scenario: Interação com alimento exibida
- **WHEN** a bula de um medicamento menciona um alimento ou bebida como fonte de interação (ex: café, suco, água mineral)
- **THEN** a interação é listada com indicação visual similar à de interação por classe, exibindo o alimento ou bebida (`referencia`), o efeito quando disponível (`efeito`) e uma orientação para o paciente evitar aquele(s) alimento(s); o sistema não verifica disponibilidade ou contexto do alimento

### Requirement: Indicação da bula de origem

O sistema SHALL exibir, para cada resultado de interação ou contra-indicação, a referência à bula de origem da informação.

#### Scenario: Resultado exibido com bula de origem
- **WHEN** o sistema exibe uma interação ou contra-indicação
- **THEN** a bula de origem (nome do medicamento e/ou número da bula) está visível junto ao resultado

### Requirement: Interface responsiva com design minimalista

O sistema SHALL ser responsivo, funcionando adequadamente tanto em telas de dispositivos móveis (smartphones) quanto em telas de computadores desktop, com design minimalista usando paleta azul e branca.

#### Scenario: Acesso em smartphone
- **WHEN** o usuário acessa a interface em um dispositivo móvel com tela pequena
- **THEN** a interface adapta o layout para a tela, mantendo usabilidade sem rolagem horizontal

#### Scenario: Acesso em desktop
- **WHEN** o usuário acessa a interface em um computador com tela larga
- **THEN** a interface utiliza o espaço disponível de forma adequada

### Requirement: Organização em componentes React com TypeScript

O sistema SHALL organizar a interface em componentes React com TypeScript, com estilização em arquivos CSS separados por componente.

#### Scenario: Componentes independentes e tipados
- **WHEN** a interface é renderizada
- **THEN** cada parte da UI (seleção de medicamentos, card de resultado, referência de bula) corresponde a um componente React separado com props tipadas via TypeScript

### Requirement: Acesso externo à máquina de execução

O sistema SHALL ser acessível a partir de dispositivos fora da máquina onde está sendo executado, mediante configuração de exposição de rede (por exemplo, via proxy reverso, VPN ou túnel).

#### Scenario: Acesso externo configurado
- **WHEN** a configuração de exposição externa está ativa
- **THEN** a interface é acessível por dispositivos na mesma rede ou via internet, conforme a estratégia configurada

#### Scenario: Acesso apenas local (padrão)
- **WHEN** nenhuma configuração de exposição externa está ativa
- **THEN** a interface é acessível apenas na máquina local (localhost)
