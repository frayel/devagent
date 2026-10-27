# ADR 024 · Revisão do ciclo: raia pela sessão, PRs de pessoas, redundância e cadências calculadas

- **Data:** 2026-10-27 · **Status:** aceita
- **Revê:** ADRs 020, 021 e 023; regra 7 dos especialistas; cadências do Passo 7

## Contexto

Uma revisão do ciclo em 27/10, cruzando o código com os PRs e issues das últimas 48 h, achou estes furos:

1. A 092a foi dividida duas vezes em 15 min (#542 em 119a/b, #543 em 120a/b), e a 093 também (#545 e #548). As duas edições na spec original eram idênticas (`status: draft`), não geravam conflito, o CI passava e o auto-merge mesclava as duas. A fila ficou com 119b, 120a e 120b para o mesmo trabalho.
2. A raia de um PR saía só do prefixo do título. Os #542 e #543 vieram de sessões do Desenvolvedor intituladas `spec:` e escaparam da regra do ADR 023.
3. `tentativa-falhou` só fechava com a spec `done`. A #523 (092, dividida) e a #550 (093, e 122 a 124, que não existem) ficariam abertas para sempre.
4. O Verificador abria PR com "0 achados" (#502, #513, #537).
5. Auto-merge, guardião e estado tratavam PR de pessoa como PR do agente: o guardião cobraria `@jules` e fecharia o PR do dono, apagaria as branches dele, e a rodada esperaria por ele ou mandaria o desenvolvedor mexer nele.
6. Especialista sem achado assumia o ciclo do desenvolvedor na mesma sessão, lendo a mesma fila sem as travas dela.
7. O Revisor criou números novos (122 a 124) ao dividir a 093.
8. A revisão não procurava duplicatas nem conferia se o código já fazia o pedido; as revisões viraram ajuste de forma.
9. Os contadores das cadências eram uma linha do `STATE.md` editada pelo desenvolvimento e pelo Especificador.
10. Uma sessão pulou o Passo 1 com três issues de produção abertas.
11. A rodada tinha 3 min de timeout, `encerrar` apagava a sessão (e o diagnóstico), o CI não rodava quando o título mudava e as raias não tinham teto de cota.

## Decisão

1. **A raia vem da sessão.** O corpo dos PRs do Jules traz `jules.google.com/task/<id>`; o job `disciplina` consulta a sessão (com `JULES_API_KEY`) e reprova o título de outra raia (`raias.RAIA_DA_PERSONA`).
2. **Redundância antes do merge.** O auto-merge roda `guardiao_prs --antes-do-merge`: PR que altera spec que a `main` já alterou depois que a branch saiu dela fecha sem merge.
3. **Tentativa órfã** fecha também quando todas as specs citadas estão `draft` ou não existem.
4. **Verificação sem achado novo em `docs/verificacao/achados/` reprova.**
5. **Só PRs do Jules (`google-labs-jules[bot]`) são do agente** para o guardião, o estado, as raias e as branches órfãs. PR de pessoa fica fora da regra 8. O auto-merge continua mesclando PR de pessoa com CI verde.
6. **Especialista sem achado encerra sem PR**, sem assumir o ciclo.
7. **PR `revisão:` só cria partes com sufixo de letra da spec que altera** e traz no corpo as linhas `Tamanho:` e `Já no código:`. O Revisor procura duplicatas e confere o código antes de aprovar.
8. **Cadências calculadas** (`devagent/cadencias.py`) a partir do `status:` e da `gaveta:` das specs. Ninguém edita contador; o Especificador não escreve mais no `STATE.md`.
9. **Issues de produção abertas vão no prompt do desenvolvedor**, com número, antes da fila.
10. Rodada com 8 min; `encerrar` não apaga a sessão; CI também em `edited`; teto diário por raia auxiliar (especificador 8, revisor 24, verificador 16).
11. 120a e 120b voltam a `draft` como duplicatas de 119a e 119b.

## Consequências

- Duas sessões que fazem o mesmo trabalho sobre a mesma spec não chegam as duas à `main`: a segunda fecha como redundante.
- Sem `JULES_API_KEY` no CI (secret ausente) a regra da sessão fica de fora sem reprovar.
- A cadência de manutenção depende da `gaveta:` certa; spec de bug marcada `saúde técnica` zera o contador. O `CICLO.md` passou a pedir a gaveta certa.
