---
id: 173
titulo: A Maré numa tela só dela, em /mare
status: ready
esforco: P
gaveta: capacidade nova
aceite: tests/test_aceite_173.py
origem: nova
revisada: 2026-11-17
---

## Problema
Pedido do dono do produto em 17/11/2026: "quero uma tela separada só com a Maré do mercado no centro da tela, para ver no computador ou no celular".

Quem quer acompanhar o humor do pregão num monitor lateral, num tablet apoiado na mesa ou no celular hoje precisa abrir o painel inteiro (`/`), rolar até a Maré e conviver com cabeçalho, menu, seletor de data e mais de vinte cards. A pergunta que a tela responde: **como está a Maré agora, num relance, sem mais nada?**

A tela não pode ter uma segunda cópia do card. Hoje o conteúdo da Maré vive inline em `app/templates/index.html`, a partir da linha 77 (`{% call painel("Maré do mercado", ...) %}`: selo de parcial, gauge, barras dos componentes, heatmap em treemap e sparkline), e o mesmo bloco ainda carrega os gauges pequenos de Apetite e Rotação (a partir de `{% if apetite_risco or rotacao_capital %}`, dentro do mesmo `call`). Copiar esse HTML para outra página faria as duas divergirem na primeira mudança, como a 144, a 147 e o treemap do PR #942 já mexeram no card três vezes.

## Comportamento esperado
1. **Rota nova `GET /mare`**, resposta `text/html` 200, com o template `app/templates/mare.html`, que estende `base.html`.
2. **Só o card.** A página mostra o card "Maré do mercado" com o que ele tem no painel geral: título, botão de método (`i`), selo de parcial, gauge, barras de Fluxo/Calma/Volume com peso, heatmap em treemap (já na `main`, `tests/test_heatmap_treemap.py`) e sparkline com a comparação. O rodapé do card (`Fonte ... · horário`, selo `desatualizado`) continua: a fonte e a data da coleta são protegidas pela seção *Transparência* do `PRODUTO.md`. Os gauges pequenos de Apetite e Rotação **não** aparecem: eles moram no mesmo `painel` por razão de layout da grade, não fazem parte da Maré.
3. **Sem cabeçalho e sem navegação.** Não aparecem o `<header>` (marca, menu, seletor de data, rótulo do pregão), o aviso de banco efêmero, nem o link de *Novidades* do rodapé.
4. **Rodapé com o aviso, e só ele:** `Conteúdo informativo gerado automaticamente. Não constitui recomendação de investimento.`, o mesmo `<p class="aviso-legal">` de `base.html`.
5. **No centro da tela.** O card fica centralizado na horizontal e na vertical da janela (`min-height: 100dvh` na página; o rodapé no pé). Largura máxima sugerida: 480 px; no celular, ocupa a largura com 16 px de margem de cada lado, sem rolagem horizontal. Cores e espaçamentos só pelos tokens de `app/static/tema.css` (`docs/DESIGN.md`).
6. **Um card, uma fonte.** O conteúdo da Maré sai de `index.html` para **uma** macro em `app/templates/componentes.html` (sugestão: `card_mare(mare, carimbo, historico=False)`), que monta o `painel` com título, método, fonte, horário e classe `painel-mare`, e o conteúdo da Maré. `index.html` e `mare.html` chamam a mesma macro. No painel geral, os gauges de Apetite e Rotação continuam dentro do mesmo card de hoje: a macro aceita um bloco opcional por `caller` (ou parâmetro equivalente), que `index.html` preenche e `mare.html` não. O texto do método fica num lugar só (na macro ou numa constante de `app/services/mare.py`).
   - **O que a macro recebe.** Hoje o bloco lê três nomes do contexto de `index.html`: `mare` (a view), `c_mare` (o carimbo, `{rodape, desatualizado}`, definido no topo do `index.html` como `_cb.get('mare') or {}`) e `is_historical` (escolhe entre `estado('sem_registro')` e `estado('indisponivel')`). A macro recebe os três por parâmetro (`carimbo` pode chegar `None`: trate como `{}`), porque macro importada não enxerga o contexto da página. `index.html` chama `card_mare(mare, c_mare, is_historical)`; `mare.html`, `card_mare(mare, carimbo)`.
   - **O `caller` dentro de outro `call`.** Dentro do corpo de `{% call painel(...) %}`, o nome `caller` é o do bloco do `painel`, não o da `card_mare`. Capture o bloco opcional antes, no topo da macro: `{% set extra = caller() if caller is defined else '' %}`, e escreva `{{ extra }}` dentro do `call painel`, no mesmo lugar onde hoje ficam os gauges pequenos. Conferido no Jinja do projeto: `card_mare(...)` sem `call` não quebra, e `{% call card_mare(...) %}...{% endcall %}` põe o conteúdo dentro do painel.
