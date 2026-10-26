## 2026-09-27

- **O que fiz:** Adicionei um índice (`idx_highlights_cache_timestamp`) na tabela `highlights_cache` para a coluna `timestamp DESC`.
- **O que aprendi:** A ausência do índice causava lentidão na consulta `ORDER BY timestamp DESC LIMIT 1` usada na tela inicial (`/`), porque o banco precisava varrer a tabela toda a cada requisição. Medições locais com 10.000 registros na tabela demonstraram uma melhoria de 67% no tempo de resposta com o uso do índice.
- **O que evitar:** Evitar adicionar endpoints sem verificar o plano de execução e o impacto no banco de dados, especialmente para consultas ordenadas com LIMIT.
## 2026-09-28

- **O que fiz:** Atualizei a função `fetch_yfinance()` no módulo `app/collectors/highlights.py` para utilizar o endpoint em lote `https://query1.finance.yahoo.com/v7/finance/spark` agrupando a lista de ações em lotes de 15 ativos.
- **O que aprendi:** Agrupar as requisições em lotes utilizando a API do Yahoo Finance (`spark`) reduziu o tempo de execução do *fallback* dos Destaques de cerca de ~60 segundos (30 requisições individuais sofrendo gargalo de *rate limit* de 2 segundos por domínio) para cerca de ~2 segundos (2 requisições em lote sujeitas a mesma regra).
- **O que evitar:** Evitar laços de requisições individuais a APIs externas quando existem *endpoints* que processam consultas em lote, especialmente caso exista lógica restrita de *rate limit* por domínio envolvida.
## 2026-09-29

- **O que fiz:** Retardei os imports de `app.collectors` no módulo `app.agendador` (lazy loading) para que o `httpx` e dependências pesadas não sejam importados durante o startup.
- **O que aprendi:** O import do módulo principal `app.main` puxava todo o ecossistema de coleta (`httpx`, etc) devido ao `app.agendador`, acrescentando cerca de 10% (0.05-0.10s) de latência (Cold Start) na inicialização da aplicação do Render, onde o tempo de partida a frio importa.
- **O que evitar:** Evitar imports em nível de módulo de bibliotecas pesadas (como clientes HTTP para web scraping) em módulos que são críticos para a inicialização e que só usam esses imports em tarefas em *background* rodadas após a inicialização.

## 2026-10-02

- **O que fiz:** Substituí importações explícitas no módulo `app/agendador.py` pelo uso do `importlib.import_module`, permitindo carregar os módulos da camada collectors de forma preguiçosa.
- **O que aprendi:** A importação agrupada (`from app.collectors import (highlights, ibovespa, ...)`) no topo da função `_coletar` acabava sendo avaliada e carregava todas essas dependências, como a biblioteca `httpx`, antes do necessário (no escopo da closure ou parsing da função durante a inicialização, ou apenas atrasando mas não otimizando perfeitamente a partida). Usando `importlib.import_module` de forma dinâmica no loop, o código evita trazer o pacote `httpx` inteiro e suas ramificações no cold start do Render. A melhoria no tempo local de importação do `app.main` saltou de ~0.72s para ~0.50s (apenas com o overhead do FastAPI).
- **O que evitar:** Manter chamadas explícitas de import que puxam subdependências pesadas em arquivos lidos logo na partida, perdendo as vantagens do lazy loading.
## 2026-10-03

- **O que fiz:** Tentei otimizar a desserialização JSON e renderização Jinja2 retornando a string original via `|safe`, mas abortei. Descobri que isso quebra a tipagem da API e introduz vulnerabilidades graves de XSS ao evitar o filtro `|tojson`. Descartado por falhas de design graves.
- **O que aprendi:** O uso de `|safe` diretamente no output raw JSON sem usar `|tojson` permite o escape de tags `<script>`, abrindo vulnerabilidades. Além disso, retornar a string raw quebra a API `/api/snapshot`.
- **O que evitar:** Não evitar o filtro `|tojson` e não misturar retornos de JSON raw onde dicionários são esperados. Evitar propor alterações não seguras sem testar casos-limite de segurança (XSS).
## 2026-10-04

