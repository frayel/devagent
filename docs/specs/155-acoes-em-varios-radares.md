---
id: 155
titulo: As ações que vários radares apontam ao mesmo tempo
status: done
esforco: M
gaveta: capacidade nova
aceite: tests/test_aceite_155.py
depende_de: 150
revisada: 2026-11-15
---

## Problema
O usuário pergunta: "qual ação aparece em mais de um radar agora, e em quais?"

A aba Alertas tem 20 radares (`RADARES` em `app/services/radares.py`). Cada um é lido sozinho. Quando PETR4 aparece no Radar de volume, na Variação Súbita e no Radar de Faca Caindo, o usuário só descobre se percorrer os cards e lembrar dos tickers. O sistema já tem os 20 resultados na mesma requisição (`index()` monta o contexto e chama `radares_servico.resumo`), mas nunca os cruza.

Nenhum dos concorrentes do `PRODUTO.md` (Status Invest, Investing, TradingView) cruza os próprios alertas. A ideia está no backlog desde a rodada "Passo 7 - 2026-11-15 3".

## Comportamento esperado
Um card novo, **"Em vários radares"**, no topo da aba Alertas Intraday (antes dos cards dos radares), com a macro `painel` de `app/templates/componentes.html`, classe `span-12 visao-micro alertas`.

- Lista as ações que aparecem em **2 ou mais** radares que estão no estado `com_alertas` (de `radares.classificar`). Uma linha por ação, com:
  - o ticker;
  - o número de radares, no formato `3 radares`;
  - os nomes dos radares (o título da tupla de `RADARES`), separados por ` · `, na ordem de `RADARES`.
- Ordem: número de radares, do maior para o menor; empate pelo ticker em ordem alfabética.
- No máximo 10 linhas. Se houver mais, a última linha diz `+N ações em 2 radares` (ou o número correspondente), sem listar.
- Abaixo da lista, uma linha de contexto: `de R radares lidos agora`, onde R é a quantidade de radares em `com_alertas` ou `sem_alertas` (os frescos). Radar `desatualizado` ou `indisponivel` não conta em R nem na confluência.
- **ⓘ (método):** "Conta, para cada ação, quantos radares com coleta em dia a citam agora. Mínimo de 2 radares. Radares desatualizados (coleta com mais de 30 minutos durante o pregão) ou indisponíveis ficam de fora. Alguns radares medem coisas parecidas (as três exaustões, por exemplo) e podem citar a mesma ação pelo mesmo motivo: o número de radares não é uma probabilidade nem uma recomendação."
- **Rodapé:** fonte `os radares desta aba` e o horário da coleta **mais antiga** entre os radares que entraram em alguma linha (conservador: a linha só é tão nova quanto o seu dado mais velho), no formato de `carimbo.formatar`.
- **Sem confluência** (nenhuma ação em 2 ou mais radares, ou nenhum radar fresco): o card **não é renderizado**. Não há frase de vazio (spec 150). Em data histórica vale a mesma regra, com os payloads daquela data e sem o teste de desatualizado (como `classificar` já faz com `is_historical`).
- Em 390 px, cada linha quebra os nomes dos radares abaixo do ticker, sem rolagem horizontal.
- A aba "Só Sinais" não muda nesta spec.

### Exemplo de ponta a ponta
Pregão de 16/11/2026, `agora` = 10:45 BRT (13:45 UTC). Payloads como os coletores gravam (item com chave `ticker`, já sem `.SA`; o Radar de Congestionamento vem como objeto com `.alertas`, cujos itens têm o atributo `ticker`):

| Radar | Coleta (BRT) | Lista | Estado |
|---|---|---|---|
| Radar de volume | 10:30 | `[{"ticker": "PETR4"}, {"ticker": "VALE3"}]` | com_alertas |
| Variação Súbita | 10:30 | `[{"ticker": "PETR4"}, {"ticker": "MGLU3"}, {"ticker": "petr4.SA"}]` | com_alertas |
| Exaustão de Queda | 10:40 | `[{"ticker": "MGLU3"}]` | com_alertas |
| Radar de Faca Caindo | 10:20 | `[{"ticker": "PETR4"}]` | com_alertas |
| Compradores de Fundo | 10:00 | `[{"ticker": "VALE3"}]` | desatualizado (45 min > 30) |
| Scanner de Capitulação | — | `None` | indisponivel |
| os outros 14 | 10:30 | `[]` | sem_alertas |

