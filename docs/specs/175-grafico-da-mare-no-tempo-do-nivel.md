---
id: 175
titulo: O gráfico da Maré anda no tempo do nível
status: ready
esforco: M
gaveta: capacidade nova
aceite: tests/test_aceite_175.py
origem: nova
---

## Problema
Pedido do dono do produto em 17/11/2026: o gráfico abaixo do heatmap deve refletir o nível de tendência escolhido (spec 174) e mostrar a variação, em horas, dias ou meses.

Hoje o gráfico é uma sparkline sem eixo (`app/templates/index.html:104-109`, `build_sparkline` em `app/services/sparkline.py`) com até 22 pontos diários (os 21 pregões de `historico_json` mais a leitura atual) e uma frase que compara só com o pregão de 5 pregões atrás (`há 5 pregões: 52 · Neutro`, `mare.view`). Ela não diz quando começa nem quando termina, não diz quanto a Maré andou e não muda com o nível. A pergunta que a spec responde: **quanto a Maré andou no tempo do nível que estou olhando, e de onde para onde?**

## Comportamento esperado
O gráfico continua no mesmo lugar do card (abaixo do heatmap), desenhado no servidor em SVG, sem Plotly. Ele segue o nível ativo da spec 174:

| Nível | Um ponto por | Pontos | Fonte dos pontos | O gauge, no gráfico |
|---|---|---|---|---|
| **Marolas** (padrão) | coleta do pregão (cerca de 15 min) | as leituras do pregão de hoje, das 10h até agora | snapshot novo `mare_intradia` | o último ponto |
| **Ondas** | pregão | os 21 pregões completos da janela | `mare_historico.leituras` (spec 174) | linha tracejada da média |
| **Maré** | mês | a média de cada mês civil dos 252 pregões da janela (12 ou 13 pontos; o primeiro e o último mês podem ser parciais) | `mare_historico.leituras` | linha tracejada da média |

1. **Linha e média.** A linha liga os pontos na ordem do tempo. Em Ondas e Maré, uma linha horizontal tracejada marca o valor do gauge (a média da janela, spec 174), para mostrar a oscilação em volta do nível.
2. **Rótulos do tempo**, em HTML abaixo do SVG (texto dentro de SVG com `preserveAspectRatio="none"` distorce): à esquerda o primeiro ponto, à direita o último. Marolas: `10:15` e `14:30`. Ondas: `16/10` e `16/11`. Maré: `dez/25` e `nov/26`.
3. **Variação**, numa linha abaixo dos rótulos, no lugar da frase `há 5 pregões`:
   - Marolas: `Hoje: de 48 (10:15) para 55 (14:30), +7 pontos`
   - Ondas: `21 pregões: de 41 (16/10) para 58 (16/11), +17 pontos`
   - Maré: `12 meses: de 35 (dez/25) para 52 (nov/26), +17 pontos`
   
   Seguida de `mín 30 · máx 61`. O número da variação usa a macro `variacao` de `componentes.html` (cor de alta, baixa ou neutra, com o sinal escrito, porque cor sozinha não basta). Variação zero: `estável`.
4. **Acessível.** O `aria-label` do SVG é a frase do item 3.
5. **Marolas antes da segunda coleta do dia** (antes das 10h, fim de semana, feriado, ou só um ponto): o gráfico mostra o último pregão com pelo menos dois pontos e a frase começa com a data (`Pregão de 16/11: de ... para ...`). Sem nenhum pregão com dois pontos (primeiros dias depois do deploy): no lugar do gráfico, `A curva do dia começa na segunda coleta do pregão`.
6. **Ondas e Maré em formação** (spec 174, item 5): sem gráfico; a mensagem da 174 basta.
7. **Data passada** no painel geral (`?data=`): Marolas usa `mare_intradia` daquela data; Ondas e Maré, o `mare_historico` daquela data. Sem registro, sem gráfico e sem frase.
8. **Troca de nível sem recarregar** (spec 174, item 3): o fragmento `/mare/card` já devolve o gráfico do nível, nada a mais no `ui.js`.

## Fontes de dados
**`mare_intradia` (novo).** Em `collect_and_save` de `app/collectors/mare.py`, depois de gravar a leitura do momento, se a hora BRT da coleta estiver entre 10:00 e 18:15 (`FIM_PREGAO` de `app/agendador.py`, para pegar o leilão de fechamento) num dia de pregão (`app/calendario.py`), acrescenta `{hora: "HH:MM", valor}` ao snapshot `mare_intradia` do dia (`gravar_snapshot` com `data_referencia` = data BRT; leitura com `ler_snapshot("mare_intradia", dia)` antes de acrescentar). Ponto da mesma `HH:MM` substitui o anterior; no máximo 40 pontos por dia (o pregão de 10h às 18h15 a cada 15 min dá 34). Sem tabela nova: o snapshot por painel e data é o que já existe (ADRs 006 e 007).

