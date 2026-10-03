# Interface Web

## Problema

Os dados de contra-indicações e interações medicamentosas estão armazenados no banco mas inacessíveis sem SQL. É necessária uma interface que permita ao usuário final selecionar medicamentos e visualizar os cruzamentos clínicos de forma clara.

## Solução Proposta

SPA React + TypeScript com um único campo de busca com autocomplete para seleção de múltiplos medicamentos. Os pares selecionados são enviados a um endpoint FastAPI que retorna as interações e contra-indicações relevantes com referência à bula de origem. Layout minimalista, paleta azul e branca, responsivo para desktop e smartphone.

## Motivação

A interface é o produto final visível do TCC — transforma o banco de dados em algo demonstrável para a banca e utilizável por profissionais de saúde.
