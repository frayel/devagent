---
id: 145
titulo: O gráfico do Ibovespa usa a mesma base do número do dia
status: done
esforco: M
gaveta: experiência
aceite: tests/test_aceite_145.py
brief: P1-4
depende_de: 134, 141
revisada: 2026-11-14
---

## Problema
O usuário perguntou: "se o card sobe 11%, por que o desenho ao lado cai de cerca de 210 mil para 167 mil?"

Em 05/11/2026 a série visual foi observada nessa queda enquanto o card mostrava alta de cerca de 11%. Observação histórica. Hipótese a validar, não causa confirmada: a série, o ajuste, a sessão ou a base do dia não são os do número. O componente real não é uma sparkline de 48px. É o gráfico `#grafico-ibovespa` (`app/templates/index.html`, `app/static/ui.js`), alimentado pelos últimos 30 fechamentos em `history_json` (`app/collectors/ibovespa.py`). Uma queda ao longo de 30 pregões pode ser verdadeira e ainda assim não ser a variação do dia. A spec 134 já pede que a variação do card bata com os dois últimos pontos; esta spec pede que a janela inteira não seja lida como se fosse o dia.

## Comportamento esperado
- A série é do mesmo instrumento do card (`^BVSP` no Yahoo, `IBOV` no MT5). Os fechamentos são os da mesma coleta que gravou o preço e o `previous_close`.
- Quando a data do último ponto é o pregão do card (spec 141), o último ponto e o preço do card diferem em no máximo 0,05%. Os dois últimos pontos e a variação do dia obedecem à spec 134.
- Legenda visível, não só `aria-label`: "Últimos 30 pregões", com a data do primeiro e a do último ponto, em `dd/mm/aaaa`. O `aria-label` repete esse intervalo e não repete o percentual do dia como se fosse o retorno dos 30 pregões. Hoje o `resumo_serie` (`app/services/ibovespa.py`) já diz "Ibovespa nos últimos N pregões: de X a Y, baixa de Z%" com o retorno da janela; falta só acrescentar as duas datas. As datas saem de `history_dict.dates` (ISO `aaaa-mm-dd`, como o coletor grava) e são formatadas no servidor, para o teste ler no HTML.
- O tooltip do último ponto mostra a data, o último preço, o fechamento do pregão anterior usado no card e a variação do dia em pontos e em percentual. Os pontos anteriores mostram data e fechamento. Datas em `America/Sao_Paulo`.
- A cor da linha segue o sinal do período (DESIGN.md seção 5: "`--alta` ou `--baixa` conforme o sinal do período"), isto é, último contra primeiro ponto da janela. Hoje `ui.js` usa `data-is-positive`, que é o sinal do dia: uma janela em queda desenhada em verde porque o dia subiu é a mesma confusão do problema. O sinal do dia continua no card.
- O preenchimento segue `docs/DESIGN.md` seção 5: até o mínimo do período, a 10% de opacidade, não `fill: 'tozeroy'` (`app/static/ui.js`). O eixo Y continua sem começar em zero. Isso é correção de desenho; não se afirma que o `tozeroy` produziu os níveis 210 mil e 167 mil.
- Se a data do último ponto e o pregão do card (spec 141) divergirem, a legenda mostra as duas datas e o card não trata a série como o intradiário de hoje.

## Fontes de dados
A série já coletada com `range=1y&interval=1d`, da qual saem os 30 últimos pontos. Plano B: sem dois pontos, o gráfico não é desenhado e o card do preço permanece, com a variação pela spec 134.

## Cálculos
Janela visual = 30 últimos fechamentos válidos. Variação do dia = último − fechamento da sessão anterior, não último − primeiro da janela. O retorno dos 30 pregões, se um dia for exibido, leva o rótulo "30 pregões" e não substitui o percentual do card.

## Exemplo numérico de ponta a ponta
Dado bruto: o coletor grava `history_json` = `{"dates": ["2026-09-23", ..., "2026-11-04", "2026-11-05"], "closes": [210000.0, ..., 165967.33, 167627.0]}`, fechamentos em pontos do índice, 30 pregões pelo `auditoria/calendario.py` (12/10 e 02/11 não contam); `current_price` = 167627.0 e `previous_close` = 165967.33, também em pontos.

