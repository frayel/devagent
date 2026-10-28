---
id: 2026-10-27-spec-098-ordem-fontes-ibovespa
severidade: media
painel: app/collectors/ibovespa.py
status: resolvido
visto_em: 2026-10-27T14:30-03:00
pr: 554
---

# Ordem de fallback errada para Ibovespa

## O que acontece
Em `app/collectors/ibovespa.py`, na função `collect_and_save` (linhas 192-203), se o MT5 não coletar os dados, a função chama `fetch_brapi()` primeiro. Somente se a Brapi falhar, ela chama `fetch_yfinance()`.

## O que deveria acontecer
O critério de aceite da spec 098 especifica claramente: "Coletores `ibovespa.py` e `mare.py` seguem MT5 -> Yahoo -> brapi". Portanto, o Yahoo Finance deveria ser tentado antes da Brapi.

## Evidência
```python
    if not data:
        data = fetch_brapi()
    if not data:
        logger.info("Falling back to yfinance...")
        data = fetch_yfinance()
```

## Como reproduzir
Basta ler o código da função `collect_and_save` em `app/collectors/ibovespa.py`.
