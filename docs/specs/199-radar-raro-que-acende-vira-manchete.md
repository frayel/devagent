---
id: 199
titulo: O radar raro que acende ganha uma linha sob a manchete
status: ready
esforco: P
gaveta: experiência
aceite: tests/test_aceite_199.py
origem: O radar raro que acende vira manchete
revisada: 2026-11-26
---

## Problema
O investidor pergunta: "acendeu alguma coisa hoje que quase nunca acende?"

Na `main` de 26/11/2026, um radar que passa semanas vazio e acende aparece como qualquer outro card no meio da aba Alertas, entre radares que acendem todo dia. O sistema já sabe separar os dois: desde a spec 166 o snapshot diário `instrumentacao` guarda `radares_pregao` e `escondidos_pregao` por radar, e desde a spec 185 `app/services/radares.py` calcula, numa função pura (`ultimo_alerta`), o último pregão em que cada radar acendeu, numa janela de 20 pregões (`JANELA_ULTIMO_ALERTA`). Esse número só aparece hoje na seção "Sem alertas", para os radares **vazios**. Para o radar que **acabou de acender**, ninguém o usa, e é exatamente aí que ele é notícia.

A manchete (`app/services/manchete.py`, primeira linha de `/`) diz o humor do índice. Uma linha logo abaixo dela, só quando houver radar raro aceso, é o lugar que o investidor das 10h05 lê sem rolar.

## Comportamento esperado
- Fora de data histórica, logo abaixo do `<p class="manchete-texto">` de `app/templates/index.html` e dentro do mesmo `div.manchete-container`, cada **radar raro aceso** ganha um `<p class="manchete-raro">` com uma destas frases:
  - **acendeu e não teve alerta em nenhum pregão anterior com registro:** `Exaustão de Alta acendeu: nenhum alerta nos 11 pregões registrados antes deste.` (`1 pregão registrado` no singular não ocorre, porque o mínimo é 10);
  - **acendeu e o alerta anterior foi há N pregões:** `Radar de Faca Caindo acendeu: o último alerta foi há 10 pregões (18/11).`
- O nome é o de `RADARES` (`app/services/radares.py`).
- **Radar raro aceso**, para a chave `c` de `RADARES`:
  1. o radar está aceso agora: `classificar(payload, c, agora, is_historical)` devolve `COM_ALERTAS` (o mesmo estado que deixa o card visível na aba Alertas);
  2. os pregões **anteriores** ao corrente na janela (`janela_pregoes(agora)[1:]`, 19 pregões) têm pelo menos `MINIMO_REGISTROS_RARO = 10` pregões com registro (a mesma definição de registro da spec 185);
  3. e, nesses pregões anteriores, o radar não acendeu em nenhum, ou o último alerta foi há `N ≥ LIMIAR_RARO = 10` pregões do calendário (`N` = posição em `janela_pregoes(agora)`, 1 é o pregão anterior).
- O pregão corrente não entra na conta do "antes": um radar que acendeu às 10h e continua aceso às 11h segue raro o dia inteiro; um que acendeu às 10h e apagou (estado `SEM_ALERTAS`) não aparece, porque a linha diz o que está aceso agora.
- Ordem: o maior intervalo primeiro (os "nenhum alerta" vêm antes de qualquer "há N"; entre "há N", o maior N primeiro; empate na ordem de `RADARES`). No máximo **2** linhas de radar; com mais de 2 radares raros, uma terceira `<p class="manchete-raro">` diz `e mais K radares raros acenderam; veja a aba Alertas.` (`mais 1 radar raro acendeu` no singular).
- Nenhum radar raro aceso, data histórica (`?data=...`) ou leitura da instrumentação que falha: nenhuma `p.manchete-raro`, e a manchete fica como hoje.
- A linha não muda o texto nem o humor da manchete, não muda a aba Alertas e não muda a seção "Sem alertas" da spec 185.
- `.manchete-raro` ganha estilo em `app/static/tema.css`, com os tokens de `docs/DESIGN.md` (texto menor que `.manchete-texto`, cor de atenção, sem negrito no texto inteiro). Classe sem estilo reprova o teste da spec 187.
- Em 390 px, a linha quebra dentro do contêiner, sem rolagem horizontal.
- Entrada em `app/novidades.json` (tipo `novidade`, `onde`: Visão Geral, manchete).

