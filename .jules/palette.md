## 2026-09-27
- **O que fiz:** Ajustei a exibição da variação percentual do Ibovespa para usar o padrão brasileiro com vírgula em vez de ponto, e incluí a indicação visual da `fonte` dos dados no painel do Ibovespa, mantendo-o consistente com os painéis de altas e baixas. Verificado visualmente que as alterações estão aplicadas (fonte aparecendo e vírgula na variação).
- **O que aprendi:** Acessar propriedades do `data` em index.html é simples, mas é preciso garantir que a propriedade também seja preenchida pelo respectivo serviço (ex.: `get_ibovespa_view_data`).
- **O que evitar:** Esquecer de atualizar os testes sempre que for alterar os formatos visuais esperados pelas validações de endpoint.
## 2026-09-28
- **O que fiz:** Adicionei formatação com separadores no padrão brasileiro (vírgula para decimal, ponto para milhar) no tooltip hover do gráfico do Ibovespa, usando as propriedades `separators` e `hovertemplate` do Plotly, para melhorar a legibilidade e a aderência ao padrão nacional. Verifiquei visualmente com screenshots do desktop e mobile após injetar a alteração.
- **O que aprendi:** A configuração visual interativa de gráficos do Plotly no frontend necessita do `separators` na propriedade `layout`, e no trace é necessário um template de tooltip bem definido com formatação numérica como `%{y:,.0f}` que respeita esses separadores.
- **O que evitar:** Evitar deixar `pytest` ser atrapalhado por warnings irrelevantes, e sempre validar com visualizadores web headless.
## 2026-10-02
- **O que fiz:** Ajustei a macro de KPI (`kpi()`) em `app/templates/componentes.html` para renderizar as variações (`variacao_str`), que estavam sendo ocultadas na interface, e ajustei as tags `<span>` na passagem de dados de `app/templates/index.html` para a `tabela_ativos` usando a tupla segura do Jinja.
- **O que aprendi:** Templates podem definir macros com propriedades não utilizadas inadvertidamente, causando falta de dados na interface. Ao aplicar `| safe` no Jinja num dicionário depois de uma concatenação `~`, é preciso envolver a expressão inteira com parênteses, senão o `safe` só se aplica ao último termo (`'</span>'`).
- **O que evitar:** Evitar recriar strings em dicionários Jinja sem agrupar toda a expressão de HTML antes do filtro `| safe`.
## 2026-10-03
- **O que fiz:** Ajustei a estilização do menu de filtros (Macro/Micro) em `app/static/tema.css` para utilizar os tokens de design do sistema (cores de superfície, texto, espaçamentos via variáveis CSS) e alinhar-se à estética do produto sem perder a funcionalidade. Verificado visualmente.
- **O que aprendi:** Novas seções podem ser adicionadas temporariamente sem seguir 100% dos tokens, e a refatoração visual ajuda a manter a coesão sem quebrar o layout.
- **O que evitar:** Evitar deixar componentes isolados visualmente do resto da interface.