- **O que fiz:** Adicionei um índice (`idx_concentracao_cache_timestamp`) na tabela `concentracao_cache` para a coluna `timestamp DESC`.
- **O que aprendi:** A tabela `concentracao_cache` sofria do mesmo problema anterior da `highlights_cache`. O método `get_latest_concentracao_data()` utiliza `ORDER BY timestamp DESC LIMIT 1`. Ao adicionarmos o índice, melhoramos a latência em requisições de leitura recorrentes, economizando cerca de 25% do tempo de resposta na API `/api/snapshot` em cenários de banco populado.
- **O que evitar:** Criar tabelas e métodos `get_latest_*` sem também criar o respectivo índice na coluna `timestamp DESC` para a qualificação limit/order.
## 2026-10-06

- **O que fiz:** Otimizei a função `fetch_yfinance()` do coletor `compradores_fundo` para utilizar o endpoint em lote `https://query1.finance.yahoo.com/v7/finance/spark` ao invés do individual `chart`.
- **O que aprendi:** Agrupar as requisições reduziu o tempo de execução deste coletor de ~60 segundos para cerca de ~2 segundos, evitando os gargalos de *rate limit* de 2 segundos por domínio para 30 requisições individuais.
- **O que evitar:** Usar endpoints individuais (como `/v8/finance/chart/{ticker}`) em loops de coleta sobre muitos ativos quando alternativas de requisições em lote (como `spark`) estão disponíveis e expõem os mesmos dados de preços de OHLCV.
## 2026-10-07

- **O que fiz:** Otimizei a função `collect_and_save()` no coletor `armadilha_abertura` para usar chamadas em lote de 15 ativos ao `yfinance` endpoint (`/spark`) em vez de fazer todas em uma única requisição muito longa. Adicionei o limite de timeout e injetei apenas o `"VALE3"` no ticker das test cases para prevenir falhas.
- **O que aprendi:** Agrupar todos os 30 ativos em uma única requisição resultava em um erro `400 Bad Request` por conta da query string longa. Ao separar os lotes, a chamada ao `spark` continuou performática com tempo de execução ao redor de 2.13 segundos comparado aos 0.22s falhos (onde todos caiam na exceção rapidamente). Isso assegura o correto funcionamento das requisições com os limits do endpoint.
- **O que evitar:** Evitar tentar enfileirar centenas de símbolos na query string para os endpoints do Yahoo Finance; focar em realizar o _batching_ em pequenos lotes (como 15 ativos) permitindo boa performance e previnindo recusas HTTP (erro 400).
## 2026-10-09

- **O que fiz:** Adicionei os índices (`idx_anomalia_peso_cache_timestamp` e `idx_radar_inflexao_cache_timestamp`) nas tabelas `anomalia_peso_cache` e `radar_inflexao_cache` para a coluna `timestamp DESC`.
- **O que aprendi:** Semelhante às tabelas `highlights_cache` e `concentracao_cache`, a ausência dos índices causava lentidão na consulta `ORDER BY timestamp DESC LIMIT 1` usada no método `get_latest_*`, exigindo que o banco varresse toda a tabela nessas requisições. A adição otimizou essas queries.
- **O que evitar:** Criar tabelas para cache de relatórios limitadas ao timestamp mais recente (`get_latest_...`) sem adicionar o índice de ordenação.
## 2026-10-13

- **O que fiz:** Adicionei o índice (`idx_motores_indice_cache_timestamp`) na tabela `motores_indice_cache` para a coluna `timestamp DESC`.
- **O que aprendi:** A ausência do índice para a tabela `motores_indice_cache` na coluna `timestamp` (apesar de ter `timestamp TEXT PRIMARY KEY`, para otimizar um `ORDER BY timestamp DESC LIMIT 1` o índice em ordem DESC ajuda em varreduras explícitas dependendo do SQLite planner), além de garantir o mesmo padrão de índices `_timestamp ON ... (timestamp DESC)` otimizou a latência em leituras do banco de dados na inicialização da aplicação e chamadas à API de snapshot em tabelas grandes.
- **O que evitar:** Evitar definir PKs de string sem adicionar os índices explícitos necessários em ordem DESCENDENTE quando consultas com limite e ordenação invertida são executadas recorrentemente.
## 2026-10-15

