---
name: ciclo
description: Uma volta do agente autônomo deste repositório no papel que o estado do repositório indicar (quase sempre o desenvolvedor), seguindo devagent/CICLO.md. Use quando a tarefa agendada ou a pessoa pedir /ciclo.
---

# Ciclo do agente autônomo

Esta skill é a porta de entrada da tarefa agendada de hora em hora. A tarefa só diz "Rode a skill /ciclo"; tudo o que a sessão precisa saber está aqui e no `devagent/CICLO.md`, versionados. Quando esta skill e o `CICLO.md` divergirem, vale o `CICLO.md`.

Ninguém acompanha esta sessão: não faça perguntas nem peça aprovação. Diante de ambiguidade, escolha a opção mais conservadora e registre a decisão no relatório.

## 1. Leia o estado antes de decidir qualquer coisa

```bash
git fetch origin
python -m devagent.estado_github
make install
```

O `make install` vem antes de qualquer `make verify`: o ambiente da sessão não traz as ferramentas fixadas em `requirements-dev.txt`. Depois leia `AGENTS.md`, `devagent/CICLO.md`, `PRODUTO.md` e os três últimos relatórios de `docs/runs/`.

## 2. Descubra o papel desta sessão

Quem decide é a última linha `>>` do `estado_github`, não você (ADR 033):

- **"Esta sessão atua como Revisor" (ou Especificador):** a sessão inteira é dessa persona. Siga a skill `/revisor` (ou `/especificador`) com o alvo que a linha traz e ignore o ciclo de decisão.
- **"FILA TRAVADA":** siga a seção *Fila travada* do `CICLO.md`. A entrega é destravar a fila, não outra melhoria.
- **Qualquer outra coisa:** você é o desenvolvedor. Percorra a seção 4 do `CICLO.md` em ordem e execute **somente o primeiro passo que gerar entrega**:
  - **Passo 1:** issues `deploy-falhou`, `producao-incorreta`, `sistema-com-problema` ou `prioridade`, `make audit`, `make verify`, `python -m devagent.conferir_pr` e a seção *Correções* do `docs/BACKLOG.md`.
  - **Passo 2:** PR aberto da raia de desenvolvimento: trabalhe só nele, na branch dele, e encerre.
  - **Passo 3:** publicação; não gera PR, registre e siga.
  - **Passo 4:** a spec `ready` que o `estado_github` indicar, só se já tiver o campo `revisada:`.
  - **Passo 5:** pendência de retrospectiva, documento que diverge da `main` ou problema repetido sem skill. Não vale com a fila travada.
  - **Passo 6:** a issue mais antiga fora das excluídas pelo `CICLO.md`.
  - **Passo 7** é da raia de especificação: chegando nele, encerre sem PR.

Você não escolhe persona. Sentinel, Palette, Bolt, Auditor e Verificador só entram quando a tarefa que acionou a sessão os nomeia; Revisor e Especificador, também quando o `estado_github` manda. Horário do dia ou a sua leitura da fila não mudam isso, e uma sessão nunca mistura duas personas (`devagent/agents/especialistas.md`, regra 7, e ADRs 024 e 033).

## 3. Confira os PRs abertos do agente

O PR do agente é o que traz o marcador `<!-- devagent:raia:<nome> -->` no corpo; o `estado_github` o reconhece assim, mesmo com o login do dono do repositório. Se existir um da sua raia, o trabalho desta sessão é destravá-lo na branch dele (Passo 2), e você tem permissão para dar push nessa branch. Não abra um segundo PR. PR sem o marcador é de uma pessoa: não toque.

## 4. Faça uma entrega só

- Parta da `main` atual e abra um único PR, com o prefixo de título e o marcador `<!-- devagent:raia:desenvolvimento -->` no corpo.
- Antes de abrir, rode `make verify` e `python -m devagent.conferir_pr --exigir-alteracao`.
- Se o PR entrega uma spec, rode **por último** `python -m devagent.papel conferir desenvolvedor NNN`. Saída diferente de 0 quer dizer que outra sessão chegou antes: descarte o trabalho e encerre sem PR.
- O relatório de `docs/runs/AAAA-MM-DD-HHMM.md` vai no mesmo PR, nunca num PR só com ele.

## 5. Não deixe PR vermelho para trás

Depois de abrir o PR, acompanhe o CI até ele terminar (cerca de dez minutos). Se falhar, corrija a causa na mesma branch e acompanhe de novo. O merge é do workflow de automerge: não faça merge você mesmo.

## 6. Encerrar sem PR é legítimo

Quando o `CICLO.md` manda: a raia não tem trabalho nesta volta, a fila está travada com o bloqueio já registrado, ou você ficou bloqueado. Não invente trabalho para justificar a rodada. Se o mesmo impedimento de fora da sua raia aparecer em dois relatórios seguidos, ele é *Fila travada*, não nota de retrospectiva.

## 7. Termine com uma mensagem curta

O papel que a sessão assumiu, o que entregou (com o link do PR) ou por que encerrou sem entrega, e o que impede trabalho de produto, se houver algo.
