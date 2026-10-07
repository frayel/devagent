---
id: 2026-10-06-paineis-sem-rodape-visivel
severidade: media
painel: multiplos
status: aberto
visto_em: 2026-10-06T01:50-03:00
---

# Painéis sem exibição correta do rodapé e fontes

## O que o investidor vê
Ao acessar o site em produção (https://devagent-vb52.onrender.com), o investidor se depara com painéis (ex. Apetite a Risco, Atrasadas do Rally, Armadilhas de Abertura) que não possuem rodapé mostrando a fonte de dados, horário de coleta ou o fuso horário (BRT). Além disso, alguns painéis mostram `Fonte yfinance · HH:MM` omitindo a data e o fuso, ou `Fonte  · ` sem dados.

## O que deveria ver
Todo painel exibido precisa conter, na sua base (rodapé), a informação da fonte de dados, da data de coleta e do horário em fuso BRT, garantindo o "Honestidade" especificado em `PRODUTO.md`.

## Evidência
Comando executado via selectolax no HTML de produção confirmou ausência da classe `.rodape` dentro das `.painel` para diversos componentes recém adicionados e malformação (apenas horas) em outros.

## Como reproduzir
1. Acesse https://devagent-vb52.onrender.com/
2. Vá até os painéis de Atrasadas do Rally, Apetite a Risco, ou Armadilhas de Abertura.
3. Observe que não há rodapé válido com `Fonte`, `Data` e `BRT`.

## Invariante proposta
O HTML de cada `.painel` renderizado deve possuir um `.rodape` não vazio contendo `Fonte`, `BRT` e data no formato `DD/MM/YYYY`.

**Atualização (06/10/2026):** A invariante proposta foi automatizada em `auditar.py`. Apesar de muitos painéis terem sido corrigidos, `Concentração Setorial` e `Volatilidade Silenciosa` ainda renderizam rodapés fora do formato correto de data (apresentam ISO datetime no lugar de DD/MM/YYYY). A issue permanece aberta.
