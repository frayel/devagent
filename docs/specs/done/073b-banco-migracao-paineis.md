---
id: 073b
titulo: Banco · migração do Ibovespa, maiores altas/baixas e séries para a nova camada
status: done
esforco: G
gaveta: saúde técnica
---

## Problema
Segunda metade da implementação da ADR 007. Com a camada genérica de banco pronta (spec 073a), é hora de migrar os primeiros painéis para a tabela `snapshots_paineis`. Os painéis escolhidos são os vigiados pelo auditor, as séries e instrumentação.

Depende da 073a.

## Comportamento esperado
- Migrados nesta fatia: `ibovespa_cache`, `highlights_cache`, `historico_diario_cache` (vira `series_diarias`), `instrumentacao_coleta_tempo` e `instrumentacao_coleta_vazia`. As funções de leitura desses painéis leem de `snapshots_paineis` via `app/banco.py`; as tabelas antigas desses cinco somem de `app/database.py`.
- Nesta fatia, `data_referencia` é a data BRT da coleta e `estado` é sempre `ao_vivo`. O cálculo correto do pregão vem na spec 077.
- Ao subir, a página inicial lê o último snapshot dos painéis migrados antes de qualquer coleta e mostra "Coletado em dd/mm HH:MM".
- A coleta de séries diárias passa a pedir à fonte só os pregões que faltam em `series_diarias`.

## Fontes de dados
A coleta de séries diárias passa a pedir à fonte só os pregões que faltam em `series_diarias`.

## Cálculos
- `payload` é JSON serializado com `default=str` para datas; a leitura devolve dicionários (ou objetos dataclass) iguais aos que o painel já usava, para os templates e services não mudarem muito.

## Critérios de aceite
- [ ] Com o banco já populado por um fixture e a coleta desligada (`COLETA_AUTOMATICA=0`), `GET /` mostra o Ibovespa e as maiores altas e baixas do fixture na primeira requisição.
- [ ] Uma segunda coleta de série diária, com os pregões já gravados, não faz requisição HTTP para eles (respx conta as chamadas).
- [ ] Todos os testes continuam passando.
- [ ] `/api/snapshot` mantém o contrato de `auditoria/README.md` para Ibovespa e maiores altas e baixas.

## Invariantes de produção
- Logo após um reinício do serviço, com o mercado aberto ou fechado, o `/api/snapshot` traz o Ibovespa com `coletado_em` anterior ao reinício (o dado veio do banco, não de uma coleta nova).

## Fora do escopo
- Migrar os demais painéis (specs 074 a 076).
- Congelamento e data de referência por pregão (spec 077).
- Seletor de pregões anteriores (spec 078).
