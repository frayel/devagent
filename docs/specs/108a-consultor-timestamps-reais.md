---
id: 108a
titulo: Banco de dados devolve timestamps reais e data da coleta das séries
status: done
esforco: P
gaveta: saúde técnica
aceite: tests/test_aceite_108a.py
revisada: 2026-10-25
---

## Problema

`app.database.get_historico_diario` devolve `"timestamp": [1] * len(closes)` (um carimbo fictício de 1 segundo desde 1970). Qualquer lógica que dependa desses carimbos (alinhamento de séries em `avaliador_historico.pre_processar_ativo`) trabalha com dados falsos. Além disso, não há como saber quando a série foi coletada para calcular defasagem.

## Comportamento esperado

### Carimbos reais

`get_historico_diario` passa a devolver, para cada ativo, os timestamps reais das barras (epoch em segundos do pregão, a partir do campo `data` de cada barra gravada por `gravar_serie`), e `coletado_em`, o maior `criado_em` das linhas lidas de `series_diarias`. Antes de mudar, o desenvolvimento lista todos os chamadores (`calculador`, `avaliador_historico`, `utils`) e confere que nenhum depende do valor fictício; os testes existentes devem continuar passando.

## Fontes de dados

Só o banco local. Nenhuma requisição nova.

## Cálculos

Nenhum cálculo novo.

## Critérios de aceite

- [ ] `get_historico_diario` devolve timestamps reais e monotônicos para uma série de fixture (nenhum valor igual a 1).
- [ ] `get_historico_diario` devolve `coletado_em` correto baseado no `criado_em` da barra mais recente da série.
- [ ] Testes existentes que chamam `get_historico_diario` continuam passando sem alterações na lógica de negócio principal.

## Invariantes de produção

- A função `get_historico_diario` sempre retorna timestamps crescentes para uma mesma série.

## Fora do escopo

- Alterar a interface do Consultor para mostrar as datas (será feito na spec 108b).
