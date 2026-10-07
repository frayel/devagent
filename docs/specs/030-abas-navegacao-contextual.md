---
id: 030
titulo: Abas de Navegação Contextual
status: ready
esforco: M
---

## Problema
O dashboard cresceu muito e a quantidade de painéis exige muita rolagem vertical, escondendo informações cruciais "abaixo da dobra". Os filtros atuais (Macro, Micro, Só Sinais) apenas ocultam painéis, mas não organizam a informação de forma estruturada. O usuário precisa de uma navegação clara para encontrar rapidamente o que procura (visão geral, sentimentos, destaques rápidos).

## Comportamento esperado
Substituir os botões de filtro atuais por um sistema de abas fixas no topo da grade de painéis (logo abaixo do header).
As abas devem organizar os painéis existentes nas seguintes categorias:
1. **Visão Geral:** Ibovespa, Maré do Mercado, Concentração Setorial, Tendência (Ibovespa).
2. **Sentimento & Risco:** Dispersão, Índice de Coesão, Apetite a Risco, Rotação de Capital, Escudo contra Quedas, Volatilidade Silenciosa.
3. **Rankings & Destaques:** Maiores altas, Maiores baixas, Força Relativa (30 dias), Atrasadas do Rally, Sempre Verde.
4. **Alertas Intraday:** Radar de volume, Variação Súbita, Radar de Faca Caindo, Armadilhas de Abertura, Compradores de Fundo, Sensibilidade ao dólar.

A navegação entre as abas não deve recarregar a página (comportamento de tabbed interface, gerido por JS/CSS, similar ao filtro atual mas estruturado visualmente como abas que trocam o conteúdo de painéis exibidos). O estado padrão (ativo) é a aba "Visão Geral". O botão de "Só Sinais" pode ser mantido ou integrado à aba de sentimentos.

## Fontes de dados
N/A (Mudança apenas de UI/UX, utiliza os dados já cacheados pelos painéis existentes).

## Cálculos
N/A

## Critérios de aceite
- [ ] As 4 abas estão visíveis no topo da grade.
- [ ] Clicar em uma aba exibe apenas os painéis correspondentes àquela categoria e oculta os demais.
- [ ] O layout continua responsivo (em telas móveis, as abas podem virar um select ou scroll horizontal).
- [ ] O teste de design visual (`test_design.py`) continua passando, sem uso de estilos inline adicionados irregularmente.

## Invariantes de produção
As mesmas do projeto original. Nenhum dado é removido, apenas reorganizado visualmente. O `/api/snapshot` deve continuar retornando todos os dados independentemente de qual aba está ativa.

## Fora do escopo
Criar novos indicadores ou painéis. Alterar o layout interno dos painéis existentes.
