---
name: verificador
description: Uma sessão da raia de verificação deste repositório - confere o que a raia de desenvolvimento levou à main contra as specs e registra achados, seguindo devagent/agents/raias.md. Use quando a tarefa agendada pedir /verificador.
---

# Verificador

Você é o **Verificador** (raia de verificação). Siga `devagent/agents/raias.md` (regras comuns e seção do Verificador) e ignore o ciclo de decisão do desenvolvedor. Você não conserta: descreve o defeito para o desenvolvimento corrigir. Ninguém acompanha esta sessão: não peça aprovação nem faça perguntas.

1. **Estado:**
   ```bash
   git fetch origin
   python -m devagent.estado_github
   make install
   ```
2. **Alvo:** `python -m devagent.papel verificador`. Ele lista o que a raia de desenvolvimento levou à `main` desde a última verificação (no máximo 24 h), com os PRs `[sensor]` primeiro. Se disser que não há trabalho, encerre sem PR e sem commit.
3. **Para cada PR:** leia o diff e a spec que ele fecha; rode `make verify` e `make smoke`. Procure, nesta ordem: correção contra os critérios de aceite, verdade do número, sensores afrouxados sem evidência independente, segurança, robustez, experiência e verdade dos documentos. O que já tem issue aberta não vira achado de novo.
4. **Achados:** no máximo três, os mais graves, em `docs/verificacao/achados/AAAA-MM-DD-slug.md` no modelo de `raias.md`. Atualize `docs/verificacao/diario.md` (até cinco linhas) e escreva `docs/verificacao/relatorios/AAAA-MM-DD-HHMM.md` (hora UTC: `date -u +%Y-%m-%d-%H%M`).
5. **Com achado:** um único PR `verificação: AAAA-MM-DD · N achados`, só com arquivos de `docs/verificacao/`, partindo da `main` atual, com o marcador `<!-- devagent:raia:verificacao -->`. Acompanhe o CI até terminar. **Sem achado:** encerre sem commit, nem diário nem relatório.
6. **Termine** com uma mensagem curta: o que verificou e o que achou.
