---
id: 048
titulo: Reorganização por Motores do Índice (Experiência)
status: done
esforco: G
---

## Problema
O usuário não sabe de relance o que está causando o movimento do Ibovespa. Atualmente, ele precisa olhar para diferentes tabelas (Força Relativa, Maiores Altas/Baixas) e deduzir se a bolsa está subindo por causa dos bancos, das commodities ou do setor de consumo interno. A grade estática tradicional não prioriza a visualização do fator primário do movimento diário.

## Comportamento esperado
A página inicial terá uma nova abordagem de organização (ou uma sub-aba destacada): "Motores do Índice".
Ao invés de exibir tabelas genéricas no topo da Visão Geral, a interface dividirá as ações de peso do índice em 3 grupos principais:
1. Financeiro (Bancos e Seguros)
2. Commodities (Vale, Petrobras, Siderurgia, Celulose)
3. Doméstico (Varejo, Construção, Energia)

O frontend calculará o impacto de cada "Motor" sobre o Ibovespa no dia e reorganizará dinamicamente a exibição, colocando o Motor de maior influência (positiva ou negativa) no topo da seção, com visualização de cards grandes para esses três grupos, mostrando a direção e a força (variação média ponderada) de cada grupo.

*Fatia desta Spec:* Apenas o backend calculará as cestas e a variação média ponderada de cada uma (usando `yfinance`), e o frontend consumirá e exibirá os 3 novos cards (Financeiro, Commodities, Doméstico) no topo da `visao-macro`, organizados por ordem de intensidade de variação (absoluta). A reorganização dinâmica completa da página baseada no motor dominante ficará para uma iteração futura.

## Fontes de dados
- Yahoo Finance (`spark` diário ou dados de fetch de cotação atual `v8/finance/chart/{symbol}`).
- Será configurada uma constante no código separando as ações por essas três categorias.
- Fallback: se a API falhar em responder os ativos, exibe "Dado indisponível" nos cards dos Motores.

## Cálculos
- Para cada categoria (Financeiro, Commodities, Doméstico), buscar as cotações das ações da lista pré-definida.
- Calcular a variação média das ações de cada cesta (usando peso igual para simplificação nesta etapa).
- Ordenar os 3 grupos por variação absoluta (do maior impacto pro menor) para exibição na UI.

## Critérios de aceite
- [ ] O contrato `/api/snapshot` retorna um objeto `motores_indice` contendo 3 listas ou objetos (Financeiro, Commodities, Doméstico) com a variação calculada.
- [ ] O frontend exibe 3 cards na seção Macro, ordenados pela maior variação absoluta no dia.
- [ ] Se o Yahoo Finance falhar, o painel exibe um aviso claro de "dado indisponível".
- [ ] Um teste com HTTP mockado (`respx`) verifica o cálculo correto da variação da cesta.

## Invariantes de produção
- A chave `motores_indice` deve existir no `/api/snapshot`.
- Os três grupos (Financeiro, Commodities, Doméstico) devem estar presentes, ou degradados graciosamente.

## Fora do escopo
- Pesos reais dinâmicos da carteira teórica B3. Utilizaremos uma média simples ou cesta simplificada para este MVP.
- Ocultação dos demais painéis baseados no motor (reorganização total de layout). Apenas os cards dos motores serão exibidos ordenados no topo.
