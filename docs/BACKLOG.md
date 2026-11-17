# Backlog

Uma lista só, em ordem de prioridade. Consolidada em 15/11/2026 a partir de 318 linhas espalhadas por 52 seções de ideias e uma tabela de features; o mapa do que saiu e por quê está em `docs/runs/2026-11-15-backlog-consolidado.md`.

**Regras deste arquivo** (Passo 7 do `devagent/CICLO.md`):

- A *Fila* tem no máximo 25 itens. Ideia nova entra numa vaga livre ou desloca a última; a deslocada desce para a *Reserva* em uma linha.
- Antes de registrar, procure aqui e em `docs/specs/`. Ideia que já existe ganha detalhe na entrada dela, não linha nova.
- A ideia que vira spec sai da *Fila* no mesmo PR `spec:`. Se for grande, a entrada fica só com o resto da visão.
- Prioridade: o que mostra número errado ao usuário, depois o que tem medida que sustenta, depois o que só este sistema pode fazer (o próprio histórico), depois o resto.

## Correções (prioridade sobre qualquer feature)

## Fila

| # | Gaveta | Ideia | Pergunta e evidência | Esforço |
|---|---|---|---|---|
| 1 | Saúde técnica | Rate limit sem travar o loop | `async_fetch_with_retry` chama `_enforce_rate_limit` (`app/collectors/utils.py:175`), que usa `time.sleep` dentro da corrotina e para todos os coletores juntos. Versão com `asyncio.sleep` e trava por domínio. Medido em 17/11: o único chamador assíncrono é `scanner_capitulacao`, que roda num `asyncio.run` próprio dentro da thread de `coletar_tudo`; o `time.sleep` serializa só as tarefas desse laço (inclusive as de `query1` e `query2`, domínios diferentes), não o servidor. O dicionário `_last_request_time` também é lido e escrito sem trava pelas threads da coleta e das opiniões. | P |
| 2 | Poda | Rodada de poda com os números da 153/154 | O que sai? Depois de 10 pregões com `rodadas_pregao` (contados desde o merge da 154) e com a contagem de radares escondidos da spec 166, decidir para cada painel apontado entre remover, fundir ou mudar de forma, citando V de R. Insumo extra: sobreposição (Jaccard) das listas dos radares nos snapshots, para achar os que citam sempre as mesmas ações (as três exaustões são as candidatas óbvias). Insumo extra 2: o custo de cada painel em segundos por pregão (`tempos` × `rodadas_pregao` da instrumentação), para pesar o que um painel quase sempre vazio custa à rodada. Já sugeridos sem número: Atrasadas do Rally, Fator Peso Pesado, tabela de baixas em dia de alta ampla. | M |
| 3 | Experiência | Card Ibovespa hoje sem sobra | Na captura desktop sobram ~150 px abaixo dos gauges MM21/MM200, porque o card estica até a altura da Maré; "−10%" e "+10%" ficam longe dos gauges. Escala junto de cada gauge e a sobra ocupada pela linha de amplitude ou pelo card menor. | P |
| 4 | Saúde técnica | Teste que reprova classe sem estilo | Quantas classes dos templates não existem no CSS? A `destaque` do Clima Global é um caso (spec 160). Cruzar `class="..."` de `app/templates/` com os seletores de `app/static/*.css`, com lista de exceção para classes de JS. | P |
| 5 | Poda | Cabeçalho do celular com o pregão uma vez só | O selo do pregão e a faixa "Fechamento de ... · dados congelados" repetem a data; em 390 px o selo corta ("Fech...") e a faixa vaza. Conferir antes com a correção da #885. | P |
| 6 | Saúde técnica | Data explícita na gravação de snapshot | `gravar_snapshot` decide `estado` e `data_referencia` por `ContextVar`, o parâmetro escondido que causou o bug da spec 124. Passar o pregão como argumento e usar o pregão, não a data UTC (que vira às 21h BRT), fora do agendador. | M |
| 7 | Saúde técnica | Radares do snapshot num laço | `app/main.py` tem 2.268 linhas; `/api/snapshot` lê os 20 radares em 20 blocos quase iguais, com formas diferentes (lista, dict, objeto). `RADARES` já lista chave e campo. Primeira fatia do registro declarativo de painéis (as ~105 funções `save_*`/`get_*` de `app/database.py`), que segue em lotes. Conferir o contrato em `auditoria/README.md`. Os nomes também divergem: módulo de coletor, chave do snapshot e chave da página (`radar_short_squeeze`/`short_squeeze`, `radar_exaustao_alta`/`exaustao_alta`); a spec 166 criou `SNAPSHOT_DO_RADAR` e a #919 nasceu dessa divergência. O registro declarativo é o lugar de um nome só. | M |
| 8 | Experiência | O radar vazio diz há quanto tempo e por quê | Vazio hoje é normal para ele ou é fonte caída? Na lista de vazios da spec 150, cada nome ganha "último alerta há N pregões" e, se a fonte falhou, a última falha de `registro_fontes`. | P |
| 9 | Capacidade nova | Os sinais do sistema têm memória | Quando a Maré foi a extremo, ou uma ação esteve em 3 ou mais radares (spec 155), o que veio nos 5 pregões seguintes? Retorno médio, quantos casos e a janela, antes de qualquer leitura preditiva. Fatia 1: Maré extrema, que tem histórico desde a 027. Fatia 2: gravar a confluência no snapshot diário e mostrar com 20 pregões. Fatia 3: o par apetite aqui × lá fora, depois da 160. | G |
| 10 | Saúde técnica | Medir quanto de série a rodada baixa repetido | 41 coletores percorrem a carteira, cada um com seu pedido ao Yahoo/MT5, em série e com 2 s por domínio. Medir primeiro quanto o cache de `series_diarias` (122) e a 063 já resolvem; se não bastar, pré-carga no início da rodada que serve todos. Junta cinco ideias antigas de cache, proxy e coleta conjunta. | M a G |
| 11 | Saúde técnica | `clima_global` coleta uma vez por manhã | A janela `pre_abertura` de `_coletar` vale de 7h a 18h15, então o painel roda ~33 vezes por dia para descrever a abertura. Conferir com a spec do painel se é intencional. | P |
| 12 | Capacidade nova | O pregão gêmeo | Com que pregão do próprio histórico o dia de hoje mais se parece até agora, e o que veio depois dele? Compara a curva intraday do Ibovespa e da Maré até a mesma hora; mostra o gêmeo, a distância e quantos pregões foram comparados. Absorve "hoje vs pior dia do ano" e "E se? Joesley Day". | G |
| 13 | Capacidade nova | Radar contra radar | Há ação apontada ao mesmo tempo por um radar de alta e um de queda? O conflito vira informação de incerteza. Exige classificar cada radar por direção. Depois do item 2 (a rodada de poda), para não classificar radar que vai sair. | M |
| 14 | Experiência | "Só Sinais" começa pela confluência | A aba abre com o card da spec 155 em vez da ordem fixa. | P |
| 15 | Saúde técnica | Uma função para `/consultor` e `/api/consultor` | As duas rotas (`app/main.py:459` e `:711`) montam o mesmo histórico por caminhos separados. | M |
| 16 | Saúde técnica | Gravação de série em lote | `gravar_serie` faz um `execute` por barra; `executemany` não aparece em `app/`. | P |
| 17 | Capacidade nova | Raio-X de uma ação | Clicar num ticker mostra, sem sair da página, todos os radares em que ele está, a ficha (P/L, P/VP, DY, ROE) e eventos do dia (dividendo, desdobramento, balanço). Junta "Drill-down", "Ficha da ação", "Agrupamento de alertas por ticker" e "Tracker de eventos corporativos". | M |
| 18 | Capacidade nova | Ibovespa sombra (pesos iguais) | Como o índice estaria se cada ação pesasse o mesmo? A distância entre os dois mede quanto o dia é dos pesos pesados. Dados já coletados. | M |
| 19 | Experiência | Modo TV | Tela para monitor secundário: sem controles, fontes grandes, manchete, Ibovespa e alertas. | P |
| 20 | Capacidade nova | O placar mede o alvo que a casa declarou | O placar da 072b dá acerto por casa pelo excesso sobre o Ibovespa em 20 pregões; desde a 158 o Consultor lê a data e o alvo de cada opinião (inclusive dos canais do Telegram, 157). Quantas chegaram ao alvo dentro do prazo que a própria casa deu? Primeira fatia: só as opiniões com alvo e prazo vencido, com amostra e janela à vista. | M |
| 21 | Poda | Repositório de Ações sai dos canais | O canal mais caro se paga? É lido por ID (2 pedidos e 4 s de pausa por mensagem, até 30 por rodada) e repassa títulos de documentos da CVM que o `filtrar_materia` descarta quase todos (spec 157, "O que se espera de cada canal"). Contar, com 10 pregões de dados, quantas opiniões gravadas vieram de cada canal (coluna **Via** de `/consultor`); com zero do Repositório, ele sai de `TELEGRAM_CANAIS`. Depois da spec 164. | P |
| 22 | Experiência | O radar raro que acende vira manchete | Quando um radar que passa quase todo pregão escondido acende, é notícia? Hoje ele aparece como qualquer outro card, no meio da aba Alertas. Com a contagem `escondidos_pregao` da spec 166, o radar escondido em mais de 90% das coletas dos últimos 10 pregões que acende ganha uma linha na manchete ("Exaustão de Alta acendeu: 1ª vez em N pregões"), com N e a janela à vista. Vira o avesso da poda: o mesmo número decide o que sai e o que se destaca. Depois de 10 pregões com a 166. | P |
| 23 | Saúde técnica | O teste do agendador confere a rodada | `test_agendador_registra_tempo` (`tests/test_instrumentacao_coleta_tempo.py`) roda `_coletar()` e termina em `pass`: não reprova nada. Fixar o relógio num pregão (técnica da `tests/test_aceite_154.py`) e conferir que `gravar_instrumentacao_rodada` recebe um tempo para cada coletor que rodou. Achado na spec 168. | P |
| 24 | Poda | Plotly de 3,9 MB para desenhar linhas | Toda página baixa `plotly-strict-2.27.0.min.js` (3.918.579 bytes, medido em 17/11), e o único tipo de traço no código é `scatter` com `mode: 'lines'` (`app/static/ui.js:141` e `:150`; nenhum `type` de traço em `app/`). O pacote `plotly-basic` da mesma versão cobre scatter e barras com uma fração do tamanho. Conferir antes, nas capturas, se algum gráfico vindo do backend usa outro tipo; trocar o arquivo exige novo `integrity` (spec 170). | P |
| 25 | Experiência | O gráfico diz quando a CDN não carregou | Se o Plotly não carrega (CDN fora, ou o `integrity` da spec 170 recusou o arquivo), os contêineres dos gráficos ficam em branco, sem dizer nada. `graficos.js` testa `window.Plotly` e escreve "gráfico indisponível" no lugar, como os painéis fazem com fonte caída. | P |

