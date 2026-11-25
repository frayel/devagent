---
id: 197
titulo: As frases do Consultor escrevem números no padrão brasileiro
status: ready
esforco: P
gaveta: experiência
aceite: tests/test_aceite_197.py
origem: Preço-alvo no padrão brasileiro
---

## Problema
"Em que preço esta recomendação muda, e quanto a regra já rendeu?" A spec 191 passou para o padrão brasileiro os números que o template de `/consultor` formata (preço, alvo, potencial, data), mas as **frases** que o Python monta e o template só repete ainda saem com ponto decimal, e uma delas erra o plural. Na mesma linha de uma recomendação o investidor lê `R$ 32,10` (spec 191) ao lado de `Fechamento acima da MM200 (R$ 30.00)`.

As frases e onde nascem:

- **gatilho** (`app/consultor/regras.py:91,101,111,121,136` e `app/consultor/sintese.py:302,315`): `Fechamento acima da MM200 (R$ 1234.50)`, `Recuo até a MM21 (R$ 38.40) ou IFR14 < 60`, `Primeiro fechamento em alta com VOL_REL >= 1.5`. Mostrada em `app/templates/consultor.html:207`.
- **motivo** (`regras.py:100,110,120,135`): `Preço < MM200 (45.68), MM21 < MM200, FR20 (-2.31%) < 0`. Mostrada no `title` da regra (`consultor.html:201`) e na coluna Motivo da tabela *Sem sinal* (`consultor.html:256`).
- **placar de um pregão passado** (`app/consultor/placar.py:74-75`, `_mensagem_do_placar`): `+5.0% contra o IBOV em 5 pregões` e, na borda da janela, `+17.1% contra o IBOV em 1 pregões`. Mostrada em `consultor.html:208`.
- **confiança da regra** (`app/consultor/calculador.py:135-136`): `... (mediana +3.2 p.p.)`. Mostrada em `consultor.html:208` e na coluna Confiança da tabela de regras (`consultor.html:75-95`).
- **limiares na tabela de regras** (`consultor.html:74` e `:89`): `VOL_REL >= 1.5` e `VOL_REL >= 1.0`, valores de `regras_limiares` impressos crus.

É o resto do item *Preço-alvo no padrão brasileiro* da Fila do backlog, que sai da fila com esta spec. A seção 7 do `PRODUTO.md` manda vírgula decimal e ponto de milhar.

## Comportamento esperado
Na página `/consultor` (dia atual e dias passados pelo seletor) e nos mesmos campos de texto de `/api/consultor` (`gatilho`, `motivo`, `mensagem_confianca`), as frases ficam assim:

| Frase | Hoje | Depois |
|---|---|---|
| gatilho com preço | `Fechamento acima da MM200 (R$ 1234.50)` | `Fechamento acima da MM200 (R$ 1.234,50)` |
| gatilho com preço e IFR | `Recuo até a MM21 (R$ 38.40) ou IFR14 < 60` | `Recuo até a MM21 (R$ 38,40) ou IFR14 < 60` |
| gatilho com VOL_REL | `... com VOL_REL >= 1.5` | `... com VOL_REL >= 1,5` |
| motivo | `Preço < MM200 (45.68), MM21 < MM200, FR20 (-2.31%) < 0` | `Preço < MM200 (45,68), MM21 < MM200, FR20 (-2,31%) < 0` |
| motivo com IFR | `... IFR14 (72.40) > 70` | `... IFR14 (72,40) > 70` |
| placar | `+5.0% contra o IBOV em 5 pregões` | `+5,0% contra o IBOV em 5 pregões` |
| placar, um pregão | `+17.1% contra o IBOV em 1 pregões` | `+17,1% contra o IBOV em 1 pregão` |
| confiança | `(mediana +3.2 p.p.)` | `(mediana +3,2 p.p.)` |
| tabela de regras | `VOL_REL >= 1.5` | `VOL_REL >= 1,5` |

As frases usam as funções que a spec 191 criou em `app/consultor/formato.py` (`reais`, `numero_br`, `percentual`); nenhuma formatação nova à mão com `replace`. Para a tabela de regras, `numero_br` é registrada como filtro do Jinja ao lado das outras três (`app/main.py:193-195`). Os números inteiros que as frases já escrevem (`IFR14 < 60`, `5 quedas seguidas`, `62% dos casos`, `n = 12`) não mudam.

## Fontes de dados
Nenhuma fonte nova. Unidades de cada valor que entra nas frases:

- `mm200`, `mm21`: `float` em **reais** (média de fechamentos, `calcular_mm`).
- `fr20`: `float` já em **pontos percentuais** (`calcular_fr20` multiplica por 100: `-2.31` é −2,31%). Não multiplicar de novo.
- `ifr14`: `float` de 0 a 100.
- `R1_GATILHO_VOL = 1.5`, `R4_GATILHO_VOL = 1.0`: razão de volume, sem unidade.
- `excesso` do placar (`_calcular_excesso`): **fração** (`0.05` é 5%).
- `excesso_mediano` da confiança (`get_consultor_confianca`): **fração** (`0.032` é 3,2 p.p.).

Plano B: valor ausente segue a regra das funções da 191 (`-`); nenhuma frase levanta exceção. Em `sintese.py`, quando `mm200` ou `mm21` falta, o código usa `0`, e `reais(0)` sai `-`: o gatilho fica `Fechamento acima da MM200 (-)` (hoje sai `R$ 0.00`, que é pior).