- Variação do dia (card): 167627 − 165967,33 = +1.659,67 pontos; 1.659,67 / 165967,33 × 100 = **+1,00%**. Base: o penúltimo ponto da série.
- Retorno da janela (aria-label e cor da linha): 167627 / 210000 − 1 = −0,2018 → **baixa de 20,2%**; linha em `--baixa`, mesmo com o card em `+1,00%`.
- Legenda: **"Últimos 30 pregões · 23/09/2026 a 05/11/2026"**.
- Coerência: |167627 − 167627| / 167627 = 0 ≤ 0,0005. Com o card em 169303,27 (1% acima): 1675,27 / 167627 = 0,0100 > 0,0005, incoerente.

## Critérios de aceite
- [ ] Fixture com 30 fechamentos de 210.000 no primeiro a 167.627 no último, card em `+1,00%` contra o penúltimo: o HTML da legenda contém "30 pregões" e as duas datas extremas, e não atribui `+1,00%` ao intervalo inteiro. O penúltimo é a base do `+1,00%`.
- [ ] O tooltip configurado para o último ponto inclui o fechamento anterior e o percentual do dia. Teste lê o `hovertemplate` ou o texto equivalente que o JS monta, sem chamar a CDN do Plotly.
- [ ] O `fill` da série não é `tozeroy`.
- [ ] Na fixture acima (dia `+1,00%`, janela −20,2%), a cor da série é a de baixa: o atributo que o template passa ao JS para escolher a cor reflete o sinal do período, não `is_positive` do dia.
- [ ] Último ponto 167.627 e preço do card 167.627: passa. Preço do card 1% acima do último ponto: o teste de coerência falha. A checagem já existe e não muda: `checar_coerencia` em `auditoria/auditar.py` (resultado `ibov.fechamento_anterior_coerente`, tolerância 0,05%, protegido). O teste monta o snapshot de `GET /api/snapshot` com a fixture, passa por `extrair_do_snapshot` e confere o resultado.
- [ ] `tests/test_aceite_145.py` usa `exigir_spec_done("145")` e não abre rede.

## Invariantes de produção
- Quando `paineis.ibovespa.historico.datas[-1]` é o `pregao` do painel, o último de `historico.fechamentos` e `valor` diferem em no máximo 0,05% (o auditor já confere isso em `ibov.fechamento_anterior_coerente`).
- A variação do card difere em no máximo 0,1 ponto percentual da variação entre os dois últimos pontos do histórico, no caso em que a spec 134 já exige isso.
- A página que mostra o gráfico também mostra as datas do primeiro e do último ponto, em `dd/mm/aaaa`, iguais a `historico.datas[0]` e `historico.datas[-1]` do snapshot.
- A cor da linha do gráfico na home corresponde ao sinal de `historico.fechamentos[-1] − historico.fechamentos[0]`.

## Fora do escopo
- Trocar a janela de 30 pregões ou o `range=1y` da coleta.
- Explicar os níveis de 05/11/2026 como série corrompida.
- Sparkline dos rankings (spec 029).

## Plano de validação
`pytest -q tests/test_aceite_145.py` sem internet. No PR de implementação, manhã e tarde do mesmo pregão mostram a legenda de 30 pregões ao lado do percentual do dia. Sem captura nesta rodada. A forma 210 mil → 167 mil pode permanecer se for o caminho real dos 30 pregões.

## Revisão
Revisada em 14/11/2026. Conferido na `main`: o gráfico é `#grafico-ibovespa` (`app/templates/index.html`) desenhado por `app/static/ui.js` com `fill: 'tozeroy'` e cor por `data-is-positive` (sinal do dia); o `hovertemplate` mostra só data e fechamento; o `aria-label` já resume a janela sem o percentual do dia, mas sem datas; não há legenda visível. Specs 134 e 141 estão `done`. Nenhuma outra spec `ready` ou `draft` trata do mesmo gráfico (146 cita o `ui.js` só por erro de console). Tamanho: 3 arquivos de código (`ui.js`, `index.html`, `services/ibovespa.py`) e 1 de teste existente (`tests/test_main.py`) mais o de aceite. Alterado: exemplo numérico de ponta a ponta, cor da linha pelo sinal do período (DESIGN.md seção 5), invariante de 0,05% condicionada ao último ponto ser do pregão do card (série do Yahoo pode chegar sem a barra de hoje), critério de coerência ancorado na checagem existente do auditor, origem e formato das datas da legenda.
