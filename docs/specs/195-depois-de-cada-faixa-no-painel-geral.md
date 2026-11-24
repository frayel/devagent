---
id: 195
titulo: Depois de cada faixa sai de /mare e vai para o painel geral
status: ready
esforco: P
gaveta: experiência
aceite: tests/test_aceite_195.py
origem: nova
revisada: 2026-11-24
---

## Problema
Pedido do dono do produto em 23/11/2026: a tela `/mare` mostra o quadro *Depois de cada faixa*, mas ela foi pedida para ter só o card *Maré do mercado* (spec 173). O quadro deve aparecer no painel geral.

A spec 183 pôs o bloco na tela solo (`app/templates/mare.html:13-44`, montado em `pagina_mare`, `app/main.py:528-536`) e deixou a página inicial de fora de propósito, para não crescer a primeira dobra da 176 (`docs/specs/183-o-que-veio-depois-de-cada-faixa-da-mare.md`, item 5). Isso contraria a 173: `/mare` é para ficar aberta num monitor ou no celular com um card só. E quem lê a Maré no painel geral não vê o que costuma vir depois da faixa de hoje.

A pergunta que a spec responde: **no painel geral, o que o Ibovespa fez depois das vezes em que a Maré esteve nesta faixa?**

## Comportamento esperado
1. **`/mare` volta a ter só o card.** O bloco *Depois de cada faixa* sai de `mare.html`, e `pagina_mare` para de ler o `mare_historico` e de montar `memoria` para ele. O resto da tela fica como está: card, seletor, aviso legal, refresh de 15 minutos.
2. **O quadro entra na Visão Geral do painel geral (`/`)**, como card próprio, com o mesmo conteúdo de hoje em `/mare`: a frase da faixa de hoje, a tabela das cinco faixas com a linha de hoje marcada, o método recolhível com fonte, data e ressalvas, e a mensagem *Memória em formação* quando `memoria` é `null`. Nenhuma mudança de texto, conta ou formato.
3. **Posição.** Logo depois de *Motores do Índice* no `index.html`, com as classes `painel-memoria-mare visao-macro visao-geral`. A grade da Visão Geral fica assim a partir de 768 px:
   - linha 1: *Ibovespa hoje* (8) e *Maré do mercado* (4, ocupando duas linhas, spec 176);
   - linha 2: *Clima Global* (4) e *Apetite e rotação* (4);
   - linha 3: *Motores do Índice*, que passa de `span-12` para `span-8`, e *Depois de cada faixa* (`span-4`), que fica na mesma coluna da Maré, logo abaixo dela;
   - depois, *Fator Peso Pesado* e *Concentração Setorial*, como hoje.
   
   Quando *Motores do Índice* não aparece (classe `escondido`), *Depois de cada faixa* ocupa `span-12`, no mesmo padrão do `clima_span` (`index.html:82`), para não deixar célula vazia (spec 149). Motores volta a `span-12` quando o quadro não existe.
4. **Uma fonte só.** O HTML do quadro sai de `mare.html` para uma macro em `app/templates/componentes.html` (sugestão: `card_mare_memoria(memoria, span)`), chamada só por `index.html`. A montagem dos dados continua em `mare_servico.memoria` e `mare_servico.view_memoria`, chamadas pela rota `/` (`index`, `app/main.py`, que já roda dentro de `lendo_pregao` e de `req_snapshot_cache_ctx`) com `app.banco.ler_snapshot("mare_historico")` e a `faixa` da variável `mare` que a rota já monta com `mare_servico.get_mare_view()` (`app/main.py:2158`), como `pagina_mare` faz hoje. Não precisa de consulta nova nem de passar `data_ref`: dentro do `lendo_pregao`, `ler_snapshot` já lê o pregão escolhido.
5. **Fora do seletor.** O quadro fica fora do card da Maré e do fragmento `/mare/card`: trocar Marolas, Ondas ou Maré não o troca nem o recarrega (regra da 183, que continua).
6. **Data passada.** Com `?data=`, o quadro usa o `mare_historico` daquele pregão e a faixa da leitura da Maré daquele pregão (os dois vêm do `lendo_pregao`, item 4). Os três casos:
   - sem `?data=` e sem `mare_historico`, ou com snapshot sem nenhum caso: *Memória em formação*, como na 183 (`view_memoria(None, ...)`);
   - com `?data=` e **sem** snapshot `mare_historico` naquele pregão: o card mostra `estado('sem_registro')` no lugar da frase e da tabela, com o título *Depois de cada faixa* e as mesmas classes (a grade não muda);
   - com `?data=` e snapshot sem nenhum caso: *Memória em formação*.
7. **Só Sinais.** Some no modo *Só Sinais* como os outros cards `visao-macro`.
8. **`/api/snapshot` não muda.** A chave `paineis.mare.memoria` da 183 continua igual.

## Fontes de dados
Nenhuma nova: o snapshot `mare_historico` da 174a, como na 183. Plano B: o da 183 (snapshot anterior, ou *Memória em formação*).

## Cálculos
Nenhum.

