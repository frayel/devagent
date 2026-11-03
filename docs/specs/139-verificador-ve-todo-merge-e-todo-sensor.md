---
id: 139
titulo: O Verificador vê todo merge na main e examina todo PR que mexe num limite
status: ready
esforco: M
gaveta: saúde técnica
aceite: devagent/tests/test_aceite_139.py
revisada: 2026-11-03
---

## Problema
O usuário perguntou: "por que o agente verificador não pegou isso?" O código mostra quatro lacunas que, juntas, deixam passar um defeito como o da spec 134 e a troca de um limite como a da spec 136:

1. **PR feito por pessoa não entra na lista.** `merges_do_desenvolvimento` (`devagent/adaptadores/jules.py:959`) filtra com `do_agente(login)` (`devagent/raias.py:66`), que só aceita o login do Jules. A exclusão é deliberada para o guardião e para o travamento de raias (comentário em `devagent/raias.py`, ADR 024: PR de outro autor "não é do agente"), mas o Verificador herdou o filtro. Dos 50 commits da `main`, 11 têm como autor Felipe Rayel, quase todos com título de desenvolvimento (`fix:`, `feat:`, `refactor:`, `agent:`). Entre eles estão o #601 (`6210c6c`) e o #602 (`35b8957`), que subiram de 12% para 20% o teto de variação diária no coletor e na auditoria, os únicos freios que teriam barrado o +12,87%. Nenhum relatório em `docs/verificacao/`, `docs/auditoria/` ou `docs/runs/` cita os dois. Não consegui consultar os PRs no GitHub para confirmar quem os abriu; o autor dos commits indica que não foi o bot. Pelo mesmo filtro, esses merges não contam como "merge novo" para abrir a sessão do Verificador (`raias_a_iniciar`).
2. **A listagem é curta.** O `github_get` usa `per_page=50` ordenado por atualização, sem paginar, e o prompt corta a lista em `merges[:15]` (`devagent/adaptadores/jules.py:721`) sem avisar que omitiu PRs.
3. **O checklist não pergunta se o número bate com o rótulo.** Os itens de `devagent/agents/raias.md` (correção, segurança, robustez, experiência, documentos) conferem o código contra a spec. "Este percentual é do período que o título diz?" é a pergunta do Auditor; mas ele só olha a produção, e o Verificador depende do `make verify`, que passou porque os dublês do Yahoo tinham a mesma suposição do código (spec 135).
4. **Mudança de limite não tem tratamento especial.** `devagent/agents/auditor.md` proíbe o *Auditor* de afrouxar limites. Para o *Verificador* não há regra equivalente: um PR que sobe um teto ou uma tolerância é lido como qualquer outro.

Ainda sobre o passado: o histórico da `main` começa num commit único (`c3ee226`, com título sem relação) que importou o repositório inteiro. O código antigo nunca foi um diff, e a lista de PRs não o alcança. Isso fica fora desta spec (ver *Fora do escopo*).

## Comportamento esperado
1. **Todo merge de desenvolvimento entra na lista.** `merges_do_desenvolvimento` deixa de exigir `do_agente`: vale qualquer autor, desde que o título seja da raia de desenvolvimento (`raia_do_titulo`) e o PR tenha sido mesclado depois de `desde`. PRs de outras raias (`spec:`, `revisão:`, `verificação:`, `auditoria:`) continuam de fora. A contagem `merges_novos` usada por `raias_a_iniciar` passa a incluir os merges de pessoas. O que o ADR 024 decidiu sobre o guardião e o travamento de raias **não muda**: `do_agente` continua valendo lá.
2. **Paginação.** A busca percorre as páginas de `state=closed&sort=updated&direction=desc` até encontrar uma página cujo PR mais antigo foi atualizado antes de `desde`, com teto de 5 páginas.
3. **Sensores primeiro.** Para cada PR da lista, o adaptador consulta `/pulls/{n}/files` (a mesma `github_get`). O PR é marcado `[sensor]` se alterar qualquer arquivo em `auditoria/` ou se o `patch` de algum arquivo tiver linha adicionada ou removida casando `^[+-].*\b\w*(MAXIM[AO]|LIMITE|TOLERANCIA|TETO)\w*\s*=`. PRs `[sensor]` vão no início do prompt. Falha ao listar os arquivos de um PR não derruba a sessão: o PR entra sem marca e o prompt diz `arquivos não consultados`.
4. **Sem corte silencioso.** O prompt traz os 15 mais recentes **mais** todos os `[sensor]`; se sobrar PR de fora, a frase final é `+N PRs omitidos; liste com git log --merges`.
5. **Checklist.** Em `devagent/agents/raias.md`, seção *Verificador*, passo 3, entram dois itens:
   - **Verdade do número:** para cada número, percentual ou rótulo de período que o PR cria ou muda e que o usuário vê, ache de onde ele sai (fonte, janela da consulta, valor de referência), confira se o período do rótulo ("hoje", "30 dias") é o da janela, e compare com outro número da mesma tela (gráfico, série, soma). Código antigo que o PR só chama também conta.
   - **Sensores:** PR marcado `[sensor]` é sempre examinado. Se afrouxa um limite, tolerância ou checagem sem evidência de **fonte independente** e **posterior** ao PR (o número que justificou a mudança, de onde veio e quando), vira achado `media`. O texto "o dado era verdadeiro" no commit não é evidência.
   O passo 1 passa a dizer que a lista inclui merges feitos por pessoas.
