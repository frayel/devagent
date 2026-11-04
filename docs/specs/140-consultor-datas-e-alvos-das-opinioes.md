---
id: 140
titulo: Consultor lê as datas e os alvos que o coletor grava
status: ready
esforco: P
gaveta: saúde técnica
aceite: tests/test_aceite_140.py
---

## Problema
Observado em produção (`/api/consultor`, 04/11/2026 12h14 BRT): os 69 ativos com consenso calculado aparecem todos como `cobertura insuficiente` (os outros 13 são `Sem sinal` sem histórico), e o painel "Informações de" mostra `Pregão: -`, `Coleta: -` e `Matéria mais recente: -`. Na mesma resposta, `fontes_opiniao.llm` informa 63 matérias processadas e 43 opiniões gravadas, e 26 ativos têm opinião. São quatro defeitos de contrato entre quem grava e quem lê:

1. **Data da opinião em formato RFC 822.** O coletor grava `consultor_fila_materias.data_publicacao` com o `pubDate` cru do RSS (`Sat, 31 Oct 2026 14:52:23 +0000`), e `extrair_opinioes` copia esse valor para `consultor_opinioes.data_materia`. `sintese.calcular_consenso` faz `datetime.fromisoformat` nessa data, recebe `ValueError` e descarta a opinião (`continue`). Nenhuma das 43 opiniões passa; todo ativo fica com 0 casas e cai em `cobertura insuficiente`. O mesmo formato quebra a deduplicação de `save_opiniao` (`data_materia LIKE 'Sat, 31 Oc%'`) e o filtro de 30 dias de `get_opinioes_historicas`, que compara texto.
2. **Preço-alvo em texto.** `preco_alvo` fica gravado como o LLM escreveu (`"R$ 82"`, `"R$ 10,50"`, `"7,20"`). `calcular_consenso` faz `float(preco_alvo)`. Hoje esse código nunca roda, por causa do defeito 1. Corrigir só a data faz o `ValueError` estourar e derrubar o consultor inteiro.
3. **Chaves que ninguém grava.** `informacoes.construir_informacoes_de` lê `sinais_pregao` e `sinais_coletado_em`, que `calcular_consultor` nunca devolve, e procura `publicada_em` nas opiniões, que têm `data_materia`. Os três campos saem sempre `-`, e o estado dos sinais nunca vira `Defasado`.
4. **Neutro unânime vira "dividido".** `calcular_consenso` só conhece `compra`, `venda` e `dividido`. VALE3 e ITUB4 têm 5 casas, todas neutras, e apareceriam como `dividido`.

Simulação com as 43 opiniões de produção, datas convertidas e alvos lidos: 9 ativos saem da cobertura insuficiente (PRIO3, USIM5, VALE3, BBDC4, CMIG4, ENEV3, ITUB4, SUZB3, TIMS3). Os outros 17 com opinião têm uma casa só e continuam corretamente em `cobertura insuficiente` (exige 2 casas em 30 dias).

## Comportamento esperado
- **Datas em ISO 8601 UTC na gravação.** `save_materia` converte `data_publicacao` com `email.utils.parsedate_to_datetime` (aceita também ISO); se nenhuma forma funcionar, usa `criado_em` e registra aviso. Uma migração idempotente em `init_db` reescreve as linhas antigas de `consultor_fila_materias.data_publicacao` e `consultor_opinioes.data_materia` que estão em RFC 822. A leitura em `calcular_consenso` usa a mesma função de conversão (`armazenamento.ler_data`), que nunca lança exceção.
- **Alvo numérico.** Função única `armazenamento.ler_preco_alvo(texto) -> float | None` lê `"R$ 1.234,50"`, `"R$ 82"`, `"7,20"` e `"82.5"`; devolve `None` se não houver número. `save_opiniao` grava o texto original (é o que aparece na tela) e `calcular_consenso` usa a função. Um alvo ilegível nunca derruba o cálculo.
- **Campos do painel.** `calcular_consultor` devolve `sinais_pregao` (timestamp da última barra do `^BVSP`, o `ibov_ts[-1]` que já calcula) e `sinais_coletado_em` (o `max_criado` de `versao_series`, em ISO). `construir_informacoes_de` lê `data_materia` em vez de `publicada_em`, pela mesma `ler_data`.
- **Consenso neutro.** Com pelo menos 2/3 das casas em `neutro`, o consenso é `neutro`. Em `obter_decisao_final`, `neutro` não muda a decisão técnica (como `dividido` hoje) e a frase passa a ser "casas neutras" em Comprar e Vender. O template mostra "neutro".

## Fontes de dados
Nenhuma nova.

## Cálculos
- Janela de 30 dias e mínimo de 2 casas: sem mudança.
- Mediana dos alvos: sem mudança, agora sobre os valores lidos por `ler_preco_alvo`.

## Critérios de aceite
- [ ] Duas opiniões de casas diferentes para o mesmo ativo, com `data_materia` `"Mon, 02 Nov 2026 10:00:00 +0000"` e data de referência 04/11/2026, produzem consenso diferente de `cobertura insuficiente`.
- [ ] `ler_preco_alvo` devolve 82.0, 10.5, 7.2, 1234.5 e None para `"R$ 82"`, `"R$ 10,50"`, `"7,20"`, `"R$ 1.234,50"` e `""`.
- [ ] Opinião com `preco_alvo` `"alvo não informado"` não gera exceção em `calcular_consultor`.
- [ ] Depois de `init_db`, nenhuma linha de `consultor_opinioes.data_materia` está em RFC 822; rodar `init_db` de novo não muda nada.
- [ ] `save_opiniao` com a mesma casa, ativo e recomendação no mesmo dia, em horários diferentes, grava uma linha só.
- [ ] Com série do `^BVSP` até 03/11/2026 e opinião de 02/11/2026 15h00 UTC, `informacoes_de` traz `sinais_pregao` `"03/11/2026"`, `sinais_coletado_em` diferente de `"-"` e `opinioes_materia_mais_recente` `"02/11/2026 12:00"`.
- [ ] Cinco casas neutras dão consenso `neutro`; três compras e uma venda dão `compra`; duas compras e duas vendas dão `dividido`.
- [ ] Os testes existentes do consultor continuam verdes.
- Arquivos tocados: `app/consultor/armazenamento.py`, `app/consultor/sintese.py`, `app/consultor/calculador.py`, `app/consultor/informacoes.py`, `app/services/consultor_opinioes.py`, `app/templates/consultor.html` (rótulo `neutro`) e o novo `tests/test_aceite_140.py`.

## Invariantes de produção
- `/api/consultor` responde 200 e com `ativos_avaliados` maior que zero, com e sem opiniões no banco.
- Depois do deploy, com as opiniões já gravadas, ao menos um ativo deixa de aparecer como `cobertura insuficiente`.

## Fora do escopo
- O formato do campo `consenso` em `consultor_recomendacoes` (spec 132).
- Novas fontes de opinião (specs 141 e 142).
- A casa extraída igual à própria empresa (ex.: "Itaú Unibanco" opinando sobre ITUB4): anotado para o backlog.