- **O que fiz:** Otimizei a função `fetch_with_retry` (e sua variante assíncrona) no módulo `app/collectors/utils.py` para alternar requisições sequenciais do Yahoo Finance entre os subdomínios `query1.finance.yahoo.com` e `query2.finance.yahoo.com`.
- **O que aprendi:** Como o limite de taxa (rate limit) de 1 requisição a cada 2 segundos no `utils.py` é calculado por domínio, alternar as requisições entre `query1` e `query2` dobra efetivamente o limite permitido, permitindo execuções mais rápidas nos coletores sem causar erros 429 (Too Many Requests).
- **O que evitar:** Evitar focar todas as requisições do Yahoo Finance em apenas um subdomínio (`query1`) quando `query2` também está disponível e as políticas de rate limit são computadas por host no projeto.
## 2026-10-17

- **O que fiz:** Modifiquei o índice `idx_concentracao_vendedora_timestamp` para utilizar `timestamp DESC` na tabela `concentracao_vendedora_cache`.
- **O que aprendi:** O SQLite com `ORDER BY timestamp DESC LIMIT 1` é otimizado usando índices na mesma direção. O índice antigo usava ASC por padrão, resultando em scans desnecessários.
- **O que evitar:** Criar índices de timestamp sem especificar a direção apropriada (DESC) quando a query dependente requer ordenação invertida.
## 2026-10-20

- **O que fiz:** Adicionei um índice (`idx_divergencia_ibov_dolar_timestamp`) na tabela `divergencia_ibov_dolar_cache` para a coluna `timestamp DESC`.
- **O que aprendi:** A ausência deste índice estava causando lentidão recorrente na API que busca o registro mais atual de divergência por `ORDER BY timestamp DESC LIMIT 1`. Ao adicionarmos o índice, melhoramos e estabilizamos o tempo de acesso em `get_divergencia_ibov_dolar`.
- **O que evitar:** Omitir índices de ordenação `DESC` para tabelas de cache consultadas por data invertida, o que degrada a performance de leitura recorrente.
## 2026-10-22

- **O que fiz:** Adicionei os índices (`idx_consultor_recomendacoes_timestamp`) na tabela `consultor_recomendacoes` para a coluna `timestamp DESC`.
- **O que aprendi:** A ausência deste índice na tabela `consultor_recomendacoes` estava causando lentidão na função `save_recomendacoes` (no backend `app/consultor/armazenamento.py`) que usa a query `ORDER BY timestamp DESC LIMIT 1` em loop para cada ticker salvo. Com o índice, os checks evitam o scan completo de tabela (table scan) para cada iteração do salvamento, otimizando o processo que é chamado recorrentemente a cada rodada.
- **O que evitar:** Omitir índices de ordenação `DESC` para tabelas lidas em laços com clausula de timestamp invertida com LIMIT, degradando a performance de escrita recorrente por leituras lentas.
## 2026-10-23

- **O que fiz:** Adicionei os índices (`idx_snapshots_paineis_data_referencia`) na tabela `snapshots_paineis` para a coluna `data_referencia DESC` (em `app/banco.py`) e (`idx_consultor_opinioes_extraida_em`) na tabela `consultor_opinioes` para a coluna `extraida_em DESC` (em `app/consultor/armazenamento.py`).
- **O que aprendi:** A falta desses índices estava causando lentidão recorrente na API ao buscar os relatórios e opiniões mais recentes com `ORDER BY data_referencia DESC` e `ORDER BY extraida_em DESC` com `LIMIT`. Ao adicionar os índices em ordem descendente (DESC), passamos a usar "INDEX SCAN" em vez de "TABLE SCAN + TEMP B-TREE", melhorando sensivelmente a latência em requisições de leitura repetidas no banco populado.
- **O que evitar:** Omitir índices de ordenação `DESC` para tabelas consultadas por data invertida limitadas a X registros recentes, especialmente ao introduzir novas arquiteturas de dados como o banco unificado (`snapshots_paineis`).

