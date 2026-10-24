---
id: 090
titulo: Yahoo Finance com 404 (o pedido está errado ou o servidor falhou?): registrar o motivo e corrigir
status: ready
esforco: M
gaveta: saúde técnica
aceite: tests/test_aceite_090.py
---

## Problema

`/sistema` mostra o Yahoo Finance com **Atenção** e erro 404. Hoje o produto não consegue dizer se a chamada está inválida ou se o servidor tem problema, porque o registro de fontes (`app/collectors/registro_fontes.py`) guarda só `HTTP 404 em <url>` da **última** falha, sem o corpo da resposta, sem o endpoint e sem o símbolo. O próprio nível mostra a dúvida: `grave()` trata 404 como "pedido que a fonte não tem" e rebaixa para *Atenção*, o que é correto para um ticker que saiu da bolsa e errado se o endpoint inteiro sumiu.

A leitura do código dá candidatos, que a implementação precisa confirmar com o registro novo e não assumir:

1. **Tickers que a bolsa não reconhece mais.** `consultor_historico` chama `/v8/finance/chart/{ticker}.SA` uma vez por ativo da carteira (cerca de 90 por hora). Um ticker renomeado, incorporado ou deslistado devolve 404 em toda rodada, para sempre. A própria tela do Consultor avisa que a composição pode estar desatualizada.
2. **Lote que cai por um símbolo.** `fetch_historico_diario_yfinance_spark` monta `{t}.SA` para todo símbolo, sem passar por `simbolo_yahoo` (que poupa `^BVSP`, `BRL=X` e símbolos com ponto), e manda 15 por chamada em `/v7/finance/spark`. Um símbolo inválido pode derrubar o lote inteiro com 404.
3. **Endpoint que mudou.** Quase todos os coletores usam `/v7/finance/spark`, que não é uma API documentada. Se o Yahoo a retirar, todos os painéis perdem o dado de uma vez.

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
