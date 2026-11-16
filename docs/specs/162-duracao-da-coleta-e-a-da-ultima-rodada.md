---
id: 162
titulo: A "Duração da coleta" de /sistema é a da última rodada, medida no relógio
status: ready
esforco: P
gaveta: saúde técnica
aceite: tests/test_aceite_162.py
origem: Duração de parede da rodada
---

## Problema
Quanto tempo a última rodada de coleta levou de verdade?

`/sistema` responde com o item "Duração da coleta" do grupo "Coleta": "rodada completa em X min", com os três coletores mais lentos no detalhe e `atencao` acima de 600 s (`verificar_tempo_coleta`, `app/services/sistema.py:582`). O número não é de nenhuma rodada:

- `estado_do_sistema()` pede `get_tempos_coleta_desde(agora − 24 h)` (`app/main.py:345`), mas a função (`app/database.py:1515`) ignora o `desde` e devolve `payload["tempos"]` do snapshot `instrumentacao` do dia BRT: a **última** duração de cada painel que rodou desde a meia-noite, cada uma de uma rodada diferente. `gravar_instrumentacao_rodada` substitui `tempos[painel]` só dos painéis que rodaram (`app/database.py:1427`), então os que não rodam mais depois do fechamento continuam lá, com a duração das 18h, somados às dos consultores que rodam até as 20h.
- A soma conta só o tempo dentro de `collect_and_save()`. A rodada é sequencial (`_coletar`, `app/agendador.py:190`) e, entre um coletor e outro, faz leituras de controle (`ler_snapshot` para decidir partida a frio e fechamento, uma por painel fora da janela), troca de `ContextVar` e importação; nada disso entra. A spec 152 estimou ~25 s por rodada só de idas ao banco fora da medida.
- Logo depois da meia-noite BRT, antes da primeira rodada do dia, o item diz "sem medições" (`inativo`), embora houvesse rodadas 1 h antes.

Esta spec grava, na mesma gravação única da 152, a rodada inteira (início, fim, duração de relógio e os tempos daquela rodada) e faz o item mostrar essa rodada, dizendo de que horas ela é.

## Comportamento esperado
- `_coletar` (`app/agendador.py`) guarda `inicio = datetime.now(timezone.utc)` e `t0 = time.perf_counter()` na primeira linha do corpo, antes das leituras do calendário. No `finally`, mede `duracao_parede = perf_counter() − t0` imediatamente antes de chamar `gravar_instrumentacao_rodada` e passa `inicio=inicio` e `duracao_parede=duracao_parede` como argumentos nomeados, além do que já passa. O `timestamp` continua sendo `datetime.now(timezone.utc)` no `finally`: é o fim da rodada.
- `gravar_instrumentacao_rodada(tempos, vazias, timestamp, durante_pregao=False, inicio=None, duracao_parede=None)` continua com 1 leitura e 1 gravação e continua gravando tudo o que grava hoje (`tempos`, `rodadas`, `vazias`, `por_hora`, `rodadas_pregao`, `vazias_pregao`), sem mudança. Quando `inicio` e `duracao_parede` vêm preenchidos **e** `tempos` não está vazio, ela também **substitui** no mesmo payload:
  ```
  "ultima_rodada": {"inicio": <inicio ISO 8601 UTC>, "fim": <timestamp ISO 8601 UTC>,
                    "duracao_parede": <segundos, float>, "tempos": <cópia de tempos desta rodada>}
  ```
  Rodada sem nenhuma medida continua sem tocar no banco. Rodada só com `vazias` e sem `tempos` (impossível hoje: todo painel vazio também tem tempo) não troca `ultima_rodada`. Chamadas sem os dois argumentos novos (`save_coleta_tempo`, `save_coleta_vazia`, testes antigos) não tocam em `ultima_rodada`.
- `get_tempos_coleta_desde` sai. No lugar, `get_ultima_rodada(agora: datetime | None = None) -> dict | None` (`app/database.py`) lê numa só consulta (`banco.ler_snapshots_datas`, spec 153) os snapshots `instrumentacao` da data BRT de `agora` e da véspera, e devolve o `ultima_rodada` de maior `fim`, ou `None` se nenhuma das duas datas tem a chave. `agora` padrão: `datetime.now(timezone.utc)`.
- `estado_do_sistema()` (`app/main.py`) chama `get_ultima_rodada(agora=agora)` e passa ao `montar` a rodada no lugar de `tempos`. Na falha de leitura, o `try` que já existe cai em `None`, como hoje cai em `{}`.
- `verificar_tempo_coleta(tempos, duracao_parede=None, inicio=None, fim=None)` (`app/services/sistema.py`):
  - com `duracao_parede`, o total é ele (não a soma); o resumo vira `"rodada das HHhMM em X,X min"`, com `HHhMM` = `inicio` em BRT; `quando` = `fim` (ISO 8601);
  - sem `duracao_parede`, comportamento de hoje, sem mudança (soma e `"rodada completa em X,X min"`);
  - em ambos: detalhe "Mais lentos: ..." dos três maiores de `tempos` (os da rodada), `atencao` se o total passa de 600 s, `ok` senão, `envelhece=False`; `tempos` vazio → `inativo`, "sem medições".