7. **Mesmos dados, mesma função.** A rota usa `mare_servico.get_mare_view()` (`app/services/mare.py:419`) e o carimbo `_carimbos_criticos(agora).get("mare")` (`app/main.py:296`; a chave só existe quando há leitura gravada), as mesmas chamadas do painel geral. Nenhum cálculo novo.
8. **Atualiza sozinha.** Como a tela foi feita para ficar aberta, ela se recarrega a cada 15 minutos (`<meta http-equiv="refresh" content="900">`, o ritmo da coleta no pregão, spec 163). Só em `/mare`.
9. **Título da aba:** `Maré do mercado · Painel B3`.
10. **Sem dado:** sem leitura gravada, a página responde 200, mostra o card com o estado `indisponivel` (macro `estado`, como no painel geral) e o aviso legal.

### Como deixar o cabeçalho de fora sem um segundo `base.html`
`base.html` ganha blocos Jinja em volta do que a tela solo não quer (nomes sugeridos): `{% block cabecalho %}` em volta do aviso de banco efêmero e do `<header>`, `{% block rodape_extra %}` em volta do link de *Novidades*, e `{% block classe_main %}grade{% endblock %}` no `class` do `<main>`. `mare.html` sobrescreve os dois primeiros vazios e troca a classe do `<main>` (sugestão: `tela-solo`). As outras páginas não mudam: o HTML de `/`, `/consultor`, `/sistema` e `/novidades` sai idêntico ao de antes.

