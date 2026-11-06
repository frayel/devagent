---
id: 134
titulo: A variação do Ibovespa no painel é a do dia, não a de um ano atrás
status: ready
esforco: M
gaveta: saúde técnica
aceite: tests/test_aceite_134.py
brief: P0-1
---

## Problema
O usuário perguntou: "o painel diz que o mercado está em alta e o Ibovespa indica +12,87%, mas o último pregão fechou em queda. Essa alta é de que período?"

Pelo código, o percentual do card "Ibovespa hoje" é calculado como se fosse a variação do dia, mas o fechamento anterior vem de outro lugar:

- `fetch_yfinance` (`app/collectors/ibovespa.py:90`) consulta `chart/^BVSP?range=1y&interval=1d`.
- Na linha 127 ele faz `meta.get("chartPreviousClose") or meta.get("previousClose")` e só usa o penúltimo fechamento da série (`valid_closes[-2]`) se os dois campos vierem vazios. Os comentários das linhas 113 e 125 se contradizem: um diz que `chartPreviousClose` "is often incorrect for B3", o outro que é "the most reliable source".
- Na API do Yahoo, `chartPreviousClose` é o fechamento anterior ao **início da janela pedida**. Com `range=1y`, é o de cerca de um ano atrás.
- O módulo do MT5 imita esse comportamento: `app/collectors/mt5.py:406` e `:419` preenchem `chartPreviousClose` com o último fechamento antes da janela. O campo correto, `previousClose` (o pregão anterior), está em `:420`, mas nunca é lido porque o primeiro campo sempre vem preenchido.
- Como o MT5 responde no lugar do Yahoo (`fetch_with_retry` chama `mt5.interceptar` antes da requisição), o rótulo da fonte pode dizer `mt5` e o defeito continua o mesmo.

O valor gravado em `previous_close` alimenta: `app/services/ibovespa.py:13` (card, `is_positive` e a manchete de `app/services/manchete.py`), `app/main.py:947` (`/api/snapshot`) e `app/collectors/anomalia_peso.py:28` (pontos por ação).

Esta leitura vem do código e de testes com dublês. Não foi conferida contra a produção; o critério 1 reproduz o defeito sem internet, e as Invariantes dizem como confirmar no site publicado.

## Comportamento esperado
O fechamento anterior passa a vir da própria série de fechamentos, nesta ordem:

1. Série válida (sem `None`) com 2 ou mais fechamentos, e a última barra é do pregão corrente (data de hoje em BRT) **ou** o preço atual é igual ao último fechamento (tolerância de 0,01%): `previous_close = fechamentos[-2]`.
2. Série cuja última barra é de um pregão anterior e o preço atual é diferente dela (antes da abertura): `previous_close = fechamentos[-1]`.
3. Série com menos de 2 fechamentos: `meta["previousClose"]`, depois `meta["regularMarketPreviousClose"]`.
4. Nada disso existe: o preço atual, com um aviso no log (variação 0, como hoje).

`chartPreviousClose` não entra em nenhum dos passos. Os dois comentários contraditórios são trocados por um que explica a regra. O resto de `fetch_yfinance` e os consumidores do campo não mudam.

## Fontes de dados
MT5 respondendo no formato do Yahoo (`chart/^BVSP`, `range=1y`); plano B: o próprio Yahoo, como hoje. Nada de fonte nova.

## Cálculos
`variação = preço atual − previous_close`; `variação % = variação / previous_close × 100`. Só muda de onde sai `previous_close`.

## Critérios de aceite
- [ ] Dado um dublê do Yahoo com `range=1y`, 250 fechamentos, penúltimo `130000.0`, último e preço atual `131300.0` e `chartPreviousClose = 105000.0`, `fetch_yfinance().previous_close == 130000.0` e a variação calculada é `+1,00%`.
- [ ] O mesmo cenário montado por `mt5.bloco_yahoo(..., "1d", "1y")` com barras diárias falsas (helper de `tests/test_mt5.py`) dá o mesmo `previous_close`: o campo `chartPreviousClose` do MT5 continua sendo o de antes da janela, e o coletor não o usa.
- [ ] Série cuja última data é anterior a hoje e cujo preço atual difere do último fechamento: `previous_close` é o último fechamento.
- [ ] Série com 1 fechamento e `previousClose` ausente: usa `regularMarketPreviousClose`; sem ele, usa o preço atual e registra aviso.
- [ ] Com o dado gravado pelo cenário do primeiro critério, `GET /` mostra `+1,00%` no card e `GET /api/snapshot` traz `paineis.ibovespa.variacao_pct` ≈ `1.0` e `fechamento_anterior == 130000.0`.
- [ ] Com o penúltimo fechamento acima do atual (queda de `-0,80%`), o card mostra `-0,80%`, `is_positive` é falso e a manchete de `gerar_manchete` diz "baixa".
- [ ] Os testes de `tests/test_ibovespa.py` e `tests/test_ibovespa_variacao_extrema.py` continuam verdes; qualquer um que dependa de `chartPreviousClose` é ajustado e citado no PR.
- Arquivos tocados: `app/collectors/ibovespa.py`, o novo `tests/test_aceite_134.py` e, se preciso, ajustes pontuais em `tests/test_ibovespa.py`.

## Invariantes de produção
- Em `/api/snapshot`, `paineis.ibovespa.fechamento_anterior` é igual (tolerância de 0,05%) ao penúltimo valor de `paineis.ibovespa.historico.fechamentos`, salvo antes da abertura do pregão, quando é igual ao último.
- A variação do card difere em no máximo 0,1 ponto percentual da calculada pelos dois últimos pontos do gráfico ao lado dele.
- Para confirmar o defeito antes do deploy: o `fechamento_anterior` atual em `/api/snapshot` deve estar perto do nível do Ibovespa de um ano atrás. A spec 138 transforma estas duas invariantes em checagens do auditor.

