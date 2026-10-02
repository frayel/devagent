# PRODUTO.md · Painel B3

> **Camada do projeto.** Este arquivo diz **o que** você constrói. **Como** você trabalha está em `devagent/CICLO.md`, que vale para qualquer projeto. Em caso de dúvida, o `CICLO.md` manda no processo e este arquivo manda no produto.

## 1. O produto

Um painel de decisão para investidores da bolsa brasileira. Ele reúne cotações, indicadores, estatísticas e opiniões coletadas em fontes públicas e responde, com transparência sobre a incerteza, a três perguntas:

1. Para onde o mercado parece estar indo (tendência do Ibovespa e dos setores)?
2. Quais ações se destacam, e por quê?
3. O que as fontes especializadas dizem, e quanto elas concordam entre si?

### Escopo aberto

As três perguntas acima são o ponto de partida, não a cerca. Você é dono do produto e pode:

- mudar o escopo do sistema, criar funcionalidades novas e expandir as existentes sem pedir permissão;
- abrir frentes que ninguém pediu: novos tipos de análise, novas visualizações, novas formas de interação, páginas inteiras, outros ativos e mercados, se servirem ao investidor;
- abandonar ou reescrever o roteiro da seção 4 e as ideias do backlog quando encontrar algo melhor.

Busque o que ainda não existe em outros painéis. Um dashboard que só repete cotações é commodity; o valor está na pergunta que ninguém fez, na conexão entre dados que ninguém cruzou, no jeito novo de mostrar incerteza. Ousadia vale para a ideia; para a entrega, continuam valendo os ciclos curtos, os testes e os itens protegidos (seção 11 e `devagent/CICLO.md`).

### Transparência (protegido)

Toda recomendação exibida precisa mostrar: a fonte, a data da coleta, o método de cálculo e um grau de confiança. O rodapé de todas as páginas exibe o aviso: *"Conteúdo informativo gerado automaticamente. Não constitui recomendação de investimento."*

## 2. Stack

| Camada | Escolha | Motivo |
|---|---|---|
| Linguagem | Python 3.12 | ecossistema de dados e scraping |
| Web | FastAPI + Jinja2 + HTMX | servidor único, sem build de frontend |
| Gráficos | Plotly.js via CDN, com tema único em `app/static/graficos.js` | gráficos interativos com JSON gerado no backend |
| Interface | tema escuro, tokens em `app/static/tema.css`, macros em `app/templates/componentes.html` | guia em `docs/DESIGN.md` |
| Dados de mercado | brapi.dev (API), yfinance (tickers `.SA`) | fontes estruturadas primeiro |
| Scraping | httpx + selectolax; Playwright só se inevitável | leve por padrão |
| Armazenamento | SQLite em disco persistente do Render, ou Postgres do Render quando necessário | começar simples |
| Agendamento de coleta | laço no próprio web service (`app/agendador.py`, ADR 004) | no plano gratuito o disco é efêmero e não é compartilhado com um Cron Job |
| Testes | pytest, respx para mockar HTTP | testes não acessam a internet |
| Qualidade | ruff (lint e format), mypy no modo básico | |
| CI | GitHub Actions, pelos alvos do `Makefile` | |
| Deploy | Render, configurado por `render.yaml` (Blueprint), `autoDeploy` a partir de `main` | |

Mudanças de stack exigem um ADR em `docs/decisions/` antes do código.

**Contrato com o núcleo.** O `Makefile` traduz o stack para o núcleo: `make verify` roda ruff, mypy e pytest; `make smoke` sobe a aplicação com o `startCommand` do `render.yaml` só com `requirements.txt`; `make audit` roda `auditoria/auditar.py`. Ao mudar o stack, mude os alvos, não o núcleo.

## 3. Estrutura do código

```
app/
  main.py              # FastAPI, rotas, /healthz e /api/snapshot
  agendador.py         # coleta periódica dentro do web service (ADR 004)
  collectors/          # um módulo por fonte de dados
  services/            # cálculos, indicadores, agregação de opiniões
  templates/           # Jinja2 + HTMX
  static/
tests/
  fixtures/            # respostas reais salvas; o auditor procura estes números em produção
auditoria/             # checagens de produção deste produto (PROTEGIDO)
  auditar.py           # Ibovespa: fonte independente, frescor, coerência, vazamento de teste
  calendario.py        # calendário de pregões da B3
  README.md            # o que o auditor verifica e o contrato /api/snapshot
render.yaml
requirements.txt       # produção
requirements-dev.txt   # desenvolvimento
```

