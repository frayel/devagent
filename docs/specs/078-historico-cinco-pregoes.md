---
id: 078
titulo: Histórico dos últimos 5 pregões
status: done
esforco: M
---

## Problema
Pedido do dono do produto (ADR 008): poder voltar aos últimos dias e ver como o mercado e os sinais estavam em cada fechamento, sem depender da memória ou de outros sites.

Depende da spec 077 (snapshots por pregão com estado `final`).

## Comportamento esperado
- No topo da página inicial e do `/consultor`, um seletor com o pregão atual e os 5 pregões anteriores que tenham snapshot, rotulados "Hoje" (ou "Último fechamento", com o mercado fechado) e `dd/mm` com o dia da semana abreviado.
- Escolher uma data carrega `/?data=AAAA-MM-DD` (e `/consultor?data=...`), via HTMX trocando só o conteúdo, sem recarregar a página. A URL muda, para poder ser compartilhada ou favoritada.
- Numa data passada:
  - todos os painéis mostram a versão `final` daquele pregão, com o horário de coleta;
  - um painel sem snapshot naquela data mostra "Sem registro neste pregão";
  - uma faixa no topo diz "Você está vendo o fechamento de dd/mm/aaaa" com um link "Voltar para hoje";
  - nenhuma coleta é disparada.
- `/api/snapshot?data=AAAA-MM-DD` devolve o snapshot daquele pregão no mesmo formato do atual. Data fora dos 5 últimos pregões, futura, inválida ou sem pregão: resposta 404 com mensagem em JSON. A página, nesses casos, volta ao pregão atual com um aviso.
- No `/consultor`, uma data passada mostra as recomendações registradas no diário (spec 072) para aquele pregão, não um recálculo.
- Em telas de 390 px o seletor vira uma lista suspensa.

## Fontes de dados
Nenhuma. Só leitura de `snapshots_paineis` e do diário do consultor.

## Cálculos
- Pregões disponíveis: as 6 datas mais recentes com pelo menos um snapshot `final` ou `incompleto` (mais o dia corrente, se o mercado estiver aberto), conforme `listar_datas`.
- Retenção de 30 pregões no banco (ADR 007). O seletor mostra só 5 anteriores; a constante `PREGOES_NO_SELETOR = 5` fica em um único lugar.

## Critérios de aceite
- [ ] Com snapshots de fixture para 7 pregões, o seletor lista o atual e os 5 anteriores, sem o mais antigo.
- [ ] `/?data=` de um pregão do fixture mostra os números desse pregão e a faixa "Você está vendo o fechamento de".
- [ ] `/api/snapshot?data=` de um pregão do fixture devolve `data_referencia` igual ao parâmetro e `estado = final`.
- [ ] `/api/snapshot?data=` com data inválida, futura ou fora da janela devolve 404.
- [ ] Um painel sem snapshot na data escolhida mostra "Sem registro neste pregão", e os demais aparecem.
- [ ] Abrir uma data passada não faz nenhuma requisição HTTP externa (respx sem chamadas).
- [ ] A rotina diária de retenção remove snapshots além de 30 pregões e preserva os mais recentes.
- [ ] O seletor funciona em 390 px sem rolagem horizontal (checklist visual do `docs/DESIGN.md`).

## Invariantes de produção
- `/api/snapshot?data=` do pregão anterior traz o Ibovespa igual ao fechamento oficial daquele dia, a no máximo 0,1% de uma fonte independente.
- O seletor nunca oferece um dia que não seja pregão no calendário da B3.

## Fora do escopo
- Comparar dois pregões lado a lado (registrar no backlog).
- Histórico intradiário de pregões passados.
- Janela maior que 5 pregões na interface.
