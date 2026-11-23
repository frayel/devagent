---
id: 194
titulo: Os pesos do Ibovespa saem de uma tabela só
status: ready
esforco: P
gaveta: saúde técnica
aceite: tests/test_aceite_194.py
origem: nova
---

## Problema
Quanto o Itaú (ITUB4) pesa no Ibovespa, 7% ou 8%? A página principal dá as duas respostas ao mesmo tempo. Quatro painéis da aba Visão Geral estimam "quantos pontos esta ação deu ao índice" com a mesma fórmula (variação da ação × peso × fechamento anterior do Ibovespa), mas cada coletor tem a sua tabela de pesos escrita à mão, com valores e unidades diferentes:

| Coletor | Constante | Painéis | Unidade | VALE3 | PETR4 | ITUB4 | PETR3 | BBDC4 | B3SA3 | BBAS3 | WEGE3 | ABEV3 | BBDC3 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `app/collectors/concentracao.py:14` | `TICKERS_PESOS` | Concentração de Ganhos, Pressão Vendedora | fração | 0,12 | 0,08 | 0,07 | 0,04 | 0,04 | 0,03 | 0,03 | 0,03 | 0,03 | 0,03 |
| `app/collectors/fator_peso_pesado.py:12` | `TICKERS_PESO` (chave com `.SA`) | Fator Peso Pesado | % | 12 | 8 | 7 | 4 | | | 3 | | | |
| `app/collectors/anomalia_peso.py:14` | `PESOS` | Anomalia de Peso | % | 12 | 8 | **8** | | **4,5** | **4** | | | | |

Medido na `main` de 23/11/2026: ITUB4, BBDC4 e B3SA3 têm pesos diferentes na Anomalia de Peso e na Concentração. Num dia em que ITUB4 sobe 2% com o Ibovespa fechando ontem em 129.000 pontos, a Concentração de Ganhos conta 180,6 pontos para ela e a Anomalia de Peso, na mesma tela, 206,4 (conta em *Cálculos*). Além disso, o texto do painel Fator Peso Pesado (`app/templates/index.html:183`) repete os pesos à mão ("VALE3 12, PETR4 8, ITUB4 7, PETR3 4, BBAS3 3"): uma quarta cópia, que precisa ser editada junto com a tabela e não tem teste.

Atualizar os pesos para a carteira da B3 de hoje é outra pergunta (ver *Fora do escopo*). Esta spec só garante que haja **um** número por ação, numa unidade só, e que a próxima atualização seja uma linha.

Medida de tamanho: `grep -rln "TICKERS_PESOS\|TICKERS_PESO\b\|anomalia_peso.PESOS\|from app.collectors.anomalia_peso"` dá 3 arquivos de código (os três coletores) e 3 de teste (`tests/test_aceite_142.py`, `tests/test_aceite_143.py`, `tests/test_anomalia_peso.py`), mais `app/templates/index.html` e `app/main.py` (o global do Jinja). Nenhum teste existente muda de asserção.

## Comportamento esperado
1. Um módulo novo, `app/collectors/pesos_ibovespa.py`, com uma constante só: `PESOS_IBOVESPA: dict[str, float]`, ticker sem `.SA` → peso **em percentual do índice** (VALE3 = `12.0`), com as 10 ações da tabela acima e os valores da coluna da Concentração (que já são os do texto do Fator Peso Pesado): VALE3 12, PETR4 8, ITUB4 7, PETR3 4, BBDC4 4, B3SA3 3, BBAS3 3, WEGE3 3, ABEV3 3, BBDC3 3. Um comentário no topo diz de onde os pesos vieram e que são aproximados, sem data de conferência (não há uma registrada hoje).
2. Uma função `pesos(tickers: Iterable[str]) -> dict[str, float]` no mesmo módulo devolve o subconjunto pedido, na ordem pedida, e levanta `KeyError` para ticker fora da tabela (painel novo não inventa peso).
3. Os três coletores passam a ler a tabela, e as constantes que os testes importam continuam existindo, derivadas dela, com o mesmo formato de hoje:
   - `concentracao.TICKERS_PESOS = {t: p / 100 for t, p in PESOS_IBOVESPA.items()}` (fração, as mesmas 10 ações e a mesma ordem; o `peso` gravado em `top3_json` e lido pelo `/api/snapshot` continua em fração, `0.12`).
   - `fator_peso_pesado.TICKERS_PESO = {f"{t}.SA": p for t, p in pesos(CINCO_MAIORES).items()}`, com `CINCO_MAIORES = ("VALE3", "PETR4", "ITUB4", "PETR3", "BBAS3")` (percentual; o mesmo dicionário de hoje, soma 34).
   - `anomalia_peso.PESOS = pesos(("VALE3", "PETR4", "ITUB4", "BBDC4", "B3SA3"))` (percentual). É aqui que os números mudam: ITUB4 8 → 7, BBDC4 4,5 → 4, B3SA3 4 → 3.
4. O texto do painel Fator Peso Pesado deixa de repetir os números: `app/main.py` registra um global do Jinja `pesos_fator_peso_pesado` com o texto `"VALE3 12, PETR4 8, ITUB4 7, PETR3 4, BBAS3 3"` e a soma (`34`) montados a partir de `fator_peso_pesado.TICKERS_PESO` (peso sem casa decimal quando inteiro, com vírgula quando não for, ex. `4,5`), e `index.html:183` usa o global. Para quem lê, o texto sai igual ao de hoje.
5. Nada mais muda: as fórmulas de cada coletor, as URLs, o agendamento, o formato do banco e do `/api/snapshot`.

