---
id: 200
titulo: O consenso do Yahoo sai do Consultor
status: ready
esforco: P
gaveta: poda
aceite: tests/test_aceite_200.py
origem: nova (página de saúde, "Yahoo · consenso · candidato à poda")
---

## Problema
O consenso do Yahoo que o Consultor promete ainda chega a aparecer, e a fonte pode ser usada?

As duas respostas são não:

- **A fonte nunca entregou.** A spec 159 criou o coletor `app/collectors/consultor_yahoo.py` (cookie em `fc.yahoo.com`, crumb e `quoteSummary?modules=financialData` por ativo) com a regra de poda embutida: bloqueado 7 dias seguidos sem leitura nova, o `/sistema` acrescenta "candidato à poda: remover o coletor numa spec de poda". Medido em 27/11/2026 às 03h UTC:
  - `python -m devagent.saude`: "Coleta · Yahoo · consenso: bloqueado (HTTP 429) desde 19/11 18:36; candidato à poda" (8 dias);
  - `GET https://devagent-vb52.onrender.com/api/consultor`: 75 ativos com a chave `consenso_yahoo`, **0** com valor diferente de `null`;
  - `docs/context/fontes-de-dados.md` ainda diz que "a primeira resposta real vista em produção deve ser conferida contra elas e registrada aqui": nenhuma foi registrada.
- **A fonte é proibida pelas regras do produto.** O `PRODUTO.md` (seção 5) manda respeitar o `robots.txt`. O ADR 005 e o próprio `docs/context/fontes-de-dados.md` (seção *Fontes proibidas*, conferida em 18/10/2026) registram o `quoteSummary` como bloqueado pelo `robots.txt`; a spec 159 não revogou nenhum dos dois. Conferido de novo em 27/11/2026: `https://query2.finance.yahoo.com/robots.txt` responde `User-agent: *` / `Disallow: /`.

O coletor gasta uma rodada da janela de fechamento por dia (ou sai cedo pela pausa), mantém duas tabelas, um item de `/sistema` em Atenção permanente e uma chave da API sempre `null`. Nada disso chega ao usuário.

## Comportamento esperado
O que sai:

1. **Coletor.** `app/collectors/consultor_yahoo.py` é apagado; `"consultor_yahoo"` sai do dicionário `janelas` e da tupla de coletores de `app/agendador.py`.
2. **Exibição.** `app/consultor/consenso_yahoo.py` é apagado. As duas chamadas a `consenso_yahoo.anexar` em `app/main.py` (rotas `/consultor` e `/api/consultor`, hoje perto das linhas 676 e 774) saem. O bloco `{% if item.consenso_yahoo %}` de `app/templates/consultor.html` sai. `/api/consultor` deixa de trazer a chave `consenso_yahoo` em cada ativo (hoje sempre `null`; nenhuma checagem de `auditoria/` a lê: `grep -rn consenso_yahoo auditoria` vazio em 27/11).
3. **Banco.** Em `app/consultor/armazenamento.py` saem `SQL_CONSENSO_YAHOO`, `SQL_CONSENSO_YAHOO_STATUS`, `criar_tabelas_consenso_yahoo`, `tem_consenso_yahoo`, `save_consenso_yahoo`, `get_consenso_yahoo`, `resumo_consenso_yahoo`, `max_coletado_em_consenso_yahoo`, `get_consenso_yahoo_status` e `set_consenso_yahoo_status`, e a chamada em `init_db` do consultor. Em `app/database.py` sai a chamada a `criar_tabelas_consenso_yahoo`. As tabelas `consultor_consenso_yahoo` e `consultor_consenso_yahoo_status` deixam de ser criadas; as que já existem no Postgres de produção ficam (sem `DROP`), como fez a spec 168 com as tabelas legadas.
4. **Cache do Consultor.** Em `app/consultor/calculador.py`, o `yahoo_ts` sai da tupla `versao_atual`, que volta a ser `(max_criado, max_extraida, status_ts)`.
5. **`/sistema`.** Saem `verificar_consenso_yahoo` e `BLOQUEIO_PODA_YAHOO` de `app/services/sistema.py`, o parâmetro `consenso_yahoo` de `montar` e `_resumo_consenso_yahoo` de `app/main.py`. O grupo Coleta perde o item "Yahoo · consenso"; os outros itens não mudam.
6. **Documentação.** Em `docs/context/fontes-de-dados.md`, a seção *Yahoo Finance (quoteSummary · consenso de analistas · consultor)* sai; a linha do `quoteSummary` em *Fontes proibidas* fica, acrescida de "o coletor da spec 159 foi removido pela spec 200 (bloqueado em produção de 19/11 a 27/11/2026, nenhuma leitura gravada)". Em *Fontes descontinuadas*, uma linha no mesmo formato da brapi.

O que fica: a decisão do Consultor, o consenso das casas e todas as colunas das tabelas de `/consultor` ficam iguais (a spec 159 já garantia que o Yahoo não entrava na decisão; `test_decisao_igual_com_e_sem_a_tabela` da 159 o provava). O `chart`/`spark` do Yahoo usado por outros coletores e pela auditoria não é tocado (ver *Fora do escopo*).

