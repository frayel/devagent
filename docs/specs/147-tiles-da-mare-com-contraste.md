---
id: 147
titulo: Os tiles da Maré têm contraste legível
status: done
esforco: P
gaveta: experiência
aceite: tests/test_aceite_147.py
brief: P2-1
depende_de: 027
revisada: 2026-11-14
---

## Problema
O usuário perguntou: "dá para ler PETR4 e VALE3 no quadradinho da Maré?"

Em 05/11/2026 o contraste entre texto e fundo desses tiles foi observado como baixo. Observação histórica, sem medição de cor naquele dia. No código atual o tile (`.heatmap-ativo` em `app/static/tema.css`) usa `color: white` e `font-size: 0.7rem`. O fundo vem de `data-cor` (`--alta`, `--baixa` ou `--borda`) e de `data-opacidade = 0,3 + 0,7 × min(|variação| / 5, 1)`, aplicado em `app/static/ui.js` e composto sobre `--superficie`.

Medido nos tokens de `app/static/tema.css` em 06/11/2026, razão de contraste WCAG: branco sobre `--alta` `#3fb68b` ≈ 2,5:1; branco sobre `--baixa` `#f0616d` ≈ 3,2:1. Texto abaixo de 18pt precisa de 4,5:1 (WCAG 2.1, critério 1.4.3). Com opacidade 1, que a fórmula atinge quando `|variação| ≥ 5%`, o tile não chega lá.

**Correção da revisão (14/11/2026):** a opacidade é aplicada com `opacity: var(--ativo-opacidade)` no próprio `.heatmap-ativo`, e `opacity` em CSS desbota o elemento inteiro, **texto incluído**. O texto renderizado não é branco: é `opacidade × branco + (1 − opacidade) × --superficie`. Por isso a opacidade baixa é o pior caso, não o melhor. Medido nos tokens atuais (cálculo na seção *Cálculos*):

| sinal | \|variação\| | opacidade | texto como está | se o texto fosse branco opaco |
|---|---|---|---|---|
| alta | 0,1 | 0,31 | ≈ 1,6:1 | ≈ 10:1 |
| alta | 1 | 0,44 | 1,84:1 | 7,55:1 |
| alta | ≥ 5 | 1,00 | 2,54:1 | 2,54:1 |
| baixa | 1 | 0,44 | 2,15:1 | 8,80:1 |
| baixa | ≥ 5 | 1,00 | 3,16:1 | 3,16:1 |
| zero (`--borda`) | 0 | 0,30 | 2,54:1 | 16,76:1 |

Nenhum estado atinge 4,5:1 hoje. O defeito depende do estado, não de um ticker específico. PETR4 e VALE3 estão entre os dez primeiros do heatmap quando entram na lista (`app/services/mare.py` corta em dez por financeiro).

Duas consequências para a implementação, que a revisão deixa explícitas:
1. A transparência tem de sair do texto: o tile não pode usar `opacity` no elemento inteiro. A intensidade vai só para o fundo (por exemplo `color-mix(in srgb, var(--ativo-cor) calc(var(--ativo-opacidade) * 100%), var(--superficie))`, ou outra forma que não toque a cor do texto).
2. Com texto branco opaco, a escala atual de 0,3 a 1 ainda falha no topo: o fundo só aceita branco até opacidade ≈ 0,68 em `--alta` e ≈ 0,79 em `--baixa`. O desenvolvimento escolhe entre limitar a intensidade máxima do fundo, mudar a cor do texto conforme o fundo ou outra saída dentro dos tokens; a spec trava o resultado (≥ 4,5:1), não a técnica.

## Comportamento esperado
- Em todo estado que a fórmula de intensidade produz (variação positiva, negativa e zero), a cor **renderizada** do texto do ticker contra o fundo composto do tile é de pelo menos 4,5:1. "Renderizada" inclui qualquer `opacity` que atinja o texto.
- `.heatmap-ativo` não declara `opacity` (a intensidade vai só para o fundo).
- A informação não depende só da cor (WCAG 1.4.1). O tile mostra `▲`, `▼` ou `■` junto do ticker, com o mesmo critério da macro `variacao`. O atributo `title` pode continuar e não é o único canal.
- Tema escuro, tokens de `tema.css`. Sem hexadecimal novo no template. `tests/test_design.py` segue reprovando cor solta.
- O heatmap continua sendo os dez ativos de maior financeiro da Maré. Não se cria outro indicador para "melhorar" o tile.

