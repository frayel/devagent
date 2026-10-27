---
id: 095
titulo: Testes que não dependem da rede (coletor de feeds do Consultor e bloqueio de rede no CI)
status: done
esforco: P
gaveta: saúde técnica
aceite: tests/test_aceite_095.py
revisada: 2026-10-25
---

## Problema

Parte dos testes chama a internet de verdade. Ao rodar `pytest` num ambiente sem acesso a `www.moneytimes.com.br` e `www.infomoney.com.br`, seis testes falham em 24/10/2026:

- `tests/test_agendador.py::test_falha_de_um_coletor_nao_impede_o_outro`
- `tests/test_agendador.py::test_mascara_token_no_estado` (esperava `token=***` no último erro e recebeu `consultor_opinioes: nenhuma fonte respondeu`)
- `tests/test_pagina_ponta_a_ponta.py::test_todo_painel_recebe_dados_do_seu_coletor`
- `tests/test_pagina_ponta_a_ponta.py::test_pagina_renderiza_com_dados_reais_dos_coletores`
- `tests/test_pagina_ponta_a_ponta.py::test_faca_caindo_mostra_dias_e_variacao`
- `tests/test_pagina_ponta_a_ponta.py::test_nenhum_painel_vaza_dicionario_cru`

Esses testes trocam o Yahoo por um falso (`tests/yahoo_falso.py`), mas o coletor `consultor_opinioes` faz `httpx.get` dos dois feeds RSS sem nenhuma troca, e os logs dos testes mostram brapi e Yahoo reais respondendo 404 (`/api/quote/list`, `ELET3.SA`). Quando o resultado depende de a internet estar de pé e de o feed responder do jeito esperado, o CI passa ou falha por motivo que não tem relação com o código do PR. É a mesma classe de problema do aviso do ADR 018 sobre testes que passam sem provar nada.

Dois PRs recentes tiveram falha de CI no passo `make verify` com mudanças que não tocam esses arquivos (o da spec 079, depois o de verificação), e o PR que abriu as specs 084 a 093, que só mexe em documentos, também falhou. Não foi possível ler o log do CI (a API devolve 403 para o download), então a ligação entre esses casos e os seis testes acima é uma inferência, não uma confirmação.

## Comportamento esperado

- Os testes do agendador e de página ponta a ponta trocam também `consultor_opinioes.collect_and_save` (ou o `httpx.get` dos feeds) por um feed de fixture, e passam sem rede.
- Um `conftest.py` com fixture `autouse` bloqueia qualquer conexão de rede que não seja `localhost`, `127.0.0.1` e `testserver`, em `socket` e `httpx`, com a mensagem "teste tentou chamar a rede: <url>". Teste que precisa de rede de verdade fica fora do `make verify`, marcado `@pytest.mark.rede` e rodado só com `pytest -m rede`.
- Um teste novo prova o bloqueio: tentar `httpx.get("https://example.com")` num teste comum levanta o erro do bloqueio.
- O `make verify` passa nesta máquina com o acesso à rede desligado e com ele ligado.

## Fontes de dados

Nenhuma.

## Critérios de aceite

- [x] Os seis testes acima passam com a rede bloqueada.
- [x] `pytest -q` inteiro passa sem acesso à rede (execução com `unshare -n` ou equivalente documentado no `Makefile`, ou o bloqueio do `conftest.py`).
- [x] Um teste que chama `httpx.get("https://example.com")` falha com a mensagem do bloqueio.
- [x] Nenhum teste fora de `@pytest.mark.rede` faz requisição externa (o bloqueio o garante).
- [x] O guia do projeto (`PRODUTO.md`, seção de testes) diz que teste não pode usar a rede.

## Invariantes de produção

Nenhum. É uma melhoria do CI.

## Fora do escopo

- Reescrever os testes de coletor que já usam `respx`.
- Mudar o código de produção dos coletores.