6. **ADR.** `devagent/decisoes/031-verificador-ve-todo-merge-e-todo-sensor.md` registra o porquê (as quatro lacunas e o caso do +12,87%), e o índice de ADRs da seção 9 do `devagent/CICLO.md` ganha a entrada `031`.

## Fontes de dados
API do GitHub já usada pelo adaptador (`github_get`). Plano B: se a listagem de PRs falhar, o comportamento atual (lista vazia, sem sessão) permanece; se só `/files` falhar, vale o item 3.

## Cálculos
Nenhum.

## Critérios de aceite
- [ ] Com `github_get` falso devolvendo 3 PRs mesclados de desenvolvimento (um do bot, um de pessoa, um de outra raia), `merges_do_desenvolvimento` devolve os 2 de desenvolvimento.
- [ ] Com 60 PRs fictícios em 2 páginas, todos os mesclados depois de `desde` aparecem; a busca para na primeira página inteira anterior a `desde`.
- [ ] Um PR que altera `auditoria/auditar.py`, e um que troca `VARIACAO_DIARIA_MAXIMA = 12.0` por `20.0` no `patch`, saem marcados `[sensor]` e no início do prompt.
- [ ] Com 20 PRs e 1 `[sensor]` antigo, o prompt traz 15 recentes + o sensor e termina com `+4 PRs omitidos`.
- [ ] Falha simulada em `/files` de um PR: o prompt contém `arquivos não consultados` para ele e a função não levanta exceção.
- [ ] `raias_a_iniciar` com `merges_novos` contando um merge de pessoa abre o Verificador (teste ao lado de `test_verificador_precisa_de_merge_e_de_intervalo`).
- [ ] `devagent/agents/raias.md` contém os rótulos `Verdade do número` e `Sensores`; o ADR 031 existe e está no índice do `CICLO.md`.
- [ ] Os testes atuais de `devagent/tests/test_raias.py` seguem verdes.
- Arquivos tocados: `devagent/adaptadores/jules.py`, `devagent/raias.py` (se a regra de autor mudar de lugar), `devagent/agents/raias.md`, `devagent/CICLO.md` (índice), `devagent/decisoes/031-...md` e o novo `devagent/tests/test_aceite_139.py`.

## Invariantes de produção
- Todo PR de desenvolvimento mesclado na `main` aparece, no máximo na verificação seguinte, no relatório do Verificador (`docs/verificacao/relatorios/`), com o resultado ou com a menção `omitido`.
- Todo PR que mexe em limite ou em `auditoria/` tem, no relatório, a linha `Sensores:` com a evidência ou com o achado.

## Fora do escopo
- Varredura retroativa do código que nunca passou por diff (os coletores do commit `c3ee226`). Vale uma spec própria: uma passada do Verificador por coletor, perguntando "de onde sai este número?". Ela fica para depois desta, para não misturar processo com mapeamento.
- Verificar PRs de outras raias.
- Mudar a cadência do Verificador (mínimo de 90 minutos entre sessões).
- Mexer em `auditoria/` ou `docs/auditoria/`.

<!-- Revisada: a spec está de acordo com escrever-spec.md e pronta. -->
