# Relatório de Execução - Implementação Spec 078

**Data:** 23/10/2026
**Especialista:** Desenvolvedor Autônomo

## Resumo
Implementamos a Spec 078 (Histórico dos últimos 5 pregões), que permite ao usuário navegar pelo fechamento dos pregões passados sem depender da memória ou outros sites.

## Passos Realizados
1. **app/constants.py**: Adicionado `PREGOES_NO_SELETOR = 5`.
2. **Retenção (app/banco.py, app/agendador.py)**: Criado `limpar_snapshots_antigos(30)` em `app/banco.py` para manter apenas os últimos 30 pregões de snapshots e adicionado à rotina diária no `_coletar` do `agendador.py`.
3. **Assinaturas dos Paineis (app/database.py)**: Alterado todos os 42 métodos `get_latest_*_data` para receber `data_referencia: date | None` repassado para `ler_snapshot`.
4. **Diário do Consultor (app/consultor/armazenamento.py)**: Implementada a recuperação de histórico pelas tabelas `consultor_fechamentos` e `consultor_recomendacoes` através de `get_recomendacoes_do_pregao()`.
5. **Roteamento (app/main.py)**: Refatorado as rotas `index`, `snapshot`, `pagina_consultor` e `api_consultor` para recuperar e validar o parâmetro de data no histórico.
6. **Templates (app/templates/base.html, componentes.html)**: UI atualizada com `<select>` iterando sobre as datas disponíveis (HTMX), aviso de snapshot congelado no topo e tratamento elegante de `painel-vazio` em painéis de snapshot sem dados naquele dia.
7. **Testes**: Consertado fixtures de banco em testes com `monkeypatch` do calendário de data e todos passaram no ciclo de QA (`make verify`, `make smoke`).
