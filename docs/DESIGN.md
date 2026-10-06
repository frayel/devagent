# DESIGN.md · Guia visual do Painel B3

> O agente segue este guia em toda mudança de interface e pode alterá-lo, mas só num PR `agent:` dedicado a ele. Nunca altere este arquivo no mesmo PR que muda a interface.
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
- **Acima da dobra em 1440×900** ficam: o Ibovespa com gráfico (`span-8`), a Maré do mercado ao lado (`span-4`), com alturas parecidas, e o começo da linha de rankings.
- Distribuição de referência para os painéis atuais:

| Linha | Painéis |
|---|---|
| 1 | Ibovespa hoje + gráfico (8) · Maré do mercado (4) |
| 2 | Maiores altas (4) · Maiores baixas (4) · Radar de volume (4) |
| 3 | Sensibilidade ao dólar (6) · próximos painéis (3 ou 6) |
| 4 | Tendência (4) · Apetite a risco (4) · Dispersão (4), todos com gauge |

A tabela é o ponto de partida, não uma regra fixa. **A grade é revista a cada painel novo:** o PR que acrescenta um painel decide onde ele entra pela importância da pergunta que responde, não pela ordem de chegada, e pode reorganizar, encolher ou fundir os vizinhos para isso. O que não muda é o princípio: acima da dobra, em 1440×900, fica o que diz como o mercado está e o que se destaca hoje. Ranking de até 5 itens é `span-3` ou `span-4`; painel com gráfico é `span-6` ou maior. A cada três painéis novos, o agente faz uma revisão de experiência da página inteira (`devagent/skills/rever-experiencia.md`).

## 4. Componentes

Todos moram como macros Jinja em `app/templates/componentes.html`. Um painel novo monta suas partes com eles; se faltar um componente, ele é criado lá, com teste, antes de ser usado.

- **`painel(titulo, span, metodo, fonte, horario)`**: o card. Cabeçalho com título à esquerda e um botão `ⓘ` à direita que abre o método de cálculo (`<details>` nativo, sem JS). Rodapé de uma linha em `--fs-meta` e `--texto-3`: `Fonte · dd/mm/aaaa HH:MM BRT`. Transparência (PRODUTO.md seção 1) mora aqui e em nenhum outro lugar.
- **`kpi(valor, rotulo, variacao)`**: número em `--fs-kpi` (ou `--fs-hero` no Ibovespa), rótulo acima em `--texto-2`, variação abaixo com seta.
- **`variacao(valor_formatado, sinal)`**: texto com `▲` ou `▼` e cor `--alta`/`--baixa`; zero usa `--texto-2` e `■`. A seta é obrigatória: a cor nunca é a única pista.
- **`tabela_ativos(linhas, colunas)`**: linhas de 32px, cabeçalho em `--superficie-2`, ticker em peso 600, números à direita, sem bordas verticais, hover em `--superficie-2`. Quando a coluna principal for uma magnitude (variação, razão de volume, correlação), a célula leva uma **barra horizontal discreta** proporcional ao valor (fundo `--alta-fundo` ou `--baixa-fundo`), para o olho comparar sem ler.
- **`gauge(valor, rotulo, minimo, maximo, formato, faixas, divergente, resumo)`**: semicírculo em SVG para todo **valor único que vive numa escala** (seção 5.1). Detalhes na seção 5.2.
- **`medidor(pct, rotulo)`**: barra dividida, só para **partes de um todo** (ex.: 19 subiram × 11 caíram). Não é usada para um valor único: para isso existe o `gauge`.
- **`estado(tipo)`**: `carregando`, `indisponivel`, `desatualizado`. Cada um com texto curto e o mesmo tamanho do conteúdo que substitui, para a página não pular. Dado com mais de 30 min durante o pregão ganha selo `desatualizado` em `--alerta`.

## 5. Gráficos (Plotly)

O stack usa Plotly (PRODUTO.md seção 2); trocar de biblioteca exige ADR. O tema é único e mora em `app/static/graficos.js`, que lê as cores dos tokens CSS com `getComputedStyle` e expõe `Painel.grafico(id, traces, opcoes)`. Nenhum template chama `Plotly.newPlot` direto.

- Fundo transparente, fonte da página em 12px `--texto-2`, `separators: ',.'`, `displayModeBar: false`, `responsive: true`.
- Grade só no eixo Y, em `--borda`; eixo X sem grade e com no máximo 6 rótulos de data no formato `dd/mm`.
- Linha de 1,5px; série de preço com preenchimento até o mínimo do período em 10% de opacidade da cor da linha.
- **Eixo Y de preço nunca começa em zero:** vai de 2% abaixo do mínimo do período até um pouco acima do máximo. Começar em zero achata a série numa faixa estreita no topo do gráfico.
- Cor da série: `--alta` ou `--baixa` conforme o sinal do período; séries neutras em `--destaque`; médias móveis em `--texto-3` tracejado.
- Marcador e rótulo no último ponto com o valor atual.
- Tooltip em `--superficie-2`, sem borda colorida, com data `dd/mm/aaaa` e valor no padrão brasileiro.
- Altura fixa por contexto (200px no Ibovespa, 160px em gráficos secundários, 48px em sparklines) para não haver salto de layout.
- Todo gráfico tem `aria-label` com um resumo em texto ("Ibovespa nos últimos 30 pregões: de 128.410 a 131.482, alta de 2,4%").

