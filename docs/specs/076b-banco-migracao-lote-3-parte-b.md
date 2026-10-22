---
id: 076b
titulo: Banco · migração dos painéis para snapshots (terceiro lote, parte b)
status: ready
esforco: M
gaveta: saúde técnica
aceite: tests/test_aceite_migracao_snapshots.py
tabelas_legadas: rotacao_capital_cache, scanner_capitulacao_cache, sensibilidade_juros_cache, sobrevivencia_semanal_cache, variacao_subita_cache, volatilidade_silenciosa_cache, volume_alerts_cache
---

## Problema
Continuação da spec 073 (ADR 007). Enquanto um painel guardar dados na tabela própria do SQLite, ele aparece vazio a cada reinício do Render. Esta fatia migra 7 painéis para `snapshots_paineis`.

Nasceu da divisão da spec 076 depois da tentativa fechada na issue #404: a sessão tentou remover as funções `save_*`/`get_latest_*` e as dataclasses de 13 painéis de uma vez, o que obrigava a reescrever dezenas de testes, e perdeu o trabalho. Esta fatia segue o caminho que deu certo na 074.

## Comportamento esperado
Painéis desta fatia: `rotacao_capital`, `scanner_capitulacao`, `sensibilidade_juros`, `sobrevivencia_semanal`, `variacao_subita`, `volatilidade_silenciosa`, `volume_alerts`.

**Como fazer (padrão da 074).** Mantenha as funções públicas de `app/database.py` e as dataclasses com a mesma assinatura: coletores, serviços e testes continuam chamando `save_<painel>_data(...)` e `get_latest_<painel>_data()`. Troque só o corpo delas:
- a gravação monta o `payload` a partir da dataclass (`data.__dict__`, com `timestamp` em ISO) e chama `gravar_snapshot("<chave>", data_utc, "ao_vivo", data.fonte, payload)`;
- a leitura chama `ler_snapshot("<chave>")` e reconstrói a dataclass (com `timestamp` de volta para `datetime`);
- a `<chave>` é a do painel no `/api/snapshot`;
- apague do `init_db` o `CREATE TABLE` e o `CREATE INDEX` da tabela antiga.

Veja `save_coesao_data` e `get_latest_coesao_data` em `app/database.py` como modelo. Não renomeie nem remova funções públicas, dataclasses ou imports nesta spec.

Fechada esta fatia, nenhuma tabela `*_cache` de painel resta no app. Por isso ela também:
- deixa o `DB_PATH`/`DATABASE_PATH` valendo só para testes e desenvolvimento local;
- atualiza `PRODUTO.md` (seções 2, 3 e 10), `docs/context/arquitetura.md`, `docs/context/operacao.md` e `docs/skills/criar-coletor.md` para descrever o Postgres como banco de produção e a camada genérica como o jeito de gravar painel novo, com exemplo de `gravar_snapshot` e `ler_snapshot`;
- mantém o `make smoke` subindo sem `DATABASE_URL` (SQLite local).

## Mapa do que cada tabela toca
Gerado a partir da `main` em 22/10. Confira antes de começar; se algum painel foi podado, deixe-o de fora.

- `rotacao_capital_cache`: `RotacaoCapitalData`, `get_latest_rotacao_capital_data`, `save_rotacao_capital_data`. Usado em `app/collectors/rotacao_capital.py`, `app/main.py`, `app/services/rotacao_capital.py`, `tests/test_gauge.py`, `tests/test_rotacao_capital.py`.
- `scanner_capitulacao_cache`: `ScannerCapitulacaoData`, `get_latest_scanner_capitulacao_data`, `save_scanner_capitulacao_data`. Usado em `app/collectors/scanner_capitulacao.py`, `app/services/scanner_capitulacao.py`.
- `sensibilidade_juros_cache`: `SensibilidadeJurosData`, `get_latest_sensibilidade_juros_data`, `save_sensibilidade_juros_data`. Usado em `app/collectors/sensibilidade_juros.py`, `app/main.py`, `app/services/sensibilidade_juros.py`.
- `sobrevivencia_semanal_cache`: `SobrevivenciaSemanalData`, `get_latest_sobrevivencia_semanal_data`, `save_sobrevivencia_semanal_data`. Usado em `app/collectors/sobrevivencia_semanal.py`, `app/main.py`, `app/services/sobrevivencia_semanal.py`, `tests/test_database_tabelas.py`.
- `variacao_subita_cache`: `VariacaoSubitaData`, `get_latest_variacao_subita_data`, `save_variacao_subita_data`. Usado em `app/collectors/variacao_subita.py`, `app/main.py`, `app/services/variacao_subita.py`, `tests/test_variacao_subita.py`.
- `volatilidade_silenciosa_cache`: `VolatilidadeSilenciosaData`, `get_latest_volatilidade_silenciosa_data`, `save_volatilidade_silenciosa_data`. Usado em `app/collectors/volatilidade_silenciosa.py`, `app/main.py`, `app/services/volatilidade_silenciosa.py`, `tests/test_volatilidade_silenciosa_collector.py`.
- `volume_alerts_cache`: `VolumeAlertsData`, `get_latest_volume_alerts_data`, `save_volume_alerts_data`. Usado em `app/collectors/volume_alerts.py`, `app/main.py`, `app/services/volume_alerts.py`, `tests/test_volume_alerts_collector.py`, `tests/test_volume_alerts_service.py`.

## Fontes de dados
Nenhuma nova.

## Cálculos
Nenhum novo. O `payload` guarda exatamente a estrutura que o painel já produzia.

## Critérios de aceite
- [ ] `tests/test_aceite_migracao_snapshots.py` passa com esta spec `done`: nenhuma tabela de `tabelas_legadas` aparece em `app/`.
- [ ] Para cada painel da lista, um teste grava pela função `save_*`, reinicia a camada (nova conexão no mesmo arquivo SQLite temporário) e confere que o `get_latest_*` devolve os mesmos números.
- [ ] Os testes existentes desses painéis passam sem mudar as asserções.

## Invariantes de produção
- Após um reinício do serviço, os painéis desta fatia aparecem na primeira carga da página, com horário de coleta anterior ao reinício.

## Fora do escopo
- Remover ou renomear as funções `save_*`/`get_latest_*` e as dataclasses. Se um dia valer a pena, é outra spec, painel a painel.
- Mudar cálculos ou a forma de exibição dos painéis.
- Congelamento e histórico (specs 077 e 078).
