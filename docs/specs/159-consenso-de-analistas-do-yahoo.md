---
id: 159
titulo: O Consultor mostra o consenso de analistas do Yahoo Finance, quando o Yahoo responder
status: ready
esforco: P
gaveta: capacidade nova
aceite: tests/test_aceite_159.py
revisada: 2026-11-15
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
- **Coletor `app/collectors/consultor_yahoo.py`**, registrado em `app/agendador.py` com a janela `"fechamento"`:
  - a janela `"fechamento"` dispara a cada rodada entre o fechamento e 20h. O coletor sai sem nenhuma chamada se a tabela já tem linhas com `data` igual a `calendario.ultimo_pregao_fechado(agora)` ou se a fonte está em pausa. É isso que garante uma rodada por dia;
  - obtém o cookie em `https://fc.yahoo.com` e o crumb em `https://query2.finance.yahoo.com/v1/test/getcrumb`, com `httpx` (timeout de 10 s por chamada) e sem dependência nova;
  - para cada ticker de `CARTEIRA_IBOVESPA` (a mesma lista que o `calcular_consultor` avalia, sem o `^BVSP`), lê `financialData` em `/v10/finance/quoteSummary/<TICKER>.SA?modules=financialData&crumb=<crumb>`;
  - grava cada leitura na tabela nova `consultor_consenso_yahoo` (`ticker`, `data`, os cinco campos e `coletado_em`), criada em `app/database.py` nos dois backends. `data` é `calendario.ultimo_pregao_fechado(agora)`;
  - ativo cuja resposta não traz `recommendationMean.raw` ou traz `numberOfAnalystOpinions.raw` igual a 0 não gera linha (o Yahoo devolve `financialData` sem esses campos para ações sem cobertura). Preço-alvo ausente vira `NULL` e a tela omite o trecho `alvo médio`;
  - **não** usa `fetch_with_retry` nem `async_fetch_with_retry`: o `registro_fontes` atribui todo domínio `finance.yahoo.com` à integração "Yahoo Finance", e um 401 aqui marcaria como fora do ar o `chart`, que é outra coisa e funciona.
- **Bloqueio honesto.** Se o crumb ou qualquer ativo vier com 401 ou 429, ou se 3 ativos seguidos falharem (rede ou 5xx), a rodada para ali, nada mais é chamado, e a fonte entra em pausa por 24 h. A pausa é gravada no banco (tabela `consultor_consenso_yahoo_status`, no formato de `consultor_opinioes_status`: `status`, `motivo`, `desde`), para um reinício do Render não repetir a chamada. O `/sistema` ganha o item "Yahoo · consenso" no grupo "Coleta": `ok` com a última leitura (`12 de 84 ativos em 14/11`), ou `atencao` com "bloqueado (HTTP 401) desde 15/11 18:40". Se o bloqueio durar 7 dias seguidos (`desde` mais de 7 dias antes, sem leitura nova), o resumo acrescenta "candidato à poda: remover o coletor numa spec de poda". O Consultor funciona igual sem ela, e nada é inventado.
- **Tela (`/consultor`).** Na coluna "Casas" das tabelas Comprar, Vender, Aguardar e No radar, abaixo do consenso das casas, cada ativo com leitura cuja `data` é a data de referência da página ou o pregão anterior a ela (`calendario.pregao_anterior`) mostra: `Yahoo: compra (2,1) · 12 analistas · alvo médio R$ 15,40`. Sem leitura nessa janela, nada aparece. Na data passada vale a mesma regra, relativa à data escolhida.
- **Não entra na decisão.** O consenso do Yahoo não conta para o mínimo de 2 casas nem muda a decisão. Juntar as duas coisas é decisão de regra, que fica para outra spec, com medição.
- **Cache do Consultor.** A versão do cache de `calcular_consultor` passa a incluir o maior `coletado_em` de `consultor_consenso_yahoo`, para a leitura nova aparecer sem esperar outra fonte mudar.
- `/api/consultor` traz `consenso_yahoo` por ativo, com os cinco campos, o `rotulo` e a `data`, ou `null`.

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
O JSON de `PETR4.SA` traz `financialData.recommendationMean.raw = 2.1` (escala de 1 = compra forte a 5 = venda forte, sem unidade), `numberOfAnalystOpinions.raw = 12` (contagem de analistas), `targetMeanPrice.raw = 15.4`, `targetLowPrice.raw = 12.0` e `targetHighPrice.raw = 19.0` (preços em reais por ação, na moeda da cotação `.SA`, não em centavos nem em milhar). Os campos `fmt` são ignorados.

