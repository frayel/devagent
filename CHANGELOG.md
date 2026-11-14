# Changelog

## [Unreleased]
- Agente: duas lições das retrospectivas de 14/11 viram instrução. A skill `devagent/skills/auto-melhoria.md` manda datar um efeito colateral (`stat -c '%w %y %n'` no arquivo, `ps -o lstart=` no processo) contra a hora de cada comando antes de culpar um deles: quatro retrospectivas atribuíram o `data.db` na raiz à suíte de testes, e a hora de criação apontava o `make smoke` (retrospectiva de 10:40, corrigido no #828). E o modelo de relatório do `devagent/CICLO.md` pede que a melhoria proposta na retrospectiva, quando traz comando ou código, seja rodada na sessão antes de registrada: a proposta `set -m` de 10:40 não funcionava no `dash` (retrospectiva de 11:40, #829).
- Agente: `devagent/smoke.sh` encerra o servidor que subiu e reprova porta já ocupada. Ele matava só o `sh -c` que lançou a aplicação, e o servidor filho continuava vivo segurando a porta: na rodada de 14/11 10:40, o segundo `make smoke` respondeu com o servidor do primeiro, que rodava o código antigo. Agora o smoke encerra a árvore inteira de processos (`pgrep -P`), só sai quando a porta deixa de responder (o encerramento gracioso leva alguns segundos) e reprova logo no início, com "porta ocupada por outro servidor", se o health check já responde antes de a aplicação subir. Pendência da retrospectiva de 14/11 10:40. Novo `devagent/tests/test_smoke.py`.
- Fix: `make smoke` deixa de criar `data.db` na raiz do repositório. O alvo subia a aplicação sem `DATABASE_PATH`, e `app/database.py` cai no caminho padrão `data.db`; como a rodada roda o smoke logo depois do `make verify`, quatro retrospectivas (13/11 18:27, 22:30, 14/11 08:39 e 09:38) culparam a suíte de testes, que o #816 já tinha isolado. O alvo agora aponta `DATABASE_PATH` para um diretório temporário (salvo quando já definido). Novo `tests/test_makefile_smoke.py`.
- Agente: o `devagent/tests/test_estrutura.py` passa a conferir também os índices de skills e contextos. Toda skill de `devagent/skills/` precisa estar no índice da seção 9 do `devagent/CICLO.md`, e todo arquivo de `docs/context/` e `docs/skills/`, no índice do `PRODUTO.md`. As duas tabelas pediam "acrescente-o no mesmo PR" sem nenhum teste, como o mapa da seção 3 antes do #826. Hoje estão completas; o teste impede que envelheçam. Pendência da retrospectiva de 14/11 08:39.
- Agente: a estrutura da seção 3 do `devagent/CICLO.md` passa a listar todos os módulos do núcleo. Ela trazia só `estado_github.py`, `guardiao_prs.py`, `config.py` e `smoke.sh`; faltavam `saude.py`, `fila_specs.py`, `cadencias.py`, `raias.py`, `conferir_pr.py`, `aceite.py` e `instalar.py`, que o próprio ciclo manda rodar ou cita. Também entram `docs/verificacao/` (raia de verificação), `.agents/skills/ciclo/SKILL.md` (a skill `/ciclo`) e as raias paralelas em `devagent/agents/`. Novo `devagent/tests/test_estrutura.py`: arquivo ou pasta de `devagent/` fora do mapa reprova o CI.
- Agente: o `devagent/OPERACAO.md` deixa de dizer que a automação de 2h "roda a persona de especialista (Sentinel na madrugada, Bolt pela manhã)" na sessão do desenvolvedor. Era a mesma contradição com `devagent/agents/especialistas.md` (regra 7) e o ADR 024 que o #823 tirou da skill `/ciclo`, mas ficou no documento de operação: agora especialistas, auditor e raias paralelas rodam em tarefas agendadas próprias, cujo prompt nomeia a persona. A tabela de workflows passa a listar `jules.yml` e `auditoria-llm.yml` como legado só manual, e o `devagent/CICLO.md` deixa de citar um adaptador "antigravity" que não existe em `devagent/adaptadores/`.
- Agente: o ADR da migração para o Antigravity Remote passa a ser o 032 (`devagent/decisoes/032-migracao-jules-para-antigravity.md`). Ele e o do Verificador (#804) foram registrados em paralelo com o mesmo número 031, e o índice da seção 9 do `CICLO.md` listava "031" duas vezes: as citações "ADR 031" no `CICLO.md`, `OPERACAO.md`, `PRODUTO.md`, `devagent/agents/raias.md`, `devagent/raias.py`, `devagent/conferir_pr.py` e na página `/sistema` não diziam qual decisão era. O do Verificador fica com o 031 porque a spec 139 e o `devagent/tests/test_aceite_139.py` fixam esse caminho. Novo `devagent/tests/test_decisoes.py`: número de ADR repetido ou ADR fora do índice reprova o CI.
- Agente: a skill `.agents/skills/ciclo` deixa de mandar o desenvolvedor assumir especialista ou raia auxiliar por horário ou pela fila de specs. Ela listava "Sentinel na madrugada, Bolt pela manhã" e Verificador/Especificador como passo do ciclo, o que contradiz `devagent/agents/especialistas.md` (regra 7) e o ADR 024; as rodadas de 14/11 00:27 e 01:38 BRT ficaram sem critério. Agora a skill percorre os Passos 1 a 7 do `CICLO.md` (antes pulava o 3 e o 5), diz que o `CICLO.md` vale quando os dois divergirem e que personas só entram quando a tarefa as nomeia. Pendência da retrospectiva de 14/11 04:38.
- Agente: a skill `devagent/skills/auto-melhoria.md` pede, na entrega, que toda instrução que manda rodar um comando seja verificada rodando o próprio comando como ficou escrito, no ambiente da sessão, com a saída citada no PR. O #820 pôs `make install` no primeiro comando da execução depois de testar só `python -m pip install -r requirements-dev.txt`, e o alvo quebrou na sessão seguinte (corrigido no #821). Pendência da retrospectiva de 14/11 03:27.
- Fix: `make install` e `make install-prod` seguem quando o pip do sistema não se deixa atualizar. No ambiente das sessões, `python -m pip install --upgrade pip` falha com "Cannot uninstall pip 24.0, RECORD file not found" (pip do Debian), e o alvo parava antes de instalar o `requirements-dev.txt`: o `make install` que o #820 pôs no primeiro comando da execução quebrava logo na primeira sessão seguinte (relatório de 14/11 03:27). A atualização do pip vira melhor esforço (`PIP_UPGRADE` no `Makefile`); a instalação das dependências continua obrigatória. Novo `tests/test_makefile_install.py`.
- Agente: o primeiro comando de toda execução inclui `make install` (`AGENTS.md`, `devagent/CICLO.md`, o modelo em `devagent/modelos/AGENTS.md` e a skill `.agents/skills/ciclo`). O ambiente da sessão não traz as ferramentas fixadas em `requirements-dev.txt`, e desde que o `make verify` passou a usar `$(PY) -m ...` ele falha com "No module named ruff" até alguém instalar à mão; as retrospectivas de 13/11 15:37, 16:38, 14/11 01:37 e 02:10 registram o mesmo passo manual.
- Fix: a página de saúde trata o HTTP 404 da API do Jules como integração desativada (ADR 031), não como atenção. O item *Sessões do Jules* acusava "API do Jules não respondeu" desde 13/11 16:28 porque a `JULES_API_KEY` que sobrou no Render chama um endereço que não existe mais; em 24 h a atenção viraria problema e abriria uma issue `sistema-com-problema` sobre uma integração aposentada. Outros erros (5xx, rede) continuam atenção. Pendência do relatório de 14/11 01:37. Novo teste em `tests/test_sistema.py`.
- Agente: o núcleo deixa de conhecer itens do produto na promoção de 24 h. `devagent/saude.py` (`pendentes`) trazia fixos os nomes "Duração da coleta", "Issues que pedem ação" e o texto "Faltam snapshots" como exceções; agora o contrato da página de saúde tem o campo opcional `envelhece` (padrão `true`), e o produto declara `envelhece=False` nesses três itens de `app/services/sistema.py`. O teste de fronteira não pegava porque os nomes não estão em `termos_do_dominio`. Pendência da retrospectiva de 13/11 21:37. Novo `tests/test_sistema_envelhece.py`.
- Agente: o Passo 1 do `CICLO.md` descreve as duas regras da página de saúde que só existiam no código. Problema com `cura: "entrega"` (contrato de `devagent/saude.py`) não trava o ciclo: a entrega é a correção, como na #807. E uma atenção aberta há mais de 24 h vira problema em `saude.pendentes`, impressa como `PROBLEMA` embora a página diga Atenção. Pendência da retrospectiva de 13/11 16:30 (a de 15:37 apontou a confusão do rótulo).
- Fix: a suíte de testes deixa de criar `data.db` na raiz do repositório. Na coleta, `import app.main` lê o banco (os alertas de `app/collectors/sistema.py` carregam na importação) antes de o fixture `setup_db` existir, com o `DB_PATH` padrão `data.db`. O `tests/conftest.py` define `DATABASE_PATH` num diretório temporário da sessão no nível do módulo, antes de qualquer teste importar a aplicação; subprocessos herdam o caminho. O arquivo esquecido fazia `test_aceite_128::test_healthz_and_root_no_sqlite` falhar de vez em quando (retrospectivas de 13/11 18:27 e 22:30). Novo `tests/test_banco_da_sessao.py`.
- Agente: o checklist do Revisor (`devagent/agents/raias.md`) pede um exemplo numérico de ponta a ponta para toda fórmula, do dado bruto com a unidade de cada campo até o número exibido. A Spec 143 revelou que a fórmula de contribuição copiada da 046 sem a unidade do peso produzia valores 100 vezes maiores desde a 046, e a revisão não pegou porque os critérios de aceite já começavam no resultado (retrospectiva de 13/11 17:38).
- Agente: `make verify` roda `ruff`, `mypy` e `pytest` como módulos do `$(PY)` (`$(PY) -m ...`), o mesmo interpretador em que `make install` instalou as versões fixadas. Um `ruff` mais novo solto no PATH (0.16 em `~/.local/bin`) deixava de entrar no lugar do 0.15.22 fixado e de acusar mais de 600 erros falsos, como aconteceu em três execuções seguidas (13/11 15:37, 16:38 e 18:27).
- Experiência: o fator peso pesado explica o sinal da conta (Spec 143). Razão positiva diz "no mesmo sentido" do Ibovespa, negativa "no sentido oposto", com o módulo como tamanho do movimento; acima de 100% avisa que o restante do índice compensou, sem corte em 100. O teto de ±500% deixa de ser silencioso: o snapshot guarda `proporcao_bruta`, `proporcao` limitada e `limitado`, e o card diz "limitado". Índice a menos de 0,1% mostra "Mercado lateral" sem razão; nome faltando ou denominador zero não publica. Corrige a contribuição em pontos, que tratava o peso 12% como 12 e inflava a razão em 100 vezes. Base do índice pelo `fechamento_anterior` da spec 134. O ⓘ declara pesos (soma 34%) e a base.
- Experiência: a lista de ganhos não repete a pressão vendedora (Spec 142). Concentração de Ganhos lista só contribuições positivas e Pressão Vendedora só negativas, cada uma cortada em 50% da soma do próprio sinal, sem teto escondido de 3 linhas; o N da frase é o número de linhas e a frase diz "K de 10 da cesta". Com o índice em queda, os ganhos "compensam"; com o índice em alta, a pressão "segurou" a alta e o card não some. Parcela acima de 100% deixa de ser cortada. Os dois cards usam o corte de 0,1% de índice estável e o estado vazio sem copiar o outro painel.
- Fix: a página de saúde deixa de acusar tickers que saíram da bolsa. Treze tickers fora da B3 (fusão, troca de código ou fechamento de capital) saem das listas do código ou viram o sucessor (BRAV3, AZZA3, MBRF3, MOTV3, EMBJ3, NATU3). `get_simbolos_suspensos` só lista símbolos que falharam nas últimas 48 h, então CPLE6, ELET3 e "Elet6", que o código não pede mais, saem do alerta. O alerta estava aberto desde 09/11 e virou problema depois de 24 h. O bloco do alerta, que aparecia quatro vezes repetido em `app/services/sistema.py`, agora aparece uma vez só.
- Experiência: cada card diz de qual pregão é o número (Spec 141). Novo `app/services/carimbo.py` (fuso `America/Sao_Paulo`, pregão pela última barra, TTL de 30 min por chave só durante o pregão); cabeçalho com pregão em leitura e "Pregões mistos" quando Ibovespa, Maré, Dispersão e Motores divergem; rodapé com fonte e `dd/mm/aaaa HH:MM BRT` nos quatro cards críticos, Motores incluído; selo `desatualizado`; `pregao` no `/api/snapshot` e `motores_indice` como objeto `{pregao, coletado_em, fonte, motores}`; aviso de coletor que falha sem segredo do ambiente.
- Fix: a main parada deixa de travar o próprio ciclo (#807). O item *Última entrega na main* da página de saúde declara `cura: "entrega"`; `saude.pedem_correcao` ignora problemas que se curam com uma entrega, e o `estado_github` marca a issue `sistema-com-problema` como `cura_por_entrega`, para que `fila_specs.instrucao` volte a indicar a fila em vez de mandar a sessão corrigir só a issue e proibir o resto. Sem isso, nenhuma sessão podia entregar o que fecharia a issue (main parada de 09/11 a 13/11).
- Experiência: a manchete não chama de alta ampla um pregão com poucas ações em alta (Spec 140). Unifica enum de humor em `paineis.manchete` (`alta_ampla`, `baixa_ampla`, `misto`, `sem_direcao`, `indisponivel`); implementa 8 regras em ordem estrita (verificação de pregões coincidentes, revisão de variação, limite de 20% de ações em alta para barrar alta ampla, divergência de motores setoriais, otimismo generalizado com tomada de risco e contagens da amostra); calcula gauge de dispersão excluindo ativos sem variação e atualiza tooltip informativo e legenda.
- Saúde técnica: o Verificador vê todo merge na main e examina todo PR que mexe num limite (Spec 139). `merges_do_desenvolvimento` deixa de filtrar por `do_agente`, incluindo merges feitos por pessoas; adiciona paginação até 5 páginas; prioriza PRs `[sensor]` (que alteram `auditoria/` ou mexem em limites/tolerâncias no `patch`) no início do prompt; evita corte silencioso trazendo 15 mais recentes + todos os sensores e indicando PRs omitidos; atualiza checklist em `raias.md` com *Verdade do número* e *Sensores*; registra ADR 031 no núcleo e no índice de `CICLO.md`.
- Saúde técnica: a auditoria confere a variação do dia do Ibovespa, não só o preço (Spec 138). Adiciona checagem interna `ibov.fechamento_anterior_coerente` (valida se o fechamento anterior coincide com o penúltimo ponto do gráfico quando o valor coincide com o último) e externa `ibov.variacao_confere_com_fonte` (compara a variação percentual do dia com a variação calculada pela fonte independente com tolerância de até 0,5 p.p., constante `TOLERANCIA_VARIACAO`). Registra em comentário o escopo de `ibov.variacao_coerente` e documenta as checagens no `auditoria/README.md`.
- Saúde técnica: a fonte de referência da auditoria nunca é a que o produto usou (Spec 137). Cria tabela explícita ligando referências da auditoria (ref_yahoo, ref_stooq) às fontes excluídas do produto (yfinance, yahoo, stooq), normaliza rótulos compostos por `+`, sinaliza aviso para fontes desconhecidas e detalha ambas as pontas (produto e referência) nos resultados da auditoria.
- Saúde técnica: confirmação por segunda fonte de variação extrema do Ibovespa (Spec 136). Exige confirmação entre MT5 e Yahoo Finance para variações entre 10% e 20% com tolerância de até 0,5 p.p.; adiciona contexto ignorado() em mt5.py para consulta direta ao Yahoo; mantém descarte de variações acima de 20%; atualiza referências ao caso relatado de 15,99% em 29/10/2026 em app/, auditoria/ e changelog.
- Saúde técnica: variação diária das ações sem janela de 15 dias e quarentena de outliers (Spec 135). Corrige o cálculo de previous_close em `highlights.py` compartilhando a função `fechamento_anterior` em `app/collectors/utils.py` sem ler `chartPreviousClose`, adiciona quarentena de variação extrema (`|change_percent| > 15.0%`) com confirmação de segunda fonte (MT5/Yahoo) e lista "Em revisão", adiciona títulos dinâmicos com a data do pregão da série ("Maiores altas · pregão dd/mm/aaaa"), tratamento de tickers sem base no rodapé, dublê do Yahoo fiel a `range` e teste de fronteira contra o uso indevido de `chartPreviousClose`.
- Saúde técnica: variação do Ibovespa do dia e sinal de revisão (Spec 134). Corrige o cálculo de previous_close pelas 4 regras sem chartPreviousClose, adiciona limiares de revisão (3,0% ou 5000 pts) com selo "em revisão", trata fechamento ausente com estado indisponível sem 0,00%, e ajusta título dinâmico ("Ibovespa hoje" / "Ibovespa") e carimbo de data/hora em BRT.
- Poda: remoção de arquivos mortos na raiz e configuração centralizada de log (Spec 133). Remove imagens e arquivos de texto órfãos da raiz, código morto não utilizado em `app/main.py` (`security = HTTPBasic()`, `verificar_credenciais`), atualiza `.gitignore` e centraliza `logging.basicConfig` no início de `app/main.py`, removendo configurações de log como efeito colateral na importação de 21 coletores.
- Saúde técnica: migração de formato de consenso para JSON no banco do Consultor (Spec 132c). Converte de forma idempotente em init_db registros legados gravados em repr de dicionário Python para JSON válido.
- Fix: preserva detalhes de falhas sistêmicas e evita sobreposição do último erro no agendador (#769). Exceções na inicialização dos painéis não são mais mascaradas como "erro fatal" genérico em `estado["detalhes"]`, e falhas de infraestrutura (banco, rede, disjuntor) têm precedência e são preservadas em `estado["ultimo_erro"]` em vez de serem sobrescritas por falhas pontuais de coletores posteriores.
- Fix: resolve travamento do disjuntor na partida a frio e falha na coleta do Ibovespa (#793). Reseta o disjuntor no `abrir_pool`, remove execução precipitada de `init_db()` na importação de `app/database.py`, evita abertura de disjuntor de 30 s para contenção temporária de pool (`PoolTimeout`), adiciona retentativa de gravação no salvamento do Ibovespa e saneia `[::1]` em `NO_PROXY`/`no_proxy` evitando `InvalidURL` no httpx. Corrige também fuso horário BRT nas consultas de instrumentação.
- Fix: desativa alerta de cron-job.org na página /sistema por padrão (ADR 031), marcando o item como Inativo quando `JULES_DISPARO_MINUTOS` não estiver configurado ou for 0, eliminando alarme falso de produção (#789).
- Fix: corrige cálculo de `previous_close` do Ibovespa para usar o pregão anterior em vez do fechamento de 1 ano atrás (`chartPreviousClose`), destravando a coleta do índice e restaurando o avanço do gráfico até o pregão mais recente (#787, #791, #772, #774). Trata também `DBInacessivelError` em `ler_snapshot` para evitar falha fatal em jobs em segundo plano.
- agent: migração do executor Jules para o Antigravity Remote e modelo híbrido (ADR 031). Suporte a marcador de raia no corpo do PR (`<!-- devagent:raia:... -->`) para validação de disciplina no CI sem chamadas de rede; diários dos especialistas em `.agents/` (com fallback retrocompatível a `.jules/`); reconhecimento do usuário do Antigravity no guardião e na conferência; remoção dos crons de schedule do GitHub Actions; criação da skill e comando `/ciclo`.
- Fix: Spec 132a - Leitura do consenso e remoção de literal_eval em main.py
- Spec 131: Histórico do Consultor sem consultas repetidas por recomendação
- Spec 126a: Agendador sem trabalho repetido (backtest único).
- **Fontes**: a brapi.dev foi removida. O MetaTrader 5 é a fonte preferencial e o Yahoo Finance a reserva; o Termômetro de Concentração de Ordens depende só do MT5. A variável `BRAPI_TOKEN` deixa de existir e pode ser apagada do painel do Render.
- **Concentração de Ordens**: o número de negócios passa a vir do MetaTrader 5 (`tick_volume` da barra diária, exposto pela ponte como `regularMarketTrades`). A brapi fica só como reserva até ser removida. Era o último painel que dependia exclusivamente dela.
- Spec 130: Página inicial não bloqueia mais o servidor e tem cache local (painéis agrupados por requisição).
- 127
- Spec 125a: intervalo de tentativa de fechamento alterado para 30 min até 20h.
- Spec 124: Seletor de pregão mostra os números do dia escolhido em todos os painéis, isolando leitura com lendo_pregao.
- Spec 129: o Postgres passa a usar um pool de conexões. Antes, cada leitura abria uma conexão nova (em 29/10, cerca de 1,6 s cada), e a `/sistema` e a página inicial demoravam segundos. O item Banco de dados da `/sistema` mostra o custo de abrir conexão e acusa Atenção acima de 500 ms.
- **Sistema**: o item Banco de dados mostra a versão do servidor e o tamanho do banco em uso. Documentação atualizada: o Postgres de produção não é mais o Neon (ADR 009).
- Fix: o coletor do Ibovespa aceita variação diária de até 20% (era 12%). Caso relatado em 29/10/2026 de que o índice teria variado 15,99% com o circuit breaker estendido (relatado, não confirmado por fonte independente), e o dado era descartado.
- Fix: a página `/sistema` não conta mais issue `producao-incorreta` ou `deploy-falhou` como Problema próprio; elas aparecem como Atenção, e a `sistema-com-problema` deixa de depender delas para fechar.
- Fix (#592): a página inicial respondia 500 com snapshot da Maré gravado antes da spec 123 (`ativos_json` obrigatório). O campo ganhou padrão e a leitura ignora chaves de outras versões.
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
- Spec 125b: Fechamento que falhou vira incompleto depois das 20h.
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
- spec 132b: Gravação do consenso em JSON no coletor implementada.
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
- spec 132b: Gravação do consenso em JSON no coletor implementada.
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
- spec 132b: Gravação do consenso em JSON no coletor implementada.
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
- Redução de transferência de banco de dados no Neon (Spec 122).

- Correcao brapi e spec 121b- Spec 123 (Heatmap visual da Maré do Mercado):
  - Adiciona propriedade `ativos_json` ao DB para rastrear principais ativos.
  - Altera front-end `app/templates/index.html` para expor via estilo inline o top-10 do fluxo e volume no pregão diário no painel da maré.
- Fecha Issues #557 (Remoção código morto da Maré) e #570.
- Spec 126b (Agendador sem trabalho repetido: feriado fora do pregao): intervalo() agora trata corretamente feriados como dias sem pregao.

- Spec 128: Postgres fail-fast implementado com disjuntor.