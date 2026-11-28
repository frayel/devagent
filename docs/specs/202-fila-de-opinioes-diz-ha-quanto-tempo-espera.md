---
id: 202
titulo: A fila de opiniões diz há quanto tempo a matéria mais antiga espera
status: done
esforco: P
gaveta: capacidade nova
aceite: tests/test_aceite_202.py
origem: A fila de opiniões tem idade
revisada: 2026-11-28
---

## Problema
Há quanto tempo a matéria mais antiga espera a extração de opiniões? Desde a spec 198 a página `/consultor` diz "N matérias na fila" contando no banco certo, mas N sozinho não diz se a fila é da última hora ou de dois dias atrás. Com a cota diária do Gemini (código `cota`) e as 10 matérias por chamada de `app/services/consultor_opinioes.py:129` (`ORDER BY criado_em ASC LIMIT 10`), a fila pode envelhecer sem que ninguém perceba.

A idade importa por um motivo que a tela hoje esconde: a cada matéria nova, `app/consultor/armazenamento.py` (`save_materia`, linha 421; ramos Postgres ~linha 466 e SQLite ~linha 501) apaga da fila **toda** linha com `criado_em` de mais de 3 dias, processada ou não, e corta a fila em 200 linhas. Matéria que espera mais de 3 dias sai sem extração, em silêncio.

Medida de tamanho: muda `app/consultor/armazenamento.py` (uma função de leitura), `app/consultor/diagnostico.py` (uma função), `app/main.py` (as rotas `pagina_consultor` e `api_consultor`, uma chamada cada) e `app/templates/consultor.html` (os ramos `aguardando` e `fila` do aviso). Testes que tocam o que muda: `grep -rl "matérias na fila\|fontes_opiniao" tests` dá `test_aceite_085.py`, `test_aceite_157.py` e `test_aceite_198.py` (e os que chamam `/api/consultor`, como `test_aceite_131.py` e `test_aceite_193.py`); nenhum muda de asserção (as frases de hoje continuam como estão, a frase nova vem depois delas).

## Comportamento esperado
1. Função nova `fila_pendente_desde() -> str | None` em `app/consultor/armazenamento.py`: `SELECT MIN(criado_em) FROM consultor_fila_materias WHERE processada = 0`, pelo `get_connection` do próprio módulo, com `init_db()` antes, como `contar_fila_pendente`. Fila vazia devolve `None`. Erro de banco propaga.
2. Função nova `idade_da_fila(agora: datetime) -> dict` em `app/consultor/diagnostico.py`, que devolve sempre as três chaves:
   - `desde`: o `criado_em` da mais antiga, como veio do banco (texto ISO), ou `None`;
   - `horas`: `(agora − desde)` em horas, arredondado a uma casa, nunca negativo, ou `None`;
   - `texto`: a idade por `ha_quanto(desde, agora)` de `app/services/sistema.py` (a mesma régua do `/sistema`: "há 40 min", "há 5 h", "há 2 dias"), ou `""`.

   Fila vazia, `criado_em` ilegível ou qualquer exceção (inclusive de `fila_pendente_desde`): `{"desde": None, "horas": None, "texto": ""}`. A função nunca levanta. `diagnostico_de_opinioes` **não muda** (as oito chaves dela são contrato da spec 198).
3. `pagina_consultor` e `api_consultor` chamam `idade_da_fila(datetime.now(timezone.utc))` só no pregão de hoje (`is_historical` falso); no pregão passado não chamam, e o valor é `{"desde": None, "horas": None, "texto": ""}`.
   - `api_consultor`: `fontes_opiniao` ganha a chave `fila_idade` com o dicionário inteiro.
   - `pagina_consultor`: passa o dicionário ao template como `fila_idade`.
4. Em `consultor.html`, nos ramos `aguardando` e `fila` do aviso (só aparecem com a lista de opiniões vazia, como hoje), quando `fila_idade.texto` não é vazio, a frase de hoje ganha depois dela, no mesmo `<p>`:
   - ` A mais antiga espera {{ fila_idade.texto }}.`
   - e, se `fila_idade.horas >= 48`, também ` Matérias com mais de 3 dias saem da fila sem extração.`

   As frases de hoje não mudam de texto. Nenhuma classe CSS nova.

## Fontes de dados
Nenhuma fonte externa nova. A coluna `criado_em` de `consultor_fila_materias`, que `save_materia` já grava com `datetime.now(timezone.utc).isoformat()` (ex.: `2026-11-28T10:00:00+00:00`). Banco fora do ar: a idade some (`texto` vazio), o aviso fica como hoje e a rota responde 200.

## Cálculos
`horas = round(max(0, (agora − desde).total_seconds()) / 3600, 1)`; `texto = ha_quanto(desde, agora)`. Exemplos de ponta a ponta, todos com `agora = 2026-11-28T15:00:00+00:00` e status `ok` com extração já feita e lista vazia (código `fila`):

