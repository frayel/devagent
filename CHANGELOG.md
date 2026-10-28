# Changelog

## [Unreleased]
- spec 119b: Adicionado validador da chave API do Gemini em background.
- **Consultor**: Exibe recomendações e opiniões em datas passadas (spec 113)
- Fix: Ibovespa daily variation falling back to incorrect previous close
- Feat: brapi secondary source client module (spec 098)

- **Testes sem rede:** Bloqueio de rede no pytest, conforme a spec 095.
- **Saúde técnica**: Detalhamento de falhas no registro HTTP para diferenciar pedidos errados de indisponibilidade (Spec 090a).
- **Saúde técnica**: Seletor de pregão da página inicial agora utiliza a variável `data`, validando o histórico em /sistema (spec 088).
- Spec 087: Otimização do tempo de carregamento da página Consultor.
- Spec 085: Consultor explica por que não há opiniões em vez de aviso vazio.
- fix(núcleo): os testes do agente não enxergam mais o evento real do PR (ADR 022). PRs de raia paralela (`spec:`, `revisão:`, `verificação:`) falhavam no CI por herdarem o título na regra 8 e entravam em laço de correção e fechamento.
- Histórico dos últimos 5 pregões na UI e API (Spec 078).
- Spec 077d: Resíduos do SQLite depois da migração - remoção das tabelas `radar_anomalia_fechamento_cache` e `consultor_confianca_regras`.
- agent: raias paralelas (ADR 021). Ao lado do desenvolvimento, que segue único, a rodada abre três raias que escrevem em outros lugares: Especificador (o antigo Passo 7, quando a fila de specs `ready` chega a uma, PR `spec:`), Revisor (revisa a próxima spec e preenche `revisada:` antes de ela entrar na fila do desenvolvimento, PR `revisão:`) e Verificador geral (confere os merges do desenvolvimento a cada 90 min no mínimo e abre achados em `docs/verificacao/`, que viram issues `verificacao`). Cada raia tem uma sessão e um PR por vez; a regra 8 do `conferir_pr` reprova PR fora da sua faixa; números de spec nova são reservados no prompt para não colidirem; o guardião fecha PR de raia paralela sem `tentativa-falhou`.
- refatoração: implementação da spec 077c, removendo resíduos do SQLite na lógica de diagnóstico do banco de dados na página /sistema.
- refatoração: implementação da spec 077b-banco-residuos-consultor.md, removendo resíduos do SQLite na lógica do Consultor.
- refatoração: implementação da spec 077b-banco-residuos-consultor.md, removendo resíduos do SQLite na lógica do Consultor.
- Spec 077a: Resíduos do SQLite depois da migração
- **Spec 077:** Congelamento de dados e data de referência no pós-pregão, melhorando o carregamento intradiário
### Added
- Spec 121a: Guia de resolução para alertas da página de sistema com causa e ação para cada tipo de problema.
- feat: Rastreador de Correlação com DI (Spec 081) - Painel que exibe a correlação entre o Ibovespa e os juros futuros (DI1F27/DI1F29) em dois horizontes de tempo (15 min intraday e diário 5 dias).
- Refatoração: migração de painéis (lote 3 parte a) para usar snapshots_paineis, removendo tabelas SQLite. (Spec 076a)
- Migração de tabelas de cache para `snapshots_paineis` (Spec 075a).
- Refatoração: migração de painéis (lote 2 parte b) para usar snapshots_paineis, removendo tabelas SQLite. (Spec 075b)
- Migração de tabelas de cache para `snapshots_paineis` (Spec 075a).
- **Spec 073**: Banco · camada única com Postgres e armazenamento do consultor
### Added
- Migração de tabelas de cache para `snapshots_paineis` (Spec 075a).
- **Consultor**: diário de recomendações com suporte ao Postgres para decisões técnicas, fechamentos e unificação de driver nas opiniões (Spec 072a).
- Consultor: cruza os sinais técnicos com o consenso das casas de análise (spec 071).
- **Spec 070:** Extrai recomendações e opiniões de casas de análise utilizando o LLM Gemini e as exibe no painel do Consultor de Investimentos.
- Implementa coleta de histórico extenso e avaliador do índice de acerto do consultor (spec 069a)

