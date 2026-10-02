---
id: 013
titulo: Experiência: Filtro Macro vs Micro
status: ready
esforco: P
---

## Problema
A página inicial está acumulando muitos painéis, misturando indicadores do cenário geral (Macro) com análises específicas de ações (Micro). O usuário que quer ver apenas o "clima geral do mercado" tem dificuldade de filtrar visualmente as informações pertinentes.

## Comportamento esperado
Criar um controle (botões ou abas discretas) no topo da página (próximo ao cabeçalho) que permita ao usuário alternar a visualização dos painéis em três modos: "Todos", "Visão Macro", e "Visão Micro".
- "Visão Macro": Oculta painéis analíticos específicos de ações (como Maiores Altas/Baixas, Fator Mola, Força Relativa, Alertas de Volume) e deixa apenas Ibovespa Hoje, Sensibilidade ao Dólar, e Índice de Coesão.
- "Visão Micro": Oculta o painel principal do Ibovespa e exibe os painéis analíticos específicos.
- O controle deve usar JS vanilla, manipulando a propriedade `display` dos componentes no CSS, sem recarregar a página.

## Fontes de dados
Não há novas fontes de dados; apenas reorganização visual na UI (frontend).

## Cálculos
Nenhum cálculo novo.

## Critérios de aceite
- [ ] O controle "Filtro: Todos | Macro | Micro" aparece visível acima do primeiro grid.
- [ ] Clicar em "Macro" oculta os painéis configurados como Micro sem quebrar a grade.
- [ ] A interação acontece sem recarregar a página (CSS classes e JavaScript).
- [ ] O design se mantém íntegro em resoluções pequenas (390px) sem gerar rolagem horizontal (teste via `make telas`).

## Invariantes de produção
- A soma dos dados disponíveis deve manter-se fiel ao JSON retornado pela api independentemente do que o usuário vê (o snapshot da API é inalterado).

## Fora do escopo
- Persistência das preferências do usuário no backend; estado restrito à sessão/document atual.
- Novos indicadores.
