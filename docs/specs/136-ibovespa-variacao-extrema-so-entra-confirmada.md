---
id: 136
titulo: Variação extrema do Ibovespa só entra no painel se uma segunda fonte confirma
status: ready
esforco: M
gaveta: saúde técnica
aceite: tests/test_aceite_136.py
revisada: 2026-11-03
---

## Problema
O usuário perguntou: "esse número do Ibovespa é de verdade?" O coletor responde com um teto fixo, e o teto já se mostrou incapaz de separar um movimento real de um dado errado:

- Em 26/10 o auditor registrou `2026-10-26-ibov-variacao-implausivel` (−13,88%, de 205.083 para 176.608) e a checagem `ibov.variacao_plausivel` falhou com o limite de ±12%. O arquivo do achado consta como resolvido e não registra a causa; a "confirmação" citada nele foi feita com o Yahoo, que também é fonte do produto.
- Dois PRs seguidos trocaram o limite de 12% por `VARIACAO_DIARIA_MAXIMA = 20.0`: o #601 (`6210c6c`, 28/10 às 23:27 −03:00) no coletor, `app/collectors/ibovespa.py:19`, e o #602 (`35b8957`, 23:33) na auditoria, `auditoria/auditar.py:58`. Ambos alegam que "em 29/10/2026 o Ibovespa variou 15,99% de verdade, com o circuit breaker estendido". As datas dos commits são anteriores ao dia citado, e nenhum documento traz uma fonte independente para o número. A frase foi copiada para `auditoria/README.md:26` e `CHANGELOG.md:8`.
- Se a hipótese da spec 134 se confirmar, o +12,87% do painel seria rejeitado pelo limite antigo (12%) e o coletor cairia na brapi, que usa o fechamento do pregão anterior. Com 20%, ele passa. O teto mais folgado tirou o único freio que existia contra um fechamento anterior errado.

Um teto fixo mede magnitude, não verdade. A pergunta certa para um movimento grande é: duas fontes independentes concordam?

## Comportamento esperado
Em `app/collectors/ibovespa.py`, depois de calcular a variação do dia pela fonte principal (MT5/Yahoo):

1. `|variação| ≤ 10%` (onde o circuit breaker da B3 começa): grava como hoje, sem chamada extra.
2. `10% < |variação| ≤ 20%`: o coletor pede a variação à **outra** fonte (brapi, `regularMarketPrice` e `regularMarketPreviousClose`, quando a principal foi MT5/Yahoo; Yahoo, quando a principal foi a brapi). Se as duas diferirem em até 0,5 ponto percentual, grava e registra no log o motivo "variação acima de 10% confirmada por X e Y". Se divergirem, ou se a outra fonte não responder, **não grava**, registra o motivo (as duas variações, ou "sem segunda fonte") e o coletor devolve `False`. O painel continua mostrando o último dado gravado, com o horário real dele, como já acontece quando a coleta falha.
3. `|variação| > 20%`: descartada sempre, mesmo com confirmação, como hoje.
4. As menções a "15,99% em 29/10/2026" em `app/collectors/ibovespa.py:14-18`, `auditoria/auditar.py:55-58`, `auditoria/README.md:26` e `CHANGELOG.md:8` são reescritas para dizer que o caso foi relatado e **não** foi confirmado por fonte independente, a menos que quem implementar consiga a confirmação por uma fonte que não seja o Yahoo (brapi com histórico, Stooq). Se confirmar, a fonte e a data de consulta entram no texto. Não se inventa o resultado: sem acesso, vale a redação "relatado, não confirmado".

Esta spec **aperta** a regra (adiciona uma confirmação) e mantém o teto de 20%. O limite do auditor (`auditoria/auditar.py:58`) não muda aqui.

## Fontes de dados
Principal: MT5/Yahoo. Confirmação: brapi (`app/collectors/brapi.py`), que já é a fonte de reserva do coletor; a chamada extra só acontece nos dias com movimento acima de 10%, então o orçamento de requisições da brapi não é afetado na rotina. Plano B da confirmação: se a brapi estiver sem cota, em disjuntor ou fora do ar, o coletor tenta o Yahoo/MT5 como segunda fonte quando a principal foi a brapi, e não grava quando nenhuma segunda fonte responde.

## Cálculos
`confirma = |var_principal − var_segunda| ≤ 0,5 p.p.`. Cada variação usa o fechamento anterior da própria fonte (a regra da spec 134 para o Yahoo/MT5; `regularMarketPreviousClose` para a brapi).

## Critérios de aceite
- [ ] Fonte principal com `+12,87%` e brapi com `−0,80%` (divergem): nada é gravado a partir da principal; o coletor segue para a brapi e grava `−0,80%` com `fonte = "brapi"`.
- [ ] Fonte principal com `+12,87%` e brapi com `+12,60%`: grava a variação da principal e registra o motivo de confirmação.
- [ ] Fonte principal com `+12,87%` e brapi indisponível (erro HTTP ou disjuntor aberto): `collect_and_save()` devolve `False` e não grava; o último dado do banco permanece.
- [ ] Variação de `+3,00%`: nenhuma chamada à brapi (espião no cliente HTTP prova zero chamadas extras).
- [ ] Variação de `+25%` com a brapi concordando: descartada.
- [ ] Os testes existentes de `tests/test_ibovespa_variacao_extrema.py` (16% aceito, 25% descartado) são atualizados para fornecer a segunda fonte e continuam provando o teto; nenhum é removido.
- [ ] Nenhuma ocorrência de "15,99%" em `app/`, `auditoria/` e `CHANGELOG.md` afirma o fato sem a ressalva da redação acima (busca em teste: `grep` no próprio teste, falhando se a frase aparecer sem "relatado").
- Arquivos tocados: `app/collectors/ibovespa.py`, `auditoria/README.md`, `auditoria/auditar.py` (só o comentário das linhas 55-58), `CHANGELOG.md`, `tests/test_ibovespa_variacao_extrema.py` e o novo `tests/test_aceite_136.py`.
- Depende da spec 134: implementar depois dela.

## Invariantes de produção
- Se `paineis.ibovespa.variacao_pct` em `/api/snapshot` tem módulo acima de 10%, o auditor (spec 138) confere a variação contra uma fonte que não seja a do produto e falha se divergir mais de 0,5 ponto percentual.
- Depois de uma coleta recusada por falta de confirmação, `paineis.ibovespa.coletado_em` não avança, e o auditor de frescor (já existente) é quem aponta se o dado envelhecer além dos 45 minutos do pregão.

## Fora do escopo
- Selo visual na tela para "variação acima de 10%".
- Mudar o limite do auditor, que fica para PR próprio com evidência (regra do `auditoria/README.md`).
- Reabrir ou editar `docs/auditoria/` (pertence ao auditor).
- Confirmar o caso de 26/10 (−13,88%): o dado já saiu da janela do gráfico e não há fonte independente registrada.
