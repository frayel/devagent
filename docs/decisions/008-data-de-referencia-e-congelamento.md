# ADR 008 · Data de referência, congelamento após o fechamento e histórico de 5 pregões

**Data:** 2026-10-18 · **Status:** aceito · **Origem:** pedido do dono do produto · **Depende de:** ADR 007

## Contexto

O agendador coleta a cada 15 minutos no pregão e a cada 2 horas fora dele (ADR 004). Fora do pregão, os dados de mercado não mudam: as coletas noturnas e de fim de semana gastam requisições, cota de fontes e tempo de CPU para gravar o mesmo valor. O dono do produto pediu que, depois do fechamento, os dados fiquem congelados e as fontes deixem de ser consultadas, e que seja possível ver os últimos 5 pregões.

## Decisão

1. **Data de referência.** Todo dado de painel pertence a um pregão. `app/calendario.py` (da aplicação, separado do `auditoria/calendario.py` para o auditor continuar independente) responde: o pregão corrente, o último pregão fechado e se o mercado está aberto. Um teste confere que os dois calendários concordam sobre os feriados do ano.
2. **Janela de cada coletor.** Cada coletor declara uma janela no registro do agendador:
   - `pregao` (padrão): coleta só entre 9h55 e 18h15 BRT em dias de pregão;
   - `pre_abertura`: também entre 7h e 9h55 BRT em dias de pregão (ex.: Clima Global, que olha bolsas estrangeiras abertas antes da B3);
   - `continua`: fontes que publicam fora do pregão, como os feeds de notícias do consultor (spec 070), a cada 2 horas;
   - `semanal`: recálculos pesados, como o histórico das regras do consultor (spec 069).
3. **Congelamento.** A primeira rodada depois das 18h15 BRT é a de fechamento. Se ela grava um painel com sucesso, o snapshot do pregão vira `final`. Se falha, há novas tentativas a cada 30 minutos até as 20h; depois disso o snapshot fica `incompleto`, com o último dado bom e um aviso no painel.
4. **Fora da janela, nenhuma requisição externa** para coletores `pregao`. A página mostra o snapshot `final` do último pregão com o rótulo "Fechamento de dd/mm/aaaa".
5. **Partida a frio.** Se o banco não tem snapshot do último pregão fechado para um painel (primeiro deploy, painel novo, banco recriado), uma única coleta é permitida fora da janela para construí-lo, e ela é registrada em `GET /api/coleta`.
6. **Histórico.** A página inicial, o `/consultor` e o `/api/snapshot` aceitam `?data=AAAA-MM-DD` para qualquer um dos 5 últimos pregões com snapshot. Sem o parâmetro, valem o pregão corrente (mercado aberto) ou o último fechado. Pregões passados exibem a versão `final` ou `incompleta`, nunca dados intradiários.

## Consequências

- Noites, fins de semana e feriados não fazem nenhuma requisição às fontes de mercado, exceto as janelas `continua` e `semanal` e a partida a frio.
- O auditor passa a checar que, fora do pregão, o `/api/snapshot` traz `estado = final` e `data_referencia` igual ao último pregão (`auditoria/README.md` atualizado num PR próprio, como manda o `devagent/CICLO.md`).
- Um painel que depende do dia corrente (por exemplo, "variação súbita" intradiária) mostra, em pregões passados, o estado no fechamento daquele dia. Isso precisa estar escrito no rótulo do painel.
- Feriado fora do calendário vira um dia sem snapshot, não um erro; o histórico pula a data.
