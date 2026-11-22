---
id: 191
titulo: O Consultor escreve preços, potenciais e datas no padrão brasileiro
status: ready
esforco: P
gaveta: experiência
aceite: tests/test_aceite_191.py
revisada: 2026-11-22
origem: Preço-alvo no padrão brasileiro
---

## Problema
"Quanto a casa espera e quando ela disse isso?" Na página `/consultor`, o investidor lê o preço-alvo, o fechamento e o potencial em formatos que não são os da seção 7 do `PRODUTO.md` (`183.476,86`, `+0,78%`, `dd/mm/aaaa`):

- `app/templates/consultor.html:111`: o resumo de cada ativo em *Opiniões Recentes* escreve `R$ 45.00` e `R$ 38.00 a R$ 45.50` (`"%.2f"|format`, ponto decimal).
- `consultor.html:133`: a coluna **Preço-Alvo** do detalhe mostra o valor cru do banco, que conforme a época da extração é `45.0`, `52.5` ou `R$ 45,00`; duas linhas da mesma tabela saem em formatos diferentes.
- `consultor.html:136`: a coluna **Data** mostra `(op.data_materia | string)[:10]`, ou seja, `2026-11-16` (ISO) e o dia em **UTC**: uma matéria das 22h30 de Brasília de 15/11 (01:30 UTC de 16/11) aparece como do dia 16.
- `consultor.html:198` e `:254`: o fechamento de cada recomendação e da tabela *Sem sinal* sai `R$ 32.10`.
- `consultor.html:218–220`: o alvo mediano do consenso sai `R$ 45.00` e o potencial `(+12.3%)`.

Visto nas capturas de `make telas` de 21/11 (item 23 da Fila do backlog). Outras partes da mesma página já seguem a convenção (`ate_o_alvo` e `metodo_do_alvo` em `app/main.py:156–177`, a frase do consenso do Yahoo em `app/consultor/consenso_yahoo.py`), então a página mistura `R$ 45,00` e `R$ 45.00` lado a lado.

## Comportamento esperado
Na página `/consultor` (dia atual e dias passados pelo seletor), todo preço em reais, todo potencial em percentual e a data de cada opinião aparecem no padrão brasileiro. Nada muda em `/api/consultor` (JSON continua com números) nem no que está gravado no banco.

| Lugar (`consultor.html`) | Hoje | Depois |
|---|---|---|
| resumo do ativo, Preço-alvo (linha 111) | `R$ 38.00 a R$ 45.50` | `R$ 38,00 a R$ 45,50` |
| detalhe, coluna Preço-Alvo (133) | `45.0` / `R$ 45,00` / `52.5` | `R$ 45,00` / `R$ 45,00` / `R$ 52,50` |
| detalhe, coluna Data (136) | `2026-11-16` (dia UTC) | `15/11/2026` (dia em Brasília) |
| recomendações (Comprar, Vender, Aguardar, No radar), fechamento (198) | `R$ 1234.50` | `R$ 1.234,50` |
| consenso, alvo e potencial (218–220) | `Alvo: R$ 45.00 (+12.3%)` | `Alvo: R$ 45,00 (+12,3%)` |
| Sem sinal, Preço (254) | `R$ 32.10` | `R$ 32,10` |

Um módulo só guarda as três funções, cada uma registrada como filtro do Jinja (`reais`, `percentual`, `data_brasilia`) e usadas nos seis lugares. Sugestão de casa: `app/consultor/formato.py` (o `app/main.py` já tem 2.400 linhas; item 6 da Fila). Os filtros `_ate_o_alvo` e `_metodo_do_alvo` podem passar a usar a função nova, sem mudar o texto que produzem.

## Fontes de dados
Nenhuma fonte nova. Os valores já chegam ao template:

