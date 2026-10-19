# ADR 006 · Persistência do consultor em Postgres externo

**Data:** 2026-10-18 · **Status:** aceito · **Origem:** pedido do dono do produto

## Contexto

O placar do consultor compara recomendações passadas com o que aconteceu depois, e as opiniões extraídas de matérias custam chamadas de LLM. As duas coisas precisam sobreviver a reinícios.

No plano gratuito do Render, o SQLite do web service se perde a cada deploy, reinício ou hibernação (15 minutos sem tráfego), conforme a ADR 004 e a documentação do Render. O Postgres gratuito do próprio Render expira 30 dias após a criação e é apagado 14 dias depois, então não serve para histórico.

O Neon oferece Postgres gratuito com 1 GB por projeto e 100 horas de computação por mês, desliga a computação após 5 minutos parado e não apaga os dados por inatividade (verificado em 18/10/2026).

## Decisão

1. As tabelas duráveis do consultor (`consultor_recomendacoes`, `consultor_opinioes`, `consultor_fila_materias`) ficam no Postgres apontado por `DATABASE_URL`. O provedor recomendado é o Neon; qualquer Postgres serve.
2. Os caches dos painéis continuam no SQLite. Esta decisão não migra o resto do produto.
3. Driver: `psycopg[binary]`, adicionado a `requirements.txt`. Um módulo `app/consultor/armazenamento.py` expõe a mesma interface para os dois bancos.
4. **Plano B.** Sem `DATABASE_URL`, ou com o Postgres inacessível, o consultor usa tabelas no SQLite e exibe o aviso: "Histórico efêmero: o placar recomeça a cada reinício do servidor." A página nunca falha por causa do banco.
5. Gravações curtas e agrupadas por rodada do agendador, para o banco poder dormir entre rodadas.

## Consequências

- Ação humana necessária: criar o projeto no Neon e cadastrar `DATABASE_URL` no Render. Até lá o consultor roda no plano B.
- Enquanto o Render hibernar, o agendador não roda e o diário fica com lacunas. O placar mede retornos a partir dos preços históricos da fonte, então uma lacuna reduz a amostra, mas não distorce o cálculo.
- O consumo estimado (algumas gravações a cada 15 minutos no pregão) fica bem abaixo das 100 horas mensais do Neon.
- Os testes usam o plano B (SQLite em memória); nenhum teste acessa Postgres real.
