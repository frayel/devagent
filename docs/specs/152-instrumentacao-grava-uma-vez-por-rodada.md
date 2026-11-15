---
id: 152
titulo: A instrumentação da coleta grava uma vez por rodada
status: ready
esforco: P
gaveta: saúde técnica
aceite: tests/test_aceite_152.py
---

## Problema
Quanto da rodada de coleta é gasto só para registrar a própria rodada?

Hoje, para cada coletor que roda, `_coletar` (`app/agendador.py`, perto da linha 410) chama `save_coleta_tempo`, e, se a coleta voltou vazia, também `save_coleta_vazia` (`app/database.py`, linhas 1400 a 1435). Cada chamada faz um `ler_snapshot("instrumentacao", hoje)` e um `gravar_snapshot` do payload inteiro: duas idas ao banco por chamada. Fora de uma requisição HTTP não há o cache de `_req_snapshot_cache`, então a leitura vai ao Postgres de verdade.

## Medidas (15/11/2026, rodada de manutenção)
- `/api/sistema` de produção às ~01h de Brasília: o diagnóstico do banco fez 2 consultas em **1093 ms** (já com a conexão do pool) e a média para abrir conexão é **1193 ms**. Ou seja, cada ida ao Postgres de produção custa na ordem de 300 a 500 ms.
- `_coletar` percorre 46 coletores. Durante o pregão, cerca de 42 deles (janela `pregao`) rodam a cada 15 min.
- Idas ao banco só para instrumentação, por rodada de pregão: 42 × 2 = **84**, mais 2 por coleta vazia. A 300 ms cada, são cerca de **25 s por rodada** que não aparecem na "Duração da coleta" de `/sistema` (4,8 min), porque `duracao` é medida antes do `save_coleta_tempo`.
- `tests/test_instrumentacao_coleta_tempo.py` não tem nenhum `assert`: as duas funções terminam em `pass` (o primeiro consulta a tabela `instrumentacao_coleta_tempo`, que `init_db` ainda cria em `app/database.py:288` mas onde ninguém grava desde que a instrumentação foi para o snapshot, e não confere o resultado). A instrumentação hoje não tem teste que reprove.

## Comportamento esperado
- `_coletar` acumula em memória, durante a rodada, a duração de cada coletor que terminou (`tempos`) e a lista dos que voltaram vazios (`vazias`), exatamente nos mesmos pontos onde hoje chama `save_coleta_tempo` e `save_coleta_vazia`.
- No fim do laço, num `finally` (para a rodada interrompida por exceção também registrar o que já mediu), uma nova função `app.database.gravar_instrumentacao_rodada(tempos, vazias, timestamp)` faz **uma** leitura e **uma** gravação do snapshot `instrumentacao` do dia (data em BRT do `timestamp`). Falha ao gravar só gera `logger.exception`, como hoje; a rodada não morre.
- A fusão no payload é a mesma de hoje, aplicada de uma vez:
  - `tempos[painel] = duração` (substitui a anterior);
  - `rodadas[painel] += 1` para cada painel em `tempos`;
  - `vazias[painel] += 1` para cada painel em `vazias`.
- O formato do payload `{"tempos", "vazias", "rodadas"}` não muda, nem quem o lê (`get_coletas_vazias_desde`, `get_rodadas_coleta_desde`, `get_tempos_coleta_desde`, `get_coletas_vazias_count`), nem o que `/api/sistema` mostra.
- `save_coleta_tempo` e `save_coleta_vazia` continuam existindo como atalhos de um painel só sobre `gravar_instrumentacao_rodada`, para não mexer nos testes que as usam.
- Coletor que levanta exceção continua sem registro de tempo e de vazio, como hoje.

## Fontes de dados
Nenhuma externa. Só o snapshot `instrumentacao` em `snapshots_paineis`.

## Cálculos
Exemplo de ponta a ponta. Payload do dia antes da rodada (durações em segundos, contagens em rodadas):

