---
id: 113a
titulo: Consultor numa data passada (exibição de recomendações e opiniões)
status: ready
esforco: M
gaveta: experiência
aceite: tests/test_aceite_113a.py
revisada: 2026-10-24
---

## Problema
Quem usa o Consultor quer ver o que ele recomendava em um pregão anterior. A spec 078 previa isso, mas a rota existe só no papel:
- o ramo histórico de `pagina_consultor` monta `dados` com `opinioes_recentes: []` e `opinioes_status: {}`, então a seção de opiniões fica vazia em qualquer data passada;

## Comportamento esperado
- `/consultor?data=AAAA-MM-DD` aceita os mesmos pregões do seletor (spec 088) e mostra:
  - as **recomendações registradas** daquele pregão em `consultor_recomendacoes`, agrupadas como na tela atual (Comprar, Vender, Aguardar, No radar), com a regra, o gatilho, o consenso e o preço da época. Nenhum recálculo.
  - as **opiniões de especialistas** com `extraida_em` até o fim daquele pregão (e dentro dos 30 dias anteriores), com a mesma tabela da tela atual.
  - o bloco "Informações de" com as datas daquele registro: o horário em que o diário foi gravado e o pregão dos sinais.
  - a faixa "Você está vendo o fechamento de dd/mm/aaaa" e o link "Voltar para hoje" (spec 088).
- Pregão sem registro no diário: "Sem registro do Consultor neste pregão." no lugar dos grupos, sem erro e sem recalcular.
- O cache da spec 087 não vale aqui: uma data passada lê só o que está gravado.
- Em 390 px, as tabelas seguem o padrão responsivo atual.

## Fontes de dados
Só o banco local (`consultor_recomendacoes`, `consultor_opinioes`, `series_diarias`). Nenhuma requisição externa.

## Critérios de aceite
- [ ] Com recomendações de fixture em três datas, `GET /consultor?data=<data>` mostra as recomendações exatas daquela data e nenhuma de outra.
- [ ] Opiniões com `extraida_em` posterior ao fim do pregão escolhido não aparecem; as anteriores (até 30 dias) aparecem.
- [ ] Data sem registro mostra "Sem registro do Consultor neste pregão." e responde 200.
- [ ] Abrir uma data passada não executa `INSERT`, `UPDATE` nem requisição externa.
- [ ] `/api/consultor?data=<data>` devolve o mesmo conteúdo em JSON, ou 404 para data fora da janela.

## Invariantes de produção
- A data mostrada no bloco "Informações de" de um pregão passado é a do registro, e não a de hoje.

## Fora do escopo
- Comparar duas datas lado a lado.
- Recalcular o que o Consultor teria dito num dia sem registro.
- Calcular o resultado e retorno após os pregões da recomendação.
- Alterar o coletor `consultor_fechamento`.
