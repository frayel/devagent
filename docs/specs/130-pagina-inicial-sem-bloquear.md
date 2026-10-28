---
id: 130
titulo: Página inicial sem bloquear o servidor
status: ready
esforco: M
gaveta: saúde técnica
aceite: tests/test_aceite_130.py
revisada: 2026-10-28
---

## Problema
`index` (`app/main.py`) é `async def`, mas não tem nenhum `await`: faz cerca de 40 leituras síncronas do banco (via `get_latest_*` e `get_*_view_data`) dentro do event loop. Enquanto uma visita monta a página, o servidor não responde a nada, nem a `/healthz` (usado pelo health check do Render).

Além disso, há leitura repetida:
- `get_ibovespa_view_data()` é chamada duas vezes (`ibovespa_data` e `data_ibov`);
- `get_latest_highlights_data()` e `get_highlights_view_data()` leem o mesmo snapshot;
- `get_latest_apetite_risco_data()` e `get_apetite_risco_view_data()` também.

## Comportamento esperado
- `index` passa a `def`, e o FastAPI a roda no threadpool. Nenhuma outra rota síncrona fica `async def` sem `await`.
- Cada snapshot é lido no máximo uma vez por requisição: um cache por requisição dentro de `ler_snapshot` (um `ContextVar` com um dicionário, aberto e fechado pela rota). O primeiro acesso carrega numa só consulta o snapshot mais recente (ou o do dia, dentro de `lendo_pregao` da spec 124) de todos os painéis: `DISTINCT ON (painel)` no Postgres, `ROW_NUMBER()` no SQLite.
- As chamadas duplicadas da lista acima saem.
- Fora de requisição (agendador), `ler_snapshot` continua consultando o banco a cada chamada.

## Fontes de dados
Nenhuma.

## Cálculos
Nenhum.

## Critérios de aceite
- [ ] `GET /` com snapshots fixture de todos os painéis executa no máximo 3 consultas a `snapshots_paineis` (espião em `cursor.execute`).
- [ ] Com `ler_snapshot` atrasado artificialmente em 1 s, uma requisição a `/healthz` disparada durante um `GET /` em andamento responde em menos de 200 ms (`httpx.AsyncClient` com `ASGITransport` e `asyncio.gather`).
- [ ] `GET /?data=D1` continua trazendo os números de D1 (critério da spec 124).
- [ ] Um teste percorre as rotas do app e reprova `async def` cujo corpo não tem `await`.
- [ ] Os testes de página existentes (`tests/test_aceite_088.py` e os de painéis) continuam verdes.
- Arquivos tocados: `app/main.py`, `app/banco.py` e o novo `tests/test_aceite_130.py`.

## Invariantes de produção
- `/healthz` responde em menos de 1 s mesmo durante a coleta e visitas simultâneas à página.

## Fora do escopo
- Cache entre requisições.
- Unificar a montagem dos painéis de `index` e `/api/snapshot` (ideia no backlog).
- Depende da spec 124 (contexto de leitura): implementar depois dela.
