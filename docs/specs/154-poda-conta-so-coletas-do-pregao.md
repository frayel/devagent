---
id: 154
titulo: O critério de poda conta só as coletas feitas durante o pregão
status: done
esforco: P
gaveta: saúde técnica
aceite: tests/test_aceite_154.py
revisada: 2026-11-15
---

## Problema
O número que vai decidir a próxima poda conta só as coletas que o critério manda contar?

O `PRODUTO.md` (seção *Manutenção neste produto*) define o candidato à poda como o painel que "ficou sem dados ou escondido em mais da metade das coletas **feitas durante o pregão**" numa janela de 10 pregões. A spec 153 levou o item "Candidatos à poda" a `/sistema`, mas o snapshot diário `instrumentacao` não guarda a hora de cada coleta. Por isso ela soma todas as coletas do dia, e registrou a aproximação no próprio *Fora do escopo*: "A aproximação conta todas as coletas do dia de pregão; está registrada aqui para a rodada de poda pesar".

Fora do pregão o agendador ainda roda (`app/agendador.py`):

- depois das 18h15 até as 20h, a cada 30 minutos (`intervalo`), com as **tentativas de fechamento** dos painéis de janela `pregao` (só os que ainda não têm snapshot `final`) e os de janela `fechamento`;
- antes da abertura, a partir das 7h, os de janela `pre_abertura` (`clima_global`), e a cada 2 horas no resto do dia, com as **partidas a frio** de painel sem snapshot.

"Durante o pregão" aqui é o que `calendario.mercado_aberto` já diz: dia de pregão e hora BRT entre `ABERTURA` (10h) e `FIM_DA_JANELA` (18h15), as duas pontas inclusive. A rodada que o agendador faz às 9h55 (`INICIO_PREGAO`) não conta; a de 18h15 em ponto conta.

São justamente as coletas com mais chance de voltar vazias: depois do fechamento muitos radares intraday não têm o que mostrar. Um painel saudável no pregão pode passar da metade só por elas, e um painel ruim no pregão pode ficar abaixo dela. A rodada de poda (backlog, "Poda: rodada de poda com os números da 153") ainda não aconteceu: é a hora de corrigir o instrumento, antes de ele decidir o que sai.

## Comportamento esperado
- `gravar_instrumentacao_rodada(tempos, vazias, timestamp, durante_pregao: bool = False)` (`app/database.py`) ganha o parâmetro `durante_pregao`. O que ela faz hoje continua igual (`tempos`, `rodadas`, `vazias`, uma leitura e uma gravação, nada no banco com rodada sem medidas). Com `durante_pregao=True`, ela também soma, no mesmo payload e na mesma gravação, `rodadas_pregao[painel] += 1` para cada painel de `tempos` e `vazias_pregao[painel] += 1` para cada painel de `vazias`. Com `durante_pregao=False`, as chaves `*_pregao` existentes no payload ficam como estão, e não são criadas.
- `_coletar()` (`app/agendador.py`) passa `durante_pregao=esta_aberto`, o valor de `calendario.mercado_aberto(...)` que ela já calcula **no início** da rodada. A rodada inteira conta como do pregão ou não; uma rodada que começa às 18h14 e termina às 18h17 conta como do pregão.
- `save_coleta_tempo` e `save_coleta_vazia` não mudam (continuam com `durante_pregao=False`).
- `verificar_candidatos_poda` (`app/services/sistema.py`) passa a somar `rodadas_pregao` e `vazias_pregao` em vez de `rodadas` e `vazias`. Uma data da janela conta como presente só se o payload tem `rodadas_pregao` como `dict` (pode ser vazio). Os snapshots gravados antes desta spec não têm a chave e contam como ausentes: o item fica em "histórico de N de 10 pregões; o critério precisa de 10" até haver 10 pregões com a contagem nova. O texto do resumo e do detalhe não muda; nome, níveis, `MIN_RODADAS_PODA`, ordem e `envelhece=False` também não.
- O item "Painéis sem dados" e os `get_*_desde` continuam lendo `rodadas` e `vazias` do dia inteiro, como hoje.

## Fontes de dados
Nenhuma externa. Só o snapshot `instrumentacao` em `snapshots_paineis`. Plano B: se a gravação falhar, o `try` que já envolve `gravar_instrumentacao_rodada` no `finally` de `_coletar` registra no log e a rodada segue, como hoje; o dia sem `rodadas_pregao` conta como ausente na janela.

## Cálculos
Para cada painel `p`, somando só as datas de `pregoes` cujo payload tem `rodadas_pregao`:

- `R(p) = Σ rodadas_pregao[p]` e `V(p) = Σ vazias_pregao[p]` (painel ausente em `vazias_pregao` conta 0), contagens inteiras de coletas;
- candidato se `R(p) ≥ 10` e `2 × V(p) > R(p)`; `P(p) = round(100 × V(p) / R(p))`, como na spec 153.

`vazias_pregao[p] ≤ rodadas_pregao[p]` dia a dia, pelo mesmo motivo da 153: o agendador põe em `vazias` só painel que também está em `tempos`.

Exemplo da gravação. Payload do dia 16/11/2026 antes: `{"tempos": {"mare": 1.0}, "rodadas": {"mare": 3}, "vazias": {"mare": 1}, "rodadas_pregao": {"mare": 2}, "vazias_pregao": {"mare": 1}}`.

