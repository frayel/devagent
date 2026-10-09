---
id: 2026-10-08-paineis-sem-dados-e-rodape
severidade: media
painel: multiplos
status: resolvido
resolvido_em: 2026-10-09
evidencia: Template `componentes.html` alterado para renderizar 'Fonte e data não disponíveis' quando as variáveis faltam, e invariante de rodapés vazios criada em `auditar.py`.
visto_em: 2026-10-08T22:30-03:00
---

# Múltiplos painéis exibem "Dado indisponível agora" e omitem fonte e data no rodapé

## O que o investidor vê
Ao acessar o site em produção (https://devagent-vb52.onrender.com), diversos painéis (como Concentração Setorial, Rotação de Capital, Variação Súbita, Radar de Faca Caindo, Scanner de Capitulação, Armadilhas de Abertura, Compradores de Fundo, Sempre Verde e Volatilidade Silenciosa) exibem a mensagem "Dado indisponível agora. A fonte não respondeu na última coleta." em vez do conteúdo. Nesses casos, o rodapé exibe apenas "Fonte  · ", sem identificar qual foi a fonte tentada, a data da falha ou o fuso horário (BRT).

## O que deveria ver
Mesmo quando a fonte falha (degradando apenas o seu painel, como exige o checklist de `PRODUTO.md`), o rodapé deveria indicar a última data da tentativa de coleta ou qual fonte foi usada, para garantir a "Honestidade" (toda informação, mesmo a falta dela, deve ter rastro). No mínimo, a ausência de dados não deve resultar num texto em branco ou "Fonte ·" incompleto, e a mensagem de erro deve explicitar que o dado está desatualizado com contexto correto (como "Quando uma fonte cai, a tela diz que o dado está desatualizado", conforme a seção de Inspeção Exploratória em auditor.md).

## Evidência
Na página de produção em 2026-10-08, 9 painéis apresentam o bloco:
```html
<div class="vazio">
  Dado indisponível agora.<br>A fonte não respondeu na última coleta.
</div>
```
E os mesmos 9 painéis possuem o rodapé malformado:
```html
<div class="rodape">Fonte  · </div>
```

## Como reproduzir
1. Acesse `https://devagent-vb52.onrender.com/`.
2. Role a página e veja os painéis indicando "Dado indisponível agora".
3. Observe o rodapé correspondente mostrando apenas "Fonte  · ".

## Invariante proposta
Verificar no auditor determinístico se os painéis, mesmo em estado de erro (com a classe `.vazio`), renderizam a fonte e a data da última tentativa no rodapé, ou uma mensagem padrão que não quebre a formatação.
