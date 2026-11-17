---
id: 172
titulo: Cada página baixa só o script que usa
status: ready
esforco: P
gaveta: poda
aceite: tests/test_aceite_172.py
origem: A página só carrega o script que usa
revisada: 2026-11-17
---

## Problema
Por que `/consultor`, `/sistema` e `/novidades` baixam um gráfico que não desenham, e todas as páginas uma biblioteca que nenhuma usa?

Toda página que estende `base.html` carrega, síncronos no `<head>` (`app/templates/base.html:8-11`), quatro scripts: o htmx, o Plotly básico, `graficos.js` e `ui.js`. Medido na `main` de 17/11:

- **htmx não tem uso.** `grep -rn "hx-\|htmx" app` acha só a tag de `base.html:8` e o endereço no CSP (`app/main.py:196`): nenhum atributo `hx-` em template e nenhuma chamada `htmx.` em JavaScript. O arquivo tem 47.755 bytes (15.566 com gzip), medido com `curl -sSL https://unpkg.com/htmx.org@1.9.10/dist/htmx.min.js | wc -c` (e com `-H 'Accept-Encoding: gzip'`).
- **Plotly só serve a `/`.** O único gráfico do produto é `#grafico-ibovespa` (`app/templates/index.html:52`), e `Painel.grafico` (`app/static/graficos.js`) volta antes de chamar `Plotly` quando o elemento não existe (`if (!el) return;`). Mesmo assim `/consultor`, `/sistema` e `/novidades` baixam e compilam os 998.628 bytes do `plotly-basic-2.27.0.min.js` (334.803 com gzip; medida da spec 171).
- **Tudo síncrono no `<head>`.** O navegador para de ler o HTML até baixar e executar cada um, então nenhuma parte do painel pinta antes do Plotly compilar.

## Comportamento esperado
1. **htmx sai.** A tag do htmx some de `base.html` e o endereço `https://unpkg.com/htmx.org@1.9.10/dist/htmx.min.js` sai do `script-src` do CSP em `app/main.py`. O `script-src` fica `'self' https://cdn.plot.ly/plotly-basic-2.27.0.min.js`. Nenhuma outra diretiva do CSP muda.
2. **Plotly só em `/`.** `base.html` ganha um bloco Jinja vazio no `<head>`, logo antes da tag de `graficos.js` (sugestão de nome: `{% block scripts_pagina %}{% endblock %}`). `index.html` preenche esse bloco com a tag do Plotly, com o mesmo `src`, `integrity="sha384-C21rxKmXDHRC0bKRfO4BhLiAheJB5GEbL2ohT8ER/IW4/oXhpHW1iygb4d6p7vsb"` e `crossorigin="anonymous"` de hoje. As outras três páginas não preenchem o bloco e não têm nenhum `<script>` externo.
3. **Scripts com `defer`.** As tags do Plotly, de `graficos.js` e de `ui.js` ganham o atributo `defer`. Scripts `defer` executam na ordem do documento, depois de o HTML ser lido e antes do `DOMContentLoaded`, que é onde `ui.js` (linhas 1 e 119) registra o desenho. Ordem final no HTML de `/`: Plotly, `graficos.js`, `ui.js`.
4. **O gráfico do Ibovespa fica igual.** Conferido em 17/11 no Chromium com as três tags em `defer` nessa ordem (Plotly básico baixado da CDN, `graficos.js` e `ui.js` da `main`, `#grafico-ibovespa` com três pontos): o gráfico desenhou os traços em `.scatterlayer` e nenhum `pageerror` apareceu.

## Fontes de dados
Nenhuma nova. O servidor não acessa CDN. Plano B quando a CDN do Plotly cai ou o `integrity` recusa o arquivo: o mesmo de hoje (página sem o gráfico do Ibovespa, resto normal; o aviso no lugar do gráfico é o item 24 da *Fila*). Sem o htmx, a página deixa de depender de `unpkg.com`.

## Cálculos
Bytes de JavaScript externo baixados por visita sem cache, com as medidas acima:

| Página | Hoje | Depois | Economia |
|---|---|---|---|
| `/` | 47.755 + 998.628 = 1.046.383 | 998.628 | 47.755 (15.566 com gzip) |
| `/consultor`, `/sistema`, `/novidades` | 1.046.383 | 0 | 1.046.383 (15.566 + 334.803 = 350.369 com gzip) |

