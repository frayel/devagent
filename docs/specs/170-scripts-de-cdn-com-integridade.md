---
id: 170
titulo: O navegador recusa htmx e Plotly alterados na CDN
status: ready
esforco: P
gaveta: saúde técnica
aceite: tests/test_aceite_170.py
origem: Scripts de CDN com integridade
revisada: 2026-11-17
---

## Problema
Se a unpkg ou a CDN do Plotly entregarem outro arquivo amanhã, o painel roda o código delas?

Hoje roda. `app/templates/base.html:8-9` carrega dois scripts de terceiros em toda página, sem o atributo `integrity`:

```html
<script src="https://unpkg.com/htmx.org@1.9.10"></script>
<script src="https://cdn.plot.ly/plotly-strict-2.27.0.min.js"></script>
```

O CSP (`app/main.py:196`) libera `script-src 'self' https://unpkg.com https://cdn.plot.ly`: qualquer arquivo dos dois domínios, de qualquer pacote. O resto do cabeçalho já é estrito (sem `unsafe-inline`, sem `unsafe-eval`, estilos por hash), e o que segura o painel inteiro é a confiança em dois servidores alheios. Um pacote comprometido na unpkg, ou um `htmx.org@1.9.10` republicado, roda com o mesmo acesso que o `ui.js`.

Há também um detalhe do htmx: o endereço `https://unpkg.com/htmx.org@1.9.10` não é um arquivo, é um redirecionamento. Medido em 17/11: a unpkg responde `301` para `/htmx.org@1.9.10/dist/htmx.min.js`, que responde `200`. O arquivo que o navegador executa é decidido pelo campo `unpkg` do `package.json` do pacote, não pelo painel.

## Comportamento esperado
1. **Endereço do arquivo, não do pacote.** O htmx passa a ser carregado de `https://unpkg.com/htmx.org@1.9.10/dist/htmx.min.js`, o destino do redirecionamento. Mesma versão, mesmo arquivo de hoje (o hash abaixo confere com o do endereço antigo seguido até o fim). O Plotly já aponta para um arquivo e fica no mesmo endereço.
2. **`integrity` e `crossorigin` nas duas tags.** Cada `<script>` externo de `base.html` ganha `integrity="sha384-..."` com o hash do arquivo e `crossorigin="anonymous"`. Sem `crossorigin`, o navegador não confere a integridade de recurso de outra origem. As duas CDNs respondem `access-control-allow-origin: *` (medido em 17/11), então o modo anônimo funciona. Valores medidos em 17/11 com `curl -sSL <url> | openssl dgst -sha384 -binary | openssl base64 -A`:

   | Arquivo | Bytes | `integrity` |
   |---|---|---|
   | `https://unpkg.com/htmx.org@1.9.10/dist/htmx.min.js` | 47.755 | `sha384-D1Kt99CQMDuVetoL1lrYwg5t+9QdHe7NLX/SoJYkXDFfX37iInKRy5xLSi8nO7UC` |
   | `https://cdn.plot.ly/plotly-strict-2.27.0.min.js` | 3.918.579 | `sha384-rfGldZ9CDA25KeQk3fLmxTf/H2jlNsx6cfUIYwkBNUz1z5ngqchk1jAp7fC9dj9y` |

   O hash do htmx é o mesmo que a documentação do htmx publica para a 1.9.10, o que confirma a medida por uma segunda fonte. Quem implementar mede os dois de novo antes do PR; se algum diferir, para e registra no relatório em vez de copiar o novo valor (arquivo de versão fixa que mudou é exatamente o que esta spec quer pegar).
3. **CSP restrito aos dois arquivos.** `script-src` passa de `'self' https://unpkg.com https://cdn.plot.ly` para `'self' https://unpkg.com/htmx.org@1.9.10/dist/htmx.min.js https://cdn.plot.ly/plotly-strict-2.27.0.min.js`. O CSP aceita caminho completo na fonte; como o htmx deixa de redirecionar (item 1), o caminho vale. Nenhuma outra diretiva muda.
4. **Se a CDN mudar o arquivo, o painel degrada como se a CDN tivesse caído.** O navegador recusa o script e registra o erro no console; a página continua servindo o HTML, como já acontece quando a CDN está fora do ar. Esta spec não cria fallback local (ver *Fora do escopo*).

Não muda: as versões (htmx 1.9.10, Plotly 2.27.0 strict), a ordem dos scripts, os dois scripts locais (`graficos.js`, `ui.js`), qualquer outro cabeçalho de segurança.

