---
id: 136
titulo: Variação extrema do Ibovespa só entra no painel se uma segunda fonte confirma
status: done
esforco: M
gaveta: saúde técnica
aceite: tests/test_aceite_136.py
revisada: 2026-11-04
---

## Problema
O usuário perguntou: "esse número do Ibovespa é de verdade?" O coletor responde com um teto fixo, e o teto já se mostrou incapaz de separar um movimento real de um dado errado:

- Em 26/10 o auditor registrou `2026-10-26-ibov-variacao-implausivel` (−13,88%, de 205.083 para 176.608) e a checagem `ibov.variacao_plausivel` falhou com o limite de ±12%. O arquivo do achado consta como resolvido e não registra a causa; a "confirmação" citada nele foi feita com o Yahoo, que também é fonte do produto.
- Dois PRs seguidos trocaram o limite de 12% por `VARIACAO_DIARIA_MAXIMA = 20.0`: o #601 (`6210c6c`, 28/10 às 23:27 −03:00) no coletor, `app/collectors/ibovespa.py:19`, e o #602 (`35b8957`, 23:33) na auditoria, `auditoria/auditar.py:58`. Ambos alegam que "em 29/10/2026 o Ibovespa variou 15,99% de verdade, com o circuit breaker estendido". As datas dos commits são anteriores ao dia citado, e nenhum documento traz uma fonte independente para o número. A frase foi copiada para `auditoria/README.md:26` e `CHANGELOG.md:8`.
- Se a hipótese da spec 134 se confirmar, o +12,87% do painel seria rejeitado pelo limite antigo (12%). Com 20%, ele passa. O teto mais folgado tirou o único freio que existia contra um fechamento anterior errado.

Um teto fixo mede magnitude, não verdade. A pergunta certa para um movimento grande é: duas fontes independentes concordam?

## Comportamento esperado
O produto tem duas fontes de mercado de origens diferentes: o MetaTrader 5 (barras da corretora, pela mt5api) e o Yahoo Finance. Uma confirma a outra. Em `app/collectors/ibovespa.py`, depois de calcular a variação do dia pela fonte principal:

1. `|variação| ≤ 10%` (onde o circuit breaker da B3 começa): grava como hoje, sem chamada extra.
2. `10% < |variação| ≤ 20%`: o coletor pede a variação à **outra** fonte. Se a principal foi o MT5, a segunda é o Yahoo; se a principal foi o Yahoo (MT5 desligado ou fora do ar), a segunda é o MT5. Se as duas diferirem em até 0,5 ponto percentual, grava e registra no log o motivo "variação acima de 10% confirmada por X e Y". Se divergirem, ou se a outra fonte não responder ou não estiver configurada, **não grava**, registra o motivo (as duas variações, ou "sem segunda fonte") e o coletor devolve `False`. O painel continua mostrando o último dado gravado, com o horário real dele, como já acontece quando a coleta falha.
3. `|variação| > 20%`: descartada sempre, mesmo com confirmação, como hoje.
4. As menções a "15,99% em 29/10/2026" em `app/collectors/ibovespa.py:14-18`, `auditoria/auditar.py:55-58`, `auditoria/README.md:26` e `CHANGELOG.md` são reescritas para dizer que o caso foi relatado e **não** foi confirmado por fonte independente, a menos que quem implementar consiga a confirmação por uma fonte que não seja o Yahoo nem o MT5 (Stooq, B3). Se confirmar, a fonte e a data de consulta entram no texto. Não se inventa o resultado: sem acesso, vale a redação "relatado, não confirmado".

Para pedir a variação ao Yahoo quando o MT5 está configurado, `app/collectors/mt5.py` ganha o contexto `ignorado()`, o oposto de `exclusivo()`: dentro dele, `interceptar` devolve `None` e a URL segue direto ao Yahoo. Para pedir ao MT5, o coletor usa `exclusivo()`, que já existe. Nenhum parser novo: as duas respostas têm o formato do `chart` do Yahoo e passam pela mesma regra de fechamento anterior da spec 134.

