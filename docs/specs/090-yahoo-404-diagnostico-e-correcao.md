---
id: 090
titulo: Yahoo Finance com 404 (o pedido está errado ou o servidor falhou?): registrar o motivo e corrigir
status: ready
esforco: M
gaveta: saúde técnica
aceite: tests/test_aceite_090.py
---

## Problema

`/sistema` mostra o Yahoo Finance com **Atenção** e erro 404 ("0 de 19 chamadas ok"). O produto não consegue dizer sozinho se o pedido está errado ou se o servidor falhou, porque o registro de fontes (`app/collectors/registro_fontes.py`) guarda só `HTTP 404 em <url>` da **última** falha, sem corpo da resposta, endpoint ou símbolo.

**Causa confirmada em produção (leitura do `/api/sistema` em 24/10/2026, 03:00 UTC).** Os 404 vêm de pedidos por ativo, `/v8/finance/chart/{ticker}.SA?range=2y&interval=1d`, para **NTCO3, SOMA3, JBSS3, MRFG3 e PETZ3**. Os cinco estão em `CARTEIRA_IBOVESPA` (`app/consultor/universo.py`), e o MetaTrader 5 também falha para os mesmos símbolos (`HTTP 503: copy_rates_from_pos returned None`). Dois serviços independentes não conhecem o ticker: o pedido está certo na forma e errado no conteúdo, porque a carteira tem papéis que deixaram de existir ou mudaram de código (fusões e reorganizações). O contador "0 de 19" é só dos pedidos que sobraram depois de o MT5 falhar, ou seja, exatamente os desses papéis. O servidor do Yahoo, nesse caso, não tem problema.

Atualizar a lista de papéis é a spec 094. Esta spec trata do que o produto faz quando um símbolo não existe e de como a tela explica isso.

**Ainda não confirmado** (candidatos que a implementação precisa verificar com o registro novo): o lote de `fetch_historico_diario_yfinance_spark` monta `{t}.SA` sem passar por `simbolo_yahoo` e manda 15 símbolos por chamada, de modo que um símbolo ruim pode derrubar o lote; e `/v7/finance/spark` não é uma API documentada e pode mudar. Nenhum dos dois aparece no erro de hoje. Não foi possível testar o Yahoo direto do ambiente de desenvolvimento (HTTP 429 do próprio Yahoo para o IP do ambiente).

## Comportamento esperado

### 1. O registro diz o que aconteceu

Para toda falha HTTP de qualquer fonte, `registro_fontes.falha` passa a guardar: endpoint (caminho sem os valores variáveis, por exemplo `/v8/finance/chart/{simbolo}`), os símbolos do pedido, o status, e os primeiros 200 caracteres do corpo da resposta, com `token`, `key`, `apikey` e `Authorization` mascarados. Mantém, por fonte, um contador por endpoint (`ok`, `falhas`, último status) com os 10 endpoints mais recentes.

### 2. Tolerância a símbolo inválido

- O montador de lote em `fetch_historico_diario_yfinance_spark` usa `simbolo_yahoo`.
- Um 404 num lote de `/v7/finance/spark` com mais de um símbolo divide o lote ao meio e repete (no máximo 4 chamadas extras por lote), até isolar o símbolo que falha. O que veio é aproveitado.
- Símbolo que devolve 404 isolado 3 vezes seguidas entra numa tabela `simbolos_sem_cotacao (fonte, simbolo, desde, ultimo_status, tentativas)` e deixa de ser pedido por 24 h (depois tenta de novo uma vez). A tabela existe nos dois backends e é coberta pelo teste de paridade de esquema da spec 084.
- O produto **não altera a carteira sozinho**: a lista de símbolos suspensos aparece em `/sistema` e na tela do Consultor ("Sem cotação no Yahoo: X, Y. Verifique a composição do Ibovespa").

### 3. O nível da fonte diz a verdade

No item Yahoo Finance de `/sistema`, o detalhe passa a trazer: os 3 endpoints com mais falhas, o status e o trecho do corpo, e os símbolos suspensos. A regra de nível fica:

- **Atenção**: falhas 404 isoladas em símbolos específicos, listados.
- **Problema**: o mesmo endpoint devolveu 404 para 3 ou mais pedidos seguidos de símbolos diferentes, **incluindo um símbolo que respondeu antes** (`^BVSP`). Texto: "o endpoint X parece ter mudado ou saído do ar". Esse caso entra na issue `sistema-com-problema` pelo caminho já existente (ADR 016).

## Fontes de dados

Yahoo Finance, como hoje. Nenhuma chamada nova além das divisões de lote descritas (limitadas e sujeitas ao limite de 1 requisição a cada 2 s por domínio).

## Critérios de aceite

- [ ] Uma falha 404 simulada (respx) com corpo conhecido fica no registro com endpoint, símbolo, status e trecho do corpo; um `token=abc` no corpo ou na URL aparece como `***`.
- [ ] O lote com um símbolo inválido entre 15 devolve os 14 válidos e marca o inválido (teste com respx que responde 404 se o símbolo ruim estiver na consulta).
- [ ] Símbolos como `^BVSP` e `BRL=X` num lote de `fetch_historico_diario_yfinance_spark` não ganham `.SA`.
- [ ] Depois de 3 respostas 404 seguidas, o símbolo não é pedido nas rodadas seguintes dentro de 24 h, e `/sistema` o lista.
- [ ] 404 em endpoint inteiro (símbolos diferentes, inclusive um conhecido) vira **Problema** com o texto do endpoint; 404 isolado fica em **Atenção** com a lista.
- [ ] Nenhum segredo aparece em `/sistema` nem em `/api/sistema` (teste varre a resposta).
- [ ] O número de requisições do Yahoo por rodada não cresce mais que o previsto: teste com 90 símbolos, 2 inválidos, confere o teto de chamadas.

## Invariantes de produção

- O item Yahoo Finance de `/sistema` não mostra falha 404 sem endpoint e símbolo no detalhe.
- Depois da correção, o Yahoo fica em *OK* ou, com símbolos suspensos, em *Atenção* com a lista; nunca em *Atenção* sem explicação.

## Fora do escopo

- Trocar o Yahoo por outra fonte ou remover o `/v7/finance/spark` dos coletores (se o endpoint morrer, vira spec própria).
- Atualizar a composição do Ibovespa automaticamente.
- A brapi (spec 091).