- `linha.alvo_min`, `linha.alvo_max`: `float` em reais (de `agrupar_por_ativo`, `app/consultor/sintese.py`).
- `op.preco_alvo`: o que o Gemini escreveu e foi gravado em `consultor_opinioes.preco_alvo`, texto ou número (`"R$ 45,00"`, `"52.5"`, `45.0`). Lido por `ler_preco_alvo` (`app/consultor/armazenamento.py:66`), que já entende os três jeitos.
- `op.data_materia`: texto ISO 8601 UTC (desde a spec 158) ou `datetime`. Lido por `ler_data` (`armazenamento.py:28`), que devolve UTC; o fuso de Brasília é `FUSO` de `app/services/carimbo.py`.
- `item.fechamento`, `item.consenso.preco_alvo_mediano`: `float` em reais. `item.consenso.potencial`: **fração** (`0.123` é 12,3%), calculada em `app/consultor/calculador.py:193`.

Plano B: valor ausente ou ilegível sai `-`, como hoje; nenhum filtro levanta exceção.

## Cálculos
**`reais(valor)`**
1. `valor` é `None`, `bool`, vazio ou `ler_preco_alvo(valor)` devolve `None` → `-`.
2. Senão, `x = ler_preco_alvo(valor)` (aceita `float`, `int` e texto; para `float` positivo devolve o próprio número).
3. Duas casas, milhar com ponto, decimal com vírgula: `f"{x:,.2f}"` e troca `,`↔`.` (o mesmo de `app/services/highlights.py:14`).
4. Prefixo `R$ ` (com espaço comum).

Como `ler_preco_alvo` devolve `None` para número `<= 0`, um fechamento `0.0` também sai `-` (hoje sai `R$ 0.00`); fechamento zero não é preço válido.

Exemplos, do dado bruto ao exibido:

| Bruto (unidade: reais) | Passo 2 | Passo 3 | Exibido |
|---|---|---|---|
| `45.0` (float) | 45.0 | `45,00` | `R$ 45,00` |
| `"R$ 45,00"` (texto, vírgula) | 45.0 | `45,00` | `R$ 45,00` |
| `"52.5"` (texto, ponto decimal) | 52.5 | `52,50` | `R$ 52,50` |
| `"R$ 1.234,50"` | 1234.5 | `1.234,50` | `R$ 1.234,50` |
| `1234.5` (float) | 1234.5 | `1.234,50` | `R$ 1.234,50` |
| `None` / `""` / `"sem alvo"` | - | - | `-` |

Atenção ao resumo do ativo: hoje o template escreve `R$ ` antes do número; com o filtro, o `R$` vem dele e sai do template (senão a página mostraria `R$ R$ 45,00`).

**`percentual(fracao, casas=1)`**: entrada em **fração**. `None` → `-`. Senão `p = fracao * 100`, `f"{p:+.{casas}f}"` com `.`→`,` e `%` no fim. Zero sai `+0,0%`, como o `:+` do Python faz e como o `ate_o_alvo` da spec 190 já faz (hoje o template escreve `(0.0%)`, sem sinal; a mudança é intencional).

| Bruto (fração) | `× 100` | Exibido |
|---|---|---|
| `0.12345` | 12.345 | `+12,3%` |
| `-0.05` | -5.0 | `-5,0%` |
| `0.0` | 0.0 | `+0,0%` |

No consenso, o template hoje escreve o `+` à mão (`{% if potencial > 0 %}+{% endif %}`); com o filtro, esse trecho sai.

**`data_brasilia(momento)`**: `ler_data(momento)`; `None` → `-`; senão `.astimezone(FUSO).strftime("%d/%m/%Y")`.

| Bruto (`data_materia`, UTC) | Em Brasília (UTC−3) | Exibido |
|---|---|---|
| `"2026-11-15T23:30:00+00:00"` | 15/11 20:30 | `15/11/2026` |
| `"2026-11-16T01:30:00+00:00"` | 15/11 22:30 | `15/11/2026` (hoje sai `2026-11-16`) |
| `"2026-11-16"` (sem hora, tratado como 00:00 UTC) | 15/11 21:00 | `15/11/2026` |
| `None` / `"lixo"` | - | `-` |

