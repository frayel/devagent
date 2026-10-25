---
id: 088
titulo: Seletor de pregão que funciona na página inicial e na API (conserto da 078)
status: done
revisada: 2026-10-24
esforco: M
gaveta: saúde técnica
aceite: tests/test_aceite_088.py
---

## Problema

O dono do produto pediu a escolha da data de referência para ver os pregões anteriores (ADR 008, spec 078). A 078 está `done`, mas em produção a página mostra só o último dia: não há seletor e `?data=` não faz nada. A leitura do código mostra por quê:

1. **Nome do parâmetro.** `index()`, `snapshot()` e `pagina_consultor()` em `app/main.py` declaram o parâmetro como `data_str`. O FastAPI lê `?data_str=`. O `<select name="data">` do `base.html`, e a spec 078 (`/api/snapshot?data=`), usam `data`. Todo valor escolhido é ignorado.
2. **Contexto incompleto.** O `TemplateResponse` de `index()` não passa `datas_disponiveis`, nem `is_historical`. O `base.html` só desenha o seletor dentro de `{% if datas_disponiveis %}`; sem a variável cai sempre no ramo "Fechamento de dd/mm/aaaa · dados congelados". A página de `/consultor` também não passa `data_referencia`, `estado_mercado` nem as variáveis do seletor.
3. **Troca de conteúdo quebrada.** O `<select>` usa `hx-get` com `hx-target="body"`. A resposta é a página inteira (`<html>…`), que o HTMX enfiaria dentro do `<body>`: documento aninhado, cabeçalho duplicado.
4. **Teste que não pega.** Os testes da 078 chamam funções, ou usam o nome interno do parâmetro, e nenhum faz o que o navegador faz: `GET /?data=2026-10-22` e procura o `<select>` no HTML.
5. **Histórico possivelmente curto.** O seletor lista `listar_datas("ibovespa", 30)`, ou seja, só os pregões com linha em `snapshots_paineis`. Se o congelamento (spec 077) não gravou o `final` em todos os pregões, o seletor teria um dia só mesmo depois de consertar os itens 1 a 3. Não há hoje nada na tela que diga quantos pregões estão guardados.

## Comportamento esperado

- O parâmetro canônico é `data` em `/`, `/consultor` e `/api/snapshot`, via `Query(alias="data")`. `data_str` continua aceito como apelido por compatibilidade.
- Toda página que estende `base.html` recebe do servidor, por uma função única, o mesmo conjunto de variáveis do seletor: `datas_disponiveis`, `data_referencia`, `is_historical`, `estado_mercado`, e o seletor aparece no cabeçalho.
- O seletor lista o pregão atual (ou o último fechamento) e os 5 anteriores com snapshot, rotulados "Hoje" ou "Último fechamento" e `dd/mm` com o dia da semana abreviado (`22/10 qui`). Com um único pregão guardado, o seletor aparece desabilitado com o texto "só há registro de dd/mm".
- Escolher uma data navega para `/?data=AAAA-MM-DD` (ou `/consultor?data=...`) por navegação normal do navegador, sem `hx-target="body"`: o `<select>` fica dentro de um `<form method="get">` com `onchange="this.form.submit()"` e um botão "Ver" dentro de `<noscript>`. A URL muda e pode ser compartilhada. (O `hx-boost` do corpo pode continuar acelerando a troca, desde que a página inteira seja o alvo.)
- Numa data passada valem todas as regras da 078: faixa "Você está vendo o fechamento de dd/mm/aaaa" com "Voltar para hoje", painel sem snapshot mostra "Sem registro neste pregão", nenhuma coleta é disparada.
- `/api/snapshot?data=AAAA-MM-DD` devolve o snapshot daquele pregão; data inválida, futura, sem pregão ou fora dos 5 anteriores devolve 404 em JSON. A página, nesses casos, volta ao pregão atual com um aviso.
- Item novo no grupo *Aplicação e banco* de `/sistema`: **Histórico de pregões**, com quantos pregões têm snapshot `final` ou `incompleto` e a data do mais antigo e do mais recente. *Atenção* se algum dia útil passado dentro da janela de 5 pregões não tem snapshot; *Problema* se nenhum pregão anterior tem.
- Se o item acima acusar falta de snapshots, a spec **não** termina: o desenvolvimento descobre por que o congelamento da 077 não gravou o dia (coletor fora da janela, falha de gravação, estado `parcial` nunca promovido a `final`), corrige e registra a causa no relatório.

## Fontes de dados

Nenhuma. Só leitura de `snapshots_paineis`.

## Critérios de aceite

- [ ] Com snapshots fixture de 7 pregões, `GET /` (cliente de teste, sem parâmetro) devolve HTML com `<select name="data">` e 6 opções, a primeira com o rótulo certo, sem o pregão mais antigo.
- [ ] `GET /?data=<pregão fixture>` devolve os números desse pregão, a opção correspondente `selected` e a faixa "Você está vendo o fechamento de".
- [ ] `GET /?data_str=<pregão fixture>` (apelido antigo) produz o mesmo resultado.
- [ ] `GET /consultor` e `GET /sistema` também trazem o seletor.
- [ ] O HTML do seletor não contém `hx-target="body"` e a troca de data é um `GET` de formulário.
- [ ] `GET /api/snapshot?data=<fixture>` devolve `data_referencia` igual ao parâmetro e `estado = final`; data inválida, futura ou fora da janela devolve 404 com JSON.
- [ ] Painel sem snapshot na data escolhida mostra "Sem registro neste pregão" e os demais aparecem.
- [ ] Abrir uma data passada não faz requisição externa (respx sem chamadas).
- [ ] Com um único pregão guardado, o seletor aparece desabilitado com o texto "só há registro de".
- [ ] `/api/sistema` traz o item "Histórico de pregões" com os níveis descritos.
- [ ] Teste de regressão: um teste que lê os nomes de parâmetro das rotas (`inspect` do app) e reprova qualquer rota com `data_str` sem o alias `data`.

## Invariantes de produção

- `GET /` no site publicado contém `name="data"` e pelo menos duas opções a partir do segundo pregão guardado.
- `/api/snapshot?data=<pregão anterior>` traz o Ibovespa igual ao fechamento oficial daquele dia, a no máximo 0,1% de uma fonte independente.
- O seletor nunca oferece um dia que não seja pregão no calendário da B3.

## Fora do escopo

- Comparar dois pregões lado a lado.
- Histórico intradiário e janela maior que 5 pregões.
- O que o Consultor mostra numa data passada (spec 089).
