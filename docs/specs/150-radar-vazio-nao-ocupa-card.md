---
id: 150
titulo: Radar sem sinal não ocupa um card
status: ready
esforco: M
gaveta: experiência
aceite: tests/test_aceite_150.py
brief: P2-4
depende_de: 141
revisada: 2026-11-15
---

## Problema
O usuário perguntou: "por que a página repete dezenas de vezes que não há sinal?"

Em 05/11/2026 foram observados muitos textos no gênero "nenhum sinal". É uma observação histórica. A spec não escolhe uma frase antiga como causa única.

Na `main` de 15/11/2026, os 20 painéis da classe `alertas` em `app/templates/index.html` já recebem `escondido` quando a lista vem vazia, e `.escondido { display: none !important; }` em `app/static/tema.css` vence o `style.display` que `app/static/ui.js` aplica ao trocar de aba. A frase `.vazio` desses cards fica no HTML, mas não aparece. Faltam quatro coisas:

1. A seção `aviso-vazio` ("Sem alertas ativos no momento.") só aparece quando **todos** os 20 radares estão vazios, e não diz quais estão. Com um único radar disparando, os outros 19 somem sem rastro: o usuário não sabe se rodaram.
2. Radar `None` (coleta que não gravou) cai na mesma condição `not x` que a lista vazia: fica escondido e conta como "sem alertas". Um radar quebrado é anunciado como radar sem sinal.
3. Radar com snapshot velho também conta como "sem alertas", como se a regra tivesse rodado agora.
4. Não há como ver os cards vazios.

As frases `.vazio` que continuam visíveis estão em painéis de outras classes (`rankings`, `visao-geral`) e ficam fora desta spec.

## Comportamento esperado
Escopo: os 20 painéis com a classe `alertas` listados na condição da seção `aviso-vazio` de `app/templates/index.html` (Radar de volume, Variação Súbita, ..., Radar de Inflexão).

- **Lista vazia** (o snapshot existe, `alertas` ou `alerts` é `[]`, e não está velho): o card continua com `escondido` e recebe também a classe `radar-vazio`. O nome do radar entra na seção "Sem alertas" (a `aviso-vazio` existente, renomeada), que lista os nomes de **todos** os radares nessa situação. A seção aparece sempre que houver pelo menos um, mesmo que outros radares tenham alertas.
- **Lista ausente** (`None`): o nome entra na seção com a marca "indisponível" (ou "sem registro" em data histórica, como já faz o macro `estado`). Não usa a frase de lista vazia nem conta no total de "sem alertas".
- **Desatualizado:** o snapshot existe, mas `carimbo.desatualizado(timestamp, agora, chave)` (de `app/services/carimbo.py`, spec 141) devolve `True`. A chave é o nome do radar no contexto. Ela não está em `TTL_MINUTOS` e cai no `TTL_MINUTOS_PADRAO` de 30 minutos, que equivale a dois ciclos de coleta de 15 minutos do `app/agendador.py`. O nome entra na seção com "desatualizado" e o horário da coleta. Não conta como "sem alertas". Em data histórica (`is_historical`), nada é desatualizado.
- **Com alertas:** o card aparece como hoje.
- **Controle "Mostrar vazios":** um formulário `GET` com um `<button type="submit" name="vazios">` que preserva o parâmetro `data`. Sem o parâmetro, o botão diz "Mostrar vazios", tem `aria-pressed="false"` e `value="1"`. Com `?vazios=1`, os cards `radar-vazio` são renderizados sem `escondido`, e o botão diz "Esconder vazios", tem `aria-pressed="true"` e `value="0"`. Funciona sem JavaScript, recebe foco pelo teclado e não depende de hover. O botão fica dentro da seção "Sem alertas".
- Em 390 px, a lista de nomes da seção é uma coluna, sem rolagem horizontal, com ou sem `vazios=1`.

Rankings que não são alertas (maiores altas, força relativa, Inflexão de Tendência em `rankings`) não são escondidos por esta spec.

### Exemplo de ponta a ponta
Pregão de 16/11/2026, `agora` = 10:45 BRT (13:45 UTC):

| Radar | Snapshot | Resultado |
|---|---|---|
| Radar de volume | `timestamp` 10:30 BRT, `alerts` com 2 linhas | card visível com 2 linhas |
| Variação Súbita | `timestamp` 10:30 BRT, `alertas: []` | idade de 15 min, abaixo do TTL de 30: "Variação Súbita" na seção; card `radar-vazio escondido` |
| Exaustão de Alta | `timestamp` 10:00 BRT, `alertas: []` | idade de 45 min, acima do TTL de 30: "Exaustão de Alta · desatualizado · 10:00" na seção; não conta como sem alertas |
| Faca Caindo | `None` | "Radar de Faca Caindo · indisponível" na seção |
| os outros 16 | `timestamp` 10:30 BRT, lista vazia | nomes na seção |

