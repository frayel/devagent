# Resumo da execução
**Data**: 2026-10-28
**Spec**: 122 - Reduzir a transferência de rede do Postgres (Neon)

## Alterações Realizadas
- `app/database.py`: Otimizado `get_historico_diario` para interpretar `range_str` e limitar o período inicial da consulta, além de respeitar `max_age_minutes` filtrando resultados velhos durante pregão. Um cache in-memory em dicionário foi implementado e associado à função, verificando a versão atual no banco via `versao_series` para manter coerência. Além disso, o tamanho do cache foi limitado (<100) para prevenir *Out of Memory* (OOM).
- `app/banco.py`: Adicionada a função `versao_series` (com suporte a SQLite e PostgreSQL via `ANY(%s)`) que busca unicamente a maior data `criado_em` da tabela sem extrair todo o conteúdo, reduzindo leitura de base. O resultado de `diagnostico()` também foi cacheado por 5 minutos.
- `app/consultor/calculador.py`: Ao processar os dados do consultor, a versão atual é montada acessando `versao_series`, e os recomendadores apenas buscam dados plenos do histórico se houver alteração ou superação de 300 segundos (5min) no tempo de expiração do cache.
- `tests/test_aceite_122.py`: Foram criados testes automatizados que cobrem espionamento das chamadas com as datas limitadas em vez de 730 dias sempre, bem como o isolamento de chamadas por cache tanto ao `get_historico_diario` como em `calcular_consultor` e `diagnostico`.
- `tests/test_aceite_087.py` e `tests/test_aceite_085.py`: Testes que foram acidentalmente afetados pela adição do cache e inicialização de banco em ambientes de mock foram modificados para resetar ou interagir corretamente.

## Observações Pós-Review
- O Code Review explicitou vulnerabilidades no dicionário global de cache, apontando potencial de memória esgotada (OOM) caso o tamanho das chaves em `get_historico_diario` fossem arbitrárias, e que se as séries expirassem durante o pregão, a omissão delas provocaria `KeyError` no cálculo do consultor. A versão corrigida aplicou limitação do cache (`len(cache) > 100`) e corrigiu checagens de `tzinfo`. A falha no array sem itens (`[]`) para SQLite foi evitada saindo da função imediatamente no topo de `versao_series`.

## Status
Spec `122-banco-reduzir-transferencia.md` concluída e alterada para `status: done`. `CHANGELOG.md` e `docs/STATE.md` atualizados.
