# Contexto · Arquitetura

Retrato do sistema como está na `main`. Atualize no mesmo PR que mudar algo aqui descrito.

## Componentes

| Componente | Onde | Papel |
|---|---|---|
| Web | `app/main.py` | FastAPI; rotas `/` (painel) e `/healthz` |
| Templates | `app/templates/` | `base.html` (layout e aviso legal), `index.html` (painel) |
| Serviços | `app/services/` | montam os dados de cada painel a partir do banco |
| Coletores | `app/collectors/` | buscam dados externos e gravam no banco |
| Banco | `app/database.py` | SQLite em `data.db`; tabela `ibovespa_cache` |

## Fluxo de dados

```
fonte externa → coletor (cron) → SQLite → serviço → template → navegador
```

A página nunca chama fontes externas. Se o banco estiver vazio, o painel mostra "dado indisponível".

## Pontos de atenção conhecidos

- `app/database.py` cria a tabela no momento do import (`init_db()` no fim do módulo).
- O caminho do banco (`data.db`) é fixo e relativo ao diretório de trabalho.
- O arquivo `data.db` está versionado no git; banco não deveria ir para o repositório (`.gitignore`).
- `render.yaml` ainda não declara o Cron Job do coletor, então em produção ninguém alimenta o banco.
