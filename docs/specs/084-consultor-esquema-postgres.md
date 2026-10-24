---
id: 084
titulo: Consultor no Postgres com o esquema completo (tabela de cota e coluna da fila)
status: ready
esforco: P
gaveta: saúde técnica
aceite: tests/test_aceite_084.py
revisada: 2026-10-24
---

## Problema

Em produção, a página `/sistema` acusa `consultor_opinioes: relation "consultor_llm_uso" does not exist`, a aba Consultor mostra sempre "Nenhuma opinião recente." e a integração Gemini aparece como *Inativo*, mesmo com `GEMINI_API_KEY` cadastrada no Render. As três coisas têm a mesma causa, confirmada no `/api/sistema` de produção em 24/10/2026: o erro da última rodada é `consultor_opinioes: relation "consultor_llm_uso" does not exist`, e o item do Gemini diz "sem chamadas desde a partida" (e não "sem GEMINI_API_KEY"), o que mostra que a chave está configurada e que nenhuma chamada saiu.

A spec 077b foi marcada `done`, mas o esquema do Postgres ficou incompleto. Em `app/consultor/armazenamento.py::init_db`, o ramo Postgres cria cinco tabelas (`consultor_opinioes`, `consultor_opinioes_status`, `consultor_recomendacoes`, `consultor_fechamentos`, `consultor_fila_materias`) e **não cria**:

1. `consultor_llm_uso`, que `app/services/consultor_opinioes.py::get_llm_uso_hoje` lê no começo de toda extração. A exceção sobe antes de qualquer chamada ao Gemini: a extração nunca chega à API, nenhuma opinião é gravada e o registro de fontes nunca vê uma chamada ao Gemini (daí o *Inativo*, que é "sem chamadas desde a partida", e não "sem chave").
2. A coluna `processada` de `consultor_fila_materias`. Ela só existe no `ALTER TABLE` do SQLite em `app/database.py`. `get_materias_nao_processadas` filtra por `processada = 0`; no Postgres isso será o próximo erro (`column "processada" does not exist`) assim que a tabela de cota existir.

O teste de aceite da 077b passou porque usa uma conexão Postgres falsa e só confere a sintaxe do SQL (`%s`, `ON CONFLICT`), não a existência das tabelas e colunas.

## Comportamento esperado

- O ramo Postgres de `init_db` cria `consultor_llm_uso (data DATE PRIMARY KEY, chamadas INTEGER NOT NULL DEFAULT 0)` e inclui `processada INTEGER NOT NULL DEFAULT 0` no `CREATE TABLE` de `consultor_fila_materias`.
- Para bancos que já existem (a produção está nesse caso), `init_db` também roda `ALTER TABLE consultor_fila_materias ADD COLUMN IF NOT EXISTS processada INTEGER NOT NULL DEFAULT 0`. Matérias já na fila ficam com `processada = 0`.
- Todo SQL que `app/services/consultor_opinioes.py`, `app/consultor/armazenamento.py` e `app/consultor/placar.py` mandam ao banco só usa tabelas e colunas que o `init_db` dos **dois** backends cria. O esquema dos dois ramos é o mesmo (nomes de tabelas e colunas).
- A cota diária do Gemini conta o dia em BRT (`America/Sao_Paulo`), não em UTC: hoje `date.today()` vira o dia às 21h BRT e a cota "zera" no meio da noite.
- Se a extração falhar **antes** de chamar o Gemini (banco, esquema), `extrair_opinioes` registra `set_opinioes_status("erro", "falha no banco: <tipo do erro>")`, protegido para que uma falha ao gravar o status não derrube a coleta, e deixa a exceção original no log. Assim a aba Consultor e `/sistema` dizem o motivo, em vez de mostrar só "Nenhuma opinião recente."

## Fontes de dados e Cálculos

Nenhuma nova.

## Critérios de aceite

- [ ] Com uma conexão Postgres falsa que registra o SQL executado, `init_db()` emite `CREATE TABLE IF NOT EXISTS consultor_llm_uso` e a coluna `processada` na criação e no `ALTER ... ADD COLUMN IF NOT EXISTS`.
- [ ] Teste de paridade: o conjunto de tabelas e colunas criado pelo ramo Postgres é igual ao do ramo SQLite (comparando os dois `CREATE TABLE` dos módulos do Consultor).
- [ ] Teste de cobertura: toda tabela citada em `FROM`, `INTO`, `UPDATE` ou `DELETE FROM` nos três módulos do Consultor aparece em um `CREATE TABLE` do `init_db` (varredura do código-fonte).
- [ ] Com SQLite temporário, o ciclo completo funciona: `save_materia`, `extrair_opinioes` com o Gemini simulado (respx), `save_opiniao`, `get_opinioes_recentes` devolve a opinião, `get_llm_uso_hoje` devolve 1.
- [ ] A data da cota é a de BRT (teste com relógio simulado às 22h BRT: ainda é o mesmo dia da cota).
- [ ] Erro de banco antes da chamada ao Gemini grava o status `erro` com o motivo e não propaga exceção para o agendador.

## Invariantes de produção

- A última rodada do coletor `consultor_opinioes` em `/api/coleta` não traz erro com `relation` ou `column` no texto.
- Com `GEMINI_API_KEY` cadastrada e matérias na fila, `/api/sistema` deixa de mostrar o erro `consultor_opinioes:` no grupo *Coleta*.

## Fora do escopo

- Mostrar o motivo da falta de opiniões na tela (spec 085).
- Ativação e validação da chave do Gemini (spec 092).
- Desempenho do Consultor (spec 087).
