---
id: 190
titulo: Cada opinião com preço-alvo diz se o alvo já foi atingido ou quanto falta
status: ready
esforco: M
gaveta: capacidade nova
aceite: tests/test_aceite_190.py
revisada: 2026-11-21
origem: O placar mede o alvo que a casa declarou
---

## Problema
A casa que deu este preço-alvo já acertou, ou quanto ainda falta?

Desde a spec 158 o Consultor guarda o preço-alvo e a data de cada opinião (`consultor_opinioes.preco_alvo` e `data_materia`), e desde a 165 a lista **Opiniões Recentes** de `/consultor` mostra cada opinião no detalhe recolhido do ativo. Mas o alvo aparece solto: a pessoa vê "BTG Pactual · compra · R$ 45,00 · 11/11" e não sabe se a ação já passou de 45 desde então, nem a que distância está. Para saber, abre outro site e faz a conta de cabeça, para cada opinião.

O item da *Fila* que originou esta spec dizia que "o placar da 072b dá acerto por casa". Isso não vale mais: o placar da 072b nunca chegou à tela e o módulo foi removido como código sem uso no #993 (19/11); de `app/consultor/placar.py` restou só `_calcular_excesso`. Esta spec é a primeira fatia do que o placar deveria responder, ancorada no dado que existe hoje: o alvo de cada opinião contra os fechamentos que o próprio Consultor guarda.

## Comportamento esperado
- **Na tabela do detalhe de cada ativo** (o `<details class="opiniao-ativo">` da lista *Opiniões Recentes*, `app/templates/consultor.html`), uma coluna nova **Até o alvo**, logo depois de **Preço-Alvo**. Para cada opinião:
  - alvo atingido: `atingido em 16/11 · R$ 45,20` (o dia do primeiro fechamento que chegou ao alvo, `dd/mm`, e esse fechamento com vírgula decimal);
  - alvo ainda não atingido: `faltam +13,4% · fech. 19/11` (a distância do último fechamento guardado até o alvo, com sinal, uma casa decimal e vírgula; e o dia desse fechamento);
  - sem alvo legível, sem data legível ou sem fechamento de referência (veja *Cálculos*): `-`.
  - A célula tem um `title` com o método da linha: `Alvo R$ 45,00 · antes da matéria: R$ 40,00 em 10/11 (alta)`, para a pessoa conferir o sentido usado.
- **Uma linha de método**, uma vez só, logo abaixo da lista (antes do rodapé "Última extração: ..."), num `<p class="fonte-dado">`, só quando a lista tem linhas, escrita literalmente no template (não por variável: o autoescape trocaria as aspas por `&#34;` e o teste de texto exato falharia): `Até o alvo: compara o preço-alvo com os fechamentos guardados pelo Consultor desde o dia da matéria. "Atingido" é o primeiro fechamento que chegou ao alvo, no sentido do fechamento anterior à matéria.`
- Nenhuma classe CSS nova (o `tests/test_classes_com_estilo.py` reprova classe sem estilo): a célula usa `class="n"`, que já existe (`th.n, td.n` em `app/static/tema.css`), e o texto sai sem cor nem seta. "Faltam +13,4%" não é alta nem queda do papel; cor de alta e baixa aqui confundiria (convenção da seção 7 do `PRODUTO.md`).
- **Pregão passado.** Em `/consultor?data=AAAA-MM-DD` e `/api/consultor?data=...`, a coluna usa só os fechamentos com `data_pregao` até a data pedida, inclusive: a página mostra o que se sabia naquele dia.
- **JSON.** Em `/api/consultor`, cada opinião dentro de `opinioes_por_ativo[].opinioes[]` ganha a chave `alvo_situacao`: `null`, ou o dicionário de *Cálculos*. Nenhuma outra chave muda; `opinioes_recentes` não ganha a chave.
- **Novidades.** Entrada nova em `app/novidades.json` (o `tests/test_aceite_156.py` exige para spec entregue com tela), com `"onde": {"pagina": "/consultor", "pagina_nome": "Consultor", "painel": "Opiniões recentes"}` e `"spec": "190"`.

## Fontes de dados
Nenhuma nova e nenhum pedido externo a mais.

