---
id: 184
titulo: Os radares de molde único entram no /api/snapshot por um laço só
status: ready
esforco: P
gaveta: saúde técnica
aceite: tests/test_aceite_184.py
origem: Radares do snapshot num laço
revisada: 2026-11-18
---

## Problema
Quanto do `/api/snapshot` é a mesma coisa escrita oito vezes? A função `snapshot` (`app/main.py:1137`) vai até a linha ~1998: são **~860 linhas** numa função só, e o arquivo inteiro tem 2.448. Cada radar entra no JSON por um bloco próprio, copiado do anterior, e as cópias já divergem em detalhe (ordem das chaves, `try` em volta do `json.loads` ou não, o que sai quando não há dado: `{"fonte": "nd", ...}`, `[]` ou `None`). Cada radar novo copia um desses blocos, e cada mudança do contrato (`auditoria/README.md`, *Contrato `/api/snapshot`*) tem de ser repetida em todos.

Medido na `main` de 18/11/2026 (rodada de manutenção vencida: 4 de 4 specs entregues desde a última de saúde técnica ou poda):

- Dos 20 radares de `RADARES` (`app/services/radares.py:18`), **8 têm exatamente o mesmo molde** no `/api/snapshot`: leem `get_latest_<radar>_data()`, fazem `json.loads(dado.alertas_json)` dentro de `try` (falha vira `[]`) e publicam `{"coletado_em": dado.timestamp.isoformat(), "fonte": dado.fonte, "alertas": alertas}`. Só muda o que sai quando o getter devolve nada:

  | Chave no `paineis` | Getter (`app.database`) | Linha em `app/main.py` | Sem dado |
  |---|---|---|---|
  | `variacao_subita` | `get_latest_variacao_subita_data` | 1551 | `{"fonte": "nd", "coletado_em": agora}` |
  | `faca_caindo` | `get_latest_faca_caindo_data` | 1588 | `{"fonte": "nd", "coletado_em": agora}` |
  | `compradores_fundo` | `get_latest_compradores_fundo_data` | 1605 | `{"fonte": "nd", "coletado_em": agora}` |
  | `concentracao_ordens` | `get_latest_concentracao_ordens_data` | 1622 | `{"fonte": "nd", "coletado_em": agora}` |
  | `armadilha_abertura` | `get_latest_armadilha_abertura_data` | 1639 | `{"fonte": "nd", "coletado_em": agora}` |
  | `short_squeeze` | `get_latest_radar_short_squeeze_data` | 1682 | `[]` |
  | `radar_inflexao` | `get_latest_radar_inflexao_data` | 1710 | `[]` |
  | `radar_absorcao_cruzada` | `get_latest_radar_absorcao_cruzada_data` | 1753 | `[]` |

  (`agora` é o `datetime.now(timezone.utc)` do começo da função, em `isoformat()`.)
- Esses 8 blocos somam **~118 linhas** (5 de 16 e 3 de ~13).
- Os outros 12 radares têm formas diferentes (lista crua sem `coletado_em`, `json.loads` sem `try`, `getattr(..., "fonte", "yfinance")`, `None` só em data histórica, chave do snapshot diferente da de `RADARES`, ou nem aparecem no snapshot). Ficam fora desta fatia: unificá-los muda o JSON publicado.
- Testes que já citam os 8 getters: `tests/test_aceite_150.py`, `tests/test_aceite_151.py`, `tests/test_concentracao_ordens.py`, `tests/test_radar_short_squeeze.py`, `tests/test_radar_inflexao.py`, `tests/test_radar_absorcao_cruzada.py`. Nenhum deles chama o `/api/snapshot` para esses radares; nenhum muda.

## Comportamento esperado
Nada muda no JSON do `/api/snapshot`, nem em nenhuma página. Muda só a forma de montar os 8 painéis da tabela:

