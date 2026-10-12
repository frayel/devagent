---
id: 046
titulo: Fator "Peso Pesado"
status: done
esforco: M
---

## Problema
O investidor quer saber se o IBOV está subindo só por causa de 2 ou 3 ações gigantes (Vale, Petrobras, Itaú) ou se a alta é generalizada.

## Comportamento esperado
Um novo painel pequeno (span-3) na visão macro (Visão Geral), próximo ao Ibovespa.
O painel exibirá a proporção da variação do IBOV no dia que é explicada apenas pelas 5 ações de maior peso (VALE3.SA, PETR4.SA, ITUB4.SA, PETR3.SA, BBAS3.SA).
Exemplo: "VALE, PETR e ITUB respondem por 85% do movimento do IBOV hoje".

## Fontes de dados
- Yahoo Finance (yfinance), endpoint chart 1d.
- Se yfinance falhar, o painel exibe "Dado indisponível".

## Cálculos
- Obter a variação em pontos do IBOV.
- Obter a variação percentual das top 5 ações.
- Calcular a contribuição teórica usando pesos estáticos aproximados (VALE3=12%, PETR4=8%, ITUB4=7%, PETR3=4%, BBAS3=3%).
- A contribuição das 5 ações é a soma (variação % * peso / 100) multiplicada pela pontuação anterior do IBOV.
- Exibir a proporção: (Contribuição Top 5 / Variação Total IBOV) * 100.
- Se a variação total do IBOV for muito próxima de zero (< 0.1%), exibir "Mercado lateral" para evitar divisão por zero ou distorções.

## Critérios de aceite
- [ ] Dado mockado onde IBOV sobe 1000 pontos e Top 5 contribui com 800, exibe "80%".
- [ ] Quando a variação do IBOV for < 0.1%, exibe "Mercado lateral".
- [ ] Se a fonte falhar, não quebra a página, exibe "Dado indisponível".

## Invariantes de produção
- A soma dos pesos utilizados no cálculo deve ser menor que 100%.
- O valor exibido no painel (proporção) nunca ultrapassa magnitudes absurdas (ex: > 500% ou < -500%, nesse caso deve ser tratado como distorção).

## Fora do escopo
- Buscar os pesos oficiais diários da carteira teórica da B3 (usaremos pesos estáticos para o MVP).
