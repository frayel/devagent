---
id: 076a
titulo: Banco · migração dos painéis para snapshots (terceiro lote, parte a)
status: done
esforco: P
gaveta: saúde técnica
aceite: tests/test_aceite_migracao_snapshots.py
tabelas_legadas: motores_indice_cache, radar_absorcao_cruzada_cache, radar_congestionamento_cache, radar_divergencia_volume_cache, radar_inflexao_cache, radar_short_squeeze_cache, relogio_volatilidade_cache
---

## Problema
Continuação da spec 073 (ADR 007). Enquanto um painel guardar dados na tabela própria do SQLite, ele aparece vazio a cada reinício do Render. Esta fatia migra 7 painéis para `snapshots_paineis`.

Nasceu da divisão da spec 076 depois da tentativa fechada na issue #404: a sessão tentou remover as funções `save_*`/`get_latest_*` e as dataclasses de 13 painéis de uma vez, o que obrigava a reescrever dezenas de testes, e perdeu o trabalho. Esta fatia segue o caminho que deu certo na 074.

## Comportamento esperado
Painéis desta fatia: `motores_indice`, `radar_absorcao_cruzada`, `radar_congestionamento`, `radar_divergencia_volume`, `radar_inflexao`, `radar_short_squeeze`, `relogio_volatilidade`.

**Como fazer (padrão da 074).** Mantenha as funções públicas de `app/database.py` e as dataclasses com a mesma assinatura: coletores, serviços e testes continuam chamando `save_<painel>_data(...)` e `get_latest_<painel>_data()`. Troque só o corpo delas:
- a gravação monta o `payload` a partir da dataclass (`data.__dict__`, com `timestamp` em ISO) e chama `gravar_snapshot("<chave>", data_utc, "ao_vivo", data.fonte, payload)`;
- a leitura chama `ler_snapshot("<chave>")` e reconstrói a dataclass (com `timestamp` de volta para `datetime`);
- a `<chave>` é a do painel no `/api/snapshot`;
- apague do `init_db` o `CREATE TABLE` e o `CREATE INDEX` da tabela antiga.

Veja `save_coesao_data` e `get_latest_coesao_data` em `app/database.py` como modelo. Não renomeie nem remova funções públicas, dataclasses ou imports nesta spec.

## Mapa do que cada tabela toca
Gerado a partir da `main` em 22/10. Confira antes de começar; se algum painel foi podado, deixe-o de fora.

- `motores_indice_cache`: `MotoresIndiceData`, `get_latest_motores_indice_data`, `save_motores_indice_data`. Usado em `app/collectors/motores_indice.py`, `app/main.py`.
- `radar_absorcao_cruzada_cache`: `RadarAbsorcaoCruzadaData`, `get_latest_radar_absorcao_cruzada_data`, `save_radar_absorcao_cruzada_data`. Usado em `app/collectors/radar_absorcao_cruzada.py`, `app/main.py`, `tests/test_radar_absorcao_cruzada.py`.
- `radar_congestionamento_cache`: `RadarCongestionamentoData`, `get_latest_radar_congestionamento_data`, `save_radar_congestionamento_data`. Usado em `app/collectors/radar_congestionamento.py`, `app/main.py`, `tests/test_radar_congestionamento.py`.
- `radar_divergencia_volume_cache`: `RadarDivergenciaVolumeData`, `get_latest_radar_divergencia_volume_data`, `save_radar_divergencia_volume_data`. Usado em `app/collectors/radar_divergencia_volume.py`, `app/main.py`, `tests/test_radar_divergencia_volume.py`.
- `radar_inflexao_cache`: `RadarInflexaoData`, `get_latest_radar_inflexao_data`, `save_radar_inflexao_data`. Usado em `app/collectors/radar_inflexao.py`, `app/main.py`, `tests/test_radar_inflexao.py`.
- `radar_short_squeeze_cache`: `RadarShortSqueezeData`, `get_latest_radar_short_squeeze_data`, `save_radar_short_squeeze_data`. Usado em `app/collectors/radar_short_squeeze.py`, `app/main.py`, `app/services/radar_short_squeeze.py`, `tests/test_radar_short_squeeze.py`.
- `relogio_volatilidade_cache`: `RelogioVolatilidadeData`, `get_latest_relogio_volatilidade_data`. Usado em `app/collectors/relogio_volatilidade.py`, `app/main.py`, `tests/test_relogio_volatilidade.py`.

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
