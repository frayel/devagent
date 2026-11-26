---
id: 198
titulo: O diagnóstico de opiniões do Consultor sai de uma função só
status: ready
esforco: P
gaveta: saúde técnica
aceite: tests/test_aceite_198.py
origem: Uma função para `/consultor` e `/api/consultor`
revisada: 2026-11-26
---

## Problema
Quantas matérias esperam a extração de opiniões? A página `/consultor` e o `/api/consultor` montam o diagnóstico de opiniões (`opinioes_diagnostico`, o aviso que aparece quando a lista *Opiniões Recentes* está vazia, e o rodapé "Última extração: ...") por dois blocos de ~60 linhas quase iguais em `app/main.py` (`pagina_consultor`, linhas ~703–775; `api_consultor`, linhas ~849–917, na `main` de 25/11/2026, `b1104e6`). É o resto do item 14 da *Fila* do backlog; a spec 193 já levou o ramo histórico das recomendações para uma função só.

A duplicação esconde dois defeitos que o usuário vê:

1. **A fila é contada no banco errado.** As duas cópias fazem `from app.database import get_connection` e contam `SELECT COUNT(*) FROM consultor_fila_materias WHERE processada = 0`. Esse `get_connection` (`app/database.py:147`) abre sempre o SQLite local (`DATABASE_PATH`, padrão `data.db`). Quem grava e consome a fila usa `app.banco.get_connection` por `app.consultor.armazenamento` (`armazenamento.py:646` e `:684` inserem; `app/services/consultor_opinioes.py:129` e `:158` leem e marcam), que em produção é o Postgres de `DATABASE_URL` (`PRODUTO.md`, seção 3). O SQLite local também tem a tabela (`app/database.py:270`), vazia. Resultado em produção: `fila_pendentes` é sempre 0. O código `fila` ("N matérias na fila, a próxima extração é na próxima rodada.") nunca aparece; no lugar dele sai `sem_materias` ("Nenhuma matéria das fontes citou ativos do Ibovespa...") mesmo com matérias esperando, e `aguardando` diz "Há 0 matérias na fila." Nos testes os dois `get_connection` caem no mesmo SQLite, por isso nenhum teste viu. São as duas únicas chamadas a `app.database.get_connection` fora de `app/banco.py` (`grep -rn "from app.database import get_connection" app`).
2. **O pregão passado fala do agora, e errado.** Em `/consultor?data=<pregão passado>`, `consultor_de_pregao_passado` (`app/consultor/placar.py:79`) devolve `opinioes_status: {}`. O `{}` é falso, as duas cópias trocam por um status padrão com `ultima_extracao_em = ""`, e o diagnóstico vira `aguardando`: a página de um pregão sem opiniões diz "Aguardando a primeira extração. Há N matérias na fila." (N da fila de hoje), e o rodapé diz "Última extração: nunca · matérias processadas em 24 h: 0 · ..." em **todo** pregão passado, com ou sem opiniões, embora a extração rode todo dia.

Há ainda uma diferença entre as cópias: na página, um erro no bloco vira `{"codigo": "erro"}`; no JSON, um erro antes de `fontes_opiniao = {...}` deixa a variável sem valor e a rota responde 500 (`NameError` no `return`).

Medida de tamanho: o que muda referencia `app/main.py`, `app/consultor/armazenamento.py` (uma função de contagem), um módulo novo e `app/templates/consultor.html`. `grep -rl "opinioes_diagnostico\|fontes_opiniao\|consultor_fila_materias" tests` dá 6 arquivos (`test_aceite_084`, `085`, `157`, `158`, `168`, `test_consultor_opinioes`), que chamam as rotas ou gravam na fila; nenhum importa os blocos. Nenhum teste existente muda de asserção.

