---
id: 2026-10-24-painel-exaustao-alta-ausente
severidade: alta
painel: exaustao_alta
status: aberto
visto_em: 2026-10-24T00:00:00-03:00
pr: 442
---

# Invariante falhada no snapshot

## O que acontece
O PR 442 prometeu adicionar o painel `exaustao_alta`. O código existe em `app/main.py` e `app/database.py`, mas a chave não foi incluída na resposta do endpoint `/api/snapshot` durante a execução, o que indica que não foi exposta de forma consistente com a regra do painel ou que falha quando vazia/não coletada. O teste `verify_prs.py` mostra apenas os painéis legados ou em banco e `exaustao_alta` não consta na saída de `/api/snapshot`. Além disso, a seção sobre "A chave exaustao_alta deve estar presente no /api/snapshot" (Invariante de produção) indica que a chave deve sempre existir (retornando lista, mesmo que vazia). O comportamento implementado na rota no arquivo `app/main.py` é condicional: `if exaustao_alta_data:`

## O que deveria acontecer
De acordo com os Critérios de Aceite e Invariantes da Spec 079:
- "A chave exaustao_alta deve estar presente no /api/snapshot e retornar uma lista (mesmo que vazia) de dicionários com chaves ticker e variacao."
A chave não deve estar ausente do snapshot quando não existirem dados coletados. Deve retornar de forma garantida.

## Evidência
Comando executado:
```python
import urllib.request, json
req = urllib.request.Request("http://127.0.0.1:8000/api/snapshot")
with urllib.request.urlopen(req) as response:
    data = json.loads(response.read().decode())
    print('exaustao_alta' in data['paineis'])
```
Retorno: `False`.
Trecho no arquivo `app/main.py`
```python
    exaustao_alta_data = get_latest_exaustao_alta_data()
    if exaustao_alta_data:
        resp["paineis"]["exaustao_alta"] = ...
```

## Como reproduzir
1. Inicie o servidor local ou faça `curl http://127.0.0.1:8000/api/snapshot`.
2. Observe as keys do dicionário de `paineis`. A chave `exaustao_alta` não existirá se o banco não possuir dados recém-coletados.
