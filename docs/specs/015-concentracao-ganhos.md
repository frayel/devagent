---
id: 015
titulo: Concentração de Ganhos do Ibovespa
status: done
esforco: M
---

## Problema
O investidor às 10h05 vê o Ibovespa subindo 1%, mas não sabe se o mercado inteiro está otimista (alta saudável) ou se apenas Vale e Petrobras estão subindo enquanto o resto cai (alta frágil). Essa ilusão do índice disfarça o real sentimento do mercado.

## Comportamento esperado
Um novo painel na página inicial chamado "Concentração de Ganhos".
Se o Ibovespa estiver em alta, exibe: "Dos X pontos de alta do índice, Y% vieram de apenas Z ações." (Onde Z é o número de ações que somam pelo menos 50% da pontuação total).
Se o Ibovespa estiver em queda, exibe: "Dos X pontos de queda do índice, Y% vieram de apenas Z ações."
Abaixo dessa manchete, uma tabela simples listando os 3 papéis que mais puxaram o índice (para cima ou para baixo, dependendo da direção do índice), mostrando: Ticker, contribuição em pontos e peso no índice.
Atualiza junto com o resto do painel via HTMX e cache no SQLite (`concentracao_cache`).

## Fontes de dados
A composição teórica do Ibovespa (pesos) não é facilmente fornecida de graça em tempo real por APIs simples.
**Plano A:** Calcular a contribuição estimada. Usaremos os 10 papéis de maior peso histórico aproximado (VALE3, PETR4, ITUB4, PETR3, BBDC4, B3SA3, WEGE3, ABEV3, ELET3, BBAS3) que costumam representar ~50% do índice. Pegamos a variação percentual de cada um via `yfinance` e multiplicamos pelo seu peso fixo estimado, traduzindo para pontos (considerando os pontos totais do IBOV no fechamento anterior).
**Plano B:** Se falhar ao coletar múltiplos tickers, o painel exibe estado indisponível.

## Cálculos
1. Fixar um dicionário com os pesos teóricos (aproximados) das top 10 ações (ex: VALE3: 12%, PETR4: 8%, ITUB4: 7%, etc). A soma não dará 100%, mas serve como proxy da concentração.
2. Coletar cotação atual e fechamento anterior do IBOV e destas 10 ações via `yfinance`.
3. Contribuição em pontos da ação = Variação % da ação * Peso da Ação * Pontuação IBOV anterior.
4. Somar a contribuição em pontos das ações do dicionário que foram na mesma direção do Ibov (altas em dia de alta, baixas em dia de baixa).
5. Determinar quantas dessas top ações foram necessárias para explicar metade (50%) dos pontos de variação totais do índice.

## Critérios de aceite
- [ ] O banco de dados SQLite inclui a tabela `concentracao_cache`.
- [ ] O coletor salva as top 3 ações contribuintes e a métrica de concentração no banco.
- [ ] O painel exibe a mensagem de concentração correta (ex: "50% da alta vem de apenas 2 ações").
- [ ] A tabela exibe os 3 ativos, seus pontos de impacto e o peso estimado.
- [ ] Se o yfinance falhar, o painel usa a macro `estado('indisponivel')`.
- [ ] Se a variação do IBOV for muito próxima de zero (ex: entre -0.1% e +0.1%), o painel exibe estado indisponível ou mensagem "Ibovespa estável, sem concentração definida".

## Invariantes de produção
- A chave `concentracao` deve existir no `/api/snapshot`.
- O valor da contribuição das top 3 ações nunca pode exceder a variação total do Ibovespa matematicamente possível, servindo como teste de sanidade.

## Fora do escopo
Raspagem diária precisa da carteira teórica da B3. Usaremos pesos estáticos aproximados das principais ações, atualizados manualmente no código se necessário.
