---
id: 124
titulo: Seletor de pregão mostra os números do dia escolhido
status: ready
esforco: M
gaveta: saúde técnica
aceite: tests/test_aceite_124.py
---

## Problema
Quem escolhe um pregão anterior no seletor vê a faixa "Você está vendo o fechamento de dd/mm/aaaa", mas os painéis continuam com os números do último pregão gravado. A spec 088 prometia "`GET /?data=<pregão fixture>` devolve os números desse pregão"; o teste dela (`tests/test_aceite_088.py`) só confere o `<select>` e a faixa, nunca um número.

Reprodução (revisão de 28/10/2026): grava-se o Ibovespa de 26/10 com 100 e o de 27/10 com 200; com `_data_referencia_snapshot` em 26/10, `get_latest_ibovespa_data()` devolve 200.

Causa:
1. `index` (`app/main.py`) e `snapshot` (`/api/snapshot`) guardam a data em `app.banco._data_referencia_snapshot`.
2. Esse `ContextVar` só é lido em `gravar_snapshot` (`app/banco.py`), para o agendador gravar no pregão certo.
3. `ler_snapshot(painel)` sem `data_referencia` sempre traz o mais recente, e todos os `get_latest_*` de `app/database.py` o chamam assim.
4. `index` nunca restaura o valor que alterou.

O texto "Sem registro neste pregão", também prometido pela 088, não existe em nenhum template.

## Comportamento esperado
- Um contexto de leitura separado do de gravação: `app.banco.lendo_pregao(data)`, um gerenciador de contexto (`with`) sobre um `ContextVar` próprio, que sempre restaura o valor anterior (`reset` do token), inclusive em exceção.
- Dentro desse contexto, `ler_snapshot(painel)` sem data filtra pelo dia do contexto. Fora dele, continua trazendo o mais recente.
- `index` e `snapshot` usam `lendo_pregao(data_ref)` quando `is_historical`, e deixam de tocar em `_data_referencia_snapshot`, que volta a ser só do agendador.
- Numa data passada, painel sem snapshot naquele dia mostra "Sem registro neste pregão" no lugar de "Dado indisponível agora", e nunca o dado de outro dia. Os demais painéis aparecem normalmente.
- Em `/api/snapshot?data=`, o painel sem snapshot no dia vem `null`.

## Fontes de dados
Nenhuma. Só leitura de `snapshots_paineis`.

## Cálculos
Nenhum novo.

## Critérios de aceite
- [ ] Com o Ibovespa gravado como `final` em D1 (111.111) e D2 (222.222), `GET /api/snapshot?data=D1` traz `paineis.ibovespa.valor == 111111` e `GET /api/snapshot` sem data traz 222222.
- [ ] `GET /?data=D1` contém o valor de D1 como a página o formata e não contém o de D2.
- [ ] Com um painel gravado só em D2, `GET /?data=D1` mostra "Sem registro neste pregão" para ele, e `/api/snapshot?data=D1` traz esse painel como `null`.
- [ ] Depois de uma requisição histórica, `get_latest_ibovespa_data()` fora de requisição devolve D2 (o contexto não vaza).
- [ ] `lendo_pregao` restaura o valor anterior quando o bloco levanta exceção.
- [ ] `tests/test_agendador.py` e `tests/test_aceite_088.py` continuam verdes.
- Arquivos tocados: `app/banco.py`, `app/main.py`, o template do componente de painel indisponível (`app/templates/componentes.html`) e o novo `tests/test_aceite_124.py`.

## Invariantes de produção
- `/api/snapshot?data=<pregão anterior>` traz `paineis.ibovespa.valor` igual ao fechamento oficial daquele dia (no máximo 0,1% de diferença para uma fonte independente) e diferente do valor do último pregão quando o índice variou entre os dois dias.

## Fora do escopo
- Painéis que não leem de `snapshots_paineis` (séries diárias, Consultor), que têm regra própria (specs 089 e 113a).
- Trocar o `ContextVar` de gravação por um parâmetro explícito (ideia no backlog).
