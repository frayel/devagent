---
id: 192
titulo: Seletor do tema que nada usa reprova o teste
status: ready
esforco: P
gaveta: poda
aceite: tests/test_aceite_192.py
origem: CSS sem uso sai do tema
---

## Problema
"O que do `tema.css` ainda pinta alguma coisa na tela?" Quem mexe no visual lê regras que parecem valer e não valem. O caso mais enganoso é o modo *Só Sinais* (`app/static/tema.css:288–340`): cinco regras e três `:not()` citam `.painel-tendencia`, `.painel-apetite` e `.painel-rotacao`, mas nenhum template tem mais essas classes. O card de Tendência não existe, e a spec 176 juntou Apetite e Rotação no card `painel-apetite-rotacao`, que some no *Só Sinais* como a Maré (decisão registrada no item 6 do *Comportamento esperado* da 176). Quem lê o CSS conclui o contrário.

O teste da spec 187 (`tests/test_classes_com_estilo.py`) cobre um lado: classe de template sem seletor. O outro lado, seletor sem classe em lugar nenhum, ninguém confere, e a lista cresce a cada card renomeado.

Medido na `main` de 22/11/2026 (`8d2f78f`), com o método da seção *Cálculos*:

- `app/static/tema.css` tem **180** nomes de classe em seletores (880 linhas).
- **20** não aparecem como palavra inteira em nenhum `.html`, `.js` ou `.py` de `app/`.
- **11** dessas são montadas em tempo de execução e ficam: `g-cor-1` a `g-cor-5` (`app/gauge.py:99,106`, `f"g-cor-{...}"`), `span-3`, `span-4`, `span-8` (`app/templates/componentes.html:4`, `span-{{ span }}`) e `novidade-correcao`, `novidade-melhoria`, `novidade-novidade` (`app/templates/novidades.html:19`, `novidade-{{ item.tipo }}`).
- **9** não são usadas por nada:

| Classe | Onde no `tema.css` (linhas) |
|---|---|
| `pilha` | 102 |
| `m-t-2` | 210 |
| `d-block` | 211 |
| `painel-estado-container` | 264–271 (com o comentário "Utilitários adicionados pelo Apetite a Risco", linha 263) |
| `painel-tendencia` | 292 (dentro de `:not()`), 313–329 |
| `painel-apetite` | 292 (dentro de `:not()`), 331–340 |
| `painel-rotacao` | 292 (dentro de `:not()`), 332–340 |
| `texto-num` | 513 |
| `tabela-scroll` | 569–572 |

O `<style>` de `app/templates/sistema.html:73` não tem seletor sem uso.

## Comportamento esperado
Nada muda na tela, em nenhuma página, largura ou modo. Muda o `tema.css` e o `make verify`:

1. **As regras mortas saem do `tema.css`.**
   - As regras inteiras de `.pilha`, `.m-t-2`, `.d-block`, `.painel-estado-container` (com o comentário da linha 263), `.texto-num` e `.tabela-scroll` saem.
   - No *Só Sinais*, saem as regras de `.painel-tendencia .duas`, `.painel-tendencia .sub`, `.painel-tendencia .kpi`, `.painel-tendencia .var`, `.painel-apetite .kpi-container`, `.painel-rotacao .duas`, `.painel-apetite .hero` e `.painel-rotacao .hero` (linhas 313–340).
   - O seletor da linha 292 fica `body.modo-so-sinais .visao-macro:not(.painel-ibovespa)`. Os três `:not()` que saem só baixam a especificidade, e isso não muda nada: no `tema.css` as únicas regras `display: ... !important` são todas `display: none !important` (linhas 293, 323, 333 e a `.escondido` da 511), então nenhuma outra regra disputa com ela.
   - As regras de `.painel-ibovespa` no *Só Sinais* (296–311) ficam: a classe existe (`index.html:47`).
2. **Teste novo, o avesso da 187:** um nome de classe que aparece em seletor do `tema.css` (ou de um `<style>` dos templates) e não aparece como palavra inteira em nenhum `.html`, `.js` ou `.py` de `app/` reprova, com a mensagem `seletor .<classe> em app/static/tema.css não é usado por nenhum template, JS ou Python: apague a regra ou registre em SEM_USO_CONHECIDOS com o motivo`.
3. **Exceção só com motivo:** as classes montadas em tempo de execução entram num dicionário `SEM_USO_CONHECIDOS` (nome → motivo) ou num prefixo declarado (`g-cor-`, `span-`, `novidade-`, cada um com o arquivo e a linha que o monta). Como na 187, exceção que deixa de valer (a classe passou a aparecer literalmente, ou o seletor saiu do CSS) também reprova até a linha sair.

O extrator de seletores reaproveita `seletores_do_css` e `estilos_dos_templates` de `tests/test_classes_com_estilo.py` (importar ou mover para um módulo comum de `tests/`), para os dois testes lerem o CSS do mesmo jeito.

