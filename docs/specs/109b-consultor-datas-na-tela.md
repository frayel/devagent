---
id: 109b
titulo: Consultor: exibição da data de cada informação na interface
status: draft
esforco: P
gaveta: experiência
aceite: tests/test_aceite_109b.py
revisada: 2026-10-25
---

## Problema

A tela do Consultor não mostra nenhuma data. Quem decide com base nela não sabe se os sinais técnicos são do último pregão ou de uma semana atrás, nem se as opiniões das casas foram lidas hoje. (Depende da Spec 109a que arruma os dados base).

## Comportamento esperado

### Bloco "Informações de" no topo do Consultor

Três datas, sempre em BRT, no formato `dd/mm/aaaa HH:MM`:

- **Sinais técnicos**: pregão da última barra do Ibovespa usada no cálculo (só `dd/mm/aaaa`) e hora da coleta (`coletado_em`).
- **Opiniões de especialistas**: horário da última extração (`ultima_extracao_em`, spec 085) e data da matéria mais recente exibida.
- **Composição do Ibovespa**: a data em que a lista `CARTEIRA_IBOVESPA` foi conferida (constante `CARTEIRA_CONFERIDA_EM` em `app/consultor/universo.py`), já que hoje só há o aviso de "possivelmente desatualizada".

Cada data traz um selo escrito, além da cor: **Atualizado** ou **Defasado**.

- Sinais: *Defasado* se a última barra for anterior ao último pregão fechado (`calendario.ultimo_pregao_fechado`), ou se a coleta tiver mais de 4 dias.
- Opiniões: *Defasado* se a última extração tiver mais de 24 h em dia útil, ou mais de 72 h em fim de semana e feriado.
- Quando algum selo é *Defasado*, o primeiro painel da página diz em uma frase o que está velho e desde quando.

`/api/consultor` devolve os mesmos campos (`informacoes_de`: `sinais_pregao`, `sinais_coletado_em`, `opinioes_extraidas_em`, `composicao_conferida_em`, e o estado de cada um).

## Fontes de dados

Só o banco local.

## Critérios de aceite (1 arquivo de teste editado)

- [ ] Com série atual, `GET /consultor` mostra "Sinais técnicos" com a data do pregão da fixture e o selo *Atualizado*.
- [ ] Com a última barra dois pregões atrás, o selo é *Defasado* e a frase de aviso no topo cita a data.
- [ ] Opiniões extraídas há 30 h em dia útil mostram *Defasado*; há 10 h, *Atualizado*; sexta à noite vista no sábado, *Atualizado*.
- [ ] A página nunca contém `1969` nem `1970`.
- [ ] `/api/consultor` traz o objeto `informacoes_de` com os quatro campos.
- [ ] Em 390 px o bloco quebra em linhas sem rolagem horizontal.

## Invariantes de produção

- A data dos sinais na tela do Consultor é igual à última data do gráfico do Ibovespa na página inicial.
- A data dos sinais nunca é anterior ao último pregão fechado por mais de um dia útil sem o selo *Defasado*.

## Revisão

A spec 109b é inviável e duplicada. A funcionalidade e o comportamento descritos aqui já foram especificados de forma quase idêntica em `docs/specs/108b-consultor-interface-datas.md`, que também descreve a exibição das datas na interface do Consultor e a dependência dos carimbos reais do banco de dados (providos pela spec 108a). Além disso, a spec 109a da qual ela depende também está como `draft` pelo mesmo motivo (duplicação da 108a). Por isso, esta spec foi marcada como `draft` para que o Especificador não repita a ideia.