## Fontes de dados
Nenhuma fonte nova. Os pesos continuam constantes no código: a B3 publica a carteira do dia em `sistemaswebb3-listados.b3.com.br`, mas o endereço respondeu à sessão desta spec com a página de bloqueio do Cloudflare (23/11/2026), e coletar pesos é a pergunta de outra spec.

## Cálculos
Sem fórmula nova. A unidade é o ponto em que as três cópias divergem, então cada coletor converte a partir do percentual da tabela:

- Concentração: `pontos = (atual / anterior − 1) × (peso / 100) × ibov_anterior`.
- Fator Peso Pesado: `pts = (var_pct / 100) × (peso / 100) × ibov_anterior`, com `var_pct` em percentual (como hoje).
- Anomalia de Peso: `impacto = var_pct × peso × ibov_anterior / 10000`, com `var_pct` em percentual (como hoje).

Exemplo de ponta a ponta, do Yahoo à tela. O `spark` entrega para `ITUB4.SA` `previousClose = 35.00` e último preço `35.70` (reais por ação); o Ibovespa gravado tem `previous_close = 129000.0` pontos. Peso na tabela: `7.0` (% do índice).

- Variação: `35,70 / 35,00 − 1 = 0,02` (fração), ou `var_pct = 2,0` (percentual).
- Concentração: `0,02 × (7,0 / 100) × 129.000 = 180,6` pontos.
- Fator Peso Pesado: `(2,0 / 100) × (7,0 / 100) × 129.000 = 180,6` pontos.
- Anomalia de Peso hoje: `2,0 × 8,0 × 129.000 / 10.000 = 206,4` → célula `+206,40 pts`. Depois desta spec: `2,0 × 7,0 × 129.000 / 10.000 = 180,6` → `+180,60 pts`, o mesmo número dos outros dois.
- Escala: se alguém puser o peso em fração (`0.07`) na Anomalia, sai `1,806` ponto, 100 vezes menor; o teste do segundo critério pega isso.

## Critérios de aceite
`tests/test_aceite_194.py`, com `exigir_spec_done("194")`, sem internet:

- [ ] `PESOS_IBOVESPA` tem as 10 ações com os valores do item 1 do *Comportamento esperado*, e `pesos(("ITUB4",)) == {"ITUB4": 7.0}`; `pesos(("XPTO3",))` levanta `KeyError`.
- [ ] Anomalia de Peso, com o Ibovespa gravado em `previous_close = 129000.0` e o `fetch_with_retry` trocado por um que devolve, no formato `spark`, ITUB4 de `35.00` para `35.70` e mais nada: `collect_and_save()` grava em `alertas_json` `{"ticker": "ITUB4", "impacto": 180.6}` (tolerância de `1e-6`).
- [ ] Concentração de Ganhos, com o `spark` de ITUB4 `35.00 → 35.70` e `^BVSP` `129000.0 → 130000.0`: a linha de ITUB4 em `top3_json` tem `pontos` igual a `180.6` (tolerância de `1e-6`) e `peso == 0.07`.
- [ ] Para todo ticker presente em mais de uma das três constantes (`concentracao.TICKERS_PESOS` × 100, `fator_peso_pesado.TICKERS_PESO` sem `.SA`, `anomalia_peso.PESOS`), o peso é o mesmo, e é o de `PESOS_IBOVESPA`.
- [ ] Nenhum dos três módulos de coletor tem um literal de peso: o texto (`inspect.getsource`) de cada um não casa com a expressão `"[A-Z]{4}\d{1,2}(\.SA)?"\s*:\s*\d`.
- [ ] A página `/` contém o texto `Pesos aproximados, somando 34%: VALE3 12, PETR4 8, ITUB4 7, PETR3 4, BBAS3 3`, e o `index.html` não contém mais `VALE3 12`.
- [ ] Os testes que já existem passam sem mudança de asserção (`make verify`), em especial `tests/test_aceite_142.py`, `tests/test_aceite_143.py`, `tests/test_anomalia_peso.py`, `tests/test_concentracao.py` e `tests/test_snapshot.py`.

## Invariantes de produção
- Em `/api/snapshot`, os `peso` das linhas de Concentração de Ganhos e de Pressão Vendedora estão entre 0 e 1 (fração) e, para a mesma ação, são iguais nos dois painéis.
- Para a mesma ação, no mesmo snapshot, os pontos da Anomalia de Peso e os da Concentração (de Ganhos ou Pressão Vendedora) diferem no máximo pela diferença de preço entre as duas coletas: com preço da ação e Ibovespa anterior iguais, a razão entre os dois é 1 (antes desta spec, 8/7 para ITUB4).
- O texto do painel Fator Peso Pesado traz pesos que somam o número que ele declara ("somando 34%").

## Fora do escopo
- Atualizar os pesos para a carteira teórica da B3 vigente e dar a eles uma data de conferência que envelhece: entra no item *A composição do Ibovespa também envelhece* do backlog, junto com o selo do `/consultor`.
- Juntar os quatro painéis que respondem "quem moveu o índice" (Concentração de Ganhos, Pressão Vendedora, Fator Peso Pesado e Anomalia de Peso): é decisão da *Rodada de poda* do backlog.
- Baixar as cotações dessas ações uma vez para os três coletores (hoje são oito pedidos ao Yahoo por rodada: dois `spark` de 10 ações, um de 5 e cinco `chart`): item *Medir quanto de série a rodada baixa repetido*.
- Os pesos da Maré (`app/services/mare.py`, `PESOS`): são pesos de componentes de um indicador, não de ações no índice.
