---
id: 126b
titulo: Agendador sem trabalho repetido (feriado fora do pregão)
status: ready
esforco: P
gaveta: saúde técnica
aceite: tests/test_aceite_126b.py
revisada: 2026-11-03
---

## Problema
A rodada de coleta gasta tempo e banco à toa em um ponto de `app/agendador.py`:

**Feriado é tratado como pregão.** `intervalo()` usa `weekday() < 5` e não `calendario.e_pregao`. Em feriado da B3 num dia útil (2/11, 20/11) a coleta roda a cada 15 min o dia inteiro.

## Comportamento esperado
- `intervalo()` usa `calendario.e_pregao(data local)`; em dia sem pregão devolve `FORA_DO_PREGAO`.

## Fontes de dados
Nenhuma.

## Cálculos
Nenhum.

## Critérios de aceite
- [ ] `intervalo()` em 02/11/2026 às 11h BRT devolve 2 h; em 28/10/2026 às 11h BRT, 15 min.
- [ ] `tests/test_agendador.py` continua verde.
- Arquivos tocados: `app/agendador.py` e o novo `tests/test_aceite_126b.py`.

## Invariantes de produção
- Em feriado da B3, `/api/sistema` não mostra rodadas a cada 15 min.

## Fora do escopo
- A janela de fechamento (spec 125).
