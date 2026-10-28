---
id: 126
titulo: Agendador sem trabalho repetido (backtest único, feriado fora do pregão)
status: ready
esforco: P
gaveta: saúde técnica
aceite: tests/test_aceite_126.py
---

## Problema
A rodada de coleta gasta tempo e banco à toa em dois pontos de `app/agendador.py`:

1. **O backtest do Consultor roda duas vezes.** Depois de `consultor_historico`, o código dispara `avaliador_historico.rodar_backtest` numa thread, com o comentário "não roda bloqueante no fluxo", e em seguida o chama de novo, de forma síncrona. O custo dobra, a rodada fica bloqueada do mesmo jeito e as duas execuções gravam no banco ao mesmo tempo (no SQLite, risco de `database is locked`). Como `consultor_historico` é semanal (todas as rodadas de sábado), isso acontece a cada 2 h no sábado.
2. **Feriado é tratado como pregão.** `intervalo()` usa `weekday() < 5` e não `calendario.e_pregao`. Em feriado da B3 num dia útil (2/11, 20/11) a coleta roda a cada 15 min o dia inteiro.

## Comportamento esperado
- `rodar_backtest` roda uma única vez por coleta de `consultor_historico`, numa thread `daemon`. Se a execução anterior ainda não terminou, a nova não começa: o agendador registra `consultor_historico: backtest anterior ainda em curso` em `detalhes` e segue.
- `intervalo()` usa `calendario.e_pregao(data local)`; em dia sem pregão devolve `FORA_DO_PREGAO`.

## Fontes de dados
Nenhuma.

## Cálculos
Nenhum.

## Critérios de aceite
- [ ] Uma rodada que coleta `consultor_historico` chama `rodar_backtest` exatamente uma vez (mock que conta chamadas) e não espera o fim dele.
- [ ] Com um backtest simulado ainda rodando (evento não liberado), uma segunda rodada não inicia outro e registra a mensagem em `detalhes`.
- [ ] `intervalo()` em 02/11/2026 às 11h BRT devolve 2 h; em 28/10/2026 às 11h BRT, 15 min.
- [ ] `tests/test_agendador.py` continua verde.
- Arquivos tocados: `app/agendador.py` e o novo `tests/test_aceite_126.py`.

## Invariantes de produção
- Em feriado da B3, `/api/sistema` não mostra rodadas a cada 15 min.

## Fora do escopo
- Deixar o próprio backtest mais rápido.
- A janela de fechamento (spec 125).
