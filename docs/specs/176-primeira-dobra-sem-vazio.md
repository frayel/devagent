---
id: 176
titulo: A primeira dobra da Visão Geral sem espaço vazio
status: ready
esforco: P
gaveta: experiência
aceite: tests/test_aceite_176.py
origem: Card Ibovespa hoje sem sobra
---

## Problema
Pedido do dono do produto em 17/11/2026: o card *Ibovespa hoje* ficou com um grande espaço em branco; diminuir esse card e trazer um ou dois cards para ocupar o espaço.

A pergunta que a tela responde: **o que o mercado está fazendo agora, sem rolar a página?** Hoje parte da primeira dobra é espaço vazio.

Na grade de 12 colunas (`app/static/tema.css:87`), a primeira linha tem *Ibovespa hoje* (`span-8`, `app/templates/index.html:42`) e *Maré do mercado* (`span-4`, `index.html:72`). Um item de grid estica até a altura da linha, e a altura é ditada pela Maré, que desde o PR #942 traz gauge, barras, treemap, legenda, sparkline e ainda os gauges de *Apetite aqui* e *Rotação* (`index.html:113-135`). Medido em 17/11 no Chromium com os dados do `make telas`:

| Janela | Ibovespa (conteúdo) | Ibovespa (esticado) | Vazio | Observação |
|---|---|---|---|---|
| 1440 px | 556 px | 1017 px | ~460 px abaixo dos gauges MM21/MM200 | o rótulo `-10%`/`+10%` fica longe dos gauges |
| 1024 px | 556 px | 556 px | ~500 × 1000 px à direita da Maré | a Maré (`span-4` vira `span-3`) fica sozinha na linha; *Clima Global* (`span-6`) não cabe ao lado |
| 390 px | 556 px | 556 px | nenhum | uma coluna |

Os gauges de Apetite e Rotação moram dentro do card da Maré por razão de layout (a spec 173 já registrou isso), mas são outra medida: Apetite aqui é SMAL11 menos Ibovespa no dia, e Rotação é bancos menos commodities. Eles fazem par com *Clima Global*, que mostra o apetite lá fora (spec 160).

## Comportamento esperado
1. **Card novo "Apetite e rotação".** Os dois gauges saem do card da Maré para um card próprio, `span-4`, com as classes `painel-apetite-rotacao visao-macro visao-geral`, posto no `index.html` logo depois de *Clima Global*. O conteúdo é o bloco `.gauges-pequenos` de hoje, sem mudança de texto, cor, escala ou cortes. O card ganha:
   - botão de método (`i`) com: "Apetite aqui: variação do dia do SMAL11 menos a do Ibovespa, em pontos percentuais. Tomando risco acima de +0,1 p.p., Defensivo abaixo de −0,1 p.p., Neutro no resto. Rotação: média da variação do dia de ITUB4, BBDC4 e BBAS3 menos a de VALE3, PETR4 e PRIO3. Para Bancos quando os bancos sobem mais de 0,5% e as commodities caem mais de 0,5%; Para Commodities no inverso; Neutra no resto. O apetite aqui e o lá fora (card Clima Global) são medidas diferentes e podem divergir." (cortes de `app/collectors/apetite_risco.py:49-54` e `app/collectors/rotacao_capital.py:13-14, 60-64`; confira os números no código na implementação e use os de lá se divergirem);
   - rodapé `Fonte <fonte> · <horário>` do Apetite (`apetite_risco.fonte`, `apetite_risco.time`). Se a Rotação tiver fonte diferente, os dois aparecem: `Fonte <f1> · <h1> · Rotação: <f2> · <h2>`. Sem Apetite, vale o da Rotação.
   - sem nenhum dos dois, o card não aparece (como o bloco hoje).
2. **Clima Global passa de `span-6` para `span-4`**, ao lado do card novo. Os dois juntos ocupam as 8 colunas abaixo do Ibovespa.
3. **A Maré ocupa duas linhas da grade** quando há mais de uma coluna: `.painel-mare { grid-row: span 2; }` a partir de 768 px. Abaixo de 768 px a grade tem uma coluna, e a regra não se aplica.
4. **O Ibovespa não estica:** `.painel-ibovespa { align-self: start; }`. O card fica com a altura do próprio conteúdo.
5. **A escala fica junto de cada gauge.** No card do Ibovespa, o `<div class="g-escala">` com `-10%` e `+10%` (`index.html:65`), hoje uma linha só abaixo dos dois gauges, passa para dentro de cada um dos dois `<div>` de gauge (MM21 e MM200), logo abaixo dele.
6. **O resto da Visão Geral não muda.** *Motores do Índice*, *Fator Peso Pesado* e *Concentração Setorial* seguem na ordem e no tamanho de hoje, abaixo. As outras abas não mudam. No modo *Só Sinais*, o card novo some como a Maré (classe `visao-macro`), o mesmo comportamento de hoje, em que os gauges somem junto com a Maré.

### Medido no protótipo
O protótipo (mesmas classes aplicadas pelo console, dados do `make telas`) deu:

