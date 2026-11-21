# Backlog

Uma lista só, em ordem de prioridade. Consolidada em 15/11/2026 a partir de 318 linhas espalhadas por 52 seções de ideias e uma tabela de features; o mapa do que saiu e por quê está em `docs/runs/2026-11-15-2056.md`.

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
| 3 | Saúde técnica | Teste que reprova classe sem estilo | Quantas classes dos templates não existem no CSS? Medido em 19/11: 43 de 187 (sem seletor e sem uso no JS). A fatia 1 (o teste que reprova classe nova, com as 43 numa lista que só encolhe) é a spec 187. A fatia 2 (Anomalias de Spread, Falso Rompimento e Divergência Volume/Preço em `tabela_ativos`, `variacao` e `estado`, 11 classes a menos) é a spec 188. A fatia 3 (as 7 do `/consultor`: os `badge-*` viram `selo ok`/`selo atencao`, 32 → 25) é a spec 189. Resta zerar as outras 25: o `aviso-dados`/`aviso-legal`/`espacador-direita` do `base.html`, `checagem-corpo` de `sistema.html`, `mare-sem-curva` e `selo-desatualizado` de `componentes.html` e as 19 de `index.html` (`manchete-container`, `kpi-group`, `selo-revisao`...). Nota de 20/11: a cor fixa por coluna dos dois radares não contradiz o sinal hoje (os coletores só gravam preço em queda e volume em alta no Falso Rompimento, e o contrário na Divergência); o defeito é a falta de estilo. | P |
| 4 | Poda | Cabeçalho do celular com o pregão uma vez só | O selo do pregão e a faixa "Fechamento de ... · dados congelados" repetem a data; em 390 px o selo corta ("Fech...") e a faixa vaza. Conferir antes com a correção da #885. | P |
| 5 | Saúde técnica | Data explícita na gravação de snapshot | `gravar_snapshot` decide `estado` e `data_referencia` por `ContextVar`, o parâmetro escondido que causou o bug da spec 124. Passar o pregão como argumento e usar o pregão, não a data UTC (que vira às 21h BRT), fora do agendador. | M |
| 6 | Saúde técnica | Radares do snapshot num laço | `app/main.py` tem 2.448 linhas e `snapshot` sozinha ~860 (medido em 18/11); `/api/snapshot` lê os 20 radares em 20 blocos quase iguais, com formas diferentes (lista, dict, objeto). A fatia 1 (os 8 radares de molde idêntico num laço, sem mudar o JSON) é a spec 184. Resta: os 12 radares de forma própria, que pedem decidir o contrato antes de unificar, e o registro declarativo de painéis (as ~105 funções `save_*`/`get_*` de `app/database.py`), que segue em lotes. Conferir o contrato em `auditoria/README.md`. Os nomes também divergem: módulo de coletor, chave do snapshot e chave da página (`radar_short_squeeze`/`short_squeeze`, `radar_exaustao_alta`/`exaustao_alta`); a spec 166 criou `SNAPSHOT_DO_RADAR` e a #919 nasceu dessa divergência. O registro declarativo é o lugar de um nome só. | M |
| 7 | Experiência | O radar vazio diz há quanto tempo e por quê | Vazio hoje é normal para ele ou é fonte caída? A fatia 1 ("último alerta há N pregões" nos nomes da seção "Sem alertas", a partir de `escondidos_pregao` da 166) é a spec 185. Resta: o radar indisponível mostrar a última falha da fonte em `registro_fontes`. | P |
| 8 | Capacidade nova | Os sinais do sistema têm memória | Quando a Maré foi a extremo, ou uma ação esteve em 3 ou mais radares (spec 155), o que veio nos 5 pregões seguintes? Retorno médio, quantos casos e a janela, antes de qualquer leitura preditiva. A fatia 1 (Maré, Ibovespa 5 pregões depois de cada faixa) é a spec 183. A fatia 2a (guardar a confluência de cada pregão fechado, com os até 30 pregões que o banco ainda tem) é a spec 186. Fatia 2b: o que as ações em 3 ou mais radares fizeram nos 5 pregões seguintes, com 20 pregões guardados. Fatia 3: o par apetite aqui × lá fora, depois da 160. | G |
| 9 | Saúde técnica | Medir quanto de série a rodada baixa repetido | 41 coletores percorrem a carteira, cada um com seu pedido ao Yahoo/MT5, em série e com 2 s por domínio. Medir primeiro quanto o cache de `series_diarias` (122) e a 063 já resolvem; se não bastar, pré-carga no início da rodada que serve todos. Junta cinco ideias antigas de cache, proxy e coleta conjunta. | M a G |
| 10 | Saúde técnica | `clima_global` coleta uma vez por manhã | A janela `pre_abertura` de `_coletar` vale de 7h a 18h15, então o painel roda ~33 vezes por dia para descrever a abertura. Conferir com a spec do painel se é intencional. | P |
| 11 | Capacidade nova | O pregão gêmeo | Com que pregão do próprio histórico o dia de hoje mais se parece até agora, e o que veio depois dele? Compara a curva intraday do Ibovespa e da Maré até a mesma hora; mostra o gêmeo, a distância e quantos pregões foram comparados. Absorve "hoje vs pior dia do ano" e "E se? Joesley Day". | G |
| 12 | Capacidade nova | Radar contra radar | Há ação apontada ao mesmo tempo por um radar de alta e um de queda? O conflito vira informação de incerteza. Exige classificar cada radar por direção. Depois do item 2 (a rodada de poda), para não classificar radar que vai sair. | M |
| 13 | Experiência | "Só Sinais" começa pela confluência | A aba abre com o card da spec 155 em vez da ordem fixa. | P |
| 14 | Saúde técnica | Uma função para `/consultor` e `/api/consultor` | As duas rotas (`app/main.py:459` e `:711`) montam o mesmo histórico por caminhos separados. Medido em 21/11: o ramo histórico de `/consultor` faz 4 consultas a `consultor_fechamentos` por recomendação (a lista de datas e três preços, dentro do laço), o de `/api/consultor` faz 2 no total; com as ~80 recomendações de um pregão, são ~320 consultas por página. A versão única usa a de 2. | M |
| 15 | Capacidade nova | Raio-X de uma ação | Clicar num ticker mostra, sem sair da página, todos os radares em que ele está, a ficha (P/L, P/VP, DY, ROE) e eventos do dia (dividendo, desdobramento, balanço). Junta "Drill-down", "Ficha da ação", "Agrupamento de alertas por ticker" e "Tracker de eventos corporativos". | M |
| 16 | Capacidade nova | Ibovespa sombra (pesos iguais) | Como o índice estaria se cada ação pesasse o mesmo? A distância entre os dois mede quanto o dia é dos pesos pesados. Dados já coletados. | M |
| 17 | Experiência | Modo TV | Tela para monitor secundário: sem controles, fontes grandes, manchete, Ibovespa e alertas. | P |
| 18 | Capacidade nova | O placar mede o alvo que a casa declarou | Quantas opiniões de cada casa chegaram ao alvo? O "placar da 072b" que este item citava nunca chegou à tela e saiu como código sem uso no #993 (19/11); de `app/consultor/placar.py` restou só `_calcular_excesso`. A fatia 1 (cada opinião da lista Opiniões Recentes diz "atingido em dd/mm" ou "faltam +X%", contra os fechamentos de `consultor_fechamentos`) é a spec 190. Resta: o placar por casa (taxa de alvos atingidos, tempo mediano até o alvo, amostra e janela à vista, mínimo de opiniões por casa), que pede ler opiniões além dos 30 dias da lista; o prazo declarado pela casa, que o Gemini ainda não extrai. | M |
| 19 | Poda | Repositório de Ações sai dos canais | O canal mais caro se paga? É lido por ID (2 pedidos e 4 s de pausa por mensagem, até 30 por rodada) e repassa títulos de documentos da CVM que o `filtrar_materia` descarta quase todos (spec 157, "O que se espera de cada canal"). Contar, com 10 pregões de dados, quantas opiniões gravadas vieram de cada canal (coluna **Via** de `/consultor`); com zero do Repositório, ele sai de `TELEGRAM_CANAIS`. Depois da spec 164. | P |
| 20 | Experiência | O radar raro que acende vira manchete | Quando um radar que passa quase todo pregão escondido acende, é notícia? Hoje ele aparece como qualquer outro card, no meio da aba Alertas. Com a contagem `escondidos_pregao` da spec 166, o radar escondido em mais de 90% das coletas dos últimos 10 pregões que acende ganha uma linha na manchete ("Exaustão de Alta acendeu: 1ª vez em N pregões"), com N e a janela à vista. Vira o avesso da poda: o mesmo número decide o que sai e o que se destaca. Depois de 10 pregões com a 166. | P |
| 21 | Poda | CSS sem uso sai do tema | O que do `tema.css` nenhum template nem JS usa? Medido em 19/11: 19 dos 180 seletores de classe não aparecem literalmente em `app/` (`d-block`, `m-t-2`, `pilha`, `tabela-scroll`, `texto-num`, `painel-rotacao`, `painel-tendencia`, `painel-estado-container`, `novidade-correcao`...); parte é dinâmica (`g-cor-N`, `span-N`, `novidade-{{ tipo }}`) e fica. O avesso da spec 187: o mesmo extrator decide o que sai. | P |
| 22 | Experiência | A composição do Ibovespa também envelhece | O selo "Composição do Ibovespa" de `/consultor` diz sempre "Atualizado": `CARTEIRA_CONFERIDA_EM` (`app/consultor/universo.py`) é uma constante, sem regra de defasagem. A B3 troca a carteira teórica a cada quatro meses (janeiro, maio, setembro); depois da primeira segunda-feira de uma vigência nova sem conferência, o selo passa a "Defasado" com a frase do motivo. Visto ao escrever a spec 189. | P |
| 23 | Experiência | Preço-alvo no padrão brasileiro | O resumo de cada ativo em Opiniões Recentes escreve `R$ 45.00` (ponto decimal, `"%.2f"` da spec 165) e a coluna Preço-Alvo do detalhe mostra o valor cru do banco (`45.0` ou `R$ 45,00`, conforme a época da extração), contra a convenção da seção 7 do `PRODUTO.md`. Visto nas capturas de `make telas` de 21/11. Um filtro de reais só, usado nos dois lugares. | P |
| 24 | Capacidade nova | A casa fora da curva | O alvo desta casa está dentro da faixa do consenso do Yahoo (`alvo_minimo`–`alvo_maximo`, spec 159) ou fora dela? Uma casa isolada acima do máximo é informação; cruzamento que os concorrentes não mostram por opinião. Depois da 190, na mesma coluna de método. Depende do Yahoo, hoje em pausa por HTTP 429 em parte do dia. | M |

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
