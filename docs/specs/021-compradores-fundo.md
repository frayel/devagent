---
id: 021
titulo: Compradores de Fundo (Reversão Intraday)
status: done
esforco: M
---

## Problema
O investidor quer saber quais ações abriram o dia despencando (potencial pânico) mas, durante o pregão, atraíram forte força compradora a ponto de virarem para o positivo, respondendo à pergunta: "O que caiu forte cedo mas já reverteu?".

## Comportamento esperado
Na tela inicial, um novo painel pequeno (metade da largura) exibindo o top 3 das ações que preencham os critérios de reversão.
O painel exibe o ticker, a queda máxima que chegou a ter no dia, e o preço atual positivo.
Se nenhuma ação preencher os critérios, exibir "Nenhuma reversão identificada hoje".

## Fontes de dados
- **yfinance:** Usar o endpoint de spark para as 30 ações de maior liquidez para obter o histórico intradiário ou `regularMarketOpen`, `regularMarketDayLow`, `regularMarketPrice`.
- Plano B: se a fonte falhar, o painel exibe estado "indisponível", mantendo os demais componentes intactos.

## Cálculos
- Para cada ação da lista de 30 tickers de alta liquidez:
  - Verificar se a mínima do dia (`Day Low`) foi menor que a abertura em pelo menos 1.5%.
  - Verificar se o preço atual (`Price`) é maior ou igual à abertura (ativo no verde).
- Ordenar as ações pelas que tiveram a maior distância percentual entre a mínima do dia e o preço atual.
- Limitar aos 3 maiores resultados.

## Critérios de aceite
- [ ] O banco de dados SQLite armazena o cache do coletor (`compradores_fundo_cache`).
- [ ] Quando o script de coleta identifica ativos que caíram > 1.5% da abertura e agora estão positivos, a lista os exibe.
- [ ] O componente exibe "Nenhuma reversão identificada hoje" se a lista vier vazia.
- [ ] A falha do yfinance resulta em tratamento de exceção na UI, mostrando apenas o card indisponível.

## Invariantes de produção
- O JSON de resposta da `/api/snapshot` deve possuir a chave `compradores_fundo` dentro de `paineis`.
- O objeto deve conter `coletado_em`, `fonte` e a lista `alertas`.

## Fora do escopo
- Gráfico intraday mostrando a reversão (exibiremos apenas os números consolidados).
- Enviar notificação quando a reversão ocorrer em tempo real.