- **Opiniões:** `consultor_opinioes`, como hoje (as mesmas que `agrupar_por_ativo` já recebe).
- **Fechamentos:** `consultor_fechamentos` (`data_pregao`, `ticker`, `preco_fechamento`), que o coletor `consultor_fechamento` grava depois das 18h BRT para cada ativo da carteira (`app/collectors/consultor_fechamento.py`, `save_fechamentos`). É a mesma tabela que o "resultado depois do fato" dos pregões passados lê (specs 113b e 131).
- **Leitura nova** em `app/consultor/armazenamento.py`, no molde das outras leituras do módulo (`init_db`, `get_connection`, `sql_para`, conexão fechada no `finally`):
  ```python
  def get_fechamentos(tickers: list[str], ate: str | None = None) -> dict[str, list[tuple[str, float]]]:
      """Ticker -> [(data_pregao 'AAAA-MM-DD', fechamento)], em ordem crescente de data; com `ate`, só data_pregao <= ate."""
  ```
  Uma consulta só (`WHERE ticker IN (...)`), não uma por ticker. Lista de tickers vazia devolve `{}` sem consultar.
- **Plano B.** Tabela vazia, ticker fora da carteira ou erro de leitura: as opiniões saem com `alvo_situacao = None`, a coluna mostra `-` e o resto da lista não muda. O erro de leitura é registrado no log e não derruba a página (os chamadores envolvem a leitura em `try/except` e seguem com `{}`).

## Cálculos
Nova função pura em `app/consultor/sintese.py`:

```python
def situacao_do_alvo(opiniao: dict, fechamentos: list[tuple[str, float]]) -> dict | None:
```

`fechamentos` é a lista do ticker da opinião, crescente por data.

1. `alvo = ler_preco_alvo(opiniao.get("preco_alvo"))`; `None` ou `<= 0` → devolve `None`.
2. `dia = ` o dia de `ler_data(opiniao.get("data_materia"))` **no fuso de Brasília** (`app.services.carimbo.FUSO`), como `AAAA-MM-DD`; data ilegível → `None`. Uma matéria às 01h00 UTC de 12/11 é do dia 11/11.
3. **Base:** o último fechamento com `data_pregao < dia` (o preço que a casa via ao publicar). Sem base → `None`. Não há outro caminho para decidir o sentido do alvo, e o conservador é não afirmar nada.
4. **Sentido:** `alta` se `alvo > base`, `baixa` se `alvo < base`; `alvo == base` → devolve `None` (a casa não apontou direção, e qualquer sentido violaria as invariantes no caso sem fechamento depois da matéria). O sentido vem do preço, não da recomendação: uma casa "neutra" com alvo acima do preço também espera alta, e uma "venda" com alvo acima do preço existe (alvo acima, mas abaixo do potencial de outras ações).
5. **Depois da matéria:** os fechamentos com `data_pregao >= dia`. O pregão do próprio dia conta: a maioria das matérias sai antes ou durante o pregão.
6. **Atingido:** o primeiro fechamento de *depois* com `preco >= alvo` (alta) ou `preco <= alvo` (baixa). Devolve:
   `{"estado": "atingido", "sentido", "alvo", "base_data", "base_preco", "data", "preco"}` (`data` e `preco` do fechamento que atingiu).
7. **Falta:** sem fechamento que atingiu, o último fechamento da lista inteira (que é o de *depois* mais recente ou, sem nenhum depois, a própria base). Devolve:
   `{"estado": "falta", "sentido", "alvo", "base_data", "base_preco", "data", "preco", "distancia"}`, com `distancia = alvo / preco − 1` (fração, não percentual).

Uma vez atingido, fica atingido, mesmo que o preço volte: a pergunta é "a casa acertou o alvo", não "o preço está no alvo hoje". Só fechamentos contam (não máxima nem mínima do dia): é o dado que o Consultor guarda, e o `title` diz que é fechamento.

**Onde entra.** `agrupar_por_ativo(opinioes, referencia=None, fechamentos=None)` ganha o parâmetro `fechamentos: dict[str, list[tuple[str, float]]] | None`. Cada opinião de `linha["opinioes"]` passa a ser uma **cópia** do dicionário de entrada com a chave `alvo_situacao = situacao_do_alvo(op, (fechamentos or {}).get(ticker, []))`. Contagem, ordem, alvos, cobertura e o resto da linha não mudam (`tests/test_aceite_165.py` continua verde sem mudar expectativa).

