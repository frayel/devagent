# AGENTS.md

Este repositório é construído por um desenvolvedor autônomo operando no Antigravity Remote. As instruções estão em duas camadas, e você lê as duas antes de agir:

1. **`devagent/CICLO.md`**: como você trabalha. O ciclo de decisão, a regra de continuidade, os limites, o relatório e o autoaperfeiçoamento. É o núcleo reaproveitável, igual em qualquer projeto.
2. **`PRODUTO.md`**: o que você constrói. O produto, o stack, as regras do domínio e o índice da documentação do projeto.

A configuração que liga as duas está em `devagent.toml` e o contrato de verificação no `Makefile` (`make verify`, `make smoke`, `make audit`).

**Personas e Subagentes.** Se a tarefa pede para atuar como **Auditor**, siga `devagent/agents/auditor.md`. Se pede **Especificador**, **Revisor** ou **Verificador**, siga `devagent/agents/raias.md`. Se pede **Sentinel**, **Palette** ou **Bolt**, siga `devagent/agents/especialistas.md`. Em todos esses casos, ignore o ciclo de decisão. Você também pode invocar subagentes especializados para tarefas em paralelo ou pesquisas de contexto.

**Ambiente e Execução.** No Antigravity Remote, você dispõe de terminal Linux dedicado (`bash`), ferramentas como `uv`, `git` e a CLI `gh` já autenticada para gerenciar PRs e checagens. O modelo de operação é híbrido: automações agendadas a cada 2h mantêm o batimento do projeto, enquanto execuções sob demanda (`/goal`) aceleram lotes de trabalho.

**Primeiro comando de toda execução:**

```bash
git fetch origin
python -m devagent.estado_github
```
