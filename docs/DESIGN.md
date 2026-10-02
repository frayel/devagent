# DESIGN.md · Guia visual do Painel B3

> **Documento protegido** (`devagent/protegidos.txt`). O agente segue este guia em toda mudança de interface e pode propor alterações, mas só num PR `agent:` dedicado a ele, que espera revisão humana. Nunca altere este arquivo no mesmo PR que muda a interface.
>
> A referência visual navegável está em `docs/design/referencia.html`. Abra-a no navegador antes de mexer em qualquer tela: ela mostra os tokens, os componentes e a grade montados com dados fictícios.

## 1. Intenção

O painel é uma mesa de trabalho para quem decide em minutos, não uma página de apresentação. Três ideias guiam tudo:

1. **Densidade com respiro.** Muita informação por tela, organizada em grade, sem cards gigantes com um número só. A referência é um terminal de mercado, não uma landing page.
2. **O número é o protagonista.** Valores grandes, alinhados e fáceis de comparar. Rótulos, bordas e fundos ficam em segundo plano.
3. **Cor significa algo.** Verde é alta, vermelho é baixa, âmbar é alerta, azul é interação. Nenhuma outra cor aparece por enfeite.

## 2. Tokens

Todas as cores, tamanhos e espaçamentos vêm de variáveis CSS declaradas **só** em `app/static/tema.css`. Nenhum template, script ou outro CSS escreve um hexadecimal, `rgb()` ou tamanho de fonte solto. O teste `tests/test_design.py` reprova o CI se isso acontecer.

### Cores (tema escuro é o padrão e o único obrigatório)

| Token | Valor | Uso |
|---|---|---|
| `--fundo` | `#0b0e14` | fundo da página |
| `--superficie` | `#121821` | cards |
| `--superficie-2` | `#19212c` | cabeçalho de tabela, hover, tooltip |
| `--borda` | `#232c38` | bordas e linhas de grade dos gráficos |
| `--texto` | `#e6e9ef` | números e títulos |
| `--texto-2` | `#a3adbb` | rótulos e textos de apoio |
| `--texto-3` | `#7d8796` | metadados (fonte, horário) |
| `--destaque` | `#7aa2f7` | links, foco, seleção, série neutra de gráfico |
| `--alta` | `#3fb68b` | variação positiva |
| `--baixa` | `#f0616d` | variação negativa |
| `--alerta` | `#e5a54b` | anomalias, dado desatualizado |
| `--alta-fundo` | `rgba(63,182,139,.12)` | fundo de selo e barra de alta |
| `--baixa-fundo` | `rgba(240,97,109,.12)` | fundo de selo e barra de baixa |

O `:root` declara `color-scheme: dark`. Todo texto sobre `--superficie` atinge contraste WCAG AA (4,5:1); `--texto-3` só é usado em textos de no máximo uma linha de metadado.

### Tipografia

- Família: pilha do sistema (`-apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif`). Nada de fontes externas: a CSP só libera os CDNs do stack.
- **Todo número** usa `font-variant-numeric: tabular-nums` e fica alinhado à direita em tabelas.
- Escala única: `--fs-meta` 12px, `--fs-base` 14px, `--fs-titulo` 15px, `--fs-kpi` 22px, `--fs-hero` 40px. Pesos: 400, 500 e 600.
- Títulos de card em `--fs-titulo`, peso 600, cor `--texto`. Sem caixa alta, sem emoji.

### Espaçamento e forma

- Escala de 4px: `--e1` 4px, `--e2` 8px, `--e3` 12px, `--e4` 16px, `--e5` 24px. Nenhum espaçamento fora dela.
- Raio `--raio` 10px nos cards e 6px em selos e botões. Sem sombra: a separação vem da diferença entre `--fundo` e `--superficie` e de uma borda de 1px `--borda`.

## 3. Grade e layout

- Uma faixa superior fixa (`header`) com o nome do produto, o estado do pregão (aberto, fechado, leilão) e o horário da última coleta em BRT.
- O conteúdo é um `<main class="grade">` em CSS Grid:
  - ≥ 1200px: 12 colunas, largura máxima 1600px, `gap: var(--e3)`, margem lateral `--e4`;
  - 768 a 1199px: 6 colunas;
  - < 768px: 1 coluna, margem lateral `--e3`, sem rolagem horizontal em 390px.
- Cada painel declara sua largura por classe (`span-3`, `span-4`, `span-6`, `span-8`, `span-12`), nunca por estilo inline. Em 6 colunas, `span-3` e `span-4` viram metade da linha; `span-6` em diante, linha inteira.
- **Acima da dobra em 1440×900** ficam: o Ibovespa com gráfico (`span-8`), tendência e termômetro de dispersão empilhados ao lado (`span-4`), e o começo da linha de rankings.
- Distribuição de referência para os painéis atuais:

| Linha | Painéis |
|---|---|
| 1 | Ibovespa hoje + gráfico (8) · Tendência e Dispersão empilhados (4) |
| 2 | Maiores altas (4) · Maiores baixas (4) · Radar de volume (4) |
| 3 | Sensibilidade ao dólar (6) · próximos painéis (3 ou 6) |

