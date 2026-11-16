---
id: 161
titulo: O item "Painéis sem dados" de /sistema conta só as últimas 3 horas
status: ready
esforco: P
gaveta: saúde técnica
aceite: tests/test_aceite_161.py
revisada: 2026-11-16
origem: `/sistema` respeita a janela que anuncia
---

## Problema
"Nenhuma coleta vazia nas últimas 3 h" é verdade quando `/sistema` diz isso?

Não é. `estado_do_sistema()` (`app/main.py:328`) pede `get_coletas_vazias_desde(agora − 3 h)` e `get_rodadas_coleta_desde(agora − 3 h)` (`app/database.py:1463` e `:1487`), e `verificar_paineis_vazios` (`app/services/sistema.py:428`) escreve "nas últimas 3 h" (`HORAS_VAZIOS = 3`). As duas funções ignoram o `desde`: leem o snapshot `instrumentacao` do dia BRT inteiro. Às 17h, um painel que voltou vazio nas 4 rodadas das 10h às 10h45 e cheio nas 25 seguintes aparece como "1 painel vazio nas últimas 3 h", e o detalhe diz "mare (4× em 29 rodadas)". O número é do dia, o rótulo é de 3 horas, e a regra de "sempre vazio" (`vazias ≥ rodadas ≥ 3`) compara o dia inteiro: um coletor que quebrou às 14h só vira `problema` se nunca tiver dado certo desde a meia-noite, ou seja, quase nunca.

A spec 152 deixou uma gravação por rodada no snapshot do dia; a 154 somou as contagens do pregão no mesmo payload. Nenhuma das duas guardou a hora. Esta spec guarda a hora em que cada contagem caiu, com a mesma gravação única, e faz as duas funções respeitarem o `desde`.

## Comportamento esperado
- `gravar_instrumentacao_rodada(tempos, vazias, timestamp, durante_pregao=False)` (`app/database.py`) continua com 1 leitura e 1 gravação, e tudo o que grava hoje (`tempos`, `rodadas`, `vazias`, `rodadas_pregao`, `vazias_pregao`) continua igual. Ela passa a somar também, no mesmo payload, `por_hora[HH]["rodadas"][painel] += 1` para cada painel de `tempos` e `por_hora[HH]["vazias"][painel] += 1` para cada painel de `vazias`, em que `HH` é a hora BRT de `timestamp` com dois dígitos (`"00"` a `"23"`). Rodada sem medidas continua sem tocar no banco.
- `get_coletas_vazias_desde(desde)` e `get_rodadas_coleta_desde(desde)` somam `por_hora[HH]["vazias"]` e `por_hora[HH]["rodadas"]` de toda **hora cheia que começa em `desde` ou depois** (hora BRT, data incluída). Como a menor unidade guardada é a hora, a janela efetiva começa em `desde` arredondado para cima até a hora cheia: nunca conta coleta mais antiga que `desde`. Ex.: `desde` = 14h20 → contam as horas 15h, 16h, 17h.
- As duas leem os snapshots `instrumentacao` de todas as datas BRT entre `desde` e agora numa só consulta (`banco.ler_snapshots_datas`, spec 153). Às 1h BRT, com `desde` às 22h da véspera, a hora 23h da véspera conta.
- Data sem `por_hora` (snapshot gravado antes desta spec) não contribui com nada. No dia do deploy, até a primeira rodada nova, o item pode dizer "nenhuma coleta vazia nas últimas 3 h" mesmo com vazios mais cedo no dia; é o que de fato se sabe.
- `verificar_paineis_vazios`, `HORAS_VAZIOS`, os textos do item e os níveis não mudam. A regra de "sempre vazio" passa a valer sobre as rodadas da janela, como o texto já diz.
- `get_tempos_coleta_desde`, `get_coletas_vazias_count` e o critério de poda (`rodadas_pregao`, `vazias_pregao`, specs 153/154) não mudam.

## Fontes de dados
Nenhuma externa. Só o snapshot `instrumentacao` em `snapshots_paineis`. Plano B: se a leitura falhar, o `try` que já envolve as duas chamadas em `estado_do_sistema` cai em `{}`, como hoje. Se a gravação falhar, o `try` do `finally` de `_coletar` registra no log e a rodada segue.

