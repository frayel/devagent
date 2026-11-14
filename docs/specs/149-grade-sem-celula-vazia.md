---
id: 149
titulo: A grade não deixa célula vazia entre os painéis macro
status: done
esforco: P
gaveta: experiência
aceite: tests/test_aceite_149.py
brief: P2-3
revisada: 2026-11-14
---

## Problema
O usuário perguntou: "por que sobra um buraco na grade ao lado da Concentração Setorial?"

Em 05/11/2026 foi observado um vazio ao lado do Fator Peso Pesado. Observação histórica; o diagnóstico abaixo é o da `main` de 14/11/2026.

Na visão geral (aba inicial), `app/static/ui.js` esconde no carregamento todo `.painel` que tem `sentimento-risco`, `rankings` ou `alertas` e não tem `visao-geral`. Dispersão e Índice de Coesão têm só `sentimento-risco`: não aparecem na visão geral e não ocupam célula ali. A sequência visível, em `app/templates/index.html`, com todos os dados presentes:

| Linha (12 colunas) | Painéis e spans | Soma |
|---|---|---|
| 1 | Ibovespa hoje 8 · Maré do mercado 4 | 12 |
| 2 | Clima Global 6 · Motores do Índice 6 (Motores vira 12 sem o Clima, `motores_span`) | 12 |
| 3 | Fator Peso Pesado 4 · Concentração Setorial 4 · **vazio 4** | 8 |
| 4 | Pressão Vendedora 12 | 12 |
| 5 | Concentração de Ganhos 12 | 12 |

Sem dado da Concentração Setorial, ela recebe `escondido` (`display: none !important` em `app/static/tema.css`, não reserva célula) e a linha 3 fica com o Fator Peso Pesado sozinho: **vazio 8**, o tamanho da observação de 05/11. O Fator Peso Pesado não tem `escondido` condicional, então aparece sempre. O buraco vem da soma dos spans, não de um painel faltando.

O guia (`docs/DESIGN.md` seção 3): em ≥ 1200px a grade tem 12 colunas; de 768 a 1199px, 6 colunas, com `span-4` na metade da linha e `span-6` ou mais na linha inteira; abaixo de 768px, uma coluna.

## Comportamento esperado
Na ordem da visão geral, os painéis visíveis empacotam sem resto, com e sem a Concentração Setorial:

- ≥ 1200px: cada linha soma 12. Um `span-12` não começa com colunas sobrando na linha anterior.
- 768 a 1199px, do Fator Peso Pesado em diante: a mesma regra em 6 colunas, com o mapeamento de `tema.css` (`span-3` e `span-4` valem 3; `span-6`, `span-8` e `span-12` valem 6).
- < 768px: uma coluna, sem célula ao lado.

A correção muda `span` de painéis que já existem, ou a ordem entre vizinhos já existentes, e pode condicionar o span ao dado presente, como o template já faz com `motores_span`. Não se cria indicador para preencher o oco. Composição que passa nas duas larguras, entre outras: Fator Peso Pesado e Concentração Setorial em dois `span-6`, com o Fator em `span-12` quando a Concentração está escondida. Fator 4 com Concentração 8 fecha as 12 colunas mas deixa 3 vazias em 6 colunas (ver *Cálculos*). O teste trava o empacotamento, não uma composição.

Painel com `escondido`, ou escondido pelas abas (regra do `ui.js` acima), não entra na conta, porque não ocupa célula.

## Fontes de dados
Nenhuma.

## Cálculos
O empacotador do teste percorre, na ordem do HTML, os filhos da `.grade` com classe `span-N` que estão visíveis na visão geral: sem `escondido` e, se forem `.painel`, com `visao-geral` ou sem nenhuma das classes `sentimento-risco`, `rankings`, `alertas`. Para cada um, se o span não cabe no que resta da linha, a linha fecha; o teste falha se ela fechou com resto maior que zero. No fim, a última linha também tem de fechar em 0.

