## 2026-09-27
- **O que fiz:** Ajustei a exibição da variação percentual do Ibovespa para usar o padrão brasileiro com vírgula em vez de ponto, e incluí a indicação visual da `fonte` dos dados no painel do Ibovespa, mantendo-o consistente com os painéis de altas e baixas. Verificado visualmente que as alterações estão aplicadas (fonte aparecendo e vírgula na variação).
- **O que aprendi:** Acessar propriedades do `data` em index.html é simples, mas é preciso garantir que a propriedade também seja preenchida pelo respectivo serviço (ex.: `get_ibovespa_view_data`).
- **O que evitar:** Esquecer de atualizar os testes sempre que for alterar os formatos visuais esperados pelas validações de endpoint.
