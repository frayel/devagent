---
id: 128
titulo: Postgres configurado não cai em silêncio para o SQLite
status: ready
esforco: M
gaveta: saúde técnica
aceite: tests/test_aceite_128.py
---

## Problema
`_determine_backend` (`app/banco.py`) testa o Postgres com duas tentativas de 10 s. Se as duas falham, devolve `sqlite_efemero`, e `get_backend_type` guarda esse resultado até o processo morrer. Na prática:

1. **Os dados se perdem.** Uma oscilação do Neon na hora do boot faz a instância inteira gravar num SQLite que some no próximo restart, até o próximo deploy ou hibernação. Coletas, snapshots `final` e recomendações do Consultor desse período desaparecem.
2. **O boot trava.** O teste roda já na importação de `app.main`, por causa do global `templates.env.globals["render_no_db"]`. Com o Postgres fora, o processo leva até cerca de 22 s para subir.
3. **O código contradiz a regra que ele mesmo cita.** O comentário em `get_connection` registra a decisão de revisão: "se um banco está configurado explicitamente, falhas de conexão devem propagar (fail fast) em vez de cair em silêncio para outro backend". O `_determine_backend` faz o contrário.

## Comportamento esperado
- Com `DATABASE_URL` definida, o backend é **sempre** `postgres`. A aplicação nunca abre nem cria SQLite nesse caso.
- Nenhuma conexão é tentada na importação de módulo. `render_no_db` e equivalentes são calculados na primeira requisição ou no `lifespan`, sem bloquear o boot.
- Postgres inacessível:
  - leituras devolvem `None` ou vazio, e os painéis mostram "Dado indisponível agora";
  - gravações levantam erro, que o agendador já registra em `ultimo_erro`;
  - um disjuntor evita pagar o timeout de conexão em toda chamada: depois de uma falha, as chamadas dos 30 s seguintes falham na hora, sem tentar conectar; passado esse prazo, a próxima chamada tenta de novo.
- A aplicação volta a usar o Postgres sozinha quando ele volta, sem restart.
- `/sistema`, item "Banco de dados": *Problema* com "Postgres configurado e inacessível desde HH:MM" enquanto o disjuntor estiver aberto.
- Sem `DATABASE_URL` (desenvolvimento local, testes), o SQLite segue como hoje.

## Fontes de dados
Nenhuma.

## Cálculos
Nenhum.

## Critérios de aceite
- [ ] Com `DATABASE_URL=postgresql://u:p@127.0.0.1:1/x`, `import app.main` termina em menos de 1 s.
- [ ] Nessa configuração, `GET /healthz` e `GET /` respondem 200, e nenhum arquivo SQLite é criado em `DATABASE_PATH`.
- [ ] Duas leituras seguidas, em menos de 30 s, chamam `psycopg.connect` uma vez só (espião). Com o relógio avançado 31 s, a terceira tenta de novo.
- [ ] Com o espião passando a conectar, a leitura seguinte ao fim do prazo devolve dados do Postgres (fake) sem restart.
- [ ] `/api/sistema` traz o item "Banco de dados" em nível *Problema* com o texto acima.
- [ ] `tests/test_banco.py` continua verde.
- Arquivos tocados: `app/banco.py`, `app/main.py`, `app/services/sistema.py` e o novo `tests/test_aceite_128.py`.

## Invariantes de produção
- `GET /api/coleta` (autenticado) nunca responde `"banco": "sqlite_efemero"` com `DATABASE_URL` configurada.

## Fora do escopo
- Pool de conexões (spec 129, que parte desta).
- Fila de gravações para repor o que se perdeu durante a queda.
