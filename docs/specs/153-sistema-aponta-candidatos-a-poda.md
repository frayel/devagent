---
id: 153
titulo: A página /sistema aponta os painéis que cumprem o critério de poda
status: ready
esforco: P
gaveta: poda
aceite: tests/test_aceite_153.py
revisada: 2026-11-15
---

## Problema
Quais painéis ficaram sem dados em mais da metade das coletas dos últimos 10 pregões?

O `PRODUTO.md` (seção *Manutenção neste produto*) define o critério de poda: "um painel que, numa janela de 10 pregões, ficou sem dados ou escondido em mais da metade das coletas feitas durante o pregão é candidato a poda". E manda que, enquanto o sistema não registrar esse histórico por painel, a rodada de manutenção crie o registro.

O dado bruto já existe, mas ninguém o lê na janela do critério:

- O snapshot diário `instrumentacao` (`snapshots_paineis`, gravado por `save_coleta_tempo` e `save_coleta_vazia` em `app/database.py`, e pela `gravar_instrumentacao_rodada` da spec 152) guarda, por dia em BRT, `rodadas[painel]` (coletas que terminaram) e `vazias[painel]` (coletas em que `collect_and_save()` devolveu `False`, "nenhuma fonte respondeu").
- `remover_snapshots_antigos(30)` (`app/banco.py:829`) mantém as 30 datas mais recentes, o bastante para 10 pregões (cerca de 14 dias corridos).
- Os leitores (`get_coletas_vazias_desde`, `get_rodadas_coleta_desde`, `app/database.py:1450-1483`) só leem o snapshot de **hoje**. O item "Painéis sem dados" de `/sistema` (`verificar_paineis_vazios`, `app/services/sistema.py:419`) olha só esse dia.

Resultado: as rodadas de manutenção propõem podas pelo gosto ("Poda: Remoção do Fator Peso Pesado", "Poda: Remover Ação Órfã", "Poda: Limpeza de Rankings Secundários" no `docs/BACKLOG.md`) sem o número que o critério pede. Esta spec é o instrumento; a poda vem na rodada seguinte, com os números (`devagent/skills/manutencao.md`, "Sem instrumento, a primeira entrega é o instrumento").

## Medidas (15/11/2026, rodada de manutenção)
- Cadência de manutenção: 11 de 4 specs entregues desde a última de saúde técnica ou poda (`python -m devagent.cadencias`).
- Ideias de poda no backlog sem medida que as sustente: pelo menos 6 linhas (`grep -n "Poda:" docs/BACKLOG.md`), nenhuma com contagem de vazios.
- Leituras de `instrumentacao` por carga de `/sistema` hoje: 3 (uma por `get_*_desde`, todas do mesmo dia; dentro de uma requisição o `_req_snapshot_cache` as junta). Com o critério lido dia a dia seriam mais 10 idas ao Postgres, a ~300 ms cada em produção (spec 152, *Medidas*): ~3 s a mais por carga. Por isso a leitura da janela é **uma** consulta.

## Comportamento esperado
- Nova função `app.banco.ler_snapshots_datas(painel: str, datas: list[date]) -> dict[date, dict]`: **uma** consulta (`SELECT data_referencia, payload FROM snapshots_paineis WHERE painel = ? AND data_referencia IN (...)`), nos dois backends (Postgres e SQLite), devolvendo o payload de cada data que existe. Datas sem snapshot não aparecem no resultado. As chaves são sempre `date` (no SQLite a coluna volta como texto `AAAA-MM-DD` e é convertida com `date.fromisoformat`) e o payload é sempre `dict` (decodificado do JSON quando o backend devolve texto, como faz `ler_snapshot`). Lista `datas` vazia devolve `{}` sem ir ao banco (`IN ()` é erro de SQL). Banco inacessível (`DBInacessivelError`) devolve `{}`, como `listar_datas`. Não filtra por `estado` (a instrumentação grava `ao_vivo`).
- Nova função `app.services.sistema.ultimos_pregoes(agora: datetime, n: int = 10) -> list[date]`: os `n` pregões fechados mais recentes, do `calendario.ultimo_pregao_fechado(agora)` para trás, por `calendario.pregao_anterior`.
- Nova função pura `app.services.sistema.verificar_candidatos_poda(historico: dict[date, dict], pregoes: list[date]) -> Item`, com `nome` **"Candidatos à poda"** (campos do `Item` existente: `nome`, `nivel`, `resumo`, `detalhe`), que soma `rodadas` e `vazias` de cada painel nas datas de `pregoes` presentes em `historico` e aplica o critério da seção *Cálculos*.
- `estado_do_sistema()` (`app/main.py`) lê a janela uma vez (`ler_snapshots_datas("instrumentacao", ultimos_pregoes(agora))`, dentro do mesmo `try` dos outros leitores; exceção vira `{}`) e passa o resultado a `sistema_servico.montar` por um parâmetro novo opcional `historico_poda: dict | None = None`. `montar` acrescenta o item à lista `coleta` (grupo de título "Coleta"), logo depois de "Painéis sem dados". Com `historico_poda=None` (chamadas antigas, inclusive as de `tests/test_sistema.py`), o item não entra e a saída de `montar` é a mesma de hoje.
- Estados do item:
  - **Histórico curto** (menos de 10 dos 10 pregões têm snapshot `instrumentacao`): `ok`, resumo `histórico de N de 10 pregões; o critério precisa de 10`, sem lista. Nenhum painel é apontado com janela incompleta.
  - **Ninguém cumpre o critério:** `ok`, resumo `nenhum painel vazio em mais da metade das coletas dos últimos 10 pregões`.
  - **Algum painel cumpre:** `atencao`, resumo `1 painel vazio em mais da metade das coletas dos últimos 10 pregões` ou `N painéis vazios em ...` (plural a partir de 2), detalhe com a lista em ordem decrescente de percentual (empate pelo nome): `painel (vazias de rodadas, P%)`, com P = `round(100 × V / R)` (inteiro).
