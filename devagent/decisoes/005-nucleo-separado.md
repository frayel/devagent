# ADR 005 · Núcleo separado do projeto, no mesmo repositório

**Data:** 2026-09-28 · **Status:** aceito

## Contexto

O `AGENTS.md` misturava o ciclo de decisão do agente com o produto. Os scripts e workflows fixavam o repositório, a URL de produção e os comandos do stack (`ruff`, `mypy`, `pytest`). O auditor de produção juntava num só arquivo o harness e as checagens de um único painel. Reaproveitar o agente em outro projeto exigiria garimpar o que era processo e o que era produto.

O dono do projeto quer reaproveitar o agente, mas também quer que ele continue se aperfeiçoando. Um repositório separado para o núcleo cortaria esse caminho: o agente só edita o repositório em que trabalha.

## Decisão

1. O núcleo mora em `devagent/`, no mesmo repositório: `CICLO.md`, personas, skills de processo, ADRs do ciclo, guardião, estado do GitHub, adaptadores (Jules e Render), harness da auditoria, modelos e instalador.
2. O projeto mora na raiz: `PRODUTO.md`, `Makefile`, aplicação, testes, `auditoria/` (checagens do produto) e `docs/`.
3. O `AGENTS.md` vira uma porta que manda ler `devagent/CICLO.md` e `PRODUTO.md`.
4. Os dois lados se falam por contratos: alvos do `Makefile`, `devagent.toml` e `/api/snapshot`.
5. `devagent/tests/test_fronteira.py` reprova o CI se o núcleo citar o produto.
6. A lista de caminhos protegidos sai da regex do `automerge.yml` e vai para `devagent/protegidos.txt`, lida da `main` e protegida por si mesma. O conjunto protegido continua o mesmo, com os caminhos novos.

## Consequências

- O agente continua podendo melhorar o núcleo, por PR `agent:`, com o CI garantindo que a melhoria permaneça genérica.
- `python -m devagent.instalar` leva o núcleo a outro projeto; melhorias posteriores chegam copiando a pasta de novo.
- Os comandos mudaram de caminho (`python -m devagent.estado_github` no lugar de `python scripts/estado_github.py`). Relatórios antigos em `docs/runs/` citam os caminhos antigos e não foram reescritos.
- Os horários de `auditoria-producao.yml` e `auditoria-llm.yml` continuam amarrados ao produto: o GitHub não permite agendamento configurável por arquivo.
