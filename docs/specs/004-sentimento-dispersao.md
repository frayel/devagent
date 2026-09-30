---
id: 004
titulo: Sentimento de Mercado Baseado na Dispersão
status: done
esforco: P
---

## Problema
O investidor quer saber o verdadeiro humor da bolsa. Muitas vezes o Ibovespa sobe impulsionado por apenas 3 papéis de muito peso (como PETR4, VALE3 e ITUB4), enquanto a grande maioria das ações da B3 está caindo. A pergunta é: "Hoje é um dia de alta generalizada, ou uma falsa euforia segurada por poucas empresas?"

## Comportamento esperado
- Na página inicial, um card de "Termômetro de Dispersão".
- Exibe de forma clara:
  - Quantas ações rastreadas subiram hoje vs quantas caíram.
  - A proporção percentual de papéis em alta (ex: "75% em alta - Euforia", ou "20% em alta - Pessimismo").
  - Horário da coleta e a fonte dos dados.

## Fontes de dados
- **URL**: brapi.dev endpoint `/api/quote/list` para obter os dados dos papéis mais líquidos (cesta do fallback ou similar).
- **Formato**: JSON.
- **Frequência**: Mesma coleta das Maiores Altas e Baixas (a cada 15 minutos via cron interno).
- **Limites**: Plano grátis da brapi (limitado na quantidade no quote, por isso o `list` é melhor caso aplicável, senão reusa a cesta já coletada da Spec 002).
- **Plano B**: Se brapi falhar, usar a cesta de 30 tickers já pré-estabelecida via `yfinance` agrupada (como na Spec 002) para compor a amostragem de dispersão.

## Cálculos
- Obter os dados de variação (`regularMarketChangePercent` ou variação calculada) da amostra de ações mais líquidas.
- `Ações_em_Alta`: Contagem de ativos cujo fechamento atual > fechamento anterior.
- `Ações_em_Baixa`: Contagem de ativos cujo fechamento atual < fechamento anterior.
- Calcular a proporção: `Ações_em_Alta / (Ações_em_Alta + Ações_em_Baixa) * 100`.

## Critérios de aceite
- [ ] O banco de dados armazena a contagem de altas, baixas e neutras da cesta.
- [ ] A view apresenta o painel na página inicial com os indicadores descritos.
- [ ] A coleta dos dados reutiliza a infraestrutura mockável do respx de forma testável e confiável sem internet.
- [ ] O sistema não quebra se parte da cesta retornar nulo (ignora os nulos para a amostragem).
- [ ] A fonte e horário de coleta são claramente visíveis, e há log do tamanho da amostra (ex: "Amostra de 30 ações de alta liquidez").

## Invariantes de produção
- A soma das proporções de alta, baixa e neutras sempre corresponde ao total de ativos válidos avaliados (100%).
- Exibe "dados insuficientes" se o total da amostra cair abaixo de um limite mínimo (ex: 10 papéis).
- O painel novo aparece na exportação JSON do `/api/snapshot`.

## Fora do escopo
- Analisar todos os 400+ ativos listados na B3 (usaremos apenas a cesta selecionada ou o endpoint de lista simplificada).
- Gráficos intraday dessa dispersão.
