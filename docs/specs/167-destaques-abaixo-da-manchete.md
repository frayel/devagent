---
id: 167
titulo: Os destaques do dia logo abaixo da manchete
status: ready
esforco: P
gaveta: experiência
aceite: tests/test_aceite_167.py
revisada: 2026-11-17
origem: "O que se destaca hoje" acima da dobra
---

## Problema

Qual ação se destaca agora, sem trocar de aba?

É a segunda pergunta do produto (`PRODUTO.md`, seção 1), e a seção de experiência do `PRODUTO.md` diz que o investidor das 10h05, em 1440×900 e sem rolar, precisa saber "como o mercado está e o que se destaca hoje". Hoje a Visão Geral responde só à primeira metade: a manchete, o Ibovespa, a Maré e os cards macro. Nenhum nome de ação aparece acima da dobra (capturas de `make telas`, 15/11). A maior alta e a maior baixa estão na aba **Rankings & Destaques** (cards "Maiores altas" e "Maiores baixas", `app/templates/index.html:274` e `:309`) e a ação citada por mais radares está na aba **Alertas Intraday** (card "Em vários radares", spec 155, `index.html:386`). Os três dados já são calculados a cada carga da página; falta mostrá-los onde o olho chega primeiro.

## Comportamento esperado

Uma faixa de uma linha, `<nav class="destaques-agora" aria-label="Destaques agora">`, com a classe `span-12`, entre a manchete (`.manchete-container`) e a barra de abas (`#abas-navegacao`). Fica fora das abas: aparece em todas elas, como a manchete.

Até três itens, nesta ordem, cada um um link:

| Item | Texto | Link |
|---|---|---|
| Maior alta | `Maior alta` + ticker + variação formatada + `às HH:MM` | `?aba=rankings` |
| Maior baixa | `Maior baixa` + ticker + variação formatada + `às HH:MM` | `?aba=rankings` |
| Em mais radares | `Em mais radares` + ticker (+ ` e mais K`, se houver empate) + `· N radares` + `às HH:MM` | `?aba=alertas` |

- A variação usa a classe de cor de alta ou baixa já usada pela macro `variacao` de `componentes.html`.
- Cada link traz no `title` a fonte e o carimbo completo: `Fonte: <highlights.fonte> · <highlights.time>` para alta e baixa, `Fonte: os radares da aba Alertas · <confluencia.horario_texto>` para o terceiro.
- Na página histórica (`/?data=AAAA-MM-DD`), o link preserva a data: `?aba=rankings&data=AAAA-MM-DD`. O `ui.js` já abre a aba pedida em `?aba=` (spec 156).
- Com o carimbo `altas_baixas` desatualizado (`carimbos['altas_baixas'].desatualizado`, spec 141, o mesmo que já marca o card Dispersão), os itens de alta e baixa ganham o selo `desatualizado` (`<span class="selo alerta selo-desatualizado">`).
- Em 360 e 390 px a faixa quebra em até três linhas (um item por linha, `flex-wrap`) e nada vaza nem rola para o lado.

Regras de cada item:

1. **Maior alta:** o primeiro de `highlights.highs`, só se `change_percent > 0`. Se a lista estiver vazia ou o primeiro não for positivo (dia em que nenhuma ação da cesta subiu), o item mostra `Maior alta: nenhuma ação em alta`, sem link.
2. **Maior baixa:** o primeiro de `highlights.lows`, só se `change_percent < 0`. Senão, `Maior baixa: nenhuma ação em baixa`, sem link.
3. **Em mais radares:** o primeiro de `confluencia.acoes` (já ordenado por número de radares e depois por ticker, `app/services/radares.py:203`). `K` é quantas outras ações de `confluencia.acoes` têm o mesmo número de radares que a primeira. A contagem é sobre a lista que o card mostra (até `MAX_LINHAS_CONFLUENCIA = 10` linhas), não sobre os excedentes, para a faixa e o card nunca discordarem. Com `confluencia.acoes` vazio, o item **não aparece** (como o próprio card da spec 155, que some sem confluência).
4. Com `highlights` ausente (`None`), os itens 1 e 2 não aparecem. Sem nenhum item, a faixa não é renderizada.

As ações **em revisão** (variação acima do limite de outlier, `em_revisao`) nunca entram na faixa: o coletor já as separa de `highs` e `lows` (`app/collectors/highlights.py:235`), e a faixa só lê `highs` e `lows`.

## Fontes de dados

Nenhuma fonte nova. A faixa lê o que a rota `/` já monta:

- `highlights` (`app/services/highlights.py`, `get_highlights_view_data`), coleta do Yahoo/MT5 já existente, com o plano B dela (sem dado, `None`);
- `contexto["confluencia"]` (`radares.confluencia`, spec 155), calculado sobre os radares com coleta em dia;
- `carimbos['altas_baixas']` (spec 141).

Se qualquer um faltar, o item correspondente some (regra 4) e o resto da página segue igual.

## Cálculos

A montagem fica numa função pura, `app/services/destaques.py: faixa(highlights, confluencia, carimbo_altas_baixas, data_historica) -> list[dict]`, chamada na rota `/` depois de `confluencia` e posta no contexto como `destaques`. O template só percorre a lista.

