---
id: 070a
titulo: Consultor · opiniões de casas de análise (feeds, pré-filtro e fila)
status: done
esforco: M
---

## Problema
O usuário quer saber o que as casas de análise dizem sobre cada ação do Ibovespa, sem ler dezenas de matérias. Estas opiniões aparecem em portais de notícia, em texto livre. Esta spec (primeira parte da spec 070) é responsável por coletar os feeds de notícias, realizar um pré-filtro para encontrar as que citam os ativos de interesse e salvá-las na fila.

## Comportamento esperado
- Coleta de feeds RSS a cada 30 minutos.
- Pré-filtro para selecionar apenas matérias que citem um ticker ou empresa do mapa da spec 068 e também um termo indicativo de recomendação.
- As matérias selecionadas são armazenadas na tabela `consultor_fila_materias` pelo armazenamento isolado. Itens com mais de 3 dias são descartados e a fila tem no máximo 200 itens.

## Fontes de dados
- **Feeds RSS**, coletados a cada 30 minutos pelo agendador, com 1 requisição a cada 2 s por domínio, timeout, retry com backoff e `User-Agent` identificável:
  - Money Times: `https://www.moneytimes.com.br/feed/`
  - InfoMoney: `https://www.infomoney.com.br/feed/`
- Só o conteúdo do próprio feed (título, descrição e `content:encoded` quando houver) é usado. A página da matéria não é baixada.

## Cálculos
1. **Pré-filtro sem LLM.** Normalizar título e descrição (minúsculas, sem acento). A matéria segue se citar um ticker do universo ou um nome do mapa empresa → tickers (spec 068) **e** um termo de opinião: `recomend`, `compra`, `venda`, `neutr`, `preco-alvo`, `preco alvo`, `carteira`, `eleva`, `rebaix`, `outperform`, `underperform`, `overweight`, `underweight`, `market perform`. Matérias já vistas (pelo `guid`) são ignoradas.
2. **Fila.** As aprovadas entram em `consultor_fila_materias` através da interface `app/consultor/armazenamento.py`. Itens com mais de 3 dias são descartados; a fila tem no máximo 200 itens.

## Critérios de aceite
- [ ] Com um fixture RSS de 10 itens, só os que citam ativo do universo e termo de opinião entram na fila.
- [ ] O limite máximo de 200 itens na fila e o descarte após 3 dias são respeitados.
- [ ] A coleta trata adequadamente erros nos feeds sem comprometer o resto da execução.
