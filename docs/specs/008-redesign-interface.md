---
id: 008
titulo: Redesign da interface segundo o guia visual
status: ready
esforco: M
---

## Problema
A página atual tem fundo claro, uma coluna de 800px que desperdiça a tela, cards altos com pouca informação, cores escritas à mão em cada template e um gráfico com tema próprio. Cada painel novo repete o padrão e o produto fica com aparência de rascunho. O dono do produto pediu um visual escuro, organizado e que aproveite a tela. O guia está em `docs/DESIGN.md` e a referência navegável em `docs/design/referencia.html`.

Esta spec tem prioridade sobre qualquer feature: a entrada correspondente está na seção *Correções* de `docs/BACKLOG.md`.

## Comportamento esperado
- A página inteira segue o `docs/DESIGN.md`: tema escuro, cabeçalho com estado do pregão e horário da coleta, grade de 12/6/1 colunas e a distribuição de painéis da seção 3.
- Comparada lado a lado com `docs/design/referencia.html` (abra os dois e capture com `make telas` e `python scripts/telas.py --pagina docs/design/referencia.html --saida telas-ref`), a página real parece o mesmo sistema.
- Nenhuma informação some: todos os painéis atuais continuam com o mesmo conteúdo, fonte e horário. O rodapé legal continua em todas as páginas (PRODUTO.md, seção 1).
- O horário exibido passa de UTC para BRT (`dd/mm/aaaa HH:MM BRT`), como pede a seção 7 do PRODUTO.md.

## Implementação
1. `app/static/tema.css` com todos os tokens da seção 2 do guia e as classes de layout e componentes. Montar `StaticFiles` em `/static` no `app/main.py` (a CSP já permite `'self'`).
2. `app/static/graficos.js` com `Painel.grafico(id, traces, opcoes)`, lendo as cores dos tokens com `getComputedStyle`. Use `'transparent'` em vez de `rgba(...)` para o fundo do Plotly.
3. `app/templates/componentes.html` com as macros `painel`, `kpi`, `variacao`, `tabela_ativos`, `medidor` e `estado` da seção 4.
4. `base.html` com o cabeçalho, o `<main class="grade">` e o rodapé; `index.html` reescrito só com macros e classes `span-N`, sem `style=`.
5. Remover o `pytestmark` de `tests/test_design.py`. É o único jeito de o CI passar quando a interface cumprir o guia (xfail estrito).
6. Se o PR passar de ~400 linhas, divida: 008a (tema, estáticos, macros e base com o painel do Ibovespa) e 008b (demais painéis e remoção do `pytestmark`). Nesse caso, mantenha o `pytestmark` até a 008b.

## Fontes de dados
Nenhuma nova. Os coletores e serviços não mudam, exceto a formatação de horário para BRT.

## Cálculos
Nenhum novo. A largura das barras nas tabelas é proporcional ao maior valor absoluto da coluna (mínimo 18%, máximo 88% da célula).

## Critérios de aceite
- [ ] `tests/test_design.py` passa sem o marcador xfail.
- [ ] Os testes existentes de cada painel continuam passando (ajuste só os que verificavam estilo ou texto que mudou, nunca os de conteúdo).
- [ ] Dado o banco de demonstração de `scripts/telas.py`, a página contém `BRT` e não contém `UTC`.
- [ ] Toda célula de variação renderizada contém `▲`, `▼` ou `■`.
- [ ] `make telas` termina sem acusar rolagem horizontal, e o corpo do PR traz as respostas do checklist visual (DESIGN.md, seção 8).

## Invariantes de produção
- O `/api/snapshot` continua com as mesmas chaves e valores de antes; só o HTML muda.
- A página em produção carrega `/static/tema.css` com status 200.

## Fora do escopo
- Tema claro e alternância de tema.
- Novos painéis, novos dados ou interações (filtros, abas, seleção de ativo).
- Trocar Plotly por outra biblioteca (exigiria ADR).
