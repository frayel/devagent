# Contexto · Arquitetura

Retrato do sistema como está na `main`. Atualize no mesmo PR que mudar algo aqui descrito.

## Componentes

| Componente | Onde | Papel |
|---|---|---|
| Web | `app/main.py` | FastAPI; rotas `/` (painel) e `/healthz` |
| Templates | `app/templates/` | `base.html` (layout e aviso legal), `index.html` (painel) |
| Serviços | `app/services/` | montam os dados de cada painel a partir do banco |
| Coletores | `app/collectors/` | buscam dados externos e gravam no banco |
| Banco | `app/database.py` | Postgres (produção) via `DATABASE_URL` ou SQLite (`data.db`, local/testes) via `app/banco.py` |

## Fluxo de dados

```
fonte externa → coletor (agendador no web service) → Postgres (camada de snapshots) → serviço → template → navegador
```

A página nunca chama fontes externas. Se o banco estiver vazio, o painel mostra "dado indisponível".

## Pontos de atenção conhecidos

- `app/database.py` cria a tabela no momento do import (`init_db()` no fim do módulo).
- A coleta roda dentro do web service (`app/agendador.py`, ADR 004): ao subir e depois em intervalos.
- Os painéis são gravados como snapshots no Postgres (`DATABASE_URL`). O SQLite (`DATABASE_PATH`) é apenas fallback local e para testes.
