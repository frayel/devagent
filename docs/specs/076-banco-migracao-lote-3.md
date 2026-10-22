---
id: 076
titulo: Banco · migração dos painéis para snapshots (último lote e remoção do SQLite em produção)
status: draft
esforco: M
gaveta: saúde técnica
---

> **Dividida em 076a e 076b** (22/10, issue #404). Esta versão fica como registro; a fila segue pelas partes.

## Problema
Continuação da spec 073 (ADR 007). Enquanto um painel guardar dados na tabela própria do SQLite, ele aparece vazio a cada reinício do Render. Esta fatia migra o último lote de painéis para `snapshots_paineis` e tira o SQLite do caminho de produção.

## Comportamento esperado
Painéis desta fatia (só os que ainda existirem na `main`; os removidos por poda ficam de fora):

- `motores_indice_cache`
- `radar_absorcao_cruzada_cache`
- `radar_congestionamento_cache`
- `radar_divergencia_volume_cache`
- `radar_inflexao_cache`
- `radar_short_squeeze_cache`
- `relogio_volatilidade_cache`
- `rotacao_capital_cache`
- `scanner_capitulacao_cache`
- `sensibilidade_juros_cache`
- `sobrevivencia_semanal_cache`
- `variacao_subita_cache`
- `volatilidade_silenciosa_cache`
- `volume_alerts_cache`

Para cada um:
- A gravação passa a usar `gravar_snapshot` e a leitura, `ler_snapshot`, com a chave igual à do painel no `/api/snapshot`.
- Séries diárias de ativos passam a vir de `series_diarias` (spec 073) quando o coletor as usa, sem baixar de novo o que já está gravado.
- A tabela antiga, a função de gravação e a de leitura específicas são removidas de `app/database.py`.
- O template e o `/api/snapshot` recebem os mesmos dados de antes.
- Concluído este lote, `app/database.py` deixa de criar ou ler qualquer tabela `*_cache`, e o `DB_PATH`/`DATABASE_PATH` passa a valer só para testes e desenvolvimento local.
- O `PRODUTO.md` (seções 2, 3 e 10), `docs/context/arquitetura.md`, `docs/context/operacao.md` e `docs/skills/criar-coletor.md` passam a descrever o Postgres como banco de produção e a camada genérica como o jeito de gravar painel novo.
- O `make smoke` continua subindo sem `DATABASE_URL` (SQLite local).

## Fontes de dados
Nenhuma nova.

## Cálculos
Nenhum novo. O `payload` guarda exatamente a estrutura que o painel já produzia.

## Critérios de aceite
- [ ] Para cada painel da lista, um teste grava um payload de fixture, reinicia a camada (nova conexão SQLite no mesmo arquivo temporário) e confere que o painel aparece na página com os mesmos números.
- [ ] Os testes existentes desses painéis passam sem mudar as asserções sobre o que é exibido.
- [ ] `app/database.py` não cria mais nenhuma das tabelas da lista.
- [ ] `grep -rn "_cache" app/` não encontra nenhuma criação ou consulta de tabela de painel.
- [ ] `docs/skills/criar-coletor.md` mostra um exemplo com `gravar_snapshot` e `ler_snapshot`.

## Invariantes de produção
- Após um reinício do serviço, os painéis desta fatia aparecem na primeira carga da página, com horário de coleta anterior ao reinício.

## Fora do escopo
- Mudar cálculos ou a forma de exibição dos painéis.
- Congelamento e histórico (specs 077 e 078).
