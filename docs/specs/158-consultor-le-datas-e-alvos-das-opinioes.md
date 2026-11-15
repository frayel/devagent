---
id: 158
titulo: O Consultor lê as datas e os alvos que o coletor grava
status: ready
esforco: P
gaveta: capacidade nova
aceite: tests/test_aceite_158.py
---

## Problema
O usuário perguntou: "por que todo ativo com opinião aparece como 'cobertura insuficiente' no Consultor?"

O defeito foi descrito em 04/11/2026 como spec 140, num ramo que nunca chegou à `main`; o número 140 foi usado depois por outra spec. Conferido de novo em produção em 15/11/2026, no `/api/consultor`:

- 75 ativos têm opinião, mas os 15 resultados com consenso calculado dizem `cobertura insuficiente`.
- `data_materia` das opiniões está no formato do RSS: `"Tue, 03 Nov 2026 16:59:51 +0000"`.
- `informacoes_de` traz `sinais_pregao: "-"`, `sinais_coletado_em: "-"` e `opinioes_materia_mais_recente: "-"`.

A gaveta é *capacidade nova* porque o consenso das casas nunca funcionou em produção. Os quatro defeitos de contrato entre quem grava e quem lê continuam no código:

1. **Data em RFC 822.** `app/collectors/consultor_opinioes.py::parse_feed` grava o `pubDate` cru em `consultor_fila_materias.data_publicacao`, e `extrair_opinioes` copia esse texto para `consultor_opinioes.data_materia`. Em `app/consultor/sintese.py::calcular_consenso`, `datetime.fromisoformat` levanta `ValueError` e a opinião é descartada (`continue`). Nenhuma passa, e todo ativo fica com 0 casas. O mesmo formato quebra a deduplicação de `save_opiniao` (`data_materia LIKE 'Tue, 03 No%'`) e o filtro de 30 dias que compara texto.
2. **Preço-alvo em texto.** `preco_alvo` fica como o Gemini escreveu (`""`, `"R$ 82"`, `"R$ 10,50"`). `calcular_consenso` faz `float(dados["preco_alvo"])`. Hoje esse código não roda por causa do defeito 1; corrigir só a data faz o `ValueError` derrubar o Consultor inteiro.
3. **Chaves que ninguém grava.** `app/consultor/informacoes.py` lê `sinais_pregao` e `sinais_coletado_em`, que `calcular_consultor` não devolve, e `publicada_em` nas opiniões, que têm `data_materia`. Os três campos saem `-`, e o estado dos sinais nunca vira `Defasado`.
4. **Neutro unânime vira "dividido".** `calcular_consenso` conta `neutro`, mas só decide `compra`, `venda` ou `dividido`. Cinco casas neutras saem como `dividido`.

As specs 086, 108b e 109b, em `draft`, pediam as datas na tela. O bloco "Informações de" existe, mas mostra `-` pelos defeitos 1 e 3. Esta spec os resolve.

## Comportamento esperado
- **Data em ISO 8601 UTC na gravação.** Uma função única `armazenamento.ler_data(texto) -> datetime | None` aceita RFC 822 (`email.utils.parsedate_to_datetime`) e ISO, e nunca levanta exceção. `save_materia` grava `data_publicacao` já convertida; se a conversão falhar, usa `criado_em` e registra um aviso. Uma migração idempotente em `init_db` reescreve em ISO as linhas antigas de `consultor_fila_materias.data_publicacao` e `consultor_opinioes.data_materia`. `calcular_consenso` e o filtro de 30 dias usam `ler_data`.
- **Alvo numérico.** A função `armazenamento.ler_preco_alvo(texto) -> float | None` lê `"R$ 1.234,50"`, `"R$ 82"`, `"7,20"` e `"82.5"`, e devolve `None` sem número. `save_opiniao` continua gravando o texto original, que é o que aparece na tela. `calcular_consenso` usa a função, e um alvo ilegível nunca derruba o cálculo.
- **Campos do painel.** `calcular_consultor` devolve `sinais_pregao`, o timestamp da última barra do `^BVSP`, e `sinais_coletado_em`, o maior `coletado_em` das séries, em ISO. `informacoes.py` lê `data_materia` por `ler_data`, no lugar de `publicada_em`.
- **Consenso neutro.** Com pelo menos 2/3 das casas em `neutro`, o consenso é `neutro`. Em `obter_decisao_final`, `neutro` não muda a decisão técnica (como `dividido` hoje), e a frase diz "casas neutras". O template mostra "neutro".

