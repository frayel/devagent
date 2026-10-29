---
id: 2026-10-29-api-snapshot-contrato
severidade: media
painel: /api/snapshot (exaustao_queda e exaustao_alta)
status: resolvido
visto_em: 2026-10-29T10:15:00-03:00
pr: 609
---

# PR 609 viola contrato da API /snapshot (formato de data e objeto vazio) e duplica código

## O que acontece
No PR #609, ao inserir `exaustao_queda` e `exaustao_alta` no endpoint `/api/snapshot` para evitar KeyError (timeout indireto no snapshot), o código que os atribui usou o formato local (`.strftime("%d/%m/%Y %H:%M:%S BRT")`) para `coletado_em`, em vez do padrão ISO `.isoformat()` esperado pelo contrato da API JSON. Além disso, se os alertas não estiverem presentes, a chave de `exaustao_queda` se torna um dicionário vazio `{}`, omitindo as chaves contratuais exigidas (`fonte` e `coletado_em`), o que é proibido pelo contrato (Memory: "The /api/snapshot endpoint contract requires that all panel entries within the paineis dictionary be objects and explicitly expose the keys fonte and coletado_em"). Para piorar, a inserção da lógica (nas linhas ~1464-1481 de `app/main.py`) foi parcialmente replicada na view da página index (linhas ~1708+).

## O que deveria acontecer
O endpoint `/api/snapshot` não deve formatar a data como `DD/MM/YYYY HH:MM:SS BRT`, mas sim retornar as datas em ISO 8601 `.isoformat()`. Mesmo quando o painel não tiver alertas (seus dados forem nulos), as chaves obrigatórias `fonte` e `coletado_em` devem estar presentes se houver `exaustao_queda_data` coletado. Se não houver nenhum dado coletado, ele não precisaria sequer adicionar a chave ao invés de forçar `{}` de maneira crua e sem chaves mínimas. A lógica entre `snapshot` e `index` deveria ter escopos corretos sem copiar/colar cego (index formatado, API em ISO).

## Evidência
Comando executado: `curl -s http://127.0.0.1:8000/api/snapshot | jq .paineis.exaustao_queda`
Retorno real: `{}`
Isso indica que mesmo que haja dados de exaustao_queda, ele está vazio quando deveria ter pelo menos `"fonte"` e `"coletado_em"`.
O trecho incorreto em `app/main.py`:
```python
    if exaustao_queda_data:
        alertas = json.loads(exaustao_queda_data.alertas_json)
        if alertas:
            exaustao_queda = {
                "coletado_em": exaustao_queda_data.timestamp.astimezone(
                    timezone(timedelta(hours=-3))
                ).strftime("%d/%m/%Y %H:%M:%S BRT"),
                "fonte": exaustao_queda_data.fonte,
                "alertas": alertas,
            }
    # ...
    if exaustao_queda:
        resp["paineis"]["exaustao_queda"] = exaustao_queda
    else:
        resp["paineis"]["exaustao_queda"] = {}
```

## Como reproduzir
Rodar a aplicação com a coleta de `exaustao_queda` que retorna zero alertas, acessar `/api/snapshot` e verificar a chave `paineis.exaustao_queda` não tem as propriedades obrigatórias.
