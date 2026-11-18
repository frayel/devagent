---
id: 178
titulo: Teste que não confere nada reprova o CI
status: done
esforco: P
gaveta: saúde técnica
aceite: tests/test_aceite_178.py
revisada: 2026-11-18
origem: O teste do agendador confere a rodada
---

## Problema
Quando um teste passa, ele provou alguma coisa? Hoje, nem sempre. Um teste sem `assert` passa enquanto o código não levantar exceção, e um `assert` comentado deixa de conferir sem que o CI note. O `make verify` contou 1222 testes passando em 18/11, mas parte deles não reprova nada.

Medido na `main` de 18/11/2026 (`ast` sobre `tests/**/*.py`, só funções `test_*` que não são fixture, e `grep -rn "^\s*#[ #]*assert" tests`):

- **5 testes sem nenhuma conferência** (sem `assert`, sem `pytest.raises`/`fail`, sem `assert_*` de mock e sem chamar helper que confira):
  - `tests/test_instrumentacao_coleta_tempo.py:18` `test_agendador_registra_tempo`: roda `_coletar()` e termina em `pass  # Tem varios paineis` (o item "O teste do agendador confere a rodada" da *Fila*, achado na spec 168);
  - `tests/test_consultor_dados_reais.py:95` `test_calculador_le_bloco_gravado_no_cache`: grava o cache, chama `calcular_consultor()` e termina em `pass`;
  - `tests/test_historico_diario_proxy.py:8` `test_fetch_historico_diario_uses_cache`: as duas conferências estão comentadas;
  - `tests/test_scanner_capitulacao.py:4` `test_scanner_capitulacao_fallback_simples`: só chama `collect_and_save()`;
  - `tests/test_aceite_095.py:12` `test_rede_liberada`: corpo `pass`.
- **11 `pass` soltos** no meio de corpos de teste (o padrão de quem trocou um `assert` por `pass`): `test_consultor_dados_reais.py` linhas 66, 67, 68, 73, 92 e 103; `test_historico_diario_proxy.py` 36 e 89; `test_instrumentacao_coleta_tempo.py` 66 e 67; `test_aceite_092b.py` 6.
- **8 `assert` comentados** em 4 arquivos: `test_historico_diario_proxy.py` (34, 35, 67, 87), `test_consultor_opinioes.py` (191, 192), `test_radar_congestionamento.py` (57) e `test_pagina_ponta_a_ponta.py` (86).
- **2 conferências que nunca falham:** `assert len(opinioes) >= 0` em `test_consultor_opinioes.py:189` e `assert len(regras) >= 0` em `test_avaliador_historico.py:64` (achada na revisão: `test_avaliador_historico` roda `rodar_backtest()` e não confere nada do que ele grava).
- **1 teste que confere por import** (achado na revisão): `tests/test_aceite_135.py:172` `test_criterio_5_fronteira_chart_previous_close` só chama dois `test_*` importados de `tests/test_fronteira_chart_previous_close.py`, que têm `assert`. Ele confere de verdade, mas a regra "função do mesmo módulo" o reprovaria.
- Um caso dentro de teste que tem outras conferências: em `test_coletor_alimenta_calculador`, o comentário "Segunda rodada dentro da hora usa o cache, sem pedir de novo" é seguido de `collect_and_save()` e `pass`, sem conferir que não houve pedido novo.

Conferido nesta sessão, descomentando cada `assert` na `main` (e desfazendo):

| Arquivo | Resultado ao descomentar | Causa |
|---|---|---|
| `test_radar_congestionamento.py:57` | passa | só estava comentado |
| `test_historico_diario_proxy.py:34` e `:67` | falham: o Yahoo é chamado mesmo com o cache gravado | o teste grava `{"symbol": ..., "response": [{"meta": ...}]}`, formato que `save_historico_diario` (`app/database.py:1727`) descarta sem gravar, porque espera o bloco de `chart.result[0]` (`timestamp` e `indicators.quote[0].close`). Com um bloco nesse formato e `range` `1mo`, o mesmo `fetch_historico_diario_yfinance_spark` serve do cache e não chama o Yahoo (conferido: 0 pedidos, 1 resultado). O defeito é do teste, não do código |
| `test_consultor_opinioes.py:191` | `NameError`: a linha que define `tickers` também está comentada | a conferência de verdade depende do texto que o mock devolve |
| `test_pagina_ponta_a_ponta.py:86` | falha: a página mostra "Dado indisponível agora. A fonte não respondeu na última coleta." | algum card fica sem dado com as fixtures de `_coletar_tudo`; não se sabe ainda se é fixture faltando ou defeito |