1. Uma tupla de módulo em `app/main.py`, `RADARES_MOLDE_UNICO`, declara para cada um dos 8: a chave em `paineis`, o nome do getter em `app.database` e o valor sem dado (`"nd"` para o objeto `{"fonte": "nd", "coletado_em": agora}` ou `"lista"` para `[]`).
2. Uma função `_painel_de_alertas(dado, agora, sem_dado)` devolve o objeto `{coletado_em, fonte, alertas}` quando há dado (com o mesmo `try` em volta do `json.loads`, falha vira `[]`) ou o valor sem dado. Um objeto novo (dict ou lista) a cada chamada, nunca um compartilhado.
3. Dentro de `snapshot`, os 8 blocos saem e um laço sobre `RADARES_MOLDE_UNICO` preenche `resp["paineis"][chave]`. O getter é lido de `app.database` na hora da chamada (`getattr(app.database, nome)()`), para quem troca o getter no módulo, como os testes fazem, continuar sendo ouvido.
4. O laço roda dentro do mesmo `with app.banco.lendo_pregao(...), app.banco.req_snapshot_cache_ctx()` de hoje: a leitura de data histórica (`?data=`) continua igual.
5. Os quatro nomes importados no topo de `app/main.py` só para esses blocos (`get_latest_variacao_subita_data`, `get_latest_compradores_fundo_data`, `get_latest_armadilha_abertura_data` e `get_latest_concentracao_ordens_data`, linhas 81–88) e os `from app.database import ...` locais de `faca_caindo`, `radar_short_squeeze`, `radar_inflexao` e `radar_absorcao_cruzada` dentro de `snapshot` (linhas 1585 e 1656–1667) saem quando ficarem sem uso, senão o `ruff` (F401) reprova. `_payloads_radares()` tem os próprios imports locais e não muda.
6. As chamadas que hoje ficam no meio dos blocos e não são desses 8 continuam, na mesma ordem relativa entre si: em particular `get_latest_radar_congestionamento_data()` (lida hoje junto do short squeeze, linha 1683) e o bloco do `radar_congestionamento` que a usa.

A ordem das chaves dentro de `paineis` pode mudar; o conteúdo, não. JSON é comparado como objeto (o auditor e os testes fazem `json.loads`).

## Fontes de dados
Nenhuma fonte nova e nenhuma dependência nova. Os dados são os mesmos `snapshots_paineis` lidos pelos mesmos getters.

## Cálculos
Exemplo de ponta a ponta, do que o getter devolve ao que o JSON publica:

- `agora = 2026-11-18T17:30:00+00:00`.
- `get_latest_variacao_subita_data()` devolve um objeto com `timestamp = datetime(2026, 11, 18, 17, 15, tzinfo=timezone.utc)`, `fonte = "mt5"` e `alertas_json = '[{"ticker": "PETR4", "variacao": -2.1}]'`.
  → `paineis.variacao_subita = {"coletado_em": "2026-11-18T17:15:00+00:00", "fonte": "mt5", "alertas": [{"ticker": "PETR4", "variacao": -2.1}]}`.
- `get_latest_faca_caindo_data()` devolve `None`.
  → `paineis.faca_caindo = {"fonte": "nd", "coletado_em": "2026-11-18T17:30:00+00:00"}`.
- `get_latest_radar_inflexao_data()` devolve `None`.
  → `paineis.radar_inflexao = []`.
- `get_latest_compradores_fundo_data()` devolve um objeto com `alertas_json = "{quebrado"`, `timestamp` 17:15 UTC e `fonte = "yfinance"`.
  → `paineis.compradores_fundo = {"coletado_em": "2026-11-18T17:15:00+00:00", "fonte": "yfinance", "alertas": []}` (o `json.loads` falha e vira `[]`, como hoje; a resposta continua 200).

Medida que a spec promete: `app/main.py` perde **pelo menos 80 linhas** (`wc -l` antes e depois, registrado no relatório da entrega), e o número de ocorrências de `json.loads(` dentro de `snapshot` cai **8**.