1. A tabela grava `2.1, 12, 15.4, 12.0, 19.0`.
2. `2.1` está acima de 1,5 e até 2,5, então o rótulo é `compra`.
3. A média é exibida com uma casa decimal e vírgula (`2,1`); o alvo médio com duas casas, vírgula e prefixo `R$` (`15.4` → `R$ 15,40`). Mínimo e máximo ficam só no `/api/consultor`.
4. A tela mostra `Yahoo: compra (2,1) · 12 analistas · alvo médio R$ 15,40`.

## Critérios de aceite
- [ ] Uma fixture JSON de `financialData` grava uma linha com os cinco campos, e o `/consultor` mostra a frase do exemplo.
- [ ] Fixtures de 401 e de 429 (via `respx`) deixam a fonte em pausa por 24 h e não gravam nada. Uma segunda chamada do coletor dentro das 24 h não faz nenhuma requisição. O `/api/consultor` responde 200 com `consenso_yahoo: null`, e o `/sistema` mostra o bloqueio. O item "Yahoo Finance" do `/sistema` não ganha falha.
- [ ] Com linhas já gravadas para o pregão, uma nova chamada do coletor não faz nenhuma requisição.
- [ ] Uma resposta `financialData` sem `recommendationMean` ou com `numberOfAnalystOpinions.raw = 0` não grava linha e não aparece na tela; sem `targetMeanPrice`, a frase sai sem o trecho `alvo médio`.
- [ ] Leitura com `data` dois pregões antes da data de referência não aparece na tela e sai `null` na API.
- [ ] A decisão de cada ativo é idêntica com e sem a tabela preenchida, com o mesmo fixture.
- [ ] As fronteiras do rótulo seguem a tabela: 1,5 dá `compra forte`, 2,5 dá `compra`, 3,5 dá `neutro` e 4,5 dá `venda`.
- [ ] `tests/test_aceite_159.py` usa `exigir_spec_done("159")` e não abre rede.
- [ ] O `app/novidades.json` ganha uma entrada `tipo: "novidade"` com `"spec": "159"` e `onde` `{"pagina": "/consultor", "pagina_nome": "Consultor", "painel": "Coluna Casas"}` (a spec 156 está `done` e exige a entrada).

## Invariantes de produção
- No máximo uma rodada de chamadas ao `quoteSummary` por dia.
- Todo `consenso_yahoo` exibido tem `data` igual à data de referência da página ou ao pregão anterior a ela.
- Toda linha de `consultor_consenso_yahoo` tem a média de recomendação entre 1 e 5 e o número de analistas maior que 0.
- Falha do `quoteSummary` não aparece como falha da integração "Yahoo Finance" no `/sistema`.
- A decisão (Comprar, Vender, Aguardar, No radar) de cada ativo é a mesma que seria sem a tabela.

## Fora do escopo
- Usar o consenso do Yahoo na decisão.
- Histórico do consenso ao longo do tempo.
- Mostrar alvo mínimo e máximo na tela, ou potencial do alvo sobre o preço.
- Converter moeda: os alvos são exibidos como o Yahoo os entrega para o ticker `.SA`.
- Contornar o bloqueio (proxy, troca de IP, navegador headless).