- `montar` passa `rodada["tempos"]`, `rodada["duracao_parede"]`, `rodada["inicio"]` e `rodada["fim"]` (convertidos de ISO) a `verificar_tempo_coleta`; com `rodada` `None`, chama `verificar_tempo_coleta({})` (→ "sem medições").

## Fontes de dados
Nenhuma externa. Só o snapshot `instrumentacao` em `snapshots_paineis`, já gravado uma vez por rodada (spec 152). Plano B: leitura falhou → o item mostra "sem medições" (`inativo`) e o resto da página segue, como hoje; gravação falhou → o `try` do `finally` de `_coletar` registra no log e a rodada segue.

Tamanho: `ultima_rodada` tem no máximo um tempo por painel da lista de `_coletar` (47), menos de 2 KB de JSON a mais no payload do dia.

## Cálculos
- `duracao_parede = perf_counter(fim) − perf_counter(início)`, em segundos de relógio monotônico, medida na mesma thread da rodada. Inclui leituras de controle, partidas a frio, gravações dos coletores e o disparo da thread do backtest; não inclui a própria gravação da instrumentação nem a espera até a próxima rodada.
- `X,X min = duracao_parede / 60`, uma casa, vírgula decimal (mesmo formato de hoje).
- Nível: `atencao` se `duracao_parede > 600` s.
- Sempre `duracao_parede ≥ Σ tempos` da mesma rodada: cada `tempos[p]` é medido com `perf_counter` dentro do intervalo `[t0, fim]`, sem sobreposição (rodada sequencial).

Exemplo de ponta a ponta. Pregão de 16/11/2026, depois do fechamento. A rodada das 18h15 BRT (21h15 UTC) rodou o fechamento de todos os painéis e deixou no snapshot do dia, entre outros, `tempos = {"ibovespa": 2.0, "mare": 1.5, "highlights": 59.0, "consultor_yahoo": 240.0, "consultor_opinioes": 30.0}` (segundos). A rodada seguinte começa às 19h00m00s BRT (`inicio` = `2026-11-16T22:00:00+00:00`). Os painéis de pregão já têm snapshot `final` e não rodam; rodam `consultor_yahoo` em 250,0 s e `consultor_opinioes` em 35,0 s (os dois, janelas `fechamento` e `continua`). As 45 leituras de controle e importações somam 6,4 s fora dos coletores. `duracao_parede = 250,0 + 35,0 + 6,4 = 291,4` s, fim às 19h04m51,4s BRT. Chamada no `finally`:

```
gravar_instrumentacao_rodada(
    {"consultor_yahoo": 250.0, "consultor_opinioes": 35.0}, [],
    datetime(2026, 11, 16, 22, 4, 51, 400000, tzinfo=timezone.utc),
    durante_pregao=False,
    inicio=datetime(2026, 11, 16, 22, 0, tzinfo=timezone.utc),
    duracao_parede=291.4,
)
```

Payload depois, só a parte nova:

```
"ultima_rodada": {"inicio": "2026-11-16T22:00:00+00:00",
                  "fim": "2026-11-16T22:04:51.400000+00:00",
                  "duracao_parede": 291.4,
                  "tempos": {"consultor_yahoo": 250.0, "consultor_opinioes": 35.0}}
```

e `tempos = {"ibovespa": 2.0, "mare": 1.5, "highlights": 59.0, "consultor_yahoo": 250.0, "consultor_opinioes": 35.0}`, como hoje.

`/sistema` às 19h10 BRT:
- Hoje: soma de `tempos` = 2,0 + 1,5 + 59,0 + 250,0 + 35,0 = 347,5 s → 347,5 / 60 = 5,79 → "rodada completa em 5,8 min", detalhe "Mais lentos: consultor_yahoo 250 s, highlights 59 s, consultor_opinioes 35 s". O `highlights` é da rodada das 18h15.
- Com a spec: 291,4 / 60 = 4,857 → "rodada das 19h00 em 4,9 min", detalhe "Mais lentos: consultor_yahoo 250 s, consultor_opinioes 35 s", `quando` = `2026-11-16T22:04:51.400000+00:00`, nível `ok`.

Virada do dia. 17/11/2026 às 0h30 BRT, sem rodada desde a meia-noite e com a última às 23h00 de 16/11 (início 23h00, 40,0 s de parede): `get_ultima_rodada` lê 17/11 (sem snapshot) e 16/11 e devolve a das 23h → "rodada das 23h00 em 0,7 min". Hoje o mesmo instante mostra "sem medições".

