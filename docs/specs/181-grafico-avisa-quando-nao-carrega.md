---
id: 181
titulo: O gráfico do Ibovespa avisa quando a biblioteca não carregou
status: done
esforco: P
gaveta: experiência
aceite: tests/test_aceite_181.py
origem: O gráfico diz quando a CDN não carregou
revisada: 2026-11-18
---

## Problema
A pergunta do usuário: **o gráfico em branco quer dizer que não há dado, ou que algo falhou?**

O único gráfico Plotly do produto é o do card Ibovespa, na home (`<div id="grafico-ibovespa" class="grafico">`, `app/templates/index.html:57`). A biblioteca vem da CDN (`https://cdn.plot.ly/plotly-basic-2.27.0.min.js`, `app/templates/index.html:6`), com `integrity` desde as specs 170 e 171. Se a CDN não responde, se o arquivo é bloqueado (extensão, rede corporativa) ou se o `integrity` o recusa, o navegador não define `window.Plotly`. O `DOMContentLoaded` de `app/static/ui.js:129` chama mesmo assim `Painel.grafico` (`app/static/graficos.js:2`), que chega a `Plotly.newPlot` e lança `ReferenceError`. O contêiner fica com 200 px de altura em branco (`app/static/tema.css:472`), sem texto, e a legenda logo abaixo ("N pregões · ...") continua lá, como se o gráfico estivesse desenhado.

Os painéis já dizem quando a fonte caiu (`estado('indisponivel')`, `app/templates/componentes.html:83`); o gráfico é o único lugar da tela que falha calado.

## Comportamento esperado
1. Em `Painel.grafico` (`app/static/graficos.js`), logo depois de achar o elemento: se `typeof window.Plotly === 'undefined'` ou `typeof window.Plotly.newPlot !== 'function'`, o elemento recebe o conteúdo abaixo e a função retorna sem lançar erro:

   ```html
   <div class="vazio grafico-indisponivel">Gráfico indisponível agora.<br>O navegador não carregou a biblioteca de gráficos.</div>
   ```

   O estilo é o de `.vazio` (`app/static/tema.css:214`), o mesmo do `estado('indisponivel')`; sem regra de CSS nova. O contêiner mantém a altura de 200 px, então o card não muda de tamanho.
2. Se `Plotly.newPlot` existe, o comportamento é o de hoje, sem mudança no layout, nas cores ou nas opções.
3. Se `Plotly.newPlot` existe mas a promessa que ele devolve é rejeitada, o elemento recebe o mesmo aviso do item 1 (um `.catch` na promessa já existente, em `graficos.js:33`).
4. O `role="img"` e o `aria-label` do contêiner (o resumo da série vindo do servidor) não mudam: o resumo continua verdadeiro mesmo sem o desenho.
5. A legenda `<p class="grafico-legenda">` não muda.
6. Nenhum outro script quebra: o resto do `DOMContentLoaded` de `ui.js` (heatmap, densidade, tema) segue funcionando com a CDN bloqueada.

## Fontes de dados
Nenhuma nova. O aviso depende só de o navegador ter ou não carregado o arquivo da CDN.

## Cálculos
Nenhum.

## Critérios de aceite
- [ ] `tests/test_aceite_181.py`, com `exigir_spec_done("181")`, sem internet. Arranjo do `_abrir_no_navegador` de `tests/test_aceite_156.py:244` (Playwright, `CHROMIUM_PATH`, `aba.route("**/*", ...)`, `aba.on("pageerror", ...)`), com o HTML de `GET /` gerado pelo `TestClient` com a série de 30 pregões dos helpers `relogio` e `_gravar` de `tests/test_aceite_145.py` (podem ser copiados para o teste novo). A rota responde `http://painel.teste/` com esse HTML **sem mudar as tags `<script>`**, serve `/static/graficos.js`, `/static/ui.js` e `/static/tema.css` lidos do disco e aborta todo o resto, inclusive `cdn.plot.ly`. A página é aberta com `aba.goto("http://painel.teste/")`, e o teste espera o `load` mais ~200 ms antes de ler o DOM.
  - **CDN bloqueada:** sem stub. `#grafico-ibovespa` contém o texto "Gráfico indisponível agora." e um `.grafico-indisponivel`, e nenhum `pageerror` foi registrado;
  - **Plotly presente:** antes do `goto`, `aba.add_init_script("window.Plotly = {newPlot: (id) => { document.getElementById(id).dataset.desenhado = '1'; return Promise.resolve(); }};")`. `#grafico-ibovespa` tem `data-desenhado="1"` e **não** contém "Gráfico indisponível";
  - **newPlot rejeita:** `add_init_script` com `window.Plotly = {newPlot: () => Promise.reject(new Error('x'))};`. `#grafico-ibovespa` contém "Gráfico indisponível agora.";
  - nos três casos, `#grafico-ibovespa` mantém `role="img"` e o mesmo `aria-label` do HTML do servidor.

  O stub entra por `add_init_script`, e não servido no lugar de `cdn.plot.ly`, porque o `<script>` da CDN tem `integrity` (specs 170 e 171): um corpo diferente do arquivo real é recusado pelo navegador, e o stub nunca rodaria. Com a CDN abortada, o `<script>` falha sem tocar no `window.Plotly` já definido pelo init script.
- [ ] `tests/test_aceite_145.py`, `tests/test_aceite_170.py`, `tests/test_aceite_171.py`, `tests/test_aceite_172.py` e `tests/test_aceite_173.py` seguem verdes sem alteração (o `index.html` não muda).
- [ ] `app/novidades.json` ganha uma entrada `melhoria` da 181 (exigência do `tests/test_aceite_156.py:232` para a gaveta experiência), por exemplo: "Quando o navegador não consegue carregar a biblioteca de gráficos, o gráfico do Ibovespa diz isso em vez de ficar em branco."
- Arquivos tocados: `app/static/graficos.js`, `app/novidades.json` e o novo `tests/test_aceite_181.py`. Hoje `grep -rl "Painel.grafico\|graficos.js" app tests` dá `app/static/ui.js`, `app/templates/base.html` e quatro testes (`test_aceite_172.py`, `test_aceite_146.py`, `test_aceite_176.py`, `test_design.py`), que não precisam mudar: a assinatura de `Painel.grafico` e o carregamento dos scripts ficam iguais.

## Invariantes de produção
- No site publicado, com a CDN no ar, `#grafico-ibovespa` da home tem um `<svg>` desenhado e **não** contém "Gráfico indisponível" (o aviso só aparece quando a biblioteca falta; aviso permanente seria defeito).
- O console da home não registra `ReferenceError: Plotly is not defined`.

## Fora do escopo
- Trocar a CDN, servir o Plotly pelo próprio servidor ou criar fallback para outra CDN (seria spec de saúde técnica própria; o `integrity` das 170 e 171 fica como está).
- Avisar falha de outros scripts (`ui.js`, `graficos.js` em si) ou dos gráficos SVG feitos no servidor (Maré, sparklines), que não dependem de CDN.
- Mudar `docs/DESIGN.md` ou o texto do `estado('indisponivel')`.
- Contar no `/sistema` quantas vezes o aviso apareceu (não há telemetria do navegador).
