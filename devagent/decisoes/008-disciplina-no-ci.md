# ADR 008 · A disciplina do ciclo é conferida no CI

- **Status:** aceita
- **Data:** 2026-10-06

## Contexto

Numa execução, o agente implementou uma spec `ready` enquanto a seção *Correções* do backlog tinha duas entradas pendentes, o que o Passo 1, item 6, e o ADR 002 proíbem. No mesmo PR, deixou a spec em `in-progress`, não atualizou o `CHANGELOG.md` nem o arquivo de estado (o contador da cadência de experiência deixou de contar) e versionou um script de exploração com nome de teste na raiz. O CI passou e o merge foi automático: todas essas regras viviam só no texto do `CICLO.md`, e o agente não tem memória entre execuções para lembrar de todas.

## Decisão

1. O núcleo ganha `devagent/conferir_pr.py`, só com biblioteca padrão, que compara o PR com a base e reprova quando:
   - alguma spec está `in-progress`;
   - há `test_*.py` ou `*_test.py` fora de uma pasta `tests/`;
   - uma spec vira `done` sem linha no CHANGELOG citando o número dela, ou sem mudança no arquivo de estado;
   - uma spec sai de `ready`/`draft` direto para `done` enquanto a seção *Correções* tem entrada pendente (sem `bloqueado`) e o PR não remove nenhuma delas.
2. Fechar uma spec que já estava `in-progress` na base é continuidade e fica fora da última regra.
3. O `ci.yml` roda a conferência no job `disciplina`. O auto-merge já espera o workflow inteiro, e o guardião repassa a falha ao agente como qualquer CI quebrado.
4. Os caminhos (`docs/specs`, `docs/BACKLOG.md`, `CHANGELOG.md`, `docs/STATE.md`) podem ser trocados na seção `[disciplina]` do `devagent.toml`.
5. A conferência entra nos itens que o autoaperfeiçoamento não pode enfraquecer.

## Consequências

Regras de processo que dependiam da memória do agente passam a ser mecânicas. Ficam de fora o que a máquina não sabe julgar: se a spec foi entregue por inteiro, se a escolha da ideia foi boa. A regra de prioridade olha só o backlog; issues `prioridade` continuam dependendo do texto do ciclo.