## Critérios de aceite
- [ ] `tests/test_aceite_172.py`, com `exigir_spec_done("172")`, sem internet:
  - **htmx fora:** nenhum arquivo de `app/templates/` contém `htmx`, e o cabeçalho `Content-Security-Policy` de `GET /healthz` não contém `unpkg.com` nem `htmx`;
  - **CSP só com o Plotly:** as fontes do `script-src` são exatamente `["'self'", "https://cdn.plot.ly/plotly-basic-2.27.0.min.js"]`;
  - **Plotly só em `/`:** com `TestClient`, o HTML de `GET /` tem exatamente uma tag `<script>` com `src` em `https://cdn.plot.ly/`, com o `integrity` do item 2, `crossorigin="anonymous"` e `defer`; o HTML de `GET /consultor`, `GET /sistema` e `GET /novidades` não tem nenhuma tag `<script>` cujo `src` comece com `http`. (Usar os mesmos fixtures e `monkeypatch` que os testes atuais dessas rotas usam para responder 200 sem banco e sem senha: `tests/test_aceite_088.py` (`mock_snapshots`), `tests/test_sistema.py`, `tests/test_consultor.py` e, para `/novidades`, `tests/test_aceite_156.py` (fixture `arquivo`, que troca `app.services.novidades.CAMINHO` por um arquivo em `tmp_path`). Um `TestClient(app)` cru, com o `lifespan`, não termina em 120 s neste ambiente, medido em 17/11. Se alguma rota não renderizar no teste, conferir o template renderizado pelo Jinja com o contexto mínimo e registrar a escolha no PR.)
  - **ordem e `defer`:** no HTML de `GET /`, as tags de Plotly, `/static/graficos.js` e `/static/ui.js` aparecem nessa ordem e as três têm `defer`; nas outras três páginas, `graficos.js` e `ui.js` têm `defer`.
- [ ] `tests/test_aceite_170.py`: as regras da 170 continuam valendo para o que sobra. `HTMX_SRC` e `HTMX_SRI` saem; `test_valores_sao_os_da_tabela` confere o Plotly em `index.html` (não mais em `base.html`); `test_csp_restrito_aos_dois_arquivos` passa a esperar `["'self'", PLOTLY_SRC]` (o nome do teste pode mudar para refletir um arquivo); `test_csp_e_template_casam` confere as tags externas de todos os templates, não só de `base.html`. `test_toda_tag_externa_tem_integridade` e `test_nenhum_endereco_de_pacote` não mudam.
- [ ] `tests/test_aceite_171.py`: `test_pacote_basico_com_integridade` lê `index.html` em vez de `base.html`; `test_csp_casa_com_o_pacote_basico` espera `["'self'", PLOTLY_SRC]` (e `HTMX_SRC` sai). `test_so_tracos_do_pacote` não muda.
- [ ] Os testes de navegador continuam verdes sem mudança: `test_aceite_146.py` (a regex de `_sem_scripts_externos` tira tags com `src` independentemente de `defer`, e o teste dispara o `DOMContentLoaded` à mão), `test_correcao_883.py` e `test_correcao_885.py` (abortam requisições externas; a docstring que cita "htmx" pode ficar). Se algum deles quebrar com o `defer`, é sinal de que a ordem de carga mudou: corrija o template, não o teste.
- Arquivos tocados: `app/templates/base.html`, `app/templates/index.html`, `app/main.py` (uma linha do CSP), `tests/test_aceite_170.py`, `tests/test_aceite_171.py` e o novo `tests/test_aceite_172.py`. Medido com `grep -rln "htmx" app tests`: `base.html`, `main.py`, `test_aceite_146.py` (comentário), `test_aceite_170.py`, `test_aceite_171.py`, `test_correcao_883.py` e `test_correcao_885.py` (docstrings). `docs/STATE.md` e `CHANGELOG.md` na entrega, como em todo PR.

## Invariantes de produção
- O HTML publicado de `/consultor`, `/sistema` e `/novidades` não tem nenhuma tag `<script>` com `src` externo (começando com `http`).
- O HTML publicado de `/` tem exatamente uma tag `<script>` externa, `https://cdn.plot.ly/plotly-basic-2.27.0.min.js`, com `defer` e `integrity`; nenhuma página publicada cita `htmx` ou `unpkg.com`.
- O cabeçalho `Content-Security-Policy` de `/` não contém `unpkg.com`.
- Na página `/` carregada num navegador, `#grafico-ibovespa` contém um `svg` com os traços em `.scatterlayer`, sem erro no console.

## Fora do escopo
- Aviso "gráfico indisponível" quando a CDN falha (item 24 da *Fila*).
- Servir o Plotly de `app/static` ou atualizar a versão (specs 170 e 171, *Fora do escopo*).
- `async` em vez de `defer`, `preload` ou qualquer mudança de `tema.css`: `async` quebra a ordem Plotly → `graficos.js` → `ui.js`.
- Dividir `ui.js` por página: os dois arquivos locais são pequenos e já servidos de `'self'`.
