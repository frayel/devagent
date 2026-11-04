---
id: 135
titulo: A variação diária das ações não usa o fechamento de 15 dias atrás
status: ready
esforco: M
gaveta: saúde técnica
aceite: tests/test_aceite_135.py
revisada: 2026-11-03
---

## Problema
O usuário perguntou: "por que a variação diária de algumas ações parece estar acumulada desde semanas atrás em vez de ser a variação de ontem para hoje?"

O defeito da spec 134 (tratar `chartPreviousClose` como "fechamento de ontem") não é exclusivo do Ibovespa. Em `app/collectors/highlights.py`, o caminho do Yahoo consulta `spark?...&range=15d&interval=1d` (linha 197) e calcula `change_percent = (preço − chartPreviousClose) / chartPreviousClose` (linhas 209 e 137). Com `range=15d`, `chartPreviousClose` é o fechamento de antes da janela de 15 dias, então a "variação do dia" de cada ação é, na verdade, a de cerca de 15 dias. Dela saem as maiores altas, as maiores quedas, a Dispersão (proporção de ações em alta) e a contagem `up_count`/`down_count`.

Levantamento dos coletores que leem `chartPreviousClose` (código atual):

| Coletor | `range` | Situação |
|---|---|---|
| `highlights.py` | `15d` | **defeito** |
| `ibovespa.py` | `1y` | defeito, corrigido na spec 134 |
| `coesao`, `concentracao_setorial`, `apetite_risco`, `rotacao_capital`, `motores_indice`, `fator_peso_pesado` | `1d` | correto: com 1 dia, o campo é o pregão anterior |
| `anomalia_peso` | `1d` (ações) | correto; o fechamento do Ibovespa que usa vem do banco e herda a spec 134 |
| `clima_global` | `2d` | correto: usa `valid_closes[-2]` e só recorre ao campo quando a série tem 1 barra |

Por que os testes não pegaram: o dublê `tests/yahoo_falso.py` ignora o `range` da URL (o número de barras só depende do `interval`) e define `chartPreviousClose = fechamentos[-2]` em todos os casos (linhas 121, 163 e 189). Ou seja, o dublê devolve sempre o "fechamento de ontem" que o código espera, e nunca o que o Yahoo e o MT5 devolvem de fato para janelas maiores que 1 dia.

## Comportamento esperado
1. **`highlights.py` (Yahoo):** o fechamento anterior vem da série `spark` do próprio ativo: penúltimo fechamento válido quando a última barra é do pregão corrente (ou o preço é igual ao último fechamento); último fechamento quando a série termina num pregão anterior; `meta["previousClose"]` com menos de 2 barras. `chartPreviousClose` deixa de ser lido. A regra é a mesma da spec 134, e o código a compartilha numa função pequena em `app/collectors/utils.py` (`fechamento_anterior(serie, preco, hoje)`), usada pelos dois coletores. Se a spec 134 já tiver criado essa função em outro lugar, reutilize-a.
2. **Dublê fiel:** `tests/yahoo_falso.py` passa a ler o `range` da URL. Para `range` diferente de `1d`, gera a quantidade de barras correspondente (5d=5, 15d=15, 1mo=21, 3mo=63, 1y=252) e preenche `chartPreviousClose` com o fechamento imediatamente anterior à **primeira** barra, como o Yahoo. `previousClose` fica com o penúltimo fechamento. Sem `range` ou com `1d`, o dublê se comporta exatamente como hoje, para limitar o estrago nos outros testes.
3. **Teste de fronteira:** um teste varre `app/collectors/*.py` e falha se um arquivo que lê `chartPreviousClose` consulta qualquer `range=` diferente de `1d`, a não ser os da lista explícita `clima_global.py` (só no caso de uma barra) e `mt5.py` (é quem o emula). Quem acrescentar um coletor com `range` maior e `chartPreviousClose` verá o teste falhar, com a mensagem apontando esta spec.
4. Se, ao trocar o dublê, outro coletor quebrar nos testes, é o mesmo defeito: corrija-o aqui se couber em poucas linhas; se não couber, registre no PR qual coletor e abra a issue, sem ampliar esta spec.

## Fontes de dados
MT5 no formato do Yahoo (`spark`); plano B: o próprio Yahoo, como hoje.

## Cálculos
`change_percent = (preço − fechamento anterior) / fechamento anterior × 100`, com o fechamento anterior da regra acima. Dispersão e rankings continuam calculados sobre `change_percent`.

## Critérios de aceite
- [ ] Dado um `spark` de 15 dias com penúltimo fechamento `10.00`, preço `10.50` e `chartPreviousClose = 8.00`, o `change_percent` do ativo é `+5.00` (e não `+31.25`).
- [ ] Com 3 ativos que sobem no dia mas estão abaixo do nível de 15 dias atrás, e 2 que caem no dia mas estão acima dele, `up_count == 3`, `down_count == 2` e a Dispersão é `60%`.
- [ ] A série do ativo com 1 barra usa `previousClose`; sem ele, o ativo é ignorado (como hoje quando `prev_close` é nulo).
- [ ] O dublê com `range=15d` devolve 15 barras e `chartPreviousClose` igual ao fechamento anterior à primeira; com `range=1d` devolve exatamente o que devolve hoje (teste comparando com um instantâneo salvo no próprio arquivo).
- [ ] O teste de fronteira passa na `main` depois das specs 134 e 135, e falha num coletor de exemplo, escrito no próprio teste, que lê `chartPreviousClose` com `range=15d`.
- [ ] `tests/test_highlights.py` e os demais testes que usam o dublê continuam verdes; os que mudarem de valor são citados no PR.
- Arquivos tocados: `app/collectors/highlights.py`, `app/collectors/utils.py` (função compartilhada), `tests/yahoo_falso.py`, os novos `tests/test_aceite_135.py` e o teste de fronteira, e ajustes pontuais nos testes de highlights.
- Meça antes de começar: `grep -rl yahoo_falso tests` e `grep -rl "highlights" tests`. Se mais de ~15 arquivos de teste mudarem por causa do dublê, divida: o dublê vira a parte "a" e o `highlights.py` a "b".

## Invariantes de produção
- Em `/api/snapshot`, para cada ação de `paineis.altas_baixas.altas` e `.baixas` que traga `sparkline`, `change_percent` difere em no máximo 0,3 ponto percentual de `(sparkline[-1] / sparkline[-2] − 1) × 100`. A comparação só vale quando a sparkline termina no pregão corrente; fora disso o auditor marca `inconclusivo`.
## Fora do escopo
- O Ibovespa (spec 134) e o teto de variação (spec 136).
- Reescrever os coletores de `range=1d`, que estão corretos.
- Mudar o tamanho das sparklines ou a janela de 15 dias, que continua servindo ao gráfico.
