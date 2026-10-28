---
id: 129
titulo: Pool de conexões do Postgres
status: ready
esforco: M
gaveta: saúde técnica
aceite: tests/test_aceite_129.py
---

## Problema
Cada leitura e cada gravação em `app/banco.py` (e em `app/consultor/armazenamento.py`, `app/consultor/placar.py`, `app/services/consultor_opinioes.py`) chama `get_connection()`, que abre uma conexão nova com `psycopg.connect(db_url, connect_timeout=10)` e a fecha no fim. Com o Neon, cada conexão nova custa um handshake TCP e TLS.

A página inicial faz cerca de 40 leituras de `snapshots_paineis`, ou seja, cerca de 40 handshakes por visita. A rodada de coleta faz o mesmo para cada um dos 46 coletores, mais as leituras de controle do agendador.

## Comportamento esperado
- Com backend `postgres`, `get_connection()` empresta uma conexão de um `psycopg_pool.ConnectionPool` (`min_size=1`, `max_size=5`, timeout de espera de 10 s), aberto no `lifespan` e fechado no desligamento.
- **A interface não muda:** `conn, backend = get_connection()` e `conn.close()` continuam valendo nos cerca de 36 pontos que já os usam. O objeto devolvido é um invólucro cujo `close()` devolve a conexão ao pool, sem fechá-la. Assim nenhum chamador precisa ser reescrito.
- O pool respeita o disjuntor da spec 128: Postgres fora não trava a requisição esperando o pool.
- `init_db()` roda uma vez no `lifespan`. As chamadas que sobram nas funções continuam baratas (já há a flag).
- `requirements.txt` passa a ter `psycopg[binary,pool]` com versão fixada.
- Sem Postgres (SQLite), nada muda.

## Fontes de dados
Nenhuma.

## Cálculos
Nenhum.

## Critérios de aceite
- [ ] Com o pool trocado por um falso, 40 chamadas seguidas de `ler_snapshot` abrem no máximo 5 conexões físicas (espião em `connect`).
- [ ] `conn.close()` do invólucro devolve a conexão ao pool (o pool falso registra a devolução e nenhuma conexão física é fechada).
- [ ] O desligamento do app fecha o pool.
- [ ] Os testes com SQLite (`tests/test_banco.py`, `tests/test_consultor_armazenamento.py`) continuam verdes sem alteração.
- Arquivos tocados: `app/banco.py`, `app/main.py` (lifespan), `requirements.txt` e o novo `tests/test_aceite_129.py`.

## Invariantes de produção
- O tempo de resposta de `GET /`, medido pelo auditor, não piora em relação à média dos 7 dias anteriores.

## Fora do escopo
- Reescrever os chamadores para `with pool.connection()`.
- Ajustar o tamanho do pool ao plano do Neon (fica para depois de medir).
- Depende da spec 128: implementar depois dela.
