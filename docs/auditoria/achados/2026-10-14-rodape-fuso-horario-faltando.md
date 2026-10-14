---
id: 2026-10-14-rodape-fuso-horario-faltando
severidade: media
painel: multiplos
status: aberto
visto_em: 2026-10-14T01:18+00:00
---

# Rodapés exibem horário sem o fuso horário (BRT) obrigatório

## O que o investidor vê
No ambiente de produção, embora a maioria dos rodapés apresente a formatação correta de data e fuso (ex: `Fonte mt5 · 13/10/2026 21:38:05 BRT`), há ocorrências em painéis onde a string finaliza após os segundos, omitindo o fuso (ex: `Fonte yfinance · 13/10/2026 21:38:05`).

## O que deveria ver
A seção de convenções do `PRODUTO.md` é clara: "fuso horário explícito (BRT)". Todos os rodapés de painel, sem exceção, precisam indicar o fuso horário BRT ao lado do horário da coleta para garantir a honestidade e clareza.

## Evidência
Comando executado via `curl` no HTML de produção revelou duas instâncias da anomalia. Por exemplo, na renderização do *Scanner de Capitulação*:
```html
<section class="painel span-4 visao-micro alertas">
  <div class="cab">
    <h2>Scanner de Capitulação</h2>
    ...
  </div>
  <div class="vazio">Nenhum clímax de capitulação detectado hoje.</div>
  <div class="rodape">Fonte yfinance · 13/10/2026 21:38:04</div>
</section>
```

## Como reproduzir
1. Acessar https://devagent-vb52.onrender.com/
2. Inspecionar o rodapé do painel *Scanner de Capitulação* e de outros painéis próximos.
3. Observar a ausência da string " BRT" no final do texto do elemento `.rodape`.

## Invariante proposta
O auditor determinístico (`auditoria/auditar.py`) deve percorrer todos os elementos da classe `.rodape` na página inicial e garantir que o texto de cada um obrigatoriamente termine com a substring " BRT".