## Fora do escopo
- Mudar o teto de variação diária e as regras de gravar ou não acima de 10% e de 20% (spec 136). O sinal de revisão desta spec não apaga o número e não substitui a 136.
- O catálogo de frases da manchete (spec 140). Esta spec só publica o sinal que a manchete consome.
- O as-of da página inteira e o TTL dos outros cards (spec 141). O card do Ibovespa continua obrigado a dizer o pregão da própria variação.
- Outros coletores com a mesma falha e o dublê do Yahoo (spec 135).
- Checagens do auditor (specs 137 e 138).
- Alterar `mt5.py`: ele imita o Yahoo de propósito, e o contrato do campo está provado em `tests/test_mt5.py:105`.
- Buscar um feed de ajuste oficial da B3 que o repositório não tem.

## Evidência histórica (brief P0-1)

Em 05/11/2026, no ambiente publicado, o card foi observado em 167.627 pts, +16.923 (+11,23%), com fonte `mt5` e carimbo 04/11 15:10. Esses três números fecham entre si: 167.627 − 16.923 = 150.704 e 16.923 / 150.704 ≈ 11,23%. A aritmética interna do card, naquela observação, era consistente. O que não está confirmado é se 150.704 era o fechamento do pregão anterior, nem se o carimbo de 04/11 era o pregão que a tela chamava de hoje.

Hipóteses a validar, não causa confirmada: base errada, fechamento antigo, janela ou índice trocados, fuso ou sessão desalinhados. A leitura de `chartPreviousClose` na seção Problema é o que o código faz hoje; ela não foi conferida contra o snapshot daquele horário. Issues abertas de frescor (#772, #764) são contexto, e esta spec não as fecha.

O campo `revisada:` de 03/11/2026 foi retirado porque o texto abaixo ainda não passou pelo Revisor.

## Sinal de revisão

`pontos = último − fechamento do pregão regular anterior` e `percentual = pontos / fechamento do pregão regular anterior × 100`, como em `docs/context/dominio-b3.md` e em `app/services/ibovespa.py`. "Oficial", neste repositório, é o fechamento da sessão regular anterior do mesmo instrumento (`^BVSP` / `IBOV`), pela regra de `previous_close` já descrita acima. Não é `chartPreviousClose` de uma janela longa e não é um ajuste publicado pela B3.

Constantes configuráveis, no coletor do Ibovespa: `LIMIAR_PCT_REVISAO = 3.0` e `LIMIAR_PONTOS_REVISAO = 5000`. Se `|percentual| > 3` ou `|pontos| >= 5000`, o card e `paineis.ibovespa` ganham `revisao_variacao: true` e um selo visível de revisão. O número continua na tela. O selo não é prova de dado errado e não autoriza apagar um pregão que tenha de fato andado isso. A spec 136 segue dona do que é gravado acima de 10% e do descarte acima de 20%.

Enquanto `revisao_variacao` for verdadeiro, o card não usa tom de alta ou queda larga. A frase da manchete é da spec 140; o aceite desta spec só exige o booleano no snapshot e o selo no HTML.

## Sessão, feriado e base ausente

- O rodapé do card traz a fonte e o carimbo da coleta em `America/Sao_Paulo` (`dd/mm/aaaa HH:MM BRT`). O percentual diz o pregão da base e o pregão do último preço quando os dois não são o mesmo dia civil.
- Pregão fechado, fim de semana ou feriado de `auditoria/calendario.py`: o card mostra o fechamento da última sessão, com a data dela. Não usa a palavra "hoje" para um número de sessão anterior.
- Sem fechamento anterior, o card não publica `0%`. A variação fica em `estado('indisponivel')` e o preço último, se existir, permanece com a fonte. Hoje `app/services/ibovespa.py` cai em `0.0` quando `previous_close` é falso; o aceite cobre esse caso.
- Falha da fonte: o último snapshot permanece com o carimbo original. A coleta que falha não avança `coletado_em`.

## Critérios de aceite (expansão)
- [ ] Fixture com último `131300`, fechamento anterior `130000`: pontos `+1.300`, percentual `+1,00%`, `revisao_variacao` falso (1% e 1.300 pontos ficam abaixo dos dois limiares).
- [ ] Fixture com último `167627` e fechamento anterior `150704`: pontos `+16.923`, percentual `+11,23%`, `revisao_variacao` verdadeiro, e o HTML do card contém o selo de revisão e os dois números. O fixture reproduz a aritmética observada; não afirma que 150.704 era o fechamento de 03/11 ou de 04/11.
- [ ] `|pontos| = 5000` com percentual de 2%: `revisao_variacao` verdadeiro. Percentual de 3,0% com 100 pontos: falso, porque o corte do percentual é estrito (`>`).
- [ ] `previous_close` ausente: a página não contém `0,00%` no card do Ibovespa e o snapshot traz a variação nula, com estado indisponível.
- [ ] Carimbo `2026-11-04T18:10:00Z` lido num instante de 05/11: o rodapé mostra `04/11/2026 15:10 BRT` e o texto do card não chama esse número de hoje.
- [ ] Os critérios originais desta spec continuam valendo. `tests/test_aceite_134.py` começa com `exigir_spec_done("134")`.

## Plano de validação
`pytest -q tests/test_aceite_134.py tests/test_ibovespa.py` sem internet. No PR de implementação, uma passagem de manhã e outra de tarde do mesmo pregão, com o `/api/snapshot` real, confirma fonte, pregão e sinal; esta spec não traz essa captura. Causa raiz do +11,23% de 05/11 só entra no relatório de implementação se a evidência a sustentar.
