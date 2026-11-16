---
id: 166
titulo: O critério de poda também conta o radar escondido por lista vazia
status: ready
esforco: P
gaveta: saúde técnica
aceite: tests/test_aceite_166.py
revisada: 2026-11-16
origem: Registrar o painel escondido por lista vazia
---

## Problema
Quais radares a aba Alertas esconde na maior parte do pregão?

O critério de poda do `PRODUTO.md` (seção *Manutenção neste produto*) chama de candidato o painel que, em 10 pregões, "ficou sem dados **ou escondido** em mais da metade das coletas feitas durante o pregão". As specs 153 e 154 contam só a primeira metade: `vazias_pregao` recebe o coletor que devolveu `False` (nenhuma fonte respondeu). Um radar que coleta direito e grava a lista vazia não entra em lugar nenhum, e é justamente esse que a aba Alertas esconde: `radares.resumo` (`app/services/radares.py:83`) dá a classe `escondido` a todo radar `SEM_ALERTAS` (com `?vazios` desligado, o padrão) e a todo radar sem snapshot.

A rodada de poda (backlog, "Rodada de poda com os números da 153/154") vai decidir quais radares saem. Sem esta contagem ela decide só pelos coletores que falham, que são poucos, e não vê os radares que quase nunca acendem, que são o alvo óbvio (as três exaustões, Atrasadas do Rally). A contagem só vale com 10 pregões gravados: cada dia sem ela atrasa a poda um dia.

A contagem nova é por **chave de `RADARES`**, a mesma que a página usa, e não por nome de coletor: os dois não batem em três casos (o módulo `radar_exaustao_alta` grava `exaustao_alta`, `radar_liquidez_abertura` grava `liquidez_abertura`, `radar_anomalias_spread` grava `anomalias_spread`). A chave de `RADARES` também é a do snapshot, com uma exceção conferida no código: `short_squeeze` é gravado e lido como `radar_short_squeeze` (`app/database.py:1117` e `:1124`).

## Comportamento esperado
1. **`radares.SNAPSHOT_DO_RADAR = {"short_squeeze": "radar_short_squeeze"}`** e **`radares.escondidos(payloads: dict[str, Any]) -> list[str]`** (novos, `app/services/radares.py`). O dict diz o nome do snapshot das chaves que não o usam como nome; as outras usam a própria chave. `escondidos` recebe os payloads crus de `ler_snapshot`, indexados pela chave de `RADARES`, e percorre `RADARES` na ordem declarada, devolvendo as chaves escondidas. Os 20 radares gravam a lista como texto JSON no campo `<campo>_json` do payload, onde `<campo>` é o terceiro elemento da tupla (`alerts_json` em `volume_alerts`, `alertas_json` nos outros 19; conferido em `app/database.py`, nas funções `save_*` de cada um). A chave é escondida quando o payload é falso (`None`, `{}` ou ausente), quando `<campo>_json` falta, não é texto ou não é JSON válido, ou quando o JSON lido é falso (lista vazia, `null`). É o que a página faz: o radar sem snapshot e o radar de lista vazia ganham a classe `escondido`. Não olha horário: o "desatualizado" fica fora (ver *Fora do escopo*).
2. **`_coletar()`** (`app/agendador.py`), no `finally`, antes de `gravar_instrumentacao_rodada` e só quando `esta_aberto` (o mesmo valor do início da rodada que a 154 já usa): lê os 20 snapshots do pregão corrente numa consulta só,

   ```python
   with app.banco.req_snapshot_cache_ctx():
       payloads = {
           c: app.banco.ler_snapshot(SNAPSHOT_DO_RADAR.get(c, c), pregao_corr)
           for c, _n, _f in RADARES
       }
   ```

   e passa `radares_escondidos=radares.escondidos(payloads)`. Se essa leitura levantar exceção, registra no log (`logger.exception`) e passa `radares_escondidos=None`; a gravação da rodada segue. Fora do pregão não lê nada e passa `None`.
