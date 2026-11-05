---
id: 132a
titulo: Leitura do consenso e remoção de literal_eval em main.py
status: ready
esforco: P
gaveta: saúde técnica
aceite: tests/test_aceite_132a.py
revisada: 2026-11-05
---

## Problema
A leitura em `app/main.py` (rotas `/consultor` e `/api/consultor`, ramo histórico) usa `ast.literal_eval` para ler o consenso das casas (que atualmente é salvo com `repr` de dicionário) e engole qualquer erro com `except: pass`.

Problemas:
- o formato é frágil;
- quando o consenso é texto (`"cobertura insuficiente"`, `app/consultor/sintese.py`), `literal_eval` falha e a tela recebe `{}` em silêncio, perdendo a informação.

## Comportamento esperado
- A leitura usa uma função única, `armazenamento.ler_consenso(bruto)`:
  - tenta JSON;
  - se não conseguir, tenta o formato antigo (`ast.literal_eval`) para as linhas já gravadas;
  - se nada funcionar, devolve o texto original e registra um aviso, nunca `{}` em silêncio.
- As duas rotas usam essa função. `import ast` sai de `app/main.py`.

## Fontes de dados
Nenhuma.

## Cálculos
Nenhum.

## Critérios de aceite
- [ ] Consenso `"cobertura insuficiente"` chega à API como `"cobertura insuficiente"`, não `{}`.
- [ ] Linha antiga com `"{'compra': 3}"` é lida corretamente (como dicionário Python).
- [ ] O dicionário lido é retornado intacto, e strings válidas JSON viram dicionário na leitura.
- [ ] `app/main.py` não contém `literal_eval`.
- Arquivos tocados: `app/consultor/armazenamento.py`, `app/main.py` e o novo `tests/test_aceite_132a.py`.

## Invariantes de produção
- Nenhuma recomendação histórica em `/api/consultor?data=` traz `consenso` vazio quando a do mesmo dia, em produção, tinha consenso.

## Fora do escopo
- Alterar a lógica de gravação.
- Fazer a migração de registros existentes.