## Fontes de dados
A lista `heatmap` que a spec 027 já grava. Plano B: sem heatmap, o bloco não é desenhado, como hoje.

## Cálculos
Intensidade (hoje chamada opacidade) = `0,3 + 0,7 × min(|variação| / 5, 1)`, com `variação` em **percentual** (como `mare.py` grava: `(fech / fech_ant − 1) × 100`; 1,0 = 1%).

Fundo composto = intensidade × cor do sinal + (1 − intensidade) × `--superficie`, canal a canal em sRGB 0–255. Se o CSS final ainda aplicar alguma opacidade ao texto, a cor do texto passa pela mesma composição. Contraste = `(L_clara + 0,05) / (L_escura + 0,05)` com a luminância relativa sRGB do WCAG 2.1 (`c ≤ 0,04045 → c/12,92`, senão `((c+0,055)/1,055)^2,4`; `L = 0,2126 R + 0,7152 G + 0,0722 B`).

Exemplo de ponta a ponta, com o CSS de hoje: PETR4 fecha a 38,38 após 38,00 → variação = (38,38/38,00 − 1) × 100 = 1,0 (%). Intensidade = 0,3 + 0,7 × min(1,0/5, 1) = 0,44. Fundo = 0,44 × `#3fb68b` (63,182,139) + 0,56 × `#121821` (18,24,33) ≈ (38, 94, 80), L ≈ 0,089. Texto com `opacity` 0,44 = 0,44 × (255,255,255) + 0,56 × (18,24,33) ≈ (122, 126, 131), L ≈ 0,206. Contraste = (0,206 + 0,05)/(0,089 + 0,05) ≈ 1,84:1. Reprovado; sem `opacity` no texto, o mesmo fundo dá (1 + 0,05)/(0,089 + 0,05) ≈ 7,55:1.

O teste calcula isso em Python a partir dos tokens lidos de `tema.css` e da regra `.heatmap-ativo` como ela estiver, para os estados possíveis: positivo e negativo com `|variação|` em {0,1; 1; 5; 10} e zero com variação 0 (sinal zero só existe com variação 0).

## Critérios de aceite
- [ ] Para cada um dos nove estados acima, a razão do teste é ≥ 4,5.
- [ ] O teste lê a regra `.heatmap-ativo` de `tema.css` e falha se ela declarar `opacity`.
- [ ] HTML de um tile com variação positiva contém `▲` e o ticker; variação negativa contém `▼`; zero contém `■`.
- [ ] `tests/test_design.py` continua verde.
- [ ] `tests/test_aceite_147.py` usa `exigir_spec_done("147")` e não abre rede.

## Invariantes de produção
- Texto de `.heatmap-ativo`, na cor que o navegador pinta, sobre o fundo pintado do tile atinge 4,5:1 no tema escuro, nos tiles mais fracos (variação perto de zero) e nos mais fortes (|variação| ≥ 5%).
- Tile de alta e tile de baixa distinguem-se também pelo sinal escrito, não só pela cor.

## Fora do escopo
- Redesign da Maré, do gauge ou da escala de cores do produto.
- Contraste do rodapé (spec 148).
- Medir de novo o pixel exato visto em 05/11/2026. A fórmula e os tokens de hoje é que o teste trava.

## Plano de validação
`pytest -q tests/test_aceite_147.py tests/test_design.py` sem internet. O PR de implementação, se mudar a interface, segue o checklist visual do `docs/DESIGN.md` com `make telas`. Esta rodada não gera captura.

## Revisão
14/11/2026. A versão original modelava o texto como branco opaco e concluía que a opacidade 0,3 passava. O CSS aplica `opacity` ao elemento inteiro, então o texto desbota junto e todos os estados falham (1,6:1 a 3,2:1). A revisão corrigiu o diagnóstico, acrescentou o exemplo numérico de ponta a ponta, tirou as combinações impossíveis (sinal positivo com variação 0) e exige que o teste falhe se `opacity` voltar à regra. Tamanho: `grep -rl heatmap app tests` dá 5 arquivos de código e 2 de teste; a implementação mexe em `tema.css`, `index.html` e no teste novo. Nada no código atual já faz o que a spec pede. Não há outra spec `ready` ou `draft` do mesmo tema (148 é rodapé).