## Critérios de aceite
`tests/test_aceite_184.py`, com `exigir_spec_done("184")`, sem internet, trocando os 8 getters de `app.database` por `monkeypatch`:

- [ ] Com os 8 getters devolvendo objetos com dado (como no exemplo), `GET /api/snapshot` responde 200 e cada uma das 8 chaves tem exatamente `{"coletado_em", "fonte", "alertas"}` com os valores esperados.
- [ ] Com os 8 getters devolvendo `None`, as 5 chaves `"nd"` são `{"fonte": "nd", "coletado_em": <agora>}` e as 3 chaves `"lista"` são `[]`.
- [ ] Com `alertas_json` inválido em um dos 8, a resposta é 200 e aquele painel tem `"alertas": []`; os outros não mudam.
- [ ] Dois painéis sem dado do mesmo tipo não são o mesmo objeto (mexer em `paineis["short_squeeze"]` não muda `paineis["radar_inflexao"]`), conferido chamando `_painel_de_alertas` duas vezes.
- [ ] `RADARES_MOLDE_UNICO` tem as 8 chaves da tabela, e todo nome de getter dela existe em `app.database`.
- [ ] O texto da função `snapshot` (`inspect.getsource`) não contém mais `get_latest_variacao_subita_data`, `get_latest_faca_caindo_data`, `get_latest_compradores_fundo_data`, `get_latest_concentracao_ordens_data`, `get_latest_armadilha_abertura_data`, `get_latest_radar_short_squeeze_data`, `get_latest_radar_inflexao_data` nem `get_latest_radar_absorcao_cruzada_data`: os 8 vêm só do laço.
- [ ] Os testes que já existem passam sem mudança de asserção (`make verify`), em especial `tests/test_aceite_150.py`, `tests/test_aceite_151.py` e os 31 arquivos de `tests/` que chamam `/api/snapshot`.

Ordem sugerida para o desenvolvimento: escrever primeiro os três primeiros critérios contra a `main` como está (devem passar sem o marcador) e só depois trocar os blocos pelo laço; assim o teste prova que o JSON não mudou.

## Invariantes de produção
- `GET /api/snapshot` em produção continua respondendo 200, e as chaves `variacao_subita`, `faca_caindo`, `compradores_fundo`, `concentracao_ordens`, `armadilha_abertura`, `short_squeeze`, `radar_inflexao` e `radar_absorcao_cruzada` continuam presentes em `paineis` em toda resposta, inclusive com `?data=` de um pregão da janela.
- Cada uma delas é um objeto com `coletado_em`, `fonte` e `alertas` (lista), ou, sem dado, `{"fonte": "nd", "coletado_em": ...}` para as cinco primeiras e `[]` para as três últimas: as mesmas formas de antes do merge.
- As checagens de `auditoria/` sobre o snapshot passam sem mudança.

## Fora do escopo
- Os outros 12 radares de `RADARES` e os demais painéis do snapshot (ibovespa, maré, clima, etc.): cada forma diferente que eles têm hoje é parte do contrato publicado, e unificá-la é mudança visível, com spec própria. O resto da visão (o registro declarativo de painéis, com um nome só por radar e as ~105 funções `save_*`/`get_*` de `app/database.py`) segue no item *Radares do snapshot num laço* da Fila do `docs/BACKLOG.md`.
- Dar `try` aos `json.loads` dos radares que hoje não têm (`exaustao_queda`, `exaustao_alta`): muda a resposta quando o JSON está quebrado (hoje 500), por isso fica fora.
- A divergência de nomes entre `RADARES`, os coletores e as chaves do snapshot (`short_squeeze`/`radar_short_squeeze`, `radar_anomalia_fechamento`/`anomalia_fechamento`) e os radares que não aparecem no snapshot (`scanner_capitulacao`).
- A página `/` (`index()`), que monta o contexto dos radares por outro caminho (`_payloads_radares()`, `app/main.py:1998`, e `index()`, linha 2222).