O terceiro caso é o comportamento de `ler_data` (data sem fuso vale UTC) e é o mesmo que o filtro `dia_brasilia` da spec 165 já produz no resumo do ativo; os dois lugares da página concordam no dia.

## Critérios de aceite
`tests/test_aceite_191.py`, com `exigir_spec_done("191")`, sem rede (página montada com dublês de `calcular_consultor`, o molde de `tests/test_aceite_189.py` e `test_aceite_190.py`):

- [ ] `reais`: cada linha da tabela de exemplos de `reais` dá exatamente o exibido.
- [ ] `percentual`: `0.12345 → "+12,3%"`, `-0.05 → "-5,0%"`, `0.0 → "+0,0%"`, `None → "-"`.
- [ ] `data_brasilia`: cada linha da tabela de exemplos dá exatamente o exibido.
- [ ] Página `/consultor` com uma opinião de `preco_alvo = "52.5"` e outra de `45.0`, `data_materia = "2026-11-16T01:30:00+00:00"`, uma recomendação do grupo *Comprar* de fechamento `1234.5` com consenso de alvo mediano `45.0` e potencial `0.12345`, e um ativo *Sem sinal* de fechamento `32.1`: o HTML contém `R$ 52,50`, `R$ 45,00`, `15/11/2026`, `R$ 1.234,50`, `(+12,3%)` e `R$ 32,10`.
- [ ] No mesmo HTML, nenhum trecho casa `R\$ \d+\.\d{2}\b` (preço com ponto decimal), nem `R\$ R\$`, nem `2026-11-16` no corpo da tabela de opiniões. Os dublês usam `gatilho` e `motivo` sem `R$` (por exemplo `""`), porque esses textos ficam fora do escopo (ver abaixo) e continuariam com `R$ 30.00`.
- [ ] `tests/test_classes_com_estilo.py` e `tests/test_templates_safe.py` continuam verdes sem mudar expectativa (nenhuma classe nova; os filtros devolvem texto comum, escapado pelo Jinja).

## Invariantes de produção
- Em `/consultor`, nos seis lugares da tabela de *Comportamento esperado*, todo valor precedido de `R$` tem vírgula decimal e duas casas (`R$ 45,00`), e nenhum aparece como `R$ 45.00` ou `45.0` solto na coluna Preço-Alvo. Verificável lendo o HTML. A linha do gatilho de cada recomendação (`<small>` sob a regra) e o `title`/coluna de motivo **não** entram nesta invariante: continuam `R$ 30.00` até o item 23 do backlog.
- A coluna Data das opiniões só tem datas `dd/mm/aaaa`.
- O potencial do consenso tem vírgula decimal e sinal (`+12,3%`).
- `/api/consultor` continua com os mesmos campos e números de antes (comparar as chaves de um dia passado antes e depois do deploy).

## Fora do escopo
- **Textos gerados pelas regras.** `gatilho` e `motivo` (`app/consultor/regras.py:96–136` e `app/consultor/sintese.py:302,315`) são montados com `:.2f` e gravados em `consultor_recomendacoes.gatilho`; trocar o formato muda o que se grava e deixa o histórico misturado. Fica no item 23 do backlog, que pede decidir antes entre migrar o texto gravado ou guardar os números e montar a frase na leitura.
- As outras páginas: os templates têm 45 `replace('.', ',')` espalhados (e o Python de `app/`, mais 22), e o milhar quase nunca sai (`R$ 1234,56`). Um formatador único para o site inteiro é o item 25 da Fila do backlog, não desta spec.
- `/api/consultor`, `/api/snapshot` e o banco: nenhum número muda de tipo ou de valor.
- O resumo do ativo continua com `dd/mm` (filtro `dia_brasilia` da spec 165); só a coluna Data do detalhe ganha o ano.
