---
id: 2026-10-02-fuso-horario-utc
severidade: media
painel: global
status: resolvido
visto_em: 2026-10-02T01:05-03:00
---

# Todos os painéis estão exibindo a última atualização em UTC em vez de BRT

## O que o investidor vê
No rodapé de vários painéis, exibe-se, por exemplo: `Última atualização: 02/10/2026 01:05:56 UTC`.

## O que deveria ver
O fuso exibido deve ser o brasileiro, conforme convenções de `PRODUTO.md` ("fuso horário explícito (BRT)").

## Evidência
Na página principal de produção, o HTML traz:
```html
<div class="text-small" style="margin-top: 15px;">
    Última atualização: 02/10/2026 01:05:56 UTC | Fonte: yfinance
</div>
```

## Como reproduzir
Acessar a URL de produção e checar os rodapés (text-small) dos painéis.

## Invariante proposta
Verificar em todo o HTML se o texto de última atualização acompanha a string "BRT".

## Resolução
Feito. Corrigido para BRT.