## Fontes de dados
Nenhuma nova. As duas CDNs já são carregadas pelo navegador do usuário; o servidor não as acessa. Plano B: o mesmo de hoje quando a CDN cai (página sem gráficos e sem atualização por htmx); um fallback em `app/static` é outra spec.

## Cálculos
O `integrity` é `sha384-` seguido do SHA-384 dos **bytes do arquivo como a CDN os entrega** (depois de seguir redirecionamentos e sem descompressão manual: o `curl` sem `--compressed` recebe o corpo sem `Content-Encoding`), em Base64 padrão com `=` de preenchimento quando houver. De ponta a ponta, para o htmx:

1. `curl -sSL https://unpkg.com/htmx.org@1.9.10/dist/htmx.min.js` → `200`, 47.755 bytes.
2. SHA-384 → 48 bytes → Base64 de 64 caracteres: `D1Kt99CQMDuVetoL1lrYwg5t+9QdHe7NLX/SoJYkXDFfX37iInKRy5xLSi8nO7UC`.
3. Atributo: `integrity="sha384-D1Kt99CQMDuVetoL1lrYwg5t+9QdHe7NLX/SoJYkXDFfX37iInKRy5xLSi8nO7UC"`.

## Critérios de aceite
- [ ] `tests/test_aceite_170.py`, com `exigir_spec_done("170")`, sem internet:
  - **toda tag externa tem integridade:** em todo `app/templates/*.html`, cada `<script src="http...">` tem `integrity` casando com `^sha384-[A-Za-z0-9+/]{64}$` e `crossorigin="anonymous"`;
  - **os valores são os da tabela:** a tag do htmx tem `src` e `integrity` iguais aos da linha do htmx, e a do Plotly, aos da linha do Plotly;
  - **nenhum endereço de pacote:** nenhum `src` externo termina em `@<versão>` sem caminho de arquivo (pega a volta ao endereço que redireciona);
  - **CSP restrito:** as fontes do `script-src` de `GET /healthz`, separadas por espaço, são exatamente `'self'` e os dois endereços de arquivo; `https://unpkg.com` e `https://cdn.plot.ly` não aparecem como fonte sozinhos;
  - **CSP e template casam:** todo `src` externo de `base.html` aparece como fonte no `script-src` (trocar um sem o outro reprova).
- [ ] `tests/test_main.py::test_security_headers` continua verde sem mudar asserção (as substrings `https://unpkg.com` e `https://cdn.plot.ly` seguem no CSP como prefixo dos caminhos).
- [ ] Os testes que abortam requisições externas no Chromium (`tests/test_aceite_146.py`, `tests/test_correcao_883.py`, `tests/test_correcao_885.py`) e o resto do `make verify` continuam verdes. Os três roteiam `**/*` (casa o novo caminho do htmx) e o `_sem_scripts_externos` do 146 remove a tag inteira por `<script\b[^>]*\bsrc=[^>]*>`, que tolera os atributos novos: nenhum dos três precisa mudar.
- Arquivos tocados: `app/templates/base.html`, `app/main.py` (só a linha do `script-src`) e o novo `tests/test_aceite_170.py`. Medido com `grep -rl "unpkg\|cdn.plot.ly" app tests`: 3 arquivos (`base.html`, `main.py`, `tests/test_main.py`), e o último não muda. `docs/STATE.md` e `CHANGELOG.md` na entrega, como em todo PR.

## Invariantes de produção
- Em `/`, o HTML publicado tem exatamente duas tags `<script>` de outra origem, cada uma com `integrity` e `crossorigin="anonymous"`.
- Para cada uma, o SHA-384 em Base64 do arquivo baixado do `src` é igual ao valor do `integrity` (o auditor baixa e compara).
- Na página carregada num navegador, `window.htmx` e `window.Plotly` existem (o hash não bloqueou o próprio script) e os gráficos da Maré aparecem.
- O cabeçalho `Content-Security-Policy` de `/` não libera `https://unpkg.com` nem `https://cdn.plot.ly` como origem inteira.

## Fora do escopo
- Servir htmx e Plotly de `app/static`, com ou sem fallback quando a CDN falhar. O `PRODUTO.md` declara Plotly via CDN; trocar isso é decisão de stack, com o peso de 3,9 MB do Plotly no repositório e no deploy.
- Atualizar htmx (1.9.10 → 2.x) ou Plotly: muda comportamento e pede spec própria.
- Um teste que baixe as CDNs e confira o hash: os testes não acessam a internet (`PRODUTO.md`, seção 2). Essa conferência é a invariante do auditor.
- Qualquer outra diretiva do CSP, inclusive `style-src`.