## 4. Roteiro inicial

A primeira spec (`001-ibovespa-hoje.md`) foi o MVP: último valor do Ibovespa, variação do dia em pontos e percentual, horário da coleta e um gráfico de linha dos últimos 30 pregões, com a fundação (FastAPI, `/healthz`, template base com o aviso legal, `render.yaml`, CI e um coletor com cache).

Sugestões de incrementos. São ponto de partida, não plano: o Passo 7 pode reordenar, substituir ou abandonar qualquer uma, e ideias próprias têm o mesmo peso.

1. Maiores altas e baixas do dia (tabela).
2. Mapa de calor setorial.
3. Médias móveis de 21 e 200 dias do Ibovespa, com sinal de tendência.
4. Ficha de uma ação: cotação, P/L, P/VP, dividend yield, ROE.
5. Consenso de analistas: preço-alvo médio e dispersão entre fontes.
6. Termômetro de sentimento a partir de manchetes de sites especializados.
7. Fluxo do investidor estrangeiro.
8. Probabilidade histórica: "quando o Ibovespa teve esta configuração, qual foi o retorno nos 20 pregões seguintes?", com o tamanho da amostra exibido.
9. Painel de acerto: comparar recomendações passadas do próprio sistema com o que aconteceu.

## 5. Regras de coleta de dados (protegido)

- Prefira APIs oficiais ou públicas. Recorra a scraping só quando não houver alternativa, e registre a decisão na spec.
- Respeite `robots.txt` e os termos de uso. Se uma fonte proibir coleta automatizada, não a use.
- No máximo 1 requisição a cada 2 segundos por domínio. User-Agent identificável.
- Faça cache de toda resposta; nunca colete a cada visita ao painel. A coleta roda no agendador do web service (`app/agendador.py`) e o site lê do banco.
- Não colete dados atrás de login ou paywall.
- Opiniões de terceiros aparecem resumidas e atribuídas, com link para a fonte original, nunca copiadas na íntegra.
- Dados de mercado podem ter atraso; exiba o atraso quando a fonte o informar.

## 6. Checklist do produto

Soma-se ao checklist de `devagent/CICLO.md`:

- Toda informação exibida mostra fonte e horário da coleta?
- Recomendações e probabilidades exibem o tamanho da amostra ou o grau de confiança?
- Coletores têm timeout, retry com backoff e cache?
- Falha de uma fonte degrada só o seu painel, sem derrubar a página?
- O painel novo aparece no `/api/snapshot` conforme o contrato em `auditoria/README.md`?
- Qualquer biblioteca usada em produção está em `requirements.txt`, e não só em `requirements-dev.txt`?
- Se o PR muda a interface: rodou `make telas`, **abriu as duas imagens de `telas/`** e respondeu o checklist visual da seção 8 do `docs/DESIGN.md` no corpo do PR e no relatório? Algum "não" significa que o PR não está pronto.

## 7. Convenções

- Números no padrão brasileiro: `183.476,86`; percentuais `+0,78%`; datas `dd/mm/aaaa`; fuso horário explícito (BRT).
- Toda a interface segue `docs/DESIGN.md`: tema escuro, tokens, grade, componentes e gráficos. Painel novo é montado com as macros de `app/templates/componentes.html` e uma classe `span-N`.
- Cores coerentes para alta e baixa em todos os painéis, sempre com seta além da cor.
- A página funciona em 390 px sem rolagem horizontal.

## 8. Onde procurar ideias

Complementa `devagent/skills/descobrir-ideias.md` com o território deste domínio:

- A dúvida que o investidor tem às 10h05, antes de decidir, e que nenhum site responde bem.
- Cruzamentos: fluxo estrangeiro × setor, manchetes × volume, consenso de analistas × o que aconteceu depois.
- Fora da B3, quando fizer sentido: câmbio, juros, commodities e bolsas estrangeiras explicam boa parte do que acontece aqui.
- Concorrentes para testar originalidade: Status Invest, Investing, TradingView, sites de corretoras.
- Cotação, gráfico e tabela de maiores altas todo painel já tem.

## 9. Auditoria: o que é verdade neste domínio

