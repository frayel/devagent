---
id: 145
titulo: O gráfico do Ibovespa usa a mesma base do número do dia
status: ready
esforco: M
gaveta: experiência
aceite: tests/test_aceite_145.py
brief: P1-4
depende_de: 134, 141
---

## Problema
O usuário perguntou: "se o card sobe 11%, por que o desenho ao lado cai de cerca de 210 mil para 167 mil?"

Em 05/11/2026 a série visual foi observada nessa queda enquanto o card mostrava alta de cerca de 11%. Observação histórica. Hipótese a validar, não causa confirmada: a série, o ajuste, a sessão ou a base do dia não são os do número. O componente real não é uma sparkline de 48px. É o gráfico `#grafico-ibovespa` (`app/templates/index.html`, `app/static/ui.js`), alimentado pelos últimos 30 fechamentos em `history_json` (`app/collectors/ibovespa.py`). Uma queda ao longo de 30 pregões pode ser verdadeira e ainda assim não ser a variação do dia. A spec 134 já pede que a variação do card bata com os dois últimos pontos; esta spec pede que a janela inteira não seja lida como se fosse o dia.

## Comportamento esperado
- A série é do mesmo instrumento do card (`^BVSP` no Yahoo, `IBOV` no MT5). Os fechamentos são os da mesma coleta que gravou o preço e o `previous_close`.
- O último ponto e o preço do card diferem em no máximo 0,05%. Os dois últimos pontos e a variação do dia obedecem à spec 134.
- Legenda visível, não só `aria-label`: "Últimos 30 pregões", com a data do primeiro e a do último ponto, em `dd/mm/aaaa`. O `aria-label` repete esse intervalo e não repete o percentual do dia como se fosse o retorno dos 30 pregões.
- O tooltip do último ponto mostra a data, o último preço, o fechamento do pregão anterior usado no card e a variação do dia em pontos e em percentual. Os pontos anteriores mostram data e fechamento. Datas em `America/Sao_Paulo`.
- O preenchimento segue `docs/DESIGN.md` seção 5: até o mínimo do período, a 10% de opacidade, não `fill: 'tozeroy'` (`app/static/ui.js`). O eixo Y continua sem começar em zero. Isso é correção de desenho; não se afirma que o `tozeroy` produziu os níveis 210 mil e 167 mil.
- Se a data do último ponto e o pregão do card (spec 141) divergirem, a legenda mostra as duas datas e o card não trata a série como o intradiário de hoje.

## Fontes de dados
A série já coletada com `range=1y&interval=1d`, da qual saem os 30 últimos pontos. Plano B: sem dois pontos, o gráfico não é desenhado e o card do preço permanece, com a variação pela spec 134.

## Cálculos
Janela visual = 30 últimos fechamentos válidos. Variação do dia = último − fechamento da sessão anterior, não último − primeiro da janela. O retorno dos 30 pregões, se um dia for exibido, leva o rótulo "30 pregões" e não substitui o percentual do card.

## Critérios de aceite
- [ ] Fixture com 30 fechamentos de 210.000 no primeiro a 167.627 no último, card em `+1,00%` contra o penúltimo: o HTML da legenda contém "30 pregões" e as duas datas extremas, e não atribui `+1,00%` ao intervalo inteiro. O penúltimo é a base do `+1,00%`.
- [ ] O tooltip configurado para o último ponto inclui o fechamento anterior e o percentual do dia. Teste lê o `hovertemplate` ou o texto equivalente que o JS monta, sem chamar a CDN do Plotly.
- [ ] O `fill` da série não é `tozeroy`.
- [ ] Último ponto 167.627 e preço do card 167.627: passa. Preço do card 1% acima do último ponto: o teste de coerência falha.
- [ ] `tests/test_aceite_145.py` usa `exigir_spec_done("145")` e não abre rede.

## Invariantes de produção
- O último fechamento de `paineis.ibovespa.historico` e o valor do card diferem em no máximo 0,05%.
- A variação do card difere em no máximo 0,1 ponto percentual da variação entre os dois últimos pontos do histórico, no caso em que a spec 134 já exige isso.
- A página que mostra o gráfico também mostra as datas do primeiro e do último ponto.

## Fora do escopo
- Trocar a janela de 30 pregões ou o `range=1y` da coleta.
- Explicar os níveis de 05/11/2026 como série corrompida.
- Sparkline dos rankings (spec 029).

## Plano de validação
`pytest -q tests/test_aceite_145.py` sem internet. No PR de implementação, manhã e tarde do mesmo pregão mostram a legenda de 30 pregões ao lado do percentual do dia. Sem captura nesta rodada. A forma 210 mil → 167 mil pode permanecer se for o caminho real dos 30 pregões.