```json
{"tempos": {"ibovespa": 1.8}, "vazias": {"mare": 2}, "rodadas": {"ibovespa": 10, "mare": 10}}
```

Rodada com três coletores: `ibovespa` em 2,0 s (ok), `mare` em 1,5 s (`collect_and_save()` devolveu `False`), `highlights` em 59,0 s (ok). Em memória: `tempos = {"ibovespa": 2.0, "mare": 1.5, "highlights": 59.0}`, `vazias = ["mare"]`.

Payload depois da gravação única:

```json
{"tempos": {"ibovespa": 2.0, "mare": 1.5, "highlights": 59.0},
 "vazias": {"mare": 3},
 "rodadas": {"ibovespa": 11, "mare": 11, "highlights": 1}}
```

Idas ao banco para a instrumentação: hoje 3 × 2 + 1 × 2 = **8**; depois, **2**. Na rodada de pregão com 42 coletores, de cerca de 84 para 2.

Se a rodada passa da meia-noite em BRT, tudo vai para o dia do `timestamp` do fim da rodada. Hoje cada coletor iria para o dia em que terminou; a diferença só existe na rodada das 0h, fora do pregão, e é aceitável.

## Critérios de aceite
- [ ] `tests/test_aceite_152.py`, com `exigir_spec_done("152")`, roda `_coletar` com três coletores falsos (dois ok, um devolvendo `False`) e `ler_snapshot`/`gravar_snapshot` espionados: **exatamente 1** leitura e **1** gravação do painel `instrumentacao` na rodada inteira.
- [ ] O mesmo teste, partindo do payload "antes" da seção *Cálculos* e com as durações do exemplo, confere o payload "depois" campo a campo.
- [ ] Um coletor que levanta exceção no meio da rodada não impede a gravação dos tempos dos que já terminaram (1 gravação, sem o painel que falhou em `tempos`).
- [ ] `gravar_instrumentacao_rodada` com `gravar_snapshot` levantando exceção não propaga a exceção para `_coletar`.
- [ ] `tests/test_instrumentacao_coleta_tempo.py` passa a ter `assert` de verdade: `save_coleta_tempo("teste_painel", 1.234, agora)` resulta em `tempos["teste_painel"] == 1.234` e `rodadas["teste_painel"] == 1` no snapshot do dia (SQLite temporário). É reforço, nunca afrouxamento.
- [ ] `tests/test_instrumentacao.py` e os testes de `/sistema` continuam verdes sem mudar expectativa.
- Arquivos tocados: `app/agendador.py`, `app/database.py`, `tests/test_instrumentacao_coleta_tempo.py` e o novo `tests/test_aceite_152.py`. Medido com `grep -rl "save_coleta_tempo\|save_coleta_vazia"`: 4 arquivos (2 de código, 2 de teste).

## Invariantes de produção
- Em `/api/sistema`, o item "Duração da coleta" continua listando os coletores mais lentos, e o item "Painéis sem dados" continua presente, nos mesmos formatos.
- Depois de uma rodada de pregão, `rodadas` de um painel de janela `pregao` no snapshot `instrumentacao` sobe de 1 por rodada (verificável comparando `/api/sistema` antes e depois).

## Fora do escopo
- Fazer os `get_*_desde` respeitarem o parâmetro `desde` (hoje leem só o snapshot do dia, apesar de `/sistema` dizer "últimas 3 h"). Fica no backlog.
- Medir o tempo total de parede da rodada (não a soma dos coletores). Fica no backlog.
- Trocar o `DATABASE_URL` de produção pelo endereço interno do Postgres: é configuração no painel do Render, de quem opera o serviço, e já está avisada em `/sistema`.
- Remover a tabela `instrumentacao_coleta_tempo`, que ficou sem gravação: é poda, vai para o backlog.
- Concorrência entre a coleta agendada e a manual: o risco de uma sobrescrever a contagem da outra já existe hoje e não aumenta.
