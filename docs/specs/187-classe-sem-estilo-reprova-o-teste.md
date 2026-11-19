---
id: 187
titulo: Classe nova sem estilo reprova o teste
status: ready
esforco: P
gaveta: saúde técnica
aceite: tests/test_aceite_187.py
origem: Teste que reprova classe sem estilo
---

## Problema
Quando um template ganha uma classe, ela muda alguma coisa na tela? Hoje ninguém confere. Um nome escrito errado, ou copiado de um tema antigo, passa no `make verify` e o elemento sai sem a cor, o alinhamento ou o espaço que o autor pensou que estava dando. A `destaque` do Clima Global foi um caso (spec 160).

Medido na `main` de 19/11/2026 (`e76e1c1`), com o método da seção *Cálculos*:

- Os 8 templates de `app/templates/` usam **187 classes estáticas** distintas.
- **48** não têm seletor em `app/static/tema.css` nem no `<style>` de `app/templates/sistema.html`. Dessas, **5** são lidas pelo JavaScript (`alertas`, `destaque`, `fora`, `mare-anuncio`, `voltar-hoje` aparecem em `app/static/ui.js` ou `app/static/graficos.js`), e **43** não fazem nada em lugar nenhum do navegador.
- Exemplo visível: os painéis *Falso Rompimento* e *Divergência Volume/Preço* (`app/templates/index.html:700–760`) montam a tabela à mão com `ranking`, `numero`, `positivo`, `negativo` e `dado-indisponivel`, e nenhuma dessas classes tem estilo. Os números saem sem cor e alinhados à esquerda, enquanto os outros radares usam `tabela_ativos` (`num`, `texto-alta`, `texto-baixa`) e `vazio`. E a coluna de volume leva `positivo` fixo mesmo quando o valor tem ▼: se alguém der estilo a `positivo` sem olhar, a tela passa a pintar de verde uma queda.

Esta spec é a primeira fatia: impedir que a lista cresça. Zerar as 43 fica para depois (ver *Fora do escopo*).

## Comportamento esperado
Nada muda no site. Muda o `make verify`:

1. Um teste novo, `tests/test_classes_com_estilo.py` (que roda sempre, sem `exigir_spec_done`), lê os templates, o CSS e o JS e reprova quando um template usa uma classe estática que não tem seletor no CSS, não aparece no JS e não está na lista de exceções.
2. A lista de exceções fica no próprio arquivo de teste, `SEM_ESTILO_CONHECIDAS`, um `dict` de classe para motivo, com as 43 classes da tabela abaixo e o motivo `"dívida medida na spec 187"`. Classe que é gancho de teste ou de leitura (por exemplo `estado`, citada em `tests/` como seletor) pode ganhar um motivo próprio no lugar desse, sem sair da lista.
3. A lista só encolhe. O teste também reprova quando uma classe de `SEM_ESTILO_CONHECIDAS` não aparece mais em nenhum template, ou passou a ter seletor no CSS ou a aparecer no JS: quem corrigiu a classe tira a linha no mesmo PR.
4. A mensagem de falha diz, para cada classe, o template onde ela está e o que fazer: "dê um seletor em `app/static/tema.css`, use uma classe que já existe, ou, se for gancho de JS ou de teste, registre em `SEM_ESTILO_CONHECIDAS` com o motivo".

As 43 classes de hoje (template onde aparecem):

| Template | Classes |
|---|---|
| `index.html` | `aba-densidade`, `alerta-vazio`, `aviso-vazio`, `conteudo-centralizado`, `dado-indisponivel`, `dado-vazio`, `destaque-texto`, `dir`, `direita`, `em-revisao`, `espaco-topo-curto`, `esq`, `estado`, `icone`, `item-revisao`, `kpi-group`, `legenda`, `manchete-container`, `negativo`, `normal`, `numero`, `positivo`, `radares-sem-leitura`, `ranking`, `rodape-ausentes`, `selo-revisao`, `tabela-compacta`, `texto-2`, `vazia`, `visao-micro` |
| `index.html` e `componentes.html` | `selo-desatualizado` |
| `componentes.html` | `mare-sem-curva` |
| `base.html` | `aviso-dados`, `aviso-legal`, `espacador-direita` |
| `consultor.html` | `badge`, `badge-negativo`, `badge-positivo`, `lista-opinioes`, `rodape-painel`, `status-neutro`, `tabela-sem-sinal` |
| `sistema.html` | `checagem-corpo` |

Se a `main` mudar entre a escrita desta spec e a entrega, a lista é a que o método der na `main` do PR de entrega, e o relatório registra a diferença.

## Fontes de dados
Nenhuma fonte externa. O teste lê arquivos do repositório: `app/templates/*.html`, `app/static/*.css` e `app/static/*.js`.

## Cálculos
**Classes dos templates.** Para cada atributo `class="..."` de cada `app/templates/*.html`:

1. troque cada trecho `{{ ... }}` por um caractere marcador sem espaço (por exemplo `\x00`), para que o pedaço de nome colado nele (`g-faixa-{{ n }}`) não conte;
2. apague cada trecho `{% ... %}`, mantendo o texto entre eles (as classes condicionais de `{% if %}badge-positivo{% else %}badge-negativo{% endif %}` contam);
3. separe por espaço e fique só com os nomes que casam `^[a-z][a-z0-9-]*$` (sem `_`: isso descarta os pedaços de expressão Jinja que caem dentro de um `class="` montado por concatenação, como o `clima_class` de `index.html:93`).

