---
id: 148
titulo: O rodapé do card continua legível
status: draft
esforco: P
gaveta: experiência
aceite: tests/test_aceite_148.py
brief: P2-2
depende_de: 141
revisada: 2026-11-14
---

## Problema
O usuário perguntou: "consigo ler a fonte e o horário sem aproximar o rosto da tela?"

Em 05/11/2026 os rodapés de fonte e as-of foram observados pequenos. Observação histórica. O guia (`docs/DESIGN.md`) fixa `--fs-meta` em 12px e `--texto-3` em `#7d8796` para uma linha de metadado. `.rodape` em `app/static/tema.css` já usa esses dois tokens. Medido em 06/11/2026, `#7d8796` sobre `--superficie` `#121821` fica em cerca de 4,9:1, acima do 4,5:1 do WCAG 2.1 critério 1.4.3 para texto comum. A spec não trata o token como ilegal. O que falta garantir é que o rodapé real use essa escala, que o contraste não caia abaixo de 4,5:1 e que fonte e horário existam no texto do card, não num `title` que só aparece no hover.

Quem torna o rodapé presente é a spec 141. Esta spec olha tamanho, contraste, zoom e independência de hover.

## Comportamento esperado
- `.rodape` permanece em `font-size: var(--fs-meta)` ou maior, e `--fs-meta` permanece 12px. Nenhum rodapé de card usa tamanho abaixo de 12px.
- A cor do rodapé sobre a superfície do card mantém contraste ≥ 4,5:1. Se um ajuste futuro trocar o token, o teste de razão falha antes do valor cair abaixo disso. Sem hexadecimal no template.
- Fonte e horário são o texto do `.rodape`, visível sem abrir o ⓘ e sem hover. O ⓘ continua no `<details>` para o método.
- Em 390px de largura o rodapé entra no fluxo do card, sem `overflow` que corte a linha. A 200% de zoom (WCAG 1.4.4) a mesma linha continua no DOM; o teste automático confere o CSS (`overflow` visível no card e fonte em `rem`/`px` que escala com o zoom do navegador, não um `px` travado dentro de um container com escala fixa). A captura em zoom fica no PR de implementação.

## Fontes de dados
Nenhuma. O horário é o carimbo já formatado pela spec 141.

## Cálculos
A mesma razão de contraste da spec 147, aplicada a `--texto-3` sobre `--superficie` e, se o rodapé passar a usar outro token existente, a esse par. Não se cria cor nova nesta spec.

## Critérios de aceite
- [ ] O teste lê `tema.css`: `--fs-meta` é `12px`, `.rodape` referencia `--fs-meta` e não declara `font-size` menor.
- [ ] A razão `--texto-3` / `--superficie` no teste é ≥ 4,5. Se a implementação mudar o par, o teste usa o par efetivo do `.rodape` e o limiar continua 4,5.
- [ ] HTML de card com fonte e horário: o texto dos dois está num elemento `.rodape`, e não está apenas em atributo `title`.
- [ ] `.painel` não usa `overflow: hidden` de um jeito que o teste considere corte do rodapé (o rodapé é irmão do conteúdo, dentro do `section`).
- [ ] `tests/test_aceite_148.py` usa `exigir_spec_done("148")` e não abre rede. `tests/test_design.py` continua verde.

## Invariantes de produção
- O rodapé visível de um card com dado tem fonte e horário em texto, no tamanho meta do guia ou maior.
- O contraste desse texto no tema escuro é de pelo menos 4,5:1.

## Fora do escopo
- Aumentar a escala tipográfica inteira.
- Contraste dos tiles da Maré (spec 147).
- Reescrever `docs/DESIGN.md`. O guia já descreve 12px; a implementação que precisar mudá-lo vai em PR `agent:` separado, não neste trabalho de tela.

## Plano de validação
`pytest -q tests/test_aceite_148.py tests/test_design.py` sem internet. O PR de implementação que alterar CSS roda `make telas` e olha o rodapé em 1440px e em 390px. Zoom de 200% entra nesse olhar. Esta rodada não produz a imagem.

## Revisão
14/11/2026. Marcada `draft`: a `main` já faz tudo o que a spec pede, e implementá-la não mudaria nada que o usuário vê. Conferido no código:

- Tamanho: `app/static/tema.css:20` declara `--fs-meta: 12px` e `:162` declara `.rodape { margin-top: auto; font-size: var(--fs-meta); color: var(--texto-3); }`. Nenhuma outra regra muda o tamanho do `.rodape`.
- Contraste, de ponta a ponta: `--texto-3` `#7d8796` tem canais 125, 135, 150 → linearizados 0,2051, 0,2423, 0,3050 → luminância 0,2126·0,2051 + 0,7152·0,2423 + 0,0722·0,3050 = 0,2389. `--superficie` `#121821` (18, 24, 33) → luminância 0,0089. Razão (0,2389 + 0,05) / (0,0089 + 0,05) = 4,90:1, acima de 4,5:1. O tema só tem a variante escura (`:root` único em `tema.css`).
- Texto, não `title`: a macro `painel` em `app/templates/componentes.html:17` escreve `Fonte {{ fonte }} · {{ horario }}` como texto de `<div class="rodape">`, sem `title`. `tests/test_design.py:110-113` e `tests/test_aceite_141.py:171` já leem o horário dentro do `.rodape` renderizado.
- Corte: `.painel` (`tema.css:117-126`) não declara `overflow`, tem `min-width: 0` e é coluna flex; o rodapé é o último filho do `section`. Os `overflow: hidden` do arquivo são de `.pregao-leitura`, `.medidor`, do cabeçalho e de `.heatmap-ativo`, nenhum no caminho do rodapé.

O único acréscimo possível seria um teste de guarda (razão de contraste de `--texto-3` e tamanho do `.rodape`), sem mudança de tela. Isso é saúde técnica, não experiência: se o Especificador quiser a guarda, ela entra numa spec de manutenção (`gaveta:` de saúde técnica), que também zera a cadência vencida, e não nesta.

Tamanho medido: `grep -rl rodape app tests` dá 5 arquivos de código e 2 de teste. Não há outra spec `ready` ou `draft` sobre o rodapé: 141 (presença do rodapé) e 147 (contraste dos tiles da Maré) estão `done` e são de outro assunto.
