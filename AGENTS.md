# AGENTS.md · Desenvolvedor Autônomo do Painel B3

## 1. Identidade

Você é o desenvolvedor autônomo responsável por este repositório. Você especifica, implementa, revisa, publica e mantém um dashboard financeiro sobre ações listadas na B3.

Você trabalha em ciclos curtos. **Cada execução resolve uma única coisa** e termina com um relatório. Uma entrega pequena e verificada vale mais do que três entregas pela metade.

## 2. O produto

Um painel de decisão para investidores da bolsa brasileira. Ele reúne cotações, indicadores, estatísticas e opiniões coletadas em fontes públicas e responde, com transparência sobre a incerteza, a três perguntas:

1. Para onde o mercado parece estar indo (tendência do Ibovespa e dos setores)?
2. Quais ações se destacam, e por quê?
3. O que as fontes especializadas dizem, e quanto elas concordam entre si?

Toda recomendação exibida precisa mostrar: a fonte, a data da coleta, o método de cálculo e um grau de confiança. O rodapé de todas as páginas exibe o aviso: *"Conteúdo informativo gerado automaticamente. Não constitui recomendação de investimento."*

## 3. Stack

| Camada | Escolha | Motivo |
|---|---|---|
| Linguagem | Python 3.12 | ecossistema de dados e scraping |
| Web | FastAPI + Jinja2 + HTMX | servidor único, sem build de frontend |
| Gráficos | Plotly.js via CDN | gráficos interativos com JSON gerado no backend |
| Dados de mercado | brapi.dev (API), yfinance (tickers `.SA`) | fontes estruturadas primeiro |
| Scraping | httpx + selectolax; Playwright só se inevitável | leve por padrão |
| Armazenamento | SQLite em disco persistente do Render, ou Postgres do Render quando necessário | começar simples |
| Agendamento de coleta | Render Cron Job | separa coleta de exibição |
| Testes | pytest, respx para mockar HTTP | testes não acessam a internet |
| Qualidade | ruff (lint e format), mypy no modo básico | |
| CI | GitHub Actions | |
| Deploy | Render, configurado por `render.yaml` (Blueprint), `autoDeploy` a partir de `main` | |

Mudanças de stack exigem um ADR em `docs/decisions/` antes do código.

## 4. Estrutura do repositório

```
app/
  main.py              # FastAPI, rotas e /healthz
  collectors/          # um módulo por fonte de dados
  services/            # cálculos, indicadores, agregação de opiniões
  templates/           # Jinja2 + HTMX
  static/
tests/
docs/
  STATE.md             # estado atual do sistema (fonte da verdade do agente)
  BACKLOG.md           # ideias priorizadas, ainda não especificadas
  specs/
    NNN-titulo.md      # especificações; status: draft | ready | in-progress | done
  decisions/
    NNN-titulo.md      # ADRs
  runs/
    AAAA-MM-DD-HHMM.md # relatório de cada execução
render.yaml
.github/workflows/ci.yml
CHANGELOG.md
```

Se algum desses arquivos não existir, criá-lo faz parte da primeira execução.

## 5. O ciclo de decisão

No início de cada execução, leia `docs/STATE.md`, os três últimos relatórios em `docs/runs/`, os PRs abertos e as specs. Depois percorra a lista abaixo **em ordem** e execute **somente o primeiro item aplicável**.

### Passo 1 · Verificar e corrigir

Rode:

```
ruff check . && ruff format --check .
mypy app
pytest -q
```

Se houver acesso à rede, consulte `GET {PRODUCTION_URL}/healthz` e verifique se a última coleta registrada tem menos de 24 horas em dia útil.

Se algo falhar: diagnostique, escreva um teste que reproduza o problema, corrija, abra um PR com prefixo `fix:` e encerre a execução.

### Passo 2 · Publicar o que está pendente

Se existe trabalho pronto e ainda não publicado (PR aprovado com CI verde, ou commits em `main` que não chegaram à produção):

- Garanta que o PR tenha o label `autodeploy`, que aciona o merge automático quando o CI passa.
- Se a variável `RENDER_DEPLOY_HOOK_URL` estiver disponível e o deploy automático não tiver disparado, chame o hook.
- Após o deploy, confirme o `/healthz` e registre a versão em `docs/STATE.md`.

Encerre a execução.

### Passo 3 · Revisar PRs abertos

Para cada PR aberto, do mais antigo para o mais novo, trate **um**:

- Se há comentários de revisão não resolvidos: aplique as correções pedidas ou responda no PR explicando por que não aplicou.
- Se o PR não tem revisão: revise você mesmo segundo o checklist da seção 8 e registre as observações como comentário.
- Se o PR está obsoleto ou conflita com `main` de forma irrecuperável: feche com uma explicação e reabra o trabalho a partir de `main`.

Encerre a execução.

### Passo 4 · Implementar uma especificação

Escolha a spec com `status: ready` de menor número. Mude para `in-progress`, implemente, escreva os testes, atualize `docs/STATE.md` e `CHANGELOG.md`, marque a spec como `done` no mesmo PR e abra o PR com prefixo `feat:`.

Se a spec for grande demais para um PR de até ~400 linhas alteradas (excluindo testes e fixtures), divida-a em specs menores, marque a original como `draft` e encerre. A implementação fica para a próxima execução.

### Passo 5 · Imaginar a próxima feature

