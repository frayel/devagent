---
id: 075
titulo: Banco · migração dos painéis para snapshots (segundo lote)
status: ready
esforco: M
gaveta: saúde técnica
---

## Problema
Continuação da spec 073 (ADR 007). Enquanto um painel guardar dados na tabela própria do SQLite, ele aparece vazio a cada reinício do Render. Esta fatia migra o segundo lote de painéis para `snapshots_paineis`.

## Comportamento esperado
Painéis desta fatia (só os que ainda existirem na `main`; os removidos por poda ficam de fora):

- `divergencia_ibov_dolar_cache`
- `dolar_correlation_cache`
- `escudo_quedas_cache`
- `esforco_resultado_cache`
- `exaustao_queda_cache`
- `exaustao_tendencia_cache`
- `faca_caindo_cache`
- `falso_rompimento_cache`
- `fator_mola_cache`
- `fator_peso_pesado_cache`
- `forca_relativa_cache`
- `liquidez_abertura_cache`
- `mare_cache`

Para cada um:
- A gravação passa a usar `gravar_snapshot` e a leitura, `ler_snapshot`, com a chave igual à do painel no `/api/snapshot`.
- Séries diárias de ativos passam a vir de `series_diarias` (spec 073) quando o coletor as usa, sem baixar de novo o que já está gravado.
- A tabela antiga, a função de gravação e a de leitura específicas são removidas de `app/database.py`.
- O template e o `/api/snapshot` recebem os mesmos dados de antes.

## Fontes de dados
Nenhuma nova.

## Cálculos
Nenhum novo. O `payload` guarda exatamente a estrutura que o painel já produzia.

## Critérios de aceite
- [ ] Para cada painel da lista, um teste grava um payload de fixture, reinicia a camada (nova conexão SQLite no mesmo arquivo temporário) e confere que o painel aparece na página com os mesmos números.
- [ ] Os testes existentes desses painéis passam sem mudar as asserções sobre o que é exibido.
- [ ] `app/database.py` não cria mais nenhuma das tabelas da lista.

## Invariantes de produção
- Após um reinício do serviço, os painéis desta fatia aparecem na primeira carga da página, com horário de coleta anterior ao reinício.

## Fora do escopo
- Mudar cálculos ou a forma de exibição dos painéis.
- Congelamento e histórico (specs 077 e 078).
