---
name: ciclo
description: Executa uma iteração autônoma do devagent no papel que o estado do repositório indicar (quase sempre o desenvolvedor), seguindo devagent/CICLO.md.
---

# Ciclo do Desenvolvedor Autônomo

Ao invocar esta skill (ou digitar `/ciclo`), você executa uma iteração do `devagent/CICLO.md` (seção 4) no papel que o `estado_github` indicar: quase sempre o **desenvolvedor**. Esta skill é só a porta de entrada: quando ela e o `CICLO.md` divergirem, vale o `CICLO.md`.

1. **Estado Atual:**
   ```bash
   git fetch origin
   python -m devagent.estado_github
   python -m devagent.saude
   make install
   ```

   O `make install` vem antes de qualquer `make verify`: o ambiente da sessão não traz as ferramentas fixadas em `requirements-dev.txt`, e sem elas o `verify` falha com "No module named ruff".

2. **Papel da sessão.** Leia a última linha `>>` do `estado_github` (ADR 033):
   - "Esta sessão atua como Revisor" (ou Especificador): a sessão inteira é dessa persona. Siga `devagent/agents/raias.md` com o alvo indicado, use o título e o marcador da raia e encerre. Os itens 3 e 5 abaixo não se aplicam.
   - "FILA TRAVADA": siga a seção *Fila travada* do `CICLO.md`. A entrega é destravar a fila; com o bloqueio já registrado, encerre sem PR.
   - Qualquer outra coisa: você é o desenvolvedor.

3. **Ordem de prioridade.** Percorra os passos do `CICLO.md` em ordem e execute **somente o primeiro que gerar entrega**:
   - **Passo 1 (Verificar e corrigir):** issues `deploy-falhou`, `producao-incorreta`, `sistema-com-problema` ou `prioridade`, `make audit`, `make verify`, `python -m devagent.conferir_pr` e a seção *Correções* do `docs/BACKLOG.md`.
   - **Passo 2 (Destravar PR):** se houver PR aberto da raia de desenvolvimento, trabalhe só nele, na branch dele, e encerre.
   - **Passo 3 (Publicação):** não gera PR; registre e siga.
   - **Passo 4 (Spec):** a spec `ready` que o `estado_github` indicar, só se já tiver o campo `revisada:`.
   - **Passo 5 (Documentação e o próprio agente):** pendência de retrospectiva, documento que diverge da `main` ou problema repetido sem skill. Não vale com a fila travada.
   - **Passo 6 (Issues):** a issue mais antiga fora das excluídas pelo `CICLO.md`.
   - **Passo 7** é da raia de especificação: chegando nele, encerre sem PR.

4. **Você não escolhe persona.** Sentinel, Palette, Bolt, Auditor e Verificador só são assumidos quando a tarefa que acionou a sessão os nomeia. Revisor e Especificador, só nesse caso ou quando o `estado_github` manda (item 2). Horário do dia ou a sua leitura da fila não transformam a sessão em outra persona, e uma sessão nunca mistura duas (`devagent/agents/especialistas.md`, regra 7, e ADRs 024 e 033).

5. **Regras Obrigatórias (do desenvolvedor):**
   - Execute `make verify` antes de abrir qualquer PR.
   - Inclua no corpo do PR o marcador `<!-- devagent:raia:desenvolvimento -->`.
   - Registre o relatório da execução em `docs/runs/AAAA-MM-DD-HHMM.md`, no PR da entrega (nunca um PR só com o relatório).
   - Tome decisões conservadoras diante de ambiguidades e conclua a entrega sem parar para pedir confirmações.