## Critérios de aceite
- [ ] `tests/test_aceite_195.py`, com `exigir_spec_done("195")`, sem internet, com os fixtures de `tests/test_aceite_183.py` (`calendario_fixo` e o `mare_historico` sintético):
  - **`/mare` só com o card:** o HTML de `GET /mare` não contém `Depois de cada faixa` nem `mare-memoria`, e tem exatamente um elemento `section.painel`;
  - **painel geral com o quadro:** o HTML de `GET /` contém `Depois de cada faixa`, a frase da faixa de hoje com os números do snapshot e a marca `hoje` na linha certa, dentro de um elemento com as classes `painel-memoria-mare`, `visao-macro` e `visao-geral`;
  - **posição:** no HTML de `/`, o card do quadro vem logo depois do de *Motores do Índice*; com Motores visível, Motores tem `span-8` e o quadro `span-4`; com Motores `escondido`, o quadro tem `span-12`;
  - **em formação:** sem `mare_historico`, `/` mostra `Memória em formação` no quadro;
  - **fora do seletor:** `GET /mare/card?nivel=ondas` não contém `Depois de cada faixa`;
  - **data passada:** com `?data=` de um pregão sem `mare_historico`, o quadro mostra o estado sem registro e o resto da página responde 200;
  - **uma fonte só:** em `app/templates/`, `mare-memoria-tabela` aparece só em `componentes.html`.
- [ ] `tests/test_aceite_183.py`: `test_snapshot_e_tela_com_historico`, `test_bloco_na_tela_em_qualquer_nivel` e `test_tabela_nao_rola_para_o_lado` passam a pedir `/` (com `?nivel=`, no segundo) em vez de `/mare`; `test_fragmento_e_pagina_inicial_sem_o_bloco` passa a conferir que o fragmento e `/mare` não têm o bloco. As asserções de conteúdo (frase, tabela, método, *poucos casos*, largura) não mudam.
- [ ] A classe do card não começa com `painel-mare`: `tests/test_aceite_173.py` acha o card da Maré com `\bpainel-mare\b` e conta `painel-mare` no HTML, e `painel-mare-memoria` casaria com os dois. Por isso `painel-memoria-mare`.
- [ ] `tests/test_aceite_173.py` e `tests/test_aceite_176.py` continuam verdes sem mudar asserções: a primeira dobra não cresce (o quadro fica na linha 3).
- [ ] `tests/test_aceite_149.py`: a única mudança é acrescentar `"Depois de cada faixa",  # spec 195` ao conjunto `TITULOS_PERMITIDOS`, como a 176 fez com *Apetite e rotação*. Sem isso, `test_so_titulos_existentes_na_visao_geral` reprova: o fixture da 149 não grava `mare_historico`, então o quadro aparece em *Memória em formação*, visível na Visão Geral. `test_12_colunas_fecham` e `test_6_colunas_do_fator_em_diante` continuam sem mudança e verdes: a linha 3 fecha em 8 + 4 (a Maré ocupa linhas 1 e 2) e a grade não ganha célula vazia.

## Invariantes de produção
- O HTML publicado de `/mare` não contém `Depois de cada faixa`.
- O HTML publicado de `/` contém `Depois de cada faixa` na Visão Geral, com o mesmo número de casos da faixa de hoje que `paineis.mare.memoria` traz no `/api/snapshot`.

## Fora do escopo
- Mudar a conta, o horizonte de 5 pregões, os textos ou o método da 183.
- Mostrar o quadro em outra aba além da Visão Geral.
- Mudar a ordem ou o tamanho de *Fator Peso Pesado* e *Concentração Setorial*.
- A célula vazia de 4 colunas ao lado de *Motores do Índice* no modo *Só Sinais*: o quadro some (item 7) e o Motores, que não é `visao-macro`, fica em `span-8`. É o mesmo comportamento que *Clima Global* já tem ao lado de *Apetite e rotação* nesse modo; a spec 149 trata da Visão Geral.
- Apagar as regras `.mare-memoria-*` de `app/static/tema.css`: continuam valendo para a tabela no painel geral.

## Revisão
Revisada em 24/11/2026. Conferido na `main`: o bloco ainda está em `mare.html` e não existe em `index.html` nem em `componentes.html`; nenhuma outra spec `ready` ou `draft` move o quadro (a 174 é `draft` e trata dos níveis). Tamanho: 4 arquivos de código (`app/main.py`, `app/templates/mare.html`, `index.html`, `componentes.html`) e 3 de teste (`test_aceite_183.py`, `test_aceite_149.py`, o novo `test_aceite_195.py`). Ajustes: (1) o aceite dizia que a `test_aceite_149.py` passaria sem mudança, mas o conjunto `TITULOS_PERMITIDOS` dela reprova qualquer título novo na Visão Geral; agora o aceite manda acrescentar o título; (2) o item 6 separava mal *Memória em formação* de *sem registro* numa data passada; agora lista os três casos; (3) o item 4 aponta a `mare` que a rota `/` já monta e o `lendo_pregao` que ela já usa, em vez de `ler_snapshot(..., data_ref)`; (4) *Fora do escopo* registra a célula vazia no modo *Só Sinais* e as regras de CSS que ficam.
