- O PR 489 implementou a Spec 086 com sucesso, provendo os timestamps reais para a página do consultor e os avisos de defasagem de sinais e opiniões. O teste de aceite da spec 086 foi incluído no commit e passou, bem como os avisos constam nas telas e nas rotas da API.
- Confirmada a resolução dos achados 'radar-exaustao-alta' (PR anterior) e 'spec-086-nao-implementada' (PR 489).
- Sem problemas de segurança identificados.
- Próxima verificação: focar em avaliar se alguma nova spec entregue impactou o tempo de carregamento da página inicial ou o consumo de chamadas das APIs externas integradas.

- Verifiquei o PR 498 referente à entrega da Spec 088.
- Notei que os critérios de aceite foram na maioria cumpridos (o seletor está na página inicial sem hx-target, api validada).
- No entanto, a implementação do seletor faltou em /consultor e /sistema, o que gerou o achado 2026-10-25-seletor-faltando-em-consultor-e-sistema.
- Próxima verificação deve focar se outros detalhes da UX, ou de consumo, sofreram impacto.

- Verifiquei o PR 501 que implementa correções para a spec 088.
- Confirmada a resolução do achado '2026-10-25-seletor-faltando-em-consultor-e-sistema'. O seletor agora é exibido corretamente nas rotas /consultor e /sistema.
- Nenhum novo defeito foi introduzido.
- Próxima verificação deve continuar observando regressões nas páginas do consultor.

- Verifiquei o PR 507 referente à divisão da spec 089.
- As specs 113a e 113b foram geradas corretamente com status ready.
- A spec 089 original falhou em informar para onde as partes foram movidas, resultando no achado '2026-10-26-spec-089-nao-aponta-partes'.
- Próxima verificação deve continuar atenta à qualidade dos metadados e conteúdos das especificações após divisão.

- Verifiquei o PR 512 referente à correção do apontamento das partes da spec 089 dividida.
- O arquivo `docs/specs/089-consultor-data-de-referencia.md` foi atualizado corretamente e agora aponta para as specs 113a e 113b.
- Confirmada a resolução do achado '2026-10-26-spec-089-nao-aponta-partes'.
- Próxima verificação: avaliar os PRs subsequentes na fila de implementação.

- Verifiquei o PR 515 referente à implementação da Spec 090b.
- A maior parte dos critérios foi cumprida, como a tolerância a falhas na coleta e registro no sistema.
- Encontrado um achado (2026-10-26-spec-090b-nao-implementada-corretamente): falta a exposição em `/` e `/consultor`. A falha foi tratada como um achado na verificação.
- Próxima verificação deve focar se outros detalhes da UX, ou de consumo, sofreram impacto após as correções inseridas.

- Verifiquei o PR 524 referente à implementação parcial e divisão da spec 092.
- A validação de chave falhou em seguir estritamente o `render.yaml` prescrito, resultando no achado '2026-10-26-spec-092-variaveis-render'.
- Encontrei vulnerabilidade de segurança potencial (Jinja2 XSS em `app/templates/index.html`) não mitigada adequadamente, gerando achado '2026-10-26-safe-jinja-falso-positivo'.
- Próxima verificação: assegurar aderência estrita aos critérios de aceite ao declarar infraestrutura e segurança da renderização.
- Verifiquei os PRs #535 e #536.
- Confirmada a resolução do achado '2026-10-26-safe-jinja-falso-positivo' (PR 535 corrigiu o escape XSS antes do filtro safe).
- Confirmada a resolução do achado '2026-10-26-spec-092-variaveis-render' (PR 536 removeu as variáveis extras do render.yaml).
- Próxima verificação deve continuar monitorando a segurança na renderização do Jinja2 e o alinhamento de infraestrutura com as specs.

- Verifiquei o PR 554 referente à base da fonte secundária Brapi (Spec 098).
- A ordem de fallback no coletor do Ibovespa foi implementada incorretamente (Brapi antes de Yahoo), gerando o achado 2026-10-27-spec-098-ordem-fontes-ibovespa.
- Um trecho de código morto permaneceu no coletor da Maré, gerando o achado 2026-10-27-spec-098-codigo-morto-mare.
- A próxima verificação deve assegurar que a ordem correta das chamadas às fontes de dados (MT5 -> Yahoo -> Brapi) foi restabelecida.