3. **`gravar_instrumentacao_rodada(..., radares_escondidos: list[str] | None = None)`** (`app/database.py`). Com `durante_pregao=True` **e** `radares_escondidos` diferente de `None`, na mesma leitura e na mesma gravação de hoje: `radares_pregao += 1` (inteiro na raiz do payload, criado com 0) e `escondidos_pregao[chave] += 1` para cada chave da lista (dict criado vazio, mesmo com a lista vazia). Em qualquer outro caso, as duas chaves ficam como estão e não são criadas. O retorno antecipado de hoje vem antes de tudo: rodada sem `tempos` e sem `vazias` não toca no banco e, portanto, também não conta em `radares_pregao`. Nada mais muda: `tempos`, `rodadas`, `vazias`, `por_hora`, `rodadas_pregao`, `vazias_pregao`, `ultima_rodada` e o retorno antecipado sem medidas.
4. **`verificar_radares_escondidos(historico, pregoes) -> Item`** (novo, `app/services/sistema.py`), item **"Radares escondidos"** no grupo Coleta, logo depois de "Candidatos à poda" e na mesma condição (`historico_poda is not None`), lendo o mesmo `historico_poda` (nenhuma consulta nova). Sempre `envelhece=False`, nunca `problema`:
   - uma data de `pregoes` só conta se o payload tem `radares_pregao` inteiro; com menos de `n` presentes (ou `n = 0`): `ok`, `histórico de K de n pregões; o critério precisa de n`;
   - com os `n` presentes: `R = Σ radares_pregao` e, por chave, `V(c) = Σ escondidos_pregao[c]` (ausente conta 0). Candidato se `R ≥ MIN_RODADAS_PODA` e `2 × V(c) > R`, com `P(c) = round(100 × V(c) / R)`;
   - sem candidato: `ok`, `nenhum radar escondido em mais da metade das coletas dos últimos n pregões`;
   - com candidatos: `atencao`, resumo `1 radar escondido em mais da metade das coletas dos últimos n pregões` (plural: `N radares escondidos em ...`), detalhe `chave (V de R, P%)` separados por `, `, em ordem de `P` decrescente e depois de chave.

   O item "Candidatos à poda" não muda.

## Fontes de dados
Nenhuma externa. Os snapshots dos 20 radares em `snapshots_paineis` (lidos numa consulta, pelo cache de `req_snapshot_cache_ctx`) e o snapshot diário `instrumentacao`. Plano B: leitura falha → `None`, a rodada não conta para os radares e o resto da instrumentação é gravado como hoje; dia sem `radares_pregao` conta como ausente.

## Cálculos
Exemplo da gravação. Payload de 17/11/2026 antes: `{"tempos": {"mare": 1.0}, "rodadas": {"mare": 3}, "rodadas_pregao": {"mare": 2}, "radares_pregao": 2, "escondidos_pregao": {"faca_caindo": 2, "volume_alerts": 1}}`.

1. Rodada às 10h15 BRT, `durante_pregao=True`, `tempos = {"mare": 1.5}`, `vazias = []`, `radares_escondidos = ["faca_caindo"]` → `radares_pregao = 3`, `escondidos_pregao = {"faca_caindo": 3, "volume_alerts": 1}`, `rodadas_pregao = {"mare": 3}`.
2. Rodada às 10h30, `True`, mesmos `tempos` e `vazias` do passo 1 (também nos passos 3 e 4), `radares_escondidos = []` → `radares_pregao = 4`, `escondidos_pregao` igual ao passo 1, `rodadas_pregao = {"mare": 4}`.
3. Rodada às 10h45, `True`, `radares_escondidos = None` (leitura falhou) → `radares_pregao = 4`, `escondidos_pregao` igual; `rodadas_pregao = {"mare": 5}`.
4. Rodada às 18h45, `durante_pregao=False`, `radares_escondidos = ["faca_caindo"]` → `radares_pregao` e `escondidos_pregao` iguais ao passo 3.

Sobre um payload sem as chaves, `tempos = {"mare": 1.5}`, `vazias = []`, `durante_pregao=True` e `radares_escondidos = []` criam `radares_pregao = 1` e `escondidos_pregao = {}`. Com `tempos = {}` e `vazias = []` (e qualquer `radares_escondidos`), nada é gravado: o payload continua sem as chaves.

Exemplo de `escondidos`. Os 20 radares com um alerta cada (`{"alerts_json": "[{\"ticker\": \"PETR4\"}]"}` para `volume_alerts`, `{"alertas_json": "[{\"ticker\": \"PETR4\"}]"}` para os outros), menos `faca_caindo` com `{"alertas_json": "[]"}`, `falso_rompimento` com `{"alertas_json": "não é json"}` e `radar_inflexao` ausente do dict → `["faca_caindo", "falso_rompimento", "radar_inflexao"]`, nessa ordem (a de `RADARES`).

Exemplo do critério. Os 10 pregões da spec 153 (13/11 a 30/10, sem 2/11), todos com `radares_pregao = 30` e `escondidos_pregao = {"faca_caindo": 16, "volume_alerts": 15}`. `R = 300`. `faca_caindo`: `V = 160`, `320 > 300` → candidato, `round(53,33) = 53`. `volume_alerts`: `V = 150`, `300` não é maior que `300` → não é. Item: `atencao`, resumo `1 radar escondido em mais da metade das coletas dos últimos 10 pregões`, detalhe `faca_caindo (160 de 300, 53%)`. Com `escondidos_pregao = {"faca_caindo": 16, "volume_alerts": 16}`: resumo `2 radares escondidos em mais da metade das coletas dos últimos 10 pregões`, detalhe `faca_caindo (160 de 300, 53%), volume_alerts (160 de 300, 53%)`. Mesmo cenário com 30/10 sem `radares_pregao`: `ok`, `histórico de 9 de 10 pregões; o critério precisa de 10`.