### Adicionado
- fix(núcleo): issues paradas voltam a andar (ADR 020). Achados de auditoria de severidade média e baixa nascem com `prioridade` e o prompt da sessão manda corrigi-los antes da próxima spec (caso #418); a `tentativa-falhou` registra a spec do PR; o guardião fecha a tentativa cuja spec já está `done` ou que não cita spec (casos #416 e #427); PR vazio de especialista fecha sem issue.
- fix(núcleo): sessão que falha no Jules é retomada e ensina (ADR 019). A rodada responde as sessões do ciclo que terminaram em `FAILED` com uma pergunta no ar e, se não voltarem em 15 min, abre `tentativa-falhou` com a spec e a última fala do agente; PR com CI vermelho e atividade na última hora espera a própria sessão corrigir em vez de chamar outra (caso #414/#415); o guardião fecha sem issue o PR de especialista que só traz o diário (caso #406/#407).
- fix(núcleo): o ciclo se recupera de tentativa perdida (ADR 018). O guardião fecha na hora PR vazio ou só de relatório, sem cobrar o agente; spec com `tentativa-falhou` aberta é dividida antes de nova tentativa; o tamanho de spec passa a contar os testes tocados; specs ganham `aceite:` e a regra 7 da disciplina exige o teste ao fechar. A 074 perde os `CREATE TABLE` que deixou para trás, e as specs 075 e 076 viram 075a, 075b, 076a e 076b (issue #404).
- fix: o cabeçalho leva de volta aos painéis a partir do Consultor e do Sistema. "Painel B3" vira link para `/`, a navegação ganha a aba "Painéis" e a aba da página atual fica marcada.
- fix: a auditoria deixa de exigir a chave `detector_acao_orfa` no `/api/snapshot`. O painel foi removido de propósito pela spec 067, e a checagem que ficou para trás gerava alarme falso (issue #370).
- fix: `/sistema` separa fonte fora do ar de pedido errado. Só 404 (ou outro 4xx que não seja 401, 403 ou 429) deixa a integração em atenção, e não em problema; o erro registrado traz a URL, com tokens mascarados. Painel vazio em todas as rodadas das últimas 3 h (ao menos 3) vira problema (spec 082).
- agent: o ciclo lê a página de saúde de produção (ADR 016). `python -m devagent.saude` lê o JSON configurado em `[saude]`; o `estado_github` mostra o resumo no início de toda execução; o job `saude` do `auditoria-producao.yml` abre, atualiza ou fecha a issue `sistema-com-problema`, que o Passo 1 trata como produção quebrada (o que depende de ajuste externo fica `bloqueado`). `/api/sistema` ganha o campo `parcial`, e a variável do intervalo do cron-job.org na página passa a ser `JULES_DISPARO_MINUTOS`.
- Spec 082: página `/sistema` (link "Sistema" no cabeçalho) e `/api/sistema` com a saúde do produto e do fluxo de desenvolvimento: versão e deploy em produção, banco, agendador da coleta, integrações externas (pelas chamadas reais dos coletores), disparos e sessões do Jules, PRs, issues que pedem ação e workflows do GitHub, incluindo agendamentos que o GitHub deixou de rodar. GitHub, Jules e Render são lidos em segundo plano; a visita não chama fonte externa.
- Spec 068a: Consultor Rota e Coleta com autenticação HTTP Basic.
- Condição de interface para ocultar painéis de alertas que estejam vazios, exibindo uma mensagem de "Sem alertas ativos no momento" se todos estiverem vazios (Spec 080).

- feat: implementa radar de anomalia de fechamento (spec 066)

### Added
- Migração de tabelas de cache para `snapshots_paineis` (Spec 075a).
- feat: Implementa a spec 070a sobre a fila e armazenamento de opiniões de casas de análise.
- Removido painel Ação Órfã (Spec 067)
- Painel de Assimetria Risco/Retorno (Spec 065) que exibe as ações mais próximas do fundo recente e distantes do topo.
- [Spec 061] Experiência: Reorganização da ordem do topo ('Clima Global' e 'Motores do Índice' movidos para baixo do 'Ibovespa' e 'Maré') na visão geral.
- Implementada proxy local para requisições diárias (Spec 063)
- Radar de Exaustão de Queda (Spec 060) exibe ações que caem há 3 dias com recuperação intraday acima da abertura.
- Termômetro de Exaustão de Tendência (Spec 059) adicionado.
- Termômetro de Concentração de Ordens (Spec 058) adicionado.
- Radar de Anomalias de Spread (Spec 057) adicionado.
- `instrumentacao_coleta_vazia`: tabela e rotina para registrar quando a coleta de um painel retorna vazia (Spec 056, saúde técnica).
- `instrumentacao_coleta_vazia`: tabela e rotina para registrar quando a coleta de um painel retorna vazia (Spec 056, saúde técnica).
- Spec 055: Experiência - Fusão de Indicadores Globais
- agent: Cadência de manutenção e poda (ADR 011): o Passo 7 classifica o trabalho em quatro gavetas (capacidade nova, experiência, saúde técnica, poda), toda rodada gera ao menos uma ideia de saúde técnica ou poda, e a cada 4 specs entregues o Passo 7 faz uma rodada obrigatória de manutenção. Nova skill `devagent/skills/manutencao.md` e critério de poda no `PRODUTO.md`.
- Spec 053: Relógio de Volatilidade Intraday, mapeando amplitudes hora a hora.
- Finaliza Spec 052: Termômetro de Clima Externo já estava implementada e adicionada no snapshot, movido para done
- Corrige `400 Bad Request` no coletor de Atrasadas do Rally fatiando requisições (resolvido por `app/collectors/atrasadas_rally.py`)

## [2026-10-13]
- Implementada Spec 051: Experiência: Densidade Dinâmica da Grade.

### Adicionado
- **Reorganização da Maré do Mercado (Spec 050)**:
  - Gauge de Confiança compactado para ocupar menos espaço.
  - Gauges de Apetite a Risco e Rotação reorganizados de forma mais densa.


### Alterado
- Consolidação de medidores de Apetite a Risco e Rotação de Capital na Maré do Mercado (Spec 049).
- Entrega a Spec 048, adicionando cards dos Motores do Índice.
### Added
- Migração de tabelas de cache para `snapshots_paineis` (Spec 075a).
- Radar de Exaustão de Queda (Spec 060) exibe ações que caem há 3 dias com recuperação intraday acima da abertura.
- `instrumentacao_coleta_vazia`: tabela e rotina para registrar quando a coleta de um painel retorna vazia (Spec 056, saúde técnica).
- Spec 047: Adicionado o painel Concentração de Força Vendedora (visoão macro) calculando a contribuição negativa dos piores 5 ativos quando o Ibovespa cai.
- Spec 046: Fator Peso Pesado (painel de contribuição das 5 maiores ações)
- Spec 045: Ajuste de espaçamento e respiro visual para o painel `.painel-mare`.
- (Spec 045) Destaque Visual para a Maré: ajustes de CSS em `tema.css` para aprimorar o destaque ao gauge e espaçamento na grade.
- Destaque Visual para a Maré adicionado como ideia, Spec 045 criada, Contador de experiência zerado no STATE.md.
- Spec 044 (Radar de Absorção Cruzada):
  - Banco de dados SQLite (`radar_absorcao_cruzada_cache`).
  - Coletor com yfinance monitorando exaustão de tendência de baixa.
  - Adicionado painel em "Alertas Intraday" e `/api/snapshot`.
- Spec 043 (Radar de Liquidez de Abertura):
  - Banco de dados SQLite (`liquidez_abertura_cache`).
  - Coletor buscando fechamentos intraday para ações de alta liquidez via `yfinance` para detectar picos anormais de volume na abertura comparados à média.
  - Exibição de painel e tabela de alertas via contrato `/api/snapshot`.
- Filtro de Sensibilidade a Juros (Spec 042) com as maiores correlações negativas.
- Painel "Falso Rompimento" na visão micro listando ações que romperam a máxima mas reverteram para baixo com volume (Spec 041).
- Spec 040: Radar de Divergência Volume/Preço. Painel de alerta intraday para exaustão de topo (alta com queda progressiva no volume médio).
- Spec 039: Índice de Esforço vs Resultado.
- feat: Adiciona Detector de Ação Órfã (Spec 038). Novo painel na visão micro que exibe as ações com queda brusca de volume intradiário (secaram em lote de 15min). Adicionado ao contrato `/api/snapshot` e verificação no auditor.
- feat: Radar de Congestionamento (Estreitamento de Bandas) (Spec 037). Novo painel que identifica ações operando em faixas estreitas com base nas Bandas de Bollinger, sinalizando potencial para um movimento forte em breve. Baseado no Yahoo Finance.
- **Radar de Short Squeeze**: Painel em "Alertas Intraday" para ações em forte queda recente, mas com alta diária violenta acompanhada de volume anormal (Spec 36).
- Radar de Short Squeeze (Capitulação Vendida) adicionado aos alertas intraday (Spec 036).
- feat: Implementa Setor Líder por Volume Financeiro (Spec 035). Adiciona o líder de volume no painel de concentração setorial.
- feat: Minimização de Painéis Indisponíveis (Spec 034) para ocultar painéis que estão sem dados na UI sem alterar API e melhorar a leitura do usuário.
- Feature (Spec 033): Radar de Anomalia de Peso Relativo Intraday
- Implementada spec 032: Radar de Inflexão, mostrando ações com queda nos últimos 15 dias mas que estão revertendo para alta no intraday.
### Changed
- Integrados os gauges de Tendência ao card principal do Ibovespa (Spec 035).
- núcleo: o Jules passa a ser acordado por um relógio externo (ADR 010). O job `vigia`, que ficava ligado 24 h por dia no Actions, dá lugar à ação `rodada` (inicia a persona da hora, destrava e sai em segundos); o `jules.yml` perde o `schedule` e é chamado a cada 30 min pelo cron-job.org via `workflow_dispatch`, porque o cron do GitHub descarta a maior parte dos disparos frequentes. Configuração em `devagent/OPERACAO.md`.
### Added
- Migração de tabelas de cache para `snapshots_paineis` (Spec 075a).
- Radar de Exaustão de Queda (Spec 060) exibe ações que caem há 3 dias com recuperação intraday acima da abertura.
- `instrumentacao_coleta_vazia`: tabela e rotina para registrar quando a coleta de um painel retorna vazia (Spec 056, saúde técnica).
- Spec 046: Fator Peso Pesado (painel de contribuição das 5 maiores ações)
- docs: atualiza estado das specs 029 e 030
### Added
- Migração de tabelas de cache para `snapshots_paineis` (Spec 075a).
- Radar de Exaustão de Queda (Spec 060) exibe ações que caem há 3 dias com recuperação intraday acima da abertura.
- `instrumentacao_coleta_vazia`: tabela e rotina para registrar quando a coleta de um painel retorna vazia (Spec 056, saúde técnica).
- Spec 046: Fator Peso Pesado (painel de contribuição das 5 maiores ações)
- feat: Implementa Abas de Navegação Contextual (Spec 030). Substitui os botões de filtro por abas no topo que organizam a interface em Visão Geral, Sentimento & Risco, Rankings & Destaques e Alertas Intraday, ocultando os painéis via JS sem recarregar a página. O filtro "Só Sinais" foi incorporado nas abas.
- feat: Adiciona Sparklines nos rankings (Spec 029). Adiciona um minigráfico (SVG) nas tabelas "Maiores altas", "Maiores baixas" e "Força Relativa", ilustrando a performance dos últimos 10 pregões com base em histórico do Yahoo Finance.
### Added
- Migração de tabelas de cache para `snapshots_paineis` (Spec 075a).
- Radar de Exaustão de Queda (Spec 060) exibe ações que caem há 3 dias com recuperação intraday acima da abertura.
- `instrumentacao_coleta_vazia`: tabela e rotina para registrar quando a coleta de um painel retorna vazia (Spec 056, saúde técnica).
- Spec 046: Fator Peso Pesado (painel de contribuição das 5 maiores ações)
- feat: Alerta de Volatilidade Silenciosa (Doji Extremo) (Spec 028). Novo painel na visão micro que exibe as top 3 ações com maior amplitude intraday e fechamento próximo à abertura (≤ 0.5% de variação), refletindo forte indecisão de mercado. Baseado em dados do Yahoo Finance.
### Changed
- agent: `docs/DESIGN.md` reduz o gráfico do Ibovespa para 200px e proíbe eixo Y de preço começando em zero (vai de 2% abaixo do mínimo do período), a pedido do dono do produto.
### Fixed
- fix: Implementa de fato a Spec 086 com datas reais e painel de defasagem (Closes #488).
- fix: JSON cru em 8 painéis e painel Ação Órfã sem tabela, ordenação nem critério
- fix: a Calma da Maré do mercado (Spec 027) passa a medir só a volatilidade de queda (semidesvio com alvo zero). Com o desvio-padrão comum, a alta de 7,42% do Ibovespa em 05/10/2026 zerava a Calma e deixava a Maré em Medo (25) no dia seguinte a uma alta histórica.
- fix: gráfico do Ibovespa com 200px de altura (antes ficava com a altura padrão do Plotly, 450px) e eixo Y a partir de 2% abaixo do mínimo do período, em vez de zero.
### Added
- Migração de tabelas de cache para `snapshots_paineis` (Spec 075a).
- Radar de Exaustão de Queda (Spec 060) exibe ações que caem há 3 dias com recuperação intraday acima da abertura.
- `instrumentacao_coleta_vazia`: tabela e rotina para registrar quando a coleta de um painel retorna vazia (Spec 056, saúde técnica).
- Spec 046: Fator Peso Pesado (painel de contribuição das 5 maiores ações)
- feat: Maré do mercado (Spec 027), índice de otimismo de 0 a 100 ao lado do Ibovespa: Fluxo (40%, volume financeiro em ações que sobem), Calma (35%, percentil da volatilidade de 10 pregões do Ibovespa) e Volume (25%, ritmo contra a média de 21 pregões no sentido da maioria). Gauge com as cinco faixas (Pânico, Medo, Neutro, Confiança, Otimismo extremo), barras dos componentes, linha dos últimos 21 pregões e selo `parcial` quando falta um componente. Chave `mare` no `/api/snapshot` e invariantes no auditor (`checar_mare`). Tendência, Dispersão e Coesão passam para a linha seguinte.
### Fixed
- agent: PR vazio não entra mais. O #171 ("Spec 027a") chegou sem nenhum arquivo, passou no CI e foi mergeado; a Maré do mercado continua sem implementação e a spec 027 segue `ready` na seção Correções. Regra 5 em `devagent/conferir_pr.py` (reprova PR sem alteração em `pull_request` ou com `--exigir-alteracao`) e segunda trava no `automerge.yml`, que fecha o PR vazio sem merge.
### Added
- Migração de tabelas de cache para `snapshots_paineis` (Spec 075a).
- Radar de Exaustão de Queda (Spec 060) exibe ações que caem há 3 dias com recuperação intraday acima da abertura.
- `instrumentacao_coleta_vazia`: tabela e rotina para registrar quando a coleta de um painel retorna vazia (Spec 056, saúde técnica).
- Spec 046: Fator Peso Pesado (painel de contribuição das 5 maiores ações)
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
- Migração de tabelas de cache para `snapshots_paineis` (Spec 075a).
- Radar de Exaustão de Queda (Spec 060) exibe ações que caem há 3 dias com recuperação intraday acima da abertura.
- `instrumentacao_coleta_vazia`: tabela e rotina para registrar quando a coleta de um painel retorna vazia (Spec 056, saúde técnica).
- Spec 046: Fator Peso Pesado (painel de contribuição das 5 maiores ações)
- Painel 'Resiliência (Fator Mola)' para mostrar a recuperação das ações frente à mínima diária.
- Inclusão do 'fator_mola' no payload JSON do `/api/snapshot`.

### Added
- Migração de tabelas de cache para `snapshots_paineis` (Spec 075a).
- Radar de Exaustão de Queda (Spec 060) exibe ações que caem há 3 dias com recuperação intraday acima da abertura.
- `instrumentacao_coleta_vazia`: tabela e rotina para registrar quando a coleta de um painel retorna vazia (Spec 056, saúde técnica).
- Spec 046: Fator Peso Pesado (painel de contribuição das 5 maiores ações)
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
- Migração de tabelas de cache para `snapshots_paineis` (Spec 075a).
- Radar de Exaustão de Queda (Spec 060) exibe ações que caem há 3 dias com recuperação intraday acima da abertura.
- `instrumentacao_coleta_vazia`: tabela e rotina para registrar quando a coleta de um painel retorna vazia (Spec 056, saúde técnica).
- Spec 046: Fator Peso Pesado (painel de contribuição das 5 maiores ações)
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

- (031) Scanner de Capitulação implementado.
- Spec 068: Motor de regras de decisão do Consultor (Comprar, Vender, Aguardar).

- Implementada a spec 069b.
- Divide a especificação 070 sobre opiniões de casas de análise em 070a e 070b.
- Divide a especificação 072 sobre consultor placar em 072a e 072b.
- Spec 72: Consultor · placar de acertos e avaliações na UI.
- Spec 76: Banco · migração dos painéis para snapshots (terceiro lote, parte b).

- Spec 079: Radar de Exaustão de Alta
- spec 084: esquema completo do Consultor no Postgres (tabela de uso de LLM e coluna de fila processada)

- Spec 090b: Tolerância a símbolo inválido

- Spec 090b: Tolerância a símbolo inválido

- Spec 090b: Tolerância a símbolo inválido

- Spec 090b: Tolerância a símbolo inválido
- **108a**: Banco de dados devolve timestamps reais e data da coleta das séries.

* spec 113b: Consultor em data passada exibe o resultado futuro da recomendação.
