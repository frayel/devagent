---
id: 029
titulo: Sparklines nos rankings
status: ready
esforco: M
---

## Problema
Ao olhar os rankings de "Maiores altas", "Maiores baixas" e "Força Relativa", o investidor vê a variação do dia, mas não sabe se aquilo é um repique de curto prazo (ponto fora da curva) ou a continuação de uma tendência forte. Um minigráfico (sparkline) do histórico recente responde a isso visualmente, enriquecendo as tabelas sem gastar espaço, conforme previsto no `docs/DESIGN.md`, seção 5.1.

## Comportamento esperado
Nas tabelas dos painéis "Maiores altas", "Maiores baixas" e "Força Relativa (30 dias)", deve ser adicionada uma nova coluna (ou integração visual ao lado do ticker/variação) exibindo um sparkline SVG.
- O sparkline será gerado no servidor usando o histórico de fechamentos, e renderizado inline (mantendo o CSP seguro, sem inline scripts ou eval) no template HTML das tabelas afetadas.
- O minigráfico exibirá o comportamento dos últimos 10 pregões do ativo, preenchendo as dimensões padronizadas pela seção 5.1 do DESIGN.md.

## Fontes de dados
A fonte principal é o Yahoo Finance (endpoint spark com intervalo `1d` e `range` cobrindo pelo menos 10 dias úteis).
A coleta do histórico deve ser adicionada aos respectivos coletores ou aproveitar dados que já buscam janelas de 30 dias (por ex. Força Relativa já busca janela maior).
- Frequência de coleta: mesma cadência já configurada (em `app/agendador.py` e cache diário/intraday).
- Limites de uso e fallback: Se os dados históricos falharem (fallback), o sparkline fica vazio ou exibe traço horizontal inócuo, mas a variação de preço diário continua aparecendo. A tabela não quebra se o minigráfico falhar.

## Cálculos
- Extrair o array contendo o preço de fechamento (close) dos últimos 10 pregões para cada ativo das tabelas.
- Normalizar o array para valores Y escalonados (de 0 a uma altura máxima para SVG) mantendo a proporção de min-max no período.
- A linha não precisa de eixo ou legendas (puramente sparkline de proporção).

## Critérios de aceite
- [ ] Ao renderizar a home, as tabelas de altas, baixas e força relativa devem conter tag `<svg>` com classe de sparkline associada.
- [ ] O teste com a página rodando offline (usando fixtures do Yahoo) exibe o path SVG no DOM gerado sem quebrar o CSP.
- [ ] O layout mobile adapta a exibição do minigráfico para caber no grid celular.
- [ ] Fallback validado: simulando falha na chamada de histórico de 10 dias, os destaques e variação do dia devem continuar aparecendo.

## Invariantes de produção
- A resposta do `/api/snapshot` reflete os dados sem o componente visual.
- Os SVGs dos sparklines não devem conter estilos arbitrários inline fora dos autorizados (tudo gerido por classes CSS).
- Gráficos gerados para os ativos da tabela representam fielmente a tendência exibida pelas fontes oficiais (Yahoo Finance).

## Fora do escopo
- Sparklines coloridos com base na inclinação ou em comparação com benchmark (a linha do gráfico será de cor padrão para sparklines de acordo com tema, sem color scale baseada na força no SVG).
- Interação por hover (tooltips do minigráfico não são escopo desta entrega, manter simplificado).
