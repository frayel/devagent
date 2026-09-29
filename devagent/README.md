# devagent · o núcleo

Um desenvolvedor autônomo que especifica, implementa, revisa, publica e audita um produto em ciclos curtos, e que aprende entre execuções. Esta pasta é a parte que não depende do produto: copie-a para outro repositório e ela funciona lá.

## As duas camadas

| | Núcleo | Projeto |
|---|---|---|
| Instruções | `devagent/CICLO.md`, `devagent/agents/` | `PRODUTO.md` |
| Procedimentos | `devagent/skills/` | `docs/skills/` |
| Decisões | `devagent/decisoes/` | `docs/decisions/` |
| Conhecimento | `devagent/OPERACAO.md` | `docs/context/` |
| Código | guardião, estado do GitHub, adaptadores, harness da auditoria | aplicação, testes, checagens de produção (`auditoria/`) |
| Configuração | lê `devagent.toml` | escreve `devagent.toml` e `Makefile` |

O `AGENTS.md` da raiz é só uma porta: manda ler o `CICLO.md` e o `PRODUTO.md`.

## Os três contratos

1. **`Makefile`** com `install`, `install-prod`, `verify`, `smoke` e `audit`. O CI, o guardião e o agente só conhecem esses nomes; o stack mora dentro deles.
2. **`devagent.toml`** com o nome do produto, o repositório, a URL de produção, o fuso e os termos do domínio.
3. **`/api/snapshot`**: o site expõe em JSON o que a tela mostra, e a auditoria compara isso com o mundo.

## A fronteira

`devagent/tests/test_fronteira.py` reprova o CI se qualquer arquivo desta pasta citar o nome do produto ou um termo de `termos_do_dominio`. É o que mantém o núcleo reaproveitável enquanto o agente o aprimora no mesmo repositório: uma lição de processo entra aqui escrita de forma geral; o exemplo concreto fica no projeto.

## Separação de poderes

`devagent/protegidos.txt` lista o que só muda com revisão humana: o guardião, o adaptador do Jules, a auditoria (núcleo e checagens do projeto), os workflows que vigiam o agente e a própria lista. O `automerge.yml` lê a lista da `main`, então um PR não consegue se desproteger. Todo o resto, inclusive o `CICLO.md`, o agente pode melhorar sozinho por PR `agent:`.

## Autoaperfeiçoamento

O núcleo vive no mesmo repositório que o produto de propósito. O agente edita `devagent/` como edita qualquer arquivo, com as mesmas regras (seção 9 do `CICLO.md` e skill `auto-melhoria`). Para levar as melhorias a outro projeto, copie a pasta de novo: o que é do projeto (`PRODUTO.md`, `devagent.toml`, `Makefile`, `auditoria/`) não é tocado.

## Adotar em um projeto novo

```bash
python -m devagent.instalar /caminho/do/projeto-novo
```

O instalador copia `devagent/` e os workflows e cria `AGENTS.md`, `PRODUTO.md`, `devagent.toml`, `Makefile` e o esqueleto de `docs/` a partir de `devagent/modelos/`, sem sobrescrever nada. Depois:

1. Preencha `PRODUTO.md` e `devagent.toml` (inclusive `termos_do_dominio`).
2. Ajuste os alvos do `Makefile` ao stack.
3. Escreva `auditoria/auditar.py` com as checagens do produto, usando `devagent.auditoria.nucleo` (`checar_saude`, `checar_pagina`, `checar_navegador`, `numeros_dos_fixtures`, `executar`).
4. Revise os horários de `auditoria-producao.yml` e `auditoria-llm.yml`.
5. Crie os secrets de `devagent/OPERACAO.md` e escreva a spec `001` do MVP.

## Atualizar um projeto que já usa o núcleo

Copie `devagent/` e os workflows por cima (o instalador só cria o que falta). Rode `make verify`: o teste de fronteira usa os termos do projeto de destino e aponta qualquer vazamento.
