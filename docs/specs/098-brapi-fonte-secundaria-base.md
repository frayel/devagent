---
id: 098
titulo: Módulo Base da brapi como fonte secundária
status: ready
esforco: M
gaveta: saúde técnica
aceite: tests/test_brapi.py
revisada: 2026-10-25
---

## Problema

Em 20/10/2026 a brapi avisou por email que chamadas autenticadas com o nosso token foram bloqueadas neste ciclo de cobrança, com o motivo "limite de ativos por requisição". O token está no plano Gratuito, que aceita **um ativo por chamada** e **15.000 requisições por mês**.

Esta spec implementa a base do módulo cliente da brapi e migra os primeiros coletores.

## Comportamento esperado

### 1. Novo módulo cliente

Novo módulo `app/collectors/brapi.py`, único lugar do código que monta URL da brapi:

- `cotacao(ticker, **params)` faz uma chamada para **um** ticker e devolve o item de `results` ou `None`.
- `cotacoes(tickers, **params)` chama `cotacao` em sequência, respeitando o limite de 1 requisição a cada 2 s por domínio que `fetch_with_retry` já aplica, e devolve um dicionário `ticker -> item` só com os que vieram.
- Recusa (com `ValueError`) qualquer ticker que contenha vírgula ou `%2C`.
- Manda o token no cabeçalho `Authorization: Bearer` em vez da query string.
- `/api/quote/list` continua permitido e também passa por esse módulo.

### 2. Erros do plano

- **403 da brapi**: não repete. O módulo desliga a brapi até a 00:00 BRT seguinte (disjuntor) e registra em `registro_fontes` uma falha grave ("HTTP 403").
- **429 da brapi**: `fetch_with_retry` deixa de repetir 429 para o domínio `brapi.dev`. Desliga a brapi até a 00:00 BRT seguinte; se indicar cota mensal esgotada, desliga até o próximo mês.

### 3. Ordem das fontes (Lote 1)

Nos coletores `ibovespa.py` e `mare.py`, a ordem passa a ser: MT5 -> Yahoo -> brapi. Eles passam a usar o novo módulo `brapi.py`. Nenhum arquivo modificado nesta spec chama `brapi.dev` diretamente.

## Critérios de aceite e testes tocados (4 testes)

- [ ] Novo módulo `app/collectors/brapi.py` implementa `cotacao` e `cotacoes` (novo teste `tests/test_brapi.py`).
- [ ] 403 da brapi liga o disjuntor sem repetir a chamada (novo teste).
- [ ] 429 da brapi não é repetido por `fetch_with_retry` (novo teste).
- [ ] Coletores `ibovespa.py` e `mare.py` seguem MT5 → Yahoo → brapi e usam o novo módulo (alterar `tests/test_ibovespa.py`, e adicionar `tests/test_mare.py` se necessário ou checar logs).

## Invariantes de produção

- A falha (403, 429) ou instabilidade da brapi não derruba a coleta do Ibovespa nem do Maré, que devem degradar graciosamente para o Yahoo Finance ou MT5 (verificável pelos testes e logs).
- O token da brapi nunca é enviado na URL (query string) para não vazar em logs de erro, sendo enviado apenas no cabeçalho `Authorization: Bearer`.

## Fora do escopo

- Migrar os demais coletores que hoje chamam a brapi (como `coesao.py`, `fator_mola.py`, `highlights.py`, etc.). Eles continuarão chamando a brapi diretamente até serem migrados no Lote 2.
- Lidar com paginação complexa ou outros endpoints da brapi além de `/api/quote/list` e `/api/quote`.
