---
id: 126a
titulo: Agendador sem trabalho repetido (backtest único)
status: ready
esforco: P
gaveta: saúde técnica
aceite: tests/test_aceite_126a.py
revisada: 2026-11-03
---

## Problema
A rodada de coleta gasta tempo e banco à toa em um ponto de `app/agendador.py`:

**O backtest do Consultor roda duas vezes.** Depois de `consultor_historico`, o código dispara `avaliador_historico.rodar_backtest` numa thread, com o comentário "não roda bloqueante no fluxo", e em seguida o chama de novo, de forma síncrona. O custo dobra, a rodada fica bloqueada do mesmo jeito e as duas execuções gravam no banco ao mesmo tempo (no SQLite, risco de `database is locked`). Como `consultor_historico` é semanal (todas as rodadas de sábado), isso acontece a cada 2 h no sábado.

## Comportamento esperado
- `rodar_backtest` roda uma única vez por coleta de `consultor_historico`, numa thread `daemon`. Se a execução anterior ainda não terminou, a nova não começa: o agendador registra `consultor_historico: backtest anterior ainda em curso` em `detalhes` e segue.

## Fontes de dados
Nenhuma.

## Cálculos
Nenhum.

## Critérios de aceite
- [ ] Uma rodada que coleta `consultor_historico` chama `rodar_backtest` exatamente uma vez (mock que conta chamadas) e não espera o fim dele.
- [ ] Com um backtest simulado ainda rodando (evento não liberado), uma segunda rodada não inicia outro e registra a mensagem em `detalhes`.
- [ ] `tests/test_agendador.py` continua verde.
- Arquivos tocados: `app/agendador.py` e o novo `tests/test_aceite_126a.py`.

## Invariantes de produção
Nenhuma.

## Fora do escopo
- Deixar o próprio backtest mais rápido.
- A janela de fechamento (spec 125).