**Classes com estilo.** Junte o texto de `app/static/*.css` e de todo bloco `<style>...</style>` dos templates. Apague **uma única vez** os blocos de declaração `{...}` que não contêm outra chave (`re.sub(r"\{[^{}]*\}", "", texto)`): os números das declarações, como `0.5rem`, somem, e os seletores de dentro de um `@media { .x { } }` continuam visíveis. Não repita a troca até estabilizar: a segunda passada apaga o `@media` inteiro com os seletores dentro (na `main` medida, `.pregao .form-inline`, `app/static/tema.css:123`, deixaria de contar e `form-inline` viraria falso positivo). Toda ocorrência de `\.([a-zA-Z][\w-]*)` no que sobra é um seletor de classe.

**Classes do JS.** Uma classe aparece no JS se o nome, delimitado por algo que não é letra, dígito, `_` nem `-`, ocorre em algum `app/static/*.js`.

**Falha.** `sem_estilo = classes_dos_templates − seletores − citadas_no_js`. Reprova se `sem_estilo − SEM_ESTILO_CONHECIDAS` não for vazio (classe nova), ou se `SEM_ESTILO_CONHECIDAS − sem_estilo` não for vazio (exceção vencida).

Exemplo de ponta a ponta:

- template: `<span class="badge {% if ok %}badge-positivo{% else %}badge-negativo{% endif %} g-faixa-{{ n }}">`
- passo 1: `badge {% if ok %}badge-positivo{% else %}badge-negativo{% endif %} g-faixa-\x00`
- passo 2: `badge badge-positivo badge-negativo g-faixa-\x00`
- passo 3: `{"badge", "badge-positivo", "badge-negativo"}` (`g-faixa-\x00` não casa)
- CSS: `.badge-confianca { color: red } @media (max-width: 600px) { .badge-positivo { margin: 0.5rem } }` → seletores `{"badge-confianca", "badge-positivo"}` (`badge` não, porque `.badge-confianca` não é `.badge` seguido de fim de nome)
- JS vazio, `SEM_ESTILO_CONHECIDAS = {"badge": "..."}`
- `sem_estilo = {"badge", "badge-negativo"}` → reprova por `badge-negativo` (classe nova). Com `badge-negativo` na lista, passa. Se depois alguém escrever `.badge { }` no CSS, reprova por `badge` (exceção vencida) até a linha sair da lista.

Na `main` medida: 187 classes − 139 com seletor − 5 do JS = 43, igual ao tamanho da lista. O teste passa no dia da entrega.

## Critérios de aceite
`tests/test_aceite_187.py`, com `exigir_spec_done("187")`, sem internet e sem servidor, chamando as funções puras que o teste da regra expõe (por exemplo `classes_dos_templates(textos)`, `seletores_do_css(texto)`, `citadas_no_js(nomes, texto)`), com textos montados no próprio teste:

- [ ] O exemplo da seção *Cálculos* dá exatamente os conjuntos mostrados em cada passo, e o resultado final é `{"badge", "badge-negativo"}`.
- [ ] Uma classe só citada dentro de `@media` conta como estilizada, inclusive quando o `@media` tem mais de uma regra; `0.5rem` e `1.25em` nas declarações não viram seletor.
- [ ] `voltar-hoje` sem seletor, mas com `document.querySelector(".voltar-hoje")` no JS, não reprova; `voltar` no mesmo JS não salva uma classe `voltar-ontem`.
- [ ] Uma classe nova sem estilo fora da lista reprova, e a mensagem cita o nome da classe e o template.
- [ ] Uma classe da lista que sumiu dos templates, ou ganhou seletor, reprova como exceção vencida, e a mensagem cita o nome.
- [ ] `tests/test_classes_com_estilo.py`, rodado contra os arquivos reais do repositório, passa; e `SEM_ESTILO_CONHECIDAS` tem no máximo 43 entradas (a lista não nasce maior que a medida).
- [ ] `make verify` passa.

## Invariantes de produção
- Nenhuma página muda: `/`, `/consultor`, `/mare`, `/novidades` e `/sistema` respondem 200 com o mesmo HTML de antes do merge (a entrega não toca em `app/`).
- `/api/snapshot` responde 200 com as mesmas chaves.

## Fora do escopo
- Corrigir as 43 classes (dar estilo, trocar por uma que já existe ou apagar). Cada correção muda o visual e cabe numa spec de *Experiência* ou num PR `fix:`; o resto da visão segue no item *Teste que reprova classe sem estilo* da Fila do `docs/BACKLOG.md`. Os primeiros candidatos são os painéis *Falso Rompimento* e *Divergência Volume/Preço*, que deviam usar `tabela_ativos` e `vazio` como os outros radares, com a cor da célula pelo sinal do valor e não fixa por coluna.
- Classes montadas em tempo de execução (`g-cor-{{ n }}`, `span-{{ largura }}`, `class="{{ x }}"`) e classes postas pelo JS (`classList.add`): o teste não as enxerga, e conferir as dinâmicas pede renderizar as páginas.
- O caminho inverso (seletor no CSS que nenhum template ou JS usa, CSS morto). É uma poda própria.
- Estilos inline (`style="..."`).
