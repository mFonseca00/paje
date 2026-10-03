# Exposição Externa e Execução Completa

## Problema

O sistema está funcional localmente mas inacessível fora da máquina de desenvolvimento. Além disso, a pipeline ainda não foi executada sobre o conjunto completo da RENAME.

## Solução Proposta

Expor a aplicação via túnel (ngrok ou cloudflared) para demonstração sem configuração de infraestrutura. Em paralelo, executar aquisição e extração do conjunto completo e verificar que a interface suporta o volume real de dados.

## Motivação

Necessário para a apresentação do TCC: a banca precisa acessar o sistema e ver os dados reais, não apenas uma amostra local.
