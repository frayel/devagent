---
id: 2026-10-15-clima-global-ausente-snapshot
severidade: media
painel: clima_global
status: aberto
visto_em: 2026-10-15T20:50-03:00
---

# Painel Clima Global ausente da resposta da API de snapshot

## O que o investidor vê
Ao analisar a estrutura e os dados do site publicado por meio da API de snapshot `https://devagent-vb52.onrender.com/api/snapshot`, não há dados referentes ao painel `clima_global`. Os testes exploratórios via `curl` atestam que a chave `clima_global` em `/api/snapshot` inexiste em ambiente de produção, desrespeitando o contrato esperado.

## O que deveria ver
Conforme as especificações e o arquivo de invariantes `docs/specs/done/052-termometro-clima-externo.md`, a chave `clima_global` deve estar obrigatoriamente presente na rota `/api/snapshot` dentro da coleção de painéis, provendo dados consistentes de S&P500 e VIX.

## Evidência
Comando executado em ambiente produtivo:
```bash
curl -s https://devagent-vb52.onrender.com/api/snapshot | jq '.paineis.clima_global'
```
Resultado retornado: `null`

A auditoria determinística do comando `make audit` registrou em log: `⚠️ clima_global.chave: Termômetro de Clima Externo ausente no snapshot`.

## Como reproduzir
1. Realize uma requisição HTTP GET no endpoint de produção: `https://devagent-vb52.onrender.com/api/snapshot`
2. Parseie o arquivo JSON devolvido e procure pela chave `clima_global` sob `paineis`. Notará a total ausência desta árvore de dados.

## Invariante proposta
A checagem em `auditar.py` denominada `clima_global.chave` já alerta a inexistência, porém o bug permanece em produção até ser propriamente fixado na rota `/api/snapshot` de `app/main.py` de modo independente dos valores estarem vazios por erro na inicialização do coletor de produção. O snapshot não deve omitir o painel, apenas mapeá-lo.
