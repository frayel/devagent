---
id: 165
titulo: Opiniões Recentes com uma linha por ativo, e as opiniões dele recolhidas na linha
status: ready
esforco: M
gaveta: experiência
aceite: tests/test_aceite_165.py
origem: issue #908
revisada: 2026-11-16
---

## Problema
O que as casas dizem, hoje, de cada ativo do Ibovespa, e elas concordam entre si?

Pedido do dono do produto na issue [#908](https://github.com/frayel/devagent/issues/908). A tabela **Opiniões Recentes** de `/consultor` tem uma linha por opinião extraída: `get_opinioes_recentes` (`app/consultor/armazenamento.py`) devolve as 20 últimas linhas de `consultor_opinioes` por `extraida_em`, sem agrupar, e o `consultor.html` desenha uma `<tr>` por linha. Daí três problemas:

- um ativo comentado por três casas, ou a mesma recomendação noticiada por duas fontes (Money Times e Telegram), ocupa várias linhas, e a pessoa junta as linhas de cabeça;
- com o teto de 20, um ativo muito citado empurra os outros para fora da tabela;
- não dá para ver de relance se as casas concordam, e a tabela pode contar diferente do consenso que o Consultor usa na decisão (`calcular_consenso`, `app/consultor/sintese.py`: janela de 30 dias pela `data_materia`, só a opinião mais recente de cada casa, mínimo de 2 casas).

## Comportamento esperado
- **A mesma regra nos dois lugares.** Em `app/consultor/sintese.py`, o laço de `calcular_consenso` que escolhe a opinião mais recente de cada casa dentro de 30 dias vira uma função pública, usada por `calcular_consenso` e pela tabela:
  ```python
  def ultima_por_casa(opinioes: list[dict], referencia: datetime | None = None) -> dict[str, dict]:
      """Casa -> a opinião mais recente dela, com `data_materia` nos 30 dias até `referencia`."""
  ```
  Devolve a opinião inteira (o dicionário que entrou), não só recomendação e alvo. A janela é a de hoje: `data_materia >= referencia − 30 dias`, **sem teto superior** (o `calcular_consenso` atual não descarta data posterior à referência, e acrescentar o teto mudaria o resultado dele). Opinião com `data_materia` ilegível (`ler_data` devolve `None`) fica de fora, como hoje. `calcular_consenso` passa a chamá-la e não muda de resultado: `tests/test_consultor_sintese.py` e `tests/test_aceite_158.py` continuam verdes sem mudar expectativa.
- **O agrupamento.** Nova função pura em `app/consultor/sintese.py`:
  ```python
  def agrupar_por_ativo(opinioes: list[dict], referencia: datetime | None = None) -> list[dict]:
  ```
  Para cada `ticker` com ao menos uma opinião em `ultima_por_casa`, uma linha com:
  - `ticker`;
  - `contagem`: `{"compra": n, "neutro": n, "venda": n}` sobre as opiniões de `ultima_por_casa` (uma por casa), com a mesma leitura de `calcular_consenso` (`compra`, `venda`; o resto é `neutro`);
  - `opinioes_texto`: as contagens diferentes de zero, na ordem Comprar, Neutro, Vender, separadas por ` · ` (`"3 Comprar · 1 Neutro"`, `"1 Vender"`);
  - `cobertura_insuficiente`: `True` quando `calcular_consenso(opinioes_do_ticker, referencia)["consenso"] == "cobertura insuficiente"`. A tabela pergunta ao próprio `calcular_consenso`, não refaz a conta do mínimo de 2 casas;
  - `alvo_min`, `alvo_max`: o menor e o maior `ler_preco_alvo` entre as opiniões de `ultima_por_casa`, ou `None` sem alvo legível;
  - `mais_recente_data` (a `datetime` em UTC) e `mais_recente_casa`: a opinião de maior `data_materia` entre as de `ultima_por_casa`;
  - `opinioes`: todas as opiniões do ticker com `data_materia` nos mesmos 30 dias (a mesma janela de `ultima_por_casa`, inclusive as repetidas de uma casa e as da mesma recomendação por duas fontes), da mais recente para a mais antiga por `data_materia`. É o detalhe: nenhuma opinião que a tabela mostra hoje dentro da janela some, só fica recolhida.

  As linhas saem ordenadas por `mais_recente_data` decrescente; empate, por `ticker` crescente.
- **De onde vêm as opiniões.**
  - `calcular_consultor` (`app/consultor/calculador.py`) já lê `opinioes_ativos = get_opinioes_ativos()` (30 dias por `extraida_em`). O dicionário de resultado ganha `"opinioes_por_ativo": agrupar_por_ativo([op for ops in opinioes_ativos.values() for op in ops], referencia=agora)`, com `agora = datetime.now(timezone.utc)` lido uma vez e passado também a cada `calcular_consenso(opinioes_ticker, agora)` do laço, para a lista e os cards usarem o mesmo instante de referência. O ramo antecipado (sem `^BVSP`) ganha `"opinioes_por_ativo": []`.
  - Os dois ramos históricos de `app/main.py` (o de `/consultor` com data e o de `/api/consultor` com data, onde já se monta `"opinioes_recentes": get_opinioes_historicas(...)`) ganham `"opinioes_por_ativo": agrupar_por_ativo(<as mesmas opiniões>, referencia=<o dia pedido às 23:59:59 UTC>)`.
  - `opinioes_recentes` não muda nem sai: continua alimentando `has_opinions`, o bloco "Informações de" (`app/consultor/informacoes.py`), a chave de cache e o JSON de `/api/consultor`.
- **A tela** (`app/templates/consultor.html`, bloco "Opiniões Recentes"). A tabela de 8 colunas dá lugar a uma lista de `<details class="opiniao-ativo">`, uma por linha de `opinioes_por_ativo`, sem JavaScript:
  - o `<summary>` traz, nesta ordem e com estes rótulos visíveis em telas largas: **Ticker** em negrito; **Opiniões** com `opinioes_texto`, seguido de ` · cobertura insuficiente` quando `cobertura_insuficiente`; **Preço-alvo** como `R$ 38.00 a R$ 45.00` com dois alvos diferentes, `R$ 52.00` com um só (ou mínimo igual ao máximo), `-` sem alvo (mesmo formato `"%.2f"` do resto da página); **Mais recente** como `14/11 · BTG Pactual`, com o dia no fuso de Brasília (`America/Sao_Paulo`), não em UTC;
  - aberto, mostra dentro de `.tabela-responsiva` a tabela das opiniões individuais do ativo com as colunas de hoje menos o Ticker: Casa, Recomendação, Preço-Alvo, Resumo, Data, Via (`origem_opiniao`) e Link ("Ler", `target="_blank"`);
  - começa fechado.
  - Sem linhas, as mesmas mensagens de diagnóstico de hoje (`sem_chave`, `cota`, `erro`, `aguardando`, `fila`, `sem_materias`, `descartadas` e o padrão "Nenhuma opinião nos últimos 30 dias."), agora num `<p>` em vez de `<tr><td colspan="8">`. A condição passa a ser `not dados.opinioes_por_ativo`.
  - O rodapé "Última extração: ..." não muda.
- **Celular.** Em 360 px a página continua sem rolar para o lado (regra do `PRODUTO.md` e issue #885): o `<summary>` quebra linha entre os quatro campos em vez de alargar a página; a tabela do detalhe rola dentro da própria `.tabela-responsiva`, como as outras tabelas da página. Para o teste da #885 medir a lista com conteúdo, `_semear` de `scripts/telas.py` grava, com `save_opiniao` (`app/services/consultor_opinioes.py`), quatro opiniões de demonstração com `data_materia` de 1 a 3 dias atrás: PETR4 por duas casas (uma com alvo) e VALE3 por uma casa.

## Fontes de dados
Nenhuma nova: só a tabela `consultor_opinioes`, já preenchida pelo laço das opiniões (spec 164). Nenhum pedido externo a mais. Se a extração estiver parada, a lista fica vazia e aparece o diagnóstico de hoje; o resto da página não muda.

## Cálculos
Janela, deduplicação e mínimo de casas são os do `calcular_consenso`, pela função compartilhada `ultima_por_casa`: opiniões com `data_materia >= referencia − 30 dias` (sem teto superior, como hoje), uma por casa (a de maior `data_materia`), e "cobertura insuficiente" com menos de 2 casas. A contagem da linha é a mesma que decide o consenso do ativo, então a tabela e o card do ativo nunca discordam.

Exemplo (referência 16/11/2026 12:00 UTC). O `preco_alvo` chega do banco como a coluna o guarda (número em reais, `45.0`, ou texto antigo do Gemini, `"R$ 45,00"`, `"52,00"`); `ler_preco_alvo` devolve sempre reais em `float` (`"R$ 45,00"` → `45.0`, `"38"` → `38.0`, `"52,00"` → `52.0`), e a tela escreve `"R$ %.2f"` → `R$ 45.00`. Não há escala (milhar, centavos ou percentual) em nenhum passo.

| Opinião | casa | ticker | rec. | alvo | data_materia |
|---|---|---|---|---|---|
| a | BTG Pactual | PETR4 | compra | R$ 45,00 | 14/11 13:00 UTC |
| b | BTG Pactual | PETR4 | neutro | - | 01/11 |
| c | XP | PETR4 | compra | 38 | 10/11 |
| d | Itaú BBA | PETR4 | compra | - | 12/11 10:00 UTC (Telegram) |
| e | Itaú BBA | PETR4 | compra | - | 12/11 14:00 UTC (Money Times) |
| f | Safra | VALE3 | venda | 52,00 | 12/11 |
| g | Genial | ITUB4 | compra | 40 | 10/10 (fora da janela) |

- PETR4: `ultima_por_casa` = {BTG: a, XP: c, Itaú BBA: e}; `opinioes_texto` = `3 Comprar`; alvo `R$ 38.00 a R$ 45.00`; mais recente `14/11 · BTG Pactual`; `cobertura_insuficiente` = False; o detalhe tem a, e, d, c, b (5 opiniões).
- VALE3: `opinioes_texto` = `1 Vender`, `cobertura_insuficiente` = True, e o `<summary>` mostra `1 Vender · cobertura insuficiente`; alvo `R$ 52.00`; mais recente `12/11 · Safra`.
- ITUB4 não aparece.
- Ordem: PETR4, VALE3.

Uma opinião às 01h00 UTC de 15/11 aparece como `14/11` (22h00 de Brasília).

## Critérios de aceite
- [ ] `tests/test_aceite_165.py`, com `exigir_spec_done("165")`, sem rede:
  - `agrupar_por_ativo` com as opiniões a a g da tabela acima e a referência 16/11/2026 12:00 UTC devolve duas linhas, PETR4 e VALE3, nessa ordem, com os valores do exemplo (`contagem`, `opinioes_texto`, `cobertura_insuficiente`, `alvo_min`, `alvo_max`, `mais_recente_casa`, e 5 e 1 itens em `opinioes`).
  - Para cada ticker da tabela, `sum(linha["contagem"].values())` é igual ao `detalhes["total"]` de `calcular_consenso` quando ele não é "cobertura insuficiente".
  - `ultima_por_casa` com as opiniões de PETR4 devolve 3 casas e, para BTG Pactual, a opinião a.
  - Com três opiniões gravadas por `save_opiniao` (PETR4 por duas casas, VALE3 por uma, `data_materia` de ontem) e `calcular_consultor` trocado por uma função que devolve o dicionário mínimo com `opinioes_por_ativo` calculado delas (mesmo molde de troca de `tests/test_consultor.py`), o HTML de `GET /consultor` tem exatamente dois `<details class="opiniao-ativo">`, contém `2 Comprar` e `1 Vender · cobertura insuficiente`, e cada link "Ler" das três opiniões aparece uma vez.
  - Sem opiniões e com o diagnóstico `sem_materias`, o HTML contém a mensagem de hoje e nenhum `<details class="opiniao-ativo">`.
  - Uma opinião com `data_materia` `2026-11-15T01:00:00+00:00` aparece no `<summary>` como `14/11`, não `15/11`.
- [ ] `tests/test_correcao_885.py` continua verde, agora com as opiniões de demonstração de `_semear` (360, 390, 768 e 1440 px).
- [ ] `tests/test_consultor_sintese.py`, `tests/test_aceite_158.py` e `tests/test_aceite_159.py` continuam verdes sem mudar expectativa.

## Invariantes de produção
- Em `/consultor`, nenhum ticker aparece em mais de um `<details class="opiniao-ativo">`.
- Em `/consultor` sem data, para todo ativo listado que tem card com `consenso` em `/api/consultor` (os itens de `resultados` que trazem a chave `consenso`), a soma das contagens do `<summary>` é igual a `consenso.detalhes.total` quando esse consenso não é "cobertura insuficiente"; e a linha diz "cobertura insuficiente" exatamente quando o consenso do ativo diz. Ativo sem card (fora da carteira ou sem 220 pregões) e a página numa data passada não têm consenso para comparar.
- A lista está em ordem decrescente de data da opinião mais recente.
- Em 360 px, `/consultor` não rola para o lado.

## Fora do escopo
- Mostrar a palavra do consenso (`compra`, `dividido`...) ou o alvo mediano na linha: o card do ativo já mostra.
- Mudar `get_opinioes_recentes`, a chave `opinioes_recentes` do JSON de `/api/consultor` ou o bloco "Informações de".
- Filtrar ou ordenar a lista por clique, ou abrir os detalhes por padrão.
- O consenso do Yahoo (spec 159) na mesma linha.
- O fuso das datas de `/sistema` (issue #902).
- O placar por casa (item 24 da *Fila* do backlog, "O placar mede o alvo que a casa declarou").

## Revisão
Revisada em 2026-11-16. Conferido contra `app/consultor/sintese.py`, `app/consultor/calculador.py`, `app/main.py` (ramos históricos de `/consultor` e `/api/consultor`), `app/templates/consultor.html`, `scripts/telas.py` e `app/services/consultor_opinioes.py`. Ajustes:
- A janela era descrita como `[referencia − 30 dias, referencia]`, mas `calcular_consenso` não tem teto superior; o texto passou a dizer a regra de hoje, para `ultima_por_casa` não mudar o resultado do consenso.
- `calcular_consultor` passa o mesmo `agora` à lista e aos `calcular_consenso` do laço, para a invariante de concordância não depender de segundos de diferença.
- O exemplo ganhou o caminho do `preco_alvo` bruto até o texto exibido, e a linha de VALE3 separa `opinioes_texto` do sufixo da tela.
- A segunda invariante ficou restrita aos ativos que têm card com consenso (os itens sem a chave `consenso`, os tickers fora da carteira e as datas passadas não têm).