**Por que existe.** Em 26/09/2026 o painel mostrou o Ibovespa a 130.000 pontos, com o índice perto de 183.000. Os três fechamentos do gráfico (128.000, 129.000, 130.000,5) eram de `tests/fixtures/brapi_response.json`, e todos os testes passavam.

**Fontes independentes** para o auditor: Yahoo Finance (`^BVSP`), Stooq (`^BVP`), Investing.com, o site da B3 e portais de notícia financeira. Nunca a mesma fonte que o coletor usou.

**Perguntas do domínio**, somadas às da persona:

- As datas do gráfico são pregões reais? Há feriado da B3 aparecendo como pregão, ou pregão faltando?
- Durante o pregão, o dado acompanha o mercado? Depois do fechamento, mostra o fechamento?
- Variação, percentual e fechamento anterior são coerentes entre si e com a fonte?

**Exemplo de bom achado.** "Às 14:37 BRT de 28/09/2026 o painel mostrava 130.000 pontos. No mesmo minuto, o Yahoo Finance (`^BVSP`) mostrava 183.476,86 e o Stooq (`^BVP`), 183.460,12. A diferença é de 29%. O gráfico termina em 27/09/2023, e os três fechamentos exibidos são idênticos aos de `tests/fixtures/brapi_response.json`."

**Agenda.** O `auditoria-producao.yml` roda a cada 30 min durante o pregão (10h às 18h BRT), antes da abertura e uma vez por dia no fim de semana; o `auditoria-llm.yml`, nos dias úteis às 18h41 BRT, depois do fechamento.

## 10. Configuração do produto

Variáveis de ambiente do produto (as do núcleo estão em `devagent/OPERACAO.md`):

| Variável | Onde | Uso |
|---|---|---|
| `BRAPI_TOKEN` | Render | token da brapi.dev (sem ele, a coleta usa só o Yahoo Finance) |
| `COLETA_AUTOMATICA` | Render, opcional | `0` desliga a coleta dentro do web service |
| `DATABASE_PATH` | opcional | caminho do banco SQLite (padrão `data.db`) |
| `DATABASE_URL` | Render | quando migrar de SQLite para Postgres |

`render.yaml` declara um web service (`uvicorn app.main:app`), `healthCheckPath: /healthz` e `autoDeploy: true`.

## 11. Índice do projeto e itens protegidos

| Arquivo | Para que serve | Leia quando |
|---|---|---|
| `docs/DESIGN.md` | guia visual: tokens, grade, componentes, gráficos, checklist visual (PROTEGIDO) | antes de qualquer mudança de interface |
| `docs/design/referencia.html` | referência navegável do guia, com dados fictícios (PROTEGIDO) | antes de qualquer mudança de interface |
| `docs/context/arquitetura.md` | componentes, fluxo de dados, decisões vigentes | antes de mexer em estrutura |
| `docs/context/dominio-b3.md` | conceitos do mercado, pregão, horários, armadilhas | antes de spec ou cálculo financeiro |
| `docs/context/fontes-de-dados.md` | cada fonte: URL, limites, termos, confiabilidade | antes de criar ou alterar coletor |
| `docs/context/operacao.md` | particularidades operacionais deste produto no Render | antes de mexer em deploy ou coleta |
| `docs/skills/criar-coletor.md` | procedimento para nova fonte de dados | ao implementar coletor |
| `docs/decisions/` | ADRs do produto: `004` coleta dentro do web service | antes de mudar stack ou arquitetura |
| `auditoria/README.md` | o que o auditor verifica e o contrato `/api/snapshot` | ao tratar issue `producao-incorreta` e ao publicar painel novo |

Ao criar um arquivo novo em `docs/context/` ou `docs/skills/`, acrescente-o a esta tabela no mesmo PR.

Itens deste arquivo que só podem ser mantidos ou reforçados, nunca enfraquecidos: a **transparência** da seção 1 (aviso legal e fonte, data, método e confiança), as **regras de coleta** da seção 5 e a obediência ao **guia visual** (`docs/DESIGN.md`). O guia e a referência estão em `devagent/protegidos.txt`: o agente pode propor mudanças neles num PR `agent:` só para isso, que espera revisão humana, e nunca no mesmo PR que altera a interface. O teste `tests/test_design.py` não pode ser afrouxado.
