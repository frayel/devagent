# ADR 014 · PR absorvido pela main não vira `tentativa-falhou`

- **Data:** 2026-10-19 · **Status:** aceita
- **Complementa:** ADR 001

## Contexto

Em 19/10, o Jules abriu o PR #344 para destravar o #343 (ADR 012). O #343 já tinha sido mesclado às 02h35, antes de a sessão terminar, então o #344 carregava o mesmo trabalho mais um relatório de execução. Às 02h55 o #345 (ADR 013) entrou mexendo nos mesmos três arquivos, e o guardião fechou o #344 por conflito grande e abriu a issue #347 pedindo para refazer o trabalho.

Não havia trabalho a refazer: tudo já estava na `main`, exceto o relatório, e um PR só de relatório é justamente o que o ADR 012 proíbe. A issue ficou aberta sem que nenhuma rodada pudesse resolvê-la, até ser fechada à mão.

## Decisão

Antes de abrir a issue, `fechar` compara o PR com a `main` (`pendentes_fora_da_main`): para cada arquivo, verifica se o diff do PR, do ponto de divergência até a ponta, esteve aplicado em algum commit da `main` depois da divergência. Olhar só a ponta da `main` não basta, porque uma mudança posterior no mesmo trecho (o #345) esconde que o conteúdo já entrou.

Se os únicos arquivos pendentes são registros de execução (`PADRAO_REGISTROS` do `conferir_pr`: `docs/runs/`, `.jules/`), o PR é fechado como absorvido, com um comentário explicando, e nenhuma issue é aberta. Se a comparação falhar (histórico raso, erro de git), vale o comportamento antigo.

## Consequências

- Issues `tentativa-falhou` passam a apontar só trabalho que de fato falta na `main`.
- Os dois jobs do `pr-guardiao.yml` fazem checkout com histórico completo, que a comparação precisa.
- Um PR cuja mudança entrou e depois foi revertida na `main` conta como absorvido. A reversão foi uma decisão posterior, e refazer o PR a desfaria.
