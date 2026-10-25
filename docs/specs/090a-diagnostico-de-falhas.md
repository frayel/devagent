---
id: 090a
titulo: O pedido está errado ou o servidor falhou? Detalhar falhas no registro
status: done
esforco: P
gaveta: saúde técnica
aceite: tests/test_aceite_090a.py
revisada: 2026-10-24
---

## Problema
Por que o produto acusa erro no Yahoo se o servidor está funcionando? `/sistema` mostra o Yahoo Finance com **Atenção** e erro 404 ("0 de 19 chamadas ok"). O produto não consegue dizer sozinho se o pedido está errado ou se o servidor falhou, porque o registro de fontes (`app/collectors/registro_fontes.py`) guarda só `HTTP 404 em <url>` da **última** falha, sem corpo da resposta, endpoint ou símbolo.

## Comportamento esperado

### 1. O registro diz o que aconteceu
Para toda falha HTTP de qualquer fonte, `registro_fontes.falha` passa a guardar: endpoint (caminho sem os valores variáveis, por exemplo `/v8/finance/chart/{simbolo}`), os símbolos do pedido, o status, e os primeiros 200 caracteres do corpo da resposta, com `token`, `key`, `apikey` e `Authorization` mascarados. Mantém, por fonte, um contador por endpoint (`ok`, `falhas`, último status) com os 10 endpoints mais recentes.

### 2. O nível da fonte diz a verdade
No item Yahoo Finance de `/sistema`, o detalhe passa a trazer: os 3 endpoints com mais falhas, o status e o trecho do corpo. A regra de nível fica:
- **Atenção**: falhas 404 isoladas em símbolos específicos, listados.
- **Problema**: o mesmo endpoint devolveu 404 para 3 ou mais pedidos seguidos de símbolos diferentes, **incluindo um símbolo que respondeu antes** (`^BVSP`). Texto: "o endpoint X parece ter mudado ou saído do ar". Esse caso entra na issue `sistema-com-problema` pelo caminho já existente.

## Fontes de dados
Nenhuma chamada nova a fontes externas nesta etapa. Apenas o registro de erros é enriquecido.

## Critérios de aceite
- [ ] Uma falha 404 simulada (respx) com corpo conhecido fica no registro com endpoint, símbolo, status e trecho do corpo; um `token=abc` no corpo ou na URL aparece como `***`.
- [ ] 404 em endpoint inteiro (símbolos diferentes, inclusive um conhecido) vira **Problema** com o texto do endpoint; 404 isolado fica em **Atenção**.
- [ ] Nenhum segredo aparece em `/sistema` nem em `/api/sistema` (teste varre a resposta).

## Invariantes de produção
- O item Yahoo Finance de `/sistema` não mostra falha 404 sem endpoint e símbolo no detalhe.

## Fora do escopo
- A adaptação de lote para tolerar símbolos e a tabela de bloqueio (ficaram na spec 090b).
