---
id: 123
titulo: Heatmap visual da Maré do Mercado
status: ready
esforco: M
aceite: tests/test_aceite_123.py
revisada: 2026-10-28
gaveta: experiência
---

## Problema
Quais ações compõem o humor da maré?

## Comportamento esperado
Substituir ou complementar a visão em texto da maré por um "heatmap" dinâmico visual, destacando a intensidade de volume e a variação da ação, mostrando blocos maiores e coloridos para os ativos com mais peso. O painel se atualiza conforme a coleta de dados da maré.

## Fontes de dados
API de cotações já coletada no banco de dados (SQLite/Postgres). Nenhuma fonte nova externa será adicionada.

## Cálculos
Tamanho do bloco: Proporcional ao volume e ao peso da ação no Ibovespa.
Cor do bloco: Intensidade de variação em percentual.

## Critérios de aceite
- [ ] O componente heatmap renderiza sem erros
- [ ] O painel exibe no mínimo os 10 ativos de maior peso

## Invariantes de produção
- Nenhuma chamada a API externa extra é feita para renderizar a página inicial
- O HTML do heatmap exibe dados se e somente se o banco tiver retornado a coleção de ativos

## Tamanho
Afetará 1 componente visual em `app/templates/index.html` e 1 arquivo de teste `tests/test_aceite_123.py` (total: 2 arquivos).

## Fora do escopo
- Coletar dados interativos ou clique no bloco de heatmap.
