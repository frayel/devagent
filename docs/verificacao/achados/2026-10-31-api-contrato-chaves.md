---
id: 2026-10-31-api-contrato-chaves
severidade: media
painel: app/main.py (Endpoint /api/snapshot)
status: aberto
visto_em: 2026-10-31T09:50:00-03:00
pr: 646
---

# Snapshot omitindo chaves contratuais obrigatórias de data/fonte em falhas do banco

## O que acontece
Durante a auditoria (make audit), identificou-se que o endpoint `/api/snapshot` não expõe as propriedades contratuais (`fonte` e `coletado_em`) exigidas em painéis como `forca_relativa`, `escudo_quedas`, `concentracao_vendedora`, `concentracao_setorial`, `apetite_risco`, `rotacao_capital`, `faca_caindo`, `concentracao_ordens`, e `relogio_volatilidade`. Isso ocorre quando os resultados não existem ou há falhas silenciosas na coleta e a API responde com dicionário omitindo essas chaves, o que viola o contrato esperado que o front-end e o teste `api.contrato_chaves` aguardam.
Comando que mostra: `PORT=8000 make audit ARGS="--url http://127.0.0.1:8000 --navegador"`

## O que deveria acontecer
Conforme diretriz ("The /api/snapshot endpoint contract requires that all panel entries within the paineis dictionary be objects and explicitly expose the keys fonte and coletado_em, even when their internal alerts list is empty or fails to parse"), o dicionário interno do painel jamais deve omitir a chave `fonte` ou `coletado_em`.

## Evidência
Saída do comando `make audit`:
`api.contrato_chaves` Painéis omitindo fonte ou coletado_em: `'forca_relativa' não possui 'fonte'; 'forca_relativa' não possui 'coletado_em'; 'escudo_quedas' não possui 'fonte'; 'escudo_quedas' não possui 'coletado_em'; 'concentracao_vendedora' não possui 'fonte'; ...`

## Como reproduzir
1. Inicie o servidor localmente (e verifique que as variáveis ou tabela para esses painéis não estejam prontas/estejam falhando).
2. Execute o script de auditoria `make audit ARGS="--url http://127.0.0.1:8000 --navegador"`.
3. Verifique os erros no Console ou na saída do report (falha em `api.contrato_chaves`).
