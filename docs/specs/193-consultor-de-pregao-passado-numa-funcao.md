---
id: 193
titulo: O Consultor de um pregão passado sai de uma função só
status: ready
esforco: P
gaveta: saúde técnica
aceite: tests/test_aceite_193.py
revisada: 2026-11-23
origem: Uma função para `/consultor` e `/api/consultor`
---

## Problema
Por que a página `/consultor?data=` de um pregão passado faz 50 vezes mais consultas ao banco que o `/api/consultor?data=` do mesmo dia, se as duas mostram a mesma coisa? As duas rotas montam o Consultor histórico (as recomendações gravadas daquele pregão, cada uma com "+X% contra o IBOV em N pregões") por dois blocos de código separados em `app/main.py`, e só um deles foi corrigido pela spec 131:

- `pagina_consultor` (`app/main.py:643`), ramo `if is_historical:` (linhas ~666–776): **dentro do laço das recomendações**, para cada uma, chama `init_db()`, abre uma conexão, lê a lista inteira de `data_pregao` de `consultor_fechamentos` e faz mais três `SELECT preco_fechamento ... WHERE data_pregao = ? AND ticker = ?` (o ativo no pregão futuro, o `^BVSP` no pregão da recomendação e no futuro).
- `api_consultor` (`app/main.py:907`), ramo `if is_historical:` (linhas ~928–1023): uma conexão, a lista de datas uma vez e um `SELECT ... WHERE ticker IN (...)` com todos os tickers; o laço só consulta um dicionário.

Medido na `main` de 23/11/2026 (`8670cdc`), em SQLite local, com 80 recomendações gravadas em 01/11/2023 e 10 pregões de fechamento (o arranjo do `tests/test_aceite_131.py`), contando `get_connection` de `app.consultor.armazenamento` e as consultas que citam `consultor_fechamentos`:

| Rota | Conexões | Consultas a `consultor_fechamentos` | Tempo |
|---|---|---|---|
| `GET /consultor?data=2023-11-01` | 166 | 403 | 0,161 s |
| `GET /api/consultor?data=2023-11-01` | 8 | 6 | 0,016 s |

Em produção o banco é Postgres remoto (Render): cada consulta é uma ida e volta pela rede, e a página é o que a pessoa abre ao trocar a data no seletor. O resto dos dois blocos é igual linha a linha (o dicionário de cada item, a mensagem, as opiniões históricas), e qualquer mudança no texto ou na regra tem de ser feita duas vezes; a 131 já mostrou que uma das cópias fica para trás.

Medida de tamanho: o que muda referencia `app/main.py` e o módulo novo; `grep -rln "api/consultor\|\"/consultor" tests` dá 23 arquivos que **chamam** as rotas, nenhum que importe os blocos. Nenhum teste existente muda de asserção.

## Comportamento esperado
Nada muda na tela de `/consultor?data=` nem no JSON de `/api/consultor?data=`. Muda onde o ramo histórico é montado:

