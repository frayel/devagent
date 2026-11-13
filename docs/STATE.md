- Spec 125a (Intervalo de tentativa de fechamento a cada 30 min até 20h):
  - O agendador agora tenta um novo fechamento a cada 30 minutos entre as 18h15 e 20h, em vez de esperar 2 horas.
  - Nenhum painel novo: o contador da cadência de experiência não muda.

- Spec 121a entregue: Sistema de alertas na página `/sistema` ganhou campos `causa` e `acao` baseados na classificação dos detalhes do erro.
# Estado do Sistema

> **Coleta em produção (2026-09-27):** até esta data nenhuma coleta rodava em produção; o painel exibia "Dados não disponíveis". A coleta agora roda no próprio web service (`app/agendador.py`, ADR 004). Diagnóstico: `GET /api/coleta`.

## Cadências

Os contadores das cadências do Passo 7 não ficam mais aqui: são calculados a partir das specs com `python -m devagent.cadencias` (ADR 024 do núcleo). Última revisão de experiência registrada à mão: 2026-10-19. Última rodada de manutenção registrada à mão: 2026-10-17, spec 063. Linha de base de manutenção: ainda não medida.

## Implementado
- [Experiência] Spec 143 - O fator peso pesado explica o sinal da conta:
  - `app/services/fator_peso_pesado.py` monta a apresentação do card e do `/api/snapshot` (`valor`, `sentido`, `frase`, `proporcao`, `proporcao_bruta`, `limitado`). Sinal com menos tipográfico (−), uma casa, padrão brasileiro.
  - `app/collectors/fator_peso_pesado.py`: contribuição = var% / 100 × peso / 100 × IBOV anterior (antes o peso entrava como 12 em vez de 12%, e a razão saía 100 vezes maior, quase sempre no teto). Grava `proporcao_bruta` e `proporcao` limitada a ±500%; denominador zero e nome faltando não gravam. Fechamento anterior por `fechamento_anterior` (spec 134), com `chartPreviousClose` só como último recurso em `range=1d`.
  - Testes de aceite em `tests/test_aceite_143.py`.
- [Experiência] Spec 142 - A lista de ganhos não repete a pressão vendedora:
  - `app/collectors/concentracao.py`: os dois coletores compartilham `_historico`, `_contribuicoes` e `_corte_metade`. Concentração de Ganhos lista só pontos teóricos positivos; Pressão Vendedora, só negativos. Cada lista corta em 50% da soma das contribuições do próprio sinal, sem teto de 3 ou 5 linhas, e grava todas as linhas em `top3_json` (o nome do campo ficou por compatibilidade com o `/api/snapshot`).
  - Frases: o N é o número de linhas e "K de 10 da cesta" diz quantos tickers tinham base e último preço. Índice em queda: ganhos "compensam" a queda. Índice em alta: a pressão "segurou" a alta, e o card não some mais. Parcela acima de 100% não passa por `min(100, ...)` e avisa que o restante da cesta compensou.
  - Os dois cards usam o corte de 0,1% (`Ibovespa estável, sem concentração definida.`) e o estado `vazio` quando não há contribuição do sinal, sem copiar a lista do outro painel.
  - Testes de aceite em `tests/test_aceite_142.py`.
- [Fix] Tickers fora da bolsa saem das listas e do alerta do Yahoo (Passo 1, problema da página de saúde):
  - Treze tickers que saíram da B3 ou trocaram de código ficaram nas listas do código, e o Yahoo responde 404 para eles. Viraram o sucessor: RRRP3→BRAV3, ARZZ3/SOMA3→AZZA3, BRFS3/MRFG3→MBRF3, CCRO3→MOTV3, EMBR3→EMBJ3, NTCO3→NATU3. Saíram sem sucessor: AZUL4, CIEL3, CRFB3, JBSS3, PETZ3. Arquivos: `app/consultor/universo.py`, `sensibilidade_juros.py`, `assimetria_risco_retorno.py`, `concentracao_ordens.py`.
  - `banco.get_simbolos_suspensos` só lista símbolos que falharam nas últimas 48 h (`JANELA_SIMBOLO_PEDIDO`): ticker que o código não pede mais (CPLE6, ELET3, "Elet6") sai do alerta.
  - A carteira em `universo.py` não foi conferida contra a B3 nesta correção (só os sucessores diretos). A conferência completa é a spec 094 (draft).
  - Testes em `tests/test_simbolos_sem_cotacao_saude.py`.
- [Experiência] Spec 141 - Cada card diz de qual pregão é o número:
  - Helper único `app/services/carimbo.py`: formata `dd/mm/aaaa HH:MM BRT` em `America/Sao_Paulo`, deriva o pregão do número da última barra (nunca promove D−1 a D0) e marca desatualizado só durante o pregão (10:00–17:00 de dia útil), com TTL de 30 min por chave (`TTL_MINUTOS`).
  - Cabeçalho mostra o pregão em leitura e o as-of a partir de Ibovespa, Maré, Dispersão e Motores; datas divergentes viram "Pregões mistos"; sessão anterior ao último pregão esperado diz "pregão anterior".
  - Rodapé dos quatro cards críticos com fonte e carimbo (e o pregão quando difere do dia da coleta); Motores ganhou rodapé e, sem carimbo, fica indisponível; selo `desatualizado` no token `--alerta` sem apagar o número.
  - `/api/snapshot`: `ibovespa`, `mare`, `altas_baixas` e `motores_indice` ganham `pregao`; `motores_indice` vira objeto `{pregao, coletado_em, fonte, motores}`. A manchete recebe os mesmos pregões.
  - Agendador: coletor que falha registra aviso com fonte e tipo da exceção, com segredos do ambiente mascarados; o snapshot anterior mantém o `coletado_em`.
  - Testes de aceite em `tests/test_aceite_141.py`.
- [Experiência] Spec 140 - A manchete não chama de alta ampla um pregão com poucas ações em alta:
  - Definido enum único de humor: `alta_ampla`, `baixa_ampla`, `misto`, `sem_direcao`, `indisponivel`.
  - Implementadas as 8 regras da manchete em ordem estrita em `app/services/manchete.py`:
    1. Sem Ibovespa ou variação indisponível -> `indisponivel` ("Resumo do mercado indisponível no momento.").
    2. Pregões divergentes entre Ibovespa, dispersão ou motores -> `indisponivel` ("Os painéis não estão no mesmo pregão; a leitura do dia fica suspensa.").
    3. `revisao_variacao` verdadeiro -> `misto` (movimento em revisão, sem menção a otimismo generalizado ou alta ampla).
    4. `fracao_em_alta < 0.20` com índice positivo -> `misto` com sinal do índice e contagens de altas, baixas e total.
    5. Conflito de motores (2 ou mais motores com sinal oposto ao do índice) -> `misto`.
    6. Sem conflito, sem revisão, índice positivo, `fracao_em_alta >= 0.50` e apetite "Tomando risco" -> `alta_ampla` ("Dia de otimismo generalizado com forte tomada de risco."). Espelho de baixa ("Defensivo") mantido.
    7. Sinais mistos com contagens da amostra; avisa sobre motores ausentes quando não for regra 6.
    8. Variação do índice igual a zero -> `sem_direcao` ("O mercado opera sem direção definida.").
  - Gauge de dispersão mantido em `up_count / (up_count + down_count)` com neutros no `total_count`; tooltip atualizado indicando exclusão de quem ficou em zero; legenda com suporte a contagem de neutros/estáveis.
  - Endpoint `/api/snapshot` passa a publicar `paineis.manchete` com `humor`, `texto`, `coletado_em` e `fonte`.
  - Testes de aceite completos em `tests/test_aceite_140.py`.
