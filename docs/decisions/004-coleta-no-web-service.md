# ADR 004 · Coleta dentro do web service

**Data:** 2026-09-27 · **Status:** aceito

## Contexto

Desde o MVP, produção nunca coletou dados. O `render.yaml` só declara o web service, o `httpx` usado pelos coletores não estava em `requirements.txt`, e o painel mostrou primeiro o dado de teste versionado em `data.db` e, depois que ele saiu do repositório, "Dados não disponíveis".

O `AGENTS.md` previa um Cron Job do Render. No plano gratuito isso não funciona: o disco do web service é efêmero e não é compartilhado com outro serviço, então o cron gravaria num banco que o site não lê.

## Decisão

O próprio web service coleta (`app/agendador.py`):

- ao subir, em segundo plano, sem atrasar o health check;
- a cada 15 minutos durante o pregão (9h55 às 18h15 BRT, dias úteis) e a cada 2 horas fora dele;
- Ibovespa e maiores altas e baixas em sequência; a falha de um não impede o outro;
- `COLETA_AUTOMATICA=0` desliga; os testes nunca coletam;
- `GET /api/coleta` mostra a última rodada e o último erro.

## Consequências

- Quando o Render hiberna o serviço (15 min sem tráfego), a coleta para e o banco se perde. Ao acordar, a primeira coleta leva alguns segundos (até cerca de um minuto para as maiores altas pelo Yahoo, por causa do limite de 1 requisição a cada 2 s). Nesse intervalo, a página mostra "Dados não disponíveis". O auditor espera 90 s antes de reprovar por isso.
- O histórico de 30 pregões vem da própria fonte a cada coleta, então perder o banco não perde histórico.
- Quando o produto precisar guardar histórico próprio (painel de acerto, séries longas), a migração é para Postgres com `DATABASE_URL`, e a coleta pode continuar aqui ou ir para um Cron Job que grave no mesmo banco.
