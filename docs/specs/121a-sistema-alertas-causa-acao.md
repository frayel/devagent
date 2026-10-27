---
id: 121a
titulo: Guia de resolução para alertas da página de sistema
status: ready
esforco: P
gaveta: saúde técnica
aceite: tests/test_aceite_121a.py
revisada: 2026-10-27
---

## Problema
Como o dono do produto descobre o que fazer com os alertas da página de sistema?

A página `/sistema` lista alertas, mas deixa o dono do produto adivinhar o que fazer, não dizendo se o defeito é do pedido ou do servidor externo, nem o que seria preciso fazer.

## Comportamento esperado
`Item` (`app/services/sistema.py`) ganha os campos `causa` e `acao`, curtos (uma frase cada), e o JSON de `/api/sistema` (que `devagent/saude.py` lê) os repete. A página os mostra abaixo do resumo, em *Atenção* e *Problema*. Regras de preenchimento, com a origem do defeito dita explicitamente:

- **Pedido errado** (HTTP 400, 404 em símbolo específico, 422): causa "pedido inválido ou ativo desconhecido (HTTP N)", ação "corrigir o pedido no coletor X; o servidor está respondendo".
- **Fonte fora do ar** (rede, 5xx, 429, 401, 403): causa "fonte indisponível ou recusando a chave (HTTP N)", ação "aguardar, ou conferir a chave no Render".
- **Banco ou esquema** (erro com `relation`, `column`, `does not exist`): causa "esquema do banco incompleto", ação "falta migração; ver spec do Consultor".
- **Integração sem chamadas**: causa "configurada, mas nunca chamada", ação "verificar o pipeline que a usa".
- Erro desconhecido: causa "causa não classificada", ação "ver o detalhe e abrir issue".

Depois de uma correção, o alerta soma quando o defeito some.

## Fontes de dados
Só dados que `/sistema` já tem. Nenhuma requisição nova.

## Critérios de aceite
- [ ] Cada categoria de falha (pedido errado, fonte fora do ar, esquema, sem chamadas, desconhecido) recebe causa e ação esperadas (testes com itens de fixture). Modifica `tests/test_sistema.py`.
- [ ] `/sistema` mostra causa e ação para itens em *Atenção* e *Problema*, sem rolagem horizontal em 390 px.
- [ ] `/api/sistema` traz `causa` e `acao` por pendência, e o núcleo (`devagent/saude.py`) continua lendo contratos antigos sem esses campos.
- [ ] Nenhum segredo aparece nos novos campos.
- Esta spec tocará `app/services/sistema.py`, `app/main.py`, `app/templates/sistema.html`, `tests/test_sistema.py` e um novo `tests/test_aceite_121a.py` (5 arquivos no total).

## Invariantes de produção
- Nenhum item de `/sistema` em *Atenção* ou *Problema* aparece sem causa e ação.

## Fora do escopo
- Corrigir a causa de cada alerta.
- Implementar o cálculo de tempo do alerta ("desde dd/mm HH:MM") (Spec 121b).
