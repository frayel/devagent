# Changelog

## [Unreleased]
### Changed
- agent: `docs/DESIGN.md` reduz o gráfico do Ibovespa para 200px e proíbe eixo Y de preço começando em zero (vai de 2% abaixo do mínimo do período), a pedido do dono do produto.
### Fixed
- fix: a Calma da Maré do mercado (Spec 027) passa a medir só a volatilidade de queda (semidesvio com alvo zero). Com o desvio-padrão comum, a alta de 7,42% do Ibovespa em 05/10/2026 zerava a Calma e deixava a Maré em Medo (25) no dia seguinte a uma alta histórica.
- fix: gráfico do Ibovespa com 200px de altura (antes ficava com a altura padrão do Plotly, 450px) e eixo Y a partir de 2% abaixo do mínimo do período, em vez de zero.
### Added
- feat: Maré do mercado (Spec 027), índice de otimismo de 0 a 100 ao lado do Ibovespa: Fluxo (40%, volume financeiro em ações que sobem), Calma (35%, percentil da volatilidade de 10 pregões do Ibovespa) e Volume (25%, ritmo contra a média de 21 pregões no sentido da maioria). Gauge com as cinco faixas (Pânico, Medo, Neutro, Confiança, Otimismo extremo), barras dos componentes, linha dos últimos 21 pregões e selo `parcial` quando falta um componente. Chave `mare` no `/api/snapshot` e invariantes no auditor (`checar_mare`). Tendência, Dispersão e Coesão passam para a linha seguinte.
### Fixed
- agent: PR vazio não entra mais. O #171 ("Spec 027a") chegou sem nenhum arquivo, passou no CI e foi mergeado; a Maré do mercado continua sem implementação e a spec 027 segue `ready` na seção Correções. Regra 5 em `devagent/conferir_pr.py` (reprova PR sem alteração em `pull_request` ou com `--exigir-alteracao`) e segunda trava no `automerge.yml`, que fecha o PR vazio sem merge.
### Added
- feat: Gauges para valores únicos (Spec 026). Macro `gauge` em SVG desenhada no servidor, com o cálculo em `app/gauge.py`; Dispersão, Índice de Coesão, Apetite a Risco, Rotação de Capital e Tendência mostram o número dentro da escala. A barra subiram × caíram da Dispersão, que saía vazia desde que a CSP proibiu estilo inline, passa a ser desenhada em SVG.
- núcleo: retomada depois de ambiente reiniciado (ADR 009). O status `in-progress` deixa de ser commitado; as cobranças do guardião trazem o comando para voltar à branch do PR; o vigia do Jules responde apontando a branch quando o PR está aberto e encerra a sessão quando o PR foi fechado; nova ação `encerrar` no `jules.yml`.
- feat: Índice de Concentração Setorial (Spec 025): setor da cesta com a maior variação média do dia, com nomes de setor em português; quando nenhum setor tem média positiva, o painel diz "Nenhum setor em alta". A chave `concentracao_setorial` entra no `/api/snapshot`.
- núcleo: `python -m devagent.conferir_pr` roda no CI e reprova PR com spec `in-progress`, script de teste fora de `tests/`, spec `done` sem CHANGELOG ou estado do sistema, ou spec nova fechada enquanto a seção Correções do backlog tem entrada pendente (ADR 008).
- agent: `docs/DESIGN.md` ganha a tabela "a forma do dado escolhe o gráfico" (5.1) e o componente `gauge` (5.2); a referência navegável mostra o gauge simples, o divergente e o com faixas, e a nova distribuição da linha 1 (Ibovespa + Maré). Specs 026 (gauges para valores únicos) e 027 (Maré do mercado, índice de otimismo de 0 a 100 por fluxo, volatilidade e volume) entram na seção Correções do backlog, a pedido do dono do produto.
- feat: Implementado Compradores de Fundo (Reversão Intraday) (Spec 021)
- feat: Implementada Rotação de Capital (Bancos vs Commodities) avaliando o estado diário (Spec 018)
- **Variação Súbita:** Adiciona painel que exibe ações com variação expressiva na última hora (Spec 017).
- feat: Implementa Concentração de Ganhos (Spec 015) com cálculo de contribuição das maiores empresas no fechamento diário.
- feat: Implementado o Índice de Coesão do Mercado (Spec 012), mostrando quantas das top 10 ações do IBOV estão na mesma direção do índice, incluindo coleta e cache em SQLite.
- feat: Adicionado Filtro Macro vs Micro (Spec 013) permitindo ocultar e exibir painéis específicos na página inicial.
- Implementada a funcionalidade "Força Relativa" (Spec 009):
  - Novo card de Força Relativa para as top ações x IBOV nos últimos 30 dias.
  - Adição da chave `forca_relativa` ao payload do `/api/snapshot`.


### Added
- Painel 'Resiliência (Fator Mola)' para mostrar a recuperação das ações frente à mínima diária.
- Inclusão do 'fator_mola' no payload JSON do `/api/snapshot`.

