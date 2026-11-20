---
id: 188
titulo: Três radares montados à mão passam a usar a tabela comum
status: ready
esforco: P
gaveta: experiência
aceite: tests/test_aceite_188.py
origem: Teste que reprova classe sem estilo
---

## Problema
Por que três cards da aba Alertas parecem de outro site? *Anomalias de Spread*, *Falso Rompimento* e *Divergência Volume/Preço* (`app/templates/index.html:655–762`, na `main` de 20/11/2026, `7d4d361`) montam a tabela e o estado vazio à mão, com classes que não têm estilo em lugar nenhum (medida da spec 187). Os outros radares da mesma aba usam `tabela_ativos`, `variacao` e `estado` de `app/templates/componentes.html`. O que o usuário vê de diferente:

1. **Números sem cor e sem alinhamento.** Em *Falso Rompimento* e *Divergência*, as colunas de percentual levam `numero`, `positivo` e `negativo`, que não têm seletor: o número sai na cor do texto, alinhado à esquerda, enquanto no *Short Squeeze* ao lado ele sai à direita, verde ou vermelho. Em *Anomalias de Spread*, o spread leva `var alta` e sai **verde**, a cor de "subiu", para um alerta de pânico incipiente.
2. **"Agora" num dia passado.** Ao abrir um pregão antigo pelo seletor de data, *Falso Rompimento* e *Divergência* sem registro dizem "Dado indisponível agora", e *Anomalias de Spread* diz "-- Sem dados". Os outros radares dizem "Sem registro neste pregão" (macro `estado('sem_registro' if is_historical else 'indisponivel')`).
3. **Vazio com outra cara.** "Nenhum falso rompimento detectado", "Nenhuma divergência detectada" e "✓ Spreads normais hoje" saem em `dado-indisponivel` e `estado normal`, sem o recuo e a cor apagada de `vazio` que os outros radares usam.

Esta é a fatia 2 do item *Teste que reprova classe sem estilo* do backlog. A spec 187 cria a lista `SEM_ESTILO_CONHECIDAS` com as 43 classes sem estilo; esta tira dela as 11 que só esses três cards usam.

**Correção de uma premissa do backlog e da spec 187.** O texto dizia que "volume em queda leva `positivo`". Conferido nos coletores, a cor fixa por coluna nunca contradiz o sinal hoje: em `app/collectors/falso_rompimento.py` o alerta só existe com `c_0 < c_1` e `v_0 > v_1` (preço sempre cai, volume sempre sobe, e as colunas levam `negativo` e `positivo`); em `app/collectors/radar_divergencia_volume.py`, só com `last_close > first_close` e volume 20% menor (preço sempre sobe, volume sempre cai, `positivo` e `negativo`). O defeito visível é a falta de estilo, não a cor trocada. Mesmo assim a cor passa a sair do sinal do valor, para não depender da regra do coletor.

## Comportamento esperado
Só muda o HTML dos três cards em `app/templates/index.html`. Os dados, os coletores, as chaves do `/api/snapshot` e a ordem das linhas ficam como estão.

| Card | Sem dado | Sem alerta | Tabela (`tabela_ativos`) |
|---|---|---|---|
| Anomalias de Spread | `estado('sem_registro' if is_historical else 'indisponivel')` | `<div class="vazio">Spreads normais hoje.</div>` | colunas *Ativo* e *Spread* (`num`); o spread é texto simples, sem `variacao` e sem cor; `id_rank` `anomalias-spread` |
| Falso Rompimento | o mesmo | `<div class="vazio">Nenhum falso rompimento detectado hoje.</div>` | colunas *Ativo*, *Variação* (`num`) e *Volume* (`num`), as duas com `variacao(texto, sinal)`; `id_rank` `falso-rompimento` |
| Divergência Volume/Preço | o mesmo | `<div class="vazio">Nenhuma divergência detectada hoje.</div>` | colunas *Alta 5d* (`num`) e *Volume* (`num`) depois de *Ativo*, as duas com `variacao`; `id_rank` `divergencia-volume` |

- O ticker vai na célula `{'tk': True, ...}`, como no *Short Squeeze* (`index.html:690–697`).
- O texto do número segue o formato de hoje: duas casas, vírgula decimal, sinal de menos quando negativo, `%` no fim (`"%.2f%%" | format(v) | replace(".", ",")`). A seta e a cor vêm do macro `variacao`, com `sinal` = 1 se o valor é maior que zero, −1 se menor, 0 se igual. O conteúdo passa pelo mesmo `| e` e `| safe` do *Short Squeeze*.
- Nenhuma classe fora do que `tabela_ativos`, `variacao`, `estado` e `vazio` já produzem entra nos três cards. Saem dos templates: `ranking`, `numero`, `positivo`, `negativo`, `dado-indisponivel`, `esq`, `dir`, `estado`, `vazia`, `normal`, `icone`.
- No teste da spec 187, `SEM_ESTILO_CONHECIDAS` perde essas 11 entradas no mesmo PR (o teste dela reprova a exceção vencida se ficarem).

