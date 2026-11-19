---
id: 185
titulo: O radar sem alerta diz há quantos pregões acendeu pela última vez
status: done
revisada: 2026-11-19
esforco: P
gaveta: experiência
aceite: tests/test_aceite_185.py
origem: O radar vazio diz há quanto tempo e por quê
---

## Problema
O usuário perguntou: "esse radar está vazio hoje porque é normal para ele, ou porque não acende há semanas?"

Na `main` de 18/11/2026, a seção "Sem alertas" da aba Alertas (spec 150, `app/templates/index.html`, `<ul class="radares-sem-alerta">`) lista só os nomes dos radares com lista vazia. Um radar que acendeu ontem e um que não acende há um mês aparecem iguais. O sistema já guarda o dado que separa os dois: desde a spec 166, cada rodada de coleta durante o pregão soma, no snapshot diário `instrumentacao`, `radares_pregao` (rodadas contadas) e `escondidos_pregao[chave]` (rodadas em que o radar estava escondido, isto é, sem alerta). Num pregão em que `escondidos_pregao[chave] < radares_pregao`, o card do radar apareceu em pelo menos uma coleta. Ninguém lê esse número fora do critério de poda de `/sistema`.

## Comportamento esperado
Escopo: só os nomes da lista `radares.sem_alertas` da seção "Sem alertas" (estado `SEM_ALERTAS` de `app/services/radares.py`). Os itens desatualizado e indisponível (`radares.outros`) não mudam.

- Cada nome da lista ganha, depois dele, um `<span class="ultimo-alerta">` com uma destas frases:
  - **acendeu no pregão corrente, mas está vazio agora:** `· teve alerta mais cedo neste pregão`;
  - **acendeu num pregão anterior da janela:** `· último alerta há N pregão(ões) (DD/MM)`, com `N` em pregões do calendário (`1 pregão`, `2 pregões`) e a data do pregão em que acendeu;
  - **não acendeu em nenhum pregão com registro na janela:** `· sem alerta nos M pregões registrados` (`1 pregão registrado` no singular), com `M` o número de pregões da janela que têm registro;
  - **nenhum pregão da janela tem registro** (ou a leitura falhou): o nome aparece sozinho, como hoje.
- Em data histórica (`?data=...`, `is_historical`), nenhum nome ganha frase: a lista fica como hoje.
- A frase não muda a ordem da lista, não esconde nem mostra card e não muda o botão "Mostrar vazios".
- Em 390 px, a lista continua numa coluna, sem rolagem horizontal, e a frase quebra junto com o nome (o `overflow-wrap: anywhere` de `.radares-sem-alerta li` já cobre).

### Exemplo de ponta a ponta
`agora` = 19/11/2026, 11:00 BRT (14:00 UTC), pregão aberto. Janela: os 20 pregões que terminam em 19/11 (19/11, 18/11, 17/11, 16/11, 13/11, ..., 22/10, pelo `app.calendario`). Snapshots `instrumentacao`:

| Data | `radares_pregao` | `escondidos_pregao` |
|---|---|---|
| 19/11 | 8 | `variacao_subita: 8`, `exaustao_alta: 8`, `faca_caindo: 5` |
| 18/11 | 40 | `variacao_subita: 37`, `exaustao_alta: 40`, `faca_caindo: 40` |
| 17/11 | 30 | `variacao_subita: 30`, `exaustao_alta: 30`, `faca_caindo: 30` |
| 16/11 e anteriores | sem `radares_pregao` | — |

Os três radares estão com lista vazia agora (estado `SEM_ALERTAS`). A seção mostra:

- `Variação Súbita · último alerta há 1 pregão (18/11)` (37 < 40 em 18/11; em 19/11, 8 = 8);
- `Exaustão de Alta · sem alerta nos 3 pregões registrados` (escondido em todas as rodadas de 19, 18 e 17/11);
- `Radar de Faca Caindo · teve alerta mais cedo neste pregão` (5 < 8 em 19/11).

Se o snapshot de 18/11 não existisse, Variação Súbita diria `sem alerta nos 2 pregões registrados`. Às 8h de 19/11, antes da primeira rodada do pregão, 19/11 ainda não tem `radares_pregao`; Variação Súbita diria `último alerta há 1 pregão (18/11)` do mesmo jeito, porque `N` conta pregões do calendário, não registros.

## Fontes de dados
Só o snapshot diário `instrumentacao` que a spec 166 já grava (`radares_pregao` e `escondidos_pregao`, por chave de `RADARES`). Leitura com `app.banco.ler_snapshots_datas("instrumentacao", datas)`, numa só consulta para as 20 datas. A retenção de 30 datas de `remover_snapshots_antigos` cobre a janela. Plano B: leitura que devolve `{}` (banco inacessível) ou data sem `radares_pregao` inteiro conta como "sem registro"; nenhuma exceção chega à rota.