- `atencao`, e não `problema`: candidato à poda é decisão de produto, não defeito. É o estado que `devagent/skills/manutencao.md` manda ler primeiro na rodada de manutenção (`python -m devagent.saude`).

## Fontes de dados
Nenhuma externa. Só o snapshot `instrumentacao` em `snapshots_paineis`, já gravado a cada rodada. Plano B: banco inacessível ou payload sem `rodadas` resulta em histórico curto (`ok`, "histórico de 0 de 10 pregões"), e o resto de `/sistema` funciona.

## Cálculos
Para cada painel `p`, somando só as datas de `pregoes` presentes em `historico`:

- `R(p) = Σ rodadas[p]` (coletas que terminaram, contagem inteira); o agendador (`app/agendador.py`, laço da rodada) põe em `tempos` todo painel cujo `collect_and_save()` retornou, com ou sem dado, e em `vazias` só os que retornaram `False`; por isso, dia a dia, `vazias[p] ≤ rodadas[p]` e `V(p)/R(p)` fica entre 0 e 1;
- `V(p) = Σ vazias[p]` (coletas sem dado, contagem inteira; painel ausente em `vazias` conta 0);
- `p` é candidato se `R(p) ≥ 10` **e** `2 × V(p) > R(p)` (estritamente mais da metade, como diz o critério do `PRODUTO.md`; a comparação em inteiros evita arredondamento de ponto flutuante).
- `P(p) = round(100 × V(p) / R(p))`, com o `round` do Python, exibido como inteiro seguido de `%`.

`R(p) ≥ 10` (em média uma coleta por pregão) evita apontar painel que quase não roda na janela, como os de janela `fechamento` ou `pre_abertura` com poucas rodadas.

Exemplo de ponta a ponta. `agora` = domingo, 15/11/2026, 03h BRT. `ultimo_pregao_fechado` = 13/11; os 10 pregões são 13, 12, 11, 10, 9, 6, 5, 4 e 3/11 e 30/10 (2/11, Finados, não é pregão). Todos os 10 têm snapshot. Em cada um dos 10 dias o payload traz (contagens em coletas):

| painel | `rodadas` por dia | `vazias` por dia |
|---|---|---|
| `fator_peso_pesado` | 28 | 15 |
| `atrasadas_rally` | 28 | 14 |
| `ibovespa` | 28 | (ausente) |
| `clima_global` | 1 | 1 |

Somas na janela: `fator_peso_pesado` R = 280, V = 150, 150/280 = 0,5357 → **candidato**, exibido `fator_peso_pesado (150 de 280, 54%)`. `atrasadas_rally` R = 280, V = 140, 140/280 = 0,5 → não é (não passa da metade). `ibovespa` V = 0 → não é. `clima_global` R = 10, V = 10, 10/10 = 1,0 → **candidato**, `clima_global (10 de 10, 100%)`.

Item: `atencao`, resumo `2 painéis vazios em mais da metade das coletas dos últimos 10 pregões`, detalhe `clima_global (10 de 10, 100%), fator_peso_pesado (150 de 280, 54%)`.

Mesmo cenário com só 9 datas no `historico` (30/10 apagada): `ok`, `histórico de 9 de 10 pregões; o critério precisa de 10`.