Painel novo entra na primeira posição livre que respeite o tamanho do seu conteúdo. Ranking de até 5 itens é `span-3` ou `span-4`; painel com gráfico é `span-6` ou maior.

## 4. Componentes

Todos moram como macros Jinja em `app/templates/componentes.html`. Um painel novo monta suas partes com eles; se faltar um componente, ele é criado lá, com teste, antes de ser usado.

- **`painel(titulo, span, metodo, fonte, horario)`**: o card. Cabeçalho com título à esquerda e um botão `ⓘ` à direita que abre o método de cálculo (`<details>` nativo, sem JS). Rodapé de uma linha em `--fs-meta` e `--texto-3`: `Fonte · dd/mm/aaaa HH:MM BRT`. Transparência (PRODUTO.md seção 1) mora aqui e em nenhum outro lugar.
- **`kpi(valor, rotulo, variacao)`**: número em `--fs-kpi` (ou `--fs-hero` no Ibovespa), rótulo acima em `--texto-2`, variação abaixo com seta.
- **`variacao(valor_formatado, sinal)`**: texto com `▲` ou `▼` e cor `--alta`/`--baixa`; zero usa `--texto-2` e `■`. A seta é obrigatória: a cor nunca é a única pista.
- **`tabela_ativos(linhas, colunas)`**: linhas de 32px, cabeçalho em `--superficie-2`, ticker em peso 600, números à direita, sem bordas verticais, hover em `--superficie-2`. Quando a coluna principal for uma magnitude (variação, razão de volume, correlação), a célula leva uma **barra horizontal discreta** proporcional ao valor (fundo `--alta-fundo` ou `--baixa-fundo`), para o olho comparar sem ler.
- **`medidor(pct, rotulo)`**: barra dividida alta × baixa, usada no termômetro de dispersão.
- **`estado(tipo)`**: `carregando`, `indisponivel`, `desatualizado`. Cada um com texto curto e o mesmo tamanho do conteúdo que substitui, para a página não pular. Dado com mais de 30 min durante o pregão ganha selo `desatualizado` em `--alerta`.

## 5. Gráficos (Plotly)

O stack usa Plotly (PRODUTO.md seção 2); trocar de biblioteca exige ADR. O tema é único e mora em `app/static/graficos.js`, que lê as cores dos tokens CSS com `getComputedStyle` e expõe `Painel.grafico(id, traces, opcoes)`. Nenhum template chama `Plotly.newPlot` direto.

- Fundo transparente, fonte da página em 12px `--texto-2`, `separators: ',.'`, `displayModeBar: false`, `responsive: true`.
- Grade só no eixo Y, em `--borda`; eixo X sem grade e com no máximo 6 rótulos de data no formato `dd/mm`.
- Linha de 1,5px; série de preço com preenchimento até o mínimo do período em 10% de opacidade da cor da linha.
- Cor da série: `--alta` ou `--baixa` conforme o sinal do período; séries neutras em `--destaque`; médias móveis em `--texto-3` tracejado.
- Marcador e rótulo no último ponto com o valor atual.
- Tooltip em `--superficie-2`, sem borda colorida, com data `dd/mm/aaaa` e valor no padrão brasileiro.
- Altura fixa por contexto (280px no Ibovespa, 160px em gráficos secundários, 48px em sparklines) para não haver salto de layout.
- Todo gráfico tem `aria-label` com um resumo em texto ("Ibovespa nos últimos 30 pregões: de 128.410 a 131.482, alta de 2,4%").

## 6. Movimento e interação

- Transições de no máximo 150ms, só em cor e opacidade. Nada pisca, nada gira, nada entra deslizando.
- Atualização via HTMX troca o conteúdo do painel sem mudar sua altura.
- Foco visível em `--destaque` com 2px de contorno em todo elemento interativo.

## 7. Proibido

- Estilo inline (`style="..."`) em templates.
- Cores, tamanhos ou espaçamentos fora dos tokens.
- Tema claro como padrão, fundo branco ou cinza claro em qualquer card.
- Sombras, gradientes decorativos, ícones de enfeite, emoji em títulos.
- Card com um único número e mais de 120px de altura vazia.
- Largura máxima de conteúdo menor que 1200px em telas largas.
- Tabela que ocupa a largura inteira da tela para três colunas.

## 8. Checklist visual (vale para todo PR que muda a interface)

Rode `make telas`, **abra as duas imagens geradas em `telas/`** e responda no relatório da execução e no corpo do PR:

- [ ] Em 1440px, o Ibovespa, a tendência e a dispersão aparecem sem rolar?
- [ ] Em 390px, não há rolagem horizontal e a ordem dos painéis faz sentido (Ibovespa primeiro)?
- [ ] Algum card tem área vazia maior que o próprio conteúdo?
- [ ] Toda alta e baixa tem seta além da cor?
- [ ] Todo número está alinhado e com algarismos tabulares?
- [ ] O gráfico usa o tema de `graficos.js` e tem resumo em `aria-label`?
- [ ] O painel novo usa as macros de `componentes.html` e uma classe `span-N`?
- [ ] Comparada com `docs/design/referencia.html`, a tela parece parte do mesmo sistema?

Se alguma resposta for "não", o PR não está pronto.
