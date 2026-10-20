---
id: 072
titulo: Consultor · diário de recomendações e placar de acertos
status: draft
esforco: M
---

## Problema
Uma recomendação só ganha peso quando o usuário vê quantas vezes ela acertou. Esta spec registra cada decisão do consultor e cada opinião de casa, e mostra depois o que aconteceu com o preço. É o item 9 do roteiro do `PRODUTO.md` ("painel de acerto") aplicado ao consultor.

## Comportamento esperado
- Nova seção "Placar" no `/consultor`, com três tabelas:
  - **Consultor:** por decisão final (Comprar, Vender, Aguardar, No radar): número de recomendações avaliadas, taxa de acerto, excesso mediano sobre o Ibovespa em 5 e 20 pregões.
  - **Regras técnicas:** o mesmo, por regra R1 a R5, com as recomendações emitidas de fato (complementa o histórico simulado da spec 069).
  - **Casas de análise:** por casa com pelo menos 5 opiniões avaliadas: taxa de acerto e excesso mediano em 20 pregões.
- Em cada linha, o tamanho da amostra; com `n < 10`, "amostra insuficiente" no lugar da taxa.
- Para Aguardar: percentual de gatilhos atingidos em até 20 pregões e o excesso nos 20 pregões após o gatilho.
- Sem `DATABASE_URL` ou com o Postgres inacessível, o placar funciona no SQLite e a seção mostra: "Histórico efêmero: o placar recomeça a cada reinício do servidor." (ADR 006). A página nunca falha por causa do banco.
- `/api/consultor` inclui `placar` e `armazenamento: "postgres" | "sqlite_efemero"`.

## Fontes de dados
- Banco: Postgres por `DATABASE_URL` (Neon recomendado), com `psycopg[binary]` em `requirements.txt` (ADR 006). Plano B: SQLite.
- Preços para avaliar: histórico diário já coletado nas specs 068 e 069.

## Cálculos
- **Registro.** Uma linha em `consultor_recomendacoes` quando a decisão final de um ativo muda, e uma linha de fechamento por ativo e pregão (gravada na primeira rodada após 18h BRT). Campos: data e hora, ticker, decisão final, regra técnica, consenso, preço, gatilho ou invalidação.
- **Opiniões.** Cada opinião validada da spec 070 é gravada em `consultor_opinioes` com a data da matéria e o preço de fechamento daquele dia.
- **Avaliação.** Para cada registro de mudança com pelo menos 5 ou 20 pregões à frente: excesso = retorno do ativo − retorno do Ibovespa entre o fechamento da data do registro e o fechamento 5 ou 20 pregões depois. Acerto: Comprar e No radar com excesso > 0; Vender com excesso < 0; opinião de casa: compra com excesso > 0, venda com excesso < 0, neutro com |excesso| ≤ 2 p.p.
- Gravações agrupadas por rodada do agendador, numa transação.

## Critérios de aceite
- [ ] Com um fixture de 3 mudanças de decisão e preços futuros conhecidos, a taxa de acerto e o excesso mediano batem com os valores calculados no teste.
- [ ] Uma decisão que se repete em rodadas seguidas gera uma única linha de mudança.
- [ ] Uma casa com 4 opiniões avaliadas não aparece na tabela de casas.
- [ ] Sem `DATABASE_URL`, a seção mostra o aviso de histórico efêmero e `armazenamento` é `sqlite_efemero`.
- [ ] Com `DATABASE_URL` apontando para um host inacessível, a página responde 200, cai para o SQLite e mostra o aviso.
- [ ] Os testes rodam sem Postgres real (SQLite em memória pela mesma interface).

## Invariantes de produção
- Toda linha do placar mostra `n`, e nenhuma taxa é exibida com `n < 10`.
- Se `armazenamento` for `sqlite_efemero`, o aviso de histórico efêmero aparece na página.

## Fora do escopo
- Migrar os caches dos painéis para o Postgres.
- Exportar o diário.
- Simular uma carteira que siga as recomendações (vai para o backlog).
