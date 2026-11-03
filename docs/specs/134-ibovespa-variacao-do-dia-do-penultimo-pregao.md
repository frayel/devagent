---
id: 134
titulo: A variação do Ibovespa no painel é a do dia, não a de um ano atrás
status: ready
esforco: P
gaveta: saúde técnica
aceite: tests/test_aceite_134.py
---

## Problema
O usuário perguntou: "o painel diz que o mercado está em alta e o Ibovespa indica +12,87%, mas o último pregão fechou em queda. Essa alta é de que período?"

Pelo código, o percentual do card "Ibovespa hoje" é calculado como se fosse a variação do dia, mas o fechamento anterior vem de outro lugar:

- `fetch_yfinance` (`app/collectors/ibovespa.py:90`) consulta `chart/^BVSP?range=1y&interval=1d`.
- Na linha 127 ele faz `meta.get("chartPreviousClose") or meta.get("previousClose")` e só usa o penúltimo fechamento da série (`valid_closes[-2]`) se os dois campos vierem vazios. Os comentários das linhas 113 e 125 se contradizem: um diz que `chartPreviousClose` "is often incorrect for B3", o outro que é "the most reliable source".
- Na API do Yahoo, `chartPreviousClose` é o fechamento anterior ao **início da janela pedida**. Com `range=1y`, é o de cerca de um ano atrás.
- O módulo do MT5 imita esse comportamento: `app/collectors/mt5.py:406` e `:419` preenchem `chartPreviousClose` com o último fechamento antes da janela. O campo correto, `previousClose` (o pregão anterior), está em `:420`, mas nunca é lido porque o primeiro campo sempre vem preenchido.
- Como o MT5 responde no lugar do Yahoo (`fetch_with_retry` chama `mt5.interceptar` antes da requisição), o rótulo da fonte pode dizer `mt5` e o defeito continua o mesmo.

O valor gravado em `previous_close` alimenta: `app/services/ibovespa.py:13` (card, `is_positive` e a manchete de `app/services/manchete.py`), `app/main.py:947` (`/api/snapshot`) e `app/collectors/anomalia_peso.py:28` (pontos por ação). O caminho da brapi (`regularMarketPreviousClose`) não tem o defeito.

Esta leitura vem do código e de testes com dublês. Não foi conferida contra a produção; o critério 1 reproduz o defeito sem internet, e as Invariantes dizem como confirmar no site publicado.

## Comportamento esperado
O fechamento anterior passa a vir da própria série de fechamentos, nesta ordem:

1. Série válida (sem `None`) com 2 ou mais fechamentos, e a última barra é do pregão corrente (data de hoje em BRT) **ou** o preço atual é igual ao último fechamento (tolerância de 0,01%): `previous_close = fechamentos[-2]`.
2. Série cuja última barra é de um pregão anterior e o preço atual é diferente dela (antes da abertura): `previous_close = fechamentos[-1]`.
3. Série com menos de 2 fechamentos: `meta["previousClose"]`, depois `meta["regularMarketPreviousClose"]`.
4. Nada disso existe: o preço atual, com um aviso no log (variação 0, como hoje).

`chartPreviousClose` não entra em nenhum dos passos. Os dois comentários contraditórios são trocados por um que explica a regra. O resto de `fetch_yfinance`, os consumidores do campo e o caminho da brapi não mudam.

## Fontes de dados
Yahoo (`chart/^BVSP`, `range=1y`) ou o MT5 respondendo no formato do Yahoo; plano B: brapi, como hoje. Nada de fonte nova.

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
- Mudar o teto de variação diária (spec 136).
- Outros coletores com a mesma falha e o dublê do Yahoo (spec 135).
- Checagens do auditor (specs 137 e 138).
- Alterar `mt5.py`: ele imita o Yahoo de propósito, e o contrato do campo está provado em `tests/test_mt5.py:105`.
