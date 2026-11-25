---
id: 196
titulo: A ação média do dia contra o Ibovespa
status: done
esforco: P
gaveta: capacidade nova
aceite: tests/test_aceite_196.py
origem: Ibovespa sombra (pesos iguais)
revisada: 2026-11-25
---

## Problema
O Ibovespa subiu 1% hoje. A ação típica também subiu, ou foram só VALE3, PETR4 e ITUB4 que levaram o índice? O card *Dispersão* diz quantas ações subiram (o "quantas"), e o *Fator Peso Pesado* diz quanto as cinco mais pesadas deram ao índice (o "quem"). Nenhum card diz **quanto subiu a ação média**, com todas pesando o mesmo, e a que distância isso fica do índice. Essa distância mede o quanto o dia é dos pesos pesados: um índice de +1,00% com a ação média em +0,30% é um dia muito diferente de um índice de +1,00% com a ação média em +1,20%, e quem só olha o número do Ibovespa não vê a diferença.

O coletor de maiores altas e baixas (`app/collectors/highlights.py`) já calcula a variação do dia de cada uma das 30 ações da lista `TICKERS`, mas grava só as cinco maiores altas, as cinco maiores baixas e as contagens (`maiores_altas_baixas`, em `app/database.py:355`). A média se perde a cada rodada. Esta spec é a primeira fatia do item *Ibovespa sombra (pesos iguais)* do backlog: o número de hoje, no card que já usa a mesma amostra sem ponderação.

A pergunta: **a ação média da amostra subiu mais ou menos que o Ibovespa hoje, e por quanto?**

## Comportamento esperado
1. **O coletor guarda a média.** `fetch_yfinance` calcula a média simples de `change_percent` das ações de `parsed_results` (as aceitas; ficam fora as `em_revisao` e as ausentes, como já ficam das contagens) e grava dois campos novos no payload de `maiores_altas_baixas`: `media_simples_pct` (float, em **percentual**, como `change_percent`) e `media_simples_n` (int, quantas ações entraram na média). Sem ação aceita, os dois ficam `None`. `HighlightsData` ganha os dois campos com padrão `None`; `get_latest_highlights_data` os lê com `payload.get(...)`, para os snapshots antigos, que não os têm, continuarem legíveis.
2. **O card *Dispersão* ganha uma linha**, abaixo da legenda "N subiram · M caíram", no mesmo card (`app/templates/index.html`, o `painel("Dispersão", ...)` da linha 162), sem mudar o gauge, o tamanho (`span-4`) nem as classes do card:
   - com a comparação disponível (item 4): `Ação média: +0,30% · Ibovespa: +1,00%` e, numa segunda linha, a diferença e a leitura: `Diferença: −0,70 p.p. · o índice foi além da ação média`;
   - só com a média (Ibovespa indisponível, em revisão ou de outro horário): `Ação média: +0,30% (28 ações)`, sem a diferença e sem leitura;
   - sem a média (`media_simples_pct` `None`, inclusive em snapshot antigo): a linha não aparece, e o resto do card fica como hoje.
   Os números seguem o padrão brasileiro com sinal e duas casas (`+0,30%`, `−0,70 p.p.`), com a seta e a cor de alta e baixa da macro `variacao` de `componentes.html` na média e na diferença.
3. **A leitura tem três textos fixos**, pela diferença `d = média − Ibovespa`, em pontos percentuais:
   - `d ≤ −0,50`: `o índice foi além da ação média` (os pesos pesados puxaram para cima, ou seguraram a queda menos que o resto);
   - `d ≥ +0,50`: `a ação média foi além do índice`;
   - entre os dois: `índice e ação média andaram juntos`.
   O limiar de 0,50 p.p. é uma escolha de leitura, não uma estatística, e aparece no texto do método.
