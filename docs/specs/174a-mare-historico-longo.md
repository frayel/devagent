---
id: 174a
titulo: O humor médio do último mês e do último ano, gravado uma vez por pregão
status: ready
esforco: M
gaveta: capacidade nova
aceite: tests/test_aceite_174a.py
origem: nova
revisada: 2026-11-17
---

## Problema
Primeira parte da spec 174 (Maré em três níveis, pedido do dono do produto em 17/11/2026). A segunda, o seletor no card, é a **174b**, e a 175 (gráfico no tempo do nível) também lê o que esta parte grava.

A Maré de hoje (spec 027) só lê o pregão corrente e os 21 anteriores. A pergunta desta parte: **qual foi o humor médio da bolsa nos últimos 21 pregões (Ondas) e nos últimos 252 (Maré)?** Ela grava esse histórico uma vez por pregão e o expõe em `/api/snapshot`; a tela vem na 174b.

| Nível | Na teoria de Dow | Janela |
|---|---|---|
| **Marolas** | oscilações diárias | a leitura do pregão corrente (a de hoje, sem mudança) |
| **Ondas** | tendência secundária (3 semanas a 3 meses) | últimos 21 pregões completos |
| **Maré** | tendência primária (um ano ou mais) | últimos 252 pregões completos |

## Comportamento esperado
1. **Coletor novo `app/collectors/mare_historico.py`** com `collect_and_save()`, no padrão dos outros módulos que `_coletar` (em `app/agendador.py`) percorre pelo nome. Ele reaproveita `buscar_ibov` e a lógica de `buscar_cesta` de `app/collectors/mare.py`, com `range=2y&interval=1d` na cesta (a URL do Ibovespa já é `range=2y`), e grava o snapshot `mare_historico` por `gravar_snapshot` (painel com o mesmo nome do módulo, para o agendador o reconhecer) com:
   - `leituras`: os até 252 pregões completos mais recentes, em ordem crescente de data, `{data, valor, fluxo, calma, volume}`, cada um por `_Calculadora.leitura(dia, 1.0)` de `app/services/mare.py` (sem fórmula nova de componente). Pregão com `valor` `None` fica de fora;
   - `heatmap_ondas` e `heatmap_mare`: as 10 ações de cada janela, `{ticker, variacao, financeiro, peso}`, no formato do heatmap de hoje (ver *Cálculos*);
   - `ate`: data ISO do último pregão completo.
2. **Uma vez por pregão completo.** Entra em `_coletar` com uma janela nova, `"diario"`, no dicionário `janelas`: coleta só quando o mercado **não** está aberto e não existe `ler_snapshot("mare_historico", ult_fechado)`, com `data_ref_coleta = ult_fechado`. Na prática roda na primeira rodada depois do fechamento (18h15 BRT, `FIM_PREGAO`) e na partida a frio (o fallback genérico do fim do bloco já checa `ler_snapshot(nome, ult_fechado)`). Cuidado com o mecanismo atual: durante o pregão o agendador força `_data_referencia_snapshot` para o pregão corrente, e uma checagem pelo último completo nunca acharia o snapshot, rodando o coletor a cada 15 min. É o mesmo tipo de defeito da issue #919: não o repita.
3. **Níveis no `/api/snapshot`.** `paineis.mare` ganha `niveis.ondas` e `niveis.mare`, cada um `{valor, faixa, pregoes, de, ate, componentes: {fluxo, calma, volume}, pesos, ausentes, heatmap}` ou `null` em formação (abaixo do mínimo, ver *Cálculos*) ou sem `mare_historico`. Uma função pura em `app/services/mare.py` (sugestão: `nivel(leituras, n)`) faz a conta; a 174b a reaproveita na tela.
4. **Marolas não muda:** o coletor `mare` e a chave `paineis.mare` atual continuam idênticos.

## Fontes de dados
Yahoo `/v8/finance/chart` (a mesma do coletor da Maré; `fonte` pelo `mt5.fonte_efetiva("yfinance")`, como hoje, só para o rótulo). São 31 requisições de cerca de 500 pontos uma vez por pregão, contra as 31 de cerca de 63 pontos que o coletor `mare` faz a cada rodada.

**Por que 2 anos bastam:** a Calma de um dia pede 120 volatilidades anteriores (`MINIMO_PERCENTIL`) sobre retornos de 10 pregões (`JANELA_VOLATILIDADE`); com cerca de 504 pregões de Ibovespa, o mais antigo dos 252 dias tem perto de 240 volatilidades antes dele. O Volume pede até 21 pregões antes (`JANELA_MEDIA_VOLUME`), também com folga.

**Plano B:** se o Yahoo falhar, `collect_and_save()` devolve `False` sem gravar, e a leitura continua no snapshot anterior (`ler_snapshot("mare_historico")` sem data devolve o mais recente); o `ate` mostra até onde vai a janela. A cobertura mínima de 80% dos pregões (`COBERTURA_MINIMA`) passa a valer sobre os 2 anos: ação listada há menos de cerca de 400 pregões sai da amostra do histórico (não da de Marolas). Com menos de 20 ações (`MINIMO_ACOES`), Fluxo e Volume ficam ausentes, como hoje.

## Cálculos
Todas com exemplo de ponta a ponta. Unidades como o Yahoo entrega: `close` em reais por ação, `volume` em quantidade de ações (unidade, não milhar).

