---
id: 091
titulo: brapi com erro 400: tratar a recusa do plano gratuito e guardar o motivo
status: ready
esforco: P
gaveta: saúde técnica
aceite: tests/test_aceite_091.py
---

## Problema

`/sistema` mostra a brapi com **Atenção** e erro 400 ("0 de 1 chamadas ok"). Hoje o produto guarda só `HTTP 400 em <url>` e nenhuma explicação.

**O que a produção mostra (leitura do `/api/sistema` em 24/10/2026, 03:00 UTC).** A chamada que falhou foi `https://brapi.dev/api/quote/PETR4,VALE3,ITUB4,BBDC4,B3SA3,ABEV3,ELET3,RENT3,WEGE3,BBAS3?token=***&fundamental=false`: **dez ativos numa chamada, sem `range`**, com token. Isso casa com o que a documentação da brapi diz do plano **Gratuito**: 1 ativo por chamada e 15.000 requisições por mês. A spec 083 parte do aviso de 20/10 da brapi sobre chamadas bloqueadas por "limite de ativos por requisição", e então o código de retorno era 403; agora o mesmo tipo de chamada volta como 400. O problema é, portanto, do **pedido** (lista de ativos acima do plano), e não do servidor.

Hipótese que **não** se confirmou: que o 400 viesse de `range` acima de 3 meses (as páginas da brapi dizem "histórico de até 3 meses" no plano gratuito). `ibovespa.py` pede `range=1y` e `mare.py`, `range=2y`, mas um teste sem token feito em 24/10/2026 com `/api/quote/PETR4?range=1y&interval=1d` devolveu 200 (PETR4 é um ativo liberado sem token, então o teste não prova o comportamento do plano). A implementação decide pelo corpo registrado, e não por esta suposição.

Depende da spec 083 (módulo único `app/collectors/brapi.py`, uma chamada por ativo, disjuntor para 403 e 429) e da 090 (registro de falhas com endpoint, símbolos e corpo).

## Comportamento esperado

1. **A causa some com a 083.** Nenhum coletor monta lista com vírgula; o módulo recusa mais de um ticker. Esta spec não repete esse trabalho.
2. **400 é uma recusa de pedido, não uma queda.** Um 400 da brapi não é repetido e **não** liga o disjuntor da 083 (que é para 403 e 429, falha da conta ou da cota). O corpo da resposta (até 200 caracteres, com `token` mascarado) vai para o registro, e o item da brapi em `/sistema` o mostra no detalhe.
3. **Pedido que falha duas vezes seguidas com 400 fica suspenso por 24 h**, para não gastar a cota mensal com uma chamada que não funciona. O item da brapi lista os pedidos suspensos (endpoint e parâmetros, sem o token).
4. **Plano sabe do histórico, se o corpo confirmar.** Se o corpo registrado de um 400 citar `range`, `interval` ou plano, `brapi.py` passa a recusar antes de chamar qualquer `range` acima de `BRAPI_HISTORICO_MAX` (padrão `3mo`), e `ibovespa.py` e `mare.py` tiram a brapi das cadeias de série longa (MT5 e Yahoo cobrem). Sem essa evidência, a regra não entra.
5. **Nível no Sistema.** 400 recorrente no mesmo pedido é *Atenção*, com endpoint, parâmetros e corpo. Se a brapi devolve 400 para um pedido de um ativo só e dentro do plano que antes funcionou, o item vira *Problema*: "a brapi mudou o contrato".

## Fontes de dados

brapi (plano Gratuito). Plano B: MT5, depois Yahoo, como na spec 083.

## Critérios de aceite

- [ ] Um 400 simulado (respx) com corpo conhecido não é repetido, não liga o disjuntor e aparece em `/sistema` com o trecho do corpo, sem o token.
- [ ] O mesmo pedido, duas vezes com 400, é suspenso por 24 h (relógio simulado) e não faz nova requisição nesse prazo; a suspensão aparece no item da brapi.
- [ ] Pedidos suspensos não entram na contagem de chamadas e de orçamento da spec 083.
- [ ] Com o corpo de 400 simulado citando `range`, `brapi.cotacao(..., range="1y")` levanta `ValueError` sem requisição e `ibovespa.py` e `mare.py` obtêm a série longa do MT5 ou do Yahoo.
- [ ] Sem esse corpo, `range` não é bloqueado.
- [ ] Um teste varre `app/` e reprova qualquer URL da brapi com mais de um ticker fora de `app/collectors/brapi.py` (regra da 083, repetida aqui para o caso do 400).

## Invariantes de produção

- O item da brapi em `/sistema` não acusa 400 por mais de 24 h sem um pedido suspenso explicado e o corpo da resposta no detalhe.

## Fora do escopo

- Trocar de plano.
- Orçamento mensal e disjuntor de 403 e 429 (spec 083).