## Cálculos
Nenhuma conta nova; muda só a escrita. Exemplos de ponta a ponta:

**Gatilho R2** (`regras.py:101`): fechamentos com MM200 = `1234.5` (reais) → `reais(1234.5)` = `R$ 1.234,50` → `Fechamento acima da MM200 (R$ 1.234,50)`.

**Gatilho R4** (`regras.py:121`): MM200 = `45.0`, `R4_GATILHO_VOL = 1.0` → `reais(45.0)` = `R$ 45,00`, `numero_br(1.0, 1)` = `1,0` → `Fechamento acima da MM200 (R$ 45,00) com VOL_REL >= 1,0`.

**Motivo R2** (`regras.py:100`): MM200 = `45.678` (reais), FR20 = `-2.31` (p.p.) → `numero_br(45.678)` = `45,68`, `numero_br(-2.31)` = `-2,31` → `Preço < MM200 (45,68), MM21 < MM200, FR20 (-2,31%) < 0`. O sinal do FR20 continua o natural do número (sem `+` forçado): R2 só dispara com FR20 negativo e R5 só com positivo, e o texto ao lado (`< 0`, `> 0`) já diz o lado.

**Placar** (`placar.py:74-75`): preço na recomendação `30.00`, fechamento 5 pregões depois `33.00` (+10%); IBOV `120000` → `126000` (+5%). `excesso = 0.10 - 0.05 = 0.05` (fração) → `percentual(0.05)` = `+5,0%` → `+5,0% contra o IBOV em 5 pregões`. Com `offset = 1`: `... em 1 pregão` (singular só quando `offset == 1`). Excesso zero sai `+0,0%` (o `percentual` da 191 sempre põe sinal; hoje sai `0.0%`); negativo `-0.023` sai `-2,3%`.

**Confiança** (`calculador.py:136`): `excesso_mediano = 0.0321` (fração) → `× 100` = `3.21` → uma casa, com sinal: `+3,2` → `(mediana +3,2 p.p.)`. Negativo `-0.004` → `-0,4 p.p.`; zero → `+0,0 p.p.`. Fazer com `numero_br` sobre o valor e o sinal (`+` quando `>= 0`), não com `percentual` (a unidade é p.p., não %).

**Tabela de regras**: `{{ regras_limiares.R1_GATILHO_VOL | numero_br(1) }}` → `1,5`; `R4_GATILHO_VOL` → `1,0`.

## Critérios de aceite
- [ ] `avaliar_ativo` com uma série cuja MM200 passa de 1.000 devolve, para R2, `gatilho` com `R$ ` seguido de ponto de milhar e vírgula decimal (`R$ 1.234,50` no formato) e `motivo` sem nenhum número com ponto decimal (regex `\d\.\d` não casa em nenhum dos dois).
- [ ] O mesmo vale para R3, R4 e R5 (gatilho e motivo) e para os dois gatilhos de `sintese.py` (`Vender` com consenso de compra; `Sem sinal` que vira `No radar`).
- [ ] `R1` devolve `gatilho` que termina em `VOL_REL >= 1,5`.
- [ ] `_mensagem_do_placar` com os números do exemplo devolve `+5,0% contra o IBOV em 5 pregões`; com `offset = 1`, `... em 1 pregão`; com excesso `-0.023`, começa com `-2,3%`.
- [ ] A confiança de uma regra com `n = 120`, 75 acertos e `excesso_mediano = 0.0321` termina em `(mediana +3,2 p.p.).`
- [ ] A página `/consultor`, montada com um dublê de `calcular_consultor` no molde de `tests/test_aceite_191.py`, não contém `VOL_REL >= 1.5` nem `VOL_REL >= 1.0`, e contém `VOL_REL >= 1,5`.
- [ ] As asserções de texto que hoje fixam o formato antigo passam a fixar o novo: `tests/test_aceite_131.py:82` e `tests/test_aceite_193.py:21,147` (`+5,0% contra o IBOV em 5 pregões`, `+17,1% contra o IBOV em 1 pregão`). É a mudança de comportamento pedida aqui, não afrouxamento de teste.
- [ ] `tests/test_aceite_197.py` usa `exigir_spec_done("197")` e roda sem internet.

## Invariantes de produção
- Em `/consultor` (hoje), nenhum texto casa com `R\$ \d+\.\d{2}\b` (preço com ponto decimal) e nenhum contém ` 1 pregões`.
- Em `/api/consultor`, os campos `gatilho` e `motivo` das recomendações do dia não contêm número com ponto decimal (`\d\.\d`).
- O valor dentro de `(R$ ...)` do gatilho de uma recomendação R2, R4 ou R5, lido de volta como número, fica a no máximo 1% da MM200 de 200 fechamentos do mesmo ticker numa fonte independente (a vírgula não pode ter trocado a escala).

## Fora do escopo
- **Gatilhos já gravados** em `consultor_recomendacoes.gatilho` não são migrados: o `/consultor?data=` de um pregão anterior ao merge mostra o texto como foi gravado. Decisão conservadora (sem mudar dado histórico); as linhas novas já nascem no formato certo. Se a mistura incomodar, uma spec própria decide entre migrar o texto ou gravar os números e montar a frase na leitura.
- O formatador único para o site inteiro (item 24 da Fila): esta spec só usa o módulo do Consultor.
- Mudar o conteúdo das frases (o que dizem), as regras, os limiares ou o cálculo do placar e da confiança.
- Outros números de `app/` com `:.2f` fora do Consultor (37 f-strings com casas fixas em `app/`, medido em 25/11).