### Exemplo de ponta a ponta
`agora` = 03/12/2026, 11:00 BRT (14:00 UTC), pregão aberto. `janela_pregoes(agora)`, pelo `app.calendario`: 03/12, 02/12, 01/12, 30/11, 27/11, 26/11, 25/11, 24/11, 23/11, 19/11, 18/11, 17/11, 16/11, ..., 05/11 (20 pregões; 20/11 é feriado). Snapshots `instrumentacao` existem de 17/11 a 03/12 (12 pregões), todos com `radares_pregao: 30`; 16/11 e anteriores não têm registro. Logo, há **11** pregões anteriores com registro (02/12 a 17/11).

`escondidos_pregao`, 30 em todos os dias com registro, exceto:

| Data | Chave | Escondido | Leitura |
|---|---|---|---|
| 01/12 | `variacao_subita` | 25 | acendeu há 2 pregões |
| 18/11 | `faca_caindo` | 28 | acendeu há 10 pregões |
| 03/12 | `short_squeeze` | 20 | acendeu mais cedo neste pregão |

Payloads às 10:55 BRT: `exaustao_alta`, `faca_caindo` e `variacao_subita` com alertas (`COM_ALERTAS`); `short_squeeze` e os outros vazios e frescos.

A manchete ganha, nesta ordem:

1. `Exaustão de Alta acendeu: nenhum alerta nos 11 pregões registrados antes deste.`
2. `Radar de Faca Caindo acendeu: o último alerta foi há 10 pregões (18/11).`

Variação Súbita não aparece (último alerta há 2 pregões). Radar de Short Squeeze não aparece (apagado agora). Se os snapshots de 17/11 e 18/11 não existissem, os pregões anteriores com registro seriam 9 e nenhuma linha apareceria.

## Fontes de dados
Só o que já existe: o snapshot `instrumentacao` (spec 166), lido numa só consulta por `app.banco.ler_snapshots_datas("instrumentacao", pregoes)`, e os payloads atuais dos radares que `_payloads_radares()` (`app/main.py`) já entrega à `/` e ao `/api/snapshot` (este o usa para `paineis.confluencia_radares`). O `/api/snapshot` calcula `raros` com esses mesmos payloads e o mesmo `classificar`, para a página e a API dizerem a mesma coisa. Nenhuma fonte externa. Plano B: leitura que falha ou devolve `{}` vira "nenhum radar raro"; nenhuma exceção chega à rota (como `_ultimo_alerta_radares` em `app/main.py` já faz).

Hoje (26/11) há cerca de 6 pregões com registro depois da 166: a linha só passa a aparecer em produção quando houver 10 pregões anteriores registrados, perto de 03/12/2026. Isso é o comportamento esperado, não defeito.

## Cálculos
- Reaproveitar `ultimo_alerta(historico, pregoes[1:])` da spec 185, sobre o **mesmo** histórico que a rota já lê para a seção "Sem alertas" (uma consulta por requisição, não duas). Hoje `_ultimo_alerta_radares` (`app/main.py`) lê o histórico e devolve só o resultado de `ultimo_alerta(historico, pregoes)`; ele precisa passar a devolver também o cálculo sobre `pregoes[1:]` (ou o histórico), sem uma segunda chamada a `ler_snapshots_datas`. `pregoes_atras` dessa chamada + 1 = `N` do pregão corrente. `registrados` dessa chamada = os "pregões registrados antes deste".
- Uma função pura nova em `app/services/radares.py`, por exemplo `radares_raros(estados: dict[str, str], anterior: dict) -> list[dict]`, que aplica os três critérios e a ordem acima e devolve `{"chave", "nome", "ultimo": date | None, "pregoes_atras": N | None}`; outra (ou a mesma) monta as frases. A forma exata é do desenvolvimento; o teste olha o HTML e o JSON.
- Constantes `LIMIAR_RARO = 10` e `MINIMO_REGISTROS_RARO = 10` no mesmo módulo, ao lado de `JANELA_ULTIMO_ALERTA`.
- Por que 10 e 10: com 20 pregões de janela, "10 pregões sem acender" é metade da janela, o mesmo corte da poda (`PRODUTO.md`, seção 8: escondido em mais da metade de 10 pregões); exigir 10 registros evita chamar de raro um radar só porque o sistema começou a contar ontem.

