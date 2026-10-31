---
id: 2026-10-31-historico-pregoes
severidade: alta
painel: sistema.verificar_historico_pregoes
status: aberto
visto_em: 2026-10-31T01:00-03:00
pr: 641
---

# Falso positivo em "Histórico de pregões" durante o pregão

## O que acontece
`app/services/sistema.py` em `verificar_historico_pregoes`, ao listar os dias recentes esperados, chamava `pregao_corrente` mas tratava o pregão que ainda está rodando como um dia do qual já se espera ter todos os snapshots, resultando em falsos positivos se executado durante as horas de mercado ativo antes do fechamento. O PR 641 piorou a situação introduzindo o uso direto de `pregao_corrente` para construir os 5 últimos pregões esperados (incluindo o que nem fechou ainda).

## O que deveria acontecer
Durante o horário de mercado (antes do fechamento do pregão de hoje), o sistema de checagem do "Histórico de pregões" para saúde só deve esperar que o dia atual tenha sido coletado *se ele já terminou*. Portanto, a janela de verificação para "snapshot faltando" deve começar a partir do `ultimo_pregao_fechado` e não do `pregao_corrente`, como o `PRODUTO.md` recomenda para checagem de dados que só consolidam após as 18h15. Se o PR já foi entregue sem resolver, o achado deveria alertar o desenvolvedor.

## Evidência
Falso problema apareceu na saúde da produção em `<https://devagent-vb52.onrender.com/api/sistema>` (Issue #642 e PR 641 introduziu o bug).

## Como reproduzir
Avalie o método passando uma string datetime em plena tarde de pregão (e.g., "2026-10-29T16:00-03:00") e perceba que ele espera as janelas fechadas daquele dia.