- [Saúde Técnica] Spec 139 - O Verificador vê todo merge na main e examina todo PR que mexe num limite:
  - `merges_do_desenvolvimento` em `devagent/adaptadores/jules.py` deixa de filtrar por `do_agente`, incluindo PRs da raia de desenvolvimento abertos por humanos.
  - Implementada paginação na busca de PRs fechados até encontrar uma página anterior a `desde`, com limite de 5 páginas.
  - Priorização de sensores via `checar_sensor_pr` e `PADRAO_SENSOR`: PRs que alteram `auditoria/` ou modificam limites (`MAXIMO/A`, `LIMITE`, `TOLERANCIA`, `TETO`) no `patch` são marcados `[sensor]` e ordenados no início do prompt.
  - Fallback gracioso para falha na listagem de arquivos (`/files`): o PR entra sem marca e com indicação `arquivos não consultados`.
  - O prompt lista os 15 PRs mais recentes mais todos os `[sensor]`, indicando `+N PRs omitidos; liste com git log --merges` quando restarem PRs de fora.
  - Checklist em `devagent/agents/raias.md` atualizado com itens *Verdade do número* e *Sensores*.
  - Registrado ADR 031 (`devagent/decisoes/031-verificador-ve-todo-merge-e-todo-sensor.md`) e atualizado índice de ADRs no `devagent/CICLO.md`.
  - Testes de aceite completos em `devagent/tests/test_aceite_139.py`.
- [Saúde Técnica] Spec 138 - A auditoria confere a variação do dia do Ibovespa, não só o preço:
  - Adicionada constante `TOLERANCIA_VARIACAO = 0.5` (0,5 ponto percentual).
  - Implementada checagem interna `ibov.fechamento_anterior_coerente` em `checar_coerencia`: se o valor exibido coincide com o último ponto do gráfico (tolerância de 0,05%), exige que `fechamento_anterior` coincida com o penúltimo ponto do gráfico (mesma tolerância); caso contrário, falha explicitando ambos os valores. Se o valor diferir do último ponto (ex.: antes da abertura) ou se o dado estiver ausente, gera `inconclusivo`.
  - Implementada checagem externa `ibov.variacao_confere_com_fonte` em `checar_referencia`: calcula a variação da fonte independente entre o fechamento do dia `d` e o último fechamento anterior `a`, comparando com `variacao_pct` com tolerância de até 0,5 p.p.; gera `inconclusivo` caso não haja referência, `a` não exista, ou a referência coincida com a fonte do produto.
  - Adicionado comentário de esclarecimento sobre o escopo e limitações de `ibov.variacao_coerente`.
  - Documentação atualizada em `auditoria/README.md`.
  - Testes de aceite completos em `tests/test_aceite_138.py`.
- [Saúde Técnica] Spec 137 - A fonte de referência da auditoria nunca é a que o produto usou:
  - Tabela explícita `FONTES_EXCLUIDAS` em `auditoria/auditar.py`: `ref_yahoo` é excluído por `yfinance` e `yahoo`; `ref_stooq` é excluído por `stooq`; `mt5` não exclui nenhuma das referências.
  - Função `obter_referencia(evitar)` quebra rótulos compostos por `+` (ex.: `yfinance+mt5`), normaliza em caixa baixa e descarta qualquer referência cujo conjunto de exclusão tenha interseção com as fontes do produto.
  - Rótulos desconhecidos não descartam referências e registram aviso `fonte do produto desconhecida: <rótulo>`.
  - Detalhamento de `ibov.confere_com_fonte` e `ibov.historico_confere` exibe ambas as pontas: `produto: <rótulo>; referência: <nome>`.
  - Se todas as referências forem descartadas ou estiverem indisponíveis, `ibov.fonte_independente` assume status `inconclusivo` explicando os motivos, nunca gerando `OK`.
  - Tabela documentada em `auditoria/README.md`.
  - Testes de aceite completos em `tests/test_aceite_137.py`.
- [Saúde Técnica] Spec 136 - Variação extrema do Ibovespa só entra se segunda fonte confirma:
  - Adicionado gerenciador de contexto `ignorado()` e função `em_modo_ignorado()` em `app/collectors/mt5.py` para permitir que chamadas ao Yahoo sigam diretamente à rede sem interceptação do MT5.
  - No coletor `app/collectors/ibovespa.py`, variações de magnitude normal (`|variação| <= 10%`) gravam sem chamadas extras.
  - Variações extremas (`10% < |variação| <= 20%`) consultam a outra fonte (`obter_variacao_segunda_fonte`): se MT5, consulta Yahoo com `mt5.ignorado()`; se Yahoo, consulta MT5 com `mt5.exclusivo()`. Se concordarem em até 0,5 p.p., o dado é gravado com a fonte primária e log de confirmação; se divergirem ou não houver segunda fonte, a gravação é recusada (retorna `False`) e as variações são logadas.
  - Variações acima de 20% continuam sendo sempre descartadas.
  - Menções ao caso de 29/10/2026 foram atualizadas em `app/`, `auditoria/` e `CHANGELOG.md` para indicar caso relatado e não confirmado por fonte independente.
  - Testes de aceite completos em `tests/test_aceite_136.py`.
- [Saúde Técnica] Spec 135 - Variação diária das ações sem janela de 15 dias e quarentena de outliers:
  - Compartilhada a função `fechamento_anterior` em `app/collectors/utils.py` com as 4 regras sem acessar `chartPreviousClose`, utilizada por `highlights.py` e `ibovespa.py`.
  - Quarentena de variação extrema (`OUTLIER_VARIACAO_DIA = 15.0`): variações acima de 15% tentam confirmação com a segunda fonte (`consultar_segunda_fonte`); se confirmada até 0,5 p.p., retorna ao ranking diário com fontes combinadas; caso contrário, é movida para a lista `em_revisao` (`paineis.altas_baixas.em_revisao` no snapshot).
  - Títulos dos painéis de altas e baixas exibem dinamicamente a data do pregão da série ("Maiores altas · pregão dd/mm/aaaa").
  - Tickers sem base ou preço não alteram `up_count` nem `down_count` e são reportados no rodapé ("Faltou dado para ...").
  - `tests/yahoo_falso.py` fiel ao parâmetro `range` da URL (15d com 15 barras e `chartPreviousClose` anterior à primeira barra; penúltimo close em `previousClose`).
  - Teste de fronteira `tests/test_fronteira_chart_previous_close.py` varre coletores e impede leitura de `chartPreviousClose` com `range != 1d`.
  - Testes de aceite completos em `tests/test_aceite_135.py`.
