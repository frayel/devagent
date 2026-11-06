---
id: 140
titulo: A manchete não chama de alta ampla um pregão com poucas ações em alta
status: ready
esforco: M
gaveta: experiência
aceite: tests/test_aceite_140.py
brief: P0-2
depende_de: 134, 135, 141
---

## Problema
O usuário perguntou: "se o Ibovespa sobe e quase todas as ações caem, por que a manchete fala em alta?"

Em 05/11/2026 a manchete convivia com Ibovespa em alta forte, motores negativos, dispersão observada de 7% (2 altas e 28 baixas), pressão vendedora e um texto de concentração falando em queda. É observação histórica, não o estado atual da produção. `app/services/manchete.py` hoje escolhe a frase só com o sinal do Ibovespa, `dispersion_pct > 50` e o estado de apetite a risco. Não lê os motores. Com o índice positivo e a dispersão em 7%, cai na frase "O mercado opera em alta, mas os indicadores internos mostram sinais mistos." A frase não cita a amostra e ainda chama o dia de alta.

A spec 022 continua valendo para o caso em que índice, maioria e apetite concordam. Esta spec acrescenta a regra única de humor quando eles não concordam.

## Comportamento esperado
A manchete e `paineis.manchete.humor` usam um único enum: `alta_ampla`, `baixa_ampla`, `misto`, `sem_direcao`, `indisponivel`. A frase visível é função desse enum. O sinal do índice não é invertido para combinar com a largura: índice em alta com poucas ações em alta é `misto`, e o texto diz as duas coisas.

Entradas, todas do mesmo pregão (a data de pregão é a da spec 141):

- Ibovespa: sinal, `revisao_variacao` (spec 134) e pregão.
- Dispersão: `up_count`, `down_count`, `total_count` de `app/services/highlights.py`.
- Motores: `variacao` de Financeiro, Commodities e Doméstico (`app/collectors/motores_indice.py`).

Ordem da regra:

1. Sem Ibovespa, ou variação indisponível: `indisponivel` e a frase já existente "Resumo do mercado indisponível no momento."
2. Pregão do Ibovespa, da dispersão ou dos motores diferentes entre si: `indisponivel` e a frase "Os painéis não estão no mesmo pregão; a leitura do dia fica suspensa." Nenhuma palavra de alta ou baixa ampla.
3. `revisao_variacao` verdadeiro: `misto`. O texto diz a direção do índice e que o movimento está em revisão. Não usa "otimismo generalizado", "pessimismo generalizado", "forte tomada de risco", "alta ampla" nem "queda generalizada".
4. `fracao_em_alta = up_count / total_count`. Abaixo de 20%, o humor não é `alta_ampla`. Acima de 80%, não é `baixa_ampla`. Com o índice positivo e `fracao_em_alta < 0,20`, o humor é `misto` e a frase traz o sinal do índice e as contagens (altas, baixas e total).
5. Conflito de motores: dos motores com número, dois ou mais têm sinal oposto ao do índice. O humor é `misto`, mesmo com dispersão alta. Motor ausente não entra na contagem e não recebe sinal inventado. A frase só precisa dizer que faltou motor quando o humor não for o da regra 6.
6. Sem conflito, sem revisão, índice positivo, `fracao_em_alta >= 0,50` e apetite "Tomando risco": permanece o caminho da spec 022, "Dia de otimismo generalizado com forte tomada de risco." O espelho de baixa também permanece.
7. Índice positivo ou negativo sem maioria e sem o conflito do item 5: `misto`, com as frases atuais de sinais mistos, mais as contagens da amostra.
8. Variação do índice igual a zero: `sem_direcao`.

Neutros (`change_percent == 0`) entram em `total_count` e não entram em `up_count` nem `down_count`, como o serviço já faz. A frase e a legenda da Dispersão mostram as três contagens. O gauge continua em `up_count / (up_count + down_count)`, e o ⓘ diz que o percentual do gauge exclui as sem variação. Ticker sem cotação não entra no denominador; o texto diz quantos faltaram quando `total_count` for menor que a cesta.

