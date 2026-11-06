---
id: 150
titulo: Radar sem sinal não ocupa um card
status: ready
esforco: M
gaveta: experiência
aceite: tests/test_aceite_150.py
brief: P2-4
depende_de: 141
---

## Problema
O usuário perguntou: "por que a página repete dezenas de vezes que não há sinal?"

Em 05/11/2026 foram observados muitos textos no gênero "nenhum sinal". Observação histórica. O template tem uma seção `aviso-vazio` ("Sem alertas ativos no momento.") quando um conjunto grande de listas vem vazio, e vários cards da classe `alertas` usam `escondido` nesse caso. Outros ainda renderizam `.vazio` ("Nenhum sinal de exaustão no momento.", "Nenhuma absorção detectada no momento." e irmãos em `app/templates/index.html`). Parte some por CSS; parte não. A spec não escolhe uma frase antiga como a causa única.

## Comportamento esperado
Escopo: painéis com a classe `alertas`.

- Lista vazia porque a regra rodou e não achou ninguém: o card individual não aparece. Os nomes desses radares entram na seção única "Sem alertas", a `aviso-vazio` já existente, visível por padrão na aba Alertas.
- Controle "Mostrar vazios", um `<button>` com `aria-pressed`, revela os cards vazios. O nome do botão está visível, o foco chega pelo teclado, e o estado não depende de hover. Sem o JavaScript, a seção "Sem alertas" continua no HTML; os cards vazios podem permanecer no DOM com `escondido`, desde que o botão exista e o teste sem JS ainda não mostre dezenas de frases soltas como conteúdo visível (classe `escondido`).
- Lista ausente (`None`, coleta que não gravou): não usa a frase de "nenhum sinal". O item na seção, ou o card se o usuário pediu para ver vazios, diz indisponível.
- Dado mais velho que o TTL da spec 141: não entra em "Sem alertas" como se a regra tivesse rodado neste pregão. Mostra desatualizado, com o carimbo.
- Em 390px a seção é uma coluna, sem rolagem horizontal. Revelar os vazios também.

Rankings que não são alertas (maiores altas, força relativa) não são escondidos por esta spec.

## Fontes de dados
As listas que cada radar já grava. Plano B: `None` vira indisponível, lista vazia vira "sem alerta", e os dois não compartilham frase.

## Cálculos
Não há regra nova de sinal. A distinção é o formato do payload: lista vazia, ausência de snapshot, ou `coletado_em` além do TTL.

## Critérios de aceite
- [ ] Fixture em que todos os radares `alertas` devolvem lista vazia: o HTML visível (sem contar nó com `escondido`) contém uma seção "Sem alertas" e não contém duas ou mais frases `.vazio` de radar. O botão "Mostrar vazios" está presente.
- [ ] O mesmo fixture com o estado do botão pressionado: os cards vazios deixam de ter `escondido`.
- [ ] Um radar `None` e os outros com lista vazia: o texto visível desse radar é o de indisponível e não é "Nenhum sinal" nem "Nenhuma".
- [ ] Um radar com lista vazia e `coletado_em` além do TTL: não é contado dentro de "Sem alertas"; o HTML traz desatualizado e o carimbo.
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

## Plano de validação
`pytest -q tests/test_aceite_150.py` sem internet. O PR de implementação percorre a aba Alertas em 1440px e em 390px, com o botão nos dois estados, num pregão real de manhã ou de tarde. Sem captura nesta rodada. A spec não marca os radares de 05/11/2026 como corrigidos.
