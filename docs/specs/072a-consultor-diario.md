---
id: 072a
titulo: Consultor · diário de recomendações (suporte a Postgres)
status: done
esforco: M
---

## Problema
(Referência: Issue #385)

Uma recomendação só ganha peso quando o usuário vê quantas vezes ela acertou. Esta spec registra cada decisão do consultor e cada opinião de casa no banco (Postgres ou SQLite). É a primeira parte do item 9 do roteiro do `PRODUTO.md` ("painel de acerto") aplicado ao consultor.

## Comportamento esperado
- Nenhuma mudança visível na UI nesta etapa (a interface vem na spec 072b).
- `/api/consultor` inclui `armazenamento: "postgres" | "sqlite_efemero"`.
- O módulo `app/consultor/armazenamento.py` lida com a conexão e persistência de dados.
- Sem `DATABASE_URL` ou com o Postgres inacessível, o registro funciona no SQLite.

## Fontes de dados
- Banco: Postgres por `DATABASE_URL` (Neon recomendado), com `psycopg[binary]` em `requirements.txt` (ADR 006). Plano B: SQLite.
- Preços: histórico diário já coletado.

## Cálculos
- **Registro.** Uma linha em `consultor_recomendacoes` quando a decisão final de um ativo muda. Campos: data e hora, ticker, decisão final, regra técnica, consenso, preço, gatilho ou invalidação.
- **Fechamento.** Uma linha de fechamento por ativo e pregão (gravada na primeira rodada após 18h BRT).
- **Opiniões.** A tabela `consultor_opinioes` também ganha suporte ao driver unificado.
- Gravações agrupadas por rodada do agendador, numa transação.

## Critérios de aceite
- [ ] O módulo de armazenamento detecta a presença de `DATABASE_URL` e conecta ao Postgres usando psycopg, ou usa SQLite local como fallback se não houver URL ou se a conexão falhar.
- [ ] Uma decisão que se repete em rodadas seguidas gera uma única linha de mudança.
- [ ] `/api/consultor` expõe o campo `armazenamento` indicando o backend ativo.
- [ ] Com `DATABASE_URL` apontando para um host inacessível, a aplicação responde normalmente e cai para o SQLite.
- [ ] Os testes rodam sem Postgres real (SQLite em memória pela mesma interface).

## Invariantes de produção
- A chave `armazenamento` em `/api/consultor` reflete o banco em uso ("postgres" ou "sqlite_efemero").

## Fora do escopo
- A interface visual do placar, os cálculos de taxa de acerto e excesso mediano (spec 072b).
