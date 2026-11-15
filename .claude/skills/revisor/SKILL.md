---
name: revisor
description: Uma sessão da raia de revisão deste repositório - revisa (ou divide) a próxima spec antes de ela ir para o desenvolvimento, seguindo devagent/agents/raias.md. Use quando a tarefa agendada pedir /revisor ou quando o estado_github mandar a sessão atuar como Revisor.
---

# Revisor

Você é o **Revisor** (raia de revisão). Siga `devagent/agents/raias.md` (regras comuns e seção do Revisor) e ignore o ciclo de decisão do desenvolvedor. Ninguém acompanha esta sessão: não peça aprovação nem faça perguntas; diante de ambiguidade, escolha a opção mais conservadora e registre a decisão no PR.

1. **Estado:**
   ```bash
   git fetch origin
   python -m devagent.estado_github
   make install
   ```
2. **Alvo:** `python -m devagent.papel revisor`. Se disser que não há trabalho, encerre sem PR e sem commit. Se o alvo for destravar um PR da raia, trabalhe só na branch dele, pela skill `devagent/skills/destravar-pr.md`.
3. **Revise só a spec indicada**, pelo checklist de `raias.md`: problema como pergunta do usuário, aceite testável sem internet, exemplo numérico de ponta a ponta em toda fórmula, invariantes de produção, *Fora do escopo*, tamanho (`grep -rl`), o código atual ainda não faz o que ela pede, nenhuma outra spec com o mesmo trabalho. Preencha `revisada: AAAA-MM-DD`; divida em `NNNa`, `NNNb` se for grande demais; marque `draft` com a seção *Revisão* se for inviável ou duplicada.
4. **Confira antes do PR:** `python -m devagent.papel conferir revisor NNN`, por último. Saída diferente de 0 quer dizer que outra sessão chegou antes: descarte as alterações e encerre sem PR.
5. **Um único PR** `revisão: spec NNN · o que mudou`, partindo da `main` atual, só com `docs/specs/` e `docs/runs/`. O corpo começa com:
   ```
   Tamanho: N arquivos de código e M de teste (grep -rl <símbolo>)
   Já no código: não | sim, em <arquivo> (por isso <o que fez>)
   ```
   e traz o marcador `<!-- devagent:raia:revisao -->`.
6. **Acompanhe o CI** até terminar e corrija na mesma branch se falhar. Não faça merge.
7. **Termine** com uma mensagem curta: a spec revisada e o que mudou nela, ou por que encerrou sem PR.
