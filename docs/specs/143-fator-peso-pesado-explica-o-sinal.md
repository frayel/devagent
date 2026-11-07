---
id: 143
titulo: O fator peso pesado explica o sinal da conta
status: ready
esforco: M
gaveta: experiência
aceite: tests/test_aceite_143.py
brief: P1-2
depende_de: 046, 134
revisada: 2026-11-07
---

## Problema
O usuário perguntou: "−50,8% do movimento explicado pelas cinco maiores é metade a favor ou metade contra?"

Em 05/11/2026 o card mostrou −50,8%. Observação histórica, não diagnóstico. A spec 046 já definiu a conta e um teto de distorção em ±500%. O coletor (`app/collectors/fator_peso_pesado.py`) grava `(contrib_pts / ibov_var_pts) × 100`, corta em silêncio para o intervalo [−500, +500] e, se `|variação do índice| < 0,1%`, grava "Mercado lateral" com proporção 0. O template escreve o percentual com o sinal e a frase "do movimento do Ibovespa é explicado pelas 5 maiores ações", igual para positivo e negativo.

Razão de contribuição pode passar de 100% quando o resto do índice compensa as cinco, e o denominador perto de zero explode. Esta spec não corta a conta para 0–100%.

## Comportamento esperado
O card continua no mesmo lugar. O número é uma razão com sinal, em percentual, da soma das contribuições teóricas das cinco sobre a variação em pontos do Ibovespa.

- Sinal positivo: as cinco andaram no mesmo sentido do índice. A frase diz "no mesmo sentido".
- Sinal negativo: andaram no sentido oposto. A frase diz "no sentido oposto". Exemplo de aceite: índice +1.000 pontos e cinco nomes somando −508 pontos → `−50,8%` e a frase "no sentido oposto", com 50,8% do tamanho do movimento. Não se lê como "explicaram uma queda".
- Módulo acima de 100% permanece. A frase diz que o restante do índice compensou. Não há corte para 100.
- Módulo acima de 500%: vale o teto da spec 046. O snapshot guarda `proporcao_bruta` e `proporcao` limitada. O card mostra o valor limitado e a palavra "limitado". O corte deixa de ser silencioso. Não é um máximo de mercado; é o guarda já especificado.
- `|variação percentual do índice| < 0,1%`: "Mercado lateral", sem razão. Denominador zero não é publicado.
- Falta qualquer uma das cinco: não publica razão parcial. O card fica indisponível. O log cita o ticker e não cita segredo.

O ⓘ declara pesos aproximados e a soma 34% (VALE3 12, PETR4 8, ITUB4 7, PETR3 4, BBAS3 3), como a spec 046. A base do índice é a da spec 134.

## Fontes de dados
`chart` `range=1d` do `^BVSP` e dos cinco tickers, Yahoo, com o MT5 na frente se a coleta já o usa. Plano B: falha ou nome faltando → indisponível, último snapshot só se o carimbo for o dessa coleta completa.

## Cálculos
`contribuição_i = (variação_percentual_i × peso_i / 100) × fechamento_anterior_do_Ibovespa`, pesos na escala da spec 046.

`razão = soma(contribuição_i) / variação_em_pontos_do_Ibovespa × 100`.

Variação do índice em pontos = último − fechamento da sessão anterior (spec 134). Unidade exibida: percentual com sinal, uma casa, padrão brasileiro.

## Critérios de aceite
- [ ] Índice de 130.000 para 131.000 (+1.000 pontos). Cinco contribuições somando −508: o card contém `−50,8%` e "sentido oposto", e não contém "limitado".
- [ ] Soma das cinco = +1.500 pontos com o índice em +1.000: o card contém `+150,0%` (ou `+150%`) e a palavra de compensação. Não contém `100%` no lugar da razão.
- [ ] Razão bruta +800: snapshot tem `proporcao_bruta` 800 e `proporcao` 500, e o HTML contém "limitado".
- [ ] Variação do índice de +0,05%: HTML contém "Mercado lateral" e não contém um percentual de razão.
- [ ] PETR3 sem preço: `collect` não grava razão, o card fica indisponível e os outros quatro não aparecem como se fossem as cinco.
- [ ] `tests/test_aceite_143.py` usa `exigir_spec_done("143")` e não abre rede.

## Invariantes de produção
- O sinal publicado é o sinal de `soma das contribuições / variação do índice`.
- Nenhuma razão com módulo entre 100 e 500 aparece cortada em 100.
- Com `|variação do índice| < 0,1%`, o snapshot não traz razão diferente de zero.
- A soma dos cinco pesos usados é 34.

## Fora do escopo
- Pesos oficiais diários da B3 (já fora da spec 046).
- Trocar a cesta das cinco.
- Remover o teto de 500%. Ele fica visível, não some.
- Tratar −50,8% de 05/11/2026 como erro já explicado.

## Plano de validação
`pytest -q tests/test_aceite_143.py` sem internet. O PR de implementação mostra o card de manhã e de tarde com o ⓘ aberto o suficiente para ler o sinal, o peso e a base. Sem captura fictícia nesta rodada.