## Fontes de dados
Nenhuma fonte nova. A manchete lê o que o Ibovespa, os highlights e os motores já gravaram. Plano B: entrada ausente degrada para `indisponivel` ou para `misto` sem inventar o sinal que falta, e o resto da página segue.

## Cálculos
`fracao_em_alta = up_count / total_count` quando `total_count > 0`. Esse é o campo que `/api/snapshot` já publica em `paineis.altas_baixas.dispersao.proporcao_alta_pct` (`app/main.py`). O gauge da página usa outro denominador, `up_count / (up_count + down_count)`, em `app/services/highlights.py`. Os dois convivem: o corte de 20% usa `total_count`; o gauge não muda de fórmula. O corte de alta ampla é 20% de `fracao_em_alta`, não o `dispersion_pct > 50` sozinho. Sinal de motor: o campo `variacao` já é a média das variações do dia do grupo (`range=1d`). Amostra, janela e método ficam no ⓘ da manchete: cesta de highlights, pregão corrente contra o fechamento anterior, fração sobre `total_count`.

## Critérios de aceite
- [ ] Fixture Ibovespa `+1,00%`, `revisao_variacao` falso, `up_count=2`, `down_count=28`, `total_count=30`, três motores negativos, mesmo pregão: humor `misto`, a frase contém o sinal de alta do índice e as contagens `2` e `30`, e não contém "otimismo generalizado" nem "alta ampla".
- [ ] O mesmo fixture com `revisao_variacao` verdadeiro: humor `misto` e a frase contém "revisão".
- [ ] Ibovespa `+1,00%`, `up_count=20`, `down_count=8`, `total_count=30`, motores positivos, apetite "Tomando risco", sem revisão: humor `alta_ampla` e a frase da spec 022.
- [ ] Ibovespa `+1,00%`, `up_count=20`, `down_count=8`, `total_count=30`, dois motores negativos: humor `misto`.
- [ ] Pregão do Ibovespa `2026-11-04` e pregão da dispersão `2026-11-05`: humor `indisponivel` e a frase de painéis em pregões diferentes.
- [ ] Motores ausentes, dispersão presente, índice `+1%` e `fracao_em_alta=0,70`: a frase não inventa sinal de motor e diz que os motores faltaram; o humor não é `alta_ampla` só por isso se o apetite também faltar. Com apetite "Tomando risco" e o item 6 satisfeito, `alta_ampla` é permitido e a frase não cita motor.
- [ ] `up_count=2`, `down_count=8`, `total_count=20` (10 neutros): o gauge mostra 20% (`2 / (2 + 8)`), não 10% (`2 / 20`), a legenda mostra `2` subiram e `8` caíram, e o ⓘ diz que o gauge exclui quem ficou em zero.
- [ ] `tests/test_aceite_140.py` usa `exigir_spec_done("140")` e não abre rede.

## Invariantes de produção
- Com menos de 20% da amostra (`up_count / total_count`) em alta, a manchete publicada não está em `alta_ampla`.
- A direção do Ibovespa na manchete é a mesma de `paineis.ibovespa.variacao_pct`.
- Ibovespa, dispersão e motores exibidos na mesma tela têm a mesma data de pregão, ou a manchete está `indisponivel`.

## Fora do escopo
- Recalcular o fechamento anterior (specs 134 e 135) e o carimbo (spec 141).
- Trocar o texto de otimismo generalizado no dia em que a regra 6 cabe.
- Novo indicador de humor além do enum da manchete.
- Redesign da faixa da manchete.

## Plano de validação
`pytest -q tests/test_aceite_140.py` sem internet. O PR de implementação registra, num pregão real, a manchete de manhã e de tarde junto com dispersão, motores e Ibovespa do mesmo `/api/snapshot`. Esta spec não traz essa captura. O humor observado em 05/11/2026 não fica marcado como corrigido por existir este arquivo.
