# ADR 018 · Falha que ensina: fechar cedo, dividir depois, provar a entrega

- **Data:** 2026-10-22 · **Status:** aceita
- **Complementa:** ADRs 009, 012, 014 e 015

## Contexto

Em 21/10 a sessão que implementava a spec 075 (13 painéis) perdeu o trabalho e abriu o PR #402 só com o relatório da execução. O relatório descrevia mudanças em dezenas de arquivos e um `make verify` verde; nada disso estava na branch. O job `disciplina` reprovou (regra 6), o guardião cobrou o agente, e a cobrança abriu uma sessão filha que criou o #403 sem nenhum arquivo, dizendo ter feito um rebase. Com dois PRs abertos, toda rodada caía no Passo 2 tentando destravar um trabalho que não existia. O guardião só fecharia três horas depois de cada cobrança, e a spec voltaria para `ready` do mesmo tamanho, pronta para falhar de novo.

Ao investigar, apareceu um segundo defeito: a spec 074 foi marcada `done` sem cumprir um dos critérios de aceite (as tabelas antigas continuavam sendo criadas). A disciplina conferia CHANGELOG e STATE, não o critério.

A causa de fundo do tamanho: a 075 pedia para apagar funções e dataclasses usadas por cerca de 100 arquivos, quase todos testes. A regra do CICLO media o PR em linhas excluindo testes, então a spec parecia caber.

## Decisão

1. **Falha irrecuperável fecha na hora.** PR sem arquivo alterado, ou só com registros de execução (e sem `Closes #N`), não tem o que corrigir na branch. O guardião fecha esse PR no primeiro CI vermelho ou na varredura, sem cobrar o agente, e abre `tentativa-falhou` mesmo que a `main` já tenha tudo (`guardiao_prs.motivo_irrecuperavel`).
2. **Tentativa falha vira divisão.** Se a próxima spec da fila tem issue `tentativa-falhou` aberta que a cite, o prompt da sessão e o `estado_github` mandam dividir, não implementar (`fila_specs.tentativas_da_spec`). O PR da divisão fecha a issue.
3. **Tamanho medido com os testes.** O Passo 4 manda contar os arquivos que referenciam o que a spec remove ou renomeia, e preferir preservar a interface pública antes de dividir.
4. **Aceite executável.** O campo `aceite:` da spec lista o teste que prova a entrega; a regra 7 do `conferir_pr` exige que ele exista quando a spec vira `done`, e o CI o roda. `devagent.aceite.exigir_spec_done` deixa o teste nascer junto com a spec e só valer quando ela fecha. A partir de `aceite_obrigatorio_desde` (seção `[disciplina]` do `devagent.toml`) o campo é obrigatório.

## Consequências

- Um PR sem trabalho deixa de travar o ciclo por horas: some no primeiro CI e vira aprendizado registrado.
- A mesma spec não é tentada duas vezes do mesmo tamanho; a segunda sessão divide.
- Fechar spec sem entregar passa a reprovar o CI, desde que a spec traga teste de aceite.
- O casamento entre issue e spec depende de o número da spec aparecer no título ou no corpo da issue. Títulos de PR sem o número escapam do desvio; o relatório da tentativa deve citar a spec.