## Critérios de aceite
- [ ] A função pura, com o histórico e os estados do exemplo, devolve `exaustao_alta` (sem alerta anterior) e `faca_caindo` (`pregoes_atras = 10`, `ultimo = 18/11/2026`), nesta ordem, e nada mais.
- [ ] Sem os snapshots de 17/11 e 18/11 (9 pregões anteriores com registro), a função devolve lista vazia.
- [ ] Com `faca_caindo` acendendo em 19/11 (`escondidos 28`, posição 9) em vez de 18/11, ele sai da lista (N = 9 < 10).
- [ ] Com 4 radares raros acesos, a página traz 3 `p.manchete-raro`: os 2 de maior intervalo e `e mais 2 radares raros acenderam; veja a aba Alertas.`
- [ ] Com o exemplo gravado no SQLite temporário e os payloads frescos às 11:00 BRT de 03/12, o HTML de `/` traz as duas frases do exemplo, cada uma num `p.manchete-raro` dentro de `div.manchete-container`, depois de `p.manchete-texto`.
- [ ] Sem nenhum snapshot `instrumentacao`, ou com `ler_snapshots_datas` levantando exceção, `/` responde 200 sem nenhum `p.manchete-raro`.
- [ ] Em `/?data=2026-12-02` (histórico), nenhum `p.manchete-raro`.
- [ ] `/api/snapshot` traz `paineis.radares_ultimo_alerta.raros` (abaixo) com o exemplo; a leitura da instrumentação continua uma consulta por requisição.
- [ ] `tests/test_aceite_185.py` e `tests/test_classes_com_estilo.py` (classe sem estilo, spec 187) continuam passando.
- [ ] Em 390 px (Chromium), com as duas linhas do exemplo, `/` não tem rolagem horizontal.

## Invariantes de produção
- `/api/snapshot` traz `paineis.radares_ultimo_alerta.raros` como lista (vazia quando não há radar raro, em data histórica ou com a leitura falhando), cada item `{"chave": <chave de RADARES>, "nome": str, "ultimo": "AAAA-MM-DD" | null, "pregoes_atras": N | null}`, e `paineis.radares_ultimo_alerta.registrados_antes` inteiro (0 em data histórica ou com a leitura falhando).
- Para todo item de `raros`: `pregoes_atras` é `null` ou `10 ≤ pregoes_atras < 20`; `registrados_antes ≥ 10`; a chave é uma das 20 de `RADARES`; e, quando `paineis` tem um painel com essa mesma chave (por exemplo `faca_caindo`, `exaustao_alta`), a lista de alertas dele não está vazia. Nem todo radar aparece em `paineis` com a chave de `RADARES` (`volume_alerts` sai como `radar_volume`; `scanner_capitulacao` e `radar_anomalia_fechamento` não têm painel próprio), e esses ficam fora desta conferência.
- `raros` tem no máximo tantos itens quanto radares com alerta no mesmo snapshot.
- O número de `p.manchete-raro` em `/` é `min(len(raros), 2)`, mais 1 quando `len(raros) > 2`.

## Fora do escopo
- Link da linha para o card do radar na aba Alertas (os cards não têm âncora hoje).
- O critério "escondido em mais de 90% das coletas" do backlog: a regra daqui usa pregões, não coletas, porque é o que a 185 já calcula.
- Mudar o texto ou o humor da manchete, a ordem dos cards ou a seção "Sem alertas".
- Notificação ou alerta fora da página.
- Guardar quais radares raros acenderam em cada pregão (memória do raro, para medir o que veio depois): ideia futura, junto do item "Os sinais do sistema têm memória" do backlog.
