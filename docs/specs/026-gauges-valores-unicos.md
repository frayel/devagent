---
id: 026
titulo: Gauges para valores únicos
status: done
esforco: M
---

## Problema
Pedido do dono do produto em 05/10/2026: "use mais gráficos onde for possível; onde são valores únicos, use um gauge".

Vários painéis mostram um número sozinho (63% em alta, 7 de 10, +0,8 p.p.). O leitor não sabe se o número é muito ou pouco sem lembrar a escala. A regra nova está em `docs/DESIGN.md`, seções 5.1 e 5.2: valor com escala vira gráfico, e valor único vira `gauge`.

## Comportamento esperado
- Existe a macro `gauge` em `app/templates/componentes.html`, desenhada em SVG no servidor, exatamente como a seção 5.2 do guia descreve e como aparece em `docs/design/referencia.html`.
- Os painéis abaixo passam a mostrar um gauge, com o número ainda em texto no centro:

| Painel | Valor | Escala | Tipo |
|---|---|---|---|
| Dispersão | % de ações em alta | 0 a 100% | simples; `--alta` a partir de 50%, `--baixa` abaixo. O `medidor` subiram × caíram continua embaixo. |
| Índice de Coesão | ações concordantes | 0 a 10 (ou 0 a `total`) | simples; `--alta` de 7 em diante, `--baixa` até 3, `--destaque` entre os dois |
| Apetite a Risco | SMLL − IBOV hoje | −2,0 a +2,0 p.p. | divergente |
| Rotação de Capital | variação bancos − variação commodities | −3,0 a +3,0 p.p. | divergente; o lado positivo diz "Para Bancos", o negativo "Para Commodities" |
| Tendência (Ibovespa) | distância do índice à MM21 e à MM200 | −10% a +10% | dois gauges divergentes lado a lado, com o valor da média abaixo de cada um |

- Depois desses, o PR passa pela página inteira com a tabela da seção 5.1 e converte qualquer outro número solto que tenha escala. Cada conversão extra é listada no corpo do PR.
- O resto do painel (rótulos de estado, legenda, fonte, horário, método) continua igual.

## Fontes de dados
Nenhuma nova.

## Cálculos
- `pct = (valor − mínimo) / (máximo − mínimo) × 100`, limitado a [0, 100]. Valor fora da escala aparece cortado no limite, com o texto do número mostrando o valor real.
- Distância à média: `(preço atual / MM − 1) × 100`, calculada no serviço do Ibovespa. Se a média estiver ausente, aquele gauge mostra `estado('indisponivel')` e o outro continua.
- Todo cálculo fica no serviço ou num filtro Jinja testado; o template só posiciona.

## Implementação
1. `gauge(valor, rotulo, minimo=0, maximo=100, formato="{:.0f}", faixas=None, divergente=False, resumo="")` em `componentes.html`, com as classes `.gauge`, `.g-trilho`, `.g-valor`, `.g-faixa-N`, `.g-agulha` em `app/static/tema.css`. As cores saem só dos tokens.
2. Filtro Jinja `gauge_pct` (ou função no serviço) com teste de unidade cobrindo valor dentro, abaixo e acima da escala e o modo divergente.
3. Trocar os painéis da tabela acima. Sem `style=` e sem `Plotly.newPlot` para gauges.
4. Rodar `make telas` e responder o checklist da seção 8 do guia no PR.
5. Se passar de ~400 linhas, divida em 026a (macro, CSS, testes, Dispersão e Coesão) e 026b (demais painéis).

## Critérios de aceite
- [x] `tests/test_componentes.py` (ou equivalente) renderiza a macro e verifica: `role="img"`, `aria-label` com o valor, `stroke-dasharray="63` para 63 de 100, e `stroke-dasharray="25` com `stroke-dashoffset="-25"` para −1,0 numa escala divergente de −2 a +2.
- [x] Valor 150 numa escala 0 a 100 gera `stroke-dasharray="100` e o texto mostra 150.
- [x] Dado o banco de demonstração de `scripts/telas.py`, a página contém pelo menos 6 elementos `class="gauge"`.
- [x] Nenhum `fill="#`, `stroke="#` ou `rgb(` nos templates (já coberto por `tests/test_design.py`).
- [x] Os testes de conteúdo existentes de cada painel continuam passando.

## Invariantes de produção
- O `/api/snapshot` mantém todas as chaves e valores de antes. Pode ganhar `mm21_dist_pct` e `mm200_dist_pct` no painel do Ibovespa, nunca perder ou renomear chaves.
- Todo gauge publicado tem `aria-label` com o mesmo número que aparece no texto.

## Fora do escopo
- Gauges animados ou que se atualizam no navegador sem recarregar o painel.
- Sparklines nas tabelas de ranking (ideia registrada no backlog).
- O painel da Maré do mercado (spec 027), que usa esta macro.