Hora visível: `HH:MM` extraído dos carimbos que já existem. `highlights.time` tem o formato `dd/mm/aaaa HH:MM:SS BRT` (`highlights.py:66`) e `confluencia.horario_texto` tem `dd/mm/aaaa HH:MM BRT` (`carimbo.formatar`); a hora é a fatia `texto[11:16]` dos dois (posições 11 a 15, contando do zero): `"17/11/2026 10:30:12 BRT"[11:16] == "10:30"`. Não converta fuso de novo: os dois carimbos já estão em BRT. Carimbo vazio ou com menos de 16 caracteres: sem `às HH:MM`.

### Exemplo de ponta a ponta

Dado bruto, como o coletor grava (`highs_json` e `lows_json`, `change_percent` já em **percentual**, não fração):

```json
highs_json = [{"ticker": "VALE3", "price": 61.4, "change_percent": 3.2141}, {"ticker": "ITUB4", "price": 33.1, "change_percent": 1.02}]
lows_json  = [{"ticker": "MGLU3", "price": 9.87, "change_percent": -4.0493}, {"ticker": "B3SA3", "price": 12.3, "change_percent": -0.5}]
timestamp  = 2026-11-17 13:30:12 UTC
```

`format_asset` dá `change_percent_formatted = "+3,21%"` para VALE3 e `"-4,05%"` para MGLU3 (o hífen é o que `format_asset` já produz), e `highlights.time = "17/11/2026 10:30:12 BRT"`.

Confluência com três radares acesos: PETR4 em 3 radares, VALE3 em 3, ITUB4 em 2, carimbo mais antigo dos citados 10:30 BRT. `confluencia.acoes = [PETR4 (3), VALE3 (3), ITUB4 (2)]`; empatadas com a primeira: 1.

Faixa exibida:

```
Maior alta VALE3 +3,21% às 10:30 · Maior baixa MGLU3 -4,05% às 10:30 · Em mais radares PETR4 e mais 1 · 3 radares às 10:30
```

Dia sem nenhuma alta: `highs_json = [{"ticker": "B3SA3", "change_percent": -0.12}, ...]` → `Maior alta: nenhuma ação em alta`.

## Critérios de aceite

`tests/test_aceite_167.py`, com `exigir_spec_done("167")`, sem rede: a função pura direto, e a página pela fixture `radares` da spec 155 (`tests/test_aceite_155.py`) com `app.main.get_highlights_view_data` trocado por um dict fixo.

- [ ] Com o exemplo acima, `faixa(...)` devolve três itens com os textos `VALE3`, `+3,21%`, `MGLU3`, `-4,05%`, `PETR4 e mais 1`, `3 radares` e a hora `10:30`, nos links `?aba=rankings`, `?aba=rankings` e `?aba=alertas`.
- [ ] `GET /` contém `class="destaques-agora"` **antes** de `id="abas-navegacao"` e depois de `manchete-texto` no HTML.
- [ ] Primeiro de `highs` com `change_percent <= 0` → `nenhuma ação em alta`, sem `href`; primeiro de `lows` com `change_percent >= 0` → `nenhuma ação em baixa`, sem `href`.
- [ ] `confluencia.acoes` vazio → só os itens de alta e baixa; `highlights = None` e `confluencia.acoes` vazio → o HTML não contém `destaques-agora`.
- [ ] Sem empate (PETR4 com 3, VALE3 com 2) → o texto não contém `e mais`.
- [ ] `data_historica = "2026-11-13"` → os links são `?aba=rankings&data=2026-11-13` e `?aba=alertas&data=2026-11-13`.
- [ ] Carimbo `altas_baixas` com `desatualizado: True` → os itens de alta e baixa trazem `selo-desatualizado`; o de radares não.
- [ ] Ticker que está em `em_revisao` e não em `highs` não aparece na faixa.
- [ ] `make telas` sem `PROBLEMA:` novo em 360, 390, 768 e 1440 px.

## Invariantes de produção

- Em `/`, se a faixa existe, ela vem entre a manchete e as abas.
- O ticker da "Maior alta" é o primeiro da tabela "Maiores altas" da aba Rankings, com a mesma variação; o mesmo para a "Maior baixa" e "Maiores baixas".
- O ticker de "Em mais radares" é o primeiro do card "Em vários radares", com o mesmo número de radares.
- "Maior alta" nunca mostra variação negativa ou zero, e "Maior baixa" nunca mostra variação positiva ou zero.
- A hora da faixa é a do rodapé do card de origem.

## Fora do escopo

- Mudar os cards "Maiores altas", "Maiores baixas" e "Em vários radares": continuam onde estão.
- Abrir a aba sem recarregar a página (o link usa o `?aba=` da spec 156).
- Mostrar mais de uma ação por item, ou sparkline na faixa.
- Incluir a faixa em `/api/snapshot`: os três números já estão lá, nos painéis de origem.
- "Só Sinais começa pela confluência" (item da Fila do backlog) e o Raio-X de uma ação: specs próprias.
