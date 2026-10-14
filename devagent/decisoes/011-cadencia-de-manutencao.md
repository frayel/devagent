# ADR 011 · Cadência de manutenção e poda no Passo 7

**Data:** 2026-10-14 · **Status:** aceito

## Contexto

O ciclo de decisão é uma fila de prioridades. Os passos 1 a 6 reagem a algo que já aconteceu (produção quebrada, PR travado, spec pronta, documentação desatualizada, issue aberta). Quando não há nada para reagir, o ciclo cai no Passo 7, e o Passo 7 sempre termina com uma spec nova. Na execução seguinte, o Passo 4 implementa essa spec, o sistema volta a ficar ocioso e o ciclo volta ao Passo 7.

Os relatórios de 11 a 15/10 mostram esse vai e vem entre os passos 4 e 7, interrompido só por falhas de produção. O dono do projeto perguntou se o agente ia criar painéis para sempre. Pelas instruções, ia.

A cadência de experiência (ADR 006) foi o primeiro freio e funcionou: gerou as revisões que reorganizaram a tela. Mas ela só olha a tela. Nenhum passo pedia ao agente para olhar o que está atrás dela:

- quase todos os módulos repetem o mesmo molde de coletor, cache e teste, e cada parte nova copia o molde de novo;
- cada parte nova acrescenta chamadas a fontes externas na mesma rodada de coleta, sem que nada meça o custo acumulado;
- partes que passam a maior parte do tempo sem dados foram escondidas da tela em vez de questionadas;
- nenhuma regra autorizava, e muito menos pedia, que o agente removesse algo que ele mesmo construiu.

Sem um passo que pergunte, o agente nunca responde.

## Decisão

- O Passo 7 passa a classificar todo trabalho em quatro gavetas: *Capacidade nova*, *Experiência*, *Saúde técnica* e *Poda*. O relatório registra a gaveta escolhida.
- Toda rodada do Passo 7 gera ao menos uma ideia de *Experiência* e uma de *Saúde técnica* ou *Poda*, esta última sustentada por uma medida.
- **Cadência de manutenção:** o `docs/STATE.md` conta as specs entregues desde a última rodada de manutenção (as de manutenção não contam). Com 4, o Passo 7 faz uma rodada obrigatória e escolhe uma ideia de *Saúde técnica* ou *Poda*. Se vencer junto com a de experiência, a manutenção vai primeiro.
- Nova skill `devagent/skills/manutencao.md`: medir antes de opinar, transformar achados em ideias com número, escrever a spec e respeitar os limites. Se o sistema não guarda a medida necessária, a primeira entrega é o instrumento de medida.
- Specs de manutenção declaram `gaveta:` no cabeçalho e são implementadas no Passo 4 com PR `refactor:`.
- O projeto indica no `PRODUTO.md` onde medir e o critério objetivo de poda. O núcleo não conhece esses caminhos. O modelo de `PRODUTO.md` e o `docs/STATE.md` inicial do instalador ganham as seções correspondentes.

## O que não muda

Os limites da seção 6 do `CICLO.md`. Em especial: testes não são apagados para o CI passar (os de uma parte podada saem junto com ela, na spec de poda), specs `done` e relatórios ficam, e checagens da auditoria só são removidas num PR próprio, depois da poda chegar à `main`. A regra de uma spec `ready` por vez e de PRs de até ~400 linhas também vale para refatorações, que vão em fatias.

## Consequências

O produto passa a alternar três ritmos: crescer, reorganizar e simplificar. Em regime, de cada seis execuções do Passo 7, cerca de uma é de manutenção e outra de experiência.

Riscos:

- **Manutenção sem fim.** O agente pode passar a gostar de refatorar. A cadência é um piso, não um teto, mas a gaveta *Capacidade nova* continua livre nas demais rodadas, e as medidas registradas no `STATE.md` mostram se o ganho prometido apareceu.
- **Poda tímida.** O agente tende a preservar o que construiu. O critério objetivo do `PRODUTO.md` existe para tirar essa decisão do gosto.
- **Refatoração que muda comportamento.** A skill exige que a saída visível continue a mesma nas specs de saúde técnica.