- Verifiquei os PRs #568 (spec 113b), #567 (spec 113a), #566 (spec 108a) e #564 (fix: anomalia_peso). Todos foram implementados de acordo com os critérios de aceite e não introduziram novos problemas visíveis.
- Os achados '2026-10-27-spec-098-codigo-morto-mare' e '2026-10-27-spec-098-ordem-fontes-ibovespa' (identificados no PR 554) foram resolvidos e confirmados na main.
- Próxima verificação deve continuar a observar se a infraestrutura e a experiência do usuário se mantêm íntegras nos próximos PRs.
- Verifiquei o PR 571 referente à entrega da Spec 119b.
- A validação ativa da chave e exposição no sistema funcionam, mas falhou ao não persistir resultados na tabela de banco de dados conforme requerido pela invariante.
- Achado criado: '2026-10-28-spec-119b-invariante-banco'. Próxima verificação focará nas correções da validação do Gemini.

- 2026-10-28: verifiquei a Spec 121a (PR #574), encontrei falso positivo na classificação de erros de banco devido ao uso de "in" para "relation" (bate com dolar_correlation).
- Verifiquei o PR 609 (fix: resolve snapshot timeout from missing exaustao_queda key).
- Identifiquei que, ao tentar resolver a ausência da chave, a inserção do código gerou um erro na montagem do JSON do `api/snapshot` por um timeout no teste, ou o dicionário retorna `{}`.
- Embora o PR tenha resolvido o problema original e testes passem, a issue #608 indica que o endpoint `api/snapshot` sofreu "The read operation timed out" em produção. O timeout não é resolvido apenas adicionando chaves duplicadas.
- Verifiquei os PRs da main recentes até o #622. O PR 617 corrigiu o formato ISO das datas e omissão de contrato (`api/snapshot`), mas na versão atual (após inserção do heatmap da Maré na Spec 123 que veio ao longo destas entregas), a página principal começou a sofrer bloqueios pesados do CSP devido ao uso de `style="..."` inline, visível na rodada do PR 622.
- O achado `2026-10-29-api-snapshot-contrato` (aberto pelo PR 609) foi verificado como resolvido, pois os PRs 613/617 corrigiram a falha do contrato ISO. O achado será mantido como resolvido.
- Adicionei um novo achado de segurança/leiaute ('2026-10-29-csp-unsafe-inline-index') que quebra a exibição do novo painel Heatmap.

- Verifiquei o PR 646.
- Confirmei a resolução do achado '2026-10-29-csp-unsafe-inline-index'. O heatmap foi refeito para usar as variáveis no style do div e a class para formatação sem usar style in-line restrito pela política do CSP.
- Adicionalmente, verifiquei que o log de auditoria indica problemas de conectividade/timeout que precisam ser analisados se for uma falha real da porta e tempo de subida.
- Adicionei um novo achado de robustez/contrato da API ('2026-10-31-api-contrato-chaves') por falha de aderência do endpoint snapshot omitindo as chaves `fonte` e `coletado_em` nos painéis recém injetados e ausentes.

- Verifiquei o PR 650 (fix: resolve missing snapshots on non-trading days Closes #647).
- A modificação atualizou o `app/calendario.py` e os testes, bem como o script `verificar_historico_pregoes`.
- Identifiquei que a função `verificar_historico_pregoes` continua usando `pregao_corrente` em vez de `ultimo_pregao_fechado`. Durante horários onde o mercado ainda não atingiu a consolidação, isso gera falsos positivos indicando que faltam snapshots de dias recuados que caíram da janela. O erro foi acentuado pela lógica ajustada para dias de fim de semana (que caem para sexta), mas durante as madrugadas de 29/10, cobrava o fechamento do dia recuando a janela e apontando 26 e 27 como ausentes. Criei o achado '2026-10-31-historico-pregoes' com severidade alta por impactar e poluir ativamente a saúde da produção.

- **2026-11-01**: Verifiquei o PR 663 que corrige o problema de histórico de pregões em `saude.py` (#656 e falso positivo arrumado em #650). A mitigação funcionou e removeu o falso positivo na página de saúde. Marquei o achado `2026-10-31-historico-pregoes` como resolvido. Próxima execução deve olhar as outras issues de produção abertas e os achados pendentes.
