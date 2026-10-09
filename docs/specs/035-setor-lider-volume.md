---
id: 035
titulo: Setor Líder por Volume Financeiro
status: done
esforco: P
---

## Problema
Responde: para qual setor o dinheiro está indo hoje, em reais, e não em %? Completa a Concentração Setorial (spec 025), que mostra só o líder por variação média.

## Comportamento esperado
Criar um painel (ou acrescentar seção) na visão macro indicando o setor com o maior volume financeiro negociado no dia, com base na cesta de ações já utilizada. O painel deve usar as macros do design system (ex. `kpi`).

## Fontes de dados
brapi / yfinance. Os mesmos usados pela cesta atual em `app.collectors.concentracao_setorial`.

## Cálculos
Para as ações com setor mapeado, acumular o volume (`volume`) de cada ativo por setor no intraday e apresentar o nome do setor vencedor, com seu montante ou percentual do total.

## Critérios de aceite
- [ ] O painel na visão macro exibe o setor líder em volume financeiro de forma destacada.
- [ ] Mock do httpx é utilizado nos testes.

## Invariantes de produção
- A chave e os dados necessários são adicionados ao contrato do `/api/snapshot`.
- `make audit` continua passando com os novos campos.

## Fora do escopo
Histórico e evolução do volume ao longo dos pregões passados para estes setores.
