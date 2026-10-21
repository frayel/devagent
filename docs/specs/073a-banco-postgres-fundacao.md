---
id: 073a
titulo: Banco · camada única com Postgres e armazenamento do consultor
status: ready
esforco: G
gaveta: saúde técnica
---

## Problema
Pedido do dono do produto (ADR 007): a aplicação precisa de um banco persistente no Postgres para não perder os dados a cada deploy do Render. A spec 073 era grande demais e foi dividida. Esta primeira metade (073a) foca em criar a camada genérica `app/banco.py` (conexão, transação, upsert de snapshots e séries) com fallback para SQLite, e refatorar `app/consultor/armazenamento.py` para utilizar a nova camada, garantindo a fundação técnica sem ainda migrar os painéis existentes.

Depende da spec 072.

## Comportamento esperado
- `app/banco.py`: conexão com Postgres quando `DATABASE_URL` existe; SQLite caso contrário. Mesma interface para os dois, com:
  - `gravar_snapshot(painel, data_referencia, estado, fonte, payload)` (upsert);
  - `ler_snapshot(painel, data_referencia=None)` (sem data: o mais recente);
  - `listar_datas(painel, limite)`;
  - `gravar_serie(ticker, barras)` e `ler_serie(ticker, inicio, fim)`;
  - transação explícita para gravações agrupadas.
- Tabelas `snapshots_paineis` e `series_diarias` conforme o ADR 007, criadas por uma função idempotente chamada ao subir.
- `app/consultor/armazenamento.py` passa a usar `app/banco.py` (usando a conexão e infraestrutura dele), sem mudar o comportamento das specs 068 a 072. O `app/consultor/armazenamento.py` mantém sua função de init e suas tabelas específicas, apenas usando `get_connection()` / pool da nova camada se aplicável, ou unificando `app/banco.py` para prover a conexão comum. (Na prática, `app/banco.py` substitui `get_connection` em `app/database.py`).
- Em produção (`RENDER` definido) sem `DATABASE_URL`: aviso no topo de todas as páginas "Banco persistente não configurado: dados se perdem ao reiniciar" e o mesmo texto em `GET /api/coleta`. A aplicação sobe normalmente.
- Postgres inacessível ao subir: até 2 tentativas com 10 s de timeout; depois, SQLite com o mesmo aviso. Nenhuma página responde 500 por causa do banco.
- `psycopg[binary]` já está em `requirements.txt` desde a spec 072; o pool tem no máximo 3 conexões (usando `psycopg_pool` se necessário ou conexão simples).

## Fontes de dados
Nenhuma nova.

## Cálculos
- Fora de `app/banco.py`, nenhum SQL específico de um dialeto. O upsert e a tradução de parâmetros (`?` no SQLite, `%s` no Postgres) ficam dentro da camada `app/banco.py`.
- O payload de snapshot é JSON serializado com `default=str` para datas.

## Critérios de aceite
- [ ] Os testes da camada rodam contra SQLite em memória e cobrem upsert, leitura do mais recente, leitura por data e listagem de datas.
- [ ] Um teste de contrato garante que `app/banco.py` gera, para Postgres, o SQL esperado de upsert (inspeção da string, sem banco real).
- [ ] Com `RENDER=1` e sem `DATABASE_URL`, a página contém o aviso de banco não persistente e responde 200.
- [ ] Com `DATABASE_URL` apontando para um host inválido, a aplicação sobe, usa SQLite e mostra o aviso.
- [ ] Todos os testes do consultor (specs 068 a 072) continuam passando utilizando o novo sistema de conexão.

## Invariantes de produção
- `GET /api/coleta` informa `banco: "postgres"` em produção.

## Fora do escopo
- Migração dos painéis de caching (Ibovespa, highlights, etc). Ficará para 073b.
- Congelamento e data de referência por pregão (spec 077).
- Seletor de pregões anteriores (spec 078).
