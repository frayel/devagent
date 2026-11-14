---
id: 144
titulo: A Maré parcial não parece um índice completo
status: done
esforco: P
gaveta: experiência
aceite: tests/test_aceite_144.py
brief: P1-3
depende_de: 027
revisada: 2026-11-14
---

## Problema
O usuário perguntou: "um 42 Neutro com Calma ausente é a Maré inteira ou só o que sobrou?"

Em 05/11/2026 o card foi observado como "parcial · sem Calma", score 42, faixa Neutro, com componente ausente. Observação histórica. A spec 027 e `indice()` em `app/services/mare.py` já escolheram a política: com componente faltando, os pesos dos presentes são reescalados para somar 1, o selo é `parcial`, e com menos de dois componentes o valor é `None` e o painel fica indisponível. Esta spec mantém essa escolha. A alternativa de não publicar score sem cobertura total contradiz a 027 e não será adotada.

O que a tela ainda mistura: `view()` coloca em cada componente `round(PESOS[k] × 100)`, o peso nominal. O template escreve "peso 35%" também quando a Calma está ausente, enquanto o 42 foi calculado sem ela. O gauge, sozinho, parece um índice completo.

Já na `main` (14/11/2026) e não é refeito: o selo `parcial · sem {{ mare.ausentes }}` em `app/templates/index.html` e os `pesos` reescalados em `snapshot()` (`/api/snapshot`). Falta: o peso visível de cada componente (hoje nominal), o rótulo do ausente sem peso e o texto de cobertura.

## Comportamento esperado
- Selo `parcial · sem {nomes}` no mesmo bloco do gauge sempre que `ausentes` não for vazio. Faixa Neutro (40 a 59, spec 027) pode continuar; o selo impede lê-la como cobertura total.
- Componente ausente: rótulo "ausente", sem peso nominal. Componentes presentes: o peso reescalado que entrou na conta, em percentual inteiro, e a soma desses percentuais é 100.
- Texto de cobertura dentro do selo: `parcial · sem Calma · 2 de 3 componentes`. Não existe "1 de 3" publicado: com menos de dois componentes `indice()` devolve `None`, `coletar()` em `app/collectors/mare.py` devolve `None` e nada é gravado (`MareData.valor` é `int`, nunca nulo). A página continua mostrando a última leitura gravada, com o carimbo de horário dela; sem nenhuma leitura gravada, o painel mostra "Dado indisponível agora".
- Quando a Calma volta, `parcial` é falso, o selo some e os pesos visíveis voltam a 40, 35 e 25.
- `/api/snapshot` segue com `parcial`, `ausentes`, `pesos` e `valor`. Os `pesos` publicados são os reescalados.

## Fontes de dados
As da spec 027. Plano B já definido: amostra inteira falha → indisponível; só o Ibovespa falha → Calma ausente, índice parcial se Fluxo e Volume existirem.

## Cálculos
`PESOS = fluxo 0,40, calma 0,35, volume 0,25`. Presentes P, `peso_usado(k) = PESOS[k] / soma(PESOS de P)`. Valor = soma `peso_usado × componente`, inteiro pelo `_arredondar` já existente (piso de x + 0,5), limites 0 e 100. Exemplo que o teste usa, escolhido para não repetir o 42 observado: Calma ausente, Fluxo 80 e Volume 20 → `80 × 0,40/0,65 + 20 × 0,25/0,65 = 56,923…` → 57. O 42 de 05/11/2026 não é reconstituído por este fixture.

Peso visível na página: `_arredondar(peso_usado(k) × 100)`, em percentual inteiro. No mesmo exemplo: Fluxo `0,40/0,65 = 0,61538…` (fração, como em `/api/snapshot`, que publica `0.6154`) → 61,538 % → 62; Volume `0,25/0,65 = 0,38461…` (`0.3846`) → 38,461 % → 38; 62 + 38 = 100. Os componentes são de 0 a 100 (não fração); os pesos são fração na API e percentual inteiro na página. Com dois presentes, os dois percentuais são x e 100 − x, e nenhum par de pesos da 027 cai em ,5 exato, então a soma é sempre 100: Fluxo+Calma 53 e 47, Calma+Volume 58 e 42. Com os três presentes, `peso_usado = PESOS` e a página mostra 40, 35 e 25.

Denominador da cobertura: 3 componentes nomeados. Ausente entra no denominador e não no numerador dos pesos usados.

## Critérios de aceite
- [ ] Fluxo 80, Calma ausente, Volume 20 (leitura gravada com `valor=57`): HTML do painel contém "parcial", "Calma" e "2 de 3"; não contém "peso 35%"; mostra "peso 62%" e "peso 38%"; o valor do gauge é 57. `indice({"fluxo": 80, "calma": None, "volume": 20})` devolve 57.
- [ ] Só a Calma presente: `indice()` devolve valor `None`; `coletar()` com fixture (sem rede, `respx` ou monkeypatch das buscas) devolve `None` e nada é gravado; sem leitura gravada, o painel mostra "Dado indisponível agora", sem gauge e sem faixa Neutro.
- [ ] Os três presentes: sem "parcial", pesos visíveis 40, 35 e 25.
- [ ] `tests/test_aceite_144.py` usa `exigir_spec_done("144")` e não abre rede.

## Invariantes de produção
- `mare.parcial` verdadeiro implica selo parcial na página e pelo menos um nome em `mare.ausentes`.
- A soma dos `mare.pesos` publicados, quando há valor, é 1, com tolerância de 0,001.
- Nenhuma leitura publicada em `/api/snapshot` tem menos de dois componentes não nulos em `mare.componentes` (com menos de dois, nada é gravado e o valor não existe).

## Fora do escopo
- Mudar pesos, faixas ou a definição de Calma, Fluxo e Volume (spec 027).
- Exigir os três componentes para publicar o número.
- Tratar o 42 de 05/11/2026 como erro de fórmula já medido.
- O texto descritivo do painel ("Fluxo (40%) ... Calma (35%) ... Volume (25%)"), que define os pesos nominais da 027 e continua igual.
- Mostrar a leitura anterior como "indisponível" quando uma coleta nova não publica valor: o carimbo de horário já diz de quando é o número.

## Plano de validação
`pytest -q tests/test_aceite_144.py tests/test_mare_snapshot_antigo.py` sem internet. Sem evidência fictícia de pregão. A recuperação da Calma é o terceiro critério, com fixture, não com produção.

## Revisão
2026-11-14. Conferido contra `app/services/mare.py` (`indice`, `snapshot`, `view`), `app/collectors/mare.py` e `app/templates/index.html`. O exemplo 57 confere (49,231 + 7,692 = 56,923). Acrescentados: o exemplo numérico dos pesos visíveis (62 e 38) com a unidade de cada campo; o que já está na `main` (selo e pesos da API); onde fica o texto de cobertura. O segundo critério pedia "painel indisponível" para uma leitura que o coletor nunca grava; foi reescrito para o que dá para testar: `indice` e `coletar` devolvem `None` e, sem leitura gravada, o painel fica indisponível. Os testes de `tests/test_mare.py` que esperam "peso 35%" gravam os três componentes e continuam válidos.
