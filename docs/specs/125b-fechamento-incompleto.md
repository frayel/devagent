---
id: 125b
titulo: Fechamento que falhou vira incompleto depois das 20h
status: ready
esforco: P
gaveta: saúde técnica
aceite: tests/test_aceite_125b.py
revisada: 2026-11-02
---

## Problema
A spec 077 diz: "...Falhou: nova tentativa a cada 30 min até 20h; depois, \`incompleto\`, com o último dado bom." O agendador (\`app/agendador.py\`) não faz isso:

1. **O \`incompleto\` nunca é gravado.** Depois das 20h, um painel da janela \`pregao\` só é coletado se não houver snapshot do dia (partida a frio). O bloco que marca \`incompleto\` (perto de \`agora_brt.time() > time(20, 0)\`) roda só quando houve coleta e ela falhou, e exige um snapshot existente. As duas condições juntas quase nunca acontecem.
2. **Consequência: o dia some do histórico.** O snapshot do dia fica \`ao_vivo\`, e \`listar_datas\` só lista \`final\`, \`incompleto\` e \`ok\`. Um pregão cuja rodada de fechamento falhou não aparece no seletor da 088.

O mesmo vale quando o Render hiberna o serviço durante a janela de fechamento: ao acordar depois das 20h, o dia fica \`ao_vivo\` para sempre.

## Comportamento esperado
- Em toda rodada em que já passou das 20h do último pregão fechado (no mesmo dia, ou ao acordar no dia seguinte), cada painel da janela \`pregao\` cujo snapshot desse pregão não é \`final\` nem \`incompleto\` é regravado como \`incompleto\`, com o mesmo payload e a mesma fonte, **sem chamar o coletor**. O painel mostra o aviso da 077: "Fechamento incompleto: último dado das HH:MM".
- Painel sem nenhum snapshot desse pregão segue a partida a frio, como hoje.
- \`detalhes\` de \`/api/coleta\` registra \`NOME: incompleto\` para cada painel marcado.

## Fontes de dados
Nenhuma nova.

## Cálculos
Nenhum.

## Critérios de aceite
- [ ] Com o snapshot \`ao_vivo\` de D num painel \`pregao\`, uma rodada às 20h05 de D grava \`incompleto\` em D com o mesmo payload, sem chamar \`collect_and_save\` desse painel.
- [ ] A mesma rodada às 08h de D+1 (o serviço dormiu) produz o mesmo resultado.
- [ ] Snapshot \`final\` continua \`final\`.
- [ ] Depois da marcação, \`listar_datas("ibovespa")\` inclui D.
- [ ] \`tests/test_agendador.py\` continua verde.
- Arquivos tocados: \`app/agendador.py\` e o novo \`tests/test_aceite_125b.py\`.

## Invariantes de produção
- Todo pregão dos últimos 5 no calendário da B3 tem snapshot do Ibovespa \`final\` ou \`incompleto\` (o item "Histórico de pregões" de \`/sistema\` não acusa dia faltando).

## Fora do escopo
- \`app/agendador_patched.py\`, que é código morto (spec 133).
- Mudar os horários da 077.
- Alterar o intervalo de tentativas de fechamento antes das 20h (spec 125a).