Os três chamadores passam os fechamentos dos tickers que têm opinião:
- `calcular_consultor` (`app/consultor/calculador.py`): `get_fechamentos(tickers)`, sem `ate`;
- os dois ramos históricos de `app/main.py` (`/consultor` e `/api/consultor` com data): `get_fechamentos(tickers, ate=target_data)`.

**Formatos na tela** (filtros Jinja novos em `app/main.py`, ao lado de `dia_brasilia`, ou montados num único filtro `ate_o_alvo` que devolve o texto da célula):
- preço: `f"{preco:.2f}".replace(".", ",")` → `45,20`;
- distância: `f"{distancia * 100:+.1f}".replace(".", ",") + "%"` → `+13,4%`, `-4,8%`;
- dia: `AAAA-MM-DD` → `dd/mm`.

### Exemplo
Fechamentos guardados (todos dias de pregão; 15/11 é domingo e 20/11 é feriado):

| data_pregao | PETR4 | VALE3 |
|---|---|---|
| 2026-11-10 | 40,00 | - |
| 2026-11-11 | 41,00 | 60,00 |
| 2026-11-12 | 42,50 | 58,00 |
| 2026-11-13 | 44,00 | 55,00 |
| 2026-11-16 | 45,20 | 53,10 |
| 2026-11-17 | 44,80 | 51,90 |
| 2026-11-18 | 43,90 | 52,40 |
| 2026-11-19 | 44,10 | 52,80 |

| Op. | casa | ticker | rec. | preco_alvo | data_materia | Base | Sentido | Até o alvo |
|---|---|---|---|---|---|---|---|---|
| a | BTG Pactual | PETR4 | compra | `"R$ 45,00"` | `2026-11-12T01:00:00+00:00` (11/11 22h BRT) | 10/11 · 40,00 | alta | `atingido em 16/11 · R$ 45,20` |
| b | XP | PETR4 | compra | `50.0` | `2026-11-17T12:00:00+00:00` | 16/11 · 45,20 | alta | `faltam +13,4% · fech. 19/11` (50 / 44,10 − 1 = 0,13379) |
| c | Ágora | PETR4 | venda | `42` | `2026-11-19T20:00:00+00:00` (19/11 17h BRT) | 18/11 · 43,90 | baixa | `faltam -4,8% · fech. 19/11` (42 / 44,10 − 1 = −0,04762) |
| d | Itaú BBA | PETR4 | neutro | `None` | `2026-11-18T12:00:00+00:00` | - | - | `-` |
| e | Safra | VALE3 | venda | `"52,00"` | `2026-11-12T15:00:00+00:00` | 11/11 · 60,00 | baixa | `atingido em 17/11 · R$ 51,90` (o 18/11 a 52,40 não desfaz) |
| f | Genial | ITUB4 | compra | `40` | `2026-11-18T12:00:00+00:00` | sem fechamento de ITUB4 | - | `-` |
| g | Safra | PETR4 | compra | `48` | `2026-11-10T13:00:00+00:00` | nenhum fechamento antes de 10/11 | - | `-` |

Na opinião **a**, o dia é 11/11 (não 12/11) porque 01h00 UTC são 22h00 de Brasília; a base é então o fechamento de 10/11, não o de 11/11.

Na mesma tabela com `ate="2026-11-13"` (página de 13/11): **a** fica `faltam +2,3% · fech. 13/11` (45 / 44 − 1 = 0,02273); **e** fica `faltam -5,5% · fech. 13/11` (52 / 55 − 1 = −0,05455). O critério de aceite só confere **a** e **e** com o corte; quais opiniões a página histórica lista continua sendo regra da spec 165.

