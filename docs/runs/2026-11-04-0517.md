---
status: done
step: 1
data: 2026-11-04T05:09:11.536536+00:00
---

# Correção da Issue #701

Resolvemos o defeito que causava a Calma zerar (caindo para 0.0, e outrora preenchendo None/0 devido a dados insuficientes) na coleta da volatilidade de quedas:

1. **Correção de Janela Insuficiente**: Em `app/collectors/mare.py`, alteramos o fallback do brapi para utilizar `range="2y"` (ao invés de `3mo`). Isso garante que a janela devolva dias suficientes para a exigência de `MINIMO_PERCENTIL = 120`.

2. **Tratamento de Anomalias**: A componente Calma zerava incorretamente na base do `yfinance` por conta de saltos de 14% que atuavam como defeitos na fonte de dados (artifacts), dominando o histórico de volatilidade. Ajustamos `app/services/mare.py` (`volatilidades`) para ignorar variações fora da realidade (> 12% em um único dia) para proteger a integridade do cálculo.