**Ondas e Maré:** `mare_historico` da spec 174, sem coleta nova.

**Plano B:** falha ao gravar o ponto intradiário não pode derrubar a gravação da leitura (try/except com log, a leitura vem antes). Sem `mare_intradia`, item 5.

## Cálculos
- **Escala vertical:** de `min(pontos, gauge)` a `max(pontos, gauge)`, com a mesma folga e o mesmo tratamento de série constante de `build_sparkline` (amplitude mínima de 10 pontos). O gauge entra na escala para a linha da média nunca sair do desenho.
- **Média mensal (Maré):** média aritmética dos `valor` diários de cada mês civil presentes na janela; mês com menos de 5 leituras na borda da janela sai do gráfico (e a frase conta os meses que ficaram: `12 meses` ou `11 meses`).
- **Variação:** último ponto menos primeiro ponto, em pontos inteiros do índice (0 a 100), com sinal. Não é percentual: a Maré já é uma escala.
- **mín e máx:** dos pontos desenhados, não das leituras diárias por trás da média mensal.
- A função de desenho pode estender `build_sparkline` (sugestão: devolver também o `y` da média) ou ser uma nova em `app/services/sparkline.py`; o card de Ibovespa e as tabelas que usam `build_sparkline` (`tbody td .spark`, `tema.css:429`) não mudam.

## Critérios de aceite
- [ ] `tests/test_aceite_175.py`, com `exigir_spec_done("175")`, sem internet:
  - **intradiário gravado:** com o relógio em 14:30 BRT de um dia de pregão e a coleta mockada, `collect_and_save` acrescenta `{"hora": "14:30", ...}` a `mare_intradia` do dia; uma segunda chamada às 14:30 substitui o ponto (continua um); às 09:40 e às 18:30, ou num sábado, não acrescenta; com 40 pontos gravados, o 41º não entra;
  - **falha isolada:** se gravar `mare_intradia` levanta exceção, a leitura `mare` foi gravada assim mesmo;
  - **Marolas:** com `mare_intradia` de hoje = `[10:15 → 48, 12:00 → 50, 14:30 → 55]`, o HTML de `GET /mare` contém `10:15`, `14:30` e `Hoje: de 48 (10:15) para 55 (14:30), +7 pontos`, e não contém `há 5 pregões`;
  - **Marolas de ontem:** sem pontos hoje e com três pontos no pregão de 16/11, a frase começa com `Pregão de 16/11:`; sem nenhum dia com dois pontos, aparece `A curva do dia começa na segunda coleta do pregão`;
  - **Ondas:** com 21 leituras sintéticas nos pregões de 16/10 (41) a 16/11 (58), sem o feriado de 02/11, `GET /mare?nivel=ondas` contém `21 pregões: de 41 (16/10) para 58 (16/11), +17 pontos`, um `polyline` com 21 pontos e a linha tracejada da média no `y` do valor do gauge;
  - **Maré:** com 252 leituras sintéticas cobrindo de dez/25 a nov/26, a série tem um ponto por mês com a média do mês, o primeiro rótulo é `dez/25`, o último `nov/26`; um mês de borda com 3 leituras sai do gráfico;
  - **queda:** variação negativa aparece como `−N pontos` com a classe de baixa da macro `variacao`;
  - **fragmento:** `GET /mare/card?nivel=ondas` traz o gráfico de Ondas.
- [ ] `/api/snapshot`: `paineis.mare` ganha `intradia: {data, pontos: [{hora, valor}]}` com o dia mostrado em Marolas. Teste no mesmo arquivo.
- [ ] Os testes de `build_sparkline` que existem continuam verdes sem mudar asserções.

## Invariantes de produção
- Em `paineis.mare.intradia.pontos`, as horas são estritamente crescentes, todas entre `10:00` e `18:15`, e são no máximo 40.
- Com o pregão aberto e a última coleta da Maré com menos de 30 minutos, o último ponto de `intradia` tem o mesmo `valor` que `paineis.mare.valor`.
- `paineis.mare.intradia.data` é um dia de pregão da B3 igual ou anterior ao pregão corrente.
- No HTML de `/mare?nivel=ondas`, a variação da frase é igual ao último menos o primeiro dos 21 valores de Ondas.

## Fora do escopo
- Eixo com marcas intermediárias, grade, zoom ou tooltip por ponto (seria Plotly, que a spec 172 deixa só no gráfico do Ibovespa).
- Desenhar o Ibovespa junto da Maré no mesmo gráfico.
- Ondas com mais de 21 pregões ou Maré com mais de 12 meses: pede histórico além dos 2 anos da spec 174.
- O "pregão gêmeo" (item 12 da *Fila* do backlog), que vai poder usar a curva intradiária gravada aqui.
