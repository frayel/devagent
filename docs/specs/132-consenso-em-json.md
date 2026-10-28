---
id: 132
titulo: Consenso das recomendações gravado em JSON
status: ready
esforco: M
gaveta: saúde técnica
aceite: tests/test_aceite_132.py
revisada: 2026-10-28
---

## Problema
`app/collectors/consultor_fechamento.py` grava o consenso das casas com `"consenso": str(item.get("consenso", ""))`, ou seja, o `repr` de um dicionário Python. A leitura em `app/main.py` (rotas `/consultor` e `/api/consultor`, ramo histórico) desfaz isso com `ast.literal_eval` e engole qualquer erro com `except: pass`.

Problemas:
- o formato é frágil e só se lê em Python;
- quando o consenso é texto (`"cobertura insuficiente"`, `app/consultor/sintese.py`), `literal_eval` falha e a tela recebe `{}` em silêncio, perdendo a informação.

## Comportamento esperado
- A gravação usa `json.dumps(consenso, ensure_ascii=False)`. Texto vira string JSON; dicionário vira objeto JSON.
- A leitura usa uma função única, `armazenamento.ler_consenso(bruto)`:
  - tenta JSON;
  - se não conseguir, tenta o formato antigo (`ast.literal_eval`) para as linhas já gravadas;
  - se nada funcionar, devolve o texto original e registra um aviso, nunca `{}` em silêncio.
- As duas rotas usam essa função. `import ast` sai de `app/main.py`.
- Uma migração idempotente em `init_db` do armazenamento reescreve em JSON as linhas antigas que o `literal_eval` consegue ler.

## Fontes de dados
Nenhuma.

## Cálculos
Nenhum.

## Critérios de aceite
- [ ] Recomendação gravada com consenso `{"compra": 3, "venda": 1}` fica no banco como JSON válido (`json.loads` funciona).
- [ ] Consenso `"cobertura insuficiente"` chega à API como `"cobertura insuficiente"`, não `{}`.
- [ ] Linha antiga com `"{'compra': 3}"` é lida corretamente e, depois de `init_db`, está gravada como JSON.
- [ ] Rodar a migração duas vezes não altera nada na segunda.
- [ ] `app/main.py` não contém `literal_eval`.
- Arquivos tocados: `app/collectors/consultor_fechamento.py`, `app/consultor/armazenamento.py`, `app/main.py` e o novo `tests/test_aceite_132.py`.

## Invariantes de produção
- Nenhuma recomendação histórica em `/api/consultor?data=` traz `consenso` vazio quando a do mesmo dia, em produção, tinha consenso.

## Fora do escopo
- Mudar o esquema da tabela (a coluna continua `TEXT`).
