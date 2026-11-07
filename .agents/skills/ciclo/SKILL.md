---
name: ciclo
description: Executa uma iteração autônoma do ciclo do devagent (verificar saúde, destravar PR, atuar como especialista ou implementar spec).
---

# Ciclo do Desenvolvedor Autônomo

Ao invocar esta skill (ou digitar `/ciclo`), execute uma iteração completa do ciclo de decisão seguindo `AGENTS.md` e `devagent/CICLO.md`:

1. **Estado Atual:**
   ```bash
   git fetch origin
   python -m devagent.estado_github
   python -m devagent.saude
   ```

2. **Ordem de Prioridade (execute apenas o primeiro que gerar entrega):**
   - **Passo 1 (Saúde & Produção):** Se houver issue `deploy-falhou`, `producao-incorreta` ou `sistema-com-problema`, investigue a causa raiz, corrija com teste de regressão e abra PR `fix:`.
   - **Passo 2 (Destravar PR):** Se houver PR do agente aberto ou travado no CI, faça checkout na branch desse PR, corrija a causa e dê push na mesma branch.
   - **Especialistas / Raias:** Se for horário de especialista (Sentinel na madrugada, Bolt pela manhã) ou se houver trabalho de raia auxiliar pendente (Verificador com merges recentes sem auditar; Especificador com fila <= 2 specs), assuma essa persona conforme `devagent/agents/`.
   - **Passo 4 / 6 (Desenvolvimento):** Implemente a próxima spec pronta revisada ou a issue prioritária mais antiga.

3. **Regras Obrigatórias:**
   - Execute `make verify` antes de abrir qualquer PR.
   - Inclua no corpo do PR o marcador da raia: `<!-- devagent:raia:<desenvolvimento|especificacao|revisao|verificacao> -->`.
   - Registre o relatório da execução em `docs/runs/AAAA-MM-DD-HHMM.md`.
   - Tome decisões conservadoras diante de ambiguidades e conclua a entrega sem parar para pedir confirmações.