A seção traz 17 nomes sem alerta, 1 desatualizado e 1 indisponível. Com `?vazios=1`, os 17 cards `radar-vazio` aparecem, cada um com a sua frase `.vazio`. Os cards desatualizado e indisponível não são `radar-vazio`.

## Fontes de dados
As listas que cada radar já grava, lidas como hoje em `index()` de `app/main.py`. Para o teste de idade, a rota passa ao template o `timestamp` bruto (`datetime`) ou um booleano já calculado. Não se reconverte a string formatada de `coletado_em`. Plano B: `None` vira indisponível, lista vazia vira "sem alerta", velho vira desatualizado, e os três não compartilham frase.

## Cálculos
Não há regra nova de sinal. A classificação de cada radar sai do payload: `None`, depois `desatualizado(...)`, depois lista vazia, depois lista com itens. A idade é `agora - timestamp`, comparada com 30 minutos, e só durante o pregão (`carimbo.no_pregao`).

## Critérios de aceite
- [ ] Fixture com os 20 radares `alertas` com lista vazia e frescos: o HTML visível (sem contar nó com `escondido`) contém a seção "Sem alertas" com os 20 nomes e nenhuma frase `.vazio` de radar. O botão "Mostrar vazios" está presente, com `aria-pressed="false"`.
- [ ] Fixture misto, com 1 radar com alertas e 19 vazios: o card com alertas está visível e a seção "Sem alertas" existe com os 19 nomes. Hoje a seção some nesse caso.
- [ ] O fixture vazio com `?vazios=1`: os 20 cards `radar-vazio` não têm `escondido` e o botão tem `aria-pressed="true"`.
- [ ] Um radar `None` e os outros vazios: o item desse radar diz "indisponível", não contém "Nenhum" nem "Nenhuma", e o nome dele não está entre os sem alerta.
- [ ] Um radar com lista vazia e `timestamp` 45 minutos antes de `agora`, com `agora` durante o pregão: não está entre os sem alerta, e o HTML traz "desatualizado" e o horário da coleta. Com o mesmo fixture em data histórica, não aparece "desatualizado".
- [ ] Maiores altas com cinco linhas continuam visíveis.
- [ ] `tests/test_aceite_150.py` usa `exigir_spec_done("150")`, congela `agora` e não abre rede.

## Invariantes de produção
- Na aba Alertas, durante o pregão, cada um dos 20 radares aparece exatamente uma vez: como card com alertas ou como nome na seção "Sem alertas".
- Radar sem snapshot nunca é listado como "sem alertas".
- Radar com coleta de mais de 30 minutos, durante o pregão, nunca é listado como "sem alertas".
- `GET /?vazios=1` responde 200 e mostra os cards vazios.

## Fora do escopo
- Apagar radar ou afrouxar o critério que o faz disparar (isso seria poda, numa spec à parte).
- A duplicata da inflexão (spec 151). O que restar obedece a esta spec se estiver na classe `alertas`.
- Novo tipo de alerta para preencher a seção.
- Frases `.vazio` de painéis fora da classe `alertas`.
- TTL próprio por radar em `TTL_MINUTOS`. Fica o padrão de 30 minutos.
- O endpoint JSON `snapshot()`, que hoje grava `[]` para radar ausente em alguns painéis.

## Plano de validação
`pytest -q tests/test_aceite_150.py`, sem internet. O PR de implementação percorre a aba Alertas em 1440 px e em 390 px, com e sem `?vazios=1`, num pregão real, de manhã ou de tarde. Sem captura nesta rodada. A spec não marca os radares de 05/11/2026 como corrigidos.

## Revisão
Revisada em 15/11/2026. O texto original dizia que, entre os cards `alertas`, "parte some por CSS; parte não". Na `main`, todos os 20 já somem quando vazios. Por isso o primeiro critério original já passava sem mudança de código. A revisão:

- reescreveu o problema com o que falta de fato: a seção é tudo ou nada e não traz os nomes, `None` e dado velho contam como "sem alertas", e não há como ver os cards vazios;
- acrescentou o critério do fixture misto, que falha hoje;
- trocou o "TTL da spec 141" pela função concreta e pelo valor de 30 minutos, que é o padrão, já que os radares não estão em `TTL_MINUTOS`;
- incluiu o exemplo numérico e a regra da data histórica;
- definiu o botão como formulário `GET` com `?vazios=1`. Isso funciona sem JavaScript e deixa o segundo critério testável pelo `TestClient`. O texto original não dizia como o estado "pressionado" chegaria ao HTML.