Normalização do ticker: `strip()`, maiúsculas, sem o sufixo `.SA`. `petr4.SA` vira `PETR4`, e a Variação Súbita conta uma vez só para PETR4.

Contagem:
- PETR4: Radar de volume, Variação Súbita, Radar de Faca Caindo → 3 radares. Coletas 10:30, 10:30, 10:20 → a mais antiga é 10:20.
- MGLU3: Variação Súbita, Exaustão de Queda → 2 radares. Coletas 10:30, 10:40.
- VALE3: Radar de volume (fresco) e Compradores de Fundo (desatualizado, fora) → 1 radar → não entra.

R = 4 com_alertas + 14 sem_alertas = 18.

O card mostra:

```
PETR4   3 radares   Radar de volume · Variação Súbita · Radar de Faca Caindo
MGLU3   2 radares   Variação Súbita · Exaustão de Queda
de 18 radares lidos agora
Fonte os radares desta aba · 16/11/2026 10:20 BRT
```

O rodapé usa 10:20: é a coleta mais antiga entre os quatro radares que entraram em alguma linha (volume 10:30, Variação Súbita 10:30, Faca Caindo 10:20, Exaustão de Queda 10:40).

## Fontes de dados
Nenhuma fonte nova e nenhuma coleta nova. O cálculo lê os payloads que `index()` já põe no contexto para os 20 radares, com o mesmo `classificar` da spec 150. O item de alerta pode ser `dict` (chave `ticker`) ou objeto (atributo `ticker`); a função `_campo` de `app/services/radares.py` já trata os dois. Item sem ticker (ausente, `None` ou texto vazio) é ignorado.

Plano B: um radar que falhou cai em `indisponivel` ou `desatualizado` e só sai da contagem; o card continua com os outros. Se nenhum radar estiver fresco, o card não aparece e o resto da aba funciona como hoje.

## Cálculos
Uma função pura nova em `app/services/radares.py`, por exemplo `confluencia(contexto, agora, is_historical) -> dict`:

1. Para cada `(chave, nome, campo)` de `RADARES`, `estado, ts = classificar(contexto.get(chave), chave, agora, is_historical)`.
2. Se `estado` for `com_alertas`, monte o **conjunto** de tickers normalizados da lista `campo` daquele payload (um radar conta no máximo uma vez por ação) e acrescente `nome` e `ts` a cada ticker.
3. `lidos` = quantidade de radares em `com_alertas` ou `sem_alertas`.
4. Linhas = tickers com 2 ou mais radares, ordenadas por `(-len(radares), ticker)`; as 10 primeiras vão para `acoes`, e o resto vira `excedentes` (quantidade).
5. `horario` = o menor `ts` entre os radares que aparecem em pelo menos uma linha (todas as linhas, não só as 10 exibidas). `ts` sem fuso é tratado como UTC antes de comparar (como `carimbo.desatualizado` faz), para não misturar `datetime` com e sem fuso; radar com `ts` `None` não entra no mínimo. `None` se não houver linha ou se nenhum radar citado tiver `ts`; aí o rodapé mostra só a fonte.

Saída: `{"acoes": [{"ticker": str, "radares": [nome, ...]}], "excedentes": int, "lidos": int, "horario": datetime | None}`.

`index()` passa o resultado ao template como `confluencia`, ao lado de `radares`.

`/api/snapshot` hoje só lê os payloads de parte dos 20 radares (não lê as três exaustões, absorção cruzada, liquidez e outros). Para `paineis.confluencia_radares`, ele lê os 20 payloads pelos mesmos getters que `index()` usa, no mesmo `lendo_pregao` e `req_snapshot_cache_ctx` que já abrem a função, e chama a mesma `confluencia`. A saída no JSON é `{"acoes": [...], "excedentes": int, "lidos": int, "horario": str | null}`, com `horario` em ISO 8601.

