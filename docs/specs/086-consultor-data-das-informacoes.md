---
id: 086
titulo: Consultor mostra a data de cada informação e avisa quando está defasada
status: draft
esforco: P
gaveta: experiência
aceite: tests/test_aceite_086.py
revisada: 2026-10-24
---

## Problema

A tela do Consultor não mostra nenhuma data. Quem decide com base nela não sabe se os sinais técnicos são do último pregão ou de uma semana atrás, nem se as opiniões das casas foram lidas hoje.

Há também um defeito por baixo. `calcular_consultor` monta o campo `timestamp` a partir de `ibov_ts[-1]`, mas `app.database.get_historico_diario` devolve `"timestamp": [1] * len(closes)` (um carimbo fictício de 1 segundo desde 1970). O valor nunca chega ao template, que não o usa, e se chegasse mostraria 31/12/1969. Qualquer lógica que dependa desses carimbos (alinhamento de séries em `avaliador_historico.pre_processar_ativo`) trabalha com dados falsos.

## Comportamento esperado

### Carimbos reais

`get_historico_diario` passa a devolver, para cada ativo, os timestamps reais das barras (epoch em segundos do pregão, a partir do campo `data` de cada barra gravada por `gravar_serie`), e `coletado_em`, o maior `criado_em` das linhas lidas de `series_diarias`. Antes de mudar, o desenvolvimento lista todos os chamadores (`calculador`, `avaliador_historico`, `utils`) e confere que nenhum depende do valor fictício; os testes existentes seguem verdes.

### Bloco "Informações de" no topo do Consultor

Três datas, sempre em BRT, no formato `dd/mm/aaaa HH:MM`:

- **Sinais técnicos**: pregão da última barra do Ibovespa usada no cálculo (só `dd/mm/aaaa`) e hora da coleta (`coletado_em`).
- **Opiniões de especialistas**: horário da última extração (`ultima_extracao_em`, spec 085) e data da matéria mais recente exibida.
- **Composição do Ibovespa**: a data em que a lista `CARTEIRA_IBOVESPA` foi conferida (constante nova em `app/consultor/universo.py`), já que hoje só há o aviso de "possivelmente desatualizada".

Cada data traz um selo escrito, além da cor: **Atualizado** ou **Defasado**.

- Sinais: *Defasado* se a última barra for anterior ao último pregão fechado (`calendario.ultimo_pregao_fechado`), ou se a coleta tiver mais de 4 dias.
- Opiniões: *Defasado* se a última extração tiver mais de 24 h em dia útil, ou mais de 72 h em fim de semana e feriado.
- Quando algum selo é *Defasado*, o primeiro painel da página diz em uma frase o que está velho e desde quando.

`/api/consultor` devolve os mesmos campos (`informacoes_de`: `sinais_pregao`, `sinais_coletado_em`, `opinioes_extraidas_em`, `composicao_conferida_em`, e o estado de cada um).

## Fontes de dados

Só o banco local. Nenhuma requisição nova.

## Critérios de aceite

- [ ] `get_historico_diario` devolve timestamps reais e monotônicos para uma série de fixture (nenhum valor igual a 1) e `coletado_em`.
- [ ] Com série atual, `GET /consultor` mostra "Sinais técnicos" com a data do pregão da fixture e o selo *Atualizado*.
- [ ] Com a última barra dois pregões atrás, o selo é *Defasado* e a frase de aviso no topo cita a data.
- [ ] Opiniões extraídas há 30 h em dia útil mostram *Defasado*; há 10 h, *Atualizado*; sexta à noite vista no sábado, *Atualizado*.
- [ ] A página nunca contém `1969` nem `1970`.
- [ ] `/api/consultor` traz o objeto `informacoes_de` com os quatro campos.
- [ ] Em 390 px o bloco quebra em linhas sem rolagem horizontal.

## Invariantes de produção

- A data dos sinais na tela do Consultor é igual à última data do gráfico do Ibovespa na página inicial.
- A data dos sinais nunca é anterior ao último pregão fechado por mais de um dia útil sem o selo *Defasado*.

## Fora do escopo

- Escolher outra data de referência (spec 089).
- Recalcular o Consultor automaticamente quando a série é renovada.

## Revisão
A spec era muito grande e foi dividida em 108a e 108b porque tocava em muitos arquivos de backend e frontend de uma vez.
