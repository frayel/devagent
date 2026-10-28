---
id: 122
titulo: Reduzir a transferência de rede do Postgres (Neon)
status: done
esforco: M
gaveta: saúde técnica
aceite: tests/test_aceite_122.py
revisada: 2026-10-27
---

## Problema
O Neon registrou 4,09 GB de transferência de rede em poucos dias. Quase todo esse volume vem da leitura da tabela `series_diarias`:

1. `get_historico_diario` (`app/database.py`) recebe `range_str` e `max_age_minutes`, mas ignora os dois. Sempre lê dois anos (`hoje - 730 dias`) de cada ticker pedido. Um coletor que pede `1d` traz centenas de linhas JSONB por ativo, a cada rodada do agendador (15 min no pregão, 2 h fora dele).
2. Como `max_age_minutes` é ignorado, o cache nunca expira: qualquer série gravada uma vez é devolvida para sempre, mesmo que esteja velha.
3. `calcular_consultor` (`app/consultor/calculador.py`) lê dois anos da carteira inteira do Ibovespa (cerca de 85 ativos) **antes** de consultar o cache em memória, porque a versão do cache é calculada a partir dos dados lidos. Cada visita à aba de recomendações e cada chamada a `/api/consultor` paga a leitura completa.
4. `banco.diagnostico()` roda `pg_database_size` e conta tabelas a cada carregamento de `/sistema`.

## Comportamento esperado
1. `get_historico_diario` converte `range_str` (`1d`, `5d`, `1mo`, `3mo`, `6mo`, `1y`, `2y`, `ytd`, `max`) na data de início e só lê esse intervalo. Valor desconhecido usa dois anos e registra aviso.
2. `get_historico_diario` respeita `max_age_minutes`: ticker cuja barra mais recente foi gravada (`criado_em`) há mais que o limite não entra no resultado, para que o coletor busque de novo na fonte. Fora do pregão, barras de pregões já fechados não expiram (os dados estão congelados).
3. Nova função `banco.versao_series(tickers) -> str`, que lê só `MAX(criado_em)` de `series_diarias` para os tickers (uma linha). `calcular_consultor` monta a versão com ela e só chama `get_historico_diario` quando a versão mudou ou o cache em memória passou de 5 min. Mesma ideia para as opiniões, se houver leitura pesada.
4. Cache em memória do processo para as séries de pregões fechados (chave: ticker e intervalo de datas), invalidado quando `gravar_serie` grava aquele ticker. Duas chamadas seguidas com o mesmo pedido fazem no máximo uma consulta ao banco.
5. `banco.diagnostico()` guarda o resultado por 5 min.

## Fontes de dados
Nenhuma nova. Tabelas `series_diarias` e `snapshots_paineis`.

## Critérios de aceite
- [ ] `get_historico_diario([...], "1d", ...)` consulta o banco com data de início no máximo 5 dias corridos antes de hoje (teste com cursor espionado verificando o parâmetro `inicio`).
- [ ] `get_historico_diario` com `max_age_minutes=15` não devolve ticker cuja última gravação tem 20 min durante o pregão; devolve fora do pregão.
- [ ] Duas chamadas seguidas a `calcular_consultor()` sem gravação nova entre elas fazem uma única leitura de `series_diarias` com barras (a segunda só lê `versao_series`).
- [ ] Duas chamadas iguais a `get_historico_diario` sem gravação entre elas geram uma consulta ao banco; após `gravar_serie` do ticker, a terceira consulta de novo.
- [ ] Duas chamadas a `diagnostico()` em menos de 5 min geram uma consulta.
- [ ] Testes existentes de `test_banco.py`, `test_consultor_armazenamento.py` e dos coletores continuam verdes.
- Esta spec tocará `app/database.py`, `app/banco.py`, `app/consultor/calculador.py`, `tests/test_banco.py` e um novo `tests/test_aceite_122.py`.

## Invariantes de produção
- Uma rodada de coleta sem visitas à página lê de `series_diarias` no máximo o intervalo pedido por cada coletor.
- Abrir a aba de recomendações duas vezes seguidas não relê as séries.

## Fora do escopo
- Mudar o esquema de `series_diarias` (uma linha por ticker e dia continua).
- Mudar o intervalo do agendador.
- Trocar o plano do Neon.