1. Rodada que começa às 10h15 BRT (`esta_aberto` = `True`), `tempos = {"mare": 1.5, "ibovespa": 2.0}`, `vazias = ["mare"]`. Depois: `rodadas = {"mare": 4, "ibovespa": 1}`, `vazias = {"mare": 2}`, `rodadas_pregao = {"mare": 3, "ibovespa": 1}`, `vazias_pregao = {"mare": 2}`.
2. Rodada que começa às 18h45 BRT (`False`), `tempos = {"mare": 0.8}`, `vazias = ["mare"]`. Depois: `rodadas = {"mare": 5, "ibovespa": 1}`, `vazias = {"mare": 3}`, `rodadas_pregao` e `vazias_pregao` iguais ao passo 1.

Exemplo do critério, de ponta a ponta. Os 10 pregões da spec 153 (13/11 a 30/10, sem 2/11), todos com as quatro chaves. Por dia, em coletas:

| painel | `rodadas` | `vazias` | `rodadas_pregao` | `vazias_pregao` |
|---|---|---|---|---|
| `fator_peso_pesado` | 34 | 18 | 30 | 14 |
| `atrasadas_rally` | 34 | 17 | 30 | 16 |

Hoje (153, dia inteiro): `fator_peso_pesado` V = 180, R = 340, 2 × 180 = 360 > 340 → candidato, `fator_peso_pesado (180 de 340, 53%)`; `atrasadas_rally` V = 170, R = 340, 340 não é maior que 340 → não é.

Com esta spec (só o pregão): `fator_peso_pesado` V = 140, R = 300, 2 × 140 = 280 ≤ 300 → **não é**; `atrasadas_rally` V = 160, R = 300, 320 > 300 → **candidato**, `round(53,33)` = 53, exibido `atrasadas_rally (160 de 300, 53%)`.

Item: `atencao`, resumo `1 painel vazio em mais da metade das coletas dos últimos 10 pregões`, detalhe `atrasadas_rally (160 de 300, 53%)`. As quatro tentativas de fechamento por dia, todas vazias, punham `fator_peso_pesado` na lista e tiravam `atrasadas_rally`.

Mesmo cenário com 30/10 só com `rodadas` e `vazias` (snapshot antigo): `ok`, `histórico de 9 de 10 pregões; o critério precisa de 10`.

## Critérios de aceite
- [ ] `tests/test_aceite_154.py`, com `exigir_spec_done("154")`:
  - num SQLite temporário, os dois passos do exemplo da gravação, com `durante_pregao=True` e depois `False`, deixam o payload exatamente como o exemplo diz, campo a campo;
  - `durante_pregao=False` sobre payload sem `rodadas_pregao` não cria a chave;
  - `_coletar()` com o relógio em 16/11/2026 10h15 BRT chama `gravar_instrumentacao_rodada` com `durante_pregao=True`, e às 18h45 BRT com `False` (coletores e banco espionados como em `tests/test_aceite_152.py`). O relógio é fixado trocando `agendador.datetime` por uma subclasse de `datetime` cujo `now(tz)` devolve o instante do teste, **sem** substituir `calendario.mercado_aberto`: o teste prova que o valor vem do relógio do início da rodada;
  - `verificar_candidatos_poda` com o `historico` do exemplo do critério devolve `atencao` e o resumo e o detalhe exatos, sem `fator_peso_pesado`;
  - com 30/10 sem `rodadas_pregao`: `ok` e `histórico de 9 de 10 pregões; o critério precisa de 10`.
- [ ] `tests/test_aceite_153.py` continua verde **sem mudar expectativa**: todo payload que os testes passam a `verificar_candidatos_poda` ganha `rodadas_pregao` e `vazias_pregao` com os mesmos números de `rodadas` e `vazias` (o `PAYLOAD_DIA` e os payloads escritos dentro de `test_um_candidato_no_singular`, `test_ninguem_acima_da_metade` e `test_data_fora_dos_pregoes_e_ignorada`). Nenhum `assert` muda, e o teste de `ler_snapshots_datas` não muda.
- [ ] `tests/test_aceite_152.py`, `tests/test_instrumentacao.py` e `tests/test_sistema.py` continuam verdes sem mudança.
- Arquivos tocados: `app/database.py`, `app/agendador.py`, `app/services/sistema.py`, `tests/test_aceite_153.py` (só fixtures) e o novo `tests/test_aceite_154.py`. Medido com `grep -rl "gravar_instrumentacao_rodada\|verificar_candidatos_poda" app tests`: 3 de código (`app/database.py`, `app/agendador.py`, `app/services/sistema.py`) e 2 de teste (`tests/test_aceite_152.py`, que não muda, e `tests/test_aceite_153.py`), mais o teste novo.

## Invariantes de produção
- `GET /api/sistema` (com a senha) continua com o item `Candidatos à poda` no grupo "Coleta", `ok` ou `atencao`, nunca `problema`.
- Se o item lista um painel `V de R, P%`, então `R ≥ 10`, `2 × V > R` e `P = round(100 × V / R)`.
- No primeiro pregão depois do deploy, o snapshot `instrumentacao` do dia tem `rodadas_pregao`, e para todo painel `rodadas_pregao[p] ≤ rodadas[p]` e `vazias_pregao[p] ≤ vazias[p]`.
- Até haver 10 pregões com a contagem nova, o resumo é "histórico de N de 10 pregões" com N < 10, e nenhum painel é listado.

## Fora do escopo
- O "escondido" do critério: painel que coleta mas fica com a classe `.escondido` por lista vazia. Continua no backlog ("Saúde técnica: registrar o 'escondido' do critério de poda").
- Mudar o item "Painéis sem dados", os `get_*_desde` ou o horário do agendador.
- Reconstruir a contagem do pregão dos snapshots antigos: eles não têm a hora das coletas.
- Podar qualquer painel. A rodada de poda vem depois de 10 pregões com a contagem nova (backlog).
- Contar coleta que levanta exceção (limitação já registrada na spec 153).
