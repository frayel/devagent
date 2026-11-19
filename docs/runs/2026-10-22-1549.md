# Entrega da Spec 076a (Banco · migração dos painéis para snapshots - lote 3, parte a)

## Decisões
- Substituição das antigas interações com SQLite via `save_..._data` e `get_latest_..._data` para funções que utilizam `gravar_snapshot` e `ler_snapshot`.
- Painéis migrados (sem novas fontes de dados ou cálculos, mantendo os comportamentos esperados e apenas alterando o back-end de persistência temporária local para `snapshots_paineis`):
  - `motores_indice`
  - `radar_absorcao_cruzada`
  - `radar_congestionamento`
  - `radar_divergencia_volume`
  - `radar_inflexao`
  - `radar_short_squeeze`
  - `relogio_volatilidade`
- Foi criado o `save_relogio_volatilidade_data` já que o `relogio_volatilidade` antes fazia chamadas brutas ao SQLite. O seu collector respectivo (`app/collectors/relogio_volatilidade.py`) e de `radar_inflexao` (`app/collectors/radar_inflexao.py`) foram adaptados.
- Testes foram consertados onde testavam interações diretas e a tabela `relogio_volatilidade_cache` agora foi abstraída com sucesso.
- O contador de manutenção não foi modificado, conforme requisitado pelas regras do repositório para specs de gaveta de "saúde técnica".

## Testes
`make verify` e `make smoke` passaram com sucesso.
