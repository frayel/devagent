---
id: 2026-10-23-paineis-fuso-horario-incompleto
severidade: media
painel: multiplos
status: resolvido
visto_em: 2026-10-23T00:15-03:00
---

# Painéis exibindo data/hora de forma incompleta no rodapé

## O que o investidor vê
Em alguns painéis (como "Clima Global", "Fator Peso Pesado", e "Concentração de Ordens"), o rodapé exibe horários sem o ano ou sem a data completa. Por exemplo:
- `Fonte yfinance · 22/10 19:39 BRT` (Falta o ano 2026)
- `Fonte brapi · 22:39 BRT` (Falta a data completa)

## O que deveria ver
O formato de data e horário deve seguir rigorosamente as convenções de `PRODUTO.md`: "datas dd/mm/aaaa" e "fuso horário explícito (BRT)". O esperado é algo como `22/10/2026 19:39 BRT` ou `22/10/2026 22:39:00 BRT`.

## Evidência
Na página de produção de 2026-10-23, o HTML contém rodapés como:
```html
<div class="rodape">Fonte yfinance · 22/10 19:39 BRT</div>
```
e
```html
<div class="rodape">Fonte brapi · 22:39 BRT</div>
```

## Como reproduzir
1. Acesse `https://devagent-vb52.onrender.com`.
2. Verifique o rodapé dos painéis "Clima Global", "Fator Peso Pesado" ou "Concentração de Ordens".

## Invariante proposta
Verificar com uma expressão regular no HTML se o texto após "Fonte" contém o padrão de data completo `dd/mm/aaaa`.

## Resolução
Verificado em produção no dia 23/10/2026 às 21:00 BRT: os rodapés foram corrigidos e agora exibem a data completa, como `23/10/2026 18:48:22 BRT`.
