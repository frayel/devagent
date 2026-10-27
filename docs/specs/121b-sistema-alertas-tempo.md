---
id: 121b
titulo: Persistência com issue de atenção prolongada no sistema de alertas
status: ready
esforco: M
gaveta: saúde técnica
aceite: tests/test_aceite_121b.py
revisada: 2026-10-27
---

## Problema
Por que os alertas de atenção do sistema não geram uma notificação se persistirem por muito tempo? `devagent/saude.py` só abre a issue `sistema-com-problema` para itens de nível *Problema*. Item em *Atenção* pode ficar semanas na tela sem que nenhum passo do ciclo o veja. A issue atual também não diz quando o alerta nasceu.

## Comportamento esperado
1. Cada item pendente na página de sistema mostra "desde dd/mm HH:MM" (primeira leitura em que apareceu com esse nível).
2. O monitor (`app/collectors/sistema.py`) guarda essa primeira vez por chave do item (grupo e nome) na memória do processo e no banco de dados (usando a tabela unificada `snapshots_paineis` sob o painel `sistema_alertas` para persistência), para sobreviver a um reinício. Item que volta a *OK* é removido da persistência.
3. `devagent/saude.py` passa a tratar como pendente de ação, além dos *Problema*, todo item em *Atenção* ou *Inativo-inesperado* que persiste por 24 h (campo `desde`). A issue `sistema-com-problema` lista esses itens separados dos problemas, com causa, ação e idade.
4. A chave que decide se há issue nova considera o conjunto de itens e continua estável entre leituras. Item de *Atenção* abaixo de 24 h só aparece no resumo, sem issue.

## Fontes de dados
Só dados que `/sistema` já tem. Banco de dados `snapshots_paineis`.

## Critérios de aceite
- [ ] Item que volta a *OK* é removido da persistência em `snapshots_paineis`; um reinício mantém o `desde` dos que continuam.
- [ ] Item em *Atenção* há 25 h gera pendência de ação na issue; há 23 h, não. Modifica `devagent/tests/test_saude.py` e `devagent/saude.py`.
- [ ] A chave da issue não muda quando só o texto ou a hora do erro mudam.
- [ ] A página `/sistema` e a api `/api/sistema` expõem o campo `desde`.
- Esta spec tocará `app/collectors/sistema.py`, `app/services/sistema.py`, `devagent/saude.py`, `devagent/tests/test_saude.py`, `tests/test_sistema.py` e um novo `tests/test_aceite_121b.py` (6 arquivos no total).

## Invariantes de produção
- Item em *Atenção* há mais de 24 h está citado em uma issue `sistema-com-problema` aberta.

## Fora do escopo
- Adicionar causa e ação na página (Spec 121a).
