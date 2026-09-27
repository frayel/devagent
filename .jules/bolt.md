## 2026-09-27

- **O que fiz:** Adicionei um índice (`idx_highlights_cache_timestamp`) na tabela `highlights_cache` para a coluna `timestamp DESC`.
- **O que aprendi:** A ausência do índice causava lentidão na consulta `ORDER BY timestamp DESC LIMIT 1` usada na tela inicial (`/`), porque o banco precisava varrer a tabela toda a cada requisição. Medições locais com 10.000 registros na tabela demonstraram uma melhoria de 67% no tempo de resposta com o uso do índice.
- **O que evitar:** Evitar adicionar endpoints sem verificar o plano de execução e o impacto no banco de dados, especialmente para consultas ordenadas com LIMIT.
