---
id: 060
titulo: Radar de Exaustão de Queda
status: ready
esforco: M
gaveta: capacidade nova
---

## Problema
O investidor procura ações que vêm apanhando no curto prazo, mas que hoje dão o primeiro sinal claro de defesa institucional (rejeição de mínimas com volume alto). A dúvida é: "Qual ativo que vinha caindo chegou a um ponto onde os vendedores desistiram e os compradores começaram a absorver fortemente?"

## Comportamento esperado
- Um novo painel (ex: na seção de Alertas Intraday) que lista as ações da cesta de acompanhamento principal (ex: as 30 mais líquidas) que atendem aos seguintes critérios:
  1. Fecharam em queda (retorno negativo) nos últimos 3 pregões consecutivos.
  2. Hoje abriram com gap de baixa.
  3. No momento atual do intraday, o preço superou a abertura (variação intraday positiva) e o volume projetado supera a média dos últimos 21 dias.
- A tabela mostra o Ticker, a Queda Acumulada (3d) e a Recuperação Intraday atual.
- O painel é incluído no `/api/snapshot` sob a chave `exaustao_queda`.

## Fontes de dados
- **Yahoo Finance (`yfinance`)**: endpoint `spark` ou `chart` para puxar os fechamentos dos últimos 5 pregões e os dados intradiários do dia atual.
- Plano B: caso o `yfinance` falhe, a brapi pode ser consultada para os dados diários, ou o painel degrada silenciosamente não exibindo os dados se os dados não puderem ser calculados.

## Cálculos
1. **Queda Acumulada (3d)**: Fechamento D-1 / Fechamento D-4 - 1. A série D-1, D-2 e D-3 devem todas ter variação negativa em relação aos seus fechamentos anteriores.
2. **Gap de Baixa**: Abertura Hoje < Fechamento D-1.
3. **Recuperação Intraday**: Preço Atual / Abertura Hoje - 1 (deve ser > 0).
4. **Volume Projetado**: Volume Atual * (Total Minutos Pregão / Minutos Decorridos). Deve ser > Média Volume (21d).

## Critérios de aceite
- [ ] O painel não é exibido (ou exibe mensagem de que não há ativos na condição) quando o filtro retorna vazio.
- [ ] O teste com fixture garante que a tabela de exaustão de queda exibe os valores calculados corretamente.
- [ ] O `/api/snapshot` inclui a chave `exaustao_queda` refletindo a tabela.

## Invariantes de produção
- A chave `exaustao_queda` deve estar presente no `snapshot` sempre que a chamada à home não falhar (podendo ser null se não houver dados em cache).
- As ações listadas no snapshot sob `exaustao_queda` não podem ter a recuperação intraday negativa.

## Fora do escopo
- Gráfico intradiário dos ativos filtrados no painel. A exibição será limitada à tabela.
