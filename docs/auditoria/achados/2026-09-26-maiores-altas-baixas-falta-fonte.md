---
id: 2026-09-26-maiores-altas-baixas-falta-fonte
severidade: media
painel: altas-baixas
status: aberto
visto_em: 2026-09-26T05:12-03:00
---

# Painel Altas e Baixas não exibe a fonte dos dados

## O que o investidor vê
O painel de maiores altas e maiores baixas informa um horário de atualização (`Última atualização: 26/09/2026 04:13:55 UTC`), mas não declara a fonte consultada.

## O que deveria ver
A indicação clara da fonte que proveu a classificação dos ativos, o que garante a honestidade (seção 2 do `AGENTS.md`).

## Evidência
No HTML da página de produção:
```html
<div class="text-small" style="margin-top: 10px;">
    Última atualização: 26/09/2026 04:13:55 UTC
</div>
```
Não há menção à Brapi ou ao Yahoo Finance.

## Como reproduzir
Acessar `https://devagent-vb52.onrender.com` e inspecionar a base das tabelas "Maiores Altas" e "Maiores Baixas".

## Invariante proposta
Verificar que a menção de horário venha acompanhada do texto com a fonte do dado (`yfinance`, `brapi` ou semelhante).
