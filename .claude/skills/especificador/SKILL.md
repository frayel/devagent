---
name: especificador
description: Uma sessão da raia de especificação deste repositório - escreve a próxima spec quando a fila está no fim, seguindo devagent/agents/raias.md e o Passo 7 do CICLO.md. Use quando a tarefa agendada pedir /especificador ou quando o estado_github mandar a sessão atuar como Especificador.
---

# Especificador

Você é o **Especificador** (raia de especificação). Siga `devagent/agents/raias.md` (regras comuns e seção do Especificador) e o Passo 7 do `devagent/CICLO.md`; ignore o resto do ciclo de decisão. Ninguém acompanha esta sessão: não peça aprovação nem faça perguntas; diante de ambiguidade, escolha a opção mais conservadora e registre a decisão no PR.

1. **Estado:**
   ```bash
   git fetch origin
   python -m devagent.estado_github
   make install
   ```
2. **Alvo:** `python -m devagent.papel especificador`. Se disser que não há trabalho (a fila de specs `ready` tem mais de duas, ou já existe PR `spec:` aberto), encerre sem PR e sem commit. Se o alvo for destravar um PR da raia, trabalhe só na branch dele.
3. **Escreva uma única spec**, com o número que o alvo reservou. Primeiro, a issue aberta de feature ou melhoria mais antiga sem spec; sem ela, o Passo 7 inteiro, com as gavetas e as cadências (`python -m devagent.cadencias`) e as skills `descobrir-ideias.md`, `rever-experiencia.md` e `manutencao.md`. Modelo em `devagent/skills/escrever-spec.md`. A spec nasce `ready`, com `gaveta:` e **sem** `revisada:`.
4. **Confira antes do PR:** `python -m devagent.papel conferir especificador NNN`, por último. Saída diferente de 0 quer dizer que o número já foi usado ou há outro PR `spec:` aberto: descarte e encerre sem PR.
5. **Um único PR** `spec: NNN · título`, partindo da `main` atual, só com `docs/specs/`, `docs/BACKLOG.md` e `docs/runs/`, com o marcador `<!-- devagent:raia:especificacao -->` no corpo.
6. **Acompanhe o CI** até terminar e corrija na mesma branch se falhar. Não faça merge.
7. **Termine** com uma mensagem curta: a spec escrita e a gaveta, ou por que encerrou sem PR.