| Fila (`processada = 0`) e `criado_em` da mais antiga | `horas` | `texto` | O aviso diz |
|---|---|---|---|
| 7 matérias, a mais antiga `2026-11-28T10:00:00+00:00` | 5.0 | `há 5 h` | `7 matérias na fila, a próxima extração é na próxima rodada. A mais antiga espera há 5 h.` |
| 1 matéria, `2026-11-28T14:20:00+00:00` | 0.7 | `há 40 min` | `1 matérias na fila, a próxima extração é na próxima rodada. A mais antiga espera há 40 min.` |
| 3 matérias, a mais antiga `2026-11-26T09:00:00+00:00` | 54.0 | `há 2 dias` | `3 matérias na fila, a próxima extração é na próxima rodada. A mais antiga espera há 2 dias. Matérias com mais de 3 dias saem da fila sem extração.` |
| fila vazia (só linhas com `processada = 1`) | `None` | `""` | o aviso de hoje para o código (`sem_materias`, por exemplo), sem frase nova |

Conta da primeira linha: 15:00 − 10:00 = 18 000 s → 300 min (≥ 90) → 5,0 h (< 36) → `ha_quanto` dá `há 5 h`. Terceira: 54 h (≥ 36) → 54 / 24 = 2,25 → `há 2 dias`; 54 ≥ 48, por isso o aviso de descarte. Linhas com `processada = 1` não contam para o `MIN`, mesmo mais antigas.

## Critérios de aceite
`tests/test_aceite_202.py`, com `exigir_spec_done("202")`, sem internet, com o banco do Consultor num SQLite de teste (o arranjo da `test_aceite_198`).

- [ ] Com as linhas da primeira linha da tabela mais uma linha `processada = 1` de `2026-11-25T08:00:00+00:00`, `fila_pendente_desde()` devolve `"2026-11-28T10:00:00+00:00"`; com a fila só de processadas, devolve `None`.
- [ ] `idade_da_fila(agora)` devolve, para as três primeiras linhas da tabela, exatamente os `horas` e `texto` da tabela; para a fila vazia, `{"desde": None, "horas": None, "texto": ""}`.
- [ ] Com `fila_pendente_desde` trocada por uma função que levanta, `idade_da_fila(agora)` devolve `{"desde": None, "horas": None, "texto": ""}` sem levantar, e `GET /api/consultor` responde 200.
- [ ] `GET /consultor` (pregão de hoje, status `ok` com extração feita, lista vazia, 7 pendentes com a mais antiga gravada 5 h e 5 min antes de agora) contém `7 matérias na fila, a próxima extração é na próxima rodada. A mais antiga espera há 5 h.`; com a mais antiga 54 h antes, contém `A mais antiga espera há 2 dias. Matérias com mais de 3 dias saem da fila sem extração.`
- [ ] `GET /api/consultor`, no arranjo de 5 h, traz `fontes_opiniao.fila_idade.texto == "há 5 h"` e `fontes_opiniao.fila_idade.horas` entre 5.0 e 5.2.
- [ ] `GET /consultor?data=2023-11-01` (pregão passado, o arranjo da 193) não contém `A mais antiga espera`, e `GET /api/consultor?data=2023-11-01` traz `fontes_opiniao.fila_idade.desde is None`; um `monkeypatch` que faz `fila_pendente_desde` levantar prova que ela não é chamada no pregão passado.
- [ ] Os testes que já existem passam sem mudança de asserção (`make verify`), em especial `tests/test_aceite_085.py`, `tests/test_aceite_198.py`, `tests/test_aceite_131.py` e `tests/test_aceite_193.py` (estes dois contam conexões no pregão passado, onde a função nova não abre nenhuma).

## Invariantes de produção
- `GET /api/consultor` responde 200 e `fontes_opiniao.fila_idade` tem as chaves `desde`, `horas` e `texto`.
- Quando `fontes_opiniao.fila == 0`, `fontes_opiniao.fila_idade.desde` é `null`; quando `fila > 0`, `desde` não é `null` (salvo erro de banco) e `horas` é um número maior ou igual a 0. Não há teto: a poda de 3 dias só roda dentro de `save_materia`, e o laço das opiniões fica até 2 h sem ler fora do pregão (`FORA_DO_PREGAO` em `app/agendador.py`) e sem gravar nada quando nenhuma fonte responde; nesses intervalos a mais antiga passa de 72 h, e é justamente isso que a frase nova deve mostrar.
- `GET /consultor?data=<pregão passado da janela>` não contém `A mais antiga espera`.

## Fora do escopo
- O selo de atenção no `/sistema` quando a fila passa de um limite de idade: fica no item *A fila de opiniões tem idade* da *Fila* do backlog.
- Contar quantas matérias a poda de 3 dias (e o teto de 200) apagou sem extração: exige registrar o descarte, que hoje não deixa rastro. Também fica no item do backlog.
- Mudar a poda de 3 dias, o teto de 200 ou o `LIMIT 10` da extração.
- Mostrar a idade quando a lista de opiniões não está vazia (o aviso inteiro só aparece com a lista vazia, como hoje).
- Mudar `diagnostico_de_opinioes` ou as frases de hoje do aviso.