1. Uma função nova `consultor_de_pregao_passado(data: str, referencia: datetime | None) -> dict` em `app/consultor/placar.py` (ao lado de `_calcular_excesso`, que ela usa) devolve o `dados` que as duas rotas montam hoje (importando `agrupar_por_ativo` e `fechamentos_das_opinioes` de `app.consultor.sintese` e as leituras de `app.consultor.armazenamento`; nenhum dos dois importa `placar`, então não há ciclo): `resultados` (os cinco grupos `Comprar`, `Vender`, `Aguardar`, `No radar`, `Sem sinal`, mais qualquer `decisao` gravada fora deles), `ativos_avaliados`, `regras_confianca` (`{}`), `opinioes_recentes`, `opinioes_por_ativo` e `opinioes_status` (`{}`).
2. Ela segue o caminho de hoje do `/api/consultor`: **uma** conexão de `app.consultor.armazenamento` para os fechamentos, a lista de `data_pregao` lida uma vez e os fechamentos de todos os tickers das recomendações mais o `^BVSP` numa consulta só (`WHERE ticker IN (...)`); o laço das recomendações não abre conexão nem consulta o banco.
3. Cada item de `resultados` tem as chaves de hoje (`ticker`, `fechamento`, `regra`, `gatilho`, `consenso`, `justificativa`, `motivo`, `timestamp`, `mensagem_confianca`) e ganha `decisao_tecnica` com a `decisao` gravada, a mesma chave que `calcular_consultor` já entrega (`app/consultor/calculador.py:208`) e que `consultor.html:202` lê. Hoje o ramo histórico não a tem; o Jinja de produção a trata como vazia, o de teste (`StrictUndefined`, `tests/conftest.py`) reprova a página (conferido na revisão: `UndefinedError: 'dict object' has no attribute 'decisao_tecnica'` em `consultor.html:202` com o arranjo da 131). No histórico só a decisão final é gravada (`decisao_final`, lida como `decisao` por `get_recomendacoes`), então `decisao_tecnica` é sempre igual ao grupo; como `justificativa` é `""`, nenhum dos dois ramos do `{% if %}` imprime nada e a tela não muda.
4. `referencia` é o que `_referencia_do_dia(data)` devolve hoje; as rotas continuam chamando `_referencia_do_dia` em `app/main.py` e passam o resultado, para o módulo do Consultor não importar `app.main`.
5. Em `pagina_consultor` e em `api_consultor`, o corpo de `if is_historical:` vira a chamada `dados = consultor_de_pregao_passado(target_data or "", _referencia_do_dia(target_data))` (no `api_consultor`, mais o `_usou_cache = False` de hoje). O `try/except` em volta, o `consenso_yahoo.anexar`, os limiares, o diagnóstico de opiniões e o `TemplateResponse`/`JSONResponse` não mudam.
6. Os `import` locais que só os blocos usavam (`get_recomendacoes`, `ler_consenso`, `get_connection`/`init_db`/`sql_para` do Consultor, `_calcular_excesso`, `get_opinioes_historicas`) saem das duas rotas quando ficarem sem uso, senão o `ruff` (F401) reprova.

## Fontes de dados
Nenhuma fonte nova e nenhuma dependência nova. As mesmas tabelas `consultor_recomendacoes`, `consultor_fechamentos` e as opiniões, pelas mesmas funções de `app.consultor.armazenamento`. Sem fechamento do pregão futuro ou do `^BVSP`, a mensagem continua "ainda sem resultado", como hoje.

## Cálculos
Os de hoje, sem mudança de fórmula nem de texto. Para cada recomendação gravada no pregão `D` (os 10 primeiros caracteres do `timestamp`), com `dps` a lista ordenada e sem repetição de `data_pregao` de `consultor_fechamentos`:

- `D` fora de `dps` → "ainda sem resultado".
- `offset = min(5, len(dps) − 1 − índice de D)`; `offset = 0` → "ainda sem resultado".
- Senão, `F = dps[índice de D + offset]`, e com os fechamentos `p_F` (ativo em `F`), `ibov_D` e `ibov_F` (`^BVSP` em `D` e `F`), todos presentes: `excesso = (p_F / preco − 1) − (ibov_F / ibov_D − 1)`, onde `preco` é o `preco` gravado na recomendação (reais por ação). Falta qualquer um dos três → "ainda sem resultado".
- Mensagem: `f"{'+' if excesso > 0 else ''}{excesso * 100:.1f}% contra o IBOV em {offset} pregões"`.

Exemplo de ponta a ponta, do banco à tela (o arranjo do `tests/test_aceite_131.py`):

- `consultor_recomendacoes`: `TICK1`, `timestamp = "2023-11-01 18:00:00 BRT"`, `decisao_final = "Comprar"`, `preco = 10.0` (R$ por ação).
- `consultor_fechamentos`: pregões de 01/11 a 10/11/2023 (10 datas); `TICK1` fecha `10,0 × (1 + 0,02·i)` e `^BVSP` fecha `100,0 × (1 + 0,01·i)` pontos no pregão `i` (0 a 9).
- `D = 2023-11-01`, índice 0, `offset = min(5, 9) = 5`, `F = 2023-11-06`.
- `p_F = 11,0`, `ibov_D = 100,0`, `ibov_F = 105,0` → `excesso = (11,0/10,0 − 1) − (105,0/100,0 − 1) = 0,10 − 0,05 = 0,05`.
- A página e o JSON mostram `+5.0% contra o IBOV em 5 pregões` (com ponto: o texto é o de hoje, ver *Fora do escopo*).
- Com `D = 2023-11-10` (último pregão), `offset = 0` → `ainda sem resultado`. Com `D = 2023-11-09`, `offset = 1` → `em 1 pregões`.

