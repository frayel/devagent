# Contexto · Fontes de dados

Uma entrada por fonte. Atualize ao criar ou alterar coletor (skill `criar-coletor.md`).

## MetaTrader 5 (mt5api) · fonte preferencial

- **Uso**: barras diárias e intradiárias de ações (`PETR4`), do Ibovespa (`IBOV`) e de qualquer símbolo que a corretora publique no terminal.
- **Onde**: terminal MT5 numa máquina Windows do dono do projeto, exposto pelo servidor [mt5api](https://github.com/dceoy/mt5api). O painel usa só `GET /rates/from-pos` (leitura).
- **Autenticação**: header `X-API-Key` com `MT5_API_KEY`; endereço em `MT5_API_URL`. Sem `MT5_API_URL`, a fonte fica desligada e a coleta volta ao comportamento anterior.
- **Como entra**: `app/collectors/mt5.py` atende as URLs do Yahoo Finance (`spark` e `chart`) dentro de `fetch_with_retry`, devolvendo o mesmo JSON montado com as barras do MT5. Se o MT5 falhar, a requisição segue ao Yahoo. Ibovespa, maiores altas/baixas e concentração setorial pedem o MT5 em modo exclusivo e só depois o Yahoo.
- **Número de negócios**: o `tick_volume` da barra diária, exposto como `regularMarketTrades` quando a barra tem `real_volume` (ativo de bolsa). Sem `real_volume`, o `tick_volume` conta cotações e o campo fica nulo. É a única fonte do Termômetro de Concentração de Ordens: sem MT5, o painel mostra Dados indisponíveis.
- **Rótulo**: o painel mostra `mt5`, `mt5+yfinance` (parte de cada fonte) ou o rótulo antigo, conforme quem respondeu de fato.
- **Símbolos**: `XXXX4.SA` vira `XXXX4`; `^BVSP` vira `IBOV`; `BRL=X` vira `DOL$` (dólar futuro cheio contínuo). Outros mapeamentos em `MT5_SIMBOLOS` (JSON). Sem mapeamento, o símbolo continua vindo do Yahoo.
- **Limites**: 1 requisição a cada 2 s, como as demais fontes; barras ficam em cache por 5 min (diárias) e 2 min (intradiárias), então uma rodada faz uma chamada por símbolo. Se o servidor cair ou recusar a chave, a fonte inteira fica em pausa por 5 min. Se o terminal recusar um símbolo (a mt5api responde 503 com `MT5 last status: ...`), só aquele símbolo fica em pausa.
- **Armadilhas**: o horário das barras é o do servidor da corretora (`MT5_FUSO_SERVIDOR`, padrão `-3`). Barras diárias recebem 13:00 UTC, como no Yahoo, para a data não mudar ao converter para BRT. O nome do índice varia entre corretoras; confira em `/symbols?group=*IBOV*`. `DOL$` é futuro, não o câmbio à vista do `BRL=X`: segue o à vista mais o prêmio do contrato, e a série contínua pode saltar na virada de vencimento, o que afeta só o retorno daquele dia.

## Yahoo Finance (endpoint de chart)

- **Uso**: cotações e séries diárias quando o MT5 não responde ou não está configurado.
- **Autenticação**: nenhuma.
- **Riscos**: API não oficial, sujeita a bloqueio e a mudanças de formato sem aviso. Não dependa dela como fonte única.
- **Armadilhas**: Ao utilizar `range=1mo` no endpoint de chart, o campo `meta.chartPreviousClose` aponta para o fechamento anterior ao primeiro candle (ou seja, de cerca de um mês atrás), e não para o último fechamento do dia útil anterior. Para calcular a variação diária, deve-se extrair o penúltimo `close` da série, e utilizar os dados do `meta` como fallback secundário.
- **Maré do mercado**: `chart/^BVSP?range=2y&interval=1d` para a volatilidade (precisa de ~280 pregões; o MT5 entrega 300 barras diárias) e `spark` da cesta com `range=3mo&interval=1d` para fluxo e volume.
- **Pendência**: o coletor atual envia um User-Agent de navegador genérico; a seção 5 do `PRODUTO.md` pede um User-Agent identificável do projeto.

## Feeds RSS de portais (opiniões de casas de análise · consultor)

- **Uso**: matérias que citam recomendações, preços-alvo e carteiras de casas de análise para ações do Ibovespa (spec 070, ADR 005).
- **Feeds verificados em 2026-10-18**: Money Times (`https://www.moneytimes.com.br/feed/`, RSS 2.0 válido, com `content:encoded`; publica carteiras semanais recomendadas) e InfoMoney (`https://www.infomoney.com.br/feed/`, RSS 2.0 válido, mistura notícias de todo tipo). O feed `https://www.infomoney.com.br/mercados/feed/` veio sem itens nessa data.
- **Limites**: 1 requisição a cada 2 s por domínio, coleta a cada 30 min, só o conteúdo do próprio feed (a página da matéria não é baixada).
- **Ritmo**: não é tempo real. Algumas matérias com opinião de casa por dia, dependendo do portal.

## Gemini (extração de opiniões · consultor)

- **Uso**: só extrair registros estruturados das matérias pré-filtradas (ADR 005). Nunca decide a recomendação.
- **Acesso**: REST `generateContent`, chave em `GEMINI_API_KEY`. O modelo é descoberto pela listagem `GET /v1beta/models` (Flash-Lite estável de versão mais alta, renovado a cada 24 h ou após um 404); `GEMINI_MODELO` força um nome fixo. Ver `app/services/gemini_modelo.py`.
- **Limites**: a camada gratuita cobre os modelos Flash e Flash-Lite, mas o Google não publica os números na página de limites; eles aparecem no AI Studio e mudam sem aviso. O coletor respeita `GEMINI_MAX_CHAMADAS_DIA` e trata 429 como estado `cota`.
- **Privacidade**: na camada gratuita, o conteúdo enviado pode ser usado pelo Google para melhorar produtos. Envie só texto público das matérias.
- **Fontes**: https://ai.google.dev/gemini-api/docs/rate-limits e https://ai.google.dev/pricing

## Telegram (opiniões e notícias · consultor, spec 141)

Três canais públicos, verificados em 2026-11-04. `https://t.me/robots.txt` responde 404. Nenhum exige login.

- **Clube Acionista** (`https://t.me/s/clubeacionista`): prévia pública ativa. Cada leitura traz as 20 mensagens mais recentes, com `data-post` (ID permanente, link `https://t.me/clubeacionista/<id>`) e `<time datetime>` em UTC; mensagens anteriores com `?before=<id>`. Só texto, uma notícia curta por mensagem, quase sempre com o ticker no início (`🔔 RADL3 - ...`). Na amostra de 04/11 (20 mensagens entre 10h00 e 12h00 BRT), cerca de 3 traziam opinião atribuída a uma casa ("Ativa Investimentos recomenda COMPRA para RADL3", "Itaú Unibanco tem recomendação Neutra com alvo de R$48,00, alerta Ativa Investimentos"); o resto eram resultados do trimestre, fatos relevantes e macro. Dezenas de mensagens por hora no pregão: a coleta pagina com `before` até alcançar o último ID salvo. A casa citada no texto é a fonte da opinião, não o canal.
- **Repositório de Ações** (`https://t.me/RepositorioDeAcoes`, ~1.100 inscritos): prévia `/s/` desativada (302 para a página do canal) e o widget `?embed=1` esconde o texto. A página de cada post (`https://t.me/RepositorioDeAcoes/<id>`) traz a primeira linha em `og:description`, e `<time datetime>` vem no widget. IDs sequenciais (159.281 às 12h07 BRT de 04/11). Conteúdo: título de cada documento entregue à CVM ("RAIA DROGASIL S.A. - Comunicado ao Mercado - Apresentações a analistas", "Valores Mobiliários Negociados e Detidos", atas, FRE). Não traz opinião de casa; serve como sinal de evento corporativo. A origem real é o sistema de documentos da CVM/B3, que tem dados abertos próprios.
- **Universo Antifrágil** (`https://t.me/universoantifragil`, ~1.350 inscritos): mesmo acesso do Repositório (sem prévia, texto só pela `og:description` truncada do post). Poucas mensagens por dia (ID 3.549 em 04/11), a maioria imagem ou link para o site (`universoantifragil.com.br/fechamento-de-mercado`), com títulos como "#BBDC4 - Análise do resultado do 3T26" e "#BBSE3 - Revisão do Guidance de 2026". Opinião é do próprio canal (Prof. Paulo Sérgio Miranda), não de casa de análise; o texto disponível é curto demais para extrair recomendação na maior parte dos posts.

## Google News RSS (manchetes · consultor, spec 141)

- **Acesso**: `https://news.google.com/rss/search?q=<termos>&hl=pt-BR&gl=BR&ceid=BR:pt-419`, RSS 2.0 sem login. Verificado em 2026-11-04: busca `RADL3 recomendação` devolveu 17 itens de vários portais (InfoMoney, Suno, Seu Dinheiro, Guia do Investidor, TradingView).
- **Conteúdo útil**: só o título (`<title>`, com o portal após ` - `), `<pubDate>` e `<source>`. O `<link>` é um redirecionamento do Google e a `<description>` repete o título em HTML. Títulos como "Safra corta preço-alvo, mas ainda vê alta de 63%" e "Goldman vê oportunidade e mantém alvo de R$ 26" já nomeiam casa e direção.
- **Ordem**: os itens não vêm por data e incluem matérias de meses atrás. Use `when:7d` na busca e descarte itens com `pubDate` mais antigo que 7 dias.
- **Volume**: uma busca por ativo do Ibovespa (~85) por rodada é demais; agrupe tickers com `OR` (até ~8 por busca) e rode a cada 2 h.

## Yahoo Finance quoteSummary (consenso · consultor, spec 142)

- **Uso pretendido**: consenso de analistas por ativo (`recommendationMean`, `numberOfAnalystOpinions`, `targetMeanPrice`, `targetLowPrice`, `targetHighPrice`) dos módulos `financialData` e `recommendationTrend`.
- **Teste em 2026-11-04, a partir do container de desenvolvimento**: chamada direta sem crumb devolveu 429; pelo `yfinance` (que obtém cookie e crumb) devolveu 401 `Invalid Crumb` e `User is unable to access this feature` para RADL3, ITUB4 e PETR4. Não há dado confirmado. O endpoint `v8/finance/chart`, já usado pelo painel, é outro e segue funcionando.
- **Risco**: o Yahoo restringe esse endpoint a IPs de datacenter e muda o mecanismo de crumb sem aviso. Precisa ser testado a partir do Render antes de contar com ele.

## Fontes antes vetadas por `robots.txt`

Desde 04/11/2026 o `robots.txt` não bloqueia fontes (`PRODUTO.md`, seção 5). Yahoo `quoteSummary` e Google News RSS, barrados em 2026-10-18 só por isso, estão registrados acima.

## Fontes proibidas

- **Relatórios de corretoras e casas de análise**: atrás de login.

## Fontes descontinuadas

- **brapi.dev** (removida em 04/11/2026): era reserva de vários painéis e fonte única do número de negócios. O plano gratuito não aceitava vários ativos por chamada, a cota mensal não cobria uma chamada por ativo, e as falhas síncronas travaram a produção em 04/11. O MT5 cobre o que ela entregava.
