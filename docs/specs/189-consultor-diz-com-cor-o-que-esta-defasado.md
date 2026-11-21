---
id: 189
titulo: O Consultor mostra com cor qual informação está defasada
status: done
revisada: 2026-11-21
esforco: P
gaveta: experiência
aceite: tests/test_aceite_189.py
origem: Teste que reprova classe sem estilo
---

## Problema
Os dados em que o Consultor se apoiou estão em dia? No quadro de informações do topo de `/consultor` (`app/templates/consultor.html:32–56`, na `main` de 21/11/2026, `dc13fcf`), cada fonte termina num selo "Atualizado" ou "Defasado". O selo usa `badge`, `badge-positivo` e `badge-negativo`, que não têm seletor em lugar nenhum (medida da spec 187): a palavra sai como texto comum, na cor do texto, colada na linha de cima. "Defasado" e "Atualizado" têm a mesma cara, e o usuário só descobre a diferença lendo palavra por palavra. O resto do produto já mostra estado num selo colorido com a palavra escrita (`.selo.ok`, `.selo.atencao` em `/sistema`, spec 082).

Esta é a fatia 3 do item *Teste que reprova classe sem estilo* do backlog. A spec 187 criou a lista `SEM_ESTILO_CONHECIDAS` (43 classes), a 188 tirou 11 (sobram 32). Esta tira as 7 que só o `consultor.html` usa:

| Classe | Onde (`consultor.html`) | Hoje | Depois |
|---|---|---|---|
| `badge` | 38, 46, 53 | sem efeito | `selo` |
| `badge-positivo` | 38, 46, 53 | sem efeito | `ok` |
| `badge-negativo` | 38, 46 | sem efeito | `atencao` |
| `status-neutro` | 103, no `<h3>` "Opiniões Recentes" | sem efeito | sai (os outros `<h3>` do `grupo-consultor`, linha 178, não têm classe) |
| `lista-opinioes` | 104, `div` que embrulha as opiniões | sem efeito | sai a classe (o `div` pode ficar ou sair; nada muda na tela) |
| `rodape-painel` | 163, rodapé do diagnóstico das opiniões | sem efeito (o texto só fica menor pelo `<small>`) | `fonte-dado`, sem o `<small>` |
| `tabela-sem-sinal` | 236, tabela do acordeão "Sem sinal" | sem efeito | sai (fica só `tabela-consultor`) |

## Comportamento esperado
Só muda o HTML de `app/templates/consultor.html`. Nenhuma regra nova no CSS, nenhum dado novo, nenhuma mudança em `app/consultor/informacoes.py`.

- **Selo de estado.** Em *Sinais técnicos* e *Opiniões de especialistas*: `<span class="selo ok">Atualizado</span>` quando o estado é `Atualizado`, e `<span class="selo atencao">Defasado</span>` em qualquer outro valor. A palavra continua escrita: a cor nunca é a única pista. Em *Composição do Ibovespa*, o selo fixo passa a `<span class="selo ok">Atualizado</span>`.
- **Por que `atencao` e não `problema`.** "Defasado" quer dizer que o dado é velho, não que está errado; a página continua recomendando e já mostra a faixa `alerta` com a frase do motivo (linhas 21–30). Em `/sistema`, `problema` fica para o que está quebrado.
- **Título "Opiniões Recentes"** sai sem classe, como os títulos dos grupos *Comprar*, *Vender*, *Aguardar* e *No radar*.
- **Rodapé do diagnóstico das opiniões** ("Última extração: ... · descartadas: N") vai num `<div class="fonte-dado">`, a mesma classe das notas da tabela de regras (tamanho `--fs-meta`, cor `--texto-2`). O texto não muda.
- **Tabela "Sem sinal"** fica com `class="tabela-consultor"`; nada muda na tela.
- `SEM_ESTILO_CONHECIDAS` de `tests/test_classes_com_estilo.py` perde as 7 entradas (e o comentário `# consultor.html`) no mesmo PR, e o teste do teto passa a `<= 25`. O teste da 187 reprova a exceção vencida se alguma ficar.
- `app/novidades.json` ganha a entrada da spec (o `tests/test_aceite_156.py` exige para spec com tela): uma `melhoria`, algo como "O quadro do Consultor mostra em amarelo a informação defasada."

## Fontes de dados
Nenhuma fonte nova. O estado vem de `construir_informacoes_de` (`app/consultor/informacoes.py`), que já devolve `estado_sinais` e `estado_opinioes` com `"Atualizado"` ou `"Defasado"`. Se o Consultor estiver indisponível, a página mostra o `alerta` `#consultor-indisponivel` de hoje e o quadro não aparece; nada muda nisso.

## Cálculos
Nenhum cálculo novo; o estado já é calculado em `informacoes.py`. Exemplo de ponta a ponta, do dado até o selo:

