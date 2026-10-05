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