### 5.1 A forma do dado escolhe o gráfico

Um número solto obriga o leitor a lembrar a escala. Sempre que o dado tiver escala, ele vira gráfico:

| O dado é | Forma | Exemplo no painel |
|---|---|---|
| um valor numa escala com limites conhecidos (%, 0 a 10, 0 a 100, correlação) | `gauge` | dispersão 63%, coesão 7/10, Maré 68 |
| um valor com sinal em torno de zero (diferença, desvio, distância de média) | `gauge` divergente, com o zero no topo | SMLL − IBOV, bancos − commodities, distância da MM21 |
| uma série no tempo | linha Plotly; em espaço curto, sparkline de 48px | Ibovespa 30 pregões, histórico da Maré |
| comparação entre até 10 itens | barra horizontal na célula da tabela | rankings |
| partes de um todo (até 5 partes) | `medidor` (barra dividida) | subiram × caíram |

Fica como número sem gráfico só o que não tem escala natural: preço, pontos do índice, volume em reais. Na dúvida, o agente pergunta "contra o quê o leitor compara este número?": se existir resposta, ela vira o eixo do gráfico.

Toda revisão de experiência (`devagent/skills/rever-experiencia.md`) procura números soltos que cabem nesta tabela.

### 5.2 Gauge

- SVG desenhado **no servidor**, dentro da macro, sem JavaScript e sem Plotly: não pisca na carga, não muda de altura e é testável no HTML.
- `viewBox="0 0 120 68"`, arco de 180° com raio 50 centrado em (60, 60): `M10 60 A50 50 0 0 1 110 60`. Altura de 96px em painel `span-3`/`span-4` e 140px quando é o protagonista do painel.
- Trilho com `pathLength="100"` e traço de 10 em `--superficie-2`. O valor é o mesmo arco com `stroke-dasharray="{pct} 100"`, na cor do significado: `--alta`, `--baixa` ou `--destaque` (neutro). Pontas retas, sem gradiente.
- **Divergente:** o preenchimento parte do topo (50) até o valor, com `stroke-dasharray="{|pct−50|} 100"` e `stroke-dashoffset="-{min(pct,50)}"`; cor `--alta` acima de zero e `--baixa` abaixo.
- **Faixas** (opcional): anel externo de 3px, raio 57, um segmento por faixa, com as classes `.g-cor-1` a `.g-cor-5`: `--baixa`, `--baixa` a 45% de opacidade, `--texto-3`, `--alta` a 45% e `--alta` (da pior para a melhor). Com faixas, o arco do valor usa a cor da faixa atual e uma agulha curta em `--texto` marca a posição só na coroa do arco (`<line>` de (60,16) a (60,1) com `transform="rotate({pct·1,8 − 90} 60 60)"`), para nunca passar por cima do número.
- O número aparece **sempre** em texto no centro, em `--fs-kpi` (ou `--fs-hero` quando protagonista), com algarismos tabulares, e o rótulo da faixa logo abaixo em `--texto-2`. O gauge nunca substitui o número; ele dá a escala.
- Mínimo e máximo da escala em `--fs-meta` e `--texto-3` nas pontas do arco.
- Valor fora da escala é cortado no limite e ganha `+` ou `−` antes do rótulo do limite ("> +2,0 p.p."). Nunca extrapola o arco.
- `role="img"` e `aria-label` com o resumo em texto ("Maré do mercado: 68 de 100, Confiança").
- Cores só por classe (`.g-trilho`, `.g-valor.alta`, `.g-faixa-1` …); nenhum `fill` ou `stroke` com cor escrita no SVG.

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
- [ ] O gráfico usa o tema de `graficos.js` (ou é um `gauge` da macro) e tem resumo em `aria-label`?
- [ ] Sobrou algum número solto que tem escala e deveria ser `gauge`, linha ou barra (seção 5.1)?
- [ ] O painel novo usa as macros de `componentes.html` e uma classe `span-N`?
- [ ] Com o painel novo, a hierarquia ainda faz sentido? Algum painel deveria subir, descer, encolher ou se fundir com outro?
- [ ] Comparada com `docs/design/referencia.html`, a tela parece parte do mesmo sistema?

Se alguma resposta for "não", o PR não está pronto.
