---
id: 070
titulo: Consultor · opiniões de casas de análise extraídas de notícias
status: draft
esforco: G
---

## Problema
O usuário quer saber o que as casas de análise dizem sobre cada ação do Ibovespa, sem ler dezenas de matérias. Essas opiniões aparecem em portais de notícia, em texto livre. Esta spec coleta as matérias, extrai as recomendações com um LLM (ADR 005) e as mostra no `/consultor`, atribuídas e com link. O cruzamento com o técnico fica para a spec 071.

Se não couber em um PR de ~400 linhas, divida em 070a (feeds, pré-filtro e fila) e 070b (extração, validação e exibição).

## Comportamento esperado
- No `/consultor`, cada ativo com opiniões nos últimos 30 dias mostra uma lista: casa, recomendação (compra, neutro ou venda), preço-alvo quando houver, data da matéria, resumo de uma linha e link para a matéria original.
- Uma seção "Opiniões recentes" lista as últimas 20 opiniões extraídas, de todos os ativos.
- **Degradação (requisito do dono do produto):** se a extração não estiver disponível, as recomendações técnicas aparecem normalmente e o topo da página mostra um único aviso: "Opiniões de especialistas indisponíveis desde HH:MM (motivo). Recomendações baseadas só nos sinais técnicos." Motivos: `sem chave configurada`, `cota do LLM esgotada`, `LLM fora do ar`, `resposta inválida do LLM`, `feeds indisponíveis`. Opiniões já guardadas continuam visíveis, com a data delas. Nenhum desses casos gera exceção não tratada, resposta 500 ou página em branco.
- `/api/consultor` inclui `opinioes` por ativo e `fontes_opiniao`: `{"llm": {"status": "ok|sem_chave|cota|erro|invalido", "desde": ...}, "feeds": [{"url", "status", "ultima_coleta"}], "fila": N}`.
- `/api/snapshot` recebe só `consultor.opinioes_status` e a contagem de opiniões nas últimas 24 h.

## Fontes de dados
- **Feeds RSS**, coletados a cada 30 minutos pelo agendador, com 1 requisição a cada 2 s por domínio, timeout, retry com backoff e `User-Agent` identificável:
  - Money Times: `https://www.moneytimes.com.br/feed/`
  - InfoMoney: `https://www.infomoney.com.br/feed/`
  Antes de implementar, confira `robots.txt` e termos de uso de cada um e registre o resultado em `docs/context/fontes-de-dados.md`. Um feed que proíba coleta automatizada não entra. Novos feeds podem ser adicionados pelo mesmo critério.
- Só o conteúdo do próprio feed (título, descrição e `content:encoded` quando houver) é usado. A página da matéria não é baixada.
- **Proibidos** (registrados em `docs/context/fontes-de-dados.md`): Yahoo `quoteSummary` e Google News RSS, bloqueados por `robots.txt`; conteúdo atrás de login ou paywall.
- **LLM:** Gemini `generateContent` por REST (`https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODELO}:generateContent`, chave no header `x-goog-api-key`), com `responseMimeType: application/json` e `responseSchema`. Variáveis: `GEMINI_API_KEY`, `GEMINI_MODELO` (padrão: o Flash-Lite gratuito vigente, conferido na página de preços do Gemini na hora de implementar), `GEMINI_MAX_CHAMADAS_DIA` (padrão 200). Timeout de 30 s, sem retry em 429 (vira estado `cota` até a próxima hora cheia).

## Cálculos
1. **Pré-filtro sem LLM.** Normalizar título e descrição (minúsculas, sem acento). A matéria segue se citar um ticker do universo ou um nome do mapa empresa → tickers (spec 068) **e** um termo de opinião: `recomend`, `compra`, `venda`, `neutr`, `preco-alvo`, `preco alvo`, `carteira`, `eleva`, `rebaix`, `outperform`, `underperform`, `overweight`, `underweight`, `market perform`. Matérias já vistas (pelo `guid`) são ignoradas.
2. **Fila.** As aprovadas entram em `consultor_fila_materias`, e as opiniões validadas em `consultor_opinioes`, ambas atrás da interface `app/consultor/armazenamento.py` (ADR 006). Nesta spec a interface só tem o SQLite; a spec 072 acrescenta o Postgres sem mudar quem a usa. Itens com mais de 3 dias são descartados; a fila tem no máximo 200 itens.
3. **Extração.** Lotes de até 10 matérias por chamada, respeitando o teto diário. O esquema pede, por opinião: `ticker`, `casa`, `recomendacao` (`compra`, `neutro`, `venda`), `preco_alvo` (número ou nulo), `resumo` (até 120 caracteres, em português, sem citar a matéria literalmente) e `trecho` (até 200 caracteres copiados da matéria, só para validação, nunca exibido). O prompt manda ignorar opiniões sobre ativos fora da lista enviada e não inventar campos.
4. **Validação no código.** Descartar a opinião se: o ticker não está no universo; o `trecho` normalizado não aparece no texto normalizado da matéria; o `preco_alvo` não aparece no texto em nenhum formato usual (`42`, `42,00`, `R$ 42`); a `casa` está vazia. Mapear sinônimos: `manter`, `market perform` → neutro; `outperform`, `overweight` → compra; `underperform`, `underweight` → venda. Contar descartes por motivo em `/api/consultor`.
5. **Duplicatas.** A mesma casa, ativo e recomendação em matérias diferentes no mesmo dia viram uma opinião só, com os links preservados.

## Critérios de aceite
- [ ] Com um fixture RSS de 10 itens, só os que citam ativo do universo e termo de opinião entram na fila.
- [ ] Com uma resposta Gemini mockada (respx) válida, as opiniões aparecem no `/api/consultor` do ativo correto, com casa, recomendação, preço-alvo, data e link.
- [ ] Uma opinião mockada com `trecho` que não está na matéria é descartada e contada como `trecho_ausente`.
- [ ] Uma opinião com preço-alvo ausente do texto é descartada e contada como `alvo_ausente`.
- [ ] Sem `GEMINI_API_KEY`: `/consultor` responde 200, mostra as recomendações técnicas e o aviso com o motivo "sem chave configurada"; nenhuma chamada HTTP ao Gemini é feita.
- [ ] Com o Gemini respondendo 429, 500, timeout ou JSON fora do esquema (um teste para cada): resposta 200, recomendações técnicas presentes, aviso com o motivo correto, matérias mantidas na fila.
- [ ] Com os dois feeds falhando: resposta 200 e aviso "feeds indisponíveis"; opiniões guardadas continuam visíveis.
- [ ] Atingido `GEMINI_MAX_CHAMADAS_DIA`, nenhuma nova chamada é feita no dia e o status fica `cota`.
- [ ] O texto enviado ao Gemini contém só conteúdo das matérias e a lista de tickers (o teste inspeciona o corpo da requisição mockada).

## Invariantes de produção
- Toda opinião exibida tem link para uma URL de um feed da lista e data de no máximo 30 dias.
- Quando `opinioes_status` não é `ok`, a página do consultor contém o aviso e ainda lista recomendações técnicas.
- Nenhum texto de opinião exibido passa de 120 caracteres.

## Fora do escopo
- Baixar a página completa das matérias.
- Relatórios de corretoras, Telegram, X, YouTube ou qualquer fonte atrás de login.
- Usar o LLM para decidir, pontuar ou redigir a recomendação final (ADR 005).
- Cruzamento com os sinais técnicos (spec 071).