- **Valor do nível** (Ondas N = 21, Maré N = 252): média aritmética dos `valor` (inteiros 0 a 100) das N leituras mais recentes de `leituras`, arredondada por `_arredondar` (meio para cima). Média dos valores, e não índice das médias, para o gauge ser a linha de média do gráfico da 175.
  *Exemplo:* 20 leituras com valor 50 e uma com 61 → (20 × 50 + 61) / 21 = 1061 / 21 = 50,52 → **51**, faixa `mare.faixa(51)`. `pregoes` = 21, `de` = data da 1ª dessas 21 leituras, `ate` = data da última.
- **Mínimo de leituras:** Ondas 15 de 21, Maré 189 de 252 (75%). *Exemplo:* `leituras` com 14 itens → `niveis.ondas` = `null`; com 188 → `niveis.mare` = `null` e `niveis.ondas` calculado com as 21 últimas. Com 200 leituras, Maré usa as 200 e `pregoes` = 200.
- **Componente do nível:** média do componente nos dias da janela em que ele não é `None`; presente em menos de 75% dos dias, fica ausente no nível. Pesos: `indice()` sobre as médias presentes (reescala de 40/35/25, como na 144), em fração 0 a 1.
  *Exemplo (Ondas, 21 dias):* Calma presente em 21 dias com média 48,0; Volume em 21 dias, média 62,0; Fluxo presente em 15 dias (15/21 = 71% < 75%) → Fluxo ausente; pesos 0,35/(0,35+0,25) = **0,5833** para Calma e **0,4167** para Volume (soma 1; visíveis 58% e 42% pela `_peso_visivel` da 144). Com Fluxo em 16 dias (76%), ele fica presente. Como o valor é a média dos valores diários, a soma ponderada das barras pode diferir do gauge em alguns pontos quando algum dia teve componente ausente; o método da 174b diz isso.
- **Heatmap da janela:** para cada ação, `variacao = (fech[último pregão da janela] / fech[pregão anterior ao primeiro da janela] − 1) × 100`, em %; `financeiro = Σ fech × volume` nos pregões da janela, em reais; ordena por `financeiro`, fica com as 10 maiores e `peso = financeiro / Σ financeiro das 10`, em fração 0 a 1 (como o heatmap de hoje). Ação sem fechamento no pregão anterior à janela fica de fora.
  *Exemplo (Ondas):* PETR4 fecha R$ 30,00 no pregão anterior à janela e R$ 31,50 no último → (31,50 / 30,00 − 1) × 100 = **+5,0%**. Nos 21 pregões, fechamento de R$ 31,00 em média × 10.000.000 ações por dia → financeiro ≈ 21 × 310.000.000 = **R$ 6,51 bi**. Se as 10 maiores somam R$ 26,04 bi, peso = 6,51 / 26,04 = **0,25** (o treemap desenha 25% da área).

## Critérios de aceite
- [ ] `tests/test_aceite_174a.py`, com `exigir_spec_done("174a")`, sem internet:
  - **cálculo:** os três exemplos de *Cálculos* acima, com `leituras` sintéticas, dão 51, `null` com 14 e com 188, Fluxo ausente com 15 de 21 e presente com 16, pesos 0,5833/0,4167;
  - **heatmap:** com séries sintéticas de 3 ações, a variação de 21 pregões e a ordem por financeiro somado batem com a conta à mão;
  - **coletor:** com o Yahoo falso de `tests/yahoo_falso.py` (já atende `range=2y`, 504 pregões), `collect_and_save()` grava `mare_historico` com no máximo 252 leituras, em ordem crescente, todas com data ≤ último pregão completo, e `heatmap_ondas`/`heatmap_mare` com no máximo 10 ações cada;
  - **agendamento:** com o calendário fixado depois das 18h15 de um dia de pregão e sem snapshot, `_coletar` chama o coletor `mare_historico` uma vez; numa segunda rodada do mesmo dia, não chama. Com o mercado aberto e snapshot do último pregão completo presente, também não chama;
  - **plano B:** com o Yahoo respondendo 429, nada é gravado e `/api/snapshot` mantém os `niveis` do snapshot anterior; sem nenhum `mare_historico`, `niveis.ondas` e `niveis.mare` são `null` e o resto de `paineis.mare` não muda.

## Invariantes de produção
- `paineis.mare.niveis.ondas.pregoes` está entre 15 e 21, e `paineis.mare.niveis.mare.pregoes` entre 189 e 252, quando não são `null`.
- `paineis.mare.niveis.<nivel>.ate` é um dia útil da B3 e, depois das 18h15 BRT de um dia de pregão, no máximo um pregão antes do último pregão completo.
- `valor` de cada nível está entre 0 e 100 e `faixa` é `mare.faixa(valor)`; os `pesos` dos presentes somam 1 (±0,001).
- O log não mostra `Partida a frio para mare_historico` mais de uma vez por pregão.

## Fora do escopo
- Seletor, card, fragmento `/mare/card`, legenda do heatmap e método: spec 174b.
- Gráfico no tempo do nível: spec 175.
- Classificar a tendência por topos e fundos (Dow clássica); aqui o nível é só a janela da média.
- Calibrar janelas (21 e 252) ou mínimos com evidência: spec nova, como manda o cabeçalho de `app/services/mare.py`.
- A correção geral da partida a frio da issue #919.
