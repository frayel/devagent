---
id: 109a
titulo: Consultor: timestamps reais em get_historico_diario
status: draft
esforco: P
gaveta: experiência
aceite: tests/test_aceite_109a.py
revisada: 2026-10-25
---

## Problema

`get_historico_diario` em `app.database` devolve `"timestamp": [1] * len(closes)` (um carimbo fictício de 1 segundo desde 1970). Qualquer lógica que dependa desses carimbos (alinhamento de séries em `avaliador_historico.pre_processar_ativo`) trabalha com dados falsos. Isso impede a correta visualização da data das informações na tela do consultor.

## Comportamento esperado

`get_historico_diario` passa a devolver, para cada ativo, os timestamps reais das barras (epoch em segundos do pregão, a partir do campo `data` de cada barra gravada por `gravar_serie`), e `coletado_em`, o maior `criado_em` das linhas lidas de `series_diarias`.
Antes de mudar, o desenvolvimento confere que os testes de `calculador` e `avaliador_historico` continuam verdes e adapta-os se precisarem.

## Fontes de dados

Só o banco local.

## Critérios de aceite (1 arquivo de teste editado)

- [ ] `get_historico_diario` devolve timestamps reais e monotônicos para uma série de fixture (nenhum valor igual a 1) e `coletado_em`.

## Revisão
A spec 109a é inviável/duplicada porque a funcionalidade descrita (obter timestamps reais em `get_historico_diario`) já foi especificada e está presente em `docs/specs/108a-consultor-timestamps-reais.md`, que também já foi revisada. O desenvolvimento já tem essa demanda através da spec 108a.
