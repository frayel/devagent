# Backlog

## Correções (prioridade sobre qualquer feature)

### Critérios da spec 002 marcados como cobertos sem teste

A spec 002 foi marcada `done`, mas os testes não cobrem três critérios:

- [ ] "O painel não quebra se a fonte retornar menos que 5 ativos": teste com 3 ativos na resposta.
- [ ] "A fonte e hora da coleta são explicitadas na tela": o template mostra só a hora. Exibir a fonte usada (brapi ou Yahoo), gravada junto com o cache, e testar as duas na página.
- [ ] Ordenação do ranking: o mock usa a mesma variação para todos os ativos, então a ordem nunca é verificada. Testar com variações distintas que a maior alta vem primeiro e a maior baixa vem primeiro.

### Expor `/api/snapshot` para o auditor

O auditor de produção hoje extrai os números do HTML, o que quebra se o template mudar. Implementar o endpoint conforme o contrato em `auditoria/README.md`, com teste em `tests/`. Não altere `auditoria/`: quando o endpoint existir, o auditor passa a usá-lo sozinho.

### Testes de maiores altas e baixas levam 2 minutos

`tests/test_highlights.py` espera o limite real de 1 requisição a cada 2 s por domínio: `test_collect_and_save_fallback` e `test_fetch_yfinance_success` levam cerca de 60 s cada. Neutralizar `time.sleep` do limitador nesses testes (como faz `tests/test_highlights_lista.py`) sem mudar o comportamento em produção.

## Features

| Feature | Valor | Fonte de dados | Esforço (P/M/G) | Risco |
|---|---|---|---|---|
| Maiores altas e baixas do dia (tabela) | Identificar destaques diários do mercado | brapi.dev | P | Baixo (dependência de API externa) |
| Alertas de volume anormal | Detectar movimentos atípicos que precedem tendências | brapi.dev | P | Baixo (depende do cálculo sobre média histórica) |
| Médias móveis (21 e 200 dias) | Análise de tendência de curto e longo prazo | yfinance | P | Baixo |
| Calendário de Balanços | Preparação para volatilidade em datas de resultados | CVM / StatusInvest (scraping) | M | Alto (fontes instáveis ou difíceis de raspar) |
| Ficha da ação (P/L, P/VP, DY, ROE) | Análise fundamentalista rápida de uma empresa | brapi.dev | M | Médio (qualidade dos dados fundamentalistas) |
| Comparador de ações (lado a lado) | Auxilia na escolha entre pares do mesmo setor | brapi.dev | M | Médio (depende da ficha da ação) |
| Mapa de calor setorial | Visualização rápida do desempenho por setor | brapi.dev / yfinance | M | Médio (categorização correta dos setores) |
| Rastreio de carteiras recomendadas | Agregação das carteiras mensais de corretoras | Scraping (bancos/corretoras) | G | Alto (layout variável e difícil extração) |
| Fluxo do investidor estrangeiro | Entender o fluxo de capital gringo na B3 | B3 (scraping ou API não oficial) | M | Alto (fonte instável ou difícil acesso) |
| Histórico de dividendos pagos vs anunciados | Prever o fluxo de caixa do investidor focado em renda | B3 / brapi.dev | G | Alto (eventos corporativos complexos) |
| Consenso de analistas | Entender a expectativa do mercado (preço-alvo) | yfinance / scraping | G | Alto (dificuldade de extração e padronização) |
| Termômetro de sentimento | Analisar humor do mercado via notícias | Scraping (Infomoney, Valor, etc) | G | Alto (mudanças no layout dos sites, NLP) |
| Probabilidade histórica | Estudar comportamento pós-padrões | yfinance | G | Médio (complexidade de cálculo) |
