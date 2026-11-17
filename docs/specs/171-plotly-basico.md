---
id: 171
titulo: A página baixa só o Plotly que desenha linhas
status: done
esforco: P
gaveta: poda
aceite: tests/test_aceite_171.py
origem: Plotly de 3,9 MB para desenhar linhas
revisada: 2026-11-17
---

## Problema
Quanto do JavaScript que a página baixa ela usa para desenhar o único gráfico do produto?

Menos de um quarto. Toda página do painel (as quatro que estendem `base.html`: `/`, `/consultor`, `/sistema`, `/novidades`) carrega `https://cdn.plot.ly/plotly-strict-2.27.0.min.js`, o pacote **completo** do Plotly, com os 48 tipos de traço (mapas, 3D, WebGL, finanças, polares...). O produto desenha um gráfico só: a linha do Ibovespa em `/` (`app/static/ui.js:120-173`), com dois traços `type: 'scatter'`, `mode: 'lines'`, um deles com `fill: 'tonexty'`. Nenhum outro `type` de traço aparece em `app/` (`grep -rn "type:" app/static app/templates`), e `graficos.js` só chama `Plotly.newPlot`.

O Plotly publica, na mesma versão e na mesma CDN, o pacote **básico**, com os traços `scatter`, `bar` e `pie`. Medido em 17/11 (`curl -sSL <url> | wc -c`, e com `-H 'Accept-Encoding: gzip'` para o tamanho que o navegador transfere):

| Arquivo | Bytes | Transferido (gzip) | Tipos de traço |
|---|---|---|---|
| `plotly-strict-2.27.0.min.js` (hoje) | 3.918.579 | 1.179.037 | 48 |
| `plotly-basic-2.27.0.min.js` | 998.628 | 334.803 | 3 (`scatter`, `bar`, `pie`) |

Os tipos foram contados com `Object.keys(Plotly.PlotSchema.get().traces)` em cada pacote carregado no Chromium. A troca tira 2.919.951 bytes de JavaScript que o navegador baixa, descompacta e compila a cada visita sem cache (844.234 bytes transferidos), em toda página, inclusive nas três que não têm gráfico.

## Comportamento esperado
1. **Pacote básico, mesma versão.** Em `app/templates/base.html`, a tag do Plotly passa a apontar para `https://cdn.plot.ly/plotly-basic-2.27.0.min.js`, com `integrity="sha384-C21rxKmXDHRC0bKRfO4BhLiAheJB5GEbL2ohT8ER/IW4/oXhpHW1iygb4d6p7vsb"` e `crossorigin="anonymous"` (a CDN responde `access-control-allow-origin: *` para o arquivo, medido em 17/11). A posição da tag, a do htmx e as dos dois scripts locais não mudam.
2. **CSP acompanha.** Em `app/main.py`, o `script-src` troca o endereço do Plotly pelo novo: `'self' https://unpkg.com/htmx.org@1.9.10/dist/htmx.min.js https://cdn.plot.ly/plotly-basic-2.27.0.min.js`. Nenhuma outra diretiva muda.
3. **O gráfico do Ibovespa fica igual.** Mesmos traços, mesmo preenchimento até a base invisível, mesmo `hovertemplate`, mesmo `hovermode: 'x unified'`, mesmos rótulos dos eixos (`tickformat: '%d/%m'`, `separators: ',.'`). Conferido em 17/11 no Chromium com os dois pacotes, sob o CSP do app (`script-src` com o arquivo e `style-src` com os dois hashes atuais), desenhando os dois traços de `ui.js` com três pontos: os atributos `d` de todos os `path` de `.scatterlayer` e os textos dos ticks saíram idênticos, e nenhum dos dois pacotes registrou violação de CSP própria. O pacote básico não usa `eval` (não precisa de `'unsafe-eval'`), como o `strict`.
4. **Gráfico novo com outro tipo de traço exige trocar o pacote.** Se um dia um painel precisar de `heatmap`, `candlestick` ou outro tipo fora do básico, a spec dele troca o arquivo (para `plotly-cartesian`, `plotly-finance` ou de volta ao `strict`) e o `integrity`. O teste desta spec reprova um `type:` fora dos três para lembrar disso.

Quem implementar mede o hash de novo antes do PR (`curl -sSL https://cdn.plot.ly/plotly-basic-2.27.0.min.js | openssl dgst -sha384 -binary | openssl base64 -A`). Se diferir do valor acima, para e registra no relatório em vez de copiar o novo (arquivo de versão fixa que mudou é o que a spec 170 quer pegar). O hash do `plotly-strict` medido na mesma sessão bateu com o da spec 170, o que confirma o método.

