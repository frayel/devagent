---
id: 099
titulo: brapi como fonte secundária, com uma chamada por ativo (Orçamento e Lote 2)
status: ready
esforco: M
gaveta: saúde técnica
---

## Problema

Dando continuidade à spec 098, precisamos controlar o orçamento mensal da brapi e migrar os coletores de cotação em lote para o novo módulo.

## Comportamento esperado

### 1. Orçamento de requisições

- Contador de chamadas à brapi persistido no banco (dia e mês corrente).
- `BRAPI_LIMITE_MENSAL` (padrão 15000). Teto diário = 90% do limite mensal dividido pelos dias do mês.
- Antes de cada chamada em `app/collectors/brapi.py`, o módulo confere o teto. Acabou: não chama, devolve `None` e registra motivo `orçamento`.

### 2. Página de sistema

O item "brapi" de `/sistema` mostra: chamadas no dia e mês, estado do disjuntor, avisos acima de 80% e problema se 403.

### 3. Ordem das fontes (Lote 2)

Migrar `concentracao_ordens.py`, `highlights.py`, `radar_anomalias_spread.py`, `concentracao_setorial.py`, `fator_mola.py` e `coesao.py` para usar `app/collectors/brapi.py` e ordem MT5 -> Yahoo -> brapi (só os faltantes).

Em `concentracao_ordens.py` (painel depende de trades que o Yahoo não traz): Se mt5 não tem, brapi é a fonte primária, com **no máximo uma atualização por hora** no pregão.

## Critérios de aceite e testes tocados (6 testes)

- [ ] Orçamento diário esgotado impede novas chamadas (`tests/test_brapi.py`).
- [ ] O contador sobrevive a reinício (`tests/test_brapi.py`).
- [ ] `/sistema` mostra consumo e disjuntor (`tests/test_sistema.py`).
- [ ] Nenhuma URL `brapi.dev/api/quote/` com mais de um ticker existe em `app/`.
- [ ] Concentração de ordens atualiza no máximo uma vez por hora pela brapi (`tests/test_concentracao_ordens.py`).
- [ ] Todos os coletores do Lote 2 usam `brapi.py` buscando só os faltantes (`tests/test_concentracao_setorial.py`, `tests/test_highlights.py`, `tests/test_radar_anomalias_spread.py`, etc).
