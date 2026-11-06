---
id: 147
titulo: Os tiles da Maré têm contraste legível
status: ready
esforco: P
gaveta: experiência
aceite: tests/test_aceite_147.py
brief: P2-1
depende_de: 027
---

## Problema
O usuário perguntou: "dá para ler PETR4 e VALE3 no quadradinho da Maré?"

Em 05/11/2026 o contraste entre texto e fundo desses tiles foi observado como baixo. Observação histórica, sem medição de cor naquele dia. No código atual o tile (`.heatmap-ativo` em `app/static/tema.css`) usa `color: white` e `font-size: 0.7rem`. O fundo vem de `data-cor` (`--alta`, `--baixa` ou `--borda`) e de `data-opacidade = 0,3 + 0,7 × min(|variação| / 5, 1)`, aplicado em `app/static/ui.js` e composto sobre `--superficie`.

Medido nos tokens de `app/static/tema.css` em 06/11/2026, razão de contraste WCAG: branco sobre `--alta` `#3fb68b` ≈ 2,5:1; branco sobre `--baixa` `#f0616d` ≈ 3,2:1. Texto abaixo de 18pt precisa de 4,5:1 (WCAG 2.1, critério 1.4.3). Com opacidade 1, que a fórmula atinge quando `|variação| ≥ 5%`, o tile não chega lá. Com opacidade 0,3, o branco sobre a cor já misturada a `--superficie` fica acima de 4,5:1. O defeito depende do estado, não de um ticker específico. PETR4 e VALE3 estão entre os dez primeiros do heatmap quando entram na lista (`app/services/mare.py` corta em dez por financeiro).

## Comportamento esperado
- Em todo estado que a fórmula de opacidade produz (variação positiva, negativa e zero; opacidade de 0,3 a 1), a cor do texto do ticker contra o fundo composto do tile é de pelo menos 4,5:1.
- A informação não depende só da cor (WCAG 1.4.1). O tile mostra `▲`, `▼` ou `■` junto do ticker, com o mesmo critério da macro `variacao`. O atributo `title` pode continuar e não é o único canal.
- Tema escuro, tokens de `tema.css`. Sem hexadecimal novo no template. `tests/test_design.py` segue reprovando cor solta.
- O heatmap continua sendo os dez ativos de maior financeiro da Maré. Não se cria outro indicador para "melhorar" o tile.

## Fontes de dados
A lista `heatmap` que a spec 027 já grava. Plano B: sem heatmap, o bloco não é desenhado, como hoje.

## Cálculos
Fundo composto = opacidade × cor do sinal + (1 − opacidade) × `--superficie`. Contraste = `(L_clara + 0,05) / (L_escura + 0,05)` com a luminância relativa sRGB do WCAG 2.1. O teste calcula isso em Python a partir dos tokens e da fórmula, para `|variação|` em {0, 1, 5, 10} e para os três sinais.

## Critérios de aceite
- [ ] Para cada combinação acima, a razão do teste é ≥ 4,5.
- [ ] HTML de um tile com variação positiva contém `▲` e o ticker; variação negativa contém `▼`; zero contém `■`.
- [ ] `tests/test_design.py` continua verde.
- [ ] `tests/test_aceite_147.py` usa `exigir_spec_done("147")` e não abre rede.

## Invariantes de produção
- Texto de `.heatmap-ativo` sobre o fundo pintado do tile atinge 4,5:1 no tema escuro.
- Tile de alta e tile de baixa distinguem-se também pelo sinal escrito, não só pela cor.

## Fora do escopo
- Redesign da Maré, do gauge ou da escala de cores do produto.
- Contraste do rodapé (spec 148).
- Medir de novo o pixel exato visto em 05/11/2026. A fórmula e os tokens de hoje é que o teste trava.

## Plano de validação
`pytest -q tests/test_aceite_147.py tests/test_design.py` sem internet. O PR de implementação, se mudar a interface, segue o checklist visual do `docs/DESIGN.md` com `make telas`. Esta rodada não gera captura.
