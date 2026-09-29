# AGENTS.md

Este repositório é construído por um desenvolvedor autônomo. As instruções estão em duas camadas, e você lê as duas antes de agir:

1. **`devagent/CICLO.md`**: como você trabalha. O ciclo de decisão, a regra de continuidade, os limites, o relatório e o autoaperfeiçoamento. É o núcleo reaproveitável, igual em qualquer projeto.
2. **`PRODUTO.md`**: o que você constrói. O produto, o stack, as regras do domínio e o índice da documentação do projeto.

A configuração que liga as duas está em `devagent.toml` e o contrato de verificação no `Makefile` (`make verify`, `make smoke`, `make audit`).

**Personas.** Se a tarefa pede para atuar como **Auditor**, siga `devagent/agents/auditor.md`. Se pede **Sentinel**, **Palette** ou **Bolt**, siga `devagent/agents/especialistas.md`. Nos dois casos, ignore o ciclo de decisão.

**Primeiro comando de toda execução:**

```bash
git fetch origin
python -m devagent.estado_github
```
