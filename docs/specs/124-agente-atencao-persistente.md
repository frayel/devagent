---
id: 124
titulo: Agente enxerga alertas persistentes em Atenção
status: ready
esforco: P
gaveta: saúde técnica
aceite: tests/test_aceite_124.py
---

## Problema

Alertas de nível *Atenção* podem ficar semanas na tela sem que nenhum passo do ciclo do agente os veja (como os quatro do dia 23/10/2026).

`devagent/saude.py` só abre a issue `sistema-com-problema` para itens de nível *Problema*. Precisamos que o agente os veja se durarem tempo demais.

## Comportamento esperado

### O ciclo do agente enxerga *Atenção* persistente

`devagent/saude.py` passa a tratar como pendente de ação, além dos *Problema*, todo item em *Atenção* ou *Inativo-inesperado* que persiste por 24 h (campo `desde`). A issue `sistema-com-problema` lista esses itens separados dos problemas, com causa, ação e idade. A chave que decide se há issue nova considera o conjunto de itens e continua estável entre leituras (o texto muda, a chave não). Item de *Atenção* abaixo de 24 h só aparece no resumo, sem issue. A regra de "Inativo esperado" (variável opcional ausente) não vira issue.

### Os alertas somem quando o defeito some

Depois de uma correção, o item deixa de aparecer na leitura seguinte; a issue é fechada pelo caminho já existente quando o conjunto de pendências zera. O corpo da issue diz a spec que trata cada item quando houver uma (campo opcional `spec` do item).

## Fontes de dados

Nenhuma requisição nova. Lê a `api/sistema`.

## Critérios de aceite

- [ ] Item em *Atenção* há 25 h gera pendência de ação na issue; há 23 h, não.
- [ ] A chave da issue não muda quando só o texto ou a hora do erro mudam.

## Invariantes de produção

- Item em *Atenção* há mais de 24 h está citado em uma issue `sistema-com-problema` aberta (verificado pelo auditor / rotina de saude).

## Fora do escopo

- Mudar a API de sistema (specs 122 e 123).
