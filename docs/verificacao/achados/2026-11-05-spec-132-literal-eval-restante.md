---
id: 2026-11-05-spec-132-literal-eval-restante
severidade: media
painel: app/main.py (rota consultor)
status: aberto
visto_em: 2026-11-05T09:00:00-03:00
pr: 755
---

# `app/main.py` ainda contém `literal_eval` da leitura antiga de consenso

## O que acontece
O PR #755 (implementação da spec 132) não removeu as chamadas a `ast.literal_eval` no processamento dos retornos históricos nas rotas `/consultor` e `/api/consultor` dentro de `app/main.py`. O código na main continua usando o `literal_eval` nas linhas ~426 e ~698 para ler o `consenso`.

## O que deveria acontecer
Conforme o critério de aceite explícito "app/main.py não contém literal_eval", a função única `armazenamento.ler_consenso(bruto)` deveria estar sendo usada no lugar e o `import ast` com o `literal_eval` removido do loop.

## Evidência
Comando: `grep -rn "literal_eval" app/main.py`
Resultado demonstra presença:
`app/main.py:426:                        consenso_dict = ast.literal_eval(row["consenso"])`
`app/main.py:698:                        consenso_dict = ast.literal_eval(row["consenso"])`

## Como reproduzir
1. Analise o arquivo `app/main.py` após o merge da Spec 132.
2. Note a presença de `ast.literal_eval(row["consenso"])` não refatorado no ramo `is_historical` de ambas as rotas.
