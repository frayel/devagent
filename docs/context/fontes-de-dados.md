# Contexto · Fontes de dados

Uma entrada por fonte. Atualize ao criar ou alterar coletor (skill `criar-coletor.md`).

## MetaTrader 5 (mt5api) · fonte preferencial

- **Uso**: barras diárias e intradiárias de ações (`PETR4`), do Ibovespa (`IBOV`) e de qualquer símbolo que a corretora publique no terminal.
- **Onde**: terminal MT5 numa máquina Windows do dono do projeto, exposto pelo servidor [mt5api](https://github.com/dceoy/mt5api). O painel usa só `GET /rates/from-pos` (leitura).
- **Autenticação**: header `X-API-Key` com `MT5_API_KEY`; endereço em `MT5_API_URL`. Sem `MT5_API_URL`, a fonte fica desligada e a coleta volta ao comportamento anterior.
- **Como entra**: `app/collectors/mt5.py` atende as URLs do Yahoo Finance (`spark` e `chart`) dentro de `fetch_with_retry`, devolvendo o mesmo JSON montado com as barras do MT5. Se o MT5 falhar, a requisição segue ao Yahoo. Ibovespa e maiores altas/baixas tentam o MT5 antes da brapi.
- **Rótulo**: o painel mostra `mt5`, `mt5+yfinance` (parte de cada fonte) ou o rótulo antigo, conforme quem respondeu de fato.
- **Símbolos**: `XXXX4.SA` vira `XXXX4`; `^BVSP` vira `IBOV`; `BRL=X` vira `DOL$` (dólar futuro cheio contínuo). Outros mapeamentos em `MT5_SIMBOLOS` (JSON). Sem mapeamento, o símbolo continua vindo do Yahoo.
- **Limites**: 1 requisição a cada 2 s, como as demais fontes; barras ficam em cache por 5 min (diárias) e 2 min (intradiárias), então uma rodada faz uma chamada por símbolo. Se o servidor cair ou recusar a chave, a fonte inteira fica em pausa por 5 min. Se o terminal recusar um símbolo (a mt5api responde 503 com `MT5 last status: ...`), só aquele símbolo fica em pausa.
- **Armadilhas**: o horário das barras é o do servidor da corretora (`MT5_FUSO_SERVIDOR`, padrão `-3`). Barras diárias recebem 13:00 UTC, como no Yahoo, para a data não mudar ao converter para BRT. O nome do índice varia entre corretoras; confira em `/symbols?group=*IBOV*`. `DOL$` é futuro, não o câmbio à vista do `BRL=X`: segue o à vista mais o prêmio do contrato, e a série contínua pode saltar na virada de vencimento, o que afeta só o retorno daquele dia.

## brapi.dev

- **Uso**: cotação e histórico do Ibovespa (`/api/quote/^BVSP`).
- **Autenticação**: `BRAPI_TOKEN` (variável de ambiente).
- **Limites**: plano gratuito tem cota de requisições; confira no site antes de aumentar a frequência.
- **Papel**: fonte principal. Se o token faltar, o coletor pula para a reserva.

## Yahoo Finance (endpoint de chart)

- **Uso**: reserva para cotação e histórico do Ibovespa.
- **Autenticação**: nenhuma.
- **Riscos**: API não oficial, sujeita a bloqueio e a mudanças de formato sem aviso. Não dependa dela como fonte única.
- **Armadilhas**: Ao utilizar `range=1mo` no endpoint de chart, o campo `meta.chartPreviousClose` aponta para o fechamento anterior ao primeiro candle (ou seja, de cerca de um mês atrás), e não para o último fechamento do dia útil anterior. Para calcular a variação diária, deve-se extrair o penúltimo `close` da série, e utilizar os dados do `meta` como fallback secundário.
- **Maré do mercado**: `chart/^BVSP?range=2y&interval=1d` para a volatilidade (precisa de ~280 pregões; o MT5 entrega 300 barras diárias) e `spark` da cesta com `range=3mo&interval=1d` para fluxo e volume. A brapi com `range=2y` é a reserva do Ibovespa.
- **Pendência**: o coletor atual envia um User-Agent de navegador genérico; a seção 5 do `PRODUTO.md` pede um User-Agent identificável do projeto.

## brapi.dev · limites do plano gratuito (verificado em 2026-09-27)

- 15.000 requisições por ciclo mensal e 1 requisição simultânea.
- `/api/quote/{tickers}` com vários ativos na mesma chamada não serve no gratuito; uma requisição por ativo estouraria a cota (30 ativos × ~40 coletas por dia).
- `/api/quote/list` não exige token e traz `stock`, `close`, `change` (% do dia), `volume` e `type` de todas as ações. As maiores altas e baixas usam uma única chamada: `?type=stock&sortBy=volume&sortOrder=desc&limit=100`, e o ranking sai das 100 ações mais negociadas do dia.
- Fonte: https://brapi.dev/docs/acoes/list e https://brapi.dev/faq/tem-algum-limite