## Critérios de aceite
- [ ] `tests/test_aceite_166.py`, com `exigir_spec_done("166")`:
  - para toda chave `c` de `RADARES`, com `<nome> = SNAPSHOT_DO_RADAR.get(c, c)` e `<campo>` o terceiro elemento da tupla, o código-fonte de `app/database.py` casa com a regex `gravar_snapshot\(\s*"<nome>"` (o nome pode vir na linha seguinte) e contém `<campo>_json` (teste de contrato lido do fonte: um radar novo com outro nome de snapshot ou outro campo reprova até a spec ser ajustada);
  - `radares.escondidos` com o exemplo acima devolve `["faca_caindo", "falso_rompimento", "radar_inflexao"]`, e com `{}` devolve as 20 chaves de `RADARES` em ordem;
  - num SQLite temporário, os quatro passos do exemplo da gravação deixam o payload exatamente como descrito, campo a campo, o caso do payload sem as chaves cria `radares_pregao = 1` e `escondidos_pregao = {}`, e o caso sem `tempos` nem `vazias` não grava nada;
  - `_coletar()` com o relógio em 17/11/2026 10h15 BRT (mesma técnica da `tests/test_aceite_154.py`: `agendador.datetime` trocado, coletores espionados), com os snapshots dos radares semeados como no exemplo de `escondidos` (o de `short_squeeze` gravado como `radar_short_squeeze`), chama `gravar_instrumentacao_rodada` com `radares_escondidos=["faca_caindo", "falso_rompimento", "radar_inflexao"]`; às 18h45 BRT, com `radares_escondidos=None`; e com `app.banco.ler_snapshot` levantando exceção só para chaves de `RADARES`, às 10h15, com `None` e sem a exceção escapar;
  - `verificar_radares_escondidos` com os três cenários do exemplo do critério devolve nível, resumo e detalhe exatos, e com nenhum candidato devolve `ok` e `nenhum radar escondido em mais da metade das coletas dos últimos 10 pregões`;
  - `montar(...)` com `historico_poda` traz "Radares escondidos" logo depois de "Candidatos à poda" no grupo Coleta; com `historico_poda=None`, nenhum dos dois.
- [ ] `tests/test_aceite_152.py`, `tests/test_aceite_153.py`, `tests/test_aceite_154.py`, `tests/test_aceite_161.py`, `tests/test_aceite_162.py`, `tests/test_aceite_164.py`, `tests/test_instrumentacao.py` e `tests/test_sistema.py` continuam verdes sem mudar expectativa.
- Arquivos tocados: `app/services/radares.py`, `app/agendador.py`, `app/database.py`, `app/services/sistema.py` e o novo `tests/test_aceite_166.py`. Medido com `grep -rl "gravar_instrumentacao_rodada\|verificar_candidatos_poda" app tests`: 3 de código e 6 de teste (`test_aceite_152.py`, `153`, `154`, `161`, `162` e `164`; conferido na revisão de 16/11), nenhum precisa mudar porque o parâmetro novo tem padrão `None`.

## Invariantes de produção
- `GET /api/sistema` (com a senha) tem o item `Radares escondidos` no grupo "Coleta", `ok` ou `atencao`, nunca `problema`.
- No primeiro pregão depois do deploy, o snapshot `instrumentacao` do dia tem `radares_pregao ≥ 1` e, para toda chave, `escondidos_pregao[c] ≤ radares_pregao`; toda chave de `escondidos_pregao` está em `RADARES`.
- Até haver 10 pregões com a contagem nova, o resumo é `histórico de K de 10 pregões` com K < 10, e nenhum radar é listado.
- Se o item lista `c (V de R, P%)`, então `R ≥ 10`, `2 × V > R` e `P = round(100 × V / R)`.

## Fora do escopo
- O radar **desatualizado** (que a página também esconde, durante o pregão, quando a idade passa do TTL): contá-lo exigiria o relógio de cada coleta no `_coletar`; fica para a rodada de poda pesar à mão.
- Os painéis fora de `RADARES` escondidos por `if not X` em `index.html` (Clima Global, Motores do Índice, Concentração Setorial, Pressão Vendedora, Concentração de Ganhos, Anomalia de Peso): eles só se escondem sem snapshot, o que o `vazias_pregao` da 154 já conta pelo coletor.
- Fundir os dois itens de poda num só, ou mudar o "Candidatos à poda".
- Reconstruir a contagem dos pregões já passados.
- Podar qualquer radar: é a rodada de poda (backlog), depois de 10 pregões com esta contagem.
- A partida a frio que roda os coletores do Consultor em toda rodada (issue #919): é correção do desenvolvimento.
