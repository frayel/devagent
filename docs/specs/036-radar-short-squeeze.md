---
id: 036
titulo: Radar de Short Squeeze (Capitulação Vendida)
status: ready
esforco: M
---

## Problema
Responde: Uma ação que vinha caindo muito recentemente, hoje está sofrendo uma alta violenta que pode caracterizar um "short squeeze" (fechamento forçado de posições vendidas)?

## Comportamento esperado
Criar um painel de alerta na seção "Alertas Intraday" que lista ações que apresentam queda acumulada superior a 10% nos últimos 10 pregões, mas que hoje apresentam alta superior a 4% com volume pelo menos 2x maior que a média histórica recente.

## Fontes de dados
yfinance (histórico de 15 dias em fechamentos diários para checar a queda e volume médio, junto com os dados intradiários ou diários de hoje para verificação de alta atual).

## Cálculos
- Identificar variação percentual dos últimos 10 pregões (fechamento atual / fechamento de 10 dias atrás - 1). Filtrar <= -10%.
- Checar se a variação no pregão atual está >= 4%.
- Checar se o volume de hoje está >= 2x a média de volume dos últimos 10 pregões.
- Ações que cumprirem as 3 condições aparecem no painel.

## Critérios de aceite
- [ ] O painel aparece listando as ações que satisfazem as regras, com a alta de hoje e o multiplicador de volume.
- [ ] A lógica possui testes mockados localmente sem requisições reais.

## Invariantes de produção
- Uma nova chave `short_squeeze` aparece no `/api/snapshot`.
- O `make audit` continua passando e não é afetado negativamente por essa inclusão.

## Fora do escopo
Checagem real de saldo de aluguel de ações na B3 (já que a disponibilidade de API para isso é inviável).