## Comportamento esperado
Nada muda para quem usa o produto. Muda o que o CI aceita em `tests/`:

1. **Teste novo `tests/test_aceite_178.py`**, que lê com `ast` todos os `tests/**/*.py` (sem importar os módulos) e reprova, com arquivo e linha na mensagem:
   1. função `test_*` de nível de módulo ou de classe, não decorada com `pytest.fixture`, **sem conferência**. Conta como conferência, em qualquer ponto do corpo: `assert`; `raise`; chamada a `pytest.raises`, `pytest.warns`, `pytest.fail` ou `pytest.skip`; chamada a método cujo nome começa com `assert_` (mocks); ou chamada a uma função do mesmo módulo, ou importada por nome de outro arquivo de `tests/` (`from tests.x import f` ou `from .x import f`), que tenha conferência por essa mesma regra (seguindo as chamadas, com proteção contra ciclo). Exceções: o corpo que só chama `exigir_spec_done(...)` (o marcador de `devagent/aceite.py`, ADR 018) e os nomes da lista `SEM_CONFERENCIA` do próprio teste;
   2. `pass` num corpo com mais de um comando, dentro de função `test_*`;
   3. linha de comentário que começa com `assert` (`^\s*#[\s#]*assert\b`) em `tests/**/*.py`;
   4. `assert len(...) >= 0`.
2. **`SEM_CONFERENCIA`** é um `dict` no topo de `tests/test_aceite_178.py`, de `"arquivo::nome"` para o motivo, com **no máximo 3** entradas e o teste reprovando se passar disso ou se uma entrada apontar para teste que não existe. Serve a teste cuja promessa é "não levanta" e que não chama nada que confira. Na revisão, a varredura com a regra 1.1 sobre a `main` de 18/11 não precisou dela para nenhum teste além, talvez, de `test_rede_liberada` (`tests/test_aceite_152.py::test_falha_ao_gravar_nao_derruba_a_rodada`, por exemplo, já passa porque os helpers que chama conferem).
3. **Os casos de hoje passam a conferir**, cada um dizendo o que o nome promete:
   - `test_agendador_registra_tempo`: fixa o relógio num pregão (técnica de `tests/test_aceite_154.py`), espia `gravar_instrumentacao_rodada` e confere que ela recebe um tempo `> 0` para cada coletor que rodou (na fixture, `FakeModule`);
   - `test_calculador_le_bloco_gravado_no_cache`: confere que `calcular_consultor()` devolve resultado para os tickers gravados sem pedir nada à rede (um `fetch_with_retry` espião com zero chamadas);
   - `test_coletor_alimenta_calculador`: os três `pass` depois de `calcular_consultor()` viram conferências do resultado, e a segunda rodada confere que `pedidos` não cresceu;
   - `test_pagina_consultor_mostra_ativos`: o `pass` final sai;
   - `test_historico_diario_proxy.py`: os dois testes gravam o cache no formato que `save_historico_diario` aceita (bloco de `chart.result[0]`, com `timestamp` e `close` de pregões recentes) e um `range` conhecido por `get_historico_diario` (por exemplo `1mo`); as quatro conferências comentadas voltam (o cacheado não é pedido, o que falta é, e a contagem de resultados);
   - `test_consultor_opinioes.py` (linhas 186 a 192): o mock devolve texto que cita BBAS3 e PETR4 de forma que `extrair_opinioes` aceite, e o teste confere que os dois tickers estão entre as opiniões gravadas; `assert len(opinioes) >= 0` sai;
   - `test_radar_congestionamento.py:57`: a conferência volta sem mudança (já passa);
   - `test_pagina_ponta_a_ponta.py:86`: descobrir qual card mostra "Dado indisponível agora". Se faltar fixture em `_coletar_tudo`, acrescentá-la e a conferência volta como está. Se for defeito do código, ver *Fora do escopo*;
   - `test_scanner_capitulacao_fallback_simples`: confere o que `collect_and_save()` devolve e o que fica gravado quando a fonte responde `{}`;
   - `test_rede_liberada`: confere algo observável de a marca `rede` desligar o bloqueio do `tests/conftest.py` (`_bloquear_rede`, linha 89), sem ir à internet; se não houver nada observável, entra em `SEM_CONFERENCIA` com o motivo;
   - `test_aceite_092b.py`: o `pass` sai (o teste vira o marcador puro);
   - `test_avaliador_historico.py:64`: `assert len(regras) >= 0` vira uma conferência do que `rodar_backtest()` gravou para PETR4 com os dados de `setup_mock_data` (ao menos uma regra, com os campos que `get_consultor_confianca` devolve); se a fixture não gerar regra nenhuma, a fixture é que muda;
   - `test_aceite_135.py:172`: nada muda; passa pela regra do import.

