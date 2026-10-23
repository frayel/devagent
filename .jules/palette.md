## 2026-10-22
- **O que fiz:** Ajustei o painel "Sensibilidade ao dólar" em `app/templates/index.html` para usar a classe `span-6` em vez de `span-8`.
- **Por que fiz:** O `docs/DESIGN.md` instrui que a distribuição na grade (em CSS Grid) recomenda que painéis com gráfico sejam `span-6` ou maior, mas a redução visa não comprometer a quebra da grade de 12 colunas sem necessidade para esse painel, já que a estrutura ao lado comporta perfeitamente este tamanho na visualização desktop de 1440px.
- **O que aprendi:** A tabela e listas sem gráfico não requerem um valor tão alto de span (como 8, usado majoritariamente pelo Ibovespa), e manter a largura equilibrada segue as regras do sistema de design.
- **O que evitar:** Deixar painéis puramente tabulares ocuparem tanto espaço horizontal (span-8) quando um span-6 já acomoda duas colunas no modo desktop, permitindo que a linha seja melhor aproveitada.

## 2026-10-19
- **O que fiz:** Padronizei a apresentação dos indicadores 'Apetite a Risco' e 'Rotação' no painel 'Maré do mercado' em `app/templates/index.html` para utilizarem a macro `kpi` fornecida por `app/templates/componentes.html`, substituindo a estrutura HTML manual e respeitando o design system (docs/DESIGN.md).
- **Por que fiz:** O guia visual instrui a não escrever marcação manual (`<div class="hero num...">`, `<div class="rot...">`) se macros já fornecem essa consistência, especialmente para os painéis principais.
- **O que aprendi:** Ao mesclar HTML gerado em Jinja e passá-lo para uma macro que aceita string segura, o uso do filtro `| safe` associado à concatenação com parênteses, bem como a atribuição de estilo (`texto-alta`, `texto-baixa`) em variáveis Jinja separadas, é essencial para manter a macro limpa e evitar injeções ou bugs visuais.
- **O que evitar:** Deixar componentes pequenos e avulsos escaparem das macros do sistema de design; todos devem compartilhar a base padrão para garantir legibilidade.
## 2026-10-16
- **O que fiz:** Refatorei os painéis 'Clima Global' e 'Motores do Índice' em `app/templates/index.html` para utilizarem a macro padrão `painel` em vez de tags HTML manuais (violava docs/DESIGN.md seção 4). Tratei os casos de ausência de dados usando `estado('indisponivel')`.
- **O que aprendi:** Variáveis locais do Jinja (`{% set motores_span = ... %}`) são ótimas para calcular parâmetros complexos (como a largura responsiva de `span-6` vs `span-12`) antes de chamar a macro `painel`, mantendo o código da chamada mais limpo.
- **O que evitar:** Nunca sobrescrever o `pytest.ini` com ferramentas de edição sem verificar o conteúdo gerado, pois quebra completamente a resolução de caminhos nos testes (Python path/module resolution).
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

