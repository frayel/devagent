---
id: 175
titulo: O gráfico da Maré anda no tempo do nível
status: ready
esforco: M
gaveta: capacidade nova
aceite: tests/test_aceite_175.py
origem: nova
revisada: 2026-11-17
---

## Problema
Pedido do dono do produto em 17/11/2026: o gráfico abaixo do heatmap deve refletir o nível de tendência escolhido (seletor da spec 174b, sobre o histórico da 174a; a 174 original foi dividida nessas duas, ambas `done`) e mostrar a variação, em horas, dias ou meses.

Hoje o gráfico é uma sparkline sem eixo (macro da Maré em `app/templates/componentes.html`, `build_sparkline` em `app/services/sparkline.py`) com até 22 pontos diários (os 21 pregões de `historico_json` mais a leitura atual) e uma frase que compara só com o pregão de 5 pregões atrás (`há 5 pregões: 52 · Neutro`, chave `comparacao` de `mare.view`). Ela não diz quando começa nem quando termina, não diz quanto a Maré andou e não muda com o nível (a 174b, item 4, deixou a sparkline igual em todos os níveis até esta spec). A pergunta que a spec responde: **quanto a Maré andou no tempo do nível que estou olhando, e de onde para onde?**

## Comportamento esperado
O gráfico continua no mesmo lugar do card (abaixo do heatmap), desenhado no servidor em SVG, sem Plotly. Ele segue o nível ativo da spec 174b:

| Nível | Um ponto por | Pontos | Fonte dos pontos | O gauge, no gráfico |
|---|---|---|---|---|
| **Marolas** (padrão) | coleta do pregão (cerca de 15 min) | as leituras do pregão de hoje, das 10h até agora | snapshot novo `mare_intradia` | o último ponto |
| **Ondas** | pregão | as mesmas `pregoes` leituras (15 a 21) que deram `niveis.ondas.valor` | `mare_historico.leituras` (spec 174a) | linha tracejada em `niveis.ondas.valor` |
| **Maré** | mês | a média de cada mês civil das mesmas `pregoes` leituras (189 a 252) que deram `niveis.mare.valor`; com 252 pregões são 13 meses, o primeiro e o último parciais | `mare_historico.leituras` | linha tracejada em `niveis.mare.valor` |

Os pontos de Ondas e Maré saem da mesma função de `app/services/mare.py` que calcula o nível (174a, item 3), para a linha tracejada ser a média exata dos pontos de Ondas e o gráfico nunca usar uma janela diferente da do gauge.

1. **Linha e média.** A linha liga os pontos na ordem do tempo. Em Ondas e Maré, uma linha horizontal tracejada marca o valor do gauge (a média da janela, 174a), para mostrar a oscilação em volta do nível.
2. **Rótulos do tempo**, em HTML abaixo do SVG (texto dentro de SVG com `preserveAspectRatio="none"` distorce): à esquerda o primeiro ponto, à direita o último. Marolas: `10:15` e `14:30`. Ondas: `16/10` e `16/11`. Maré: `nov/25` e `nov/26` (mês abreviado em minúsculas, sem ponto, ano com dois dígitos).
3. **Variação**, numa linha abaixo dos rótulos, no lugar da frase `há 5 pregões` (a chave `comparacao` sai de `mare.view`):
   - Marolas: `Hoje: de 48 (10:15) para 55 (14:30), +7 pontos`
   - Ondas: `21 pregões: de 41 (16/10) para 58 (16/11), +17 pontos` (o número é `niveis.ondas.pregoes`; com 18 leituras, `18 pregões`)
   - Maré: `13 meses: de 35 (nov/25) para 52 (nov/26), +17 pontos` (o número é a quantidade de meses desenhados)

   Seguida de `mín 30 · máx 61`. A frase tem duas formas:
   - **texto puro**, igual aos exemplos acima, no `aria-label` do SVG (item 4). Sinal negativo é o `−` (U+2212), não o hífen: `−6 pontos`. Variação zero: `estável` no lugar de `+0 pontos`;
   - **na tela**, o trecho da variação (`+7 pontos`) vai pela macro `variacao(valor_formatado, sinal)` de `componentes.html`, que acrescenta a seta e a classe `alta`, `baixa` ou `neutra` (cor sozinha não basta). Por isso o HTML visível tem `<span class="var alta">▲ +7 pontos</span>` no meio da frase: os testes conferem a frase inteira pelo `aria-label`, e a classe pelo `span`.
