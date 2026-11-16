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
| 1 | Saúde técnica | Rate limit sem travar o loop | `async_fetch_with_retry` chama `_enforce_rate_limit` (`app/collectors/utils.py:175`), que usa `time.sleep` dentro da corrotina e para todos os coletores juntos. Versão com `asyncio.sleep` e trava por domínio. | P |
| 2 | Saúde técnica | Scripts de CDN com integridade | `base.html` carrega htmx (unpkg) e Plotly (cdn.plot.ly) sem `integrity`, e o CSP libera os dois domínios. Fixar hash ou servir de `app/static`. | P |
| 3 | Saúde técnica | Registrar o painel escondido por lista vazia | O critério de poda do `PRODUTO.md` conta "sem dados **ou escondido**", mas a 153/154 só contam fonte que não respondeu; a classe `.escondido` não deixa rastro. Gravar, na gravação única da 152, as chaves de `/api/snapshot` que saíram vazias. Pré-requisito do item 4. | P |
| 4 | Poda | Rodada de poda com os números da 153/154 | O que sai? Depois de 10 pregões com `rodadas_pregao` (contados desde o merge da 154) e com o item 3, decidir para cada painel apontado entre remover, fundir ou mudar de forma, citando V de R. Insumo extra: sobreposição (Jaccard) das listas dos radares nos snapshots, para achar os que citam sempre as mesmas ações (as três exaustões são as candidatas óbvias). Já sugeridos sem número: Atrasadas do Rally, Fator Peso Pesado, tabela de baixas em dia de alta ampla. | M |
| 5 | Experiência | "O que se destaca hoje" acima da dobra | A segunda pergunta do produto (quais ações se destacam) tem resposta sem trocar de aba? Na Visão Geral não aparece nome de ação até o rodapé (`make telas`, 15/11). Faixa com maior alta, maior baixa e a ação em mais radares (spec 155) logo abaixo da manchete. | M |
| 6 | Experiência | Card Ibovespa hoje sem sobra | Na captura desktop sobram ~150 px abaixo dos gauges MM21/MM200, porque o card estica até a altura da Maré; "−10%" e "+10%" ficam longe dos gauges. Escala junto de cada gauge e a sobra ocupada pela linha de amplitude ou pelo card menor. | P |
| 7 | Saúde técnica | Teste que reprova classe sem estilo | Quantas classes dos templates não existem no CSS? A `destaque` do Clima Global é um caso (spec 160). Cruzar `class="..."` de `app/templates/` com os seletores de `app/static/*.css`, com lista de exceção para classes de JS. | P |
| 8 | Poda | Cabeçalho do celular com o pregão uma vez só | O selo do pregão e a faixa "Fechamento de ... · dados congelados" repetem a data; em 390 px o selo corta ("Fech...") e a faixa vaza. Conferir antes com a correção da #885. | P |
| 9 | Poda | Tabela `instrumentacao_coleta_tempo` | Só `init_db` a cria (`app/database.py:288`); nenhuma gravação no código depois da 152. Uma tabela e um índice a menos. | P |
| 10 | Saúde técnica | Data explícita na gravação de snapshot | `gravar_snapshot` decide `estado` e `data_referencia` por `ContextVar`, o parâmetro escondido que causou o bug da spec 124. Passar o pregão como argumento e usar o pregão, não a data UTC (que vira às 21h BRT), fora do agendador. | M |
| 11 | Saúde técnica | Radares do snapshot num laço | `app/main.py` tem 2.268 linhas; `/api/snapshot` lê os 20 radares em 20 blocos quase iguais, com formas diferentes (lista, dict, objeto). `RADARES` já lista chave e campo. Primeira fatia do registro declarativo de painéis (as ~105 funções `save_*`/`get_*` de `app/database.py`), que segue em lotes. Conferir o contrato em `auditoria/README.md`. | M |
| 12 | Experiência | O radar vazio diz há quanto tempo e por quê | Vazio hoje é normal para ele ou é fonte caída? Na lista de vazios da spec 150, cada nome ganha "último alerta há N pregões" e, se a fonte falhou, a última falha de `registro_fontes`. | P |
| 13 | Capacidade nova | Os sinais do sistema têm memória | Quando a Maré foi a extremo, ou uma ação esteve em 3 ou mais radares (spec 155), o que veio nos 5 pregões seguintes? Retorno médio, quantos casos e a janela, antes de qualquer leitura preditiva. Fatia 1: Maré extrema, que tem histórico desde a 027. Fatia 2: gravar a confluência no snapshot diário e mostrar com 20 pregões. Fatia 3: o par apetite aqui × lá fora, depois da 160. | G |
| 14 | Saúde técnica | Medir quanto de série a rodada baixa repetido | 41 coletores percorrem a carteira, cada um com seu pedido ao Yahoo/MT5, em série e com 2 s por domínio. Medir primeiro quanto o cache de `series_diarias` (122) e a 063 já resolvem; se não bastar, pré-carga no início da rodada que serve todos. Junta cinco ideias antigas de cache, proxy e coleta conjunta. | M a G |
| 15 | Saúde técnica | `clima_global` coleta uma vez por manhã | A janela `pre_abertura` de `_coletar` vale de 7h a 18h15, então o painel roda ~33 vezes por dia para descrever a abertura. Conferir com a spec do painel se é intencional. | P |
| 16 | Saúde técnica | Duração de parede da rodada | "Duração da coleta" de `/sistema` soma só `collect_and_save`, sem leituras de controle nem instrumentação. O número passa a incluir o custo do banco. Junto: `get_tempos_coleta_desde` ignora o `desde` (rótulo "24 h") e lê só o dia BRT; a spec 161 corrigiu os vazios e deixou este de fora. | P |
| 17 | Capacidade nova | O pregão gêmeo | Com que pregão do próprio histórico o dia de hoje mais se parece até agora, e o que veio depois dele? Compara a curva intraday do Ibovespa e da Maré até a mesma hora; mostra o gêmeo, a distância e quantos pregões foram comparados. Absorve "hoje vs pior dia do ano" e "E se? Joesley Day". | G |
| 18 | Capacidade nova | Radar contra radar | Há ação apontada ao mesmo tempo por um radar de alta e um de queda? O conflito vira informação de incerteza. Exige classificar cada radar por direção. Depois do item 4, para não classificar radar que vai sair. | M |
| 19 | Experiência | "Só Sinais" começa pela confluência | A aba abre com o card da spec 155 em vez da ordem fixa. | P |
| 20 | Saúde técnica | Uma função para `/consultor` e `/api/consultor` | As duas rotas (`app/main.py:459` e `:711`) montam o mesmo histórico por caminhos separados. | M |
| 21 | Saúde técnica | Gravação de série em lote | `gravar_serie` faz um `execute` por barra; `executemany` não aparece em `app/`. | P |
| 22 | Capacidade nova | Raio-X de uma ação | Clicar num ticker mostra, sem sair da página, todos os radares em que ele está, a ficha (P/L, P/VP, DY, ROE) e eventos do dia (dividendo, desdobramento, balanço). Junta "Drill-down", "Ficha da ação", "Agrupamento de alertas por ticker" e "Tracker de eventos corporativos". | M |
| 23 | Capacidade nova | Ibovespa sombra (pesos iguais) | Como o índice estaria se cada ação pesasse o mesmo? A distância entre os dois mede quanto o dia é dos pesos pesados. Dados já coletados. | M |
| 24 | Experiência | Modo TV | Tela para monitor secundário: sem controles, fontes grandes, manchete, Ibovespa e alertas. | P |

## Reserva

Ideias com algum valor que não cabem na fila. Sobem quando abrir vaga; não ganham detalhe aqui.

- Estatística do próprio índice: probabilidade de o gap fechar no dia, efeito dia da semana, risco de correção pela distância da MM20, chance de nova máxima no ano.
- Rankings simples: volatilidade absoluta, maiores quedas do mês, distância da MM200, pares que andam juntos no mês.
- Mapa de calor setorial ou do índice inteiro em blocos por peso (a ideia mais repetida do histórico antigo; conferir antes o que a 123 e a 025 já mostram).
- Ibovespa em dólar (toggle no card principal).
- Simulador de rentabilidade contra o CDI.
- Modos de cor alternativos: tons de cinza (Zen / Foco no risco), contraste extremo, denso tipo terminal.
- Ocultar painéis dentro de 1 desvio padrão da média (aparece 5 vezes; esperar o item 5 da fila, que poda primeiro).
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
