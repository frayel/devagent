---
id: 077
titulo: Data de referência e congelamento dos dados após o fechamento
status: done
esforco: M
---

## Problema
Pedido do dono do produto (ADR 008): durante o pregão o painel deve mostrar dados atuais; depois do fechamento, os dados ficam congelados e as fontes deixam de ser consultadas até o próximo pregão. Hoje o agendador coleta a cada 2 horas fora do pregão, inclusive em fins de semana, e regrava os mesmos números.

Depende das specs 073 a 076: só faz sentido congelar quando todos os painéis estão no Postgres.

## Comportamento esperado
- `app/calendario.py`: `pregao_corrente(agora)`, `ultimo_pregao_fechado(agora)`, `mercado_aberto(agora)` e `proximos_pregoes`, com os feriados da B3 e horários em BRT.
- `data_referencia` de cada snapshot passa a ser o pregão a que o dado pertence: durante o pregão, o dia corrente; entre a meia-noite e a abertura, o último pregão fechado.
- Cada coletor declara sua janela (`pregao`, `pre_abertura`, `continua`, `semanal`) no registro do agendador, conforme o ADR 008. Sem declaração, vale `pregao`. Clima Global declara `pre_abertura`; os feeds do consultor, `continua`; o histórico das regras do consultor, `semanal`.
- Rodada de fechamento: a primeira depois das 18h15 BRT em dia de pregão. Snapshot gravado com sucesso nela vira `final`. Falhou: nova tentativa a cada 30 min até 20h; depois, `incompleto`, com o último dado bom.
- Fora da janela, o agendador não chama nenhum coletor `pregao` e não faz requisição externa para eles.
- Partida a frio: se falta no banco o snapshot do último pregão fechado de um painel, uma única coleta é feita fora da janela, gravada como `final` daquele pregão e registrada em `GET /api/coleta` como `partida_a_frio`.
- Cabeçalho da página inicial e do `/consultor`:
  - mercado aberto: "Ao vivo · atualizado às HH:MM";
  - fechado: "Fechamento de dd/mm/aaaa · dados congelados";
  - snapshot `incompleto`: aviso no painel afetado, "Fechamento incompleto: último dado das HH:MM".
- Painéis intradiários (Variação Súbita, Armadilha de Abertura, Liquidez de Abertura e semelhantes) ganham no rótulo, quando o mercado está fechado, "situação no fechamento".
- `/api/snapshot` passa a trazer, na raiz, `data_referencia` e `estado_mercado` (`aberto` ou `fechado`), e cada painel traz o próprio `estado`.

## Fontes de dados
Nenhuma nova.

## Cálculos
- Horário de verificação em BRT (UTC−3, sem horário de verão).
- Janela `pregao`: 9h55 a 18h15 em dias de pregão. `pre_abertura`: 7h a 18h15. `continua`: a cada 2 h, todos os dias. `semanal`: sábado, uma vez.
- Feriados: `app/calendario.py` tem lista própria; um teste compara com `auditoria/calendario.py` para o ano corrente e o seguinte.

## Critérios de aceite
- [ ] Com o relógio simulado num sábado às 14h e o banco com snapshots finais da sexta, uma rodada do agendador não faz nenhuma requisição HTTP para coletores `pregao` (respx sem chamadas) e a página mostra "Fechamento de" com a data da sexta.
- [ ] Numa segunda-feira de pregão às 11h, a rodada coleta normalmente e grava `ao_vivo` com `data_referencia` da segunda.
- [ ] Às 18h20, uma rodada bem-sucedida marca os snapshots do dia como `final`; às 18h50 não há nova coleta desses painéis.
- [ ] Com a rodada de fechamento falhando até 20h, o snapshot vira `incompleto` e o painel mostra o aviso.
- [ ] Num feriado da B3 em dia útil, nenhum coletor `pregao` roda e a página mostra o fechamento do pregão anterior.
- [ ] Com o banco vazio num domingo, cada painel faz uma única coleta de partida a frio e `/api/coleta` a registra.
- [ ] O Clima Global coleta às 8h de um dia de pregão; os feeds do consultor coletam num domingo.
- [ ] Os feriados de `app/calendario.py` e de `auditoria/calendario.py` coincidem para os dois anos testados.

## Invariantes de produção
- Fora do pregão, `/api/snapshot` traz `estado_mercado = fechado`, `data_referencia` igual ao último pregão do calendário da B3 e os painéis com `estado = final` (ou `incompleto`, com aviso visível).
- Fora do pregão, o valor do Ibovespa exibido é o fechamento oficial do último pregão, a no máximo 0,1% de uma fonte independente.
- Entre 20h de sexta e 7h de segunda, `GET /api/coleta` não registra nenhuma coleta de coletor `pregao`, exceto partidas a frio.

## Fora do escopo
- Seletor de pregões anteriores (spec 078).
- Ajustar o auditor (`auditoria/`): feito num PR próprio depois desta spec, conforme o `devagent/CICLO.md`.
- Pregões com horário especial (véspera de Natal, Quarta-Feira de Cinzas): registrar no backlog.
