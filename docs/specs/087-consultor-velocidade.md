---
id: 087
titulo: Consultor abre em poucos segundos (consulta única, sem gravar na visita, com cache)
status: ready
esforco: M
gaveta: saúde técnica
aceite: tests/test_aceite_087.py
revisada: 2026-10-24
---

## Problema

A tela do Consultor demora para carregar. A leitura do código aponta quatro causas, todas no caminho de uma visita (`GET /consultor` e `GET /api/consultor`, que chamam `calcular_consultor`):

1. **Uma consulta e uma conexão por ativo.** `app.database.get_historico_diario` chama `app.banco.ler_serie` uma vez por ticker. A carteira tem cerca de 90 ativos, e cada chamada abre uma conexão nova ao Postgres (`psycopg.connect`) e traz até dois anos de barras. São ~90 conexões TLS ao Neon por visita.
2. **DDL a cada operação.** Toda função de `app/consultor/armazenamento.py` (`get_opinioes_recentes`, `get_opinioes_ativos`, `get_opinioes_status`, `save_*`) começa com `init_db()`, que roda cinco `CREATE TABLE IF NOT EXISTS` pela rede, sem guarda de "já inicializado". `app/banco.py::init_db` já tem essa guarda (`_db_initialized`); a do Consultor não.
3. **Escrita dentro da visita.** O fim de `calcular_consultor` chama `save_recomendacoes` e `save_fechamentos`: abrir a página grava no banco. Além de lento, isso faz o diário do Consultor só existir nos dias em que alguém abriu a tela.
4. **Recálculo completo a cada visita.** Todas as regras são reavaliadas para todos os ativos mesmo quando nenhum dado mudou desde a visita anterior.

## Comportamento esperado

1. **Leitura em lote.** Nova função `ler_series(tickers, inicio, fim)` em `app/banco.py`, com uma única consulta (`WHERE ticker = ANY(%s)` no Postgres, `IN (...)` no SQLite) numa única conexão, que devolve `{ticker: [barras]}`. `get_historico_diario` passa a usá-la. `ler_serie` continua existindo para quem pede um ticker só.
2. **Esquema do Consultor inicializado uma vez por processo**, com a mesma guarda de `app/banco.py`, reiniciada em teste por uma função de reset.
3. **Visita só lê.** `save_recomendacoes` e `save_fechamentos` saem de `calcular_consultor`. Passam a ser chamadas por um coletor novo `consultor_fechamento` registrado no agendador com a janela do fechamento do pregão (ADR 008: primeira rodada depois das 18h15 BRT, com novas tentativas a cada 30 min até as 20h). A spec 089 usa esse registro para o histórico; aqui basta mover a escrita e manter a regra de só gravar mudança de decisão.
4. **Cache da visão.** O resultado de `calcular_consultor` fica em memória, indexado por uma *versão dos dados*: o maior `criado_em` das séries lidas, o maior `extraida_em` das opiniões e o horário do status das opiniões. Mesma versão, mesmo resultado, sem recálculo. TTL máximo de 5 minutos. O cache não vale para pregões passados (a spec 089 tem o seu).
5. **Medida.** `/api/consultor` devolve `duracao_ms` (tempo de `calcular_consultor`, com `cache: true|false`) e o grupo *Coleta* de `/sistema` mostra a duração do Consultor ao lado da duração da rodada.

Meta: com o cache quente, `GET /consultor` em até 1 s; a frio, em até 4 s.

## Fontes de dados

Nenhuma nova. Nenhuma dependência nova (sem `psycopg_pool`); a economia vem de usar uma conexão por leitura em lote.

## Critérios de aceite

- [ ] `calcular_consultor()` com 90 tickers de fixture abre no máximo 5 conexões e executa no máximo 12 consultas (teste conta chamadas a `get_connection`).
- [ ] `ler_series` devolve o mesmo conteúdo que chamar `ler_serie` ticker a ticker, nos dois backends (SQLite real, Postgres com conexão falsa conferindo o SQL com `ANY(%s)`).
- [ ] A inicialização do esquema do Consultor roda uma vez: duas chamadas seguidas a `get_opinioes_status` emitem os `CREATE TABLE` só na primeira.
- [ ] `GET /consultor` e `GET /api/consultor` não executam `INSERT` nem `UPDATE` (conexão falsa registra os comandos).
- [ ] Duas chamadas seguidas a `calcular_consultor` com os mesmos dados fazem o cálculo uma vez; mudar uma opinião ou renovar uma série invalida o cache.
- [ ] O coletor `consultor_fechamento` grava recomendações e fechamentos e fica fora da janela de pregão; com a mesma decisão do dia anterior, não duplica linha.
- [ ] `/api/consultor` traz `duracao_ms` e `cache`.

## Invariantes de produção

- `GET /consultor` responde em até 4 s a frio e em até 1,5 s na segunda visita (o auditor mede com a mesma cronometragem que usa nas outras páginas).
- Abrir `/consultor` não altera `consultor_recomendacoes`: a contagem de linhas é a mesma antes e depois da visita.

## Fora do escopo

- Pré-calcular as recomendações em tabela própria.
- Trocar o driver, criar pool de conexões ou mudar o banco.
- Otimizar os demais painéis (o mesmo padrão de `ler_serie` por ticker pode existir neles e vira ideia no backlog).
