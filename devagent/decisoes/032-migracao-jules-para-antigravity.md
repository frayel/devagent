# ADR 032 · Migração do Jules para o Antigravity Remote e modelo híbrido

- **Data:** 2026-11-06 · **Status:** aceita
- **Revê:** ADRs 009, 010, 012, 021, 024, 025, 028; CICLO.md; OPERACAO.md

## Contexto

O devagent operava sobre a API do Google Labs Jules (`jules.googleapis.com`), acionado por um cron externo (`cron-job.org`) chamando `workflow_dispatch` a cada 5 min. Esse arranjo impunha limitações técnicas e operacionais:

1. **Validação de raia acoplada:** O job de disciplina do CI consultava a API do Jules por rede para checar se o título da sessão batia com o prefixo do PR (ADR 024). Sem a API ou com falhas de rede, a validação falhava ou dependia de `JULES_API_KEY`.
2. **Ambiente efêmero instável:** Sessões do Jules frequentemente sofriam reinício de container no meio do trabalho, perdendo alterações locais (ADR 009).
3. **Loop de reconciliação de 5 min:** O cron rodava centenas de vezes por dia apenas para verificar se havia sessões em andamento ou planos travados (`destravar`), gastando minutos e chamadas desnecessárias.
4. **Cotas rígidas de tarefas diárias:** O ritmo precisava ser artificialmente espaçado por `JULES_LIMITE_DIARIO` (ADR 028).

Com o Antigravity Remote, o agente executa em uma máquina virtual Linux Debian 12 dedicada, com persistência do workspace durante a sessão, ferramentas nativas (`uv`, `gh`, `git`), suporte a subagentes e sem bloqueios de aprovação de plano.

## Decisão

1. **Modelo Híbrido de Execução:**
   - **Automação agendada a cada 2h:** Executada no Antigravity Remote para manter o batimento contínuo do projeto, saúde de produção, verificação de PRs e especialistas (Sentinel de madrugada, Bolt pela manhã).
   - **Modo Contínuo Sob Demanda (`/goal`):** Para sprints intensivos, o desenvolvedor usa o slash command `/goal`, encadeando múltiplas specs e passos consecutivamente.
   - **Remoção do cron externo de 5 minutos:** Desativação do schedule do `jules.yml` e remoção da dependência do `cron-job.org`.
2. **Validação Autônoma de Raias via Marcador:**
   - O corpo do PR passa a declarar a raia através do marcador HTML: `<!-- devagent:raia:<nome> -->` (`desenvolvimento`, `especificacao`, `revisao`, `verificacao`).
   - O `conferir_pr.py` valida esse marcador localmente sem fazer requisições à API externa, mantendo fallback retrocompatível para sessões legadas do Jules.
3. **Diários em `.agents/`:**
   - A pasta `.jules/` é migrada para `.agents/` para os diários das personas (Sentinel, Palette, Bolt), mantendo retrocompatibilidade total na leitura e conferência de PRs.
4. **Identidade do Agente:**
   - O núcleo reconhece logins do Antigravity (`antigravity`, `antigravity-bot`) e permite customização de bot via `devagent.toml`.
   - As cobranças do guardião de PRs usam a menção `@antigravity`.

## Consequências

- Elimina a dependência de serviços externos de cron (`cron-job.org`) e de chaves secretas para a API do Jules no CI.
- A disciplina do CI roda mais rápido e deterministicamente (sem chamadas HTTP externas).
- Menor overhead de execuções vazias; o agente trabalha com foco em entregas completas e verificadas por rodada.
