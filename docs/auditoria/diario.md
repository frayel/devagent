# Diário do auditor

Memória entre execuções do auditor LLM. No máximo 20 linhas: condense em vez de acumular.

- 2026-09-26 · Criação e Execução. Incidente de origem confirmado: produção exibe dados de testes/fixtures. Os dados apontam 130.000 pontos em vez dos 183.477 (verificado via Yahoo Finance). A auditoria reportou as falhas determinísticas.
- Durante a inspeção exploratória, foi confirmado que a página principal ainda **não** mostra a fonte dos dados e que a variação percentual do Ibovespa não segue o padrão de formatação brasileiro (usa `.` em vez de `,`). Achados foram criados.
- Pendente de verificar: Se a resolução da exibição dos dados de testes (fixtures) introduzirá novas regressões na performance da coleta ou problemas no carregamento.