4. **Quando comparar.** A diferença só é mostrada quando as três condições valem: o Ibovespa da página tem variação (`variacao_indisponivel` falso), a variação não está em revisão (`revisao_variacao` falso) e os carimbos das duas coletas (`ibovespa` e `maiores_altas_baixas`) estão a no máximo 20 minutos um do outro. As duas saem da mesma rodada do agendador (`app/agendador.py:297-298`), de 15 em 15 minutos no pregão; 20 minutos aceita a mesma rodada e recusa a mistura de pregões. A conta da comparação fica numa função pura em `app/services/highlights.py` (sugestão: `comparar_com_ibovespa(media_pct, n, ibov_pct, ibov_ts, media_ts, ibov_valida)`), chamada pela rota `/` com os dados que ela já monta.
5. **Método à vista.** O texto de ajuda do card *Dispersão* (terceiro argumento de `painel(...)`) ganha uma frase: "Ação média: média simples da variação do dia das ações da amostra, todas com o mesmo peso, comparada à variação do Ibovespa da mesma rodada. Diferença em pontos percentuais; a partir de 0,50 p.p., para cima ou para baixo, o card diz quem foi além." Fonte e horário são os do card, que já os mostra.
6. **Data passada.** Com `?data=`, a linha usa o payload de `maiores_altas_baixas` e a leitura do Ibovespa daquele pregão, como o card já faz. Pregão gravado antes desta spec não tem `media_simples_pct`: a linha não aparece, sem erro. A regra dos 20 minutos do item 4 vale também aqui, com os carimbos gravados nos dois payloads daquele pregão; se eles se afastam mais que isso, a linha mostra só a média, sem diferença (a degradação conservadora, nunca uma comparação de rodadas diferentes).
7. **`/api/snapshot`.** `paineis.altas_baixas` ganha a chave `acao_media`: `{"media_pct": 0.30, "amostra": 4, "ibovespa_pct": 1.00, "diferenca_pp": -0.70, "leitura": "o índice foi além da ação média"}`, com `ibovespa_pct`, `diferenca_pp` e `leitura` `null` quando a comparação do item 4 não vale, e a chave inteira `null` quando não há média. Os números vão sem arredondar no JSON; o exemplo acima usa os do item *Cálculos*. A chave `dispersao` não muda.

## Fontes de dados
Nenhuma nova. As variações já coletadas por `app/collectors/highlights.py` (MetaTrader 5, com o Yahoo `spark` de reserva) e a variação do Ibovespa do snapshot `ibovespa`. Nenhum pedido novo à rede.

Plano B: se o coletor de maiores altas e baixas falha, o card *Dispersão* já mostra `indisponivel` e a linha nova não existe; se só o Ibovespa falha, a linha mostra a média sem comparação (item 2).

## Cálculos
- `change_percent` de cada ação já sai do coletor em **percentual**: `(preço − fechamento anterior) / fechamento anterior × 100`.
- `media_simples_pct = soma(change_percent das aceitas) / n`, com `n = len(parsed_results)`.
- `ibov_pct` é o `variation_pct` de `get_ibovespa_view_data`, também em percentual: `(atual − fechamento anterior) / fechamento anterior × 100`.
- `diferenca_pp = media_simples_pct − ibov_pct`. Percentual menos percentual dá ponto percentual; não se divide nem multiplica por 100 em nenhum passo.

**Exemplo de ponta a ponta.** Quatro ações aceitas, todas com fechamento anterior de R$ 90,00 (o `spark_com_precos` de `tests/test_highlights.py`):

| Ação | Preço | change_percent |
|---|---|---|
| A | 91,80 | (91,80 − 90) / 90 × 100 = +2,00 |
| B | 90,90 | +1,00 |
| C | 89,55 | −0,50 |
| D | 88,83 | −1,30 |

`media_simples_pct = (2,00 + 1,00 − 0,50 − 1,30) / 4 = 1,20 / 4 = +0,30`, `media_simples_n = 4`.

Ibovespa: fechamento anterior 129.000 pontos, atual 130.290. `ibov_pct = 1.290 / 129.000 × 100 = +1,00`.

`diferenca_pp = 0,30 − 1,00 = −0,70` ≤ −0,50 → leitura `o índice foi além da ação média`.

