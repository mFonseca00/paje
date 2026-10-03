## Purpose

Define os requisitos de exposição externa do sistema e de execução da pipeline completa sobre o conjunto total da RENAME, encerrando o ciclo de desenvolvimento do TCC.

## ADDED Requirements

### Requirement: Exposição da aplicação via túnel

O sistema SHALL ser acessível a partir de dispositivos fora da máquina local mediante configuração de túnel (ngrok ou cloudflared).

#### Scenario: Acesso externo via túnel configurado
- **WHEN** o túnel está ativo
- **THEN** a interface é acessível por dispositivos fora da rede local via URL fornecida pelo túnel

#### Scenario: Acesso apenas local (padrão)
- **WHEN** nenhuma configuração de exposição externa está ativa
- **THEN** a interface é acessível apenas em localhost

### Requirement: Execução da pipeline completa

O sistema SHALL processar aquisição e extração do conjunto completo da RENAME após as metas de validação serem atingidas.

#### Scenario: Pipeline executada sobre conjunto completo
- **WHEN** as metas de F2 ≥ 0,80 e revocação ≥ 0,90 foram atingidas na fase de validação
- **THEN** a pipeline de aquisição e extração é executada para todos os medicamentos da RENAME, registrando resultados no banco

### Requirement: Interface funcional com volume real de dados

O sistema SHALL funcionar corretamente na interface web com o volume de dados resultante da execução completa da RENAME.

#### Scenario: Busca e cruzamento com volume completo
- **WHEN** a interface é usada com o banco populado com todos os medicamentos da RENAME
- **THEN** busca, autocomplete e cruzamentos retornam resultados corretamente sem degradação perceptível
