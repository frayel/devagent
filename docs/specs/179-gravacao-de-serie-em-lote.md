---
id: 179
titulo: A série diária é gravada em lote
status: done
revisada: 2026-11-18
esforco: P
gaveta: saúde técnica
aceite: tests/test_aceite_179.py
origem: Gravação de série em lote
---

## Problema
Quanto da rodada de coleta é gasto conversando com o banco, uma barra de cada vez? Hoje, `gravar_serie` (`app/banco.py:618`) faz um `cursor.execute` por barra, nos dois backends (Postgres e SQLite). `executemany` não aparece em `app/`.

Medido na `main` de 18/11/2026:

- O maior chamador é `consultor_historico.collect_and_save` (`app/collectors/consultor_historico.py`): 75 tickers de `CARTEIRA_IBOVESPA` mais `^BVSP` = **76 séries de 2 anos** (`range_str="2y"`, ~500 pregões cada), renovadas a cada `REFRESCO = 60` min. Cada renovação manda ao banco cerca de 76 × 500 = **~38.000 `INSERT ... ON CONFLICT` separados**, cada um com sua ida e volta ao Postgres do Render.
- Os outros chamadores passam por `save_historico_diario` (`app/database.py:1727`), chamado por `fetch_historico_diario_yfinance_spark` e `..._chart` (`app/collectors/utils.py`) a cada série que não veio do cache: `faca_caindo`, `fator_mola`, `assimetria_risco_retorno` (`3mo`, ~63 barras), `radar_exaustao_alta`, `exaustao_tendencia`, `exaustao_queda`.
- Quem referencia `gravar_serie`: 5 arquivos (`app/banco.py`, `app/database.py`, `tests/test_aceite_108a.py`, `tests/test_aceite_086.py`, `tests/test_aceite_122.py`).

## Comportamento esperado
Nada muda no que o usuário vê, nem no conteúdo de `series_diarias`. Muda só a forma de escrever: `gravar_serie(ticker, barras)` monta a lista de parâmetros `(ticker, data_pregao, barras_str, agora)` de todas as barras e chama **um** `cursor.executemany` com o mesmo `INSERT ... ON CONFLICT ... DO UPDATE` de hoje, em cada backend, seguido do mesmo `conn.commit()`.

- No Postgres, o `executemany` do psycopg 3 já agrupa os comandos em pipeline: as ~500 idas e voltas por série viram poucas.
- No SQLite, `executemany` é nativo do `sqlite3`.
- A assinatura, o retorno (`None`), o `init_db()`, o `get_connection()` e o `conn.close()` no `finally` continuam iguais. Lista vazia continua retornando antes de abrir conexão.
- **Barras com a mesma data na mesma chamada:** hoje a última vence (cada `INSERT` posterior atualiza o anterior). Com `executemany`, cada linha continua sendo um comando separado, então a última continua vencendo. O teste de aceite fixa isso.
- **Barra sem `data`:** hoje vai `data_pregao = None` ao banco e o erro sobe para quem chamou (`save_historico_diario` engole). Continua igual: a spec não acrescenta filtro.
- **Falha no meio da série:** hoje, no Postgres, um `execute` que falha interrompe o laço antes do `commit`, e a conexão devolvida ao pool desfaz o que já tinha ido; nada da série fica gravado. Com `executemany` é o mesmo: a exceção sobe antes do `commit`. Não se acrescenta `try` por barra.

## Fontes de dados
Nenhuma fonte nova. Nenhuma dependência nova (`executemany` é do `psycopg` e do `sqlite3`, já usados).

## Cálculos
Exemplo de ponta a ponta, com o que vai ao banco:

