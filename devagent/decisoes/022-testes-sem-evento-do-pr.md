# ADR 022 · Os testes do núcleo não enxergam o evento real do PR

- **Data:** 2026-10-24 · **Status:** aceita
- **Corrige:** efeito colateral do ADR 021

## Contexto

A regra 8 do `conferir_pr` lê o título do PR em `GITHUB_EVENT_PATH`. Esse arquivo existe em todo job do GitHub Actions, inclusive no job `test`. Oito testes (`test_aceite.py` e `test_conferir_pr.py`) chamam `conferir()` sem passar o título, então herdavam o título real do PR. Num PR de raia (`spec:`, `revisão:`, `verificação:`), os arquivos de fixture caíam fora da faixa e os testes reprovavam, sem que o PR tivesse feito algo errado.

O efeito foi um laço. O CI do PR de raia ficava vermelho; a sessão do Jules tentava consertar mexendo em testes e em `conferir_pr.py`, fora da faixa dela, e o job `disciplina` também reprovava; o guardião cobrava três vezes e fechava; a rodada abria outra sessão para a mesma spec. Em 24/10, a revisão da spec 085 gerou quatro PRs (#449, #452, #454, #456) e a verificação, três (#443, #447, #455). PRs de desenvolvimento não têm prefixo e passavam, o que escondeu o defeito.

## Decisão

1. `devagent/tests/conftest.py` remove `GITHUB_EVENT_PATH` e `GITHUB_EVENT_NAME` do ambiente de todos os testes. O teste que precisa de um evento o monta com `monkeypatch`.
2. Um teste (`test_isolamento_ci.py`) protege o isolamento.
3. A regra 8 não muda. Ela continua valendo no CI, onde o título do PR existe.

## Consequências

- PRs de raia deixam de falhar por um defeito que não é deles.
- Quem alterar o `conferir_pr` não depende mais do título do PR que está rodando o CI.
