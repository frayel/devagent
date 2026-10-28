---
id: 127
titulo: Endpoints de diagnóstico dizem a verdade (/api/coleta e cache do /api/consultor)
status: ready
esforco: P
gaveta: saúde técnica
aceite: tests/test_aceite_127.py
revisada: 2026-10-28
---

## Problema
Dois endpoints de diagnóstico mentem sem ninguém perceber:

1. **`/api/coleta` perdeu metade da resposta.** As specs 073a e 077a dizem que ele informa `banco` (`"postgres"` em produção) e o aviso "Banco persistente não configurado". O código que montava isso (`ligada`, `banco`, `aviso`) ficou depois do `return` de `obter_pregoes_disponiveis` (`app/main.py`), onde nunca executa. A rota devolve só `agendador.estado`. O endpoint também é público e expõe as mensagens de erro dos coletores.
2. **O campo `cache` do `/api/consultor` está sempre `True`.** A rota faz `from app.consultor.calculador import _consultor_cache_time`, que copia o valor uma vez, e compara essa mesma variável local antes e depois de `calcular_consultor()`. Sempre que existe algum cache, o campo diz que ele foi usado, mesmo quando o cálculo foi refeito.

## Comportamento esperado
- `GET /api/coleta` devolve `ligada`, `banco`, `ultima_coleta`, `ultimo_erro`, `detalhes` e, em produção sem Postgres, `aviso`, como as specs 073a e 077 descrevem.
- `/api/coleta` fica atrás de `exigir_senha`, como `/api/sistema`. Sem `CONSULTOR_SENHA` continua aberto, como as outras rotas protegidas.
- O código morto depois do `return` sai.
- `cache` em `/api/consultor` é `True` só quando `calcular_consultor` devolveu o resultado guardado sem recalcular. A informação vem do próprio calculador (atributo lido pelo módulo no momento certo, ou um campo no retorno), não de uma cópia feita na importação.

## Fontes de dados
Nenhuma.

## Cálculos
Nenhum.

## Critérios de aceite
- [ ] `GET /api/coleta` traz as chaves `ligada` e `banco`. Com `RENDER=1` e sem `DATABASE_URL`, traz `aviso`.
- [ ] Com `CONSULTOR_SENHA` definida, `GET /api/coleta` sem credenciais devolve 401, e com `consultor:<senha>` devolve 200.
- [ ] Primeira chamada a `/api/consultor` com o cache vazio traz `cache: false`; a segunda, sem dado novo e em menos de 5 min, traz `cache: true`.
- [ ] `tests/test_aceite_087.py` continua verde.
- Arquivos tocados: `app/main.py`, possivelmente `app/consultor/calculador.py`, e o novo `tests/test_aceite_127.py`.

## Invariantes de produção
- `GET /api/coleta` (autenticado) responde `"banco": "postgres"`.

## Fora do escopo
- Mudar o formato de `detalhes`.
