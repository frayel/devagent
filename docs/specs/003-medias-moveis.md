---
id: 003
titulo: Médias Móveis de 21 e 200 dias para o Ibovespa
status: ready
esforco: P
---

## Problema
O investidor quer saber rapidamente se a tendência do Ibovespa a curto e longo prazo é de alta, baixa ou indefinição, sem precisar abrir uma plataforma de gráficos complexa e configurar indicadores.

## Comportamento esperado
- Uma nova seção ou card na tela principal (logo abaixo ou ao lado do Ibovespa Hoje) exibindo "Tendência (Ibovespa)".
- Exibição de dois indicadores:
  - Curto Prazo (Média Móvel de 21 pregões): O valor da média e se o Ibovespa atual está acima (Sinal: Alta) ou abaixo (Sinal: Baixa).
  - Longo Prazo (Média Móvel de 200 pregões): O valor da média e o sinal correspondente.
- As atualizações acompanham o ciclo de atualização das cotações diárias (mesmo timer).

## Fontes de dados
- **Primária:** yfinance (histórico de até `1y` para garantir pelo menos 200 pregões úteis).
- **Fallback:** brapi.dev caso yfinance falhe. Se ambas falharem, exibe "Tendência indisponível".
- **Frequência de coleta:** A mesma do Ibovespa (diária durante o pregão, mantendo a regra de cache do agendador).

## Cálculos
- Coletar o histórico de fechamentos do ticker `^BVSP`.
- `MM21`: Média aritmética simples dos fechamentos dos últimos 21 pregões.
- `MM200`: Média aritmética simples dos fechamentos dos últimos 200 pregões.
- Em dias de pregão em andamento, o "último valor" (cotação atual) deve integrar a média como se fosse o fechamento do dia.
- Regra de Sinal: Se Preço Atual > MM, então "Alta". Se Preço Atual < MM, então "Baixa". Se igual, "Neutra".

## Critérios de aceite
- [ ] A coleta traz dados suficientes de histórico para calcular a MM200 (busca usando range `1y` ou maior no yfinance).
- [ ] O cálculo das médias desconsidera fins de semana/feriados (usa os últimos 21/200 candles retornados).
- [ ] O banco de dados armazena os valores calculados em cache adequadamente.
- [ ] Se o número de dados for inferior a 200, a MM200 não é exibida, informando "Dados insuficientes".
- [ ] Testes unitários validam a precisão do cálculo da média aritmética usando fixtures.
- [ ] A exibição das médias apresenta a fonte e horário da última atualização.

## Invariantes de produção
- A página mostra MM21 e MM200 com sinais indicativos (Alta/Baixa).
- Valores refletem a média simples dos últimos pregões disponíveis, divergindo no máximo 1% do Yahoo Finance.
- Se o mercado estiver fechado, as médias consideram o último fechamento disponível como o dado mais recente.
- A /api/snapshot exporta chaves e valores estruturados para "medias_moveis" ou embutidos nos dados do Ibovespa.

## Fora do escopo
- Médias móveis exponenciais (EMA).
- Aplicar médias móveis para todas as ações (apenas o índice será calculado nesta spec inicial).
- Gráfico sobrepondo as linhas de MM no gráfico base de cotação.
