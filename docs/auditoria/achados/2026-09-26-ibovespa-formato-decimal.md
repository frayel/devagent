---
id: 2026-09-26-ibovespa-formato-decimal
severidade: baixa
painel: ibovespa
status: aberto
visto_em: 2026-09-26T05:12-03:00
---

# Formato de variação percentual usa ponto em vez de vírgula

## O que o investidor vê
A variação percentual exibida para o Ibovespa é `+0.78%`, o que reflete o formato norte-americano (com ponto decimal).

## O que deveria ver
A variação no formato padrão brasileiro: `+0,78%`, o qual usa vírgula como separador decimal.

## Evidência
No HTML da página de produção:
```html
<div style="font-size: 1.2em; margin-top: 5px;"
     class="positive">
    +1.000 (+0.78%)
</div>
```

## Como reproduzir
Acessar `https://devagent-vb52.onrender.com` e inspecionar a variação em porcentagem do Ibovespa.

## Invariante proposta
Usar Regex para capturar os percentuais e garantir que usem `,` (vírgula) para separação das casas decimais.
