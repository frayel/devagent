# Backlog

## Correções (prioridade sobre qualquer feature)

### Painel exibe dado de teste em produção (Ibovespa 130.000 pontos)

**Sintoma:** a página inicial mostra "Ibovespa hoje: 130.000 pontos", com histórico de três dias em 2023 (25/09 a 27/09). O valor real do índice em 26/09/2026 está perto de 183.476 pontos.

**Causa raiz (quatro falhas combinadas):**

1. **O valor vem do fixture.** `tests/fixtures/brapi_response.json` tem `regularMarketPrice: 130000.5` e o histórico de 2023. O teste `test_index_with_data` chama `collect_and_save()` com esse JSON mockado.
2. **Os testes escrevem no banco real.** `DB_PATH = "data.db"` é fixo em `app/database.py`, e o fixture `setup_db` de `tests/test_ibovespa.py` só apaga a tabela do banco da aplicação. O último teste deixa o registro do fixture gravado.
3. **`data.db` está versionado**, apesar de constar no `.gitignore`. Entrou no PR #8 (índice de performance) com o registro `130000.5` gravado em 2026-09-26 03:23 UTC, durante o run de testes daquele PR. O Render faz o build a partir do repositório e serve esse arquivo.
4. **O coletor nunca roda em produção.** `render.yaml` declara só o web service. Falta o cron job de coleta que o `AGENTS.md` (seção 12) exige: dias úteis, a cada 15 minutos durante o pregão. Sem coleta, o site mostra o único dado que existe no banco.

**Correção esperada (PR `fix:`):**

- [ ] Remover `data.db` do repositório com `git rm --cached data.db`, mantendo a regra no `.gitignore`.
- [ ] Tornar o caminho do banco configurável (ex.: `DATABASE_PATH`, com padrão `data.db`), documentar em `README.md` e `docs/context/operacao.md`.
- [ ] Isolar os testes: fixture que aponta o banco para `tmp_path` do pytest. Nenhum teste pode criar ou alterar `data.db` na raiz.
- [ ] Declarar o cron job de coleta no `render.yaml` (`python -m app.collectors.ibovespa`), conforme a seção 12 do `AGENTS.md`. Verificar se web service e cron job compartilham o armazenamento: no Render, disco persistente não é compartilhado entre serviços, e no plano gratuito o disco é efêmero. Se não houver armazenamento compartilhado, registrar ADR em `docs/decisions/` com a alternativa escolhida (Postgres do Render via `DATABASE_URL`, ou coleta no startup do web service mais atualização periódica em background) e, se depender de configuração no painel do Render, abrir issue `bloqueado` com o ajuste exato.
- [ ] Coletar ao subir a aplicação quando o banco estiver vazio, para o painel não nascer sem dados após cada deploy.
- [ ] Teste de regressão: falha se `data.db` estiver no índice do git (`git ls-files data.db` vazio).
- [ ] Teste de regressão: a página indica dado desatualizado quando a última coleta tem mais de 24 horas em dia útil, em vez de exibir o valor antigo como se fosse de hoje.
- [ ] Atualizar `docs/STATE.md` (hoje afirma que a coleta funciona) e `CHANGELOG.md`.

**Lição para a retrospectiva:** o Passo 1.3 (saúde de produção) deveria ter pegado isso, porque o horário exibido é o da coleta e o histórico é de 2023. Vale reforçar a checagem: comparar o valor exibido com uma fonte independente e conferir se a última data do histórico é o pregão mais recente.

### Expor `/api/snapshot` para o auditor

O auditor de produção hoje extrai os números do HTML, o que quebra se o template mudar. Implementar o endpoint conforme o contrato em `auditoria/README.md`, com teste em `tests/`. Não altere `auditoria/`: quando o endpoint existir, o auditor passa a usá-lo sozinho.

## Features

| Feature | Valor | Fonte de dados | Esforço (P/M/G) | Risco |
|---|---|---|---|---|
| Maiores altas e baixas do dia (tabela) | Identificar destaques diários do mercado | brapi.dev | P | Baixo (dependência de API externa) |
| Alertas de volume anormal | Detectar movimentos atípicos que precedem tendências | brapi.dev | P | Baixo (depende do cálculo sobre média histórica) |
| Médias móveis (21 e 200 dias) | Análise de tendência de curto e longo prazo | yfinance | P | Baixo |
| Calendário de Balanços | Preparação para volatilidade em datas de resultados | CVM / StatusInvest (scraping) | M | Alto (fontes instáveis ou difíceis de raspar) |
| Ficha da ação (P/L, P/VP, DY, ROE) | Análise fundamentalista rápida de uma empresa | brapi.dev | M | Médio (qualidade dos dados fundamentalistas) |
| Comparador de ações (lado a lado) | Auxilia na escolha entre pares do mesmo setor | brapi.dev | M | Médio (depende da ficha da ação) |
| Mapa de calor setorial | Visualização rápida do desempenho por setor | brapi.dev / yfinance | M | Médio (categorização correta dos setores) |
| Rastreio de carteiras recomendadas | Agregação das carteiras mensais de corretoras | Scraping (bancos/corretoras) | G | Alto (layout variável e difícil extração) |
| Fluxo do investidor estrangeiro | Entender o fluxo de capital gringo na B3 | B3 (scraping ou API não oficial) | M | Alto (fonte instável ou difícil acesso) |
| Histórico de dividendos pagos vs anunciados | Prever o fluxo de caixa do investidor focado em renda | B3 / brapi.dev | G | Alto (eventos corporativos complexos) |
| Consenso de analistas | Entender a expectativa do mercado (preço-alvo) | yfinance / scraping | G | Alto (dificuldade de extração e padronização) |
| Termômetro de sentimento | Analisar humor do mercado via notícias | Scraping (Infomoney, Valor, etc) | G | Alto (mudanças no layout dos sites, NLP) |
| Probabilidade histórica | Estudar comportamento pós-padrões | yfinance | G | Médio (complexidade de cálculo) |