Tamanho do payload: cada hora guarda no máximo um contador por painel em cada lista (~45 painéis). O agendador roda a cada 15 min das 9h55 às 18h15, a cada 30 min até as 20h e a cada 2 h no resto (`app/agendador.py:28-31,51`), então são até ~20 horas com chave por dia: algumas dezenas de KB de JSON no pior caso, numa linha só.

## Cálculos
Para cada painel `p` e cada hora cheia `h` (data e hora BRT) com início `≥ teto_hora(desde)`:

- `R(p) = Σ_h por_hora[h]["rodadas"][p]` e `V(p) = Σ_h por_hora[h]["vazias"][p]`, contagens inteiras de rodadas; painel ausente numa hora conta 0. Os dicionários devolvidos têm só painéis com contagem > 0.
- `teto_hora(t)` é `t` se `t` já está na hora cheia (minuto, segundo e microssegundo zero), senão a hora cheia seguinte.

Exemplo de ponta a ponta. Pregão de 16/11/2026, coleta a cada 15 min. O painel `mare` volta vazio nas 4 rodadas das 10h, 10h15, 10h30 e 10h45 BRT e cheio em todas as outras; `ibovespa` cheio sempre. Cada rodada chama `gravar_instrumentacao_rodada({"mare": 1.0, "ibovespa": 2.0}, vazias, timestamp)` com `vazias = ["mare"]` nas quatro primeiras e `[]` nas demais.

Payload depois da rodada das 17h00 BRT (rodadas das 10h00 às 17h00: 29), só a parte nova:

```
"por_hora": {
  "10": {"rodadas": {"mare": 4, "ibovespa": 4}, "vazias": {"mare": 4}},
  "11": {"rodadas": {"mare": 4, "ibovespa": 4}, "vazias": {}},
  ... "12" a "16" iguais a "11" ...
  "17": {"rodadas": {"mare": 1, "ibovespa": 1}, "vazias": {}}
}
```

e `rodadas = {"mare": 29, "ibovespa": 29}`, `vazias = {"mare": 4}`, como hoje.

`/sistema` às 17h05 BRT: `desde` = 14h05, `teto_hora` = 15h. Contam as horas 15, 16 e 17: `R = {"mare": 9, "ibovespa": 9}`, `V = {}`. Item: `ok`, "nenhuma coleta vazia nas últimas 3 h". Hoje o mesmo instante mostra `atencao`, "1 painel vazio nas últimas 3 h", detalhe "mare (4× em 29 rodadas)".

Mesmo dia, `/sistema` às 11h05 BRT (rodadas das 10h00 às 11h00: 5): `desde` = 8h05, `teto_hora` = 9h. Contam as horas 9 (sem chave), 10 e 11: `R = {"mare": 5, "ibovespa": 5}`, `V = {"mare": 4}`. Item: `atencao`, "1 painel vazio nas últimas 3 h", detalhe "mare (4× em 5 rodadas)", igual a hoje.

Coletor quebrado. Se a partir das 14h00 `mare` voltar vazio em toda rodada, às 17h05 contam as horas 15 a 17: `R = {"mare": 9, ...}`, `V = {"mare": 9}`, `9 ≥ 9` e `9 ≥ 3` → `problema`, "1 sempre vazio: mare". Hoje, com o dia inteiro (`V = 4 + 13 = 17` de `R = 29`: as 4 rodadas das 10h mais as 13 das 14h00 às 17h00), fica em `atencao`.

Virada do dia. 17/11/2026 às 1h10 BRT, com rodadas (a cada 2 h) às 23h de 16/11 e à 1h de 17/11, as duas com `mare` vazio: `desde` = 22h10 de 16/11, `teto_hora` = 23h de 16/11. Contam 23h de 16/11 e 0h e 1h de 17/11: `R = {"mare": 2, ...}`, `V = {"mare": 2}`. Item `atencao` (2 rodadas, abaixo do mínimo de 3 para "sempre vazio").