## Critérios de aceite
- [ ] Com o fixture do exemplo e `agora` congelado em 16/11/2026 10:45 BRT, a página `/` contém o card "Em vários radares" com `PETR4`, `3 radares`, `MGLU3`, `2 radares` e `de 18 radares lidos agora`, e PETR4 vem antes de MGLU3 no HTML.
- [ ] No mesmo fixture, o texto do card não contém `VALE3` (o segundo radar dele está desatualizado), e o rodapé traz `10:20`.
- [ ] `confluencia` com o fixture do exemplo devolve `lidos == 18`, `excedentes == 0` e, para PETR4, os radares na ordem de `RADARES`: `["Radar de volume", "Variação Súbita", "Radar de Faca Caindo"]`. A Variação Súbita aparece uma vez, mesmo com `PETR4` e `petr4.SA` na lista.
- [ ] Um item objeto (o Radar de Congestionamento como `RadarCongestionamentoData` com `.alertas`) entra na contagem como um item `dict`.
- [ ] Com 12 tickers, cada um em 2 radares: o card mostra 10 linhas e `+2 ações em 2 radares`.
- [ ] Com os 20 radares vazios e frescos, ou com só uma ação por radar sem repetição, o HTML não contém "Em vários radares".
- [ ] O mesmo fixture com `?data=` de uma data histórica (payloads com `timestamp` de 3 horas antes): Compradores de Fundo **não** fica de fora por idade, e VALE3 aparece com `2 radares`.
- [ ] `GET /api/snapshot` traz `paineis.confluencia_radares` com `acoes` e `lidos` iguais aos do card no fixture do exemplo; sem confluência, `acoes` é `[]`.
- [ ] `tests/test_aceite_155.py` usa `exigir_spec_done("155")`, congela `agora` e não abre rede (pode reaproveitar o mapa `GETTERS` de `tests/test_aceite_150.py`).

## Invariantes de produção
- Toda ação listada no card "Em vários radares" aparece, na mesma página, em pelo menos dois cards de radar visíveis (não escondidos), e os nomes listados na linha dela são exatamente esses cards.
- O número de radares de cada linha é igual à quantidade de nomes listados nela, e é 2 ou mais.
- Nenhum radar citado no card aparece, na mesma página, na seção "Sem alertas" como desatualizado ou indisponível.
- O horário do rodapé do card não é mais recente que o horário de coleta de nenhum dos radares citados.
- `paineis.confluencia_radares.lidos` está entre 0 e 20.

## Fora do escopo
- Peso por radar, nota composta ou qualquer leitura de "comprar/vender" a partir da contagem. O card conta citações; não recomenda.
- Agrupar radares parecidos (as três exaustões) para descontar a correlação. Fica registrado no ⓘ e no backlog.
- Histórico: "quantas vezes PETR4 esteve em 3 radares nos últimos 10 pregões" e o que aconteceu depois. É a segunda fatia da ideia (backlog).
- Link do ticker para o card de cada radar ou para a ficha da ação.
- Mudar a aba "Só Sinais", a seção "Sem alertas" ou a regra de qualquer radar.
- Radares fora de `RADARES` (rankings, Inflexão de Tendência em `rankings`, anomalia de peso).

## Revisão
Revisada em 2026-11-15 contra a `main`. Conferido: `RADARES`, `classificar` e `_campo` existem em `app/services/radares.py` como a spec descreve; os 20 cards de `index.html` leem `.ticker` dos itens e nenhum corta a lista (a invariante "aparece em dois cards visíveis" vale); 16/11/2026 é pregão e 10:45 BRT está dentro do horário, com TTL de 30 min, então Compradores de Fundo às 10:00 fica desatualizado. Nada de confluência no código hoje (`grep -rn confluencia app tests` vazio) e nenhuma outra spec com o tema. Ajustes: o rodapé do exemplo ganhou o ` BRT` que `carimbo.formatar` escreve; o passo 5 dos cálculos agora diz o que fazer com `ts` sem fuso ou `None`; e o `/api/snapshot`, que hoje não lê todos os 20 payloads, passa a ter a origem dos dados e o formato do `horario` escritos.