- Entrada: `gravar_serie("PETR4", [{"data": "2026-11-16", "close": 38.10}, {"data": "2026-11-17", "close": 38.42}, {"data": "2026-11-17", "close": 38.50}])`.
- Hoje: 3 chamadas a `cursor.execute`, uma por barra.
- Depois: 1 chamada a `cursor.executemany` com 3 tuplas, na ordem da entrada:
  `("PETR4", "2026-11-16", '[{"data": "2026-11-16", "close": 38.1}]', agora)`, `("PETR4", "2026-11-17", '[{"data": "2026-11-17", "close": 38.42}]', agora)`, `("PETR4", "2026-11-17", '[{"data": "2026-11-17", "close": 38.5}]', agora)`.
- Resultado em `series_diarias` (igual ao de hoje): 2 linhas para `PETR4`; a de `2026-11-17` tem `barras = [{"data": "2026-11-17", "close": 38.5}]` (a última vence). `ler_serie("PETR4", date(2026,11,16), date(2026,11,17))` devolve 2 barras, com `close` 38.1 e 38.5.

Ganho esperado na renovação do `consultor_historico`: de ~38.000 chamadas a `execute` para **76 chamadas a `executemany`** (uma por série).

## Critérios de aceite
Em `tests/test_aceite_179.py`, com `exigir_spec_done("179")`, sem internet e só em diretório temporário:

- [ ] **Uma chamada por série.** Com `app.banco.get_connection` trocado por uma conexão falsa (cursor que registra as chamadas, backend `"postgres"` e depois `"sqlite_efemero"`) e `init_db` neutralizado, `gravar_serie("PETR4", <3 barras do exemplo>)` faz exatamente 1 `executemany`, com 3 tuplas iguais às do exemplo (comparando os três primeiros campos; o quarto é o mesmo `agora` nas três), 0 `execute` com `INSERT`, e 1 `commit`. Vale para os dois backends.
- [ ] **Mesmo conteúdo no banco.** Com o SQLite real do fixture `setup_db` do `tests/conftest.py` (arquivo em `tmp_path`, sem `DATABASE_URL`, backend `"sqlite_efemero"`; `BANCO_TIPO` não é lido por `app/`), a gravação do exemplo deixa 2 linhas para `PETR4`, e `ler_serie` devolve `close` 38.1 e 38.5 (a última barra repetida vence).
- [ ] **Lista vazia não abre conexão.** `gravar_serie("PETR4", [])` não chama `get_connection`.
- [ ] Os testes existentes que usam `gravar_serie` (`test_aceite_086.py`, `test_aceite_108a.py`, `test_aceite_122.py`) passam sem mudar a expectativa.

## Invariantes de produção
- `/api/snapshot` e as páginas mostram os mesmos números antes e depois do deploy (a mudança não altera o que é gravado).
- O painel do Consultor continua com histórico de 2 anos para os tickers da carteira (a página `/consultor` não passa a mostrar "dado indisponível" por falta de série).
- O tempo de `consultor_historico` em `tempos` do snapshot `instrumentacao` (spec 153, gravado ao fim de cada rodada por `app/agendador.py`), nas rodadas em que a série é renovada, não aumenta em relação aos 5 pregões anteriores ao deploy.

## Fora do escopo
- Gravar várias séries numa só chamada (um `executemany` por rodada, não por ticker): exige mudar `save_historico_diario` e os coletores. Fica para o item *Medir quanto de série a rodada baixa repetido* da Fila.
- Mudar o formato da coluna `barras` (hoje uma lista com uma barra por linha) ou o esquema de `series_diarias`.
- Outras funções `gravar_*` de `app/banco.py`, que gravam uma linha por chamada.
- `invalidar_cache_historico` e a leitura (`ler_series`, `get_historico_diario`).

## Linha de base da manutenção
Rodada de 18/11/2026 (cadência de manutenção em 6 de 4). Medidas: `gravar_serie` com 1 `execute` por barra nos dois backends; ~38.000 `INSERT` por renovação horária do `consultor_historico` (76 séries de 2 anos); 0 usos de `executemany` em `app/`. Meta: 1 `executemany` por série.