Na tela: `Ação média: +0,30% · Ibovespa: +1,00%` e `Diferença: −0,70 p.p. · o índice foi além da ação média`.

Escala errada aparece logo: se `change_percent` fosse tratado como fração, a média sairia `+0,003%`; se o Ibovespa entrasse em fração, a diferença sairia `+0,29 p.p.` e a leitura viraria "andaram juntos".

## Critérios de aceite
- [ ] `tests/test_aceite_196.py`, com `exigir_spec_done("196")`, sem internet (respx e os fixtures de `tests/test_highlights.py`):
  - **média gravada:** com o `spark` das quatro ações do exemplo, `fetch_yfinance()` devolve `media_simples_pct` a menos de 0,001 de `0.30` e `media_simples_n == 4`; com uma quinta ação a +20% que a segunda fonte não confirma (vai para `em_revisao`; a segunda fonte é simulada com `monkeypatch` de `app.collectors.highlights.consultar_segunda_fonte`, como em `tests/test_aceite_135.py`), a média e o `n` não mudam;
  - **comparação pura:** a função do item 4 devolve, para média `0.30`, Ibovespa `1.00` e carimbos a 3 minutos, diferença `-0.70` e a leitura `o índice foi além da ação média`; para `1.20` e `1.00`, `índice e ação média andaram juntos`; para `1.60` e `1.00`, `a ação média foi além do índice`; com carimbos a 25 minutos, ou com o Ibovespa em revisão, ou com a variação indisponível, sem diferença e sem leitura;
  - **tela:** com os snapshots `maiores_altas_baixas` e `ibovespa` do exemplo gravados na mesma rodada, o HTML de `GET /` contém, dentro do card *Dispersão*, `+0,30%`, `+1,00%`, `0,70 p.p.` e `o índice foi além da ação média`;
  - **sem comparação:** com o snapshot `ibovespa` 25 minutos antes, o card contém `Ação média: +0,30% (4 ações)` e não contém `p.p.`;
  - **snapshot antigo:** um payload de `maiores_altas_baixas` sem os campos novos lê sem erro, `GET /` responde 200 e o card não contém `Ação média`;
  - **snapshot:** `GET /api/snapshot` traz `paineis.altas_baixas.acao_media` com `media_pct`, `amostra`, `ibovespa_pct`, `diferenca_pp` e `leitura` iguais aos do exemplo, e `null` nos três últimos no caso sem comparação.
- [ ] `tests/test_highlights.py` continua verde sem mudar asserções.
- [ ] `make telas` sem `PROBLEMA:` novo: em 360 px as duas linhas novas cabem no card *Dispersão* sem vazar nem cortar.

## Invariantes de produção
- Em `/api/snapshot`, quando `paineis.altas_baixas.acao_media.diferenca_pp` não é `null`, ele é igual a `media_pct − ibovespa_pct` com erro de no máximo 0,01, e `ibovespa_pct` está a no máximo 0,05 p.p. de `paineis.ibovespa.variacao_pct` do mesmo snapshot.
- `acao_media.amostra` é no máximo 30 e pelo menos `dispersao.em_alta + dispersao.em_baixa` (a diferença são as ações estáveis, com variação zero).
- `acao_media.media_pct` fica entre a menor e a maior variação das ações publicadas em `altas_baixas` (a última das maiores baixas e a primeira das maiores altas).
- A `leitura` é uma das três frases do item 3 e bate com o sinal e o tamanho de `diferenca_pp`.

## Fora do escopo
- A linha do "Ibovespa de pesos iguais" no gráfico do Ibovespa, com a série dos últimos 30 pregões, e a distância acumulada entre os dois: fica no item *Ibovespa sombra (pesos iguais)* do backlog, como fatia 2. Ela pede guardar a média de cada pregão fechado.
- Ampliar a amostra para as ~85 ações da carteira teórica, ou trocar a lista `TICKERS` do coletor.
- Mediana, desvio ou qualquer outra medida além da média simples.
- Levar a leitura para a manchete (`app/services/manchete.py`).
- Mudar o gauge, as contagens ou a `dispersao` do snapshot.