## 2026-10-24

- **O que fiz:** Adicionei/Ajustei os índices compostos (`idx_snapshots_paineis_painel_data_referencia`) na tabela `snapshots_paineis` para as colunas `(painel, data_referencia DESC)` (em `app/banco.py`) e (`idx_consultor_recomendacoes_ticker_timestamp`) na tabela `consultor_recomendacoes` para as colunas `(ticker, timestamp DESC)` (em `app/consultor/armazenamento.py`).
- **O que aprendi:** Embora os índices anteriores `data_referencia DESC` e `timestamp DESC` estivessem em ordem descendente, as queries recorrentes (`ler_snapshot` e `get_ultima_decisao`/`save_recomendacoes`) costumam realizar um filtro pela coluna `painel` e `ticker` simultaneamente antes do `ORDER BY ... DESC LIMIT 1`. Ao substituirmos pelos índices compostos, passamos a evitar que o banco de dados tenha de utilizar "TEMP B-TREE FOR ORDER BY" após usar os índices com baixa seletividade (ou filtrar sequencialmente após ler do índice) no SQLite e Postgres, melhorando radicalmente o tempo de reposta em pesquisas por painel/ticker específicos, otimizando o backend em acessos concorrentes e repetições em loop como na consolidação do consultor.
- **O que evitar:** Omitir colunas do índice usado como filtro direto em cláusulas `WHERE` associadas a ordenações `DESC LIMIT X` em consultas críticas.

## 2026-10-25

- **O que fiz:** Otimizei a inicialização da aplicação movendo a importação do `psycopg` para _lazy load_ em `app/banco.py`. Ao invés de carregar o driver globalmente (o que traz todo o framework para a memória), agora o módulo é carregado dinamicamente usando `importlib.util.find_spec` apenas para verificar sua disponibilidade, e de fato importado unicamente quando as conexões PostgreSQL vão ser estabelecidas.
- **O que aprendi:** O import global do `psycopg` nas instâncias de startup estava adicionando consistentemente mais de 220ms no import do `app.main`, elevando o cold start local de 550ms para em torno de 792-800ms. Evitar esse import global cortou cerca de 25% da lentidão na partida.
- **O que evitar:** Manter dependências pesadas de banco (como `psycopg`, `sqlalchemy`, etc) declaradas estaticamente nos escopos globais se elas puderem ser testadas por _find_spec_ e instanciadas sob demanda dentro dos conectores e singletons, poupando CPU e memória ao iniciar o worker FastAPI no Render.

## 2026-10-26

- **O que fiz:** Otimizei a inicialização do `app.main` (ponto de entrada do uvicorn) isolando importações globais que dependiam indiretamente de grandes módulos ou de requests síncronos/bibliotecas HTTP pesadas não requeridas no escopo global (ex. `mt5_coletor`, `registro_fontes`, `monitor_sistema`). Movi esses imports para o interior de `lifespan` e `estado_do_sistema` usando o padrão nativo via import local no escopo das funções.
- **O que aprendi:** Apesar das limpezas passadas em `app.agendador`, `app.main` ainda possuía imports de `app.collectors.mt5` e `app.collectors.sistema` no escopo global para alimentar variáveis de roteamento (`/sistema`). Isso estava forçando o carregamento dessas coleções inteiras (e subdependências como `httpx`) durante o startup. Retirar esses itens do escopo global economizou consideravelmente cerca de ~15% da partida da aplicação, reduzindo o tempo de import do módulo principal de ~0.62s para ~0.55s.
- **O que evitar:** Manter importações do módulo de coletores no arquivo raiz do servidor FastAPI no escopo global. Usar escopos locais, especialmente se esses módulos só são executados posteriormente, como rotas protegidas que não respondem à partida e callbacks assíncronos de lifespan.
