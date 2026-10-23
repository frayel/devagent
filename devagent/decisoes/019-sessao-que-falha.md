# ADR 019 · Sessão que falha no Jules é retomada e, se não voltar, ensina

- **Data:** 2026-10-22 · **Status:** aceita
- **Complementa:** ADRs 012, 013 e 018

## Contexto

Três defeitos apareceram ao olhar as sessões de 21 e 22/10 no próprio Jules.

1. **Pergunta seguida de falha.** As sessões das specs 074 e 076a travaram num problema técnico (indentação quebrada por edição com regex no primeiro caso; testes que ainda consultavam tabelas removidas no segundo), fizeram uma pergunta e, na mesma mensagem, o Jules encerrou a tarefa em `FAILED`. O `destravar` só responde sessões em `AWAITING_USER_FEEDBACK`, então a resposta padrão nunca chegou. A rodada seguinte abriu outra sessão a partir da `main`, sem saber que a anterior tinha caído nem onde. Ao contrário do PR fechado pelo guardião, a sessão que falha não deixava rastro no repositório.
2. **Sessão nova para PR que já estava sendo corrigido.** Às 18h o job `disciplina` reprovou o #414. A rodada viu o PR como `travado` e abriu uma sessão para destravá-lo, enquanto a sessão dona do PR já corrigia pelo CI Fixer. A sessão nova reimplementou a spec 076b do zero e abriu o #415 depois que o #414 tinha sido mesclado; o guardião fechou por conflito grande.
3. **Varredura limpa tratada como trabalho perdido.** O Sentinel não achou nada e abriu o #406 só com o diário. A regra 1 do ADR 018 fechou como sessão que perdeu o trabalho e abriu a issue #407 mandando dividir uma spec que não existe.

## Decisão

1. **Retomada da sessão que falhou.** A rodada olha as sessões do ciclo em `FAILED` atualizadas nas últimas 6 h. Na primeira vez, manda a resposta que faltou (marcada com `[retomada automática]`) e não inicia sessão nova nessa volta. Enquanto a retomada tem menos de 15 min, a fila espera.
2. **Falha que não volta vira issue.** Se a sessão do desenvolvedor continuar em `FAILED` depois disso, ou se o Jules recusar a mensagem, a rodada abre uma issue `tentativa-falhou` com a spec do prompt e a última fala do agente. A issue cita a spec, então a regra 2 do ADR 018 faz a próxima sessão dividi-la, já sabendo onde a anterior travou. Um marcador com o nome da sessão impede issue repetida. Sessões dos especialistas são retomadas, mas não viram issue: não têm spec a dividir.
3. **PR vermelho com atividade recente está em correção.** O `situacao_dos_prs` trata como `esperar` o PR com CI falho que teve atividade (push ou cobrança do guardião) há menos de 60 min. Só depois disso ele fica `travado` e chama o desenvolvedor. O guardião continua cobrando e fechando nos prazos de sempre.
4. **Especialista sem achado não é falha.** PR de Sentinel, Palette ou Bolt que só traz o diário é fechado pelo guardião sem abrir `tentativa-falhou`.

## Consequências

- A pergunta que a sessão deixa no ar recebe resposta mesmo quando o Jules já encerrou a tarefa, se a API aceitar a mensagem nesse estado. Isso ainda precisa ser confirmado em produção; se não aceitar, a falha vira issue na hora.
- Uma falha custa no máximo 15 min de fila parada.
- O workflow `jules.yml` passa a precisar de `issues: write`.
- Um PR travado sem ninguém trabalhando nele espera até 60 min a mais antes de chamar o desenvolvedor.