### Scripts
`/mare` não desenha Plotly: não preenche o bloco `scripts_pagina` da spec 172. `ui.js` continua (é ele que dimensiona o heatmap pelos `data-peso`). A 172 já está na `main` (#944): o bloco `scripts_pagina` existe em `base.html`, e `/mare` simplesmente não o preenche.

## Fontes de dados
Nenhuma nova. O snapshot `mare` gravado por `app/collectors/mare.py`. Plano B: o mesmo do painel geral (item 10).

## Cálculos
Nenhum.

## Critérios de aceite
- [ ] `tests/test_aceite_173.py`, com `exigir_spec_done("173")`, sem internet, com a leitura da Maré mockada como em `tests/test_mare.py` (e os fixtures de rota de `tests/test_aceite_088.py`, porque um `TestClient(app)` cru com o `lifespan` não termina em 120 s neste ambiente, medido na spec 172):
  - **rota:** `GET /mare` responde 200 e `text/html`;
  - **só o card:** o HTML contém exatamente um elemento com a classe `painel-mare`, o gauge da Maré (`aria-label` "Maré do mercado, de 0 a 100") e as três barras `mare-componentes`; não contém `<header`, `class="menu"`, `seletor-data`, `rodape-novidades` nem `aviso-banco-efemero`; não contém os gauges de Apetite (`SMLL − IBOV`) nem de Rotação;
  - **aviso:** contém `Conteúdo informativo gerado automaticamente. Não constitui recomendação de investimento.` exatamente uma vez;
  - **transparência:** contém o rodapé do card `Fonte <fonte> · <horário>` com a fonte e o horário do mock;
  - **refresh e título:** contém `<meta http-equiv="refresh" content="900">` e `<title>Maré do mercado · Painel B3</title>`; o HTML de `GET /` não contém `http-equiv="refresh"`;
  - **sem dado:** com `get_latest_mare_data` devolvendo `None`, `GET /mare` responde 200 com o estado indisponível e o aviso legal;
  - **um card, uma fonte:** em todo `app/templates/`, a string `mare-componentes` aparece em um único arquivo (o de componentes), e tanto `index.html` quanto `mare.html` chamam a macro da Maré (`grep` pelo nome da macro);
  - **painel geral intacto:** o HTML de `GET /`, com o mesmo mock, continua com o card da Maré e, dentro do mesmo `painel-mare`, os gauges de Apetite e Rotação quando os mocks os trazem.
- [ ] Teste de navegador no padrão de `tests/test_aceite_146.py` (Chromium do ambiente, sem rede externa): em 390×844 e em 1440×900, a diferença entre a margem esquerda e a direita do card é de no máximo 2 px, o centro vertical do card fica a no máximo 10% da altura da janela do centro da área acima do rodapé (ou o card começa no topo, se for mais alto que a janela) e `document.documentElement.scrollWidth <= window.innerWidth`.
- [ ] Os testes atuais do card (`tests/test_mare.py`, `tests/test_aceite_144.py`, `tests/test_aceite_146.py`, `tests/test_aceite_147.py`, `tests/test_aceite_169.py` e `tests/test_heatmap_treemap.py`) continuam verdes sem mudar asserções: a extração para macro não muda o HTML do card no painel geral.

## Invariantes de produção
- `GET https://<site>/mare` responde 200 e o HTML não contém `<header`.
- O número do gauge em `/mare` é igual a `paineis.mare.valor` do `/api/snapshot` do mesmo momento (a página e o snapshot leem o mesmo registro).
- O HTML de `/mare` contém o aviso legal exatamente uma vez e o rodapé `Fonte ... · ...` do card.

## Fora do escopo
- Escolher o nível de tendência (Marolas, Ondas, Maré): spec 174.
- Gráfico no tempo do nível (horas, dias, meses): spec 175.
- Ver uma data passada em `/mare` (`?data=`): a tela mostra sempre a leitura mais recente.
- Modo quiosque, tela cheia por botão, PWA ou ícone para a tela inicial do celular.
- Telas solo de outros cards. Se a tela da Maré provar uso, a generalização (`/card/<nome>`) é outra spec.

## Revisão
Revisada em 17/11/2026 contra a `main` em `9ff280f`.
- **Já no código:** não. Não há rota `/mare` em `app/main.py`, nem `mare.html`, nem macro da Maré em `componentes.html`; `base.html` ainda não tem os blocos `cabecalho`, `rodape_extra` e `classe_main`.
- **Duplicata:** não. A 174 e a 175 constroem sobre esta (o seletor vive na macro daqui) e já a citam; nenhuma outra spec cria a tela.
- **Tamanho:** 6 arquivos de código (`app/main.py`, `app/templates/base.html`, `app/templates/index.html`, `app/templates/componentes.html`, `app/templates/mare.html` novo, `app/static/tema.css`) e 1 de teste novo. `grep -rl "mare-componentes\|painel-mare" app tests` dá 3 arquivos (`tema.css`, `index.html`, `tests/test_aceite_146.py`); o teste só procura a classe e continua valendo. Cabe numa sessão.
- **Ajustes no texto:** o número de linha do `index.html` (era 72-112, hoje 77), a 172 e o treemap deixaram de ser condicionais (os dois já estão na `main`), o carimbo passa a `.get("mare")`, e o item 6 ganhou o que a macro recebe (`mare`, carimbo, `historico`) e o cuidado com `caller` aninhado em `call painel`.
- **Cálculos:** nenhum, então não há exemplo numérico a exigir. A invariante do gauge confere `paineis.mare.valor`, que `mare_servico.snapshot` já publica.

