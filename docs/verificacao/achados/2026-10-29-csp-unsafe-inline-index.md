---
id: 2026-10-29-csp-unsafe-inline-index
severidade: alta
painel: app/templates/index.html (Heatmap da Maré)
status: aberto
visto_em: 2026-10-29T21:48:14-03:00
pr: 622
---

# Uso de unsafe-inline style viola CSP e quebra heatmap

## O que acontece
Na renderização da página inicial (`/`), o painel de "Maré do mercado" agora exibe o heatmap (Spec 123) com o bloco HTML gerado com estilos embutidos (inline styles), como `style="display: flex; ..."` e `<div ... style="flex-grow: {{ ativo.peso }}; ...">`. Contudo, o projeto possui um Content-Security-Policy (CSP) rígido que bloqueia estilos `unsafe-inline`. Como resultado, os navegadores modernos (e os testes no Playwright na auditoria de produção) bloqueiam a aplicação dessas formatações, destruindo o leiaute e cores da visualização e estourando erros de JavaScript/Segurança na página.
Comando que mostra: `PORT=8000 make audit ARGS="--url http://127.0.0.1:8000 --navegador"`

## O que deveria acontecer
Conforme diretriz e memória ("The project enforces a strict Content-Security-Policy (CSP) that prohibits unsafe-inline for styles and scripts"), os atributos `style="..."` não devem ser usados de forma indiscriminada. As propriedades estáticas de layout devem ser migradas para classes num arquivo CSS estático e as definições dinâmicas (como `flex-grow`, opacidade e `background-color`) que dependem das variáveis devem ser resolvidas com `style nonce`, uso estrito de chaves sem inline, ou convertidas de uma maneira que seja compatível com a política CSP do projeto (ex.: CSS variables definidas via `style nonce` no cabeçalho ou tags injetadas).

## Evidência
Saída do comando de auditoria:
`pagina.sem_erros_js` Página carrega sem erros de JavaScript: `Applying inline style violates the following Content Security Policy directive 'style-src 'self' ...'. Either the 'unsafe-inline' keyword, a hash ..., or a nonce ('nonce-...') is required to enable inline execution.`

Trecho problemático em `app/templates/index.html` (linhas ~60 e ~64):
```html
        <div class="heatmap" style="display: flex; flex-wrap: wrap; gap: 2px; margin-top: var(--e3);">
            {% for ativo in mare.heatmap %}
            {% set cor = 'var(--cor-alta)' if ativo.variacao > 0 else 'var(--cor-baixa)' if ativo.variacao < 0 else 'var(--cor-neutro)' %}
            <div title="{{ ativo.ticker }}: {{ '%.2f' | format(ativo.variacao) | replace('.', ',') }}%"
                 style="flex-grow: {{ ativo.peso }}; width: max(30px, {{ ativo.peso * 100 }}%); background-color: {{ cor }};
                        opacity: {{ 0.3 + 0.7 * ([ativo.variacao|abs / 5, 1]|min) }};
                        color: white; font-size: 0.7rem; text-align: center; padding: 4px 2px; border-radius: 2px; overflow: hidden; white-space: nowrap;">
```

## Como reproduzir
1. Inicie a aplicação com dados ativos.
2. Rode `PORT=8000 make audit ARGS="--url http://127.0.0.1:8000 --navegador"` ou abra o navegador normal na rota inicial `/` com DevTools abertos no painel do Console.
3. Observe os múltiplos erros "Content Security Policy directive" bloqueando o layout do painel da Maré.
