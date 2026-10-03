---
id: 2026-10-03-fuso-horario-forca-escudo
severidade: media
painel: global
status: aberto
visto_em: 2026-10-03T01:00-03:00
---

# Painéis Força Relativa e Escudo contra Quedas estão exibindo a última atualização sem BRT e sem data

## O que o investidor vê
No rodapé dos painéis Força Relativa e Escudo contra Quedas, exibe-se, por exemplo: `Fonte yfinance · 00:43`.

## O que deveria ver
O fuso exibido deve ser o brasileiro e conter a data, conforme convenções de `PRODUTO.md` ("fuso horário explícito (BRT)" e "datas dd/mm/aaaa"). Exemplo: `03/10/2026 00:43:00 BRT`.

## Evidência
Na página principal de produção, o HTML traz:
```html
<div class="rodape">Fonte yfinance · 00:43</div>
```

## Como reproduzir
Acessar a URL de produção e checar os rodapés dos painéis "Força Relativa (30 dias)" e "Escudo contra Quedas".

## Invariante proposta
Verificar no auditor determinístico se todas as strings de última atualização contêm o sufixo "BRT" e seguem o padrão completo de data e hora.
