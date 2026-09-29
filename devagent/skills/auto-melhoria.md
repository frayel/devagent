# Skill · Melhorar instruções, skills e contextos

Use no Passo 5, ou sempre que a Retrospectiva de uma execução apontar uma melhoria.

## 1. Partir de evidência

Toda mudança começa por um problema observado: um relatório em `docs/runs/`, uma issue, um PR que precisou de correção, um CI que falhou. Cite o link no PR. Mudança sem evidência é opinião, e opinião envelhece mal em instruções.

## 2. Escolher o lugar certo

Primeiro pergunte: **isto vale para qualquer projeto ou só para este produto?** O núcleo (`devagent/`) é reaproveitado em outros repositórios; o que você ensina a ele, todos os projetos aprendem.

| O que você aprendeu | Onde registrar |
|---|---|
| Uma regra de processo do agente (ordem, limites, formato, relatório) | `devagent/CICLO.md` |
| Um procedimento de processo que vai se repetir em qualquer projeto | nova skill em `devagent/skills/` |
| Uma decisão sobre o ciclo ou o núcleo | ADR em `devagent/decisoes/` |
| O que o produto é, promete ou como ele é construído | `PRODUTO.md` |
| Um procedimento que só faz sentido neste produto | nova skill em `docs/skills/` |
| Um fato sobre o sistema, o domínio, uma fonte ou a operação deste projeto | `docs/context/` |
| Uma decisão sobre o produto ou o stack | ADR em `docs/decisions/` |
| Como humanos rodam, configuram ou entendem o projeto | `README.md` |
| O que existe hoje em produção | `docs/STATE.md` |

Não duplique: se o fato já está em um lugar, os outros apontam para ele.

**Fronteira.** Nada dentro de `devagent/` pode citar o produto. O teste `devagent/tests/test_fronteira.py` reprova o CI se aparecer um termo de `termos_do_dominio` (em `devagent.toml`). Se a lição nasceu de um caso concreto, escreva a regra de forma geral no núcleo e deixe o exemplo no projeto. Quando surgir um termo novo do domínio, acrescente-o à lista.

## 3. Escrever bem

- Instruções imperativas e verificáveis ("rode X e confira Y"), não desejos ("tente garantir qualidade").
- Uma skill cabe numa tela: quando usar, passos, armadilhas conhecidas.
- Ao alterar uma regra, apague a versão antiga. Duas regras conflitantes são piores que nenhuma.
- Mantenha o `CICLO.md` e o `PRODUTO.md` enxutos: se uma seção passar de ~40 linhas, extraia o detalhe para uma skill ou um contexto e deixe o ponteiro.

## 4. Respeitar os limites

Leia a subseção *Limites do autoaperfeiçoamento* da seção 9 do `devagent/CICLO.md` e os itens protegidos do `PRODUTO.md`. Os itens protegidos só podem ser mantidos ou reforçados.

## 5. Entregar

- PR próprio com prefixo `agent:` (para `devagent/`, `AGENTS.md`, `PRODUTO.md` e skills) ou `docs:` (demais documentos).
- Corpo do PR: problema observado, evidência, mudança, efeito esperado na próxima execução.
- Atualize o índice certo (seção 9 do `CICLO.md` ou o do `PRODUTO.md`) se criou ou removeu arquivos.
- Mudança no ciclo de decisão: ADR em `devagent/decisoes/`. Mudança no stack: ADR em `docs/decisions/`.
