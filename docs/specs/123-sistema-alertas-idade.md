---
id: 123
titulo: Idade dos alertas no sistema
status: ready
esforco: P
gaveta: saúde técnica
aceite: tests/test_aceite_123.py
---

## Problema

Como o dono do produto descobre há quanto tempo um alerta da página de sistema está pendente?

## Comportamento esperado

### Há quanto tempo

Cada item pendente no sistema mostra "desde dd/mm HH:MM" (primeira leitura em que apareceu com esse nível). O monitor (`app/collectors/sistema.py`) guarda essa primeira vez por chave do item (grupo e nome) na memória do processo e no banco de dados (usando a tabela unificada `snapshots_paineis` sob o painel `sistema_alertas` para persistência), para sobreviver a um reinício. Item que volta a *OK* é removido da persistência.

## Fontes de dados

Só dados que `/sistema` já tem. Nenhuma requisição nova.

## Critérios de aceite

- [ ] `/sistema` mostra "desde dd/mm HH:MM" para itens em *Atenção* e *Problema*.
- [ ] `/api/sistema` traz `desde` por pendência.
- [ ] Item que volta a *OK* é removido da persistência em `snapshots_paineis`; um reinício mantém o `desde` dos que continuam.

## Invariantes de produção

- (Nenhuma nova; o auditor continua verificando o `/api/snapshot` normalmente).

## Fora do escopo

- Agente ler a persistência para abrir issue (spec 124).
