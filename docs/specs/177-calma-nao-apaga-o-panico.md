---
id: 177
titulo: A Calma não apaga o pânico de verdade
status: done
esforco: P
gaveta: experiência
aceite: tests/test_aceite_177.py
origem: nova
revisada: 2026-11-18
---

## Problema
Pergunta do dono do produto em 18/11/2026: por que a Calma aparece como ausente no nível Ondas da Maré?

Porque o cálculo jogou fora a maior queda do ano. Em 26/10/2026 o Ibovespa caiu 13,9% (de 205.083 para 176.608 pontos, Yahoo `^BVSP`). A queda foi do mercado, não da fonte: a mediana das 30 ações da cesta da Maré caiu 14,9% no mesmo pregão, e 27 das 30 caíram.

`volatilidades` (`app/services/mare.py:111`) descarta todo retorno diário com `|r| ≥ 0,12` como se fosse erro de dado. A janela da Calma exige 10 retornos válidos, então um descarte apaga a Calma por 10 pregões seguidos. Medido em 18/11 com os dados do Yahoo:

- a Calma ficou `None` de 26/10 a 09/11, os 10 pregões depois da queda;
- em Ondas (21 pregões, de 19/10 a 17/11), 10 dias ficaram sem Calma: presença de 52%, abaixo dos 75% da spec 174a, e o componente sai `ausente`;
- o índice desses dias foi calculado só com Fluxo e Volume, e Ondas mostrou 43 (Neutro).

O efeito é o inverso do que o card promete. A Calma mede a agitação das quedas, e o filtro a desliga justo na semana de maior agitação. Nem a spec 027 nem a 174 pedem esse corte: ele está no código sem regra escrita.

## Comportamento esperado
1. **Retorno grande confirmado pela cesta entra na conta.** Um retorno diário do Ibovespa com `|r| ≥ 0,12` só é descartado quando a cesta não confirma o movimento. Ele é mantido quando, no mesmo pregão:
   - pelo menos 20 ações da cesta (`MINIMO_ACOES`) têm retorno nesse pregão; e
   - a mediana dos retornos log dessas ações tem o mesmo sinal de `r` e `|mediana| ≥ |r| / 2`.
2. **Sem confirmação possível, o comportamento de hoje.** Quando a cesta não cobre o pregão (amostra pequena, ou pregão anterior ao `range=3mo` da leitura do dia), o retorno de `|r| ≥ 0,12` continua descartado. Retornos abaixo de 12% não mudam.
3. **O mesmo cálculo nos três níveis.** A regra vale dentro de `_Calculadora`, que serve à leitura do dia (Marolas), ao histórico longo (`app/collectors/mare_historico.py`, Ondas e Maré) e ao histórico de 21 pregões do coletor `mare`. Nenhuma fórmula nova de componente: só o filtro muda.
4. **Constantes nomeadas** no topo de `app/services/mare.py`, com comentário que cita esta spec e o 26/10/2026: o limiar (`0,12`) e a fração de confirmação (`0,5`).
5. **Método do card.** O texto do botão `i` é uma única string, no `painel("Maré do mercado", ...)` de `app/templates/componentes.html`. A frase entra logo depois de `então uma alta forte não reduz a calma.`: `Um dia de mais de 12% só fica de fora se as ações da cesta não acompanharam o movimento (erro provável da fonte).`

## Fontes de dados
Nenhuma nova. A confirmação usa as séries da cesta que `_Calculadora` já recebe (`self.acoes`). Plano B: item 2.

## Cálculos
- `r_t = ln(Ibov_t / Ibov_{t−1})`, como hoje.
- Mediana da cesta no pregão `t`: mediana de `ln(fech_t / fech_ant)` das ações válidas da amostra (`self.acoes`, depois de `_acoes_validas`) que têm o pregão `t` e algum pregão anterior. `fech_ant` é o último fechamento antes de `t`, a mesma regra de `_variacoes`.
- Alinhamento: `confirmacao[i]` é a mediana da cesta no pregão `self.dias_ibov[i]`; pregão do Ibovespa que não está em `self.sessoes`, ou com menos de `MINIMO_ACOES` ações com retorno, vale `None`. Com `amostra_ok` falso, toda a lista é `None` (item 2).
- Sugestão de interface, para não quebrar quem chama: `volatilidades(fechamentos, confirmacao=None)`, em que `confirmacao` é uma lista alinhada com os fechamentos, com a mediana da cesta em cada pregão ou `None`. Sem o argumento, o comportamento é o atual (os testes de `tests/test_mare.py` que chamam `volatilidades(fech)` não mudam).

