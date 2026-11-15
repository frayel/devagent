---
id: 151
titulo: A inflexão aparece uma vez só
status: done
esforco: P
gaveta: experiência
aceite: tests/test_aceite_151.py
brief: P2-5
depende_de: 032, 150
revisada: 2026-11-15
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

O bloco "Inflexão de Tendência" sai do template. Quem estava só nele passa a ver queda e hoje no card que fica. Lista vazia obedece à spec 150 (seção "Sem alertas", não um segundo "Nenhuma inflexão"). Lista com nomes aparece uma vez. O endpoint `snapshot()` de `app/main.py` já tem uma única chave `paineis.radar_inflexao`, e continua assim: a duplicata é só do template.

## Fontes de dados
O coletor atual (Yahoo `spark`, com `fonte` gravada por `mt5.fonte_efetiva("yfinance")`). Plano B: falha da coleta (`successful_fetches == 0`, devolvido como `False`) não grava snapshot, e por isso não forja lista vazia. O template vê o que a spec 150 já trata: sem nenhum snapshot (`radar_inflexao` é `None`), o card diz "indisponível" (ou "sem registro" em data histórica); com o último snapshot velho, o nome entra na seção "Sem alertas" como "desatualizado".

## Cálculos
Os do coletor, sem ajuste de limiar. Proveniência no ⓘ: os dois limiares, o índice das barras (`−1`, `−2`, `−16`) e o teto de cinco nomes. O acumulado vai do 16º fechamento antes do último até o penúltimo (14 pregões); o texto atual "15 dias" do card que sai não é copiado.

### Exemplo de ponta a ponta
O `spark` entrega `close` em reais por ação, um valor por pregão. Para um ticker com 21 fechamentos válidos, em que `close[-16] = 40,00`, `close[-2] = 36,00` e `close[-1] = 37,08`:

- `retorno_acumulado = (36,00 − 40,00) / 40,00 × 100 = −10,00` (já em percentual, não fração);
- `variacao_hoje = (37,08 − 36,00) / 36,00 × 100 = 3,00`;
- `−10,00 < −5` e `3,00 > 2`: entra. O payload grava `{"ticker": "XXXX3", "retorno_acumulado": -10.0, "variacao_hoje": 3.0}` (arredondado a duas casas);
- o card mostra `XXXX3 · -10,00% · 3,00%`, no formato `%.2f%%` com vírgula que o Radar de Inflexão já usa.

Contraexemplo: `close[-2] = 38,20` dá acumulado `−4,50`, que não passa do corte, e o ticker fica fora mesmo com hoje de `+3%`. Ticker com menos de 16 fechamentos válidos é ignorado.

## Critérios de aceite
- [ ] Fixture com um nome (`retorno_acumulado −8`, `variacao_hoje +3`): o HTML contém esse ticker uma vez, com as duas colunas, e não contém o título "Inflexão de Tendência".
- [ ] O texto do ⓘ desse painel contém `5%` e `2%` (os cortes) e `16` (a janela), e o painel mostra a `fonte` do snapshot.
- [ ] Lista vazia: não há card com "Nenhuma ação com inflexão no momento." nem com "Nenhuma inflexão detectada hoje." A ausência fica a cargo da seção da spec 150.
- [ ] Sem snapshot (`radar_inflexao` é `None`): o HTML diz "indisponível" e não contém frase de lista vazia; o ticker não aparece e o nome do radar não está entre os sem alerta da seção da spec 150.
- [ ] `tests/test_aceite_151.py` usa `exigir_spec_done("151")` e não abre rede. `tests/test_radar_inflexao.py` (spec 032, coletor e `snapshot()`) continua verde sem alteração.

## Invariantes de produção
- A home não tem dois títulos de inflexão.
- Cada nome em `paineis.radar_inflexao` satisfaz acumulado `< −5` e hoje `> 2`, ou a lista está vazia.
- A página que lista o nome também mostra os dois números.

## Fora do escopo
- Mudar os cortes, a janela de 16 barras ou o teto de cinco.
- Criar uma terceira definição de reversão.
- Reabrir a spec 032, que descreveu o sinal; esta só unifica a apresentação.

## Revisão
2026-11-15. Tamanho: 1 arquivo de código (`app/templates/index.html`, o único com "Inflexão de Tendência") e 0 de teste a alterar; cabe numa sessão. Ainda não feito na `main`: os dois cards estão nas linhas 363 e 989. Sem duplicata: a 032 descreveu o sinal e a 150 tratou só os vazios, ambas `done`. Ajustes: exemplo numérico de ponta a ponta; o plano B dizia que a coleta com `False` gera "indisponível", mas ela não grava nada e o template vê o último snapshot (ou `None`), então o critério passou a ser o `None`; a chave única do `snapshot()` já existe e virou invariante, não mudança; o critério do ⓘ ficou com strings testáveis.

## Plano de validação
`pytest -q tests/test_aceite_151.py` sem internet, mais o teste já existente do radar de inflexão se o nome do arquivo continuar o da spec 032. O PR de implementação olha as abas Rankings e Alertas no mesmo pregão e mostra o sinal uma vez. Sem captura nesta rodada.
