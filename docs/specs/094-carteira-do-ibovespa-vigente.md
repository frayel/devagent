---
id: 094
titulo: Carteira do Consultor igual à composição vigente do Ibovespa
status: draft
esforco: M
gaveta: saúde técnica
aceite: tests/test_aceite_094.py
revisada: 2026-10-25
---

## Revisão

A spec foi marcada como `draft` por ser inviável neste momento e desviar da skill de especificação:
1. **Contradição com a `main`:** A spec exige colocar um aviso "no bloco 'Informações de' (spec 086)". Esse bloco não existe na `main`, pois a spec 086 ainda não foi implementada. Uma spec não pode depender de componentes de UI ou funções inexistentes.
2. **Quebra de autonomia:** A instrução "abre issue bloqueado com o motivo e para" viola a política de execução ponta a ponta do agente desenvolvedor. O plano B deve permitir concluir o PR (ex.: se a B3 falhar, usar a lista antiga, mas seguir com a criação do coletor e tabelas).
3. **Formato do problema:** O problema não foi descrito como uma pergunta do usuário.

## Problema

A lista de ativos do Consultor (`CARTEIRA_IBOVESPA` em `app/consultor/universo.py`) tem papéis que deixaram de existir ou mudaram de código. O `/api/sistema` de produção de 24/10/2026 mostra cinco deles falhando em **duas fontes independentes**: o MetaTrader 5 devolve `HTTP 503: copy_rates_from_pos returned None` e o Yahoo devolve 404 para **NTCO3, SOMA3, JBSS3, MRFG3 e PETZ3**. Todos estão nas linhas 52, 53, 59, 65 e 73 do arquivo.

Efeitos: cada rodada de `consultor_historico` perde pedidos e tempo com esses papéis (a rodada gasta 32 s só nesse coletor); o Consultor avalia e mostra menos ativos do que a carteira real tem; os testes retroativos de regra (`avaliador_historico`, 2 anos) trabalham com uma lista que não existe mais; e o Yahoo e o MT5 aparecem com falha nos painéis de saúde sem um defeito de integração.

O arquivo declara a composição vigente de 02/09/2026 a 30/12/2026 (`COMPOSICAO_INICIO`, `COMPOSICAO_VIGENTE_ATE`), mas a lista não bate com isso. A B3 revisa a carteira a cada quadrimestre, e noticiou entradas e saídas para o ciclo de setembro de 2026, por exemplo a entrada de Tenda e a saída de PetroReconcavo ([DGABC](https://www.dgabc.com.br/Noticia/4341534/b3-2-previa-do-ibovespa-confirma-entrada-de-tenda-e-saida-de-petroreconcavo), [Mercado & Consumo](https://mercadoeconsumo.com.br/17/08/2026/mc-capital/b3-2a-previa-do-ibovespa-confirma-entrada-de-tenda-e-saida-de-petroreconcavo/amp/)). A implementação precisa conferir a lista inteira contra a fonte oficial, e não só trocar os cinco papéis acima.

## Comportamento esperado

- `CARTEIRA_IBOVESPA` passa a ser a composição vigente publicada pela B3 (`FONTE_URL`, a página da carteira teórica, ou o arquivo oficial de composição que ela oferece). Cada ativo da lista tem o ticker exato da B3, com a classe certa (ON, PN, UNIT).
- `COMPOSICAO_CONFERIDA_EM` (constante nova) registra o dia da conferência contra a fonte, e `COMPOSICAO_INICIO` e `COMPOSICAO_VIGENTE_ATE` são os da vigência real. Se o desenvolvimento não alcançar a fonte oficial, ele **não inventa** a lista: deixa a lista como está, abre issue `bloqueado` com o motivo e para.
- **Conferência de cotação.** Um teste de dados (marcado para rodar no CI só com rede, ou com respostas gravadas de cada ativo) confere que todo ticker da lista tem série no banco. Um coletor semanal leve, janela `semanal` do ADR 008, pede uma barra recente de cada ativo ao MT5 e ao Yahoo e grava `carteira_sem_cotacao (ticker, desde, fontes_que_falharam)` para o que falha nas duas.
- Em `/sistema`, novo item no grupo *Coleta*: **Composição do Ibovespa**. *OK* dentro da vigência e com todos os ativos cotados; *Atenção* se algum ativo está sem cotação nas duas fontes (lista no detalhe) ou 7 dias depois do início de um novo quadrimestre sem nova conferência; *Problema* depois de 30 dias nessa situação ou com a vigência vencida.
- O Consultor ignora na tela, e no cálculo, ativos de `carteira_sem_cotacao`, mostrando uma linha "Sem cotação: X, Y. Verifique a composição" no bloco "Informações de" (spec 086), em vez de listá-los como "Sem sinal" para sempre.
- A rotina de manutenção do ciclo (`devagent/skills/manutencao.md`) ganha o item "conferir a carteira do Ibovespa no começo de janeiro, maio e setembro". Essa mudança é do núcleo e vai em PR próprio, como manda o `CICLO.md`; esta spec só a registra como consequência.

## Fontes de dados

B3 (composição da carteira teórica do Ibovespa), MT5 e Yahoo para conferir cotação. Plano B: se a B3 não responde, a lista fica como está e o item de `/sistema` fica em *Atenção* com a data da última conferência.

## Critérios de aceite

- [ ] Nenhum dos cinco tickers NTCO3, SOMA3, JBSS3, MRFG3 e PETZ3 permanece em `CARTEIRA_IBOVESPA`, a menos que a conferência contra a B3 os confirme.
- [ ] A lista não tem duplicatas e todo ticker casa com `^[A-Z]{4}\d{1,2}$`.
- [ ] `COMPOSICAO_CONFERIDA_EM` está dentro da vigência e `COMPOSICAO_VIGENTE_ATE` é posterior a `COMPOSICAO_INICIO`.
- [ ] Com cotações de fixture em que um ativo falha no MT5 e no Yahoo, o coletor grava `carteira_sem_cotacao` e o Consultor o omite do cálculo.
- [ ] `/sistema` mostra o item "Composição do Ibovespa" com os quatro níveis nos casos acima (relógio simulado para as datas).
- [ ] O Consultor mostra a linha "Sem cotação:" só quando há ativos suspensos.
- [ ] A tabela `carteira_sem_cotacao` existe nos dois backends e entra no teste de paridade da spec 084.

## Invariantes de produção

- Nenhum ativo da carteira acusa 404 no Yahoo e falha no MT5 ao mesmo tempo, a não ser que esteja listado em `carteira_sem_cotacao` e no item "Composição do Ibovespa".
- A quantidade de ativos da lista é igual à que a B3 divulga para a carteira vigente; qualquer diferença vira *Atenção* no item "Composição do Ibovespa".

## Fora do escopo

- Reavaliar o histórico de regras com a composição de cada época (viés de sobrevivência fica registrado como ideia no backlog).
- Raspar a B3 automaticamente a cada quadrimestre.
- Tratar o 404 do Yahoo em si (spec 090).
