---
id: 2026-10-31-historico-pregoes
severidade: alta
painel: app/services/sistema.py
status: aberto
visto_em: 2026-10-31T11:20:00-03:00
pr: 650
---

# Falso positivo em "Histórico de pregões" usando pregao_corrente em andamento

## O que acontece
Em `app/services/sistema.py`, o método `verificar_historico_pregoes` calcula a janela recente de pregões esperados utilizando a função `pregao_corrente(agora)`. Porém, a função `pregao_corrente` retorna a data de "hoje" mesmo durante o andamento do pregão (antes das 18h15). Quando a avaliação de saúde do sistema roda (ex: à tarde, ou de madrugada), o código cobra o snapshot de hoje que ainda não ocorreu. Como a lista é fixa em 5 posições puxando do pregão atual para trás, as datas mais antigas legítimas acabam saindo da lista ou sendo cobradas prematuramente. A correção feita no PR 650 acentuou o erro exigindo os 5 últimos a partir de "hoje", gerando falso positivo no alerta do monitor de saúde.
Comando que mostra o comportamento: chamar o script gerando uma data às `10:00` durante o pregão.

## O que deveria acontecer
O `verificar_historico_pregoes` deveria usar `ultimo_pregao_fechado(agora)` para criar a janela de 5 dias passados esperados. Um dia em andamento não deveria ser cobrado pela verificação de saúde como "faltando" até que sua janela de fechamento tenha se encerrado (após as 18h15). O histórico só consolida a necessidade do snapshot para os dias concluídos.

## Evidência
A saúde da aplicação está acusando (Issue #651):
`Do 28/10 ao 30/10. Faltam snapshots na janela recente: 2026-10-27, 2026-10-26` porque espera que a lista englobe [31, 30, 29, 28, 27] ou [30, 29, 28, 27, 26] prematuramente dependendo do uso de datas, perdendo o registro correto do histórico.

## Como reproduzir
1. Crie um ambiente python simulando a data e horário atual como um dia de pregão útil antes das 17h.
2. Invoque `verificar_historico_pregoes` e avalie as datas listadas no "esperados".
3. A lista de "faltando" cobrará erroneamente o próprio dia simulado ou esquecerá as datas mais antigas corretas.