Lentidão real. Rodada de pregão com `Σ tempos` = 590,0 s e 25,0 s fora dos coletores: `duracao_parede` = 615,0 s → "rodada das HHhMM em 10,2 min", `atencao`. Hoje: 590,0 s → "rodada completa em 9,8 min", `ok`.

## Critérios de aceite
- [ ] `tests/test_aceite_162.py`, com `exigir_spec_done("162")`, num SQLite temporário:
  - a chamada do exemplo sobre um snapshot com os `tempos` da rodada das 18h15 deixa `ultima_rodada` exatamente como o exemplo diz e `tempos` como hoje (todas as cinco chaves);
  - `get_ultima_rodada(agora=16/11/2026 19h10 BRT)` devolve essa rodada, e `verificar_tempo_coleta` com ela dá resumo `"rodada das 19h00 em 4,9 min"`, detalhe `"Mais lentos: consultor_yahoo 250 s, consultor_opinioes 35 s"`, nível `ok` e `quando` igual ao `fim`;
  - o cenário da virada do dia devolve a rodada das 23h de 16/11 lendo as duas datas numa só chamada a `ler_snapshots_datas`, e o resumo `"rodada das 23h00 em 0,7 min"`;
  - com rodadas nas duas datas, vence a de maior `fim`;
  - snapshot sem `ultima_rodada` (payload de antes desta spec) nas duas datas → `None` → item `inativo`, "sem medições";
  - o cenário da lentidão real dá `atencao` e `"10,2 min"`;
  - `gravar_instrumentacao_rodada` sem `inicio`/`duracao_parede` não cria nem altera `ultima_rodada`; com eles e `tempos` vazio, não toca no banco;
  - `agendador._coletar()` com coletores falsos (como em `tests/test_aceite_152.py`) grava `ultima_rodada` com `duracao_parede ≥ Σ tempos`, `inicio ≤ fim` e continua com 1 leitura e 1 gravação do `instrumentacao`.
- [ ] O teste não depende da hora real: `get_ultima_rodada` recebe `agora` explícito.
- [ ] `tests/test_aceite_152.py`, `tests/test_aceite_153.py`, `tests/test_aceite_161.py`, `tests/test_sistema.py`, `tests/test_sistema_envelhece.py` e `tests/test_instrumentacao_coleta_tempo.py` continuam verdes sem mudar expectativa. Em `tests/test_aceite_154.py`, o espião de `gravar_instrumentacao_rodada` (linha 123) passa a aceitar os dois argumentos nomeados novos (`**_`); a asserção (`durante_pregao`) não muda.
- Tamanho, medido com `grep -rl "get_tempos_coleta_desde\|verificar_tempo_coleta\|gravar_instrumentacao_rodada" app tests`: 4 de código (`app/agendador.py`, `app/database.py`, `app/main.py`, `app/services/sistema.py`) e 5 de teste (`test_aceite_152`, `test_aceite_154`, `test_aceite_161`, `test_sistema`, `test_sistema_envelhece`), dos quais só o `test_aceite_154` muda (a assinatura do espião), mais o novo `tests/test_aceite_162.py`.

## Invariantes de produção
- `GET /api/sistema` (com a senha) continua com o item "Duração da coleta" no grupo "Coleta".
- Com a coleta ligada e depois da primeira rodada pós-deploy, o resumo do item começa por `"rodada das "` seguido de `HHhMM`, e o `quando` do item fica no máximo 3 h antes de agora (o maior intervalo do agendador é 2 h, mais a duração da rodada).
- A hora do resumo é anterior ao `quando` e no máximo 20 min antes dele (nenhuma rodada medida passou de 10 min; o dobro dá folga sem esconder rodada travada).
- No snapshot `instrumentacao` do dia, `ultima_rodada.duracao_parede ≥ Σ ultima_rodada.tempos`, e `fim − inicio` difere de `duracao_parede` em no máximo 1 s.
- Todo painel de `ultima_rodada.tempos` também está em `tempos` do mesmo snapshot, com o mesmo valor.

## Fora do escopo
- Remover `tempos` do payload do dia: os testes da 152 e da 154 o leem, e o critério de poda pode vir a usá-lo (item "Rodada de poda" do backlog).
- Histórico de durações por rodada ou gráfico de tendência: só a última rodada.
- Mudar o limite de 600 s, o intervalo do agendador ou a ordem dos coletores.
- Medir o tempo da gravação da instrumentação (ela é o próprio registro).
- Paralelizar ou acelerar a coleta (item "Medir quanto de série a rodada baixa repetido" e "Rate limit sem travar o loop" do backlog).
