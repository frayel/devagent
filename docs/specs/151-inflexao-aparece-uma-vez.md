---
id: 151
titulo: A inflexão aparece uma vez só
status: ready
esforco: P
gaveta: experiência
aceite: tests/test_aceite_151.py
brief: P2-5
depende_de: 032, 150
---

## Problema
O usuário perguntou: "Inflexão de Tendência e Radar de Inflexão são o mesmo sinal duas vezes?"

Os dois blocos estão em `app/templates/index.html` e leem o mesmo `radar_inflexao`. O coletor (`app/collectors/radar_inflexao.py`) pede `spark` `range=1mo&interval=1d`, exige 16 fechamentos e calcula:

- `retorno_acumulado = (fechamento[-2] − fechamento[-16]) / fechamento[-16] × 100`
- `variacao_hoje = (fechamento[-1] − fechamento[-2]) / fechamento[-2] × 100`

Entra na lista quem tem acumulado `< −5` e hoje `> 2`. A lista fica com no máximo cinco nomes, do acumulado mais negativo para o menos negativo. O card "Inflexão de Tendência" (aba rankings) mostra só a variação de hoje e, vazio, a frase "Nenhuma ação com inflexão no momento." O card "Radar de Inflexão" (aba alertas) mostra a queda acumulada e o hoje, e recebe `escondido` quando não há alerta. O ⓘ do primeiro cita os cortes `>5%` em 15 dias e `> 2%` hoje; o do segundo fala em "caíram muito" e "subindo forte", sem os números.

Não há segundo cálculo. A diferença útil que a tela perde no rankings é a coluna da queda, que o payload já traz.

## Comportamento esperado
Um único painel, na aba alertas, com as duas colunas: queda acumulada (`retorno_acumulado`) e variação de hoje. O ⓘ publica os cortes `−5%` e `+2%`, a janela de 16 fechamentos e a fonte. Os cortes não mudam.

O bloco "Inflexão de Tendência" sai do template. Quem estava só nele passa a ver queda e hoje no card que fica. Lista vazia obedece à spec 150 (seção "Sem alertas", não um segundo "Nenhuma inflexão"). Lista com nomes aparece uma vez. Snapshot: uma chave `radar_inflexao`, não duas.

## Fontes de dados
O coletor atual. Plano B: falha da coleta (`successful_fetches == 0`, já devolvido como `False`) deixa o estado indisponível da spec 150, não uma lista vazia forjada.

## Cálculos
Os do coletor, sem ajuste de limiar. Proveniência no ⓘ: os dois limiares, o índice das barras (`−1`, `−2`, `−16`) e o teto de cinco nomes.

## Critérios de aceite
- [ ] Fixture com um nome (`retorno_acumulado −8`, `variacao_hoje +3`): o HTML contém esse ticker uma vez, com as duas colunas, e não contém o título "Inflexão de Tendência".
- [ ] O ⓘ desse painel contém `5` e `2` referindo-se aos cortes, e o nome da fonte.
- [ ] Lista vazia: não há card com "Nenhuma ação com inflexão no momento." nem com "Nenhuma inflexão detectada hoje." A ausência fica a cargo da seção da spec 150.
- [ ] Coleta que devolve `False`: estado indisponível, distinto da lista vazia.
- [ ] `tests/test_aceite_151.py` usa `exigir_spec_done("151")` e não abre rede. Os testes da spec 032 que procuram o sinal continuam verdes, apontando para o único card.

## Invariantes de produção
- A home não tem dois títulos de inflexão.
- Cada nome em `paineis.radar_inflexao` satisfaz acumulado `< −5` e hoje `> 2`, ou a lista está vazia.
- A página que lista o nome também mostra os dois números.

## Fora do escopo
- Mudar os cortes, a janela de 16 barras ou o teto de cinco.
- Criar uma terceira definição de reversão.
- Reabrir a spec 032, que descreveu o sinal; esta só unifica a apresentação.

## Plano de validação
`pytest -q tests/test_aceite_151.py` sem internet, mais o teste já existente do radar de inflexão se o nome do arquivo continuar o da spec 032. O PR de implementação olha as abas Rankings e Alertas no mesmo pregão e mostra o sinal uma vez. Sem captura nesta rodada.
