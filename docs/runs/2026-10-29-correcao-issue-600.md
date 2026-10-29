# Correção Issue #600

## Problema
A produção estava reportando a issue 600 devido à quebra de contrato da API `/api/snapshot` (`app.acessivel`). O contrato estipula que todos os itens presentes no dicionário `paineis` do snapshot devam ser estritamente objetos e expor explicitamente as chaves `fonte` e `coletado_em`. Antes das correções, múltiplos painéis retornavam ou listas, ou objetos vazios `{}` ou nulos `None` sem as metadados adequados quando não havia dados ou quando os dados eram salvos como listas diretamente.

## Solução
A lógica de retorno da API `snapshot()` no `app/main.py` foi ajustada caso a caso:
- Painéis como `esforco_resultado`, `divergencia_volume`, `falso_rompimento`, `liquidez_abertura`, `anomalia_peso` e `anomalias_spread` passaram a encapsular os alertas de retorno num dicionário `{"alertas": alertas, "fonte": ..., "coletado_em": ...}` quando retornados na API.
- Se o valor do painel possuir dados não encontrados (caso de exceção) ou não definidos (else vazios), omitimos a chave do painel em vez de atribuir uma lista vazia sem propriedades.
- Adicionalmente, quando há erro de formatação (ex: json parse de erro), os painéis mantêm coerência e preservam a chave em vez de falhar.

Como essa normalização de output afeta como o cliente/testador lê a lista de alertas, os testes `tests/test_esforco_resultado.py`, `tests/test_falso_rompimento.py`, `tests/test_radar_anomalias_spread.py` e `tests/test_radar_divergencia_volume.py` foram atualizados para buscar os itens em `snap["paineis"]["nome_do_painel"]["alertas"]` (se a resposta for uma lista originalmente) em vez da própria chave base.
