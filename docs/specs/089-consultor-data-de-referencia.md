---
id: 089
titulo: Consultor numa data passada (recomendações e opiniões daquele pregão)
status: draft
esforco: M
gaveta: experiência
aceite: tests/test_aceite_089.py
revisada: 2026-10-24
---

## Problema

Quem usa o Consultor quer ver o que ele recomendava em um pregão anterior e comparar com o que aconteceu depois. A spec 078 previa isso ("no `/consultor`, uma data passada mostra as recomendações registradas no diário"), mas a rota existe só no papel:

- depende do seletor e do parâmetro `data`, consertados na spec 088;
- o ramo histórico de `pagina_consultor` monta `dados` com `opinioes_recentes: []` e `opinioes_status: {}`, então a seção de opiniões fica vazia em qualquer data passada;
- o diário (`consultor_recomendacoes`) só é gravado quando alguém abre a página: `calcular_consultor` chama `save_recomendacoes` dentro da visita. Dias sem visita não têm registro, e o histórico teria buracos que ninguém consegue explicar.

Depende das specs 084, 086, 087 e 088. A 087 move a gravação do diário para o coletor `consultor_fechamento`; esta spec define o que o histórico faz com ele.

## Comportamento esperado

- `/consultor?data=AAAA-MM-DD` aceita os mesmos pregões do seletor (spec 088) e mostra:
  - as **recomendações registradas** daquele pregão em `consultor_recomendacoes`, agrupadas como na tela atual (Comprar, Vender, Aguardar, No radar), com a regra, o gatilho, o consenso e o preço da época. Nenhum recálculo.
  - as **opiniões de especialistas** com `extraida_em` até o fim daquele pregão (e dentro dos 30 dias anteriores), com a mesma tabela da tela atual.
  - o bloco "Informações de" (spec 086) com as datas daquele registro: o horário em que o diário foi gravado e o pregão dos sinais.
  - a faixa "Você está vendo o fechamento de dd/mm/aaaa" e o link "Voltar para hoje" (spec 088).
- Pregão sem registro no diário: "Sem registro do Consultor neste pregão." no lugar dos grupos, sem erro e sem recalcular.
- **Resultado depois do fato.** Para cada recomendação de um pregão passado, a tabela mostra a variação do ativo contra o Ibovespa nos pregões seguintes já disponíveis (até 5 pregões, o que existir), com a regra do `placar` já usada em `app/consultor/placar.py`. Se ainda não passou nenhum pregão, mostra "ainda sem resultado". O texto de amostra e janela fica no rodapé da tabela ("n = N recomendações, janela de até 5 pregões, preço de fechamento contra o IBOV").
- O coletor `consultor_fechamento` (spec 087) grava o diário uma vez por pregão, depois do fechamento, mesmo sem visita; fora do pregão não faz requisição externa.
- O cache da spec 087 não vale aqui: uma data passada lê só o que está gravado.
- Em 390 px, as tabelas seguem o padrão responsivo atual.

## Fontes de dados

Só o banco local (`consultor_recomendacoes`, `consultor_opinioes`, `series_diarias`). Nenhuma requisição externa.

## Cálculos

- Resultado por recomendação: `retorno_ativo(n) - retorno_ibov(n)` em pontos percentuais, com n de 1 a 5 pregões depois do dia da recomendação, usando fechamentos de `series_diarias`. Ativo ou Ibovespa sem fechamento no dia n: n é omitido, não preenchido com zero.
- Amostra e janela explícitas no rodapé, como em todo número do Consultor.

## Critérios de aceite

- [ ] Com recomendações de fixture em três datas, `GET /consultor?data=<data>` mostra as recomendações exatas daquela data e nenhuma de outra.
- [ ] Opiniões com `extraida_em` posterior ao fim do pregão escolhido não aparecem; as anteriores (até 30 dias) aparecem.
- [ ] Data sem registro mostra "Sem registro do Consultor neste pregão." e responde 200.
- [ ] A variação contra o Ibovespa dos pregões seguintes bate com a conta feita à mão sobre a série de fixture; sem pregão seguinte, o texto é "ainda sem resultado".
- [ ] Abrir uma data passada não executa `INSERT`, `UPDATE` nem requisição externa.
- [ ] O coletor `consultor_fechamento` grava o diário sem visita à página e não duplica quando a decisão é igual à do dia anterior.
- [ ] `/api/consultor?data=<data>` devolve o mesmo conteúdo em JSON, ou 404 para data fora da janela.

## Invariantes de produção

- O diário tem uma linha por ativo avaliado para cada pregão dos últimos 5, sem depender de alguém ter aberto a página.
- A data mostrada no bloco "Informações de" de um pregão passado é a do registro, e não a de hoje.

## Fora do escopo

- Comparar duas datas lado a lado.
- Recalcular o que o Consultor teria dito num dia sem registro.
- Janela maior que 5 pregões.
