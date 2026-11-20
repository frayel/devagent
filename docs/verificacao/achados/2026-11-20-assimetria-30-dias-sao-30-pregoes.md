---
id: 2026-11-20-assimetria-30-dias-sao-30-pregoes
severidade: media
painel: Assimetria Risco/Retorno (app/collectors/assimetria_risco_retorno.py)
status: aberto
visto_em: 2026-11-20T00:20-03:00
pr: 991
---

# O card Assimetria Risco/Retorno diz "30 dias", mas a janela é de 30 pregões (~6 semanas)

## O que acontece
O PR #991 passou a mostrar na tela o card que antes não aparecia (a rota `/` não passava `assimetria_risco_retorno` ao template). O subtítulo do card (`app/templates/index.html:811`) diz "Ações muito próximas da sua mínima de 30 dias (<=2%) e distantes da sua máxima (>=10%)".

No coletor, `app/collectors/assimetria_risco_retorno.py:56-69` baixa `3mo` de candles diários, descarta os `None` e faz `closes_30 = valid_closes[-30:]`. São os **30 últimos pregões**, não 30 dias corridos. Com ~21 pregões por mês, a janela real é de cerca de 42 dias corridos (mais, com feriado). `min_30` e `max_30` saem dessa janela maior.

O rótulo de período não é o da janela da consulta: o usuário lê "mínima de 30 dias" e recebe a mínima de ~6 semanas. Uma ação a 1,5% da mínima de 30 pregões pode estar a mais de 2% da mínima dos últimos 30 dias corridos (e vice-versa), e entra ou sai do top 3 por causa disso.

Os rótulos das colunas também carregam um segundo número sem fonte à vista: `dist_max_pct` é `(max - atual) / atual` (quanto a ação precisa subir para chegar à máxima), mas a célula diz "X% máx" sob "Da máxima", o que se lê como queda desde a máxima.

## O que deveria acontecer
O rótulo diz o que a janela é ("30 pregões"), ou o coletor corta a janela em 30 dias corridos. A spec 065 só fala "30 dias" e "spark 30d", sem dizer pregões: a decisão é do desenvolvimento, mas texto e conta precisam concordar.

## Evidência
```
sed -n 56,69p app/collectors/assimetria_risco_retorno.py   # valid_closes[-30:]
sed -n 811p app/templates/index.html                        # "mínima de 30 dias"
```
Não há teste que confira a janela contra o rótulo.

## Como reproduzir
Alimente o coletor com 45 candles diários (um por dia corrido de uma sequência com fins de semana pulados): `closes_30` cobre 30 pregões, ~42 dias corridos, e não 30.
