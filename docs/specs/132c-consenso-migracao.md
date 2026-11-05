---
id: 132c
titulo: Migração de formato de consenso para JSON
status: ready
esforco: P
gaveta: saúde técnica
aceite: tests/test_aceite_132c.py
revisada: 2026-11-05
---

## Problema
A base de dados atual possui várias linhas gravadas usando o formato `repr` do Python (`"{'compra': 3}"`). Embora as rotas saibam ler este formato legado, é ideal que os dados no banco de dados sejam gradualmente convertidos para o formato JSON correto.

## Comportamento esperado
- Uma migração idempotente em `init_db` do armazenamento do consultor (`app/consultor/armazenamento.py`) lê os registros antigos que contêm dicionários Python e os reescreve em JSON.
- A função de migração usa `ast.literal_eval` para detectar o formato legado de dicionário de forma segura e fazer o `UPDATE` correspondente com `json.dumps`.

## Fontes de dados
Nenhuma.

## Cálculos
Nenhum.

## Critérios de aceite
- [ ] Linha antiga com `"{'compra': 3}"` é processada e, depois de `init_db`, está gravada como o JSON equivalente (ex: `'{"compra": 3}'`).
- [ ] Rodar a migração duas vezes não altera nada na segunda vez.
- Arquivos tocados: `app/consultor/armazenamento.py` e o novo `tests/test_aceite_132c.py`.

## Invariantes de produção
- A migração não quebra a leitura de `/api/consultor?data=` e não altera dados caso a gravação do formato não-JSON não seja de fato um dict avaliável.

## Fora do escopo
- Mudar o esquema da tabela (a coluna continua `TEXT`).