## Reserva

Ideias com algum valor que não cabem na fila. Sobem quando abrir vaga; não ganham detalhe aqui.

- Estatística do próprio índice: probabilidade de o gap fechar no dia, efeito dia da semana, risco de correção pela distância da MM20, chance de nova máxima no ano.
- Rankings simples: volatilidade absoluta, maiores quedas do mês, distância da MM200, pares que andam juntos no mês.
- Mapa de calor setorial ou do índice inteiro em blocos por peso (a ideia mais repetida do histórico antigo; conferir antes o que a 123 e a 025 já mostram).
- Ibovespa em dólar (toggle no card principal).
- Simulador de rentabilidade contra o CDI.
- Modos de cor alternativos: tons de cinza (Zen / Foco no risco), contraste extremo, denso tipo terminal.
- Ocultar painéis dentro de 1 desvio padrão da média (aparece 5 vezes; esperar o item 2 da fila, que poda primeiro).
- Comparar com a mesma hora do pregão anterior (o seletor da 088 já troca o dia inteiro).
- Calendário de dividendos previsto pelo histórico anual.

## Estacionadas por falta de fonte

Dependem de dado que o sistema não tem de graça e com estabilidade. Voltam se a fonte aparecer, numa spec própria de fonte.

- **Livro de ofertas e negócios** (spread, bid/ask, iceberg, ticket médio, vácuo de liquidez, ação sem negócio). As specs 057 e 058 já usam o que a brapi entrega; o resto pede book.
- **Leilão de abertura e fechamento** (volume, preço, puxada, spoofing). A 066 cobre o que dá com barras.
- **Curva de juros intraday** (DI longo, inversão de curva, ações imunes a juros). A 042 e a 081 cobrem o que dá com dado diário.
- **Notícias e sentimento** (polaridade de manchetes, resiliência a notícias, movimento silencioso). Exigem fonte de notícias e NLP; nenhuma fonte permitida pelo `PRODUTO.md` hoje.
- **Derivativos** (skew de opções, fuga de capital em proteção) e **aluguel de ações** (BTC)
- **Cripto contra a bolsa**. A fonte existe (Yahoo), mas a pergunta não é de quem usa o produto.
- **Fluxo estrangeiro, carteiras recomendadas, consenso e dispersão de preço-alvo**: fontes de scraping instável. Consenso entra pela spec 159; dispersão de preço-alvo pode ser fatia dela.
- **Agressão por lado na Maré** (pedido do dono do produto, 05/10): sem fonte gratuita estável.

## Descartadas

- Divisão da spec 068: feita (068a, 068b).
- Tirar a contagem "de R radares lidos" da aba Alertas: R é o denominador da confluência. Rever se o card da 155 ficar vazio na maior parte das coletas.
- Compactação de cache SQLite e otimização de métricas antigas: o banco migrou para Postgres (073 a 077).
- Pool de conexões SQLite: resolvido pela 129, já em Postgres.
- Termômetro de sentimento neutro: o painel de sentimento por manchetes não existe.
