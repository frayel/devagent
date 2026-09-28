## 2026-09-27
- **O que fiz:** Ajustei a exibição da variação percentual do Ibovespa para usar o padrão brasileiro com vírgula em vez de ponto, e incluí a indicação visual da `fonte` dos dados no painel do Ibovespa, mantendo-o consistente com os painéis de altas e baixas. Verificado visualmente que as alterações estão aplicadas (fonte aparecendo e vírgula na variação).
- **O que aprendi:** Acessar propriedades do `data` em index.html é simples, mas é preciso garantir que a propriedade também seja preenchida pelo respectivo serviço (ex.: `get_ibovespa_view_data`).
- **O que evitar:** Esquecer de atualizar os testes sempre que for alterar os formatos visuais esperados pelas validações de endpoint.
## 2026-09-28
- **O que fiz:** Adicionei formatação com separadores no padrão brasileiro (vírgula para decimal, ponto para milhar) no tooltip hover do gráfico do Ibovespa, usando as propriedades `separators` e `hovertemplate` do Plotly, para melhorar a legibilidade e a aderência ao padrão nacional. Verifiquei visualmente com screenshots do desktop e mobile após injetar a alteração.
- **O que aprendi:** A configuração visual interativa de gráficos do Plotly no frontend necessita do `separators` na propriedade `layout`, e no trace é necessário um template de tooltip bem definido com formatação numérica como `%{y:,.0f}` que respeita esses separadores.
- **O que evitar:** Evitar deixar `pytest` ser atrapalhado por warnings irrelevantes, e sempre validar com visualizadores web headless.
