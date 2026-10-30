---
id: 2026-10-29-producao-fora-do-ar
severidade: alta
painel: todos
status: resolvido
resolvido_em: 2026-10-29
visto_em: 2026-10-29T01:13-03:00
---

# Produção fora do ar respondendo HTTP 500

## O que o investidor vê
A página inicial da aplicação em produção não carrega, devolvendo um erro 500 (Internal Server Error).

## O que deveria ver
A página inicial do produto contendo todos os painéis e o dashboard funcional.

## Evidência
Ao executar `curl -i "https://devagent-vb52.onrender.com/"` e `curl -i "https://devagent-vb52.onrender.com/api/snapshot"`, ambas retornam:
```
HTTP/2 500
date: Thu, 29 Oct 2026 01:18:42 GMT
content-type: text/plain; charset=utf-8
cf-cache-status: DYNAMIC
rndr-id: 68971aa4-735a-4af7
server: cloudflare
vary: Accept-Encoding
x-render-origin-server: uvicorn
cf-ray: a51e5901fbeb90bd-ORD
alt-svc: h3=":443"; ma=86400

Internal Server Error
```

## Como reproduzir
1. Navegar para https://devagent-vb52.onrender.com/ no navegador
2. Ou executar no terminal `curl -i "https://devagent-vb52.onrender.com/"`

## Invariante proposta
O auditor determinístico já verifica se a página inicial e a API devolvem 200, então não é necessária uma invariante nova (a regra `app.home Página inicial responde 200` falha automaticamente).

## Resolução
Verificado em 2026-10-29. A página inicial `https://devagent-vb52.onrender.com/` e a rota `https://devagent-vb52.onrender.com/api/snapshot` agora respondem com HTTP 200, e a aplicação carrega corretamente. O auditor determinístico executou com 0 falhas (26 checagens verificadas).
