"""Isolamento dos testes do núcleo em relação ao ambiente do CI.

No GitHub Actions, GITHUB_EVENT_PATH aponta para o evento real do PR em
andamento. `conferir_pr` lê o título dali e aplica a regra 8 (raias, ADR 021);
sem este isolamento, um PR de raia (`spec:`, `revisão:`, `verificação:`) faz os
testes avaliarem os arquivos de fixture como se fossem do PR e reprovarem
(ADR 022). Cada teste que precisa de um evento o monta por conta própria.
"""

import pytest


@pytest.fixture(autouse=True)
def sem_evento_do_github(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GITHUB_EVENT_PATH", raising=False)
    monkeypatch.delenv("GITHUB_EVENT_NAME", raising=False)