| Janela | Ibovespa | Coluna da esquerda (Ibovespa + gap + Clima/Apetite) | Maré |
|---|---|---|---|
| 1440 px | 556 px | 556 + 12 + 308 = 876 px | 876 px (conteúdo ~720 px) |
| 1024 px | 556 px, linha inteira | Clima 315 px e Apetite 411 px, empilhados à direita da Maré | 737 px |
| 390 px | 556 px | uma coluna: Ibovespa, Maré, Clima, Apetite e rotação | 708 px |

A 1440 px o vazio abaixo do Ibovespa cai de ~460 px para 0. A 1024 px o vazio à direita da Maré cai de ~1000 px de altura para ~120 px no pé do card novo.

### Relação com a spec 173
A 173 (tela `/mare`) extrai o card da Maré para uma macro e prevê um bloco opcional por `caller` só para os gauges de Apetite e Rotação no painel geral. Esta spec tira esses gauges da Maré. Implemente **depois da 173**: na entrega desta, a macro da Maré deixa de receber o bloco de Apetite e Rotação no `index.html`, e a asserção "painel geral intacto" de `tests/test_aceite_173.py`, que procura os gauges de Apetite e Rotação dentro do `painel-mare` de `GET /`, passa a procurá-los no `painel-apetite-rotacao`. Diga isso no corpo do PR. Se a 173 ainda não estiver `done`, o bloco sai direto do `index.html`.

## Fontes de dados
Nenhuma nova. `get_apetite_risco_view_data()` e `get_rotacao_capital_view()` já chegam ao template. Plano B: o de hoje (item 1, card ausente sem dado).

## Cálculos
Nenhum.

## Critérios de aceite
- [ ] `tests/test_aceite_176.py`, com `exigir_spec_done("176")`, sem internet:
  - **HTML** (`TestClient` com os fixtures de rota de `tests/test_aceite_088.py` e os mocks de `tests/test_aceite_146.py`): o card `painel-apetite-rotacao` existe, tem `span-4`, `visao-macro`, o botão de método com o texto do item 1 e o rodapé `Fonte <fonte> · <horário>` do mock; contém `SMLL − IBOV` e `Bancos - Cmdts`; o `painel-mare` **não** contém mais nenhum dos dois; o *Clima Global* tem `span-4`; o card novo vem depois do *Clima Global* no HTML. Sem Apetite e sem Rotação, o card não aparece.
  - **Escala:** no `painel-ibovespa`, há dois `g-escala`, cada um dentro do `<div>` do seu gauge.
  - **Navegador** (Chromium do ambiente, sem rede externa, página do `make telas` ou HTML do `TestClient` com `app/static` servido, no padrão de `tests/test_aceite_146.py`):
    - a 1440×900: a altura do `painel-ibovespa` é a do conteúdo (diferença entre o fundo do último filho e o fundo do card de no máximo 24 px, o `padding`); `|fundo do card novo − fundo da Maré| <= 24 px`; o card novo e o *Clima Global* começam na mesma altura e logo abaixo do Ibovespa (diferença de topo igual ao `gap` da grade, ±2 px);
    - a 1024×900: o *Clima Global* e o card novo ficam à direita da Maré (borda esquerda deles depois da borda direita da Maré), o topo do *Clima Global* é o da Maré (±2 px) e o fundo do card novo fica a no máximo 24 px do fundo da Maré;
    - a 390×844: a ordem vertical é Ibovespa, Maré, Clima Global, Apetite e rotação; `scrollWidth <= innerWidth`.
- [ ] `tests/test_aceite_146.py`, `tests/test_aceite_160.py`, `tests/test_apetite_risco.py`, `tests/test_rotacao_capital.py`, os testes do heatmap e o `make telas` (sem `PROBLEMA`) seguem verdes. Única asserção alterada fora deste arquivo: a de `tests/test_aceite_173.py` descrita acima, se a 173 já estiver `done`.
- Arquivos tocados: `app/templates/index.html` (e `app/templates/componentes.html`, se a 173 já criou a macro), `app/static/tema.css`, o novo `tests/test_aceite_176.py` e, no caso acima, `tests/test_aceite_173.py`. `grep -rl "gauges-pequenos" app tests` dá hoje 2 arquivos (template e CSS).

## Invariantes de produção
- Em `/` a 1440 px, o card *Ibovespa hoje* não tem espaço vazio maior que 40 px abaixo do último elemento de conteúdo.
- O HTML de `/` tem um `painel-apetite-rotacao` com os valores de `paineis.apetite_risco.diferenca` do `/api/snapshot` do mesmo momento, e o `painel-mare` não tem `SMLL − IBOV`.
- A fonte e o horário do Apetite aparecem no rodapé do card novo.

## Fora do escopo
- Diminuir o card da Maré (tirar sparkline ou heatmap) ou mudar o que ele mostra além de perder os dois gauges.
- Mudar a largura do Ibovespa (segue `span-8`) ou o gráfico de 30 pregões.
- Reorganizar *Motores do Índice*, *Fator Peso Pesado* e *Concentração Setorial*, ou as outras abas.
- Juntar Apetite aqui e Clima Global num card só: são fontes e horários diferentes, e a spec 160 escolheu nomes separados.
- Layout configurável pelo usuário (arrastar cards).