Exemplo de ponta a ponta, `main` de 14/11, 12 colunas, todos os dados presentes: Ibovespa 8 (resta 4) → Maré 4 (resta 0, linha fecha) → Clima 6 (resta 6) → Motores 6 (resta 0) → Dispersão e Coesão ignoradas (só `sentimento-risco`) → Fator Peso Pesado 4 (resta 8) → Concentração Setorial 4 (resta 4) → Pressão Vendedora 12 não cabe em 4: a linha fecha com resto 4 e o teste falha. Depois da correção com Fator 4 e Concentração 8: Fator 4 (resta 8) → Concentração 8 (resta 0) → Pressão 12 (resta 0) → Ganhos 12 (resta 0): passa.

Mesmo exemplo em 6 colunas, do Fator em diante, com a correção: Fator 4→3 (resta 3) → Concentração 8→6 não cabe em 3: resto 3, falha. Por isso a composição 4 + 8 não basta sozinha nas duas larguras; 6 + 6 (vale 6 + 6 em 6 colunas, uma linha cada) passa nas duas.

## Critérios de aceite
- [ ] No HTML renderizado da home com todos os painéis macro presentes, o empacotador de 12 colunas (seção *Cálculos*) fecha toda linha em 12, inclusive a linha do Fator Peso Pesado com a Concentração Setorial.
- [ ] Com a Concentração Setorial em `escondido` (sem dado), o empacotador não conta o span dela e mesmo assim fecha toda linha em 12.
- [ ] Nos dois casos acima, o empacotador de 6 colunas, a partir do Fator Peso Pesado, fecha toda linha em 6.
- [ ] O empacotador ignora Dispersão e Índice de Coesão na visão geral (só `sentimento-risco`); um teste unitário do empacotador com a sequência da `main` de 14/11 (exemplo de *Cálculos*) falha com resto 4.
- [ ] O teste falha se aparecer na visão geral um painel cujo título não existia no template antes desta spec. A lista de títulos permitidos é a do próprio teste, copiada do template na data da implementação, mais nada.
- [ ] `tests/test_aceite_149.py` usa `exigir_spec_done("149")` e não abre rede.

## Invariantes de produção
- Na visão geral em 1440px não há célula vazia de grade entre o Fator Peso Pesado e os painéis que o seguem, com ou sem a Concentração Setorial.
- Em 1000px, do Fator Peso Pesado em diante, também não.
- A página em 390px não ganha rolagem horizontal por causa dessa rearrumação.

## Fora do escopo
- Redesign da grade ou novo painel.
- Mudar o que a Concentração Setorial calcula (spec 025).
- A aba de alertas e os radares vazios (spec 150).
- A aba Sentimento & Risco, onde Dispersão (4) e Coesão (4) deixam 4 colunas na linha; fica para outra spec.
- A linha 1 em 768 a 1199px: Ibovespa (8→6) ocupa a linha e Maré (3) fica ao lado de 3 colunas vazias, porque Clima (6) não cabe. Resolver exige mexer no topo da página; fica para outra spec.

## Plano de validação
`pytest -q tests/test_aceite_149.py` sem internet. O PR de implementação que mexer no template roda `make telas` e olha a visão geral em 1440×900 e em 390px. Esta rodada não produz a imagem.

## Revisão
14/11/2026. O diagnóstico original dizia que Dispersão, Índice de Coesão e Fator Peso Pesado fechavam uma linha na visão geral e sobravam 8 colunas ao lado da Concentração Setorial. Na `main`, Dispersão e Coesão têm só `sentimento-risco` e o `ui.js` os esconde na visão geral; o vazio é de 4 colunas com a Concentração presente e de 8 sem ela. Um teste escrito pelo texto antigo contaria painéis invisíveis e passaria ou falharia pelo motivo errado. Alterado: diagnóstico com a sequência real, regra de visibilidade das abas no empacotador, exemplo numérico de ponta a ponta nas duas larguras, critério para o caso sem Concentração Setorial (o Fator aparece sempre), escopo das 6 colunas limitado do Fator em diante e os dois vazios fora desta spec registrados em *Fora do escopo*. Tamanho: `grep -rl 'Concentração Setorial' app tests` dá 1 arquivo (`app/templates/index.html`); a implementação mexe nele e no teste novo. Nada no código já faz o que a spec pede (o vazio existe na `main`). Não há outra spec `ready` ou `draft` do mesmo tema (`grep -il 'célula vazia\|buraco\|empacot' docs/specs`).
