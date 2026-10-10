---
id: 038
titulo: Detector de Ação Órfã
status: ready
esforco: M
---

## Problema
O investidor quer saber quais ações de seu universo de acompanhamento secaram drasticamente de liquidez (perderam volume de negócios a ponto de travar o book), sinalizando risco elevado de execução de ordens e spreads enormes.

## Comportamento esperado
Adicionar um alerta na seção "Alertas Intraday" quando uma ou mais ações de alta liquidez ficarem mais de 15 minutos sem nenhum ou com volume irrisório em pleno pregão, ou cujo spread atual explodiu.
Apresentar uma tabela com: Ticker, Tempo sem negócios (ou queda drástica de volume), e aviso de risco.
Se nenhum papel sofrer isso, não exibir nada (painel não aparece).

## Fontes de dados
Endpoint de quote ou histórico da `brapi.dev` ou `yfinance` para observar a ausência de movimento (volume zero em candle de 15 min no intraday).
Plano B: Se falhar ou fora de pregão regular, painel fica inativo silenciosamente.

## Cálculos
- Baixar o volume intraday 15m das ações líquidas acompanhadas.
- Checar se, durante horário comercial (ex: entre 11:00 e 16:00 BRT), algum candle fechou com volume = 0 ou <= 5% da média de 15m normal (ou se o bid/ask da quote tem spread extremo > 2%).
- Sinalizar as ações afetadas.

## Critérios de aceite
- [ ] Teste automatizado que, ao fornecer mock com volume 0 no período atual intraday, dispare a anomalia.
- [ ] A chave correspondente no `/api/snapshot` é exposta sem quebrar a aplicação principal.

## Invariantes de produção
- A chave `acao_orfa` em `/api/snapshot` não vaza nulos quando os dados falham (deve expor lista vazia).

## Fora do escopo
Identificar qual corretora está atuando ou o histórico completo de trades. Apenas exibir o estado crítico de iliquidez.
