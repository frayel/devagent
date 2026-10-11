---
id: 040
titulo: Radar de Divergência Volume/Preço (Exaustão)
status: ready
esforco: M
---

## Problema
O usuário quer prever topos de curto prazo. Uma ação subindo forte chama a atenção de compradores desavisados, mas se essa alta não for acompanhada de expansão de volume, o movimento é frágil. Identificar "divergência" (preço sobe, volume cai) protege o investidor de armadilhas.

## Comportamento esperado
Adicionar um painel na seção "Alertas Intraday" se houver ações demonstrando divergência de topo.
Exibe uma tabela contendo: Ticker, Alta Acumulada (%) e Variação Média do Volume (%), indicando que o volume está secando.
Se nenhuma ação se encaixar nos critérios, o painel não aparece.

## Fontes de dados
`yfinance` (endpoint chart) buscando dados de fechamento e volume dos últimos 5 pregões para ativos de alta liquidez.

## Cálculos
- Baixar a cotação e volume dos últimos 5 pregões via yfinance.
- Verificar se o ativo obteve retorno positivo nos 5 dias (fechamento atual > fechamento 5 dias atrás).
- Verificar se houve queda persistente no volume (ex: o volume médio dos dias recentes é menor que o dos primeiros dias do período) ou se há divergência técnica declarada.
- Exibir os casos onde a alta de preço é acompanhada pela queda do volume negociado.

## Critérios de aceite
- [ ] Teste automatizado confirma a lógica de divergência (preço subindo e volume declinando).
- [ ] Painel oculto e contrato `/api/snapshot` não quebram se não houver ativos que atendam aos requisitos.

## Invariantes de produção
A chave `divergencia_volume` em `/api/snapshot` expõe a lista (podendo ser vazia) sem quebrar o layout.

## Fora do escopo
Detectar divergência de fundo (divergência bullish). Foco exclusivo em exaustão de topo (divergência bearish de volume).