- [Saúde Técnica] Spec 134 - Variação do Ibovespa do dia e sinal de revisão:
  - Definidas as constantes `LIMIAR_PCT_REVISAO = 3.0` e `LIMIAR_PONTOS_REVISAO = 5000.0` no coletor de Ibovespa.
  - O cálculo de `previous_close` em `app/collectors/ibovespa.py` segue as 4 regras da spec sem acessar `chartPreviousClose`.
  - Tratamento de fechamento ausente em `app/services/ibovespa.py` e `app/main.py`: `variacao_indisponivel: True`, variação percentual nula e `estado: "indisponivel"`, sem exibir `0,00%` no card.
  - Variações extremas acima dos limiares ativam `revisao_variacao: True`, exibindo o selo `<span class="selo alerta selo-revisao">em revisão</span>` e mantendo tom neutro no badge de variação.
  - Título do card ajustado dinamicamente para `"Ibovespa hoje"` apenas se a coleta for da data civil atual em BRT, ou `"Ibovespa"` para pregões anteriores.
  - Testes de aceite completos em `tests/test_aceite_134.py`.
- [Poda] Spec 133 - Poda de arquivos mortos e configuração de log na importação:
  - Removidos arquivos órfãos da raiz: `commit_description.txt`, `screenshot_desktop.png`, `telas_desktop.png` e `verification.png`.
  - Atualizado `.gitignore` com regras para ignorar `*.db` e `*.png` na raiz, e `commit_*.txt`.
  - Removido código morto em `app/main.py` (`security = HTTPBasic()`, `verificar_credenciais` e import de `Depends`).
  - Centralizada a configuração de `logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")` no início de `app/main.py`.
  - Removidas chamadas a `logging.basicConfig` que causavam efeito colateral de configuração global de log na importação de 21 coletores em `app/collectors/`.
  - Criados testes de aceite em `tests/test_aceite_133.py`.
- [Saúde Técnica] Spec 132c - Migração de formato de consenso para JSON:
  - Implementada função idempotente `migrar_consenso_para_json` em `app/consultor/armazenamento.py`, chamada durante `init_db()`.
  - Converte registros legados gravados em formato `repr` de dicionário Python (`"{'compra': 3}"`) para JSON equivalente (`'{"compra": 3}'`) usando `ast.literal_eval` seguro e `json.dumps`.
  - Registros já em JSON válido ou textos simples que não são dicionários avaliáveis são preservados sem alterações.
  - Testes de aceite cobrem conversão, idempotência e compatibilidade com `/api/consultor` em `tests/test_aceite_132c.py`.
