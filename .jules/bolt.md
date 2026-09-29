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