## Fontes de dados
Nenhuma. Só `tests/`.

## Cálculos
Não há fórmula. O exemplo de ponta a ponta da regra 1.1, do código ao veredito:

```python
def _conferir(x):            # helper com conferência
    assert x == 2

def test_a():                # passa: chama helper do módulo que confere
    _conferir(1 + 1)

def test_b():                # reprova: "tests/x.py:7 test_b sem conferência"
    calcular()
    pass                     # e reprova pela regra 1.2, linha 9
```

## Critérios de aceite
- [ ] `tests/test_aceite_178.py` passa na `main` depois da mudança e lista zero violações das regras 1.1 a 1.4.
- [ ] O mesmo teste tem casos próprios que alimentam o verificador com código-fonte de exemplo (strings, sem escrever arquivo fora de `tmp_path`) e conferem que ele reprova: teste sem conferência; `pass` solto; `assert` comentado; `assert len(x) >= 0`; e que **não** reprova: helper do módulo com `assert`, função `test_*` importada de outro arquivo de `tests/` que tem `assert`, `pytest.raises`, `mock.assert_called_once()`, corpo só com `exigir_spec_done("NNN")`, fixture chamada `test_db`.
- [ ] `SEM_CONFERENCIA` tem no máximo 3 entradas, cada uma com motivo, e todas apontam para testes que existem.
- [ ] Nenhum teste existente perde conferência: a contagem de `assert` em `tests/` não cai (confira com `grep -rc "assert" tests` antes e depois e escreva os dois números no PR).
- [ ] `make verify` passa, sem `skip` novo e sem `xfail` novo além do previsto em *Fora do escopo*.

## Invariantes de produção
Nenhuma mudança visível no site publicado: `/api/snapshot` e as páginas continuam iguais, e o `make audit` dá o mesmo resultado antes e depois do merge. A garantia desta spec vive no CI: um PR que acrescente teste sem conferência, `pass` solto ou `assert` comentado em `tests/` fica vermelho no `make verify`.

## Fora do escopo
- Corrigir código da aplicação. Se uma conferência restaurada revelar defeito em `app/` (o candidato é `test_pagina_ponta_a_ponta.py:86`), o PR abre uma issue com o label `bug` descrevendo o card e a fixture, e o teste fica com `@pytest.mark.xfail(strict=True, reason="#N")` apontando para ela. Desativar ou apagar o teste continua proibido.
- `devagent/tests/`: o núcleo tem regras próprias; esta spec só olha `tests/`.
- Avaliar se cada conferência é a melhor possível (mutação de código, cobertura). A regra é o piso: todo teste confere alguma coisa.
- O item 4 da *Fila* (classe de template sem estilo), que é outra checagem estática.
