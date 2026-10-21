---
id: 073
titulo: Banco · camada única com Postgres e primeiros painéis migrados
status: draft
esforco: G
gaveta: saúde técnica
---

## Problema
Pedido do dono do produto (ADR 007): ao acordar, o Render mostra os painéis vazios e eles vão aparecendo aos poucos, porque o SQLite renasce vazio. Esta primeira fatia cria a camada de banco única, a tabela genérica de snapshots e migra os painéis que o auditor vigia (Ibovespa e maiores altas e baixas), a série diária compartilhada e a instrumentação de coleta.

Depende da spec 072 (o `app/consultor/armazenamento.py` já fala com o Postgres). Se não couber em um PR de ~400 linhas, divida em 073a (camada e tabelas) e 073b (migração dos painéis desta fatia).

## Comportamento esperado
- `app/banco.py`: conexão com Postgres quando `DATABASE_URL` existe; SQLite caso contrário. Mesma interface para os dois, com:
  - `gravar_snapshot(painel, data_referencia, estado, fonte, payload)` (upsert);
  - `ler_snapshot(painel, data_referencia=None)` (sem data: o mais recente);
  - `listar_datas(painel, limite)`;
  - `gravar_serie(ticker, barras)` e `ler_serie(ticker, inicio, fim)`;
  - transação explícita para gravações agrupadas.
- Tabelas `snapshots_paineis` e `series_diarias` conforme o ADR 007, criadas por uma função idempotente chamada ao subir.
- `app/consultor/armazenamento.py` passa a usar `app/banco.py`, sem mudar o comportamento das specs 068 a 072.
- Migrados nesta fatia: `ibovespa_cache`, `highlights_cache`, `historico_diario_cache` (vira `series_diarias`), `instrumentacao_coleta_tempo` e `instrumentacao_coleta_vazia`. As funções de leitura desses painéis leem de `snapshots_paineis`; as tabelas antigas desses cinco somem.
- Nesta fatia, `data_referencia` é a data BRT da coleta e `estado` é sempre `ao_vivo`. O cálculo correto do pregão vem na spec 077.
- Ao subir, a página inicial lê o último snapshot dos painéis migrados antes de qualquer coleta e mostra "Coletado em dd/mm HH:MM".
- Em produção (`RENDER` definido) sem `DATABASE_URL`: aviso no topo de todas as páginas "Banco persistente não configurado: dados se perdem ao reiniciar" e o mesmo texto em `GET /api/coleta`. A aplicação sobe normalmente.
- Postgres inacessível ao subir: até 2 tentativas com 10 s de timeout; depois, SQLite com o mesmo aviso. Nenhuma página responde 500 por causa do banco.
- `psycopg[binary]` já está em `requirements.txt` desde a spec 072; o pool tem no máximo 3 conexões.

## Fontes de dados
Nenhuma nova. A coleta de séries diárias passa a pedir à fonte só os pregões que faltam em `series_diarias`.

## Cálculos
- Fora de `app/banco.py`, nenhum SQL específico de um dialeto. O upsert e a tradução de parâmetros (`?` no SQLite, `%s` no Postgres) ficam dentro da camada.
- `payload` é JSON serializado com `default=str` para datas; a leitura devolve dicionários iguais aos que o painel já usava, para os templates não mudarem.

## Critérios de aceite
- [ ] Os testes da camada rodam contra SQLite em memória e cobrem upsert, leitura do mais recente, leitura por data e listagem de datas.
- [ ] Um teste de contrato garante que `app/banco.py` gera, para Postgres, o SQL esperado de upsert (inspeção da string, sem banco real).
- [ ] Com o banco já populado por um fixture e a coleta desligada (`COLETA_AUTOMATICA=0`), `GET /` mostra o Ibovespa e as maiores altas e baixas do fixture na primeira requisição.
- [ ] Uma segunda coleta de série diária, com os pregões já gravados, não faz requisição HTTP para eles (respx conta as chamadas).
- [ ] Com `RENDER=1` e sem `DATABASE_URL`, a página contém o aviso de banco não persistente e responde 200.
- [ ] Com `DATABASE_URL` apontando para um host inválido, a aplicação sobe, usa SQLite e mostra o aviso.
- [ ] Todos os testes das specs 068 a 072 continuam passando.
- [ ] `/api/snapshot` mantém o contrato de `auditoria/README.md` para Ibovespa e maiores altas e baixas.

## Invariantes de produção
- Logo após um reinício do serviço, com o mercado aberto ou fechado, o `/api/snapshot` traz o Ibovespa com `coletado_em` anterior ao reinício (o dado veio do banco, não de uma coleta nova).
- `GET /api/coleta` informa `banco: "postgres"` em produção.

## Fora do escopo
- Migrar os demais painéis (specs 074 a 076).
- Congelamento e data de referência por pregão (spec 077).
- Seletor de pregões anteriores (spec 078).
