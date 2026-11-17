---
id: 169
titulo: Os tiles do heatmap mostram o nome do ativo inteiro
status: ready
esforco: P
gaveta: experiência
aceite: tests/test_aceite_169.py
origem: nova
---

## Problema
Qual é o ativo desse quadrado?

O heatmap da Maré do Mercado (`.heatmap` em `app/templates/index.html:91`, `.heatmap-ativo` em `app/static/tema.css:693`) dá a cada tile `width: max(30px, peso * 100%)`. O peso é a fração do financeiro do ativo entre os dez maiores (`app/services/mare.py:298`, `financeiro / total_fin`, de 0 a 1). Um ativo com 4% do financeiro recebe 4% da largura, e 4% de uma linha de 374 px são 15 px: o piso de 30 px vale. O texto (`▲ KLBN11`, 0,7rem) precisa de uns 59 px, e a regra tem `overflow: hidden` e `white-space: nowrap`, então o nome some pela direita. O `title` mostra o ticker inteiro, mas só no hover, que não existe no celular.

Medido em 17/11 no Chromium headless, com `tema.css` de hoje e dez ativos de pesos 0,22, 0,20, 0,15, 0,10, 0,09, 0,07, 0,06, 0,05, 0,04 e 0,02 (`PETR4`, `VALE3`, `ITUB4`, `BBDC4`, `BOVA11`, `ABEV3`, `B3SA3`, `WEGE3`, `KLBN11`, `RENT3`), contêiner com a largura da janela menos 16 px (8 px de cada lado):

| Janela | Tiles cortados (de 10) | Menor tile |
|---|---|---|
| 360 px | 7 | 31 px |
| 390 px | 7 | 31 px |
| 768 px | 3 | 39 px |
| 1280 px | 1 (`KLBN11`, 51 px) | 51 px |

A largura natural do texto, medida com `scrollWidth`, vai de 55 a 59 px nos tickers de 5 e 6 caracteres. O defeito não depende de ticker, só do peso e da largura da tela: o heatmap é o único componente do painel em que o nome do ativo é o conteúdo, e ele não se lê.

## Comportamento esperado
1. **Largura mínima do tile pelo texto.** `.heatmap-ativo` ganha `min-width: 10ch` e `box-sizing: border-box`. O `ch` acompanha a fonte do tile (0,7rem), então o mínimo continua certo se o tamanho do texto mudar. A 0,7rem, 10ch mais o `padding` de 2 px de cada lado dão 71 px, contra 59 px do texto mais largo medido (folga de 12 px para `W` e `M`).
2. **O peso reparte a sobra, não define a largura.** No lugar de `flex-grow` mais `width: max(30px, ...)`, a regra passa a `flex: var(--ativo-peso, 1) 1 0`. A base é zero: cada tile começa no mínimo e a sobra da linha se divide na proporção do peso. Com `flex-basis` igual ao peso a soma passa de 100% por causa do `gap` (9 × 2 px) e o último tile caía sozinho numa linha de baixo; com base zero a linha quebra só quando o próximo mínimo não cabe, e cada linha termina preenchida de ponta a ponta.
3. **O heatmap quebra em linhas por conta própria.** `.heatmap` já tem `flex-wrap: wrap` e não muda. Na tela larga os dez tiles cabem numa linha; no celular, em duas ou três. Nenhum JavaScript novo.
4. **Sem o JavaScript, tiles iguais.** O peso chega pela variável `--ativo-peso`, que `app/static/ui.js:13` escreve por causa da CSP (sem `style` inline). O `1` do `var(--ativo-peso, 1)` faz a página ainda legível se o script não rodar: dez tiles de largura igual, nenhum cortado.
5. **Ticker fora do padrão não vaza.** Um ticker de mais de 8 caracteres não precisa caber: o tile mostra reticências (`text-overflow: ellipsis`) e não ultrapassa o contêiner. O `title` com ticker e variação continua como está.

Não muda: a cor e a intensidade do fundo (`color-mix`), o texto branco, o ▲/▼/■, o `padding` vertical, o `border-radius`, os dez ativos de maior financeiro e o contraste da spec 147.

## Fontes de dados
Nenhuma. O heatmap já recebe `ativos[].ticker`, `variacao` e `peso` da Maré. Plano B não se aplica: a mudança é só de CSS.

## Cálculos
O peso é uma **fração** (0 a 1), não percentual: `PETR4` com `financeiro` 1.500.000 num total de 6.818.182 tem `peso = 0,22`. Largura de cada tile, de ponta a ponta, num contêiner de 374 px (janela de 390 px menos 16 px), dez tiles, `gap` de 2 px:

