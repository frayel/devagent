---
id: 091
titulo: brapi com erro 400: respeitar o limite de histórico do plano gratuito
status: ready
esforco: P
gaveta: saúde técnica
aceite: tests/test_aceite_091.py
---

## Problema

`/sistema` mostra a brapi com erro 400. Um 400 é, em regra, pedido mal formado ou fora do que o plano permite, não instabilidade do servidor, mas hoje o produto só guarda `HTTP 400 em <url>` e nenhuma explicação.

A documentação da brapi (páginas de preços e limites) diz que o plano **Gratuito** tem 1 ativo por chamada, 15.000 requisições por mês e histórico de **até 3 meses**. As páginas não informam qual status volta ao pedir mais histórico que o plano. O código pede mais:

| Coletor | Pedido à brapi | Excede o plano |
|---|---|---|
| `ibovespa.py` | `/api/quote/%5EBVSP?range=1y&interval=1d` | sim (12 meses) |
| `mare.py` | `/api/quote/%5EBVSP?range=2y&interval=1d` | sim (24 meses) |
| `highlights.py` | `range=1mo&interval=1d` | não |

A hipótese principal é, portanto, que os pedidos de 1 ano e 2 anos recebem 400. A confirmação vem do corpo da resposta, que a spec 090 passa a registrar.

Depende da spec 083 (módulo único `app/collectors/brapi.py`, uma chamada por ativo, disjuntor para 403 e 429) e da 090 (registro com corpo e endpoint).

## Comportamento esperado

1. **O cliente da brapi conhece o plano.** `app/collectors/brapi.py` (spec 083) recusa, antes de chamar, um `range` acima de 3 meses com `ValueError("plano gratuito da brapi: histórico até 3 meses")`. Os valores aceitos ficam numa constante (`1d, 5d, 1mo, 3mo`), com o limite lido de `BRAPI_HISTORICO_MAX` (padrão `3mo`) para o dia em que o plano mudar.
2. **A brapi sai das cadeias de histórico longo.** `ibovespa.py` e `mare.py` deixam de pedir `1y` e `2y` à brapi. A série longa vem do MT5 e do Yahoo, na ordem da spec 083. A brapi só entra com `range` dentro do plano, para o trecho recente, quando as outras fontes falharam.
3. **400 não é repetido nem desliga a fonte.** Um 400 da brapi não é refeito e **não** liga o disjuntor da 083 (que é para 403 e 429). Um mesmo pedido (endpoint, símbolo e parâmetros) que devolveu 400 duas vezes seguidas fica suspenso por 24 h, para não gastar a cota mensal com uma chamada que não funciona. A suspensão aparece no item da brapi em `/sistema`.
4. **Nível no Sistema.** 400 recorrente no mesmo pedido é *Atenção*, com o endpoint, os parâmetros e o trecho do corpo da resposta no detalhe. Se a brapi devolve 400 para pedidos que já funcionaram antes (mesmo endpoint, parâmetros dentro do plano), o item vira *Problema*: "a brapi mudou o contrato".

## Fontes de dados

brapi (plano Gratuito), com o limite de histórico de 3 meses. Plano B: MT5, depois Yahoo, como na spec 083.

## Critérios de aceite

- [ ] Nenhum pedido a `brapi.dev` em `app/` leva `range` acima de 3 meses; um teste varre os coletores e o módulo `brapi.py` (URL e parâmetros) e reprova `1y`, `2y`, `5y`, `10y` e `max`.
- [ ] `brapi.cotacao(..., range="1y")` levanta `ValueError` sem fazer requisição.
- [ ] `ibovespa.py` e `mare.py` obtêm a série longa do MT5 ou do Yahoo (respx) e não chamam a brapi com `1y` ou `2y`.
- [ ] Um 400 da brapi não é repetido e não liga o disjuntor; o mesmo pedido, duas vezes com 400, é suspenso por 24 h (relógio simulado) e não faz nova requisição nesse prazo.
- [ ] O item da brapi em `/sistema` mostra o trecho do corpo do 400 com `token` mascarado e o pedido suspenso.
- [ ] A contagem de chamadas da spec 083 não soma pedidos suspensos.

## Invariantes de produção

- O item da brapi em `/sistema` não acusa 400 recorrente por mais de 24 h sem estar associado a um pedido suspenso explicado.
- Painéis que dependem de histórico longo (Maré, Ibovespa) continuam com 1 ano ou mais de série a partir de MT5 ou Yahoo.

## Fora do escopo

- Trocar de plano ou pedir upgrade na brapi.
- Reescrever os coletores que só usam `range` curto.
- Orçamento mensal e disjuntor 403 e 429 (spec 083).
