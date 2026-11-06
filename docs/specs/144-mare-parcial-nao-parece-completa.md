---
id: 144
titulo: A Maré parcial não parece um índice completo
status: ready
esforco: P
gaveta: experiência
aceite: tests/test_aceite_144.py
brief: P1-3
depende_de: 027
---

## Problema
O usuário perguntou: "um 42 Neutro com Calma ausente é a Maré inteira ou só o que sobrou?"

Em 05/11/2026 o card foi observado como "parcial · sem Calma", score 42, faixa Neutro, com componente ausente. Observação histórica. A spec 027 e `indice()` em `app/services/mare.py` já escolheram a política: com componente faltando, os pesos dos presentes são reescalados para somar 1, o selo é `parcial`, e com menos de dois componentes o valor é `None` e o painel fica indisponível. Esta spec mantém essa escolha. A alternativa de não publicar score sem cobertura total contradiz a 027 e não será adotada.

O que a tela ainda mistura: `view()` coloca em cada componente `round(PESOS[k] × 100)`, o peso nominal. O template escreve "peso 35%" também quando a Calma está ausente, enquanto o 42 foi calculado sem ela. O gauge, sozinho, parece um índice completo.

## Comportamento esperado
- Selo `parcial · sem {nomes}` no mesmo bloco do gauge sempre que `ausentes` não for vazio. Faixa Neutro (40 a 59, spec 027) pode continuar; o selo impede lê-la como cobertura total.
- Componente ausente: rótulo "ausente", sem peso nominal. Componentes presentes: o peso reescalado que entrou na conta, em percentual inteiro, e a soma desses percentuais é 100.
- Texto de cobertura "2 de 3" (ou "1 de 3" não chega a publicar valor: menos de dois componentes continua indisponível, como `indice()`).
- Quando a Calma volta, `parcial` é falso, o selo some e os pesos visíveis voltam a 40, 35 e 25.
- `/api/snapshot` segue com `parcial`, `ausentes`, `pesos` e `valor`. Os `pesos` publicados são os reescalados.

## Fontes de dados
As da spec 027. Plano B já definido: amostra inteira falha → indisponível; só o Ibovespa falha → Calma ausente, índice parcial se Fluxo e Volume existirem.

## Cálculos
`PESOS = fluxo 0,40, calma 0,35, volume 0,25`. Presentes P, `peso_usado(k) = PESOS[k] / soma(PESOS de P)`. Valor = soma `peso_usado × componente`, inteiro pelo `_arredondar` já existente (piso de x + 0,5), limites 0 e 100. Exemplo que o teste usa, escolhido para não repetir o 42 observado: Calma ausente, Fluxo 80 e Volume 20 → `80 × 0,40/0,65 + 20 × 0,25/0,65 = 56,923…` → 57. O 42 de 05/11/2026 não é reconstituído por este fixture.

Denominador da cobertura: 3 componentes nomeados. Ausente entra no denominador e não no numerador dos pesos usados.

## Critérios de aceite
- [ ] Fluxo 80, Calma ausente, Volume 20: HTML contém "parcial", "Calma" e "2 de 3"; não contém "peso 35%"; os pesos visíveis de Fluxo e Volume somam 100; o valor do gauge é 57.
- [ ] Só a Calma presente: painel indisponível, sem gauge e sem faixa Neutro.
- [ ] Os três presentes: sem "parcial", pesos visíveis 40, 35 e 25.
- [ ] `tests/test_aceite_144.py` usa `exigir_spec_done("144")` e não abre rede.

## Invariantes de produção
- `mare.parcial` verdadeiro implica selo parcial na página e pelo menos um nome em `mare.ausentes`.
- A soma dos `mare.pesos` publicados, quando há valor, é 1, com tolerância de 0,001.
- `mare.valor` nulo quando há menos de dois componentes.

## Fora do escopo
- Mudar pesos, faixas ou a definição de Calma, Fluxo e Volume (spec 027).
- Exigir os três componentes para publicar o número.
- Tratar o 42 de 05/11/2026 como erro de fórmula já medido.

## Plano de validação
`pytest -q tests/test_aceite_144.py tests/test_mare_snapshot_antigo.py` sem internet. Sem evidência fictícia de pregão. A recuperação da Calma é o terceiro critério, com fixture, não com produção.
