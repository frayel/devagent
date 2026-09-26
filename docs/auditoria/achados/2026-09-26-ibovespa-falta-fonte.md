---
id: 2026-09-26-ibovespa-falta-fonte
severidade: media
painel: ibovespa
status: aberto
visto_em: 2026-09-26T05:12-03:00
---

# Painel Ibovespa não exibe a fonte dos dados

## O que o investidor vê
O painel exibe "Última atualização: 26/09/2026 04:13:56 UTC", mas não informa de onde vieram os dados.

## O que deveria ver
A informação deve incluir claramente o nome e, se possível, a URL da fonte que originou os dados (ex: Yahoo Finance, Brapi), de acordo com a exigência da seção 2 do `AGENTS.md` (Toda informação mostra fonte, data e horário da coleta).

## Evidência
O trecho de HTML extraído da página principal mostra:
```html
<div class="text-small" style="margin-top: 10px;">
    Última atualização: 26/09/2026 04:13:56 UTC
</div>
```

## Como reproduzir
Acessar `https://devagent-vb52.onrender.com` e inspecionar visualmente o painel de Ibovespa.

## Invariante proposta
Verificar se os blocos de atualização contêm palavras-chave relativas às fontes, por exemplo, verificando o texto das tags com classe `text-small`.
