---
id: 2026-11-04-producao-inacessivel-brapi-timeout
severidade: alta
painel: infra
status: aberto
visto_em: 2026-11-04T07:15:00-03:00
pr: 730
---

# Produção inacessível devido a timeout gerado por falhas síncronas na brapi

## O que acontece
A aplicação em produção (Render) fica inacessível com erro de timeout (The read operation timed out) ao requisitar a página inicial ou `/api/snapshot`.

## O que deveria acontecer
O serviço não deve apresentar timeout na requisição e travar os workers síncronos, permanecendo altamente disponível. As requisições de coleta síncrona aos dados da brapi.dev que limitam lotes não deviam realizar backoff longo em caso de HTTP 400, entupindo o worker HTTP da requisição e resultando no timeout 504 no load balancer.

## Evidência
A issue #733 de falha no app.acessivel mostra timeout. Rodando localmente curl -s https://devagent-vb52.onrender.com/api/snapshot sucessivamente reflete timeouts recorrentes confirmados. Isso advém de chamadas falhas para brapi.dev retornando HTTP 400 com retry.

## Como reproduzir
Inundar `/api/snapshot` com curl simulando tráfego durante a falha da Brapi.
