---
id: 150
titulo: Radar sem sinal não ocupa um card
status: ready
esforco: M
gaveta: experiência
aceite: tests/test_aceite_150.py
revisada: 2026-11-15
brief: P2-4
depende_de: 141
---

## Problema
O usuário perguntou: "por que a página repete dezenas de vezes que não há sinal?"

Em 05/11/2026 foram observados muitos textos no gênero "nenhum sinal". Observação histórica. O template tem uma seção `aviso-vazio` ("Sem alertas ativos no momento.") quando um conjunto grande de listas vem vazio, e vários cards da classe `alertas` usam `escondido` nesse caso. Outros ainda renderizam `.vazio` ("Nenhum sinal de exaustão no momento.", "Nenhuma absorção detectada no momento." e irmãos em `app/templates/index.html`). Parte some por CSS; parte não. A spec não escolhe uma frase antiga como a causa única.

Estado na `main` em 15/11/2026 (revisão): os 20 radares listados na condição da seção `aviso-vazio` (`app/templates/index.html`, linha ~400) já recebem `escondido` quando a lista vem vazia **e também quando o payload é `None`**. Três defeitos sobram: (1) a seção `aviso-vazio` só aparece quando os 20 estão vazios ao mesmo tempo, e não diz quais radares rodaram sem achar nada; (2) radar sem snapshot some calado, misturado com "sem alerta"; (3) radar com snapshot velho também some como se tivesse rodado agora. Não existe controle para revelar os vazios. O trabalho desta spec é esse, não esconder cards que já se escondem.

## Comportamento esperado
Escopo: os 20 radares da condição `aviso-vazio` atual (volume, variação súbita, concentração de ordens, exaustão de queda, de alta e de tendência, absorção cruzada, liquidez de abertura, congestionamento, faca caindo, anomalias de spread, short squeeze, falso rompimento, divergência volume/preço, esforço vs resultado, scanner de capitulação, armadilha de abertura, compradores de fundo, anomalia de fechamento, radar de inflexão). Ficam fora, embora tenham a classe `alertas`: Relógio de Volatilidade, Sensibilidade a Juros e Sensibilidade ao dólar, que não são listas de sinais. A lista de radares fica num lugar só (uma constante no Python ou uma lista no template), e a condição de 20 `and` encadeados some.

- Lista vazia porque a regra rodou e não achou ninguém: o card individual não aparece. Os nomes desses radares entram na seção única "Sem alertas", a `aviso-vazio` já existente, que passa a aparecer sempre que **pelo menos um** radar está vazio (não só quando os 20 estão), visível por padrão na aba Alertas. Se nenhum radar estiver vazio, a seção não aparece.
- Controle "Mostrar vazios", um `<button>` com `aria-pressed`, dentro da seção "Sem alertas", revela os cards vazios. O nome do botão está visível, o foco chega pelo teclado, e o estado não depende de hover. O estado pressionado tem forma no servidor: `GET /?vazios=1` renderiza os cards vazios sem `escondido` e o botão com `aria-pressed="true"`; sem o parâmetro, cards vazios com `escondido` e `aria-pressed="false"`. Com JavaScript, o clique alterna as duas coisas sem recarregar (em `app/static/ui.js`); sem JavaScript, o botão leva ao mesmo endereço com ou sem `vazios=1`. É esse parâmetro que torna o segundo critério testável sem navegador.
- Lista ausente (`None`, coleta que não gravou): não usa a frase de "nenhum sinal" e não conta como vazio. Entra na seção como item à parte, com o nome do radar e o texto do `estado('indisponivel')` (ou `sem_registro` no modo histórico), e o card, se o usuário pediu para ver vazios, mostra o mesmo estado.
- Dado velho: não entra em "Sem alertas" como se a regra tivesse rodado neste pregão. Entra como item à parte, "desatualizado", com o carimbo `dd/mm/aaaa HH:MM BRT` da coleta. "Velho" é a regra da spec 141 já na `main`, sem regra nova: durante o pregão, `app.services.carimbo.desatualizado(timestamp, agora, chave)` (TTL padrão de 30 minutos, `idade > TTL`); fora do pregão, o pregão do snapshot (`carimbo.pregao_de`) anterior ao último pregão fechado (`app.calendario.ultimo_pregao_fechado`). No modo histórico (pregão escolhido no seletor) não há selo de desatualizado.
- Hoje o contexto do `index` (`app/main.py`) entrega `coletado_em` já formatado em texto (`formatar_data`). A decisão de desatualizado usa o `timestamp` bruto do registro, não a string reparseada.
- Em 390px a seção é uma coluna, sem rolagem horizontal. Revelar os vazios também.

Rankings que não são alertas (maiores altas, força relativa) não são escondidos por esta spec.

## Fontes de dados
As listas que cada radar já grava. Plano B: `None` vira indisponível, lista vazia vira "sem alerta", e os dois não compartilham frase.

## Cálculos
Não há regra nova de sinal. Cada radar cai em exatamente um de quatro estados, nesta ordem:

1. payload `None` → **indisponível**;
2. snapshot velho (regra da spec 141 acima) → **desatualizado**, qualquer que seja a lista;
3. lista vazia → **sem alerta** (entra em "Sem alertas");
4. lista com nomes → card visível, como hoje.