## Critérios de aceite
- [ ] `tests/test_aceite_161.py`, com `exigir_spec_done("161")`, num SQLite temporário:
  - as 29 rodadas do exemplo, gravadas com os timestamps BRT das 10h00 às 17h00, deixam `por_hora` exatamente como o exemplo diz, hora a hora, e `rodadas` e `vazias` como hoje;
  - `get_coletas_vazias_desde` e `get_rodadas_coleta_desde` com `desde` = 16/11/2026 14h05 BRT devolvem `{}` e `{"mare": 9, "ibovespa": 9}`; com 8h05 BRT, nas 5 primeiras rodadas, `{"mare": 4}` e `{"mare": 5, "ibovespa": 5}`;
  - `desde` exatamente na hora cheia (15h00) conta a hora 15; `desde` às 15h00m01s não conta;
  - o cenário do coletor quebrado, passado a `verificar_paineis_vazios(V, 3, R)`, dá `problema` e "1 sempre vazio: mare";
  - o cenário da virada do dia devolve `V = {"mare": 2}`, lendo as duas datas;
  - snapshot de uma data sem `por_hora` (payload com só `tempos`, `rodadas` e `vazias`) devolve `{}` nas duas funções;
  - `gravar_instrumentacao_rodada` continua com 1 leitura e 1 gravação (espião como em `tests/test_aceite_152.py`).
- [ ] O teste não depende da hora real (lição do relatório de 16/11 02h40): as duas funções ganham o parâmetro opcional `agora: datetime | None = None` (padrão: `datetime.now(timezone.utc)`), que só define a última data BRT a ler, e o teste o passa explicitamente.
- [ ] `tests/test_aceite_152.py`, `tests/test_aceite_153.py`, `tests/test_aceite_154.py`, `tests/test_sistema.py` e `tests/test_instrumentacao.py` continuam verdes sem mudar expectativa.
- Arquivos tocados: `app/database.py`, `app/main.py` (passa o `agora` que já calcula) e o novo `tests/test_aceite_161.py`. Medido com `grep -rl "get_coletas_vazias_desde\|get_rodadas_coleta_desde\|gravar_instrumentacao_rodada" app tests`: 3 de código (`app/database.py`, `app/main.py`, `app/agendador.py`, este sem mudança) e 2 de teste (`tests/test_aceite_152.py`, `tests/test_aceite_154.py`), que não mudam.

## Invariantes de produção
- `GET /api/sistema` (com a senha) continua com o item "Painéis sem dados" no grupo "Coleta".
- Depois da primeira rodada pós-deploy, o snapshot `instrumentacao` do dia tem `por_hora`, e para todo painel `p` a soma de `por_hora[h]["rodadas"][p]` sobre as horas do dia é no máximo `rodadas[p]` (igual, nos dias inteiros depois do deploy); o mesmo para `vazias`.
- O número de rodadas que o detalhe do item mostra ("N× em M rodadas") nunca passa de 13. A janela efetiva vai de `teto_hora(desde)` até agora, no máximo 3 h com as duas pontas incluídas, e o agendador espera 15 min depois do fim de cada rodada: 3 h ÷ 15 min + 1 = 13 (caso de `/sistema` aberto exatamente na hora cheia, com rodadas em :00, :15, :30, :45). Fora desse caso, até 12.

## Fora do escopo
- `get_tempos_coleta_desde` (rótulo "24 h", lê o último valor do dia BRT). Fica no backlog como item próprio, junto da "duração de parede da rodada".
- Mudar `HORAS_VAZIOS`, os textos ou os níveis do item.
- Reconstruir a contagem por hora dos snapshots antigos: eles não têm a hora.
- Registrar o painel "escondido" por lista vazia (item próprio do backlog, pré-requisito da rodada de poda).
- Remover `rodadas` e `vazias` do dia: o critério de poda e `get_coletas_vazias_count` ainda os leem.

## Revisão
Revisada em 16/11/2026. Conferido: `get_coletas_vazias_desde` e `get_rodadas_coleta_desde` (`app/database.py:1463`, `:1487`) ignoram o `desde` e leem o dia BRT; nenhum código ou spec guarda `por_hora`; `ler_snapshots_datas` existe (`app/banco.py:573`); `tests/test_aceite_152.py` e `tests/test_aceite_154.py` comparam chaves do payload uma a uma, então a chave nova não os quebra; nenhum teste substitui as duas funções, então o novo parâmetro `agora` não quebra mock. Corrigido: no cenário do coletor quebrado, a contagem do dia inteiro é `V = 17`, não 16; a invariante de rodadas na janela é 13, não 12 (a janela inclui a hora cheia de início e o instante atual). As rodadas do agendador não caem em minutos redondos (o intervalo conta do fim da rodada anterior); os timestamps em :00/:15/:30/:45 do exemplo são só do teste.

