# ADR 031 · O Verificador vê todo merge na main e examina todo PR que mexe num limite

- **Data:** 2026-11-03 · **Status:** aceita
- **Revê:** ADRs 021 (raias paralelas), 024 (revisão do ciclo); CICLO.md; raias.md

## Contexto

Uma investigação sobre por que o Verificador não detectou o defeito da variação diária de +12,87% e a elevação do teto de variação (#601 e #602) revelou quatro lacunas operacionais:

1. **Exclusão de PRs abertos por humanos:** `merges_do_desenvolvimento` exigia `do_agente(login)`, herdando a regra do guardião e travamento de raias (ADR 024), deixando de fora commits e merges feitos por humanos na `main` (11 dos últimos 50 commits eram de pessoas). Esses PRs nunca eram avaliados nem abriam sessões do Verificador.
2. **Listagem curta sem paginação:** A consulta à API do GitHub usava `per_page=50` sem paginação, e o prompt cortava a lista em 15 PRs sem avisar sobre omissões.
3. **Checklist sem verificação de rótulo vs. período:** O checklist do Verificador não orientava checar se o período do rótulo exibido na interface ("hoje", "30 dias") correspondia à janela da consulta e à verdade do dado.
4. **Ausência de tratamento especial para limites e sensores:** Diferente do Auditor, o Verificador não priorizava PRs que alteravam constantes de tolerância, limites máximos ou arquivos de auditoria.

## Decisão

1. **Todo merge de desenvolvimento entra na verificação:** `merges_do_desenvolvimento` inclui qualquer PR da raia de desenvolvimento (`raia_do_titulo`), independente de ser do agente ou de pessoas.
2. **Paginação na busca de merges:** A busca percorre até 5 páginas de PRs fechados ordenados por atualização decrescente até encontrar um PR atualizado antes de `desde`.
3. **Priorização de sensores:** PRs que alteram arquivos em `auditoria/` ou modificam limites (`MAXIMO/A`, `LIMITE`, `TOLERANCIA`, `TETO`) no patch são marcados `[sensor]` e posicionados no início do prompt. Falhas ao consultar `/files` não travam a sessão e registram `arquivos não consultados`.
4. **Sem corte silencioso no prompt:** O prompt lista os 15 PRs mais recentes mais todos os `[sensor]`; se restarem PRs de fora, informa explicitamente `+N PRs omitidos; liste com git log --merges`.
5. **Checklist atualizado:** Adicionados os itens *Verdade do número* e *Sensores* no checklist do Verificador em `devagent/agents/raias.md`.

## Consequências

- O Verificador tem visibilidade completa sobre qualquer alteração mesclada na `main`.
- Qualquer afrouxamento de limites ou auditoria é examinado com prioridade.
