---
id: 176
titulo: A primeira dobra da Visão Geral sem espaço vazio
status: ready
esforco: P
gaveta: experiência
aceite: tests/test_aceite_176.py
origem: Card Ibovespa hoje sem sobra
revisada: 2026-11-18
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
2. **Clima Global passa de `span-6` para `span-4`**, ao lado do card novo. Os dois juntos ocupam as 8 colunas abaixo do Ibovespa. O texto de método do Clima Global (`clima_metodo`, `index.html:102`) termina hoje em "o apetite aqui (card Maré do mercado)"; com a mudança isso fica falso, e o trecho passa a "o apetite aqui (card Apetite e rotação)".
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

Remedido na revisão em 18/11, depois da spec 175 (gráfico da Maré no tempo do nível, que deixou a Maré mais alta), com as mesmas regras aplicadas pelo console sobre a `main` e os dados do `make telas`:

| Janela | Ibovespa | Clima e Apetite | Maré |
|---|---|---|---|
| 1440 px | 556 px (topo 268, fundo 824) | os dois com topo 836 (gap de 12 px) e fundo 1142 | 874 px (topo 268, fundo 1142) |
| 1024 px | 556 px, linha inteira | à direita da Maré: Clima 864 a 1237, Apetite 1249 a 1718 | 854 px (864 a 1718) |
| 390 px | 556 px | uma coluna, nessa ordem depois da Maré | 842 px; `scrollWidth` 390 |

Os critérios de navegador abaixo passam com essas medidas. Na `main` de 18/11, sem as regras, o vão entre a escala `-10%`/`+10%` e o rodapé do Ibovespa a 1440 px é de 589 px (era ~460 px em 17/11; a Maré cresceu com a 175).

### Relação com a spec 173
A 173 (tela `/mare`) já está `done`: o card da Maré é a macro `card_mare` de `app/templates/componentes.html:137`, e o `index.html:77` a chama com `{% call card_mare(...) %}` passando o bloco `.gauges-pequenos` pelo `caller`. Na entrega desta spec, o bloco sai desse `call` e vai para o card novo; o `index.html` passa a chamar a macro sem `caller` (`{{ card_mare(...) }}`, que a macro já aceita pelo `caller is defined`). A macro em si não muda; o comentário dela (`componentes.html:131-135`) cita os gauges de Apetite e Rotação no painel geral como exemplo do bloco opcional; atualize-o para não citar mais.

O teste `test_painel_geral_mantem_apetite_e_rotacao_no_card` de `tests/test_aceite_173.py:137` procura `SMLL − IBOV` e `bancos − commodities` dentro do `painel-mare` de `GET /`. Ele passa a procurá-los no `painel-apetite-rotacao` e a afirmar que o `painel-mare` de `GET /` não os tem (o nome da função pode mudar para dizer isso). As outras asserções da 173 não mudam. Diga isso no corpo do PR.

## Fontes de dados
Nenhuma nova. `get_apetite_risco_view_data()` e `get_rotacao_capital_view()` já chegam ao template. Plano B: o de hoje (item 1, card ausente sem dado).

## Cálculos
Nenhum.

## Critérios de aceite
- [ ] `tests/test_aceite_176.py`, com `exigir_spec_done("176")`, sem internet:
  - **HTML** (`TestClient` com os fixtures de rota de `tests/test_aceite_088.py` e os mocks de `tests/test_aceite_146.py`): o card `painel-apetite-rotacao` existe, tem `span-4`, `visao-macro`, o botão de método com o texto do item 1 e o rodapé `Fonte <fonte> · <horário>` do mock; o método do *Clima Global* diz "card Apetite e rotação" e não diz mais "card Maré do mercado"; contém `SMLL − IBOV` e `Bancos - Cmdts`; o `painel-mare` **não** contém mais nenhum dos dois; o *Clima Global* tem `span-4`; o card novo vem depois do *Clima Global* no HTML. Sem Apetite e sem Rotação, o card não aparece.
  - **Escala:** no `painel-ibovespa`, há dois `g-escala`, cada um dentro do `<div>` do seu gauge.
  - **Navegador** (Chromium do ambiente, sem rede externa, página do `make telas` ou HTML do `TestClient` com `app/static` servido, no padrão de `tests/test_aceite_146.py`):
    - a 1440×900: a altura do `painel-ibovespa` é a do conteúdo: a distância entre o topo do `.rodape` do card e o fundo do elemento logo antes dele é de no máximo 24 px (o `.rodape` tem `margin-top: auto`, `tema.css:176`, e desce para o fundo do card quando ele estica; por isso medir o fundo do último filho contra o fundo do card não prova nada: dá ~17 px esticado ou não). Hoje essa distância é 589 px; com as regras desta spec, 12 px; `|fundo do card novo − fundo da Maré| <= 24 px`; o card novo e o *Clima Global* começam na mesma altura e logo abaixo do Ibovespa (diferença de topo igual ao `gap` da grade, ±2 px);
    - a 1024×900: o *Clima Global* e o card novo ficam à direita da Maré (borda esquerda deles depois da borda direita da Maré), o topo do *Clima Global* é o da Maré (±2 px) e o fundo do card novo fica a no máximo 24 px do fundo da Maré;
    - a 390×844: a ordem vertical é Ibovespa, Maré, Clima Global, Apetite e rotação; `scrollWidth <= innerWidth`.
- [ ] `tests/test_aceite_146.py`, `tests/test_aceite_160.py`, `tests/test_apetite_risco.py`, `tests/test_rotacao_capital.py`, os testes do heatmap e o `make telas` (sem `PROBLEMA`) seguem verdes. Único teste alterado fora deste arquivo: o de `tests/test_aceite_173.py` descrito acima.
- Arquivos tocados: `app/templates/index.html`, `app/static/tema.css`, o novo `tests/test_aceite_176.py`, `tests/test_aceite_173.py` e, só para o comentário, `app/templates/componentes.html`. `grep -rl "gauges-pequenos" app tests` dá hoje 2 arquivos (template e CSS).

## Invariantes de produção
- Em `/` a 1440 px, o card *Ibovespa hoje* não tem espaço vazio maior que 40 px entre o último elemento de conteúdo e o rodapé `Fonte ... · horário`.
- O HTML de `/` tem um `painel-apetite-rotacao` com os valores de `paineis.apetite_risco.diferenca` do `/api/snapshot` do mesmo momento, e o `painel-mare` não tem `SMLL − IBOV`.
- A fonte e o horário do Apetite aparecem no rodapé do card novo.

## Fora do escopo
- Diminuir o card da Maré (tirar sparkline ou heatmap) ou mudar o que ele mostra além de perder os dois gauges.
- Mudar a largura do Ibovespa (segue `span-8`) ou o gráfico de 30 pregões.
- Reorganizar *Motores do Índice*, *Fator Peso Pesado* e *Concentração Setorial*, ou as outras abas.
- Juntar Apetite aqui e Clima Global num card só: são fontes e horários diferentes, e a spec 160 escolheu nomes separados.
- Layout configurável pelo usuário (arrastar cards).