**Exemplo de ponta a ponta (26/10/2026).** O Yahoo entrega o fechamento do `^BVSP` em pontos e o de cada ação em reais por ação (`chart.result[0].indicators.quote[0].close`).
1. Ibovespa: 23/10 = 205.083 pontos, 26/10 = 176.608 pontos. `r = ln(176.608 / 205.083) = ln(0,86116) = −0,1495`. `|r| = 0,1495 ≥ 0,12`: candidato a descarte.
2. Cesta: 30 ações válidas com o pregão de 26/10 (≥ 20, a amostra basta). A mediana dos retornos simples foi −14,9%; em log, a mediana é `ln(1 − 0,149) = −0,1613` (a mediana dos logs é o log da mediana, porque `ln` é crescente).
3. Confirmação: mesmo sinal (as duas negativas) e `|−0,1613| = 0,1613 ≥ |r| / 2 = 0,0747`. O retorno de −0,1495 fica na janela.
4. σ10 de 26/10: a janela tem os 10 retornos de 12/10 a 26/10; o −0,1495 domina a soma dos quadrados (`0,1495² = 0,02235`). Com os outros 9 retornos medidos, `σ10 = √(Σ min(r,0)² / 10) × √252 = 0,758` (anualizado, fração: 75,8% ao ano), contra 0,105 em 23/10.
5. Calma: 0,758 é maior que todos os 252 σ10 anteriores, então o percentil é 100 e `Calma = 100 − 100 = 0` (Pânico), o número que o card mostra.

Contraexemplo: com a mediana da cesta em −1% (`ln 0,99 = −0,0101`), `0,0101 < 0,0747`: o retorno é descartado e a Calma de 26/10 a 09/11 fica `None`, como hoje.

**Efeito medido em 18/11** (dados do Yahoo de 18/11/2024 a 17/11/2026, protótipo da regra acima):

| | Hoje | Com a regra |
|---|---|---|
| Calma de 26/10 a 04/11 | ausente | 0 (Pânico) |
| Calma de 05/11 a 09/11 | ausente | 0,4 a 1,2 |
| Calma de 17/11 (Marolas) | 44,4 | 46,6 |
| Ondas | 43 · Neutro, Calma ausente | 36 · Medo, Calma 21,1 |
| Maré (com o Ibovespa baixado) | 49, Calma 43,7 | 48, Calma 42,1 |

Em dois anos, só 26/10/2026 passou do limiar; a alta de 7,7% de 05/10/2026 está abaixo dele e não muda. A volatilidade de queda de 26/10 fica em 0,758 (anualizada), sete vezes a de 23/10 (0,105). Calma 0 nesses dias é o que a fórmula da 027 diz de um σ10 acima de todos os 252 anteriores.

## Critérios de aceite
- [ ] `tests/test_aceite_177.py`, com `exigir_spec_done("177")`, sem internet, com séries sintéticas:
  - **confirmado entra:** Ibovespa com uma queda de 14% no pregão `t` e 25 ações com mediana de −15% no mesmo pregão: `volatilidades(..., confirmacao)` não tem `None` nos 10 pregões a partir de `t` e o σ10 de `t` é maior que o de `t−1`; `_Calculadora(...).leitura(t, 1.0).componentes["calma"]` não é `None`;
  - **não confirmado sai:** mesma queda do Ibovespa com a mediana da cesta em −1%: os 10 pregões a partir de `t` ficam `None`, como hoje;
  - **sinal contrário sai:** Ibovespa −14% com a mediana em +8%: descartado;
  - **amostra pequena:** com 19 ações no pregão `t`, o retorno é descartado;
  - **sem confirmação, igual a hoje:** `volatilidades(fech)` sem o segundo argumento devolve exatamente o que devolve na `main` de 18/11 para as séries de `tests/test_mare.py`;
  - **Ondas volta a ter Calma:** com 21 leituras geradas por `mare_historico.calcular` a partir das séries sintéticas do primeiro caso, `mare.nivel(...)` não lista `calma` em `ausentes`;
  - **método:** o HTML de `GET /mare` contém a frase do item 5.
- [ ] Os testes atuais (`tests/test_mare.py`, `tests/test_aceite_174a.py`, `tests/test_aceite_174b.py`) continuam verdes sem mudar asserções.

## Invariantes de produção
- Para todo pregão `t` das `leituras` de `mare_historico` em que `|ln(Ibov_t / Ibov_{t−1})| ≥ 0,12` e a mediana da cesta tem o mesmo sinal e pelo menos metade do tamanho, a Calma de `t` e dos 9 pregões seguintes não é `null`.
- Enquanto 26/10/2026 estiver na janela de Ondas (até 21 pregões depois), `paineis.mare.niveis.ondas.ausentes` não contém `calma`, desde que o histórico tenha sido gravado com o Ibovespa (ver *Fora do escopo*).

## Fora do escopo
- **Histórico longo gravado sem o Ibovespa.** Em produção, em 18/11, a Calma também está ausente em Maré, embora o cálculo com o Ibovespa dê Calma em 242 de 252 dias. A suspeita, não confirmada sem os logs: `buscar_ibov` devolve `{}` em silêncio quando o Yahoo recusa o pedido feito depois dos 30 da cesta, e `mare_historico` grava assim mesmo. É bug, vai como issue separada: não gravar o snapshot sem Ibovespa suficiente e tentar de novo na rodada seguinte.
- Mudar o limiar de 12%, a janela de 10 retornos ou a exigência de 10 retornos válidos.
- Usar outra fonte para conferir o Ibovespa (B3, brapi, MT5).
- Recalcular snapshots `mare` já gravados: a leitura do dia se corrige na próxima coleta, e o histórico longo na próxima gravação diária.
