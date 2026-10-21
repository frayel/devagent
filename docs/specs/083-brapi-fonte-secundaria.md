---
id: 083
titulo: brapi como fonte secundária, com uma chamada por ativo e orçamento de requisições
status: ready
esforco: M
gaveta: saúde técnica
---

## Problema

Em 20/10/2026 a brapi avisou por email que 68 chamadas autenticadas com o nosso token foram bloqueadas neste ciclo de cobrança, com o motivo "limite de ativos por requisição". O token está no plano Gratuito, que aceita **um ativo por chamada** (o Startup aceita 10 e o Pro, 20) e **15.000 requisições por mês**. O dado existe na brapi; o formato da chamada é que o plano recusa.

Seis coletores montam uma URL com a lista de tickers separada por vírgula (`/api/quote/PETR4,VALE3,...`):

| Coletor | Ativos na chamada | Posição da brapi hoje |
|---|---|---|
| `concentracao_ordens.py` | 30 | única fonte |
| `highlights.py` (`fetch_brapi`) | 30 | segunda (depois de `/api/quote/list`), antes do Yahoo |
| `radar_anomalias_spread.py` | cesta de liquidez | **primeira** |
| `concentracao_setorial.py` | lista setorial | primeira quando o MT5 não está configurado |
| `fator_mola.py` | lista própria | depois do Yahoo |
| `coesao.py` | 10 | depois do Yahoo |

Toda chamada dessas falha com 403 a cada rodada do agendador (a cada 15 min no pregão), e o painel cai na fonte seguinte ou fica vazio. Além disso, `fetch_with_retry` repete 429 com backoff, o que só gasta cota quando o motivo é limite do plano.

`ibovespa.py` e `mare.py` pedem só `^BVSP` e não estão bloqueados, mas `ibovespa.py` também põe a brapi antes do Yahoo quando o MT5 não está configurado.

## Comportamento esperado

### 1. Ordem das fontes

Em todos os coletores de cotação a ordem passa a ser a mesma, a que o PRODUTO.md já declara:

1. MetaTrader 5 (via `mt5.exclusivo()` / interceptação das URLs do Yahoo);
2. Yahoo Finance;
3. brapi, só para o que as duas primeiras não entregaram.

A brapi deixa de ser a primeira fonte em `radar_anomalias_spread`, `concentracao_setorial`, `ibovespa` e `highlights` (o `/api/quote/list` também passa para depois do Yahoo). Quando a fonte primária entregou parte dos ativos, a brapi busca **só os que faltaram**, não a lista inteira.

### 2. Uma chamada por ativo, num único cliente

Novo módulo `app/collectors/brapi.py`, único lugar do código que monta URL da brapi:

- `cotacao(ticker, **params)` faz uma chamada para **um** ticker e devolve o item de `results` ou `None`.
- `cotacoes(tickers, **params)` chama `cotacao` em sequência, respeitando o limite de 1 requisição a cada 2 s por domínio que `fetch_with_retry` já aplica, e devolve um dicionário `ticker -> item` só com os que vieram.
- Recusa (com `ValueError`) qualquer ticker que contenha vírgula ou `%2C`.
- Manda o token no cabeçalho `Authorization: Bearer` em vez da query string, para ele não aparecer em URL de log ou de erro.
- `/api/quote/list` continua permitido (é uma requisição só) e também passa por esse módulo.

Os seis coletores da tabela, `ibovespa.py` e `mare.py` passam a usar esse módulo. Nenhum outro arquivo de `app/` chama `brapi.dev` diretamente.

### 3. Orçamento de requisições

- Contador de chamadas à brapi persistido no banco (dia e mês corrente), para sobreviver a reinício da instância.
- `BRAPI_LIMITE_MENSAL` (padrão 15000). Teto diário = 90% do limite mensal dividido pelos dias do mês.
- Antes de cada chamada, o módulo confere o teto diário. Acabou o orçamento do dia: não chama, devolve `None` e registra o motivo `orçamento` (não é falha da fonte).
- Quando a brapi é fonte secundária de um painel, ela nunca gasta mais que o que falta do orçamento do dia; se a lista de faltantes não cabe, busca os primeiros e deixa o resto vazio.

### 4. Erros do plano

- **403 da brapi**: não repete. O módulo desliga a brapi até a 00:00 BRT seguinte (disjuntor) e registra em `registro_fontes` uma falha grave com o detalhe "plano da brapi recusou a chamada (HTTP 403)".
- **429 da brapi**: `fetch_with_retry` deixa de repetir 429 para o domínio `brapi.dev`. Desliga a brapi até a 00:00 BRT seguinte; se o corpo da resposta indicar cota mensal esgotada, desliga até o primeiro dia do mês seguinte.
- Com o disjuntor ligado, nenhuma chamada sai. As rodadas seguintes não acumulam 403 nem 429.

### 5. Concentração de ordens

O painel depende de `regularMarketTrades` (número de negócios), que o Yahoo não traz. Se a mt5api expuser o número de negócios do dia para o símbolo, use-a como fonte primária. Se não expuser, a brapi continua sendo a fonte do painel, com uma chamada por ativo e **no máximo uma atualização por hora** no pregão: entre uma atualização e outra, o painel mostra a última coleta com o horário dela. Conta: 30 ativos × 7 atualizações × 22 pregões ≈ 4.600 chamadas por mês, um terço da cota.

### 6. Página de sistema

O item "brapi" do grupo *Integrações externas* de `/sistema` e `/api/sistema` mostra também:

- chamadas no dia e no mês contra o teto;
- estado do disjuntor (ligado, motivo e até quando);
- **Atenção** acima de 80% do teto mensal; **Problema** com o disjuntor ligado por 403.

## Restrições

- Nenhuma dependência nova.
- Não mudar o plano da brapi nem pedir troca de plano: o projeto fica no Gratuito.
- Nenhum segredo na página, no JSON ou nos logs (o token sai da URL).
- Testes usam respostas gravadas; nenhum teste chama a brapi de verdade.

## Critérios de aceite

- [ ] Nenhuma URL `brapi.dev/api/quote/` com mais de um ticker existe em `app/`; um teste varre o código e reprova vírgula ou `%2C` em URL da brapi fora de `app/collectors/brapi.py`.
- [ ] Todos os coletores de cotação seguem MT5 → Yahoo → brapi, e a brapi só busca os ativos que faltaram (teste com a primária devolvendo parte da lista).
- [ ] 403 da brapi liga o disjuntor sem repetir a chamada; a rodada seguinte não faz nenhuma requisição à brapi (teste).
- [ ] 429 da brapi não é repetido por `fetch_with_retry`; 429 do Yahoo continua sendo (teste).
- [ ] Orçamento diário esgotado impede novas chamadas e aparece como `orçamento`, não como falha (teste).
- [ ] O contador sobrevive a reinício (lido do banco).
- [ ] Concentração de ordens atualiza no máximo uma vez por hora pela brapi e mostra o horário da última coleta.
- [ ] `/sistema` mostra consumo do dia e do mês e o estado do disjuntor.
- [ ] PRODUTO.md (tabela de fontes e de variáveis) cita `BRAPI_LIMITE_MENSAL`, a ordem das fontes e a regra de uma chamada por ativo.
