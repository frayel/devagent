---
id: 2026-10-26-spec-090b-nao-implementada-corretamente
severidade: media
painel: app/main.py (rotas / e /consultor)
status: aberto
visto_em: 2026-10-26T11:00-03:00
pr: 515
---

# Símbolos suspensos do Yahoo não são expostos em tela

## O que acontece
Em `app/main.py`, as rotas `/` e `/consultor` não buscavam a lista de símbolos suspensos (`get_simbolos_suspensos()`) para repassar ao contexto do Jinja as informações necessárias (no caso, a variável `suspensos_yahoo`). Isso impedia que a mensagem "Sem cotação no Yahoo: X, Y. Verifique a composição do Ibovespa" aparecesse na tela, deixando a especificação 090b parcialmente incompleta na UI.

## O que deveria acontecer
O critério de aceite da spec 090b diz que a lista de símbolos suspensos aparece na tela do Consultor ("Sem cotação no Yahoo: X, Y. Verifique a composição do Ibovespa"). Portanto, a variável `suspensos_yahoo` deve ser passada através do template context nas respectivas rotas no `main.py`.

## Evidência
Com o PR 515 mesclado, a regra foi implementada corretamente no banco e na coleta (`app/collectors/utils.py`), além de `/sistema` via `app/services/sistema.py`, mas faltava no `app/main.py` para injetar em `index.html` e `consultor.html`.

## Como reproduzir
Adicionar um símbolo inválido, deixá-lo falhar 3x para que fique suspenso, e observar que nas telas principais o alerta não era exibido antes dessa correção.
