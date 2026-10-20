---
id: 2026-10-20-detector-acao-orfa-ausente-snapshot
severidade: media
painel: detector_acao_orfa
status: aberto
visto_em: 2026-10-20T00:40:58+00:00
---

# Detector de Ação Órfã ausente no snapshot

## O que o investidor vê
Ao analisar a estrutura e os dados do site publicado por meio da API de snapshot `https://devagent-vb52.onrender.com/api/snapshot`, não há dados referentes ao painel `detector_acao_orfa`. Os testes exploratórios via `curl` atestam que a chave `detector_acao_orfa` em `/api/snapshot` inexiste em ambiente de produção, desrespeitando o contrato esperado.

## O que deveria ver
A chave `detector_acao_orfa` deve estar presente na rota `/api/snapshot` dentro da coleção de painéis.

## Evidência
Comando executado em ambiente produtivo:
```bash
curl -s https://devagent-vb52.onrender.com/api/snapshot | jq '.paineis.detector_acao_orfa'
```
Resultado retornado: `null`

A auditoria determinística do comando `make audit` registrou em log: `⚠️ detector_acao_orfa.chave: Detector de ação órfã ausente no snapshot`.

## Como reproduzir
1. Realize uma requisição HTTP GET no endpoint de produção: `https://devagent-vb52.onrender.com/api/snapshot`
2. Parseie o arquivo JSON devolvido e procure pela chave `detector_acao_orfa` sob `paineis`. Notará a total ausência desta árvore de dados.

## Invariante proposta
A checagem em `auditar.py` denominada `detector_acao_orfa.chave` já alerta a inexistência.
