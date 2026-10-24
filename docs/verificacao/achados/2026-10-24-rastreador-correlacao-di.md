---
id: 2026-10-24-rastreador-correlacao-di
severidade: media
painel: app/templates/index.html
status: aberto
visto_em: 2026-10-24T12:00:00-03:00
pr: 450
---

# Painel de Correlação com DI não é renderizado na página inicial

## O que acontece
A Spec 081 exige um novo painel para o Rastreador de Correlação com Juros Futuros (DI). O backend (`app/main.py`) exporta corretamente a variável `correlacao_di` para o contexto do template Jinja. No entanto, o arquivo `app/templates/index.html` (frontend) não foi modificado. Como o Jinja não possui nenhum código HTML para consumir a variável `correlacao_di`, o painel nunca aparece na tela.

## O que deveria acontecer
O critério de aceite da spec dita que "O painel é renderizado na tela e ocultado adequadamente quando os dados estiverem indisponíveis." Para que isso ocorra, o frontend (`app/templates/index.html`) deveria usar as macros Jinja do sistema (ex: a macro `painel` importada de `componentes.html`) para expor o novo painel para o usuário.

## Evidência
No commit diff do PR #450, o arquivo `app/templates/index.html` não consta entre os modificados.

## Como reproduzir
Basta acessar a página inicial do produto. Mesmo que o backend tenha retornado os dados de correlação DI na API e exposto via `snapshot()`, nada é desenhado na tela inicial.