## Cálculos
Uma função nova em `app/services/radares.py`, por exemplo `ultimo_alerta(historico: dict[date, dict], pregoes: list[date]) -> dict[str, dict]`, pura (sem banco), com `pregoes` do mais recente para o mais antigo (`pregoes[0]` é `calendario.pregao_corrente(agora)`, os outros vêm de `pregao_anterior`, 20 no total):

Não reaproveite `sistema.ultimos_pregoes(agora)`: ela começa em `ultimo_pregao_fechado`, que durante o pregão é ontem, e deslocaria `pregoes_atras` em um (Faca Caindo diria "há 1 pregão" em vez de "mais cedo neste pregão"). A janela daqui começa em `pregao_corrente`.


- um pregão **tem registro** se o payload dele tem `radares_pregao` inteiro (não `bool`) e maior que 0;
- o radar `c` **acendeu** num pregão com registro se `escondidos_pregao.get(c, 0) < radares_pregao`;
- para cada chave de `RADARES`: `ultimo` = o primeiro pregão de `pregoes` (do mais recente) em que acendeu, ou `None`; `pregoes_atras` = a posição dele em `pregoes` (0 é o pregão corrente), ou `None`;
- `registrados` = quantos pregões da janela têm registro (o mesmo número para todos os radares).

A frase sai disso: `pregoes_atras == 0` → "mais cedo neste pregão"; `pregoes_atras ≥ 1` → "há N pregões (DD/MM)"; `ultimo is None` e `registrados ≥ 1` → "sem alerta nos M pregões registrados"; `registrados == 0` → sem frase. A contagem mede o que o usuário viu: o card apareceu em pelo menos uma coleta daquele pregão. Uma rodada que leu um snapshot ainda com alertas de uma coleta anterior conta como acesa, como no critério de poda da 166.

`index()` lê o histórico uma vez por requisição (fora de data histórica) e passa o resultado a `radares.resumo`, que monta cada item de `sem_alertas` com o nome e a frase. A forma exata (lista de dicts ou de pares) é do desenvolvimento; o teste olha o HTML.

## Critérios de aceite
- [ ] A função pura, com o histórico do exemplo e a janela de 20 pregões terminando em 19/11/2026, devolve `variacao_subita` com `ultimo = 18/11` e `pregoes_atras = 1`, `faca_caindo` com `pregoes_atras = 0`, `exaustao_alta` com `ultimo = None`, e `registrados = 3`.
- [ ] Dia sem `radares_pregao`, com `radares_pregao` igual a `True`, a `0` ou a texto não conta como registro; chave ausente de `escondidos_pregao` num dia com registro conta como acesa (0 < R).
- [ ] Com o exemplo gravado no SQLite temporário e os três radares com lista vazia e frescos às 11:00 BRT de 19/11, o HTML de `/` traz, na seção "Sem alertas", as três frases do exemplo, cada uma num `span.ultimo-alerta` dentro do `li` do nome.
- [ ] Sem nenhum snapshot `instrumentacao`, a seção traz os nomes sem nenhum `span.ultimo-alerta`, e a página responde 200.
- [ ] Com `ler_snapshots_datas` trocado por uma função que levanta exceção, `/` responde 200 e a seção traz os nomes sem frase.
- [ ] Em `/?data=2026-11-18` (histórico), nenhum `span.ultimo-alerta` aparece.
- [ ] `/api/snapshot` traz `paineis.radares_ultimo_alerta` (abaixo) com o exemplo.
- [ ] Em 390 px (Chromium), a seção "Sem alertas" com as frases não tem rolagem horizontal.

## Invariantes de produção
- `/api/snapshot` traz `paineis.radares_ultimo_alerta = {"janela": 20, "registrados": M, "radares": {<chave>: {"ultimo": "AAAA-MM-DD" | null, "pregoes_atras": N | null}}}` com as 20 chaves de `RADARES`, calculado como na tela, independente de o radar estar vazio agora. Em data histórica ou com a leitura falhando, `registrados` é 0 e todos os radares têm `null`.
- Para todo radar: `ultimo` é `null` se e somente se `pregoes_atras` é `null`; quando não é, `0 ≤ pregoes_atras < janela` e `0 ≤ registrados ≤ janela`.
- Toda frase "sem alerta nos M pregões registrados" visível usa o mesmo `M` que `registrados`.

## Fora do escopo
- A última falha da fonte (`registro_fontes`) ao lado do radar indisponível: fica no item da Fila do backlog.
- Contar alertas por hora (`por_hora`) ou mostrar a hora do último alerta; a granularidade é o pregão.
- A manchete do radar raro que acende (item 20 da Fila), que usa a mesma contagem com outra regra.
- Mudar o critério de poda da 166, a gravação de `instrumentacao` ou a retenção dos snapshots.