Medida que a spec promete (registrada no relatório da entrega, com o mesmo arranjo de 80 recomendações): `GET /consultor?data=` faz **no máximo 8** conexões e **no máximo 6** consultas a `consultor_fechamentos`, as mesmas do `/api/consultor` de hoje; `app/main.py` perde **pelo menos 100 linhas** (`wc -l` antes e depois).

## Critérios de aceite
`tests/test_aceite_193.py`, com `exigir_spec_done("193")`, sem internet, no SQLite de teste:

- [ ] Com o arranjo do exemplo (80 recomendações `Comprar` em 01/11/2023 e 10 pregões), `GET /consultor?data=2023-11-01` responde 200, a página contém `+5.0% contra o IBOV em 5 pregões`, e, espiando `app.consultor.armazenamento.get_connection` como a 131, abre no máximo 8 conexões.
- [ ] No mesmo arranjo, o número de consultas que citam `consultor_fechamentos` durante `GET /consultor?data=2023-11-01` é o mesmo com 1 e com 80 recomendações (o laço não consulta o banco).
- [ ] `consultor_de_pregao_passado("2023-11-01", None)` devolve `resultados["Comprar"]` com 80 itens, cada um com `mensagem_confianca == "+5.0% contra o IBOV em 5 pregões"` e `decisao_tecnica == "Comprar"`; com a data `2023-11-09`, `"em 1 pregões"`; com `2023-11-10`, `"ainda sem resultado"`; sem o `^BVSP` em `F`, `"ainda sem resultado"`.
- [ ] Com `app.consultor.consenso_yahoo.anexar` trocado por uma função que não faz nada (`monkeypatch`), os `resultados` do JSON de `GET /api/consultor?data=2023-11-01` e os que a função devolve para a mesma data são iguais (comparação de dicionário, item a item).
- [ ] O texto de `pagina_consultor` e de `api_consultor` (`inspect.getsource`) não contém mais `consultor_fechamentos` nem `_calcular_excesso`: o histórico vem só da função.
- [ ] Os testes que já existem passam sem mudança de asserção (`make verify`), em especial `tests/test_aceite_131.py`, `tests/test_aceite_113b.py`, `tests/test_aceite_190.py` e `tests/test_aceite_191.py`.

Ordem sugerida: escrever primeiro o terceiro e o quarto critérios contra uma cópia do bloco do `/api/consultor` movida para a função, e só depois trocar as duas rotas.

## Invariantes de produção
- `GET /consultor?data=<pregão da janela>` responde 200 e mostra, em cada recomendação, `ainda sem resultado` ou `±X.X% contra o IBOV em N pregões` com 1 ≤ N ≤ 5, o mesmo texto que `GET /api/consultor?data=<mesmo pregão>` traz em `mensagem_confianca` para o mesmo ticker.
- Para o mesmo pregão, o número de recomendações por grupo é igual na página e no JSON.
- O tempo de `GET /consultor?data=` de um pregão com recomendações gravadas não passa de 3 s (antes, ~4 consultas por recomendação ao Postgres).

## Fora do escopo
- O texto da mensagem: ponto decimal (`+5.0%`) e plural fixo (`em 1 pregões`) ficam como estão; o padrão brasileiro dela entra no resto do item *Preço-alvo no padrão brasileiro* do backlog, junto com `gatilho` e `motivo`.
- O diagnóstico de opiniões (`opinioes_diagnostico`, ~60 linhas iguais nas duas rotas, com a consulta a `consultor_fila_materias`): fica no backlog, no resto do item desta spec.
- O ramo do pregão corrente (`calcular_consultor()`), o cache e a medição de tempo do `/api/consultor`.
- A leitura de `consultor_fechamentos` por todas as datas dos tickers (`WHERE ticker IN (...)` sem filtro de data): é o que a 131 entregou e o volume cabe hoje; restringir à janela `D..F` é otimização separada.