## Fontes de dados
Nenhuma nova.

## Cálculos
A janela de 30 dias e o mínimo de 2 casas não mudam. A mediana dos alvos passa a ser calculada sobre os valores de `ler_preco_alvo`, ignorando `None`.

### Exemplo de ponta a ponta
Data de referência: 04/11/2026. Duas opiniões sobre VALE3:

| Casa | Recomendação | `preco_alvo` | `data_materia` |
|---|---|---|---|
| BTG | neutro | `"R$ 82"` | `"Mon, 02 Nov 2026 10:00:00 +0000"` |
| XP | neutro | `""` | `"2026-11-03T13:00:00+00:00"` |

1. `ler_data` devolve 02/11 10:00 UTC e 03/11 13:00 UTC. As duas estão dentro de 30 dias e são de casas diferentes, então são 2 casas e o mínimo é atingido.
2. `ler_preco_alvo` devolve `82.0` e `None`. A lista de alvos fica `[82.0]`, a mediana é `82.0` e a faixa é `(82.0, 82.0)`.
3. 2 de 2 casas são neutras, 2/2 ≥ 2/3, então o consenso é `neutro`. Antes desta spec, as duas eram descartadas no passo 1 e o ativo saía como `cobertura insuficiente`.

## Critérios de aceite
- [ ] O exemplo acima produz consenso `neutro`, mediana `82.0` e `detalhes.total` 2.
- [ ] `ler_preco_alvo` devolve 82.0, 10.5, 7.2, 1234.5 e `None` para `"R$ 82"`, `"R$ 10,50"`, `"7,20"`, `"R$ 1.234,50"` e `""`.
- [ ] Uma opinião com `preco_alvo` `"alvo não informado"` não gera exceção em `calcular_consultor`.
- [ ] Depois de `init_db`, nenhuma linha de `consultor_opinioes.data_materia` está em RFC 822, e rodar `init_db` de novo não muda nada.
- [ ] `save_opiniao` com a mesma casa, ativo e recomendação no mesmo dia, em horários diferentes e em formatos de data diferentes, grava uma linha só.
- [ ] Com a série do `^BVSP` até 03/11/2026 e uma opinião de 02/11/2026 15h00 UTC, `informacoes_de` traz `sinais_pregao` `"03/11/2026"`, `sinais_coletado_em` diferente de `"-"` e `opinioes_materia_mais_recente` `"02/11/2026 12:00"`.
- [ ] Cinco casas neutras dão `neutro`; três compras e uma venda dão `compra`; duas compras e duas vendas dão `dividido`.
- [ ] `tests/test_aceite_158.py` usa `exigir_spec_done("158")` e não abre rede.
- [ ] Se a spec 156 estiver `done`, o `app/novidades.json` ganha uma entrada `correcao` com `onde` `{"pagina": "/consultor", "painel": "Opiniões recentes"}`.

## Invariantes de produção
- Toda `data_materia` em `/api/consultor` é ISO 8601.
- Com opiniões de 2 ou mais casas em 30 dias, o ativo não aparece como `cobertura insuficiente`.
- `informacoes_de.sinais_pregao` nunca é `-` quando há série do `^BVSP`.

## Fora do escopo
- Mudar o mínimo de 2 casas ou a janela de 30 dias.
- Novas fontes de opinião (spec 157).
