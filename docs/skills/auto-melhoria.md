# Skill · Melhorar instruções, skills e contextos

Use no Passo 5, ou sempre que a Retrospectiva de uma execução apontar uma melhoria.

## 1. Partir de evidência

Toda mudança começa por um problema observado: um relatório em `docs/runs/`, uma issue, um PR que precisou de correção, um CI que falhou. Cite o link no PR. Mudança sem evidência é opinião, e opinião envelhece mal em instruções.

## 2. Escolher o lugar certo

| O que você aprendeu | Onde registrar |
|---|---|
| Uma regra de comportamento do agente (ordem, limites, formato) | `AGENTS.md` |
| Um procedimento com passos que vai se repetir | nova skill em `docs/skills/` |
| Um fato sobre o sistema, o mercado, uma fonte ou a operação | `docs/context/` |
| Como humanos rodam, configuram ou entendem o projeto | `README.md` |
| O que existe hoje em produção | `docs/STATE.md` |

Não duplique: se o fato já está em um lugar, os outros apontam para ele.

## 3. Escrever bem

- Instruções imperativas e verificáveis ("rode X e confira Y"), não desejos ("tente garantir qualidade").
- Uma skill cabe numa tela: quando usar, passos, armadilhas conhecidas.
- Ao alterar uma regra, apague a versão antiga. Duas regras conflitantes são piores que nenhuma.
- Mantenha o `AGENTS.md` enxuto: se uma seção passar de ~40 linhas, extraia o detalhe para uma skill ou um contexto e deixe o ponteiro.

## 4. Respeitar os limites

Leia a subseção *Limites do autoaperfeiçoamento* da seção 13 do `AGENTS.md`. Os itens protegidos só podem ser mantidos ou reforçados.

## 5. Entregar

- PR próprio com prefixo `agent:` (para `AGENTS.md` e skills) ou `docs:` (demais documentos).
- Corpo do PR: problema observado, evidência, mudança, efeito esperado na próxima execução.
- Atualize o índice da seção 13 se criou ou removeu arquivos.
- Mudança no ciclo de decisão ou no stack: acrescente um ADR em `docs/decisions/`.
