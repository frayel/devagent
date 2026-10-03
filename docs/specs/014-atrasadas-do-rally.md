---
id: 014
titulo: Atrasadas do Rally (Laggards)
status: ready
esforco: M
---

## Problema
Em dias em que o mercado (Ibovespa) está em alta recente forte, o investidor frequentemente procura por "laggards" - ações que ficaram para trás e ainda não acompanharam o movimento de alta, buscando oportunidades de compra mais baratas dentro do rally.

## Comportamento esperado
Um novo painel na seção analítica da página inicial mostrando "Atrasadas do Rally".
Exibe uma lista curta (top 3) das ações de alta liquidez que mais caíram ou menos subiram nos últimos 5 pregões, considerando dias em que o Ibovespa subiu forte no mesmo período.
Incluirá a variação da ação nos últimos 5 dias vs variação do Ibovespa no mesmo período.

## Fontes de dados
- `yfinance` para histórico (últimos 5-10 pregões) de 30 tickers líquidos e do Ibovespa (`^BVSP`).
- Se yfinance falhar, o painel exibe "Dados não disponíveis".

## Cálculos
1. Calcular o retorno acumulado do Ibovespa nos últimos 5 pregões.
2. Se o retorno do Ibov for positivo e > 2%, calcular o retorno acumulado das 30 ações de alta liquidez no mesmo período.
3. Subtrair o retorno da ação do retorno do Ibov (Retorno Ibov - Retorno Ação).
4. Ordenar pelas maiores diferenças positivas (ações que ficaram para trás em relação ao Ibov).
5. Se o Ibov não estiver num rally (>2% em 5 dias), exibir "Ibovespa sem rally recente".

## Critérios de aceite
- [ ] O painel aparece no snapshot com os dados corretos (`atrasadas_rally`).
- [ ] Mostra corretamente o caso em que o Ibov não subiu >2% em 5 dias.
- [ ] O painel é renderizado corretamente, seguindo as diretrizes de design.

## Invariantes de produção
- Apenas exibe dados se a coleta do histórico estiver bem-sucedida.

## Fora do escopo
- Ações ilíquidas fora do universo de 30 ações mapeado (e.g. BOVA11, small caps).
