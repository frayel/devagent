---
id: 142
titulo: A lista de ganhos não repete a pressão vendedora
status: ready
esforco: M
gaveta: experiência
aceite: tests/test_aceite_142.py
brief: P1-1
depende_de: 134, 015, 047
---

## Problema
O usuário perguntou: "por que o texto de ganhos e a lista de quedas contam a mesma história?"

Em 05/11/2026 o texto observado foi "919 pontos de queda… 50% vieram de apenas 4 ações", e a lista mostrava os mesmos três perdedores WEGE3, PETR4 e BBDC4 nos dois painéis. Observação histórica. Esses três tickers estão em `TICKERS_PESOS` (`app/collectors/concentracao.py`); a spec não afirma a ordem calculada naquele instante.

O código explica a forma do defeito, sem fechar a causa do dia: `fetch_yfinance` guarda em `top3_json` só `contribs[:3]`, enquanto `acoes_50_pct` pode passar de 3. O filtro de ganhos fica com contribuições do mesmo sinal do índice. Com o índice em queda, a lista de "ganhos" são quedas. A pressão vendedora (`fetch_concentracao_vendedora_yfinance`) também lista `t_pts < 0`. As duas frases falam de queda. O percentual exibido passa por `min(100, ...)`.

As specs 015 e 047 entregaram os painéis. Esta spec corrige o que cada lista significa.

## Comportamento esperado
Dois painéis, os mesmos de hoje, sem painel novo.

- **Concentração de Ganhos** lista só contribuições positivas (`t_pts > 0`), da maior para a menor. Se o índice caiu, o título e a frase falam em ganhos que compensam a queda, não em "pontos de queda vieram de". Sem contribuição positiva, o estado é "Nenhuma contribuição positiva na cesta", e a lista de perdedores não é copiada para cá.
- **Pressão Vendedora** lista só contribuições negativas. Se o índice subiu, a frase fala em contribuição que segurou a alta. O coletor hoje devolve `None` quando `ibov_var_pts >= 0` e o card some; passa a publicar a lista negativa com essa frase, ou o estado vazio se não houver contribuição negativa.
- O inteiro N da frase é o número de linhas renderizadas. Se o corte de 50% precisa de 4 nomes, a tabela tem 4 linhas. Não há teto escondido de 3.
- Nome sem barra não entra. A frase diz "K de N da cesta" com K o número de tickers que tinham base e último preço.

## Fontes de dados
Yahoo `spark` com `range=5d&interval=1d`, como o coletor, com MT5 na frente quando `mt5.fonte_efetiva` já troca a fonte. Plano B: falha dos dois deixa o card em `estado('indisponivel')` e não reaproveita a lista do outro painel.

## Cálculos
Cesta e pesos: `TICKERS_PESOS`, frações estáticas (VALE3 0,12 … a soma das dez é 0,50). Não são os pesos oficiais do dia da B3.

`pontos_teóricos = variação_da_ação × peso × fechamento_anterior_do_Ibovespa`.

A variação da ação e a do índice usam o fechamento da sessão anterior da própria série (spec 134 para o índice). Unidade da coluna: pontos teóricos, com o sinal.

Ganhos: ordenar `pontos_teóricos > 0` do maior ao menor e somar até atingir 50% da soma das contribuições positivas. A frase usa essa soma e esse N. A parcela pode passar de 100% do movimento do índice quando o resto da cesta compensa; o texto mostra a parcela sem `min(100, ...)` e, se passar de 100%, diz que o restante compensou.

Pressão: o mesmo com `pontos_teóricos < 0`, em módulo, sobre a soma das contribuições negativas.

Índice estável: o coletor de ganhos já usa `|ibov_var_pct| < 0,001`, e essa variável é a razão `(atual − anterior) / anterior`, isto é, 0,1%. A pressão não tem esse corte: devolve `None` quando a variação em pontos é ≥ 0. Os dois cards passam a usar o corte de 0,1% e a frase "Ibovespa estável, sem concentração definida.", sem listar nomes.

## Critérios de aceite
- [ ] Índice −919 pontos. Três nomes com pontos teóricos negativos e quatro com positivos. A pressão lista só os negativos; os ganhos listam só os positivos. WEGE3, PETR4 e BBDC4, se estiverem entre os negativos, não aparecem em ganhos.
- [ ] Quatro nomes positivos somam a metade dos ganhos: a frase contém `4` e a tabela tem 4 linhas.
- [ ] Índice em queda e frase de ganhos: o texto contém "compens" e não contém "pontos de queda".
- [ ] Soma teórica dos ganhos igual a 140% do movimento do índice: a frase mostra um número maior que 100 e não mostra 100 no lugar.
- [ ] Um ticker da cesta sem barra: K = 9 se a cesta tem 10, e a frase contém `9`.
- [ ] `tests/test_aceite_142.py` usa `exigir_spec_done("142")` e não abre rede.

## Invariantes de produção
- Nenhuma linha de Concentração de Ganhos tem pontos negativos, e nenhuma de Pressão Vendedora tem pontos positivos.
- O inteiro de ações na frase de cada painel é igual ao número de linhas da tabela desse painel.
- Os pesos publicados somam 0,50 na cesta inteira, ou a frase declara quantos nomes entraram.

## Fora do escopo
- Pesos oficiais diários da carteira teórica.
- Fundir os dois painéis num só.
- O fator das cinco maiores (spec 143), que usa outra cesta e outra escala de peso.

## Plano de validação
`pytest -q tests/test_aceite_142.py` sem internet. Manhã e tarde do mesmo pregão, no PR de implementação, conferem as duas listas e o N. Esta spec não traz captura. O texto observado em 05/11/2026 segue como evidência, não como bug já fechado.