### Added
- Painel 'Resiliência (Fator Mola)' para mostrar a recuperação das ações frente à mínima diária.
- Inclusão do 'fator_mola' no payload JSON do `/api/snapshot`.
### Changed
- agent: Guia visual em `docs/DESIGN.md` (tema escuro, tokens, grade de 12 colunas, componentes, tema único de gráficos e checklist visual) com referência navegável em `docs/design/referencia.html`, ambos protegidos. `make telas` captura a interface em 1440 e 390 px com dados de demonstração; o workflow `telas.yml` anexa as capturas aos PRs que mexem em `app/templates` ou `app/static`. `tests/test_design.py` guarda o guia (xfail estrito até a spec 008). Spec 008 de redesign entra na seção Correções do backlog.
- agent: Revisão de experiência (ADR 006): nova skill `devagent/skills/rever-experiencia.md`; toda rodada do Passo 7 gera ao menos uma ideia de experiência a partir das capturas, e a cada três painéis novos o Passo 7 faz uma revisão obrigatória da página inteira. A grade passa a ser revista a cada painel novo.
- feat: Implementa Sensibilidade ao Dólar (Spec 006) calculando correlação de Pearson dos retornos do BRL=X com ativos da B3.
- feat: Documenta e marca como concluída a Spec 004 (Termômetro de Dispersão), cuja implementação já havia sido entregue em PRs anteriores.
- feat: Implementa Alertas de Volume Anormal (Spec 005) consultando variações atípicas em ações da B3 via Yahoo Finance (análise das últimas 3 semanas para identificação de descolamento de >50%).
- Núcleo do desenvolvedor autônomo separado do produto, no mesmo repositório (ADR 005 em `devagent/decisoes/`): `AGENTS.md` vira porta de entrada para `devagent/CICLO.md` (processo) e `PRODUTO.md` (produto); scripts, personas, skills de processo e ADRs do ciclo foram para `devagent/`; `devagent.toml` e o `Makefile` (`make verify`, `make smoke`, `make audit`) são o contrato entre as camadas; o auditor foi dividido em harness (`devagent/auditoria/nucleo.py`) e checagens do produto (`auditoria/auditar.py`); caminhos protegidos passam para `devagent/protegidos.txt`; `devagent/tests/test_fronteira.py` impede o núcleo de citar o produto; `python -m devagent.instalar` leva o núcleo a outro projeto.
- feat: Implementa painéis de "Tendência (Ibovespa)" com médias móveis de curto e longo prazo (Spec 003).
- feat: Implementa painéis de Maiores Altas e Maiores Baixas (Spec 002).
### Fixed
- fix: Implementa testes para o endpoint `/api/snapshot` conforme contrato do auditor de produção e registra a conclusão no backlog.
- test(highlights): Adiciona cobertura para os critérios da spec 002 marcados como sem teste: testa comportamento com menos de 5 ativos, testa a presença da fonte no template da página, e valida a ordenação do ranking de maiores altas e maiores baixas. Testes de maiores altas e baixas não levam mais 2 minutos após isolamento com monkeypatch.
- Maiores altas e baixas vazias com `BRAPI_TOKEN`: o plano gratuito da brapi não aceita 30 ativos numa chamada. O coletor passa a usar `/api/quote/list` (uma chamada, sem token), com ranking entre as 100 ações mais negociadas do dia; Yahoo continua como reserva.
- `httpx` faltava em `requirements.txt`: os coletores não rodariam em produção.
- fix(coleta): introduzido `fetch_with_retry` em `app/collectors/utils.py` com limite de requisições de 2s, User-Agent identificável e *backoff* exponencial de retry em erros 429 e 5xx, de acordo com as diretrizes do AGENTS.md seção 9. Substituídas chamadas diretas via `httpx` nos coletores.
- fix(coletor): Yahoo Finance fallback agora extrai a variação diária corretamente pelo penúltimo candle (ou `meta.previousClose`) em vez de basear o cálculo do candle do mês passado.
- CI: `ruff` fixado em 0.15.22; a versão 0.16 ampliou as regras padrão e deixou o lint vermelho na `main`, travando o auto-merge.
### Added
- Coleta automática dentro do web service (`app/agendador.py`, ADR 004): ao subir, a cada 15 min no pregão e a cada 2 h fora dele; diagnóstico em `/api/coleta`. Produção passa a exibir dados reais.
- `scripts/jules.py` e workflows `jules.yml`/`auditoria-llm.yml`: sessões do Jules criadas pela API sem aprovação de plano; planos pendentes aprovados e perguntas respondidas a cada 15 min.
- Auditor de produção (`auditoria/`): confere o site publicado contra Yahoo Finance/Stooq, calendário da B3, coerência dos números e vazamento de fixtures; workflow `auditoria-producao.yml` abre issues `producao-incorreta`.
- Persona do auditor LLM (`docs/agents/auditor.md`) e workflow `auditoria-achados.yml`, que transforma achados em issues.
- `automerge.yml` exige revisão humana para PRs que alteram o auditor.
- Feature: Ibovespa Hoje (MVP).
- Banco de dados SQLite local.
- Coletor de dados da brapi.dev e Yahoo Finance.
- Integração com Plotly.js para gráficos.

- Correção: implementado redesign da interface segundo o guia visual (spec 008).
