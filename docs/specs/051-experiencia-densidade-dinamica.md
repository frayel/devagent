---
id: 051
titulo: "Experiência: Densidade Dinâmica da Grade"
status: ready
esforco: P
---

## Problema
A tela do dashboard apresenta uma grade confortável com bastante respiro (paddings e gaps), mas isso obriga usuários focados em leitura rápida a rolarem a página para visualizar painéis importantes (como Alertas Intraday ou Concentração Setorial). Como adaptar a tela para leitores panorâmicos sem arruinar a experiência confortável padrão? (Responde: A tela parece muito apertada/espaçada para leitura rápida?)

## Comportamento esperado
- Adicionar um pequeno toggle/botão no cabeçalho ou menu de navegação de abas (ex: "Compacto" / "Confortável").
- Ao ativar a opção "Compacto", uma classe `.compacto` é aplicada à tag `<body>` ou ao container principal `.grade`.
- O CSS reduz os paddings internos de `.painel` e o `gap` da `.grade`, diminuindo também margens e possivelmente o tamanho de fontes não essenciais.
- A visualização na primeira dobra passa a exibir mais componentes ao mesmo tempo sem requerer rolagem.
- O estado selecionado pelo usuário pode ser persistido via `localStorage`.

## Fontes de dados
Nenhuma fonte de dados externa necessária. Funcionalidade apenas de UI/CSS.

## Cálculos
Nenhum cálculo backend necessário.

## Critérios de aceite
- [ ] O toggle de densidade deve estar visível e funcional no cabeçalho ou barra de abas.
- [ ] O clique no toggle alterna uma classe CSS que altera visivelmente `padding` e `gap` da grade.
- [ ] O teste automatizado renderiza a página e verifica se o botão/toggle de densidade está presente no HTML gerado.

## Invariantes de produção
- A mudança de CSS não oculta nenhum elemento essencial de dados ou de transparência (horários, aviso legal, links) presentes na visão "Confortável".
- O contrato da API `/api/snapshot` não sofre nenhuma alteração estrutural, visto que a mudança afeta apenas o cliente visual.

## Fora do escopo
- Permitir uma customização granular (ex: deslize livre) da densidade. Serão apenas 2 estados: Confortável (Padrão) e Compacto.
- Mudanças nos layouts dos gráficos Plotly/D3 (o foco é apenas nas margens e padding dos containers HTML).
