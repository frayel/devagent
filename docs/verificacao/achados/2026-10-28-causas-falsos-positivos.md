---
id: 2026-10-28-causas-falsos-positivos
severidade: media
painel: app/services/sistema.py
status: aberto
visto_em: 2026-10-28T13:20-03:00
pr: 574
---

# Falsos positivos no preenchimento de causa e ação de banco

## O que acontece
A inicialização do objeto `Item` busca por palavras-chave com `in` simples para classificar como "esquema do banco incompleto": `elif any(x in texto for x in ("relation", "column", "does not exist")):`. Isso acaba gerando falsos positivos. Em particular, os painéis que mencionam "dolar_cor**relation**" no seu nome ou resumo acabam recebendo essa causa erroneamente, mesmo quando o nível de alerta é OK ou a falha é de coleta, não de banco.

## O que deveria acontecer
De acordo com os critérios de aceite (e bom senso para diagnóstico), a detecção da causa deveria usar limites de palavra (como `\b` em regex) para buscar as palavras do erro de banco, evitando que partes de palavras (como `dolar_correlation`) desencadeiem falsos positivos, e também não deve preencher a causa/ação para itens que estão OK.

## Evidência
Na saída do `/api/sistema`, itens de `OK` ou com erros de coleta exibem `causa: 'esquema do banco incompleto'` devido ao nome "dolar_correlation".

## Como reproduzir
Rode `uvicorn app.main:app` com um estado que menciona `dolar_correlation` no detalhe (como em "Duração da coleta") e consulte `/api/sistema`.