## Fontes de dados
Nenhuma nova; uma a menos. Sem plano B a desenhar: o Consultor já funcionava sem o Yahoo, que nunca entregou leitura em produção.

## Cálculos
Nenhum. Medida de poda: dias seguidos de bloqueio (8, contados do `desde` da pausa, 19/11 18:36, a 27/11 03h UTC) e ativos com consenso na API (0 de 75).

## Critérios de aceite
- [ ] `tests/test_aceite_200.py`, com `exigir_spec_done("200")`, sem internet:
  - **coletor fora:** `app/collectors/consultor_yahoo.py` e `app/consultor/consenso_yahoo.py` não existem, e nenhum `.py` de `app/` contém `consultor_yahoo`, `consenso_yahoo`, `quoteSummary` ou `getcrumb`;
  - **tabelas fora:** depois de `init_db` (o `setup_db` do `conftest.py`), o `sqlite_master` não tem `consultor_consenso_yahoo` nem `consultor_consenso_yahoo_status`;
  - **API sem a chave:** com os mesmos `monkeypatch` de `tests/test_aceite_193.py` (`_arranjo` e o cliente autenticado), nenhum ativo de `GET /api/consultor` tem a chave `consenso_yahoo`, e a resposta é 200;
  - **`/sistema` sem o item:** `sistema_servico.montar(...)` com as entradas mínimas de `tests/test_sistema.py` não produz item de nome `Yahoo · consenso`;
  - **template:** `app/templates/consultor.html` não contém `consenso_yahoo`.
- [ ] Testes que saem junto com o código podado (`devagent/skills/manutencao.md`, seção 4): `tests/test_aceite_159.py` e `tests/fixtures/yahoo/` (cinco arquivos, usados só por ele; conferir com `grep -rn "fixtures/yahoo" tests`).
- [ ] Testes que só perdem a referência, sem afrouxar o que verificam:
  - `tests/test_aceite_168.py`: as duas tabelas saem de `ESPERADAS` e entram em `LEGADAS` (o nome `test_init_db_cria_exatamente_as_dez_tabelas` pode passar a dizer oito);
  - `tests/test_agendador_partida_a_frio.py`: `consultor_yahoo` sai das listas; as asserções sobre `consultor_fechamento` e `clima_global` ficam;
  - `tests/test_aceite_193.py`: sai o `monkeypatch` de `consenso_yahoo.anexar` (linhas ~181 e ~185);
  - `tests/test_aceite_191.py`: sai a chave `"consenso_yahoo": None` do dicionário de teste.
  - `tests/test_aceite_162.py` usa `"consultor_yahoo"` só como nome de exemplo em `tempos`; pode ficar.
- [ ] Tamanho medido em 27/11 com `grep -rlE "consenso_yahoo|consultor_yahoo" app tests`: 9 arquivos de código (`agendador.py`, `collectors/consultor_yahoo.py`, `consultor/armazenamento.py`, `consultor/calculador.py`, `consultor/consenso_yahoo.py`, `database.py`, `main.py`, `services/sistema.py`, `templates/consultor.html`) e 6 de teste (`test_aceite_159`, `162`, `168`, `191`, `193`, `test_agendador_partida_a_frio`). Quase tudo é remoção.
- [ ] `make verify` verde; `CHANGELOG.md` (entrada `Poda`, citando a spec 159), `docs/STATE.md` e `app/novidades.json` na entrega, como em todo PR. A entrada da 159 no `CHANGELOG.md` e a spec 159 (`done`) ficam como estão: poda não apaga história.

## Invariantes de produção
- `GET /api/consultor` publicado não contém a chave `consenso_yahoo` em nenhum ativo.
- O HTML publicado de `/consultor` não contém o texto `Yahoo:`.
- O `/sistema` publicado não tem o item "Yahoo · consenso", e a página de saúde (`python -m devagent.saude`) deixa de listar essa atenção.
- O número de ativos avaliados (`ativos_avaliados` de `/api/consultor`) e a contagem por decisão (Comprar, Vender, Aguardar, No radar) no mesmo instante são os mesmos de antes do merge: a poda não muda decisão.

## Fora do escopo
- `DROP TABLE` das duas tabelas no Postgres de produção: ficam órfãs, como as legadas da spec 168.
- Outra fonte de consenso de analistas. O ADR 005 registra que não há fonte gratuita e permitida; se aparecer, é spec nova de capacidade.
- O item 20 da *Fila* ("A casa fora da curva"), que dependia da faixa `alvo_minimo`–`alvo_maximo` do Yahoo, sai do backlog neste mesmo PR `spec:`, por depender da fonte podada.
- O `robots.txt` de `query1`/`query2.finance.yahoo.com` responde `Disallow: /` para todo o host, o que alcança também o `chart` e o `spark` que vários coletores (reserva do MT5) e a auditoria usam. Isso é uma pergunta de regra do produto, maior que esta poda; fica como item da *Fila* do backlog, para decisão do dono antes de qualquer spec.