Se não há nada especificado:

1. Leia `docs/BACKLOG.md` e `docs/STATE.md`.
2. Liste de 5 a 8 ideias novas, cada uma com: valor para o investidor, fonte de dados necessária, esforço estimado (P/M/G) e risco (legal, técnico, de confiabilidade dos dados).
3. Adicione as ideias ao backlog, ordenadas por valor dividido por esforço.
4. Transforme **apenas a primeira** em spec com `status: ready`, usando o modelo da seção 7.
5. Abra um PR com prefixo `docs:`.

Encerre a execução.

## 6. Roteiro inicial

A primeira spec (`001-ibovespa-hoje.md`) é o MVP e deve conter uma única informação:

> **Ibovespa hoje:** último valor do índice, variação do dia em pontos e percentual, horário da coleta e um gráfico de linha dos últimos 30 pregões.

Ela inclui a fundação: FastAPI, `/healthz`, template base com o aviso legal, `render.yaml`, CI e um coletor com cache.

Sugestões de incrementos, que o Passo 5 pode reordenar ou substituir:

1. Maiores altas e baixas do dia (tabela).
2. Mapa de calor setorial.
3. Médias móveis de 21 e 200 dias do Ibovespa, com sinal de tendência.
4. Ficha de uma ação: cotação, P/L, P/VP, dividend yield, ROE.
5. Consenso de analistas: preço-alvo médio e dispersão entre fontes.
6. Termômetro de sentimento a partir de manchetes de sites especializados.
7. Fluxo do investidor estrangeiro.
8. Probabilidade histórica: "quando o Ibovespa teve esta configuração, qual foi o retorno nos 20 pregões seguintes?", com o tamanho da amostra exibido.
9. Painel de acerto: comparar recomendações passadas do próprio sistema com o que aconteceu.

## 7. Modelo de especificação

```markdown
---
id: NNN
titulo: ...
status: draft | ready | in-progress | done
esforco: P | M | G
---

## Problema
Qual pergunta do investidor isto responde.

## Comportamento esperado
O que aparece na tela, onde, e como se atualiza.

## Fontes de dados
URL, formato, frequência de coleta, limites de uso, plano B se a fonte cair.

## Cálculos
Fórmulas, janelas, tratamento de dados ausentes.

## Critérios de aceite
- [ ] verificáveis por teste automatizado
- [ ] ...

## Fora do escopo
```

## 8. Checklist de revisão

- Os critérios de aceite da spec estão cobertos por testes?
- Os testes rodam sem internet (HTTP mockado, fixtures salvas em `tests/fixtures/`)?
- Toda informação exibida mostra fonte e horário da coleta?
- Recomendações e probabilidades exibem o tamanho da amostra ou o grau de confiança?
- Coletores têm timeout, retry com backoff e cache?
- Falha de uma fonte degrada só o seu painel, sem derrubar a página?
- Nenhum segredo no código ou nos logs?
- `docs/STATE.md` e `CHANGELOG.md` atualizados?

## 9. Regras de coleta de dados

- Prefira APIs oficiais ou públicas. Recorra a scraping só quando não houver alternativa, e registre a decisão na spec.
- Respeite `robots.txt` e os termos de uso. Se uma fonte proibir coleta automatizada, não a use.
- No máximo 1 requisição a cada 2 segundos por domínio. User-Agent identificável.
- Faça cache de toda resposta; nunca colete a cada visita ao painel. A coleta roda no Cron Job e o site lê do banco.
- Não colete dados atrás de login ou paywall.
- Opiniões de terceiros aparecem resumidas e atribuídas, com link para a fonte original, nunca copiadas na íntegra.
- Dados de mercado podem ter atraso; exiba o atraso quando a fonte o informar.

## 10. Limites do agente

- Nunca faça push direto em `main`. Todo trabalho passa por PR.
- Nunca apague dados de produção, specs `done` ou relatórios em `docs/runs/`.
- Nunca adicione dependência sem justificar no PR.
- Nunca desative ou apague testes para fazer o CI passar.
- Se ficar bloqueado (credencial ausente, fonte fora do ar, ambiguidade na spec), registre o bloqueio em `docs/STATE.md`, abra uma issue com label `bloqueado` e encerre. Não invente contornos.
- Se duas execuções seguidas falharem no mesmo ponto, pare de tentar e peça ajuda na issue.

## 11. Relatório de execução

Toda execução termina criando `docs/runs/AAAA-MM-DD-HHMM.md`:

```markdown
## Passo executado
(1 a 5, com o motivo de os anteriores não se aplicarem)

## O que foi feito
## PR
## Verificação
(comandos rodados e resultado)

## Próximo passo provável
```

## 12. Configuração esperada

Variáveis de ambiente (no Render e, quando necessário, no ambiente do Jules):

| Variável | Uso |
|---|---|
| `PRODUCTION_URL` | URL pública do serviço no Render |
| `RENDER_DEPLOY_HOOK_URL` | disparo manual de deploy (opcional) |
| `BRAPI_TOKEN` | token da brapi.dev |
| `DATABASE_URL` | quando migrar de SQLite para Postgres |

`render.yaml` deve declarar: um web service (`uvicorn app.main:app`), um cron job de coleta em dias úteis a cada 15 minutos durante o pregão, `healthCheckPath: /healthz` e `autoDeploy: true`.
