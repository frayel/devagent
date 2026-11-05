---
id: 132b
titulo: Gravação do consenso em JSON no coletor
status: done
esforco: P
gaveta: saúde técnica
aceite: tests/test_aceite_132b.py
revisada: 2026-11-05
---

## Problema
`app/collectors/consultor_fechamento.py` grava o consenso das casas usando o formato `str(item.get("consenso", ""))`, que corresponde ao `repr` de um dicionário Python. Este formato é difícil de ler em outras linguagens e frágil.

## Comportamento esperado
- A gravação em `app/collectors/consultor_fechamento.py` usa `json.dumps(consenso, ensure_ascii=False)`.
- Texto simples de consenso passa a ser gravado como string JSON ("\"cobertura insuficiente\""); dicionário passa a ser gravado como objeto JSON.

## Fontes de dados
Nenhuma.

## Cálculos
Nenhum.

## Critérios de aceite
- [ ] Recomendação gravada com consenso `{"compra": 3, "venda": 1}` fica no banco como JSON válido (`json.loads` funciona).
- Arquivos tocados: `app/collectors/consultor_fechamento.py` e o novo `tests/test_aceite_132b.py`.

## Invariantes de produção
- O endpoint da API do consultor não exibe erro ao ler as novas linhas que já foram gravadas em JSON (depende da leitura introduzida na 132a).

## Fora do escopo
- Migrar o banco existente.
