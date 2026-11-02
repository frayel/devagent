---
id: 125a
titulo: Intervalo de tentativa de fechamento a cada 30 min até 20h
status: ready
esforco: P
gaveta: saúde técnica
aceite: tests/test_aceite_125a.py
revisada: 2026-11-02
---

## Problema
A spec 077 diz: "Rodada de fechamento: a primeira depois das 18h15 BRT em dia de pregão. Snapshot gravado com sucesso nela vira \`final\`. Falhou: nova tentativa a cada 30 min até 20h...". O agendador (\`app/agendador.py\`) não faz isso:

**Não há nova tentativa a cada 30 min.** \`intervalo()\` devolve 2 h assim que passa de \`FIM_PREGAO\` (18h15). Entre 18h15 e 20h cabe uma rodada só.

## Comportamento esperado
- \`intervalo()\` devolve 30 min entre \`FIM_PREGAO\` e 20h em dia de pregão.

## Fontes de dados
Nenhuma nova.

## Cálculos
Nenhum.

## Critérios de aceite
- [ ] \`intervalo()\` às 18h40 BRT de um dia de pregão devolve 30 min; às 20h10, 2 h.
- [ ] \`tests/test_agendador.py\` continua verde.
- Arquivos tocados: \`app/agendador.py\` e o novo \`tests/test_aceite_125a.py\`.

## Invariantes de produção
Nenhuma (as de fechamento final ficam na 125b).

## Fora do escopo
- \`app/agendador_patched.py\`, que é código morto (spec 133).
- Marcar o estado como \`incompleto\` após 20h (spec 125b).