## Comportamento esperado
1. Uma função nova `contar_fila_pendente() -> int` em `app/consultor/armazenamento.py` conta `consultor_fila_materias WHERE processada = 0` pelo `get_connection` do próprio módulo (o de `app.banco`, o mesmo das gravações), com `init_db()` antes, como as vizinhas. Erro de banco propaga (quem trata é a função do item 2).
2. Uma função nova `diagnostico_de_opinioes(dados: dict | None, pregao_passado: bool) -> dict` num módulo novo `app/consultor/diagnostico.py` devolve o dicionário que as duas rotas montam hoje, sempre com as oito chaves `codigo`, `motivo`, `desde`, `ultima_extracao_em`, `materias_processadas`, `opinioes_gravadas`, `descartadas` e `fila_pendentes`:
   - **Pregão de hoje** (`pregao_passado=False`): a mesma árvore de decisão de hoje (`sem_chave`, `cota`, `erro`/`invalido` → `erro`, nunca extraído → `aguardando`, `ok` com fila → `fila`, `ok` sem opiniões com descartadas → `descartadas`, `ok` sem opiniões → `sem_materias`, senão `ok`), com `fila_pendentes = contar_fila_pendente()`.
   - **Pregão passado** (`pregao_passado=True`): `codigo = "pregao_passado"`, sem consultar a fila (`fila_pendentes = None`) e com os campos de status vazios (`""` e `0`): o status da extração é de agora, não daquele dia.
   - **Qualquer exceção** (inclusive de `contar_fila_pendente`): `codigo = "erro"`, `motivo = "diagnóstico indisponível"` e as outras chaves com os padrões (`""`, `0`, `fila_pendentes = None`). A função nunca levanta.
3. `pagina_consultor` e `api_consultor` trocam o bloco pelo resultado de `diagnostico_de_opinioes(dados, is_historical)`. No `api_consultor`, `fontes_opiniao` passa a ser montado fora do `try`, com `diagnostico` e `fila` (= `fila_pendentes` do diagnóstico) vindos da função e `llm` e `feeds` como hoje; a rota não responde 500 por erro no diagnóstico. Os `import` locais que só o bloco usava (`from app.database import get_connection`, `cast`, `Dict`) saem, senão o `ruff` (F401) reprova.
4. Em `consultor.html`, com `opinioes_diagnostico.codigo == "pregao_passado"` e a lista vazia (a condição que o aviso já usa, `{% if not opinioes_por_ativo %}`), o aviso é `Nenhuma opinião gravada nos 30 dias até dd/mm/aaaa.` (a data do pregão: `data_referencia.strftime('%d/%m/%Y')`, como em `base.html`; não o filtro `data_brasilia`, que converte fuso e pode trocar o dia), e o rodapé "Última extração: ..." não aparece. Em pregão de hoje, aviso e rodapé ficam como estão. Nenhuma classe CSS nova.

## Fontes de dados
Nenhuma fonte nova e nenhuma dependência nova. A tabela `consultor_fila_materias` e o status de `consultor_opinioes_status`, pelas funções de `app.consultor.armazenamento`. Banco fora do ar: o diagnóstico sai `erro` com o motivo "diagnóstico indisponível", a lista de opiniões e as recomendações seguem como hoje.

## Cálculos
Sem fórmula nova; a contagem e a árvore de decisão de hoje, lidas no banco certo. Exemplo de ponta a ponta (o arranjo do aceite):

- Banco do Consultor (`app.banco.get_connection`; em produção o Postgres): `consultor_fila_materias` com 10 linhas, 7 com `processada = 0` e 3 com `processada = 1`.
- SQLite local de `app.database.get_connection` (outro arquivo): `consultor_fila_materias` vazia.
- `consultor_opinioes_status`: `status = "ok"`, `ultima_extracao_em = "2026-11-25T14:00:00Z"`, `descartadas = 0`. Nenhuma opinião nos 30 dias.
- Hoje: `fila_pendentes = 0` (SQLite local) → `codigo = "sem_materias"` → a página diz "Nenhuma matéria das fontes citou ativos do Ibovespa com opinião de casa de análise nos últimos 30 dias."
- Depois: `fila_pendentes = 7` (banco do Consultor) → `codigo = "fila"` → a página diz `7 matérias na fila, a próxima extração é na próxima rodada.` e o JSON traz `fontes_opiniao.fila == 7` e `fontes_opiniao.diagnostico.fila_pendentes == 7`.
- Mesmo arranjo, `GET /consultor?data=<pregão passado sem opiniões>` (ex.: `2023-11-01`): `codigo = "pregao_passado"` → `Nenhuma opinião gravada nos 30 dias até 01/11/2023.`, sem "Aguardando a primeira extração" e sem "Última extração: nunca".

