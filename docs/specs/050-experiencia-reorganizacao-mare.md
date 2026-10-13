---
id: 050
titulo: Experiência: Reorganização da Maré do Mercado (Consolidação de Sinais)
status: ready
esforco: P
---

## Problema
Consigo ler rapidamente a direção principal e seus motivadores? A revisão de experiência (com a captura da tela) mostra que a macro `Painel da Maré do mercado` no canto superior direito está dominando visualmente o topo da interface. Ele inclui Confiança, Apetite a Risco e Rotação usando gauges semi-circulares. Apesar de terem métricas relacionadas ao fluxo e volume, eles competem pela atenção e tomam espaço vertical considerável na primeira dobra ("above the fold") do produto, empurrando informações mais urgentes ou detalhadas (como os rankings de Força Relativa, ou destaques intraday) para baixo. A informação da Maré do Mercado seria melhor absorvida se fosse mais horizontal e integrada.

## Comportamento esperado
- O `Painel da Maré do Mercado` será reestruturado para ser mais compacto verticalmente.
- O gauge principal de `Confiança` será reduzido de tamanho ou redesenhado para ocupar menos altura (possivelmente utilizando o formato de barra horizontal, semelhante ao de "Fluxo", "Calma" e "Volume" que já existem abaixo dele).
- Os sub-gauges `Apetite a Risco` e `Rotação` serão movidos para uma disposição lado a lado ou compactados em uma única linha com mini-gauges.
- Nenhuma informação, aviso legal ou fonte atual será removida; apenas reorganizada e reestilizada via CSS (redução de paddings/gaps ou troca de layout de flex-col para flex-row onde apropriado).
- A hierarquia visual resultante deve permitir que o painel vizinho (Ibovespa Hoje) mantenha seu destaque e que mais conteúdo das abas ou seções abaixo fiquem visíveis sem rolagem inicial.

## Fontes de dados
Nenhuma fonte de dados nova. A spec é puramente de experiência de usuário (UX/UI) e reordenação de componentes visuais baseada em CSS/Jinja. O plano B em caso de falha de layout é a reversão para os estilos anteriores.

## Cálculos
Nenhum novo cálculo. Utiliza os dados já fornecidos pelo contexto atual dos gauges (`mare_cache`, etc).

## Critérios de aceite
- [ ] Verificável visualmente via `make telas`: o painel da `Maré do mercado` ocupa visivelmente menos espaço vertical do que na versão anterior.
- [ ] Verificável visualmente via `make telas`: os três sub-indicadores ("Apetite a Risco", "Rotação" e "Confiança") continuam legíveis, mas dispostos de forma mais densa.
- [ ] A página roda sem erros de compilação do Jinja ou falhas nos testes visuais existentes (`test_design.py`).

## Invariantes de produção
- A seção "Maré do mercado" e os valores de Apetite a risco, rotação e confiança continuam presentes e acessíveis no payload `/api/snapshot`.
- O aviso legal de rodapé ("Conteúdo informativo gerado automaticamente. Não constitui recomendação de investimento.") permanece visível.

## Fora do escopo
- Alteração na lógica de cálculo ou nas regras de negócio que alimentam os indicadores de Maré, Apetite a Risco, ou Rotação.
- Modificações fora do componente/macro `Painel da Maré do mercado` e seu container CSS adjacente.
