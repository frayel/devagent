---
id: 149
titulo: A grade não deixa célula vazia entre os painéis macro
status: ready
esforco: P
gaveta: experiência
aceite: tests/test_aceite_149.py
brief: P2-3
---

## Problema
O usuário perguntou: "por que sobra um buraco na grade ao lado da Concentração Setorial?"

Em 05/11/2026 foi observado um vazio entre o Fator Peso Pesado e a Concentração Setorial. Observação histórica. No template atual (`app/templates/index.html`), Dispersão, Índice de Coesão e Fator Peso Pesado são `span-4` e fecham uma linha de 12 colunas. O painel seguinte, Concentração Setorial, é `span-4`. O próximo, Pressão Vendedora, é `span-12` e desce para a linha de baixo. Sobram 8 colunas ao lado da Concentração Setorial. `.escondido` é `display: none !important` (`app/static/tema.css`) e não reserva célula. O buraco vem da soma dos spans, não de um painel faltando.

O guia (`docs/DESIGN.md` seção 3): em ≥ 1200px a grade tem 12 colunas; de 768 a 1199px, 6 colunas, com `span-4` na metade da linha e `span-6` ou mais na linha inteira; abaixo de 768px, uma coluna.

## Comportamento esperado
Na ordem da visão geral, os painéis visíveis empacotam sem resto:

- ≥ 1200px: cada linha soma 12. Um `span-12` não começa com colunas sobrando na linha anterior.
- 768 a 1199px: a mesma regra em 6 colunas, com o mapeamento do guia (`span-4` vale 3, `span-6` e acima valem 6).
- < 768px: uma coluna, sem célula ao lado.

A correção muda `span` de painéis que já existem, ou a ordem entre vizinhos já existentes. Não se cria indicador para preencher o oco. Composição aceitável, entre outras: Concentração Setorial na mesma linha de outros `span-4` já presentes; Pressão Vendedora e Concentração de Ganhos em dois `span-6`; ou Concentração Setorial em `span-12`. O teste trava o empacotamento, não uma dessas três.

Painel com `escondido` na visão geral não entra na conta, porque não ocupa célula.

## Fontes de dados
Nenhuma.

## Cálculos
Não há. O empacotador do teste percorre os `span-N` visíveis e falha quando uma quebra de linha deixa resto maior que zero.

## Critérios de aceite
- [ ] No HTML da home com todos os painéis macro presentes, o empacotador de 12 colunas termina cada linha em 12, inclusive a região que hoje deixa 8 colunas depois do `span-4` da Concentração Setorial.
- [ ] O mesmo HTML, mapeado para 6 colunas, não deixa meia linha vazia.
- [ ] O teste falha se aparecer um painel cujo título não existia no template antes desta spec. A lista de títulos permitidos é a do próprio teste, copiada do template na data da implementação, mais nada.
- [ ] Com a Concentração Setorial em `escondido`, o empacotador não conta o span dela.
- [ ] `tests/test_aceite_149.py` usa `exigir_spec_done("149")` e não abre rede.

## Invariantes de produção
- Na visão geral em 1440px não há célula vazia de grade entre o Fator Peso Pesado e os painéis que o seguem.
- A página em 390px não ganha rolagem horizontal por causa dessa rearrumação.

## Fora do escopo
- Redesign da grade ou novo painel.
- Mudar o que a Concentração Setorial calcula (spec 025).
- A aba de alertas e os radares vazios (spec 150).

## Plano de validação
`pytest -q tests/test_aceite_149.py` sem internet. O PR de implementação que mexer no template roda `make telas` e olha a visão geral em 1440×900 e em 390px. Esta rodada não produz a imagem.
