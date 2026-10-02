---
id: 009
titulo: Força Relativa contra o Ibovespa
status: ready
esforco: P
---

## Problema
O investidor quer saber quais ações estão sistematicamente performando melhor ou pior que o Ibovespa (benchmark) nos últimos 30 pregões, e não apenas o número absoluto delas num único dia. Isso ajuda a identificar tendência estrutural.

## Comportamento esperado
Na página inicial (após a seção de destaques do dia), um card "Força Relativa (30 dias)" exibirá:
- Ação com Maior Força Relativa: Ticker e % de superação vs IBOV no período.
- Ação com Menor Força Relativa: Ticker e % de defasagem vs IBOV no período.
- Uma pequena explicação textual do cálculo: "Comparação da rentabilidade acumulada de 30 ações de alta liquidez frente ao Ibovespa em 30 pregões."

## Fontes de dados
- yfinance (`/v8/finance/chart/{ticker}.SA`) para as ações da lista de alta liquidez e `^BVSP` para o benchmark. A coleta pode usar o endpoint de batch (spark) ou iteração com backoff/retry.
- Plano B: se a fonte falhar, exibir "Dados não disponíveis".

## Cálculos
1. Para cada ticker da lista (e para o `^BVSP`), obter os fechamentos dos últimos 30 pregões.
2. Calcular a rentabilidade acumulada do período: `(Último_Fechamento / Primeiro_Fechamento) - 1`.
3. Calcular a força relativa da ação `A`: `Rentabilidade_A - Rentabilidade_IBOV`.
4. Encontrar as ações com maior Força Relativa positiva e menor Força Relativa (negativa).

## Critérios de aceite
- [ ] Calculado corretamente usando os fixtures (diferença entre o acumulado da ação e do Ibovespa).
- [ ] API expõe os dados em `/api/snapshot` (`forca_relativa`).
- [ ] Renderizado na tela respeitando o `docs/DESIGN.md`.
- [ ] Falha em uma das fontes deve ser tratada graciosamente e não causar 500.

## Invariantes de produção
- Acesso à API (`/api/snapshot`) possui uma chave `forca_relativa` e sub-chaves com os maiores e menores tickers.

## Fora do escopo
- Permitir ao usuário escolher diferentes benchmarks (ex: CDI ou Dólar).
- Permitir trocar a janela de tempo (ex: 5 dias, 1 ano).
