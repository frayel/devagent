---
id: 159
titulo: O Consultor mostra o consenso de analistas do Yahoo Finance, quando o Yahoo responder
status: ready
esforco: P
gaveta: capacidade nova
aceite: tests/test_aceite_159.py
---

## Problema
O usuário perguntou: "o que o mercado como um todo espera desta ação, além das poucas casas que aparecem nas notícias?"

O dono do produto pediu o Yahoo Finance como fonte de opinião em 04/11/2026. A spec escrita naquele dia (então 142) ficou num ramo que nunca chegou à `main`. O endpoint `quoteSummary` (módulo `financialData`) traz por ativo:

- `recommendationMean` (média de recomendação);
- `numberOfAnalystOpinions` (número de analistas);
- `targetMeanPrice`, `targetLowPrice` e `targetHighPrice` (preço-alvo médio, mínimo e máximo).

Hoje o Consultor monta o consenso casa por casa, a partir de matérias.

Em 04/11/2026, chamado a partir do contêiner de desenvolvimento, o endpoint recusou com 429 sem crumb e 401 `Invalid Crumb`. Não se sabe se o IP do Render recebe o mesmo tratamento: o endpoint `chart` do Yahoo funciona a partir do Render (a auditoria o usa), mas o `quoteSummary` exige cookie e crumb.

## Comportamento esperado
- **Coletor `app/collectors/consultor_yahoo.py`**, uma vez por dia depois do fechamento:
  - obtém o cookie em `https://fc.yahoo.com` e o crumb em `https://query2.finance.yahoo.com/v1/test/getcrumb`, com `httpx` e sem dependência nova;
  - para cada ativo da carteira, lê os cinco campos de `financialData` em `/v10/finance/quoteSummary/<TICKER>.SA?modules=financialData&crumb=<crumb>`;
  - grava cada leitura na tabela nova `consultor_consenso_yahoo` (`ticker`, `data`, os cinco campos e `coletado_em`).
- **Bloqueio honesto.** Se vier 401 ou 429, ou se houver 3 falhas seguidas, a fonte entra em pausa por 24 h, e o `/sistema` mostra "Yahoo · consenso: bloqueado (HTTP 401)" com o horário. O Consultor funciona igual sem ela, e nada é inventado. Se o bloqueio durar 7 dias seguidos, o item do `/sistema` passa a sugerir a remoção do coletor numa spec de poda.
- **Tela (`/consultor`).** Na linha de cada ativo com leitura do dia ou do pregão anterior, aparece ao lado do consenso das casas: `Yahoo: compra (2,1) · 12 analistas · alvo médio R$ 15,40`. Sem leitura, nada aparece.
- **Não entra na decisão.** O consenso do Yahoo não conta para o mínimo de 2 casas nem muda a decisão. Juntar as duas coisas é decisão de regra, que fica para outra spec, com medição.
- `/api/consultor` traz `consenso_yahoo` por ativo, ou `null`.

## Fontes de dados
Yahoo Finance `quoteSummary`, `financialData`. O formato vem do JSON real; a primeira resposta bem-sucedida em produção é registrada numa seção do `docs/context/fontes-de-dados.md` no PR de implementação. Plano B: o bloqueio acima.

## Cálculos
Os números aparecem como o Yahoo os entrega. `recommendationMean` é traduzido assim:

| Média | Rótulo |
|---|---|
| de 1 a 1,5 | compra forte |
| acima de 1,5 até 2,5 | compra |
| acima de 2,5 até 3,5 | neutro |
| acima de 3,5 até 4,5 | venda |
| acima de 4,5 | venda forte |

### Exemplo de ponta a ponta
O JSON traz `financialData.recommendationMean.raw = 2.1`, `numberOfAnalystOpinions.raw = 12`, `targetMeanPrice.raw = 15.4`, `targetLowPrice.raw = 12.0` e `targetHighPrice.raw = 19.0`, todos em reais e por ação.

1. A tabela grava `2.1, 12, 15.4, 12.0, 19.0`.
2. `2.1` está acima de 1,5 e até 2,5, então o rótulo é `compra`.
3. A tela mostra `Yahoo: compra (2,1) · 12 analistas · alvo médio R$ 15,40`.

## Critérios de aceite
- [ ] Uma fixture JSON de `financialData` grava uma linha com os cinco campos, e o `/consultor` mostra a frase do exemplo.
- [ ] Fixtures de 401 e de 429 deixam a fonte em pausa por 24 h e não gravam nada. O `/api/consultor` responde 200 com `consenso_yahoo: null`, e o `/sistema` mostra o bloqueio.
- [ ] A decisão de cada ativo é idêntica com e sem a tabela preenchida, com o mesmo fixture.
- [ ] As fronteiras do rótulo seguem a tabela: 1,5 dá `compra forte`, 2,5 dá `compra`, 3,5 dá `neutro` e 4,5 dá `venda`.
- [ ] `tests/test_aceite_159.py` usa `exigir_spec_done("159")` e não abre rede.
- [ ] Se a spec 156 estiver `done`, o `app/novidades.json` ganha uma entrada `novidade` com `onde` `{"pagina": "/consultor", "painel": "Recomendações"}`.

## Invariantes de produção
- No máximo uma rodada de chamadas ao `quoteSummary` por dia.
- Todo `consenso_yahoo` exibido tem `data` do dia ou do pregão anterior.

## Fora do escopo
- Usar o consenso do Yahoo na decisão.
- Histórico do consenso ao longo do tempo.
