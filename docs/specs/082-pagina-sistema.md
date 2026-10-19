---
id: 082
titulo: Página de sistema (saúde das integrações, do deploy e do fluxo de desenvolvimento)
status: done
esforco: M
gaveta: saúde técnica
---

## Problema

Hoje, para saber se algo quebrou, o dono do produto precisa abrir o Render, o GitHub Actions, o Jules, o cron-job.org e o `/api/coleta`, um de cada vez. Falhas silenciosas passam dias sem ninguém ver: em 19/10/2026 a auditoria de produção, agendada para rodar a cada 30 min no pregão, não tinha uma execução agendada desde 18/10 14:32, porque o GitHub descarta agendamentos quando está sobrecarregado. Nada no produto mostrava isso.

## Comportamento esperado

Uma página `/sistema` (link "Sistema" no cabeçalho, ao lado de "Consultor") responde, em uma tela: o que está funcionando, o que pede atenção e o que quebrou. A mesma informação sai em JSON em `/api/sistema`.

Cada verificação tem um nível escrito no selo, além da cor: **Problema**, **Atenção**, **OK** ou **Inativo** (desligado ou sem configuração). O primeiro painel diz o estado geral e lista só o que é problema ou atenção, problemas primeiro.

Grupos e regras:

- **Aplicação e banco**: versão em produção (commit, data, mensagem), deploy (main à frente do commit em produção: OK até 20 min, atenção até 1 h, problema depois), último deploy no Render (com `RENDER_API_KEY`), início da instância, banco (tipo, tamanho, latência; atenção se `DATABASE_URL` existe mas a aplicação ainda grava no SQLite).
- **Coleta**: agendador (última rodada contra o intervalo esperado: atenção acima de 2× + 10 min, problema acima de 4× + 10 min), erro da última rodada, painéis com coleta vazia nas últimas 3 h (problema se o painel ficou vazio em todas as rodadas da janela, com ao menos 3) e duração da rodada.
- **Integrações externas**: MetaTrader 5, Yahoo Finance, brapi, Gemini e qualquer outro domínio chamado, a partir do resultado final das chamadas dos próprios coletores desde que a instância subiu. Problema se as últimas chamadas (ao menos 3, até 5) falharam e alguma por rede, 5xx, 429 ou chave recusada (ou o MT5 está em pausa); só 404 e afins são pedidos que a fonte não tem e ficam em atenção, com a URL no detalhe. Atenção também se a última falhou ou 30% das 20 últimas falharam.
- **Fluxo de desenvolvimento**: disparos do `jules.yml` pelo cron-job.org (atenção sem disparo há 3 intervalos, problema há 30 min ou 3 falhas seguidas), sessões do Jules (com `JULES_API_KEY`: ativas, esperando resposta há mais de 30 min, paradas há 3 h, falhas e cota de 24 h), PRs abertos (atenção acima de 3 h, problema acima de 12 h), issues com `deploy-falhou` ou `producao-incorreta` (problema) e `prioridade`, `tentativa-falhou` ou `bloqueado` (atenção), última entrega na main (atenção após 12 h, problema após 48 h), fila de specs e limite da API do GitHub.
- **Workflows do GitHub**: cada workflow versionado com o resultado da última execução. Falha em PR é atenção; falha na main ou em execução agendada é problema. Para workflows com `cron`, a página calcula os horários que já deveriam ter rodado (com 1 h de folga) e acusa atenção a partir de 3 agendamentos sem execução.

## Restrições

- Visita nenhuma dispara requisição externa (PRODUTO.md, seção 5). GitHub, Jules e Render são lidos por um laço em segundo plano a cada 5 min com `GITHUB_TOKEN` e a cada 20 min sem ele, respeitando 1 requisição a cada 2 s por domínio. Banco, coleta e integrações vêm da memória e do banco da própria instância.
- Nenhum segredo aparece na página ou no JSON: nem chaves, nem a URL da mt5api, nem tokens em URLs de erro.
- Protegida pela mesma `CONSULTOR_SENHA` do Consultor; sem a variável, pública.
- Sem dependência nova: o cron é lido por um módulo próprio de 5 campos.

## Critérios de aceite

- [x] `/sistema` e `/api/sistema` respondem com os cinco grupos e o resumo geral, problemas primeiro.
- [x] `fetch_with_retry`, `async_fetch_with_retry` e a mt5api registram sucesso e falha por fonte, com segredos mascarados.
- [x] O laço do monitor sobe com a aplicação, fica desligado nos testes e com `MONITOR_SISTEMA=0`, e uma falha de leitura guarda o erro sem apagar o retrato anterior.
- [x] Agendamentos descartados pelo GitHub aparecem como atenção.
- [x] Testes cobrem os níveis de cada verificação, o leitor de cron, a senha e a ausência de segredos na página.
- [x] Interface com as macros e tokens do guia, `span-4` e `span-12`, sem rolagem horizontal em 390 px.
