---
name: ciclo
description: Executa uma iteração autônoma da raia de desenvolvimento do devagent, seguindo o ciclo de decisão de devagent/CICLO.md.
---

# Ciclo do Desenvolvedor Autônomo

Ao invocar esta skill (ou digitar `/ciclo`), você é o **desenvolvedor** e executa uma iteração do ciclo de decisão de `devagent/CICLO.md` (seção 4). Esta skill é só a porta de entrada: quando ela e o `CICLO.md` divergirem, vale o `CICLO.md`.

1. **Estado Atual:**
   ```bash
   git fetch origin
   python -m devagent.estado_github
   python -m devagent.saude
   make install
   ```

   O `make install` vem antes de qualquer `make verify`: o ambiente da sessão não traz as ferramentas fixadas em `requirements-dev.txt`, e sem elas o `verify` falha com "No module named ruff".

2. **Ordem de prioridade.** Percorra os passos do `CICLO.md` em ordem e execute **somente o primeiro que gerar entrega**:
   - **Passo 1 (Verificar e corrigir):** issues `deploy-falhou`, `producao-incorreta`, `sistema-com-problema` ou `prioridade`, `make audit`, `make verify`, `python -m devagent.conferir_pr` e a seção *Correções* do `docs/BACKLOG.md`.
   - **Passo 2 (Destravar PR):** se houver PR aberto da raia de desenvolvimento, trabalhe só nele, na branch dele, e encerre.
   - **Passo 3 (Publicação):** não gera PR; registre e siga.
   - **Passo 4 (Spec):** a spec `ready` que o `estado_github` indicar, só se já tiver o campo `revisada:`.
   - **Passo 5 (Documentação e o próprio agente):** pendência de retrospectiva, documento que diverge da `main` ou problema repetido sem skill.
   - **Passo 6 (Issues):** a issue mais antiga fora das excluídas pelo `CICLO.md`.
   - **Passo 7** é da raia de especificação: chegando nele, encerre sem PR.

3. **Personas não entram nesta skill.** Sentinel, Palette, Bolt, Auditor, Especificador, Revisor e Verificador só são assumidos quando a tarefa que acionou a sessão os nomeia; aí vale o arquivo da persona em `devagent/agents/` e esta skill não se aplica. Horário do dia ou fila de specs não transformam a sessão do desenvolvedor em especialista ou em outra raia: cada uma é acionada em sessão própria (`devagent/agents/especialistas.md`, regra 7, e ADR 024).

4. **Regras Obrigatórias:**
   - Execute `make verify` antes de abrir qualquer PR.
   - Inclua no corpo do PR o marcador `<!-- devagent:raia:desenvolvimento -->`.
   - Registre o relatório da execução em `docs/runs/AAAA-MM-DD-HHMM.md`, no PR da entrega (nunca um PR só com o relatório).
   - Tome decisões conservadoras diante de ambiguidades e conclua a entrega sem parar para pedir confirmações.