## Fontes de dados
Nenhuma nova. A CDN do Plotly já é carregada pelo navegador do usuário; o servidor não a acessa. Plano B: o mesmo de hoje quando a CDN cai ou o `integrity` recusa o arquivo (página sem o gráfico do Ibovespa, resto da página normal; o aviso no lugar do gráfico é o item 24 da *Fila*).

## Cálculos
Economia por visita sem cache, com os números da tabela:

- bytes de JavaScript: 3.918.579 − 998.628 = 2.919.951 (−74,5%);
- bytes transferidos com gzip: 1.179.037 − 334.803 = 844.234 (−71,6%).

O `integrity` segue a regra da spec 170: `sha384-` + Base64 do SHA-384 dos bytes que a CDN entrega (`curl` sem `--compressed`).

## Critérios de aceite
- [ ] `tests/test_aceite_171.py`, com `exigir_spec_done("171")`, sem internet:
  - **pacote básico com integridade:** em `base.html` há exatamente uma tag `<script>` com `src` em `https://cdn.plot.ly/`, igual a `https://cdn.plot.ly/plotly-basic-2.27.0.min.js`, com o `integrity` do item 1 e `crossorigin="anonymous"`;
  - **CSP casa:** as fontes do `script-src` de `GET /healthz` são exatamente `'self'`, o endereço do htmx e o do Plotly básico; `plotly-strict` não aparece no cabeçalho;
  - **só traços do pacote:** toda ocorrência de `type:` seguida de texto entre aspas (regex `type:\s*['"](\w+)['"]`) em `app/static/*.js` e `app/templates/*.html` tem o nome em `{scatter, bar, pie}`. Na `main` de hoje casam só os dois `type: 'scatter'` de `ui.js` (linhas 141 e 150); nenhum outro `type:` com aspas existe nesses arquivos; o teste falha se encontrar zero (para não passar por regex quebrada).
- [ ] `tests/test_aceite_170.py`: as constantes `PLOTLY_SRC` e `PLOTLY_SRI` passam para o endereço e o hash do pacote básico; nenhuma outra linha do arquivo muda. As cinco regras da 170 (integridade em toda tag externa, nenhum endereço de pacote, CSP restrito a arquivos, CSP e template casando) continuam valendo com o arquivo novo.
- [ ] `tests/test_main.py::test_security_headers` continua verde sem mudança (`https://cdn.plot.ly` segue como prefixo do caminho). Os testes que abortam requisições externas no Chromium (`test_aceite_146.py`, `test_correcao_883.py`, `test_correcao_885.py`) não citam o nome do arquivo e não mudam.
- Arquivos tocados: `app/templates/base.html` (uma linha), `app/main.py` (uma linha), `tests/test_aceite_170.py` (duas constantes) e o novo `tests/test_aceite_171.py`. Medido com `grep -rl "plotly-strict" app tests`: `app/templates/base.html`, `app/main.py`, `tests/test_aceite_170.py`. `docs/STATE.md` e `CHANGELOG.md` na entrega, como em todo PR.

## Invariantes de produção
- Em `/`, o HTML publicado carrega `https://cdn.plot.ly/plotly-basic-2.27.0.min.js` e nenhum outro arquivo de `cdn.plot.ly`; o SHA-384 do arquivo baixado é igual ao `integrity` da tag.
- Na página `/` carregada num navegador, `window.Plotly` existe, `Object.keys(Plotly.PlotSchema.get().traces)` tem 3 itens, e `#grafico-ibovespa` contém um `svg` com dois traços em `.scatterlayer` e nenhum erro de CSP no console vindo do Plotly.
- O cabeçalho `Content-Security-Policy` de `/` não cita `plotly-strict`.

## Fora do escopo
- Tirar o Plotly das três páginas sem gráfico (`/consultor`, `/sistema`, `/novidades`) ou carregá-lo com `defer`: muda a ordem de carga de `graficos.js` e `ui.js` e pede teste de navegador próprio. Já está na *Fila* (item 25), junto com o htmx, que nenhum template usa.
- Atualizar o Plotly (2.27.0 → 2.35 ou 3.x) ou trocar de biblioteca: muda comportamento e pede spec própria.
- Servir o Plotly de `app/static` ou fallback local (mesma razão da spec 170).
- O aviso "gráfico indisponível" quando a CDN falha (item 24 da *Fila*).
