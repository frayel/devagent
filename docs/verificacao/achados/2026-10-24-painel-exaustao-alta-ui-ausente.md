---
id: 2026-10-24-painel-exaustao-alta-ui-ausente
severidade: alta
painel: app/main.py
status: aberto
visto_em: 2026-10-24T00:00:00-03:00
pr: 442
---

# Radar de Exaustão de Alta não é renderizado na página inicial

## O que acontece
No arquivo `app/main.py`, a função `index()` (responsável por renderizar a interface gráfica `app/templates/index.html`) não busca os dados do "Radar de Exaustão de Alta" nem repassa a variável `exaustao_alta` ao contexto do template Jinja. Como consequência, o painel nunca renderiza os alertas na interface, ficando sempre em branco na página inicial (a variável no Jinja fica vazia/nula).

## O que deveria acontecer
Ao expor um novo painel, os dados devem ser integrados em dois lugares dentro de `app/main.py`: na resposta do endpoint `snapshot()` e como variável de contexto na função `index()`. O PR apenas adicionou os dados no endpoint `snapshot()`. A função `index()` também deveria usar `get_latest_exaustao_alta_data()` e passar `exaustao_alta` no contexto do `TemplateResponse`, cumprindo assim o critério de aceite de exibir os dados na tela.

## Evidência
Em `app/main.py`, na função `index()`, há a busca por `exaustao_queda_data` e `exaustao_tendencia_data`, mas `exaustao_alta_data` é omitida. Na chamada de retorno, `exaustao_alta` não está no dicionário `context`.

## Como reproduzir
Basta rodar a aplicação e verificar que, mesmo havendo ativos em exaustão de alta identificados pelo coletor (e adicionados artificialmente na API local de testes), o respectivo painel na página HTML não lista os alertas na interface inicial.