- Agora é quinta, 19/11/2026, 15:00 BRT (dia de pregão; a sexta 20/11 é feriado nacional). As opiniões foram extraídas em 18/11/2026 às 10:00 BRT: idade de 29 h, maior que 24 h em dia útil, então `estado_opinioes = "Defasado"` (`informacoes.py:87–90`). O quadro mostra `<span class="selo atencao">Defasado</span>` em *Opiniões de especialistas*, e a faixa `#alerta-opinioes-defasado` continua acima.
- Os sinais referem-se ao pregão de 18/11/2026 e o último pregão fechado, às 15:00 de 19/11, é 18/11: `estado_sinais = "Atualizado"`. O quadro mostra `<span class="selo ok">Atualizado</span>` em *Sinais técnicos*.

## Critérios de aceite
`tests/test_aceite_189.py`, com `exigir_spec_done("189")`, sem internet, lendo `GET /consultor` com o `TestClient` (como `tests/test_aceite_165.py` e `tests/test_aceite_180.py`) e trocando `app.consultor.informacoes.construir_informacoes_de` por um dublê com `monkeypatch`, para fixar os estados sem depender do relógio. Detalhes que a revisão conferiu na `main`:

- `app/main.py:842` importa `construir_informacoes_de` dentro da rota, então o `monkeypatch.setattr(app.consultor.informacoes, "construir_informacoes_de", dublê)` vale na chamada seguinte. O dublê devolve todas as chaves que o template lê: `estado_sinais`, `frase_sinais`, `sinais_pregao`, `sinais_coletado_em`, `estado_opinioes`, `frase_opinioes`, `opinioes_extraidas_em`, `opinioes_materia_mais_recente` e `composicao_conferida_em`.
- `calcular_consultor` também é trocado (`monkeypatch.setattr(app.main, "calcular_consultor", ...)`), com o mesmo dicionário de `_pagina` do `tests/test_aceite_165.py`.
- O rodapé "Última extração:" só aparece quando não há opinião (`{% if not opinioes_por_ativo %}`, `consultor.html:144`): o caso que confere o `fonte-dado` usa `opinioes_recentes = []`.
- O teto de `tests/test_aceite_187.py:108` (`<= 43`) continua passando com 25; só o de `tests/test_classes_com_estilo.py:176` muda.


- [ ] Com `estado_sinais = "Atualizado"` e `estado_opinioes = "Defasado"`, o HTML contém `<span class="selo ok">Atualizado</span>` dentro do bloco *Sinais técnicos* e `<span class="selo atencao">Defasado</span>` dentro do bloco *Opiniões de especialistas* (o bloco é o trecho entre o `<h4>` com o título e o `</div>` que fecha o `info-conteudo`).
- [ ] Com os dois estados `"Defasado"`, nenhum dos dois blocos contém `selo ok`.
- [ ] O bloco *Composição do Ibovespa* contém `<span class="selo ok">Atualizado</span>`.
- [ ] O `<h3>` com "Opiniões Recentes" não tem atributo `class`.
- [ ] O texto "Última extração:" está dentro de um elemento com a classe `fonte-dado`.
- [ ] Nenhuma das 7 classes da tabela do *Problema* aparece como token num `class="..."` de `app/templates/consultor.html` (ler o arquivo e usar `classes_dos_templates` de `tests/test_classes_com_estilo.py`, não procurar o texto).
- [ ] `SEM_ESTILO_CONHECIDAS` não tem nenhuma das 7 e tem no máximo 25 entradas; o teste da spec 187 passa contra os arquivos reais.
- [ ] `make verify` passa.

## Invariantes de produção
- Em `/consultor`, cada um dos três blocos do quadro de informações termina num `span` com a classe `selo` e o texto "Atualizado" ou "Defasado".
- Todo selo "Defasado" tem a classe `atencao`; todo selo "Atualizado" tem a classe `ok`. Nenhum selo do quadro sai sem cor de fundo.
- Quando um selo diz "Defasado", a faixa `alerta` com a frase do motivo da mesma fonte (`#alerta-sinais-defasado` ou `#alerta-opinioes-defasado`) também está na página.
- Em 360 px, `/consultor` não rola para o lado (`make telas` sem `PROBLEMA:`).
- `/api/consultor` responde 200 com as mesmas chaves de antes.

## Fora do escopo
- Depende das specs 187 e 188 (`done`).
- O selo de *Composição do Ibovespa* sempre dizer "Atualizado": `CARTEIRA_CONFERIDA_EM` é uma constante e não há regra de defasagem para a composição. Medir quando ela deveria virar "Defasado" (a B3 rebalanceia a carteira a cada quatro meses) é outra spec; aqui só muda a classe.
- O `badge-confianca` do cabeçalho: já tem estilo.
- As outras 25 classes da lista (`index.html`, `componentes.html`, `base.html`, `sistema.html`): seguem no item *Teste que reprova classe sem estilo* da Fila do `docs/BACKLOG.md`.
- Mudar a regra de defasagem (24 h em dia útil, 72 h fora dele, 4 dias para os sinais) ou os textos das faixas.
- Dar estilo próprio às linhas do quadro (o `<br>` entre os campos).
