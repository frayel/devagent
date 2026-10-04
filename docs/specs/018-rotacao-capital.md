---
id: 018
titulo: Rotação de Capital (Bancos vs Commodities)
status: done
esforco: P
---

## Problema
O investidor olha o Ibovespa no zero a zero e acha que "nada aconteceu". Mas frequentemente isso ocorre porque o mercado está rodando carteira: vendendo peso pesado (Vale/Petro) e comprando bancos, ou vice-versa. O painel deve responder: o dinheiro está trocando de mãos entre os dois principais motores da bolsa?

## Comportamento esperado
No painel de visão macro, uma seção pequena indicando se há "Rotação de Capital" detectada no dia.
- Exibe o status: `Para Bancos`, `Para Commodities` ou `Neutra`.
- Exibe a variação média de Bancos e a variação média de Commodities.
- Se Bancos sobem e Commodities caem fortemente (ou vice-versa), destaca o fluxo de capital.

## Fontes de dados
- **yfinance:** Cotações do dia para os principais papéis. Bancos (`ITUB4.SA`, `BBDC4.SA`, `BBAS3.SA`) e Commodities (`VALE3.SA`, `PETR4.SA`, `PRIO3.SA`).
- Plano B: degrada graciosamente e não exibe o alerta de rotação.

## Cálculos
- Coleta a variação diária atual para os tickers de Bancos e Commodities.
- Calcula a média simples da variação para cada grupo.
- Se a variação média de um grupo for > 0.5% e do outro for < -0.5%, considera como Rotação para o grupo positivo.
- Caso contrário, Neutra.

## Critérios de aceite
- [ ] O banco de dados SQLite armazena o cache deste coletor (`rotacao_capital_cache`).
- [ ] Quando os critérios de rotação são atendidos, exibe os valores médios de cada setor e o status correspondente.
- [ ] Falha da fonte yfinance captura a exceção, não quebra a página e exibe painel vazio ou com erro amigável.
- [ ] Testes sem internet usando mock do httpx verificam o cálculo da rotação.

## Invariantes de produção
- A chave `rotacao_capital` existe dentro de `paineis` no `/api/snapshot`.
- O valor possui `coletado_em`, `fonte`, estado da rotação e as variações setoriais.

## Fora do escopo
- Acompanhar outros setores como Varejo ou Elétricas.
- Acompanhamento tick a tick em tempo real (apenas o snapshot da coleta periódica).
