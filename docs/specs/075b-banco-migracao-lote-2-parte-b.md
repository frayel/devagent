---
id: 075b
titulo: Banco · migração dos painéis para snapshots (segundo lote, parte b)
status: ready
esforco: P
gaveta: saúde técnica
aceite: tests/test_aceite_migracao_snapshots.py
tabelas_legadas: falso_rompimento_cache, fator_mola_cache, fator_peso_pesado_cache, forca_relativa_cache, liquidez_abertura_cache, mare_cache
---

## Problema
Continuação da spec 073 (ADR 007). Enquanto um painel guardar dados na tabela própria do SQLite, ele aparece vazio a cada reinício do Render. Esta fatia migra 6 painéis para `snapshots_paineis`.

Nasceu da divisão da spec 075 depois da tentativa fechada na issue #404: a sessão tentou remover as funções `save_*`/`get_latest_*` e as dataclasses de 13 painéis de uma vez, o que obrigava a reescrever dezenas de testes, e perdeu o trabalho. Esta fatia segue o caminho que deu certo na 074.

## Comportamento esperado
Painéis desta fatia: `falso_rompimento`, `fator_mola`, `fator_peso_pesado`, `forca_relativa`, `liquidez_abertura`, `mare`.

**Como fazer (padrão da 074).** Mantenha as funções públicas de `app/database.py` e as dataclasses com a mesma assinatura: coletores, serviços e testes continuam chamando `save_<painel>_data(...)` e `get_latest_<painel>_data()`. Troque só o corpo delas:
- a gravação monta o `payload` a partir da dataclass (`data.__dict__`, com `timestamp` em ISO) e chama `gravar_snapshot("<chave>", data_utc, "ao_vivo", data.fonte, payload)`;
- a leitura chama `ler_snapshot("<chave>")` e reconstrói a dataclass (com `timestamp` de volta para `datetime`);
- a `<chave>` é a do painel no `/api/snapshot`;
- apague do `init_db` o `CREATE TABLE` e o `CREATE INDEX` da tabela antiga.

Veja `save_coesao_data` e `get_latest_coesao_data` em `app/database.py` como modelo. Não renomeie nem remova funções públicas, dataclasses ou imports nesta spec.

## Mapa do que cada tabela toca
Gerado a partir da `main` em 22/10. Confira antes de começar; se algum painel foi podado, deixe-o de fora.

- `falso_rompimento_cache`: `FalsoRompimentoData`, `get_latest_falso_rompimento_data`, `save_falso_rompimento_data`. Usado em `app/collectors/falso_rompimento.py`, `app/main.py`, `tests/test_falso_rompimento.py`.
- `fator_mola_cache`: `FatorMolaData`, `get_latest_fator_mola_data`, `save_fator_mola_data`. Usado em `app/collectors/fator_mola.py`.
- `fator_peso_pesado_cache`: `FatorPesoPesadoData`, `get_latest_fator_peso_pesado_data`, `save_fator_peso_pesado_data`. Usado em `app/collectors/fator_peso_pesado.py`, `app/main.py`, `tests/test_fator_peso_pesado.py`.
- `forca_relativa_cache`: `ForcaRelativaData`, `get_latest_forca_relativa_data`, `save_forca_relativa_data`. Usado em `app/collectors/forca_relativa.py`, `app/main.py`, `app/services/forca_relativa.py`, `tests/test_forca_relativa.py`.
- `liquidez_abertura_cache`: `LiquidezAberturaData`, `get_latest_liquidez_abertura_data`, `save_liquidez_abertura_data`. Usado em `app/collectors/radar_liquidez_abertura.py`, `app/main.py`, `tests/test_radar_liquidez_abertura.py`.
- `mare_cache`: `MareData`, `get_latest_mare_data`, `save_mare_data`. Usado em `app/collectors/mare.py`, `app/main.py`, `app/services/mare.py`, `tests/test_mare.py`.

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
