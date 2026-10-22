---
id: 075a
titulo: Banco · migração dos painéis para snapshots (segundo lote, parte a)
status: done
esforco: P
gaveta: saúde técnica
aceite: tests/test_aceite_migracao_snapshots.py
tabelas_legadas: divergencia_ibov_dolar_cache, dolar_correlation_cache, escudo_quedas_cache, esforco_resultado_cache, exaustao_queda_cache, exaustao_tendencia_cache, faca_caindo_cache
---

## Problema
Continuação da spec 073 (ADR 007). Enquanto um painel guardar dados na tabela própria do SQLite, ele aparece vazio a cada reinício do Render. Esta fatia migra 7 painéis para `snapshots_paineis`.

Nasceu da divisão da spec 075 depois da tentativa fechada na issue #404: a sessão tentou remover as funções `save_*`/`get_latest_*` e as dataclasses de 13 painéis de uma vez, o que obrigava a reescrever dezenas de testes, e perdeu o trabalho. Esta fatia segue o caminho que deu certo na 074.

## Comportamento esperado
Painéis desta fatia: `divergencia_ibov_dolar`, `dolar_correlation`, `escudo_quedas`, `esforco_resultado`, `exaustao_queda`, `exaustao_tendencia`, `faca_caindo`.

**Como fazer (padrão da 074).** Mantenha as funções públicas de `app/database.py` e as dataclasses com a mesma assinatura: coletores, serviços e testes continuam chamando `save_<painel>_data(...)` e `get_latest_<painel>_data()`. Troque só o corpo delas:
- a gravação monta o `payload` a partir da dataclass (`data.__dict__`, com `timestamp` em ISO) e chama `gravar_snapshot("<chave>", data_utc, "ao_vivo", data.fonte, payload)`;
- a leitura chama `ler_snapshot("<chave>")` e reconstrói a dataclass (com `timestamp` de volta para `datetime`);
- a `<chave>` é a do painel no `/api/snapshot`;
- apague do `init_db` o `CREATE TABLE` e o `CREATE INDEX` da tabela antiga.

Veja `save_coesao_data` e `get_latest_coesao_data` em `app/database.py` como modelo. Não renomeie nem remova funções públicas, dataclasses ou imports nesta spec.

## Mapa do que cada tabela toca
Gerado a partir da `main` em 22/10. Confira antes de começar; se algum painel foi podado, deixe-o de fora.

- `divergencia_ibov_dolar_cache`: `get_divergencia_ibov_dolar`, `save_divergencia_ibov_dolar`. Usado em `app/collectors/divergencia_ibov_dolar.py`, `app/main.py`, `tests/test_divergencia_ibov_dolar.py`.
- `dolar_correlation_cache`: `DolarCorrelationData`, `get_latest_dolar_correlation_data`, `save_dolar_correlation_data`. Usado em `app/collectors/dolar_correlation.py`, `app/main.py`, `app/services/dolar_correlation.py`, `tests/test_dolar_correlation.py`.
- `escudo_quedas_cache`: `EscudoQuedasData`, `get_latest_escudo_quedas_data`, `save_escudo_quedas_data`. Usado em `app/collectors/escudo_quedas.py`, `app/main.py`, `app/services/escudo_quedas.py`.
- `esforco_resultado_cache`: `EsforcoResultadoData`, `get_latest_esforco_resultado_data`, `save_esforco_resultado_data`. Usado em `app/collectors/esforco_resultado.py`, `app/main.py`, `tests/test_esforco_resultado.py`.
- `exaustao_queda_cache`: `ExaustaoQuedaData`, `get_latest_exaustao_queda_data`, `save_exaustao_queda_data`. Usado em `app/collectors/exaustao_queda.py`, `app/main.py`.
- `exaustao_tendencia_cache`: `ExaustaoTendenciaData`, `get_latest_exaustao_tendencia_data`, `save_exaustao_tendencia_data`. Usado em `app/collectors/exaustao_tendencia.py`, `app/main.py`.
- `faca_caindo_cache`: `FacaCaindoData`, `get_latest_faca_caindo_data`, `save_faca_caindo_data`. Usado em `app/collectors/faca_caindo.py`, `app/main.py`, `app/services/faca_caindo.py`, `tests/test_faca_caindo.py`.

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
