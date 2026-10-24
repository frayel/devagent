---
id: 090b
titulo: Como o sistema reage a símbolos deslistados no Yahoo? Suspender por 24h e isolar
status: ready
esforco: P
gaveta: saúde técnica
aceite: tests/test_aceite_090b.py
revisada: 2026-10-24
---

## Problema
Como evitar que papéis extintos continuem derrubando a coleta do lote inteiro? **Causa confirmada em produção:** Os 404 vêm de pedidos por ativo para **NTCO3, SOMA3, JBSS3, MRFG3 e PETZ3**. Os cinco estão na carteira do Ibovespa, mas mudaram de código.
Além disso, candidatos a falha: o lote de `fetch_historico_diario_yfinance_spark` monta `{t}.SA` sem passar por `simbolo_yahoo` e manda 15 símbolos por chamada, de modo que um símbolo ruim derruba o lote.

## Comportamento esperado

### 1. Tolerância a símbolo inválido
- O montador de lote em `fetch_historico_diario_yfinance_spark` usa `simbolo_yahoo`.
- Um 404 num lote de `/v7/finance/spark` com mais de um símbolo divide o lote ao meio e repete (no máximo 4 chamadas extras por lote), até isolar o símbolo que falha. O que veio é aproveitado.
- Símbolo que devolve 404 isolado 3 vezes seguidas entra numa tabela `simbolos_sem_cotacao (fonte, simbolo, desde, ultimo_status, tentativas)` e deixa de ser pedido por 24 h (depois tenta de novo uma vez). A tabela existe nos dois backends e é coberta pelo teste de paridade de esquema da spec 084.
- O produto **não altera a carteira sozinho**: a lista de símbolos suspensos aparece em `/sistema` e na tela do Consultor ("Sem cotação no Yahoo: X, Y. Verifique a composição do Ibovespa").

## Fontes de dados
Yahoo Finance, como hoje. Nenhuma chamada nova além das divisões de lote descritas (limitadas e sujeitas ao limite de 1 requisição a cada 2 s por domínio).

## Critérios de aceite
- [ ] O lote com um símbolo inválido entre 15 devolve os 14 válidos e marca o inválido (teste com respx que responde 404 se o símbolo ruim estiver na consulta).
- [ ] Símbolos como `^BVSP` e `BRL=X` num lote de `fetch_historico_diario_yfinance_spark` não ganham `.SA`.
- [ ] Depois de 3 respostas 404 seguidas, o símbolo não é pedido nas rodadas seguintes dentro de 24 h, e `/sistema` o lista.
- [ ] O número de requisições do Yahoo por rodada não cresce mais que o previsto: teste com 90 símbolos, 2 inválidos, confere o teto de chamadas.

## Invariantes de produção
- Depois da correção, o Yahoo fica em *OK* ou, com símbolos suspensos, em *Atenção* com a lista; nunca em *Atenção* sem explicação.

## Fora do escopo
- Atualizar a composição do Ibovespa automaticamente (spec 094).
- A brapi (spec 091).
