---
id: 2026-10-25-seletor-faltando-em-consultor-e-sistema
severidade: media
painel: app/main.py (rotas /consultor e /sistema)
status: aberto
visto_em: 2026-10-25T12:00-03:00
pr: 498
---

# Seletor de pregão não está disponível no Consultor e Sistema

## O que acontece
Em `app/main.py`, as rotas `/consultor` e `/sistema` não passam as variáveis `datas_disponiveis`, `datas_seletor`, `is_historical`, etc. para o template `consultor.html` e `sistema.html`. Por isso, o seletor de pregão (`<select name="data">` no `base.html`) não é exibido nessas páginas, pois está condicionado a `{% if datas_disponiveis %}`.

## O que deveria acontecer
O critério de aceite da spec 088 diz: "GET /consultor e GET /sistema também trazem o seletor". O seletor deveria aparecer no cabeçalho em todas as páginas que estendem `base.html`.

## Evidência
Com o PR 498 mesclado, o seletor aparece na página inicial (`/`), mas requests a `/consultor` e `/sistema` retornam HTML sem a tag `<select class="seletor-data"`.

## Como reproduzir
Rodar a aplicação e acessar as rotas `/consultor` e `/sistema`, e verificar que o seletor de data está ausente no cabeçalho.