## Fontes de dados
Nenhuma fonte nova. Os três cards leem o que já está gravado (`get_latest_radar_anomalias_spread_data`, `get_latest_falso_rompimento_data`, `get_latest_radar_divergencia_volume_data`). Se a fonte cair, o card mostra o `estado('indisponivel')` comum; num pregão passado sem registro, `estado('sem_registro')`.

## Cálculos
Nenhum cálculo novo; só o sinal que escolhe a cor. Exemplo de ponta a ponta, do dado como o coletor o grava até a célula:

- **Falso Rompimento.** O Yahoo entrega fechamentos em reais e volumes em unidades: D-1 fecha 20,00 com volume 1.000.000; D-0 fecha 19,50 com volume 1.800.000 e máxima acima da de D-1. O coletor grava `variacao = (19,50 − 20,00) / 20,00 × 100 = −2,5` e `var_volume = (1.800.000 − 1.000.000) / 1.000.000 × 100 = 80,0` (percentuais, não frações). Células: `<span class="var baixa">▼ -2,50%</span>` e `<span class="var alta">▲ 80,00%</span>`.
- **Divergência.** Fechamentos de 5 pregões de 10,00 a 10,50; volume médio dos 3 primeiros 1.000.000 e dos 2 últimos 600.000. O coletor grava `alta_acumulada = (10,50 − 10,00) / 10,00 × 100 = 5,0` e `var_volume = (600.000 − 1.000.000) / 1.000.000 × 100 = −40,0`. Células: `<span class="var alta">▲ 5,00%</span>` e `<span class="var baixa">▼ -40,00%</span>`.
- **Anomalias de Spread.** `spread_percent = 0,85` (percentual, como gravado). Célula `n` com o texto `0,85%`, sem `var`, sem seta e sem cor.
- **Sinal zero.** `var_volume = 0,0` sai `<span class="var neutra">■ 0,00%</span>`.

## Critérios de aceite
`tests/test_aceite_188.py`, com `exigir_spec_done("188")`, sem internet, gravando os dados com `save_radar_anomalias_spread_data`, `save_falso_rompimento_data` e `save_radar_divergencia_volume_data` no banco temporário do `conftest` e lendo `GET /` com o `TestClient` (como `tests/test_aceite_185.py`):

- [ ] Com os alertas do exemplo da seção *Cálculos*, o card *Falso Rompimento* contém `var baixa` com `▼ -2,50%` e `var alta` com `▲ 80,00%`, e as duas células têm a classe `n`; o card *Divergência Volume/Preço* contém `var alta` com `▲ 5,00%` e `var baixa` com `▼ -40,00%`.
- [ ] Com `var_volume = 0,0`, a célula sai com `var neutra` e `■`.
- [ ] O card *Anomalias de Spread* mostra `0,85%` numa célula `n` e não contém `var alta` nem `var baixa`.
- [ ] O ticker de cada linha sai numa célula `tk`.
- [ ] Com os três radares gravados sem alertas, cada card mostra o texto de vazio da tabela dentro de um `div` com a classe `vazio`.
- [ ] Em `GET /?data=<pregão passado sem registro>`, os três cards mostram "Sem registro neste pregão" e nenhum contém "agora" nem "Sem dados".
- [ ] O HTML dos três cards não contém nenhuma das 11 classes listadas em *Comportamento esperado* (procurar pelo token dentro de `class="..."`, não pelo texto).
- [ ] `SEM_ESTILO_CONHECIDAS` de `tests/test_classes_com_estilo.py` não tem nenhuma das 11 e tem no máximo 32 entradas; o teste da spec 187 passa contra os arquivos reais.
- [ ] `make verify` passa.

## Invariantes de produção
- Na aba Alertas de `/`, os cards *Anomalias de Spread*, *Falso Rompimento* e *Divergência Volume/Preço* respondem dentro de uma `<table>` com `<tbody data-rank="...">`, como os outros radares, ou com um `div.vazio`.
- Toda célula de percentual com seta nesses cards tem a cor do próprio sinal: `▲` com `var alta`, `▼` com `var baixa`.
- O spread de *Anomalias de Spread* nunca sai verde.
- `/api/snapshot` responde 200 com as mesmas chaves e os mesmos valores de antes (`paineis.falso_rompimento`, `paineis.divergencia_volume`, `paineis.anomalias_spread`).
- Em 360 px, os três cards não fazem a página rolar para o lado (`make telas` sem `PROBLEMA:`).

## Fora do escopo
- Depende da spec 187 (`done`): sem a lista `SEM_ESTILO_CONHECIDAS`, a parte de encolher a lista não tem onde ser feita. Se a 187 não estiver `done`, a entrega espera.
- As outras 32 classes da lista, entre elas `badge`, `badge-positivo`, `badge-negativo` e `status-neutro` do `/consultor`: seguem no item *Teste que reprova classe sem estilo* da Fila do `docs/BACKLOG.md`.
- Mudar os critérios dos coletores, a ordem, o número de alertas (3) ou os textos de descrição dos cards.
- Barras (`barra`) nas células: nenhum dos três cards tem hoje.
- O radar indisponível dizer a última falha da fonte (item *O radar vazio diz há quanto tempo e por quê* do backlog).