Um snapshot de uma data fora de `pregoes` (por exemplo, sábado 14/11, com coleta semanal) é ignorado, mesmo que `ler_snapshots_datas` o devolva.

## Critérios de aceite
- [ ] `tests/test_aceite_153.py`, com `exigir_spec_done("153")`:
  - `verificar_candidatos_poda` com o `historico` do exemplo (10 datas) devolve `Item` com `nome` `Candidatos à poda`, `nivel` `atencao`, o resumo e o detalhe exatos do exemplo, `atrasadas_rally` e `ibovespa` fora da lista.
  - Com 9 das 10 datas: `nivel` `ok` e resumo `histórico de 9 de 10 pregões; o critério precisa de 10`.
  - Com 10 datas e nenhum painel acima de 0,5: `nivel` `ok` e o resumo "nenhum painel ...".
  - Um payload de data fora de `pregoes` (14/11) com `vazias` altíssimas não muda o resultado.
  - `ultimos_pregoes(datetime(2026, 11, 15, 6, 0, tzinfo=timezone.utc))` devolve as 10 datas do exemplo, sem 2/11.
  - `ler_snapshots_datas("instrumentacao", [...])` num SQLite temporário com três datas gravadas por `gravar_snapshot` (uma delas fora da lista pedida) devolve só as duas pedidas, com o payload igual ao gravado, e faz **uma** chamada a `cursor.execute` de `SELECT` (espionado).
  - `montar(..., historico_poda=None)` não contém o item `Candidatos à poda`; `montar(..., historico_poda=<exemplo>)` contém, no grupo `coleta`, logo depois de `Painéis sem dados`.
- [ ] `tests/test_sistema.py` continua verde sem mudar expectativa.
- Arquivos tocados: `app/banco.py`, `app/services/sistema.py`, `app/main.py` e o novo `tests/test_aceite_153.py`. Medido com `grep -rl "verificar_paineis_vazios\|def montar\|estado_do_sistema" app tests`: 3 arquivos (2 de código, 1 de teste, que não muda).

## Invariantes de produção
- `GET /api/sistema` (com a senha) tem, no grupo de coleta, um item com `nome` `Candidatos à poda` (grupo de título "Coleta"), com `nivel` `ok` ou `atencao`, nunca `problema`.
- Se o `nivel` é `atencao`, cada painel da lista traz `V de R, P%` com `R ≥ 10`, `2 × V > R` e `P` = `round(100 × V / R)` (por isso `P ≥ 50`: 141 de 280 é candidato e aparece como 50%).
- Se o resumo diz "histórico de N de 10 pregões", então N < 10 e nenhum painel é listado.

## Fora do escopo
- **Podar** qualquer painel. Esta spec só mede; a primeira rodada de manutenção depois de 10 pregões com o item visível escolhe o que sai, citando os números (backlog).
- O "escondido" do critério do `PRODUTO.md`: painel que coleta com sucesso mas fica com a classe `.escondido` por lista vazia (sem alertas no dia) não conta como vazio aqui. Registrar isso pede gravar, por rodada, quais chaves de `/api/snapshot` saíram vazias; fica no backlog como segunda fatia.
- Separar as coletas "feitas durante o pregão" das tentativas de fechamento (18h-20h) e da pré-abertura: o snapshot diário não guarda a hora de cada coleta. A aproximação conta todas as coletas do dia de pregão; está registrada aqui para a rodada de poda pesar.
- Fazer os `get_*_desde` respeitarem `desde` e mudar o item "Painéis sem dados" (ideia do backlog de 15/11).
- Mudar como a instrumentação grava (spec 152) ou o prazo de `remover_snapshots_antigos`.
- Coleta que levanta exceção: o agendador não a registra nem em `rodadas` nem em `vazias`, então um painel que sempre falha com exceção não aparece aqui. Ele já aparece nos erros da coleta em `/sistema`; contá-lo no critério pede mudar a instrumentação (spec 152), fora daqui.
- Mostrar o histórico de poda na página pública ou no `/api/snapshot`: é diagnóstico de operação, fica em `/sistema`.

## Revisão
Revisada em 15/11/2026. O exemplo de datas foi conferido contra `app/calendario.py` (`ultimo_pregao_fechado` de 15/11 03h BRT dá 13/11; 2/11 é feriado). Acrescentados: conversão de tipos de `ler_snapshots_datas` no SQLite e lista vazia sem consulta; critério em inteiros (`2 × V > R`) e `round` do Python para P; por que `V ≤ R` (agendador); limitação das coletas com exceção no *Fora do escopo*; o grupo é identificado pelo título "Coleta".