Exemplo de ponta a ponta, TTL: `agora` = quarta 11/11/2026 14:00 BRT (pregão aberto no calendário). Registro de `exaustao_queda` com `timestamp` 11/11/2026 16:29 UTC (= 13:29 BRT) e `alertas_json = "[]"`: idade 31 min > 30 → desatualizado; a seção mostra "Exaustão de Queda · desatualizado · 11/11/2026 13:29 BRT" e o nome não aparece entre os "Sem alertas". Com `timestamp` 16:30 UTC (13:30 BRT): idade 30 min, não é > 30 → sem alerta, e "Exaustão de Queda" aparece na lista "Sem alertas". O mesmo registro de 13:29 BRT lido no sábado 14/11/2026 10:00 BRT: fora do pregão, último pregão fechado é 13/11 e o snapshot é de 11/11 → desatualizado.

## Critérios de aceite
- [ ] Fixture em que todos os radares `alertas` devolvem lista vazia: o HTML visível (sem contar nó com `escondido`) contém uma seção "Sem alertas" e não contém duas ou mais frases `.vazio` de radar. O botão "Mostrar vazios" está presente.
- [ ] O mesmo fixture com `GET /?vazios=1`: os cards vazios deixam de ter `escondido` e o botão tem `aria-pressed="true"`; sem o parâmetro, `aria-pressed="false"`.
- [ ] Um único radar com lista vazia e os demais com nomes: a seção "Sem alertas" aparece e contém o nome desse radar (hoje ela só aparece com os 20 vazios).
- [ ] Um radar `None` e os outros com lista vazia: o texto visível desse radar é o de indisponível e não é "Nenhum sinal" nem "Nenhuma".
- [ ] Com `agora` fixado em 11/11/2026 14:00 BRT, `exaustao_queda` vazio com `timestamp` 13:29 BRT: o nome não está na lista "Sem alertas"; o HTML traz "desatualizado" e `11/11/2026 13:29`. Com `timestamp` 13:30 BRT: o nome está na lista "Sem alertas".
- [ ] Relógio de Volatilidade, Sensibilidade a Juros e Sensibilidade ao dólar não entram na seção "Sem alertas".
- [ ] Maiores altas com cinco linhas continuam visíveis.
- [ ] `tests/test_aceite_150.py` usa `exigir_spec_done("150")` e não abre rede.

## Invariantes de produção
- Na aba Alertas, com as regras tendo rodado e voltado vazias, há um bloco "Sem alertas" e não um card por radar vazio.
- Radar sem snapshot não usa a frase de lista vazia.
- Radar velho não é anunciado como "sem sinal hoje".

## Fora do escopo
- Apagar radar ou afrouxar o critério que o faz disparar (isso seria poda, spec à parte).
- A duplicata da inflexão (spec 151), que deixa de existir como segundo card; o que restar obedece a esta spec quando estiver na classe `alertas`.
- Novo tipo de alerta para preencher a seção.
- O `/api/snapshot`: o fallback de `radar_volume` sem dado grava `coletado_em = agora` (`app/main.py`, ~linha 1103). É o mesmo tipo de carimbo forjado que a spec 141 proíbe, mas mexer no contrato da API é spec à parte.
- Mudar o TTL ou a regra de `carimbo.desatualizado` (spec 141).

## Plano de validação
`pytest -q tests/test_aceite_150.py` sem internet. O PR de implementação percorre a aba Alertas em 1440px e em 390px, com o botão nos dois estados, num pregão real de manhã ou de tarde. Sem captura nesta rodada. A spec não marca os radares de 05/11/2026 como corrigidos.

## Revisão
Revisada em 15/11/2026. Não é duplicata: a spec 080 (`done`) criou a seção `aviso-vazio` e o `escondido` dos cards; esta corrige o que a 080 deixou de fora. O que mudou no texto: (1) o *Problema* registra que os cards vazios e os `None` já recebem `escondido` na `main`, e o trabalho real passa a ser a seção listar quais radares estão vazios (com um só vazio, não só com os 20), separar indisponível e desatualizado, e criar o botão; (2) o escopo nomeia os 20 radares e exclui Relógio e as duas Sensibilidades, que têm a classe `alertas` mas não são listas de sinal; (3) "desatualizado" passa a ser a regra já existente da spec 141 (`carimbo.desatualizado` no pregão, `pregao_de` contra `ultimo_pregao_fechado` fora dele), com exemplo numérico e o aviso de que `coletado_em` no contexto do `index` já é texto; (4) o estado pressionado do botão ganhou forma no servidor (`?vazios=1`), para o critério ser testável sem navegador; (5) dois critérios novos (um só radar vazio; exclusões) e dois itens novos no *Fora do escopo*.

Tamanho: `index.html`, `app/main.py` (contexto dos radares com `timestamp` bruto e o estado de cada um, de preferência num helper), `app/static/ui.js`, `app/static/tema.css` e o teste de aceite. Testes que leem `escondido` no HTML: `tests/test_aceite_141.py` e `tests/test_aceite_149.py`, que precisam continuar verdes. Cabe numa sessão.
