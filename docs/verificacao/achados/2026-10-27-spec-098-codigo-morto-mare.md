---
id: 2026-10-27-spec-098-codigo-morto-mare
severidade: baixa
painel: app/collectors/mare.py
status: resolvido
visto_em: 2026-10-27T14:30-03:00
pr: 554
---

# Código morto em coletor da maré

## O que acontece
Em `app/collectors/mare.py`, a variável `URL_IBOV_BRAPI_DEPRECATED` (linhas 36-39) não foi removida durante a migração, apesar da função `fetch_ibovespa_brapi` não existir mais.

## O que deveria acontecer
Código morto deve ser removido para manter a base de código limpa, o novo módulo centraliza o uso da URL da Brapi.

## Evidência
```python
URL_IBOV_BRAPI_DEPRECATED = (
    "https://brapi.dev/api/quote/%5EBVSP?token={token}&range=2y&interval=1d"
    "&fundamental=false"
)
```

## Como reproduzir
Ler as primeiras linhas de `app/collectors/mare.py`.
