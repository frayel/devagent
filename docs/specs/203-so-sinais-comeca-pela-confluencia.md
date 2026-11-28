---
id: 203
titulo: A aba Só Sinais começa pelas ações em vários radares
status: ready
esforco: P
gaveta: experiência
aceite: tests/test_aceite_203.py
origem: "Só Sinais" começa pela confluência
---

## Problema
O usuário que abre a aba **Só Sinais** pergunta: "qual ação está chamando atenção agora?"

Hoje a aba mostra todos os painéis na ordem do HTML da home, com gráficos, tabelas e cards de visão macro escondidos (`body.modo-so-sinais` em `app/static/tema.css`). O card que responde exatamente essa pergunta, **"Em vários radares"** (spec 155, classe `painel-confluencia`), está no meio da página: em `app/templates/index.html` ele vem depois do Ibovespa, da Dispersão, da Coesão, do Fator Peso Pesado, da Concentração Setorial, das pressões, das altas e baixas, da Força Relativa e da Anomalia de Peso. Na prática, quem entra em Só Sinais vê primeiro o Ibovespa e uma sequência de cabeçalhos de painéis cujas tabelas sumiram, e o cruzamento dos radares fica abaixo da dobra.

A spec 155 deixou a aba de fora de propósito ("A aba Só Sinais não muda nesta spec"), e a 167 apontou este item para spec própria.

## Comportamento esperado
1. **Ao entrar em Só Sinais** (clique no botão `data-aba="sinais"` ou `/?aba=sinais`, que hoje simula o clique), o card **"Em vários radares"** passa a ser o **primeiro painel da grade**: fica imediatamente antes do painel do Ibovespa (`.painel-ibovespa`), abaixo da manchete, dos destaques e da barra de abas, que não mudam de lugar.
2. **A mudança é na ordem do documento, não só visual.** O `app/static/ui.js` move o nó `section.painel-confluencia` para antes de `.painel-ibovespa` (por exemplo, `ibovespa.before(confluencia)`). Não usar a propriedade CSS `order`: ela mudaria só o desenho, a ordem de foco do teclado e do leitor de tela continuaria a antiga (WCAG 1.3.2 e 2.4.3), e todos os itens da grade têm `order: 0`, inclusive a manchete e as abas, que subiriam junto.
3. **Ao sair de Só Sinais** (clique em qualquer outra aba), o card volta exatamente ao lugar de origem: entre a Anomalia de Peso e a seção "Sem alertas", como no HTML servido. Guardar a posição original ao carregar a página (um marcador, como um `document.createComment('confluencia')` inserido no lugar dele, ou a referência ao irmão seguinte) e reinserir o card ali. Na aba Alertas Intraday ele continua o primeiro card da aba, como hoje.
4. **Sem card, nada muda.** O card só é renderizado quando há ação em 2 ou mais radares (`{% if confluencia and confluencia.acoes %}`). Sem ele, Só Sinais fica como hoje e o script não gera erro no console.
5. O conteúdo do card não muda: título, lista, "de R radares lidos agora", memória da confluência (spec 186), ⓘ e rodapé seguem como estão. O CSS de Só Sinais não esconde nada dele (é `visao-micro` e usa `ul`, não `table`); isso não muda.
6. Pregão passado (`?data=`): mesmo comportamento, porque o card e o script são os mesmos.
7. Entrada em `app/novidades.json` (tipo `melhoria`, `spec: "203"`, `onde` com `aba: "sinais"`, `aba_nome: "Só Sinais"` e `painel: "Em vários radares"`), exigida por `test_toda_entrega_visivel_tem_novidade` para spec de experiência entregue.

## Fontes de dados
Nenhuma fonte nova. O card usa o contexto `confluencia` que `index()` já monta a partir dos radares (spec 155). Se os radares estiverem indisponíveis, o card não aparece e a aba fica como hoje (item 4).

## Cálculos
Nenhum. A ordem das linhas do card, a contagem de radares e o rodapé continuam os da spec 155. Exemplo da ordem dos painéis, para o teste:

- HTML servido (Visão Geral): `... Anomalia de Peso` → `Em vários radares` → `Sem alertas` → `Radar de volume` ...; o Ibovespa é o primeiro `section.painel` da grade.
- Depois do clique em Só Sinais: o primeiro `section.painel` dentro da grade é `Em vários radares`, o segundo é o do Ibovespa.
- Depois do clique em Alertas Intraday: a ordem dos `section.painel` no documento é de novo idêntica à do HTML servido (mesma lista de títulos `h2`, na mesma ordem).

## Critérios de aceite
Em `tests/test_aceite_203.py`, com `exigir_spec_done("203")`. Os testes de navegador servem a página da aplicação ao Chromium headless como `tests/test_correcao_883.py` (rota interceptada, requisição externa abortada) e usam um contexto com confluência como o `radares`/`_exemplo` de `tests/test_aceite_155.py` (pelo menos uma ação em 2 radares).

- [ ] Com confluência, depois do clique em `data-aba="sinais"`: o primeiro `section.painel` em ordem de documento é o que contém `h2` "Em vários radares", e o segundo tem a classe `painel-ibovespa`. A caixa (`bounding_box`) do card fica acima da do Ibovespa.
- [ ] Com confluência, abrindo `/?aba=sinais` direto: a mesma ordem do item acima.
- [ ] Com confluência, clique em Só Sinais e depois em Alertas Intraday: a lista de títulos `h2` de todos os `section.painel`, em ordem de documento, é igual à lista lida antes do primeiro clique (o card voltou ao lugar).
- [ ] Ida e volta duas vezes (Só Sinais → Visão Geral → Só Sinais → Visão Geral) não duplica o card: há exatamente um `section.painel-confluencia` no documento ao final, e a ordem é a do HTML servido.
- [ ] Sem confluência (nenhuma ação em 2 radares, ou o banco de demonstração de `scripts/telas.py`, que hoje não gera o card): clique em Só Sinais não registra erro no console (`page.on("pageerror")` vazio) e o primeiro `section.painel` é o do Ibovespa.
- [ ] Nenhuma violação de CSP no console durante os cliques (como em `test_consultor_sem_violacao_de_csp`).
- [ ] `app/static/tema.css` não ganha regra com `order:` para `.painel-confluencia` (a ordem vem do documento, item 2).

## Invariantes de produção
- Em `/` com o card "Em vários radares" presente, o HTML servido continua com o card entre a Anomalia de Peso e "Sem alertas" (a mudança de ordem é só no navegador, na aba Só Sinais). `/api/snapshot` não muda.
- Na aba Só Sinais, aberta por `/?aba=sinais`, o primeiro painel visível abaixo das abas é "Em vários radares" quando ele existe, e o do Ibovespa quando não existe.

## Fora do escopo
- Card vazio ("nenhuma ação em 2 ou mais radares agora") em Só Sinais: hoje o card some sem confluência, e mudar isso é decisão da spec 155, não desta.
- Reorganizar o resto da aba Só Sinais (os cabeçalhos de painéis cujas tabelas somem, os radares vazios). Vai para a rodada de poda (item 2 da *Fila*) ou para uma revisão de experiência própria.
- Destacar a confluência na Visão Geral: a linha "Destaques agora" (spec 167) já mostra a ação em mais radares.
- Mudar a ordem de qualquer outra aba ou o comportamento de `?aba=` (spec 156).