- Preservação e detalhamento de falhas sistêmicas no Agendador (#769):
  - Exceções na inicialização/verificação dos painéis em `app/agendador.py` passam a ser registradas em `estado["detalhes"]` com a mensagem real do erro (incluindo o prefixo `erro fatal: <mensagem>`), em vez de serem ofuscadas por uma string genérica.
  - Implementada função `_registrar_erro` que prioriza e preserva falhas sistêmicas/infraestrutura (banco indisponível, disjuntor aberto, timeout) em `estado["ultimo_erro"]`, impedindo que falhas pontuais de fontes ("nenhuma fonte respondeu") em coletores posteriores sobrescrevam o erro raiz do ciclo.
- Correção de resiliência do disjuntor e coleta do Ibovespa (#793):
  - Resolvido travamento do disjuntor na partida a frio em ambientes com Postgres configurado (Render/Supabase): `_reset_disjuntor()` executado após `abrir_pool()` no lifespan.
  - Removida chamada indevida de `init_db()` na importação de `app/database.py`, garantindo cumprimento da spec 128 (nenhuma conexão ao banco na importação de módulos).
  - Ajustado `_ConexaoDoPool` para não abrir disjuntor de 30 s para `PoolTimeout` (contenção temporária de pool de conexões) e abrir o pool sob demanda se fechado.
  - Adicionadas retentativas com backoff em `save_ibovespa_data` para proteger contra oscilações de boot.
  - Saneamento de loopback IPv6 `[::1]` em `NO_PROXY`/`no_proxy` para evitar `httpx.InvalidURL: Invalid port: ':1]'`.
  - Fuso horário BRT corrigido em consultas de instrumentação de coletas.
- Migração para Antigravity Remote e modelo híbrido (ADR 031):
  - Validação de raias no CI via marcador HTML no corpo do PR (`<!-- devagent:raia:<nome> -->`), sem chamadas de rede à API externa do Jules.
  - Pasta `.agents/` para diários dos especialistas (com fallback retrocompatível a `.jules/`).
  - Reconhecimento dos logins do Antigravity no guardião de PRs e conferência de disciplina.
  - Removido schedule de cron do GitHub Actions (`jules.yml` e `auditoria-llm.yml`).
  - Criada skill `/ciclo` (`.agents/skills/ciclo/SKILL.md`) para execução autônoma.
- [Saúde Técnica] Spec 132a - Leitura tolerante de consenso (JSON, dict, texto) implementada e `ast.literal_eval` removido de `app/main.py`.

- Spec 131: Histórico do Consultor sem consultas repetidas por recomendação
  - contador de painéis: 1

- Remoção da brapi.dev (04/11/2026, a pedido do dono do produto):
  - Saíram `app/collectors/brapi.py`, os ramos `fetch_brapi` de Ibovespa, maiores altas e baixas, coesão, concentração setorial, fator mola, radar de spread, Maré e concentração de ordens, a variável `BRAPI_TOKEN` e o item brapi da `/sistema`.
  - As fontes de mercado passam a ser MetaTrader 5 (preferencial) e Yahoo Finance. O número de negócios do Termômetro de Concentração de Ordens vem só do MT5; sem ele, o painel mostra Dados indisponíveis.
  - As menções à brapi nas entradas abaixo descrevem o estado da época.

- Spec 129 (Pool de conexões do Postgres):
  - `app/banco.py`: `get_connection()` empresta uma conexão de um `psycopg_pool.ConnectionPool` (1 a 5 conexões, espera de 10 s, conexão testada antes de ser entregue); o `close()` do invólucro devolve ao pool. Os chamadores não mudaram.
  - O pool abre e fecha no `lifespan` de `app/main.py`; o SQLite segue sem pool.
  - `/sistema`, item Banco de dados: mostra quanto custa abrir uma conexão e fica em Atenção a partir de 500 ms, com a ação de usar o endereço interno do Postgres.
  - Implementada antes da spec 128 (disjuntor), porque a `/sistema` levava segundos com cada conexão nova custando cerca de 1,6 s em produção.

- Spec 095 (Testes sem rede):
  - Bloqueio de conexões socket no pytest (`conftest.py`).
  - Marker `pytest.mark.rede`.
  - Isolamento do `make verify` das chamadas na internet e mocking de `consultor_opinioes` nos testes ponta a ponta.

- Spec 087 (Consultor abre em poucos segundos):
  - Consulta em lote no histórico (`ler_series`).
  - Guardião de inicialização de esquema em processo único.
  - Escrita fora da visita com o agendamento de fechamento.
  - Cache de visão temporário com TTL.
- Spec 085 (Consultor Motivos Sem Opinião):
  - Substituição da frase "Nenhuma opinião recente" por 7 diagnósticos.
  - Atualização do banco Postgres e SQLite para suportar as colunas de data da ultima extração, matérias processadas e descartadas.
- Spec 081 (Rastreador de Correlação com DI):
  - Coletor buscando fechamentos intraday recentes para Juros Futuros (DI1F27/DI1F29) via `yfinance`.
  - Cálculo de correlação com o Ibovespa (15 min intraday e diário de 5 dias).
  - Exibição de correlação no painel.
- Spec 082 (Página de sistema):
  - `/sistema` e `/api/sistema`, protegidas pela `CONSULTOR_SENHA`; link "Sistema" no cabeçalho.
  - `app/collectors/registro_fontes.py`: resultado final de cada chamada às fontes externas, por integração.
  - `app/collectors/sistema.py`: monitor em segundo plano do GitHub, do Jules e do Render (5 min com `GITHUB_TOKEN`, 20 min sem).
  - `app/services/sistema.py` e `app/services/cron.py`: níveis de cada verificação e agendamentos perdidos.

- Spec 068b (Consultor Regras de Decisão):
  - Lógica de avaliação de regras de análise técnica.
  - Endpoint /api/consultor com o histórico completo e cálculos executados on the fly.
  - Interface do consultor construída agrupada por recomendações.

- Spec 080 (Simplificação de Painéis de Alerta):
  - Modificado o `app/templates/index.html` para não renderizar a estrutura completa de alertas (cards e tabelas) quando a lista de alertas está vazia.
  - Adicionado um bloco único "Sem alertas ativos no momento" na aba de alertas.

- Spec 067 (Poda do Painel Ação Órfã):
  - Removido o painel Ação Órfã da página inicial.

- Spec 065 (Análise de Assimetria Risco/Retorno):
  - Banco de dados SQLite (`assimetria_risco_retorno_cache`).
  - Coletor com yfinance (endpoint spark 30d).
  - Exibição de ações muito próximas da mínima (<=2%) e distantes da máxima (>=10%) nos últimos 30 dias.
  - Adicionado painel em rankings e no contrato `/api/snapshot`.

- Spec 064 (Divergência Ibovespa vs Dólar):
  - Banco de dados SQLite (`divergencia_ibov_dolar_cache`).
  - Coletor buscando dados intradiários do Ibov e Dólar.
  - Alerta de correlação positiva.
  - Adicionado ao contrato `/api/snapshot`.

- Spec 062 (Instrumentação de Tempo de Coleta):
  - Banco de dados SQLite (`instrumentacao_coleta_tempo`).
  - `app/agendador.py` registra e salva o tempo de execução de cada painel para basear futuras podas.
- Spec 061 (Experiência Ordem do Topo):
  - Reorganizado `app/templates/index.html` para mover os painéis 'Clima Global' e 'Motores do Índice' para baixo do 'Ibovespa' e 'Maré', garantindo a hierarquia visual acima da dobra.
- Spec 060 (Radar de Exaustão de Queda):
  - Banco de dados SQLite (`exaustao_queda_cache`).
  - Coletor com `yfinance` para queda de 3 dias, gap de baixa e recuperação intraday.
  - Exibição na visão micro.
  - Adicionado ao contrato `/api/snapshot`.

- Spec 059 (Termômetro de Exaustão de Tendência):
  - Banco de dados SQLite (`exaustao_tendencia_cache`).
  - Coletor com yfinance buscando dados `spark` diários.
  - Painel "Exaustão de Tendência" adicionado na seção "Alertas Intraday".
  - Chave `exaustao_tendencia` no `/api/snapshot`.
- Spec 058 (Termômetro de Concentração de Ordens):
  - Banco de dados SQLite (`concentracao_ordens_cache`).
  - Coletor buscando `regularMarketTrades` via `brapi`.
  - Cálculo de ticket médio intraday (Volume Financeiro / Trades).
  - Exibição de painel na `visao-micro`.
  - Adicionado ao contrato `/api/snapshot`.


- Spec 057 (Radar de Anomalias de Spread):
  - Banco de dados SQLite (`anomalias_spread_cache`).
  - Coletor buscando bid e ask para cesta de liquidez (`brapi` primário, `yfinance` fallback).
  - Cálculo de variação percentual do spread atual para as 10 ações mais líquidas.
  - Exibição de painel em Alertas Intraday e `/api/snapshot`.

- Spec 056 (Instrumentação de Coleta Vazia):
  - Banco de dados SQLite (`instrumentacao_coleta_vazia`).
  - Registra a hora e o painel quando uma coleta falha ou retorna vazia.

- Spec 055 (Experiência: Fusão de Globais):
  - Reorganizada seção Visão Geral no `index.html`.
  - Reduzido tamanho do "Clima Global" e "Motores do Índice" para span-6 para caberem lado a lado na mesma linha.

- Spec 053 (Relógio de Volatilidade Intraday):
  - Coletor com yfinance buscando dados intraday (^BVSP) em formato 15m.
  - Cálculo de amplitude máxima para encontrar pico de volatilidade.
  - Exibição de painel em "Alertas Intraday" e `/api/snapshot`.

- Spec 052 (Termômetro de Clima Externo):
  - Banco de dados SQLite (`clima_global_cache`).
  - Coletor buscando S&P 500 Futuros e VIX via `yfinance` e calculando a variação e o status de humor (Apetite/Aversão/Neutro).
  - Exibição de painel na visão geral cruzando os indicadores.
  - Adicionado ao contrato `/api/snapshot`.

- Spec 051 (Experiência: Densidade Dinâmica da Grade):
  - Adicionado toggle (Confortável/Compacto) no cabeçalho das abas para alterar paddings e espaçamentos (classe `.compacto` via CSS).
  - Estado armazenado no `localStorage` via JavaScript.


- Spec 046 (Fator "Peso Pesado"):
  - Banco de dados SQLite (`fator_peso_pesado_cache`).
  - Coletor com yfinance buscando ^BVSP e top 5 ações por peso para calcular a contribuição no movimento.
  - Exibição de painel na visão macro com a proporção.
  - Adicionado ao contrato `/api/snapshot`.
  - Contador da cadência de experiência: 1.

- Spec 045 (Destaque Visual para a Maré):
  - Ajuste de espaçamento e respiro do painel `.painel-mare` com `padding` e `gap` ajustados no CSS, conforme guia visual.
  - Ocultação parcial/diminuída a opacidade dos itens componentes para dar mais destaque ao gauge.
  - Nenhum painel novo: o contador da cadência de experiência não muda.

- Spec 044 (Radar de Absorção Cruzada):
  - Banco de dados SQLite (`radar_absorcao_cruzada_cache`).
  - Coletor com yfinance (chart intraday) monitorando ações com queda forte que apresentam pico de volume atípico nas mínimas, sinalizando defesa institucional (VSA).
  - Adicionado painel em "Alertas Intraday" e no `/api/snapshot`.
- Spec 043 (Radar de Liquidez de Abertura):
  - Banco de dados SQLite (`liquidez_abertura_cache`).
  - Coletor buscando alertas de anomalia de volume da primeira hora via `yfinance`.
  - Exibição de ações com maior proporção volume atual / media no painel Alertas Intraday.
  - Adicionado ao contrato `/api/snapshot`.
- Spec 042 (Filtro de Sensibilidade a Juros):
  - Painel de correlação inversa no Sentimento & Risco.
  - Coletor buscando DI1F27.SA e cesta focada em juros.
  - Adicionado ao /api/snapshot.
- Spec 041 (Alerta de Falso Rompimento):
  - Banco de dados SQLite (`falso_rompimento_cache`).
  - Coletor buscando fechamentos, máximas e volumes para 30 ações de alta liquidez via `yfinance` nos últimos 2 dias.
  - Cálculo de rompimento da máxima do dia anterior seguido de reversão de preço e aumento de volume.
  - Exibição de painel na visão micro e tabela de alertas via contrato `/api/snapshot`.
- Spec 040 (Radar de Divergência Volume/Preço):
  - Tabela `radar_divergencia_volume_cache` no banco SQLite.
  - Coletor com yfinance (chart v8) buscando fechamentos de 5 dias para identificar topos.
  - Adicionado painel em "Alertas Intraday" e `/api/snapshot` exporta dados se disponíveis.
- Spec 035 (Reorganização dos Gauges de Tendência):
  - Integrados medidores de MM21 e MM200 ao card "Ibovespa hoje".
  - Removido o painel autônomo de Tendência (Ibovespa).
- Spec 035 (Setor Líder por Volume Financeiro):
  - Adicionado setor líder por volume e valor financeiro ao painel "Concentração Setorial" na visão macro.
  - Banco de dados SQLite (`concentracao_setorial_cache`) e `/api/snapshot` atualizados.
  - O contador de painéis, seções ou telas acrescentados permanece em 0, pois a UI foi integrada num painel existente.
- Spec 034 (Minimização de Painéis Indisponíveis):
  - Adicionada classe `.escondido` com `display: none` no CSS.
  - Painéis "Concentração Setorial", "Concentração de Ganhos" e "Anomalia de Peso" agora são ocultados da UI se estiverem sem dados para economizar espaço de tela, mantendo `/api/snapshot` intacto.
- Spec 033 (Anomalia de Peso):
  - Banco de dados SQLite (`anomalia_peso_cache`).
  - Coletor com `yfinance` buscando dados intraday.
  - Cálculo de ações com maior impacto no Ibovespa no dia.
  - Exibição na visão macro e no contrato `/api/snapshot`.

- Spec 032 (Radar de Inflexão):
  - Banco de dados SQLite (`radar_inflexao_cache`).
  - Coletor buscando fechamentos dos últimos 15 dias para ações via `yfinance`.
  - Cálculo de ações que caíram >5% nos últimos 15 dias, mas hoje revertem com alta >2%.
  - Exibição de painel "Inflexão de Tendência" na página inicial e via `/api/snapshot`.
- Spec 039 (Índice de Esforço vs Resultado):
  - Tabela `esforco_resultado_cache` no banco de dados SQLite.
  - Coletor com yfinance (chart v8) buscando volume e cotações (close vs open) diários de 1 mês.
  - Adicionado painel em "Alertas Intraday" e no `/api/snapshot`.
- Spec 038 (Detector de Ação Órfã):
  - Coletor com yfinance (spark intraday 15m).
  - Exibe ações caindo drásticamente em volume (secando) com risco de spread.
  - Adicionado painel em "Alertas Intraday" e no `/api/snapshot`.
- Spec 037 (Radar de Congestionamento):
  - Banco de dados SQLite (`radar_congestionamento_cache`).
  - Coletor com `yfinance` buscando histórico de fechamentos diários (spark).
  - Cálculo de Bandwidth das Bandas de Bollinger e geração de minigráficos.
  - Exibição de painel na visão de Alertas Intraday e via `/api/snapshot`.
- Spec 048 (Reorganização por Motores do Índice):
  - Banco de dados SQLite (`motores_indice_cache`).
  - Coletor buscando fechamentos intraday para as ações representativas de 3 motores (Financeiro, Commodities, Doméstico) via `yfinance`.
  - Cálculo de variação e exibição de cards na visão macro da home.
  - Adicionado painel e chaves em `/api/snapshot`.

- Spec 049 (Consolidação de Gauges na Maré do Mercado):
  - Consolidou-se os medidores semicirculares (gauges) de Apetite a Risco e Rotação de Capital no painel da Maré do Mercado.
  - Painéis isolados foram removidos para limpar a interface sem perder funcionalidade.

- Spec 050 (Experiência: Reorganização da Maré do Mercado):
  - Consolidado layout dos gauges no Painel da Maré do mercado.
  - Gauge de Confiança não é mais `grande`.
  - Gauges de Apetite a Risco e Rotação usando novo grid `gauges-pequenos`.
  - Contador da cadência de experiência: 1.
- Spec 068a (Consultor Rota e Coleta):
  - Rota protegida por senha GET /consultor e GET /api/consultor com autenticação HTTP Basic (usuário `consultor`).
  - Criação do módulo `app/consultor/universo.py` com a lista do Ibovespa.
  - Snapshot de api/snapshot atualizado.
- Spec 069b (Consultor Confiança Exibição):
  - Integração da confiança na resposta da API e interface UI.
- Spec 069a (Consultor Confiança Coleta):
  - Banco de dados SQLite (`consultor_confianca_regras`).
  - Coletor com `yfinance` buscando dados diários com histórico de 2y.
  - Cálculo sem viés de futuro da taxa de acerto e excesso mediano de cada regra, projetando os retornos 20 pregões à frente.
- Spec 036 (Radar de Short Squeeze):
  - Coletor com yfinance (spark).
  - Exibe ações caindo >=10% nos últimos 10 dias com aumento anormal de volume (>2x média diária) e alta >= 4%.
  - Adicionado painel em "Alertas Intraday" e no `/api/snapshot`.
- Spec 031 (Scanner de Capitulação):
  - Adicionado painel em "Alertas Intraday".
  - Coletor com yfinance buscando dados intraday (15m).
  - Exibe ações caindo >2% com aumento anormal de volume (>3x média diária) em candles com sombras inferiores longas.
  - Adicionado em `/api/snapshot`.
- Spec 030 (Abas de Navegação Contextual):
  - Adicionado menu de abas fixas no topo da grade.
  - Painéis categorizados em "Visão Geral", "Sentimento & Risco", "Rankings & Destaques" e "Alertas Intraday".
  - Filtro "Só Sinais" movido para o botão de abas.
  - Nenhuma nova dependência de dados, reorganização via JS/CSS.

- Spec 029 (Sparklines nos rankings):
  - Adicionados minigráficos (sparklines) nas tabelas "Maiores altas", "Maiores baixas" e "Força Relativa".
  - O desenho da linha SVGs é gerado e processado do backend a partir do histórico de 10 dias.
  - Componentes ajustados para acomodar o minigráfico.

- Spec 028 (Volatilidade Silenciosa):
  - Banco de dados SQLite (`volatilidade_silenciosa_cache`).
  - Coletor com `yfinance` buscando dados diários (spark).
  - Exibição de ações com alta amplitude intraday mas baixa variação entre abertura e fechamento.
  - Adicionado painel na `visao-micro` e ao contrato `/api/snapshot`.

- Spec 027 (Maré do mercado):
  - Cálculo em `app/services/mare.py` e coletor `app/collectors/mare.py` (cesta `TICKERS` com `spark` 3mo e Ibovespa com `chart` 2y, MT5 preferencial, brapi como reserva do Ibovespa); cache `mare_cache`.
  - Painel `span-4` ao lado do Ibovespa; Tendência, Dispersão e Coesão viram a linha seguinte.
  - Chave `mare` no `/api/snapshot`; `checar_mare` em `auditoria/auditar.py`.
  - Contador da cadência de experiência: 1.

- Spec 026 (Gauges para valores únicos):
  - Macro `gauge` em `componentes.html` e cálculo em `app/gauge.py` (filtro `gauge_pct` e global `gauge_dados`).
  - Gauges em Dispersão, Índice de Coesão, Apetite a Risco, Rotação de Capital e Tendência (MM21 e MM200, `mm21_dist_pct` e `mm200_dist_pct` no serviço do Ibovespa).
  - `medidor` desenhado em SVG; `scripts/telas.py` semeia coesão, apetite e rotação.
  - Nenhum painel novo: o contador da cadência de experiência não muda.

- Spec 025 (Concentração Setorial):
  - Banco de dados SQLite (`concentracao_setorial_cache`).
  - Coletor com MT5, brapi e `yfinance`, nessa ordem, agrupando a cesta por setor (nomes em português; ações sem setor mapeado ficam de fora).
  - Painel na visão macro com o setor de maior variação média; sem setor em alta, mostra "Nenhum setor em alta".
  - Chave `concentracao_setorial` no `/api/snapshot`, com `ha_setor_em_alta`.

- Spec 024 (Sobrevivência Semanal):
  - Banco de dados SQLite (`sobrevivencia_semanal_cache`).
  - Coletor com `yfinance` buscando dados diários.
  - Cálculo de ativos com fechamento positivo consecutivo nos últimos 5 dias.
  - Exibição de painel via contrato `/api/snapshot`.

- Spec 023 (Armadilha de Abertura):
  - Banco de dados SQLite (`armadilha_abertura_cache`).
  - Coletor com `yfinance` buscando dados intraday.
  - Exibição de ações que abriram com gap de alta (>1%) e reverteram abaixo do fechamento de ontem.
  - Adicionado painel à visão micro e ao contrato `/api/snapshot`.
- Spec 022 (Manchete Dinâmica):
  - Criação do `app/services/manchete.py` com lógica para resumir indicadores cacheados.
  - Integração no `app/main.py` injetando manchete em `index.html`.
  - Exibição condicional de mensagem dinâmica baseada na dispersão, apetite a risco e direção do Ibovespa.
- Spec 021 (Compradores de Fundo):
  - Banco de dados SQLite (`compradores_fundo_cache`).
  - Coletor com `yfinance` buscando dados de reversão intraday.
  - Exibição de ações com reversão no frontend.
  - Adicionado ao contrato `/api/snapshot`.
- Spec 020 (Radar de Faca Caindo):
  - Banco de dados SQLite (`faca_caindo_cache`).
  - Coletor com `yfinance` buscando dados diários (spark).
  - Cálculo de dias consecutivos em queda e retorno acumulado.
  - Exibição de painel na `visao-micro`.
  - Adicionado ao contrato `/api/snapshot`.
- Spec 019 (Modo Só Sinais):
  - Adicionado botão de filtro "Só Sinais" na interface.
  - Criado comportamento CSS e JS para ocultar gráficos e tabelas, focando nos indicadores de sentimento.
- Spec 018 (Rotação de Capital):
  - Banco de dados SQLite (`rotacao_capital_cache`).
  - Coletor com `yfinance` para bancos e commodities.
  - Cálculo de variação e direção do fluxo de capital (Bancos vs Commodities).
  - Exibição do fluxo direcional no painel de visão macro.
  - Adicionado ao contrato `/api/snapshot`.
- Spec 016 (Apetite a Risco):
  - Banco de dados SQLite (`apetite_risco_cache`).
  - Coletor com `yfinance` para SMAL11.SA e ^BVSP, calculando a diferença percentual de desempenho.
  - Exibe o estado 'Tomando risco', 'Defensivo' ou 'Neutro' e a variação da diferença no componente de frontend (com CSS próprio para cores do texto).
  - Adicionado ao contrato `/api/snapshot`.
- Spec 014 (Atrasadas do Rally):
  - Banco de dados SQLite (`atrasadas_rally_cache`).
  - Coletor com yfinance para `^BVSP` e 30 ações de alta liquidez.
  - Retorno de 5 dias calculado.
  - Adicionado painel 'Atrasadas do Rally' à home page e `/api/snapshot`.
- Spec 013 (Filtro Macro vs Micro):
  - Adicionado filtro de botões (Todos, Macro, Micro) na página inicial.
  - Oculta ou exibe painéis via JavaScript e CSS (display: none).
- Spec 012 (Índice de Coesão):
  - Banco de dados SQLite (`coesao_cache`).
  - Coletor com `yfinance` para as 10 principais ações e o Ibovespa, calculando convergência de direção.
  - Adicionado ao contrato `/api/snapshot`.
- Spec 011 (Revisão de Experiência Mobile):
  - Correção de rolagem horizontal em telas de 390px (ajuste `.duas`).
  - Reorganização lógica dos painéis da página inicial em `index.html`.
- Spec 009 (Força Relativa):
  - Banco de dados SQLite (`forca_relativa_cache`).
  - Coletor com yfinance buscando variações e comparando com benchmark IBOV.
  - Exibição das ações com maior e menor força relativa em 30 pregões.
  - Adicionado ao contrato `/api/snapshot`.

- Spec 007 (Fator Mola):
  - Banco de dados SQLite (`fator_mola_cache`).
  - Coletor buscando volume das ações mais líquidas via `yfinance` e `brapi`.
  - Exibição de ações com maior recuperação no intraday em relação à mínima.
  - Adicionado ao contrato `/api/snapshot`.
- Spec 007 (Fator Mola):
  - Banco de dados SQLite (`fator_mola_cache`).
  - Coletor buscando volume das ações mais líquidas via `yfinance` e `brapi`.
  - Exibição de ações com maior recuperação no intraday em relação à mínima.
  - Adicionado ao contrato `/api/snapshot`.
- Spec 006 (Sensibilidade ao Dólar):
  - Banco de dados SQLite (`dolar_correlation_cache`).
  - Coletor com fonte de dados yfinance para BRL=X e 30 ações de alta liquidez.
  - Cálculo de correlação de Pearson sobre os retornos dos últimos 30 pregões sobrepostos.
  - Exibição de tabela de maiores correlações positivas e negativas.
  - Adicionado ao contrato `/api/snapshot`.
- Núcleo do agente separado do produto (ADR 005 em `devagent/decisoes/`): processo em `devagent/`, produto em `PRODUTO.md`, contrato no `Makefile` e no `devagent.toml`.
- Configuração inicial do projeto (FastAPI, Ruff, Mypy, Pytest).
- Spec 001 (Ibovespa Hoje):
  - Banco de dados SQLite (`ibovespa_cache`).
  - Coletor com duas fontes: brapi.dev e fallback para Yahoo Finance.
  - Exibição de pontuação, variação diária e horário de coleta.
  - Gráfico de linha dos últimos 30 pregões usando Plotly.js.
  - Tratamento de falhas nas fontes de dados.
- Spec 002 (Maiores Altas e Baixas do Dia):
  - Banco de dados SQLite (`highlights_cache`).
  - Coletor com fonte de dados brapi.dev e fallback yfinance, rastreando lista de 30 tickers de alta liquidez.
  - Exibição de duas tabelas com top 5 altas e baixas (variação percentual).
  - Tratamento de falhas e UI para dados não disponíveis.
- Spec 003 (Médias Móveis de 21 e 200 dias para o Ibovespa):
  - Inclusão dos campos `mm21` e `mm200` no cache `ibovespa_cache`.
  - Cálculo de médias móveis baseado em histórico estendido (`1y`).
  - Card "Tendência (Ibovespa)" com sinais de alta, baixa ou neutra.
  - Atualização automática em cada coleta com fallback para dados insuficientes.
- Spec 004 (Sentimento de Mercado Baseado na Dispersão):
  - Termômetro de dispersão na página inicial com contagem de altas/baixas e proporção.
  - Banco de dados SQLite (`highlights_cache`) armazena as contagens.
  - Exposição no JSON `/api/snapshot`.
- Spec 005 (Alertas de Volume Anormal):
  - Banco de dados SQLite (`volume_alert_cache`).
  - Coletor buscando volume das 30 ações mais líquidas via `yfinance` (spark endpoint).
  - Cálculo de anomalia (volume atual > 50% da média das últimas 3 semanas).
  - Exibição de tabela de alertas na home e via contrato `/api/snapshot`.

- Spec 010 (Escudo contra Quedas):
  - Banco de dados SQLite (`escudo_quedas_cache`).
  - Coletor buscando histórico do Ibovespa e ativos via `yfinance`.
  - Exibição do top 3 ativos que mais tiveram retornos positivos nos pregões de queda do Ibovespa nos últimos 30 pregões.
  - Adicionado ao contrato `/api/snapshot`.
- Spec 015 (Concentração de Ganhos):
  - Banco de dados SQLite (`concentracao_cache`).
  - Coletor com yfinance buscando ^BVSP e top 10 ações por peso para calcular contribuição.
  - Exibição de texto explicativo e tabela de top 3 ativos no painel `visao-macro`.
  - Adicionado ao contrato `/api/snapshot`.

- Spec 017 (Alerta de Variação Súbita):
  - Banco de dados SQLite (`variacao_subita_cache`).
  - Coletor buscando fechamentos intraday recentes para 30 ações de alta liquidez via `yfinance`.
  - Cálculo de variação percentual na última hora > 1.5%.
  - Exibição de painel e tabela de alertas via contrato `/api/snapshot`.

- Spec 070 dividida em 070a e 070b.
- Spec 070a: Implementação de pré-filtro e fila de opiniões via feed.
- Spec 070b: Extração via Gemini e exibição no painel Consultor.

- Spec 071: Consultor exibe decisão final cruzando indicadores técnicos e consenso de casas de análise.
- Spec 073 dividida em 073a e 073b por causa de tamanho.
- Spec 072 dividida em 072a e 072b por causa de tamanho.
- Spec 073a (Banco · camada única com Postgres e armazenamento do consultor):
  - Camada genérica `app/banco.py` criada com fallback para SQLite efêmero.
- Spec 072b (Consultor · placar de acertos e avaliações na UI):
  - Lógica de placar implementada em `app/consultor/placar.py`, computando excessos de retorno para decisões, regras e casas de análise (janelas de 5 e 20 pregões, e gatilhos para Aguardar).
  - Endpoint `/api/consultor` e visualização `pagina_consultor` (em `app/main.py`) atualizados para incluir o objeto do placar.
  - Adicionada a seção "Placar" em `app/templates/consultor.html` com o aviso sobre histórico efêmero (`sqlite_efemero`).
  - Contador da cadência de experiência: 1 -> 2 (Painel do Placar adicionado).
- Spec 072a (Consultor diário de recomendações Postgres):
  - Tabela `consultor_recomendacoes` e `consultor_fechamentos`.
  - Fallback local no SQLite.
  - Endpoint expõe o backend de armazenamento ativo.

- Spec 073b (Banco · migração do Ibovespa, maiores altas/baixas e séries para a nova camada):
  - Migração de tabelas de cache legadas para `snapshots_paineis` e `series_diarias` no Postgres com fallback SQLite.
- Spec 075a (Banco · migração dos painéis para snapshots - lote 2 parte a):
  - Migração das tabelas divergencia_ibov_dolar_cache, dolar_correlation_cache, escudo_quedas_cache, esforco_resultado_cache, exaustao_queda_cache, exaustao_tendencia_cache, faca_caindo_cache para snapshots_paineis.
  - As funções continuam como fachada e gravam/leem em `snapshots_paineis`. Os `CREATE TABLE` saíram em 22/10.
- Spec 074 (Migração dos painéis para snapshots - lote 1):
  - Migração das tabelas anomalia_peso, anomalias_spread, apetite_risco, armadilha_abertura, assimetria_risco_retorno, atrasadas_rally, clima_global, coesao, compradores_fundo, concentracao, concentracao_ordens, concentracao_setorial, concentracao_vendedora para snapshots_paineis.
  - As funções `save_*`/`get_latest_*` continuam como fachada e gravam/leem em `snapshots_paineis`. Os `CREATE TABLE` que tinham ficado para trás no `init_db` saíram em 22/10, junto com o teste de aceite `tests/test_aceite_migracao_snapshots.py`.
- Specs 075 e 076 divididas em 075a, 075b, 076a e 076b (issue #404), seguindo o padrão de fachada da 074.
- Spec 075b (Banco · migração dos painéis para snapshots - lote 2 parte b):
  - Migração de 6 tabelas (`falso_rompimento_cache`, `fator_mola_cache`, `fator_peso_pesado_cache`, `forca_relativa_cache`, `liquidez_abertura_cache`, `mare_cache`) para `snapshots_paineis`.
- Spec 076a (Banco · migração dos painéis para snapshots - lote 3 parte a):
  - Migração de 7 tabelas (`motores_indice_cache`, `radar_absorcao_cruzada_cache`, `radar_congestionamento_cache`, `radar_divergencia_volume_cache`, `radar_inflexao_cache`, `radar_short_squeeze_cache`, `relogio_volatilidade_cache`) para `snapshots_paineis`.
- Spec 076b (Banco · migração dos painéis para snapshots - lote 3 parte b):
  - Migração de 7 tabelas (`rotacao_capital_cache`, `scanner_capitulacao_cache`, `sensibilidade_juros_cache`, `sobrevivencia_semanal_cache`, `variacao_subita_cache`, `volatilidade_silenciosa_cache`, `volume_alerts_cache`) para `snapshots_paineis`.
- Spec 077 (Data de referência e congelamento dos dados após o fechamento):
  - Congelamento e alteração de estados da coleta configurados em `app/agendador.py` e `app/database.py`.
  - Feriados da B3 e lógica de pregão implantados em `app/calendario.py` e `test_calendario.py`.
  - UI exibe horários do fechamento ou atualizado em tempo real dependendo do estado do mercado.

- Spec 077a (Resíduos do SQLite depois da migração):
  - Consultor ajustado para rodar nativamente no Postgres usando `sql_para` e `ON CONFLICT`, consertando consultas na produção.
  - Diagnóstico do banco movido para `app/banco.py`, capturando o tamanho usando `pg_database_size`.
  - Spec 077d (Resíduos do SQLite): Migradas e removidas do `init_db` as tabelas `radar_anomalia_fechamento_cache` e `consultor_confianca_regras`.
- Spec 077b (Resíduos do SQLite depois da migração - Consultor no Postgres):
  - Lógica do SQLite convertida para usar `sql_para` no Postgres na lógica do Consultor (tabela `consultor_llm_uso`, `consultor_opinioes_status`, `consultor_opinioes`).
- Spec 077c (Diagnóstico do Banco):
  - Lógica de diagnóstico do banco movida para `app/banco.py` e integrada ao postgres.
  - Atualizada a página /sistema para exibir os dados reais do Postgres.
- Spec 078 (Histórico dos últimos 5 pregões):
  - Adicionado suporte ao parâmetro `?data=` nas rotas principais e de API.
  - Implementado o controle de contexto de data no `app/banco.py`.
  - Criada rotina de exclusão de snapshots antigos (30 dias).
  - Adicionado seletor HTMX na UI e atualização de `get_recomendacoes` no `app/consultor/armazenamento.py`.
- Spec 088 (Seletor de pregão corrigido):
  - Unificou a variável `data` nas rotas (`index`, `snapshot`, `consultor`).
  - Trocou o HTMX do `<select>` por um `<form method="get">` padrão.
  - Adicionada checagem e alerta na página `/sistema` para o histórico.
- Spec 079 (Capacidade Nova: Radar de Exaustão de Alta):
  - Criado app/collectors/radar_exaustao_alta.py
  - Adicionado ExaustaoAltaData em app/database.py com salvamento/leitura via snapshots.
  - Atualizado app/agendador.py.
  - Atualizado app/main.py e app/templates/index.html para exibição do novo painel.

- implementado 084-consultor-esquema-postgres.md (saúde técnica, contador de specs não incrementado)
- Corrigido problema da spec 089, adicionado aviso de onde foram as partes derivadas (specs 113a e 113b).

- Spec 090a (Diagnóstico de falhas):
  - Registro HTTP agora anota falhas de endpoint separadamente e esconde segredos da URL e corpo.
  - Atualizada página de diagnóstico /sistema e seus testes.

- Spec 090b (Tolerância a símbolo inválido):
  - Adicionada tabela de suspensão de símbolos em SQLite e Postgres.
  - Isola 404 de lote na query e reporta alertas no Yahoo Finance para o consultor.
- Spec 093 movida para draft e dividida em 121a e 121b.

- Implemented Spec 098: brapi secondary source client module.
- Fixed Issue 531: Ibovespa implausible daily variation.
- **108a**: Banco de dados devolve timestamps reais e data da coleta das séries.
- **113a**: Consultor data passada exibicao (test_aceite_113a adicionado).

## 2026-10-24: Consultor resultados passados
- O sistema agora mostra o desempenho real de cada ativo avaliado em datas passadas contra o IBOV até 5 pregões.
- A coleta automática roda também no fechamento para gravar esse histórico (spec 113b).

- Spec 119b (Gemini ativo, validar a chave):
  - Validacao da chave API do Gemini via validador_gemini em background.
- Otimização do consumo de dados via banco reduzindo histórico lido e adicionando caches em memória para o cálculo do consultor (Spec 122).

- Spec 124 (Seletor de pregão mostra números do dia):
  - Foi criado o gerenciador de contexto lendo_pregao no app/banco.py e isolada a gravação de snapshots da leitura de histórico em requisições GET (/?data=...).
- Spec 121: 1- Spec 123 (Heatmap visual da Maré do Mercado):
  - Adicionado novo atributo `ativos_json` ao DB (em `/api/snapshot`). O HTML renderiza as ações mais movimentadas com background que indica a variação utilizando a paleta de alta/baixa.

- Spec 125b: Modificado app/agendador.py para gravar estado incompleto após as 20h para falhas de coleta.

Página Inicial Sem Bloquear (spec 130)
- `index` roda sincronamente em threadpool do FastAPI.
- Em requisições de página, todos os painéis para a dada data de referência são lidos do banco em uma única consulta e oxigenados num cache restrito ao tempo de vida da requisição (usando `contextvars`), não bloqueando o backend de processar novas rotas (como o `/healthz`).
- **127**: O `/api/coleta` agora exige senha e mostra corretamente os dados (`ligada`, `banco`, `aviso`). O `/api/consultor` exibe `cache: true/false` corretamente com base no uso real do cache (não mais copiado incorretamente do escopo global).

- Spec 126a (Agendador sem trabalho repetido): backtest do Consultor roda exatamente uma vez por coleta.
- Spec 126b (Agendador sem trabalho repetido): Tratamento correto de feriados usando app.calendario.e_pregao() em app/agendador.py.

- Implementada a spec 128 para evitar que banco Postgres inacessível em startup perca dados no SQLite.
- Spec 132b: Gravação do consenso em JSON no coletor implementada.
