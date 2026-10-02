---
id: 012
titulo: Índice de Coesão do Mercado
status: done
esforco: P
---

## Problema
O Ibovespa pode estar subindo ou caindo puxado por apenas uma ou duas ações muito pesadas, mascarando a real direção das principais blue chips. O investidor quer saber se a direção do índice tem unanimidade entre os maiores papéis.

## Comportamento esperado
Um novo painel exibindo o "Índice de Coesão". Ele analisará as top 10 ações do IBOV (por peso) e mostrará quantas delas estão na mesma direção (alta ou baixa) do índice no dia.
Mostrará a proporção (ex: "8 de 10 ações") e um medidor visual ou alerta indicando "Alta Coesão" ou "Distorção".

## Fontes de dados
- **Principal:** API do yfinance para coletar cotações intraday (variações do dia) das 10 principais ações e do índice `^BVSP`.
- **Plano B:** brapi.dev se o yfinance falhar.
- **Top 10 Tickers:** Lista estática das 10 ações mais líquidas/pesadas (VALE3.SA, PETR4.SA, ITUB4.SA, BBDC4.SA, BBAS3.SA, WEGE3.SA, ABEV3.SA, RENT3.SA, SUZB3.SA, BPAC11.SA).

## Cálculos
- Coletar a variação percentual (%) diária de `^BVSP` e de cada uma das 10 ações.
- Direção do IBOV: Positiva (>=0) ou Negativa (<0).
- Contar quantas das 10 ações possuem a mesma direção que o IBOV.
- Coesão: "Alta Coesão" (>= 7), "Baixa Coesão" (<= 3), "Neutra" (4 a 6).

## Critérios de aceite
- [ ] Coletor `coesao` salva a contagem de ações concordantes no SQLite em `coesao_cache`.
- [ ] A página inicial exibe o painel de Coesão com a quantidade de ações (X de 10).
- [ ] Quando a fonte falhar, exibe "Dados não disponíveis".

## Invariantes de produção
- A contagem exibida e exposta em `/api/snapshot` deve ser um inteiro entre 0 e 10.
- A direção das top 10 ações deve ser computada contra a direção do próprio IBOV.

## Fora do escopo
- Pesos reais do IBOV dinâmicos (usaremos uma lista estática representativa de 10 blue chips).
- Gráficos históricos de coesão.
