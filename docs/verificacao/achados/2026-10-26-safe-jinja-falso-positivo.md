---
id: 2026-10-26-safe-jinja-falso-positivo
severidade: media
painel: app/templates/index.html e app/templates/componentes.html
status: resolvido
visto_em: 2026-10-26T14:10-03:00
pr: 524
---

# `| safe` foi usado inadequadamente para strings arbitrárias em chamadas `variacao` que foram movidas

## O que acontece
Em `app/templates/index.html`, nas alterações introduzidas pelo PR #524 (que removeu `| safe` do template de `componentes.html`), foi introduzido código com chamadas à macro `variacao` onde o input (ex: `data.variation`) está sujeito ao `| safe` aplicado posteriormente.
Exemplo do PR 524 em index.html:
```html
{{ kpi(data.current_price|default("") + " pontos", "", (variacao(data.variation ~ " (" ~ data.variation_percent ~ ")", data.variation_raw|default(0))) | safe, True) }}
```
Além disso, em `app/templates/componentes.html`:
```html
{% macro variacao(valor_formatado, sinal) %}
<span class="var {% if sinal > 0 %}alta{% elif sinal < 0 %}baixa{% else %}neutra{% endif %}">
  {% if sinal > 0 %}▲{% elif sinal < 0 %}▼{% else %}■{% endif %} {{ valor_formatado }}
</span>
{% endmacro %}
```
Como a macro agora retorna HTML e em `index.html` nós envelopamos com `| safe`, qualquer variável dentro de `valor_formatado` (como `data.variation`) é processada como HTML confiável se não tiver `| e` aplicado *antes* de concatenar ou passar.

## O que deveria acontecer
Conforme o relato de PR do Sentinel na alteração (e a diretiva de Segurança para `| safe`), strings arbitrárias (que podem vir de APIs como Yahoo Finance, Brapi etc) que compõem essas variáveis de string devem sofrer escape explícito `| e` antes de serem marcadas como `safe` no Jinja2.

## Evidência
```jinja2
{{ kpi(data.current_price|default("") + " pontos", "", (variacao(data.variation ~ " (" ~ data.variation_percent ~ ")", data.variation_raw|default(0))) | safe, True) }}
```
Nenhuma das variáveis injetadas (ex: `data.variation` ou `data.variation_percent`) recebe `| e`.

## Como reproduzir
Ler `app/templates/index.html` (e.g. linhas do ibovespa ou componentes dinâmicos de texto não escapado antes de ser envelopado por `safe`).