## Fontes de dados
Nenhuma. Só os arquivos do repositório: `app/static/tema.css`, `app/templates/*.html`, `app/static/*.js`, `app/**/*.py`.

## Cálculos
Do arquivo ao veredito, com uma regra do próprio `tema.css`:

1. **Seletores.** Tira os comentários `/* ... */`, tira os blocos de declaração `{...}` mais internos (uma passada, como `seletores_do_css` da 187, para o `@media` não engolir o arquivo) e colhe `\.([a-zA-Z][\w-]*)` do que sobra. Da linha 292, `body.modo-so-sinais .visao-macro:not(.painel-ibovespa):not(.painel-tendencia):not(.painel-apetite):not(.painel-rotacao) {` rende `modo-so-sinais`, `visao-macro`, `painel-ibovespa`, `painel-tendencia`, `painel-apetite`, `painel-rotacao`.
2. **Uso.** Para cada nome, procura `(?<![\w-])<nome>(?![\w-])` no texto de todos os `.html`, `.js` e `.py` de `app/`, sem contar o próprio `tema.css`. Palavra inteira: `painel-apetite` **não** casa dentro de `painel-apetite-rotacao` (o `-` seguinte barra), e `num` não casa dentro de `texto-num`.
   - `modo-so-sinais`: aparece em `app/static/ui.js` → usado.
   - `painel-ibovespa`: aparece em `app/templates/index.html:47` → usado.
   - `painel-tendencia`, `painel-apetite`, `painel-rotacao`: zero ocorrências → sem uso.
3. **Exceções.** Nome que começa por um prefixo declarado (`g-cor-2`, `span-8`, `novidade-correcao`) ou que está em `SEM_USO_CONHECIDOS` não reprova.
4. **Veredito.** Sem uso − exceções = conjunto que reprova. Na `main` de 22/11: 20 − 11 = **9** (a tabela do *Problema*). Depois desta spec: **0**.

Conferência dos números: 180 nomes em seletor, 20 sem ocorrência literal, 11 dinâmicos, 9 mortos. Se a implementação medir diferente na `main` dela (classe nova ou removida desde 22/11), vale a medida dela, registrada no PR; o critério é o conjunto final vazio.

## Critérios de aceite
`tests/test_aceite_192.py`, com `devagent.aceite.exigir_spec_done("192")`:

- [ ] Com um CSS de fixture `.usada { } .morta { } .g-cor-3 { }` e um template `<div class="usada">`, o teste acusa `morta` e só ela (o prefixo `g-cor-` absolve `g-cor-3`).
- [ ] `.painel-apetite { }` com um template que só tem `painel-apetite-rotacao` acusa `painel-apetite` (palavra inteira, não prefixo).
- [ ] Um seletor dentro de `@media (max-width: 600px) { .morta { } }` é colhido e acusado.
- [ ] Uma classe citada só num `.py` (`f"texto-alta"` ou `"texto-alta"`) ou só num `.js` conta como usada.
- [ ] Exceção vencida em `SEM_USO_CONHECIDOS` (nome que passou a aparecer literalmente, ou cujo seletor saiu do CSS) reprova.
- [ ] No repositório real, o conjunto que reprova é vazio.
- [ ] Os seletores de `app/static/tema.css`, colhidos pelo passo 1 dos *Cálculos*, não têm nenhuma das nove classes da tabela do *Problema* (`painel-apetite-rotacao`, se aparecer, é outro nome); e o arquivo contém `body.modo-so-sinais .visao-macro:not(.painel-ibovespa) {`.
- [ ] `tests/test_classes_com_estilo.py` (spec 187) continua passando sem mudar `SEM_ESTILO_CONHECIDAS`: nenhuma classe de template perdeu o seletor.

## Invariantes de produção
- A página inicial, `/consultor`, `/sistema` e `/novidades` têm a mesma aparência de antes em 390 px e 1280 px, nos modos Todos e *Só Sinais* (comparar as capturas de `make telas` antes e depois; nenhuma diferença de pixel esperada).
- No modo *Só Sinais*, o card *Ibovespa hoje* continua visível com o valor em fonte grande, e o card *Apetite e rotação* continua escondido (como desde a spec 176).
- `/api/snapshot` não muda.

## Fora do escopo
- Decidir se o card *Apetite e rotação* deve voltar a aparecer no *Só Sinais*. A spec 019 o mostrava; a 176 escolheu escondê-lo. Se valer rever, é uma spec de experiência própria (ligada ao item "Só Sinais começa pela confluência" da Fila).
- Regras que têm classe viva mas propriedades que não mudam nada (sobrescritas por outra regra, valor igual ao padrão): pede análise de cascata, não um teste de texto.
- Os seletores do `<style>` de `sistema.html` além de entrar na leitura do teste (hoje sem morto), e mover esse `<style>` para o `tema.css`.
- As 25 classes de template sem estilo da 187: são o item "Teste que reprova classe sem estilo" da Fila.