## 2024-11-20
- **O que fiz:** Corrigi o template `index.html` para o painel "Atrasadas do Rally", utilizando o array `linhas` no macro `tabela_ativos` em vez de tags HTML puras (`<tr>`, `<td>`), o que quebrava o layout.
- **O que aprendi:** O macro `tabela_ativos` gera sua própria `<table>` e `<tbody>`. Passar tags HTML externas pra dentro dele ou injetar elementos da tabela de forma mista compromete o layout da página.
- **O que evitar:** Evitar escrever HTML de tabela diretamente em componentes que foram criados para receber dados em arrays dicionários padronizados, pois isso ignora a aplicação global do design system na aplicação.
## 2026-10-06
- **O que fiz:** Padronizei o painel "Força Relativa" para usar a macro `kpi` e corrigi a classe `sem-dados` para `vazio` em "Atrasadas do Rally" de acordo com o Design System.
- **Por que fiz:** A versão anterior usava classes customizadas não definidas (`linha-kpis`, `kpi-secundario`), violando os tokens de design (Seção 4 de docs/DESIGN.md) e regras de macros (Seção 5).
- **O que aprendi:** É importante revisar templates para garantir que macros padrão estejam sendo utilizadas no lugar de layouts improvisados.
## 2026-10-10
- **O que fiz:** Adicionei atributo `role="img"` e um resumo textual no `aria-label` do gráfico do Ibovespa (em `app/templates/index.html`), gerando a string de resumo com variação percentual na função de serviço `app/services/ibovespa.py`.
- **Por que fiz:** Docs/DESIGN.md seção 5 manda que 'Todo gráfico tem aria-label com um resumo em texto' e o checklist de design reprovava a ausência desse `aria-label` e resumo.
- **O que aprendi:** Templates lidam mal quando as chaves de dicionário podem faltar, é melhor usar `.get('key', '')` do que `.key` ao estender objetos já testados.
- **O que evitar:** Deixar objetos da interface com gráfico sem leitura apropriada pra screen readers.
## 2026-10-10
- **O que fiz:** Ajustei o painel "Volatilidade Silenciosa" em `app/templates/index.html` para usar a macro padronizada `tabela_ativos` em vez de uma `<table>` customizada, garantindo alinhamento com o sistema de design (docs/DESIGN.md, Seção 4).
- **Por que fiz:** Elementos de tabela não padronizados estavam quebrando a consistência visual. A macro fornece o layout oficial com o espaçamento e alinhamento adequados, lidando apropriadamente com o design iterativo do layout da página.
- **O que aprendi:** Qualquer componente tabular, especialmente aqueles que incluem propriedades financeiras comuns (preço, variação), deve empregar as ferramentas das macros para manter a unidade do estilo da aplicação.
- **O que evitar:** Evitar escrever tags HTML nativas `<table>` e `<tbody>` diretamente nos templates de painéis para novos alertas ou seções analíticas.
## 2026-10-11
- **O que fiz:** Tentei rodar, mas já havia PR do agente aberto (#240). Encerrei sem mudanças funcionais.
- **O que aprendi:** Não se deve abrir PR vazio ao abortar execução por restrição de concorrência.
- **O que evitar:** Abrir PR quando a instrução é 'encerrar sem mudanças'.## 2026-10-12
- **O que fiz:** Adicionei as propriedades `barra` e `valor_barra` às células de magnitude ("Amplitude", "5d (Ativo)", "Retorno") das tabelas nos painéis "Volatilidade Silenciosa", "Atrasadas do Rally" e "Radar de Faca Caindo" em `app/templates/index.html`.
- **Por que fiz:** O `docs/DESIGN.md` (seção 4) instrui que colunas que representam uma magnitude devem exibir uma barra horizontal discreta para facilitar a comparação visual pelo usuário. A macro `tabela_ativos` já suportava isso, mas os painéis não estavam passando os dados na renderização.
- **O que aprendi:** Ao adicionar chaves em dicionários de templates Jinja multi-linha, a formatação precisa ser cautelosa para não quebrar a compilação do template e o diff deve ser rigorosamente verificado.
- **O que evitar:** Modificar código visual (HTML/Jinja) utilizando Regex diretamente sem revisar o impacto se a sintaxe exata for alterada de leve no original (ex: espaços extras ou aspas); scripts em python injetando linha a linha via replace se mostraram mais confiáveis aqui.
## 2026-10-18
- **O que fiz:** Padronizei o painel "Fator Peso Pesado" em `app/templates/index.html` para usar a macro `kpi` em vez de estruturar o HTML manualmente com `<span class="fs-hero num">`. A descrição agora é passada adequadamente no parâmetro `variacao_str` para renderizar abaixo do valor numérico.
- **Por que fiz:** O `docs/DESIGN.md` instrui o uso da macro `kpi` para apresentar métricas em destaque, eliminando a criação de layouts improvisados.
- **O que aprendi:** A macro `kpi` é versátil o suficiente para comportar descrições textuais se passarmos o texto via `variacao_str`, dispensando marcação manual de divs.
- **O que evitar:** Escrever HTML customizado para apresentar números e labels quando já existem macros padrão que garantem a consistência visual do projeto.
## 2026-10-20
- **O que fiz:** Padronizei os painéis "Clima Global", "Motores do Índice" e "Concentração Setorial" em `app/templates/index.html` para usarem a macro `kpi` em vez de estruturar o HTML manualmente com `<div class="kpi">`.
- **Por que fiz:** O `docs/DESIGN.md` instrui o uso da macro `kpi` para apresentar métricas em destaque.
- **O que aprendi:** Templates lidam bem com a substituição de blocos HTML longos por chamadas da macro `kpi` usando as funções `variacao` para a string de formatação. O uso de `| safe` é necessário em strings que concatenam com HTML interno.
- **O que evitar:** Escrever `<div class="kpi">` manualmente em templates ao invés de usar a macro correspondente.
## 2026-10-21
- **O que fiz:** Padronizei o painel "Concentração Setorial" em `app/templates/index.html` para usar a macro `kpi` no "Maior volume", substituindo a marcação manual HTML.
- **Por que fiz:** A diretriz visual do sistema exige o uso da macro `kpi` em vez de tags `<div class="kpi">` customizadas.
- **O que aprendi:** Ao encapsular strings HTML complexas na macro `kpi`, aplicar corretamente o filtro `| safe` a toda a expressão englobada por parênteses evita que a estrutura `<p class="sub">` vaze como texto bruto na página.
- **O que evitar:** Construir painéis híbridos onde metade usa macros padronizadas e a outra metade utiliza marcação HTML manual.
## 2026-10-23
- **O que fiz:** Adicionei os atributos `role="img"` e `aria-label` à macro `sparkline` em `app/templates/componentes.html` (e apliquei nas chamadas em `index.html`), permitindo que as minisséries temporais tenham resumo textual audível ("Evolução de [TICKER]").
- **Por que fiz:** O `docs/DESIGN.md` (seção 5) dita que todo gráfico precisa ter um `aria-label` com o resumo da série em texto para a acessibilidade.
- **O que aprendi:** A macro `sparkline` estava utilizando apenas `aria-hidden="true"`, o que inviabilizava a compreensão do contexto desse elemento por leitores de tela em tabelas de ranking.
- **O que evitar:** Deixar elementos visuais de dados (ainda que secundários ou miniaturas) sem a devida descrição para acessibilidade (Screen Readers).
