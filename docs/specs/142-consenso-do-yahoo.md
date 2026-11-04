---
id: 142
titulo: Consenso de analistas do Yahoo Finance, quando o Yahoo responder
status: ready
esforco: P
gaveta: capacidade nova
aceite: tests/test_aceite_142.py
---

## Problema
O dono do produto pediu o Yahoo Finance como fonte de opinião. O `quoteSummary` traz o consenso pronto por ativo (média de recomendação, número de analistas, preço-alvo médio, mínimo e máximo), que o consultor hoje monta casa por casa a partir de matérias. O `robots.txt` deixou de bloquear fontes em 04/11/2026.

Em 04/11/2026, testado a partir do container de desenvolvimento, o endpoint recusou: 429 sem crumb, 401 `Invalid Crumb` e `User is unable to access this feature` pelo `yfinance`. Não se sabe se o IP do Render recebe o mesmo tratamento.

## Comportamento esperado
- **Passo 0, antes de codar:** rodar no Render (shell ou rota temporária protegida por `CONSULTOR_SENHA`) uma chamada `yfinance.Ticker("PETR4.SA").info` e registrar o resultado em `docs/context/fontes-de-dados.md`. Se vier 401 ou 429 também lá, marcar esta spec como `blocked` com o motivo e parar.
- Coletor `app/collectors/consultor_yahoo.py`, uma vez por dia depois do fechamento: para cada ativo da carteira, lê `recommendationMean`, `numberOfAnalystOpinions`, `targetMeanPrice`, `targetLowPrice` e `targetHighPrice` (`financialData`) e grava numa tabela `consultor_consenso_yahoo` (ticker, data, campos, coletado_em).
- Sem nova dependência pesada: se `yfinance` não estiver em `requirements.txt`, usar `httpx` com cookie e crumb (`https://fc.yahoo.com` e `/v1/test/getcrumb`), como o `yfinance` faz.
- **Na tela**, o consenso do Yahoo aparece ao lado do consenso das casas, com o número de analistas e a data. Ele **não** entra na conta de 2 casas nem muda a decisão. Juntar as duas coisas é decisão de regra, que fica para outra spec com medição.
- Com 401, 429 ou 3 falhas seguidas, a fonte entra em pausa por 24 h e `/sistema` mostra o motivo. O consultor funciona igual sem ela.

## Fontes de dados
Ver `docs/context/fontes-de-dados.md`, seção Yahoo Finance quoteSummary.

## Cálculos
Nenhum. Os números são exibidos como o Yahoo entrega, com `recommendationMean` traduzido (1 a 1,5 compra forte, 1,5 a 2,5 compra, 2,5 a 3,5 neutro, 3,5 a 4,5 venda, acima de 4,5 venda forte).

## Critérios de aceite
- [ ] O resultado do passo 0 está registrado em `fontes-de-dados.md`, com data.
- [ ] Fixture JSON de `financialData` grava uma linha com os cinco campos.
- [ ] Fixture de resposta 401 deixa a fonte em pausa e não grava nada; `/api/consultor` responde 200.
- [ ] `/api/consultor` traz `consenso_yahoo` por ativo quando houver linha do dia ou do pregão anterior, e `null` caso contrário.
- [ ] A decisão de cada ativo é idêntica com e sem a tabela preenchida (mesmo fixture).
- Arquivos tocados: `app/collectors/consultor_yahoo.py`, `app/consultor/armazenamento.py`, `app/consultor/calculador.py`, `app/templates/consultor.html`, `app/agendador.py` e o novo `tests/test_aceite_142.py`.

## Invariantes de produção
- Nenhuma chamada ao `quoteSummary` fora da janela diária.

## Fora do escopo
- Usar o consenso do Yahoo na decisão.