1. Mínimo do tile: 10ch + 4 px de `padding` ≈ 71 px.
2. Quantos cabem numa linha: `n × 71 + (n − 1) × 2 ≤ 374`, então `n = 5` (363 px). Dez tiles, duas linhas de cinco.
3. Largura da primeira linha (`PETR4`, `VALE3`, `ITUB4`, `BBDC4`, `BOVA11`, pesos 0,22 / 0,20 / 0,15 / 0,10 / 0,09, soma 0,76): sem mínimo, os tiles dividiriam os 366 px úteis (374 menos 4 `gap` de 2 px) na proporção do peso, e `BBDC4` ficaria com 48 px e `BOVA11` com 43 px. Os dois ficam abaixo de 71 px, então travam no mínimo; os 224 px que sobram (366 − 2 × 71) se dividem entre os outros três (soma 0,57): `ITUB4` receberia 59 px, também abaixo, e trava em 71 px; os 153 px restantes vão para `PETR4` (0,22 / 0,42 × 153 = 80 px) e `VALE3` (0,20 / 0,42 × 153 = 73 px). Larguras: 80, 73, 71, 71 e 71 px, que somam 366. É o que o Chromium devolve na medida.
4. A segunda linha se reparte do mesmo jeito, pelos pesos 0,07 / 0,06 / 0,05 / 0,04 / 0,02.

Na janela de 1280 px (contêiner de 1264 px) os dez tiles cabem numa linha (10 × 71 + 9 × 2 = 728 px): `PETR4` 253 px, `VALE3` 230 px, `ITUB4` 174 px, `BBDC4` 117 px, e os quatro últimos no mínimo de 71 px. Proporção: a ordem dos pesos se mantém; a proporção exata só vale para os tiles acima do mínimo.

Pesos todos 0 (`total_fin = 0`) não chegam à tela: `heatmap` só é montado com amostra válida. Se chegassem, os tiles ficariam no mínimo, alinhados à esquerda, sem sumir.

## Critérios de aceite
- [ ] `tests/test_aceite_169.py`, com `exigir_spec_done("169")`, roda no Chromium headless como `tests/test_aceite_156.py` (página montada com `app/static/tema.css` e as variáveis de `app/static/ui.js`, sem internet) e confere, com os dez ativos do exemplo do *Problema*, em janelas de 360, 390, 768 e 1280 px:
  - **nenhum tile cortado:** para todo tile, `scrollWidth <= clientWidth`;
  - **nenhum tile menor que 10ch** (medido com `getBoundingClientRect`, tolerância de 1 px);
  - **linha preenchida:** em cada linha, a soma das larguras dos tiles mais os `gap` é o da largura do contêiner, tolerância de 1 px. Isso pega o tile órfão;
  - **quebra esperada:** 1 linha a 768 e 1280 px, no máximo 3 a 360 e 390 px;
  - **peso ordena a largura a 1280 px:** `PETR4 >= VALE3 >= ITUB4 >= BBDC4 >= BOVA11` (larguras dos tiles de maior peso);
  - **ticker mais largo:** com `TAEE11` e `KLBN11` no lugar de dois ativos, e com `▼` e `■` no lugar de `▲`, o resultado de nenhum cortado se mantém a 360 px.
- [ ] **Sem JavaScript:** sem escrever `--ativo-peso`, `--ativo-cor` e `--ativo-opacidade`, nenhum tile fica cortado a 390 px e os dez têm a mesma largura (tolerância de 1 px).
- [ ] **Ticker de 9 caracteres:** com `ABCDEFGHI`, o tile não passa da borda direita do contêiner.
- [ ] `tests/test_aceite_147.py` (contraste e ausência de `opacity` em `.heatmap-ativo`), `tests/test_aceite_123.py` e o resto do `make verify` continuam verdes, sem mudar asserção.
- Arquivos tocados: `app/static/tema.css` e o novo `tests/test_aceite_169.py`. Medido com `grep -rlw "heatmap-ativo" app tests`: 4 arquivos referenciam a classe (CSS, template, `ui.js`, testes 123 e 147), e nenhum deles muda além do CSS. O `docs/STATE.md` e o `CHANGELOG.md` são atualizados na entrega, como em todo PR.

## Invariantes de produção
- Em `/`, na Maré do Mercado, todo tile do heatmap mostra o ticker inteiro (confira em 390 px de largura): nenhum nome termina em corte.
- O heatmap tem de uma a três linhas e nenhuma linha termina com espaço vazio à direita.
- Ordem, cor e ▲/▼/■ dos tiles são os mesmos de antes do deploy.

## Fora do escopo
- Proporção exata entre os tiles: abaixo do mínimo, o peso deixa de mandar na largura. É a troca por ler o nome. Treemap com área proporcional ao peso e rótulos que se escondem é outra ideia, de esforço maior, e não está na *Fila*.
- Ordenar ou agrupar os ativos por peso nas linhas (hoje a ordem é a da Maré, por financeiro decrescente, que já é do maior para o menor).
- Mudar quantos ativos o heatmap tem (os dez maiores, spec 147) ou o que a cor significa.
- Truncar o ticker por regra, trocar `title` por tooltip ou abrir o ativo por clique (spec 123 deixou o clique fora).
