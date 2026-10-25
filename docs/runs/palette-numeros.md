# Relatório de Execução - Palette (2026-10-25)

## Objetivo
Resolver problemas de formatação de números, que estavam usando ponto em vez de vírgula para separar casas decimais nos painéis, desobedecendo a diretriz de formatação brasileira (`PRODUTO.md`).

## Resumo das Ações
- Utilizei scripts em Python para identificar ocorrências de formatação com vírgula no template `app/templates/index.html`. Foram encontrados dezenas de `format` do tipo `("%.2f%%" | format(...))` que estavam sem o encadeamento `.replace('.', ',')`.
- Substituí os blocos de HTML contendo as formatações utilizando substituições seguras em bloco e regex-like scripts para aplicar `replace('.', ',')`.
- Todos os testes no `make verify` continuaram passando após as alterações.
- Verificação do frontend: capturei novas imagens usando `make telas` e verifiquei visualmente que as porcentagens e magnitudes nas tabelas (ex: Atrasadas do Rally, Exaustão de Alta/Queda, Radares) agora utilizam corretamente a vírgula como separador decimal.

## Checklist Visual
- [x] Em 1440px, o Ibovespa, a tendência e a dispersão aparecem sem rolar? **Sim.**
- [x] Em 390px, não há rolagem horizontal e a ordem dos painéis faz sentido (Ibovespa primeiro)? **Sim.**
- [x] Algum card tem área vazia maior que o próprio conteúdo? **Não.**
- [x] Toda alta e baixa tem seta além da cor? **Sim.**
- [x] Todo número está alinhado e com algarismos tabulares? **Sim.**
- [x] O gráfico usa o tema de `graficos.js` (ou é um `gauge` da macro) e tem resumo em `aria-label`? **Sim.**
- [x] Sobrou algum número solto que tem escala e deveria ser `gauge`, linha ou barra (seção 5.1)? **Não percebido no escopo.**
- [x] O painel novo usa as macros de `componentes.html` e uma classe `span-N`? **N/A (nenhum painel novo criado).**
- [x] Com o painel novo, a hierarquia ainda faz sentido? **N/A.**
- [x] Comparada com `docs/design/referencia.html`, a tela parece parte do mesmo sistema? **Sim.**

As formatações do app agora são consistentes com a regra brasileira descrita no `PRODUTO.md`.
