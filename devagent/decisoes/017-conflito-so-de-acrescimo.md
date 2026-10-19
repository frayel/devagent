# ADR 017 · Conflito só de acréscimo não fecha PR

- **Data:** 2026-10-19 · **Status:** aceita
- **Complementa:** ADR 014 (PR absorvido pela main)

## Contexto

O guardião mede o conflito de um PR com a `main` contando as linhas entre os marcadores e fecha o PR acima de 3 arquivos ou 40 linhas. Em 19/10 ele fechou o #362 (spec 068b) por "conflito grande, 2 arquivos, 93 linhas". O #362 e o #358 (página de sistema) tinham acrescentado, cada um, um bloco de estilos no fim do `tema.css` e uma entrada em `docs/STATE.md`, no mesmo ponto. Nenhum dos dois alterou o que já existia; das 93 linhas, só 2 (o contador de experiência) eram conflito de fato. O trabalho de uma spec de esforço G seria refeito do zero por causa de dois blocos empilhados.

Arquivos onde todo PR escreve no fim (`tema.css`, `STATE.md`, `CHANGELOG.md`) produzem esse padrão sempre que dois PRs correm em paralelo.

## Decisão

- O merge de teste usa `merge.conflictStyle=diff3`. Um trecho cuja base está vazia é acréscimo dos dois lados e não entra na medida de tamanho (`contar_conflito` em `devagent/guardiao_prs.py`).
- O limite de 3 arquivos e 40 linhas vale só para as linhas reais. Arquivo em conflito sem marcadores (removido de um lado, binário) continua contando como grande.
- O comentário de conflito pequeno avisa quantas linhas são só acréscimo e pede para manter os dois blocos.
- A skill `destravar-pr.md` mede do mesmo jeito.

## Consequências

- PRs que só colidem por acréscimo deixam de ser descartados: o Jules recebe o pedido de resolução, como em qualquer conflito pequeno.
- Um bloco grande acrescentado por um lado junto com uma alteração real do outro no mesmo trecho tem base não vazia e continua contando inteiro.
