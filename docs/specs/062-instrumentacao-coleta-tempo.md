# Spec 062: Instrumentação de Tempo de Coleta
gaveta: saúde técnica

## Objetivo
Registrar o tempo gasto na execução do coletor de cada painel, armazenando no banco de dados para embasar decisões futuras de poda por custo.

## Critérios de Aceite
- O `app/agendador.py` mede o tempo de execução de `coletor.collect_and_save()` para cada painel.
- O tempo (em segundos) é salvo na tabela `instrumentacao_coleta_tempo` usando uma nova função no `app/database.py`.
- O comportamento visível e os dados armazenados de cada coletor não são alterados.
