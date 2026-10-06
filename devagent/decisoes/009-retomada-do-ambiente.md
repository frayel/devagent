# ADR 009 · Retomada depois de ambiente reiniciado

- **Status:** aceita
- **Data:** 2026-10-06

## Contexto

Uma sessão do agente abriu um PR com a spec ainda em `in-progress`; o job `disciplina` (ADR 008) reprovou o PR no primeiro push. O guardião cobrou duas vezes. Entre uma cobrança e outra, o ambiente da sessão foi reiniciado e perdeu as alterações locais. O agente voltou para a `main` limpa, anunciou que recriaria a spec do zero e parou perguntando se devia continuar na branch. Três falhas se somaram:

1. O ciclo mandava mudar a spec para `in-progress` antes de implementar, e o agente fazia commit desse estado. Como o PR é aberto no primeiro push, ele já nascia reprovado.
2. As cobranças do guardião diziam "corrija nesta mesma branch", mas não diziam como reencontrá-la depois de um reinício.
3. O vigia responde perguntas com "sim, siga". Para uma sessão que perdeu o ambiente, isso confirmava o plano errado: refazer da `main`. E uma sessão cujo PR já tinha sido fechado também recebia "siga", o que levaria a um PR duplicado.

## Decisão

1. `in-progress` deixa de ser commitado. A spec vai de `ready` direto para `done` no PR; o primeiro commit só sai com spec, testes, CHANGELOG e estado prontos. O job `disciplina` continua reprovando `in-progress`.
2. Toda cobrança do guardião (CI falhou, conflito) traz a instrução de retomada: `git fetch origin && git checkout -B <branch> origin/<branch>`, sem recomeçar da `main` e sem perguntar.
3. O vigia lê o PR de cada sessão parada numa pergunta. PR aberto: a resposta aponta a branch e manda continuar nela. PR fechado ou mesclado: a sessão recebe ordem de encerrar, sem novos commits nem PRs.
4. O adaptador ganha `encerrar <sessão>`, disponível no `jules.yml` como ação manual, para o dono do produto parar uma sessão sem abrir a interface.
5. A skill `destravar-pr` ganha a seção *Ambiente reiniciado*.

## Consequências

Um reinício do ambiente passa a custar uma volta, não o trabalho inteiro. O vigia faz uma chamada à API do GitHub por sessão parada, o que cabe com folga no limite do token do Actions. Se a leitura do PR falhar, o vigia volta à resposta antiga, que é pior mas não trava o ciclo.