Esta spec **aperta** a regra (adiciona uma confirmação) e mantém o teto de 20%. O limite do auditor (`auditoria/auditar.py:58`) não muda aqui.

## Fontes de dados
Principal: MT5, com o Yahoo como reserva (ordem atual de `collect_and_save`). Confirmação: a outra das duas. A chamada extra só acontece nos dias com movimento acima de 10%. Plano B da confirmação: nenhum; sem segunda fonte, o dado não é gravado. Com o MT5 desligado, isso significa que variações acima de 10% não entram no painel até alguém religá-lo, e o motivo fica no log e no item do coletor em `/sistema`.

## Cálculos
`confirma = |var_principal − var_segunda| ≤ 0,5 p.p.`. Cada variação usa o fechamento anterior da própria série, pela regra da spec 134.

## Critérios de aceite
- [ ] MT5 com `+12,87%` e Yahoo com `−0,80%` (divergem): nada é gravado, `collect_and_save()` devolve `False` e o log traz as duas variações.
- [ ] MT5 com `+12,87%` e Yahoo com `+12,60%`: grava a variação do MT5, com `fonte = "mt5"`, e registra o motivo de confirmação.
- [ ] MT5 desligado, Yahoo com `+12,87%`: sem segunda fonte, `collect_and_save()` devolve `False` e não grava; o último dado do banco permanece.
- [ ] MT5 com `+12,87%` e Yahoo fora do ar (erro HTTP): não grava, motivo "sem segunda fonte".
- [ ] Variação de `+3,00%`: nenhuma chamada extra (espião no cliente HTTP prova que só a fonte principal foi chamada).
- [ ] Variação de `+25%` com as duas fontes concordando: descartada.
- [ ] Dentro de `mt5.ignorado()`, uma URL do Yahoo vai à rede mesmo com `MT5_API_URL` configurada (teste em `tests/test_mt5.py`); fora dele, o comportamento atual não muda.
- [ ] Os testes existentes de `tests/test_ibovespa_variacao_extrema.py` (16% aceito, 25% descartado) são atualizados para fornecer a segunda fonte e continuam provando o teto; nenhum é removido.
- [ ] Nenhuma ocorrência de "15,99%" em `app/`, `auditoria/` e `CHANGELOG.md` afirma o fato sem a ressalva da redação acima (busca em teste: `grep` no próprio teste, falhando se a frase aparecer sem "relatado").
- Arquivos tocados: `app/collectors/ibovespa.py`, `app/collectors/mt5.py` (só o contexto `ignorado`), `auditoria/README.md`, `auditoria/auditar.py` (só o comentário das linhas 55-58), `CHANGELOG.md`, `tests/test_ibovespa_variacao_extrema.py`, `tests/test_mt5.py` e o novo `tests/test_aceite_136.py`.
- Depende da spec 134: implementar depois dela.

## Invariantes de produção
- Se `paineis.ibovespa.variacao_pct` em `/api/snapshot` tem módulo acima de 10%, o auditor (spec 138) confere a variação contra uma fonte que não seja a do produto e falha se divergir mais de 0,5 ponto percentual.
- Depois de uma coleta recusada por falta de confirmação, `paineis.ibovespa.coletado_em` não avança, e o auditor de frescor (já existente) é quem aponta se o dado envelhecer além dos 45 minutos do pregão.

## Fora do escopo
- Selo visual na tela para "variação acima de 10%".
- Mudar o limite do auditor, que fica para PR próprio com evidência (regra do `auditoria/README.md`).
- Reabrir ou editar `docs/auditoria/` (pertence ao auditor).
- Confirmar o caso de 26/10 (−13,88%): o dado já saiu da janela do gráfico e não há fonte independente registrada.