## Critérios de aceite
`tests/test_aceite_198.py`, com `exigir_spec_done("198")`, sem internet. Para separar os dois bancos no teste, `app.banco.get_connection` (e o nome importado em `app.consultor.armazenamento`) é trocado por `monkeypatch` por uma função que abre um segundo arquivo SQLite em `tmp_path` e devolve a tupla `(conn, "sqlite_efemero")`, como o original; antes, `armazenamento.reset_db_init()` (ou `monkeypatch.setattr(armazenamento, "_consultor_db_initialized", False)`, como a `test_aceite_129`), para o `init_db()` do Consultor criar as tabelas nesse arquivo; o `DATABASE_PATH` de `app.database` continua no SQLite de teste, com a fila vazia.

- [ ] Com o arranjo do exemplo, `contar_fila_pendente()` devolve 7.
- [ ] `GET /consultor` (pregão de hoje) responde 200 e contém `7 matérias na fila, a próxima extração é na próxima rodada.`; `GET /api/consultor` traz `fontes_opiniao.fila == 7` e `fontes_opiniao.diagnostico.codigo == "fila"`.
- [ ] `diagnostico_de_opinioes(dados, False)` devolve, para cada status de hoje, o mesmo `codigo` da árvore atual: `sem_chave`, `cota`, `erro` (com `erro` e com `invalido`), `aguardando` (sem `ultima_extracao_em`), `fila`, `descartadas`, `sem_materias` e `ok` (um caso por código, com `dados` montado à mão).
- [ ] `diagnostico_de_opinioes({"opinioes_status": {}, "opinioes_recentes": []}, True)` devolve `codigo == "pregao_passado"` e `fila_pendentes is None`, sem chamar `contar_fila_pendente` (um `monkeypatch` que levanta prova que não é chamada).
- [ ] Com `contar_fila_pendente` trocado por uma função que levanta, `diagnostico_de_opinioes(dados, False)` devolve `codigo == "erro"` com as oito chaves, e `GET /api/consultor` responde 200 com `fontes_opiniao.diagnostico.codigo == "erro"`.
- [ ] `GET /consultor?data=2023-11-01` (o arranjo de pregões da 193, sem opiniões) contém `Nenhuma opinião gravada nos 30 dias até 01/11/2023.` e não contém `Aguardando a primeira extração` nem `Última extração: nunca`; `GET /api/consultor?data=2023-11-01` traz `fontes_opiniao.diagnostico.codigo == "pregao_passado"`.
- [ ] O texto de `pagina_consultor` e de `api_consultor` (`inspect.getsource`) não contém `consultor_fila_materias` nem `app.database import get_connection`; `grep -rn "from app.database import get_connection" app` só acha `app/banco.py`.
- [ ] Os testes que já existem passam sem mudança de asserção (`make verify`), em especial `tests/test_aceite_085.py`, `tests/test_aceite_131.py`, `tests/test_aceite_157.py`, `tests/test_aceite_168.py` e `tests/test_aceite_193.py`. A 131 e a 193 contam as conexões de `armazenamento.get_connection` no pregão passado; o ramo `pregao_passado` não chama `contar_fila_pendente`, por isso a contagem não sobe. No pregão de hoje a contagem passa a abrir uma conexão do banco do Consultor no lugar da do SQLite local.

Ordem sugerida: primeiro o terceiro critério, com a árvore copiada do `api_consultor` para a função; depois a contagem no banco certo; por último as rotas e o template.

## Invariantes de produção
- Em `GET /api/consultor`, `fontes_opiniao.fila` é igual a `fontes_opiniao.diagnostico.fila_pendentes`, e é um inteiro ≥ 0 no pregão de hoje (ou `null` com `codigo == "erro"`).
- Quando `fontes_opiniao.fila > 0` e o status é `ok` com extração já feita, `fontes_opiniao.diagnostico.codigo == "fila"`.
- `GET /consultor?data=<pregão passado da janela>` responde 200 e não contém `Aguardando a primeira extração` nem `Última extração: nunca`.
- `GET /api/consultor` responde 200 mesmo com o banco do Consultor fora do ar no momento do diagnóstico.

## Fora do escopo
- O status da extração **daquele** pregão (quantas matérias foram processadas no dia): o banco guarda só o status corrente (`consultor_opinioes_status` tem uma linha). Se valer a pena, é spec de capacidade nova.
- Mudar os textos dos avisos do pregão de hoje ou a árvore de decisão: ficam como estão.
- A idade da matéria mais antiga da fila (ideia nova da *Fila* do backlog, *A fila de opiniões tem idade*).
- O resto do `api_consultor` (`opinioes_api`, `resultados_dict`, `atualizado_em` sem fuso): fica como está.