4. **Acessível.** O `aria-label` do SVG é a frase do item 3 em texto puro (hoje é `resumo_serie`, que esta spec substitui no card da Maré).
5. **Marolas antes da segunda coleta do dia** (antes das 10h15, fim de semana, feriado, ou só um ponto): o gráfico mostra o pregão mais recente com pelo menos dois pontos, procurando `ler_snapshot("mare_intradia", d)` em hoje e, se preciso, nos até 5 pregões anteriores (`calendario.pregao_anterior`), e a frase começa com a data (`Pregão de 16/11: de ... para ...`). Não use `listar_datas`: ele ignora snapshots com estado `ao_vivo`, que é o estado gravado durante o pregão. Sem nenhum desses dias com dois pontos (primeiros dias depois do deploy): no lugar do gráfico, `A curva do dia começa na segunda coleta do pregão`.
6. **Ondas e Maré em formação** (spec 174b, item 5, nível `null`): sem gráfico; a mensagem da 174b basta.
7. **Data passada** no painel geral (`?data=`): Marolas usa `ler_snapshot("mare_intradia", data)` daquela data (sem procurar pregões anteriores); Ondas e Maré, o `mare_historico` daquela data, como a 174b já faz. Sem registro, sem gráfico e sem frase.
8. **Troca de nível sem recarregar** (spec 174b, item 3): o fragmento `/mare/card` já devolve o gráfico do nível, nada a mais no `ui.js`.