## Critérios de aceite
- [ ] `tests/test_aceite_190.py`, com `exigir_spec_done("190")`, sem rede:
  - `situacao_do_alvo` com cada opinião de a a g e a lista de fechamentos do ticker dela (tabela do exemplo) devolve o `estado`, o `sentido`, a `data`, o `preco` e a `distancia` (com `pytest.approx`, 4 casas) da tabela; d, f e g devolvem `None`; uma opinião extra com alvo igual ao fechamento-base (PETR4, alvo `44,10`, matéria em 20/11 12:00 UTC, base 19/11 · 44,10) também devolve `None`.
  - Com os fechamentos cortados em `2026-11-13`, **a** e **e** saem `falta`, com `distancia` 0,02273 e −0,05455.
  - `get_fechamentos(["PETR4", "VALE3", "ITUB4"])`, depois de gravar as linhas do exemplo em `consultor_fechamentos` (banco de teste, por `INSERT` direto: `save_fechamentos` grava só a data de hoje e só depois das 18h BRT, então não serve para semear datas passadas), devolve as duas listas em ordem crescente e nenhuma chave `ITUB4`; com `ate="2026-11-13"`, a última data de PETR4 é `2026-11-13`; com `[]`, devolve `{}`.
  - `agrupar_por_ativo` com as opiniões a, b, c, d, a referência 21/11/2026 12:00 UTC e os fechamentos do exemplo: cada item de `linha["opinioes"]` tem `alvo_situacao`, e os dicionários de entrada não ganharam a chave (cópia, não mutação). Sem `fechamentos`, toda `alvo_situacao` é `None`.
  - Com as opiniões a, b e c gravadas por `save_opiniao`, os fechamentos do exemplo gravados e `calcular_consultor` trocado por uma função que devolve o dicionário mínimo com `opinioes_por_ativo` calculado delas e dos fechamentos (mesmo molde de `tests/test_aceite_165.py`), o HTML de `GET /consultor` contém `atingido em 16/11 · R$ 45,20`, `faltam +13,4% · fech. 19/11`, `faltam -4,8% · fech. 19/11`, o cabeçalho `Até o alvo` e a linha de método exatamente uma vez.
  - Sem opiniões (lista vazia), o HTML não contém a linha de método.
- [ ] `tests/test_aceite_165.py`, `tests/test_consultor_sintese.py`, `tests/test_aceite_158.py` e `tests/test_correcao_885.py` continuam verdes sem mudar expectativa.
- [ ] `tests/test_classes_com_estilo.py` e `tests/test_templates_safe.py` continuam verdes (nenhuma classe nova; nenhum `| safe` novo).
- [ ] `make telas` sem `PROBLEMA:` novo em `/consultor` nas quatro larguras: a tabela do detalhe, uma coluna mais larga, continua rolando dentro da própria `.tabela-responsiva`.

## Invariantes de produção
Verificáveis em `/api/consultor` (sem data e com `?data=`), sem ler o código:
- Toda opinião com `alvo_situacao` não nulo tem `base_data` anterior ao dia (Brasília) da `data_materia`, e `data` maior ou igual a `base_data`.
- `estado == "atingido"` implica `preco >= alvo` quando `sentido == "alta"` e `preco <= alvo` quando `sentido == "baixa"`.
- `estado == "falta"` implica `distancia == alvo / preco − 1` (com 4 casas) e o alvo ainda não alcançado: `preco < alvo` na alta, `preco > alvo` na baixa.
- Com `?data=AAAA-MM-DD`, nenhuma `data` nem `base_data` passa da data pedida.
- Toda opinião sem preço-alvo tem `alvo_situacao` nulo.

## Fora do escopo
- O placar por casa (quantas opiniões de cada casa chegaram ao alvo, com amostra e janela): é o resto do item *O placar mede o alvo que a casa declarou* da *Fila* do backlog. Precisa de opiniões além dos 30 dias da lista e de um número mínimo por casa.
- O prazo do alvo: `consultor_opinioes` não guarda prazo, e o Gemini não o extrai hoje. Esta spec não diz "dentro do prazo".
- Máxima e mínima do dia: só fechamentos guardados.
- Gravar `^BVSP` em `consultor_fechamentos` (issue #1005, um bug do resultado depois do fato): esta spec não depende do Ibovespa.
- Mudar o formato `R$ 45.00` do resumo (`<summary>`) do ativo, ou a coluna **Preço-Alvo** crua do detalhe: item próprio na *Fila*.
- Mostrar a situação do alvo no card do ativo, no consenso ou no Yahoo (spec 159).
- Semear opiniões com alvo e fechamentos em `scripts/telas.py`: as opiniões de demonstração da 165 já exercitam a tabela; a coluna nova sai `-` nelas.