## Fontes de dados
**`mare_intradia` (novo).** Em `collect_and_save` de `app/collectors/mare.py`, depois de `save_mare_data(dado)`, se a hora BRT de `dado.timestamp` estiver entre 10:00 e 18:15 inclusive (`FIM_PREGAO` de `app/agendador.py`, para pegar o leilão de fechamento) num dia de pregão (`calendario.e_pregao`), acrescenta `{hora: "HH:MM", valor}` ao snapshot `mare_intradia` do dia: lê `ler_snapshot("mare_intradia", dia)`, acrescenta e grava com `gravar_snapshot("mare_intradia", dia, "ao_vivo", dado.fonte, {"data": dia ISO, "pontos": [...]})`, com `dia` = data **BRT** de `dado.timestamp` (atenção: `save_mare_data` usa `data.timestamp.date()`, que é UTC; aqui não). Ponto da mesma `HH:MM` substitui o anterior; pontos em ordem crescente de hora; no máximo 40 pontos por dia (o pregão de 10h às 18h15 a cada 15 min dá 34). Sem tabela nova: o snapshot por painel e data é o que já existe (ADRs 006 e 007). A guarda de horário também protege contra a partida a frio fora da janela (issue #919): coleta da Maré às 20h não acrescenta ponto.

**Ondas e Maré:** `mare_historico` da spec 174a, sem coleta nova.

**Plano B:** falha ao gravar o ponto intradiário não pode derrubar a gravação da leitura (try/except com log, a leitura vem antes) nem mudar o retorno `True` de `collect_and_save`. Sem `mare_intradia`, item 5. `remover_snapshots_antigos` guarda 30 datas, então `?data=` mais antiga fica sem curva de Marolas (item 7).

## Cálculos
Unidades: `valor` é inteiro de 0 a 100 (pontos do índice, não percentual), tanto em `mare_intradia.pontos` quanto em `mare_historico.leituras`; `hora` é `HH:MM` BRT; `data` é ISO.

- **Escala vertical**, no mesmo `viewBox 0 0 200 48` de `build_sparkline`: `menor = min(pontos + [gauge])`, `maior = max(pontos + [gauge])` (em Marolas o gauge é o último ponto e não muda nada); `y(v) = 44 − (v − menor) / (maior − menor) × 40`, arredondado a 1 casa; série constante (`maior − menor` < 1e-6) vira `menor = v − 5`, `maior = v + 5`, como `build_sparkline` faz hoje. Não há folga além dessa. O gauge entra na escala para a linha da média nunca sair do desenho.
  *Exemplo (Ondas):* 21 leituras, a primeira 41, 19 com 50 e a última 58 → `niveis.ondas.valor` = (41 + 19 × 50 + 58) / 21 = 1049 / 21 = 49,95 → **50**. `menor` = 41, `maior` = 58. Linha tracejada em y(50) = 44 − (50 − 41) / 17 × 40 = 44 − 21,18 = **22,8**; o primeiro ponto em `0,44.0`, o último em `200,4.0`; passo horizontal 200 / 20 = 10.
- **Média mensal (Maré):** média aritmética dos `valor` diários de cada mês civil (pela `data` da leitura) dentro das leituras do nível, arredondada por `_arredondar` (meio para cima); mês com menos de 5 leituras sai do gráfico (só acontece nas bordas). A frase conta os meses que ficaram.
  *Exemplo:* nov/26 com 10 leituras, 8 de 50 e 2 de 55 → (8 × 50 + 2 × 55) / 10 = 510 / 10 = **51**. Com o calendário da B3, os 252 pregões até 16/11/2026 vão de 10/11/2025 a 16/11/2026: nov/25 tem 14 leituras, dez/25 20, …, nov/26 10 → 13 pontos, `13 meses`, rótulos `nov/25` e `nov/26`. Se a janela começasse em 26/11/2025, nov/25 teria 3 leituras e sairia: `12 meses`, de `dez/25`.
- **Variação:** valor do último ponto desenhado menos o do primeiro, inteiro, com sinal. *Exemplo:* 58 − 41 = **+17 pontos**; 49 − 55 = **−6 pontos**; 50 − 50 = **estável**. Não é percentual: a Maré já é uma escala.
- **mín e máx:** dos pontos desenhados, não das leituras diárias por trás da média mensal nem do gauge. *Exemplo (Ondas acima):* `mín 41 · máx 58`.
- A função de desenho pode estender `build_sparkline` (sugestão: parâmetro opcional `referencia` que entra na escala e devolve também o `y` dela) ou ser uma nova em `app/services/sparkline.py`; as chamadas atuais de `build_sparkline` (`highlights`, `forca_relativa`, `radar_congestionamento`, o card de Ibovespa e as tabelas com `tbody td .spark`) não mudam de saída.

## Critérios de aceite
- [ ] `tests/test_aceite_175.py`, com `exigir_spec_done("175")`, sem internet:
  - **intradiário gravado:** com `dado.timestamp` em 14:30 BRT de um dia de pregão e a coleta mockada, `collect_and_save` acrescenta `{"hora": "14:30", ...}` a `mare_intradia` do dia BRT; uma segunda chamada às 14:30 substitui o ponto (continua um); às 09:40 e às 18:30, ou num sábado, não acrescenta; com 40 pontos gravados, o 41º não entra; às 22:30 BRT (01:30 UTC do dia seguinte) não grava nada em nenhum dos dois dias;
  - **falha isolada:** se gravar `mare_intradia` levanta exceção, a leitura `mare` foi gravada assim mesmo e `collect_and_save` devolve `True`;
  - **Marolas:** com `mare_intradia` de hoje = `[10:15 → 48, 12:00 → 50, 14:30 → 55]`, o HTML de `GET /mare` contém os rótulos `10:15` e `14:30`, o `aria-label="Hoje: de 48 (10:15) para 55 (14:30), +7 pontos"`, `mín 48 · máx 55`, e não contém `há 5 pregões`;
  - **Marolas de ontem:** sem pontos hoje e com três pontos no pregão de 16/11, a frase começa com `Pregão de 16/11:`; sem nenhum dia com dois pontos, aparece `A curva do dia começa na segunda coleta do pregão`;
  - **Ondas:** com o `mare_historico` sintético do exemplo de *Cálculos* (21 leituras nos pregões de 16/10 a 16/11/2026, sem o feriado de 02/11, primeira 41, última 58, as outras 50), `GET /mare?nivel=ondas` contém `aria-label="21 pregões: de 41 (16/10) para 58 (16/11), +17 pontos"`, um `polyline` com 21 pontos e a linha tracejada da média com `y` 22.8;
  - **Maré:** com 252 leituras sintéticas nos pregões de 10/11/2025 a 16/11/2026, a série tem 13 pontos, um por mês com a média do mês, o primeiro rótulo é `nov/25` e o último `nov/26`; com as leituras começando em 26/11/2025 (3 leituras em nov/25), o primeiro rótulo é `dez/25` e a frase diz `12 meses`;
  - **queda:** variação negativa aparece como `−6 pontos` (U+2212) no `aria-label` e dentro de um `span` com a classe `baixa` da macro `variacao`; variação zero, `estável` com a classe `neutra`;
  - **fragmento:** `GET /mare/card?nivel=ondas` traz o gráfico de Ondas.
- [ ] `/api/snapshot`: `paineis.mare` ganha `intradia: {data, pontos: [{hora, valor}]}` com o dia mostrado em Marolas (o de hoje ou o do item 5), ou `null` sem nenhum dia com dois pontos. Teste no mesmo arquivo.
- [ ] Os testes de `build_sparkline` que existem continuam verdes sem mudar asserções. A única asserção antiga que muda é `"há 5 pregões: 56 · Neutro"` em `tests/test_mare.py` (comportamento que esta spec remove): troque pela checagem de que o card tem o gráfico de Marolas ou a mensagem do item 5.

## Invariantes de produção
- Em `paineis.mare.intradia.pontos`, as horas são estritamente crescentes, todas entre `10:00` e `18:15`, e são no máximo 40.
- Com o pregão aberto e a última coleta da Maré com menos de 30 minutos, o último ponto de `intradia` tem o mesmo `valor` que `paineis.mare.valor`.
- `paineis.mare.intradia.data` é um dia de pregão da B3 igual ou anterior ao pregão corrente.
- No HTML de `/mare?nivel=ondas`, a variação da frase é igual à última menos a primeira das `niveis.ondas.pregoes` leituras mais recentes de `mare_historico`, e o número de pregões da frase é `paineis.mare.niveis.ondas.pregoes`.

## Fora do escopo
- Eixo com marcas intermediárias, grade, zoom ou tooltip por ponto (seria Plotly, que a spec 172 deixa só no gráfico do Ibovespa).
- Desenhar o Ibovespa junto da Maré no mesmo gráfico.
- Ondas com mais de 21 pregões ou Maré com mais de 252: pede histórico além dos 2 anos da spec 174a.
- A correção geral da partida a frio da issue #919 (aqui só a guarda de horário do ponto intradiário).
- O "pregão gêmeo" (item 12 da *Fila* do backlog), que vai poder usar a curva intradiária gravada aqui.

## Revisão
Revisada em 17/11/2026. O que mudou:
- A spec 174 foi dividida em 174a (histórico) e 174b (seletor), ambas `done`; as referências passam a apontar a parte certa, e os pontos de Ondas e Maré passam a ser as mesmas leituras que deram o gauge (`pregoes` de 15 a 21 e de 189 a 252), não 21 e 252 fixos.
- O exemplo de Maré era impossível: 252 pregões até 16/11/2026 começam em 10/11/2025 (conferido com `app/calendario.py`), então são 13 meses, de `nov/25`, não 12 a partir de `dez/25`. Exemplo e aceite corrigidos.
- A escala dizia "a mesma folga e amplitude mínima de 10 pontos" de `build_sparkline`, que não tem folga nem amplitude mínima, só o caso da série constante (±5). Fórmula escrita e exemplos numéricos de ponta a ponta acrescentados para escala, média mensal e variação.
- A frase com a macro `variacao` leva seta e `span` no meio do texto; o aceite agora confere a frase pelo `aria-label` (texto puro) e a classe pelo `span`.
- Marolas de ontem: a procura usa `ler_snapshot` por data, porque `listar_datas` ignora snapshots `ao_vivo`; a data do snapshot é a BRT, não a UTC de `save_mare_data`.
- O teste antigo `tests/test_mare.py` que afirma `há 5 pregões` é declarado como a asserção que muda.
