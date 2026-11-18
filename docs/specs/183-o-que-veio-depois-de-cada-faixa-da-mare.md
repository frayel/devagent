---
id: 183
titulo: O que o Ibovespa fez nos 5 pregões depois de cada faixa da Maré
status: ready
esforco: M
gaveta: capacidade nova
aceite: tests/test_aceite_183.py
origem: Os sinais do sistema têm memória
revisada: 2026-11-18
---

## Problema
A Maré (spec 027) diz em que faixa está o humor da bolsa hoje: Pânico, Medo, Neutro, Confiança ou Otimismo extremo. Ela não diz o que a pessoa quer saber em seguida: **quando a Maré esteve nesta faixa antes, o que o Ibovespa fez nos dias seguintes?**

Desde a spec 174a o sistema grava, uma vez por pregão, a leitura diária da Maré dos últimos até 252 pregões (snapshot `mare_historico`, campo `leituras`). Falta só o fechamento do Ibovespa de cada um desses dias para cruzar faixa e retorno seguinte. Nenhum painel de mercado mostra isso para o próprio indicador dele, com a amostra à vista.

É a primeira fatia do item *Os sinais do sistema têm memória* do `docs/BACKLOG.md`: só a Maré, só o Ibovespa, um horizonte só (5 pregões). Leitura descritiva do passado, não previsão.

## Comportamento esperado
1. **O histórico guarda o fechamento do Ibovespa.** Em `app/collectors/mare_historico.py`, `calcular` acrescenta a cada item de `leituras` o campo `ibov`: o fechamento do Ibovespa naquele dia, em pontos, tirado do `ibov: dict[date, float]` que a função já recebe (`buscar_ibov`). Dia sem fechamento no dicionário fica com `ibov: null`. Nenhuma requisição nova: o coletor já baixa os 2 anos do Ibovespa.
2. **Função pura `memoria(leituras, faixa_hoje, horizonte=5)` em `app/services/mare.py`**, com a conta de *Cálculos*. Devolve `null` quando não há nenhum caso (inclusive no snapshot antigo, gravado antes desta spec, em que nenhuma leitura tem `ibov`).
3. **`/api/snapshot`:** `paineis.mare.memoria` com o retorno da função, ao lado de `niveis` (mesmo ponto de `app/main.py` que monta `niveis`, lendo o mesmo `ler_snapshot("mare_historico")`). Formato:
   ```json
   {
     "horizonte": 5,
     "de": "2025-11-18", "ate": "2026-11-10",
     "faixa_hoje": "Medo",
     "todos": {"casos": 247, "media": 0.21, "positivos": 53},
     "faixas": [
       {"faixa": "Pânico", "casos": 4, "media": null, "positivos": null, "confianca": "poucos casos"},
       {"faixa": "Medo", "casos": 38, "media": 0.62, "positivos": 58, "confianca": "moderada"},
       ...
     ]
   }
   ```
   `faixas` traz as cinco faixas sempre, na ordem de `FAIXAS`, inclusive com `casos: 0`. `media` em %, duas casas; `positivos` em % inteiro. Sem `mare_historico` ou sem caso, `memoria` é `null` e o resto de `paineis.mare` não muda. A chave `memoria` está sempre presente, como `niveis`; por isso o `test_sem_historico_niveis_nulos_e_resto_da_mare_igual` de `tests/test_aceite_174a.py` (que hoje exige `set(resto) == {"fonte", "coletado_em"}` tirando só `niveis`) passa a tirar também `memoria` do `resto`, e só isso muda nele.
4. **Na tela solo `/mare` (spec 173), abaixo do card**, um bloco *Depois de cada faixa*, **fora** do card e do fragmento `/mare/card` (o seletor Marolas, Ondas e Maré não o troca nem o recarrega). Ele tem:
   - uma frase sobre a faixa de hoje: *"Nos 38 pregões entre 18/11/2025 e 10/11/2026 em que a Maré fechou em Medo, o Ibovespa andou em média +0,62% nos 5 pregões seguintes e subiu em 58% deles. Em todos os 247: +0,21% e 53%."* Com a faixa de hoje em *poucos casos*: *"A Maré fechou em Pânico em só 4 pregões entre 18/11/2025 e 10/11/2026: poucos casos para dizer o que costuma vir depois."*;
   - uma tabela com as cinco faixas: **Faixa**, **Casos**, **Ibovespa 5 pregões depois** (média, com sinal e seta, números tabulares) e **Subiu em**; a linha da faixa de hoje marcada (texto "hoje", não só cor). Faixa em *poucos casos* mostra o número de casos e "poucos casos" no lugar dos outros dois números;
   - o método em uma linha recolhível, no padrão dos outros métodos da página: fonte (Yahoo, o `fonte` do snapshot), data da coleta (`coletado_em` do `mare_historico`), a conta, o grau de confiança e as três ressalvas de *Cálculos*.
   A rota `pagina_mare` de `app/main.py` lê o `mare_historico` ela mesma para o bloco, em qualquer `?nivel=` (hoje `_card_mare_nivel` só o lê fora do Marolas), e a `faixa_hoje` vem da mesma view da Maré que o card usa (`get_mare_view()`).
   Com `memoria` `null`, o bloco mostra *"Memória em formação: o histórico ainda não tem o fechamento do Ibovespa de cada dia."* e nada mais. Os dados do bloco vêm do servidor; nenhum JavaScript novo.
5. **A página inicial não muda.** O card da Maré da página inicial e o fragmento `/mare/card` ficam como estão (a primeira dobra da spec 176 não cresce).

## Fontes de dados
O snapshot `mare_historico` da spec 174a (Yahoo `/v8/finance/chart`, uma coleta por pregão completo, depois das 18h15 BRT). O fechamento do Ibovespa vem da mesma resposta que a 174a já usa para a Calma; o custo de coleta não muda.

**Plano B:** se o Yahoo falhar, a 174a não grava e o snapshot anterior continua valendo; a memória sai dele, com o `ate` mostrando até onde vai. Até a primeira coleta depois do merge (as leituras antigas não têm `ibov`), a memória fica *em formação* e o resto da página funciona.

## Cálculos
Sobre `leituras` em ordem crescente de data, só as que têm `valor` e `ibov` (as outras ficam de fora, e a contagem de 5 segue sobre as que sobram).

- **Faixa do dia:** `faixa(valor)` da leitura (a leitura diária, de pregão completo, que a 174a grava; é o Marolas no fechamento).
- **Retorno seguinte:** para a leitura de posição `i`, `r_i = (ibov[i+5] / ibov[i] − 1) × 100`, em %, com `ibov[i+5]` o fechamento da 5ª leitura seguinte. As 5 últimas leituras não têm `r` e não contam como caso.
- **Por faixa:** `casos` = quantos `r_i` com essa faixa; `media` = média aritmética desses `r_i`, arredondada a 2 casas; `positivos` = `round(100 × (quantos r_i > 0) / casos)` (zero não é positivo; arredondamento meio para cima, por `_arredondar`). **`todos`** faz a mesma conta com todos os casos e mostra os números com qualquer quantidade de casos (sem `confianca`).
- **Grau de confiança por faixa:** menos de 10 casos → `poucos casos` (e `media` e `positivos` vão `null`); de 10 a 29 → `baixa`; 30 ou mais → `moderada`. Nunca `alta`: um ano só e janelas sobrepostas (abaixo).
- **`de` e `ate`:** a data da primeira e da última leitura **com caso** (a `ate` fica 5 leituras antes da última gravada).
- **`faixa_hoje`:** `faixa` da leitura de Marolas atual (a mesma do card, `paineis.mare.faixa`); sem leitura atual, a faixa da última leitura do histórico.

*Exemplo de ponta a ponta (horizonte 5):* 7 leituras com `ibov` 100.000, 101.000, 99.000, 100.000, 102.000, 103.000, 104.050 e `valor` 15, 15, 50, 50, 50, 50, 50. Só as duas primeiras têm caso (da 3ª à 7ª, não há 5 leituras depois): `r_0 = (103.000 / 100.000 − 1) × 100 = +3,00`; `r_1 = (104.050 / 101.000 − 1) × 100 = +3,0198… → +3,02`. Pânico: 2 casos → `poucos casos`, `media` e `positivos` `null`. `todos`: 2 casos, `media = (3,00 + 3,0198) / 2 = 3,0099 → +3,01` (a média usa os `r` sem arredondar), `positivos = 100`. `de` = data da 1ª leitura, `ate` = data da 2ª.

*Exemplo com 10 casos:* 10 casos em Medo com `r` = +3, +2, +2, +1, +1, +1, 0, −1, −1, −2 → soma 6, `media` = **+0,60**; 6 maiores que zero → `positivos` = **60**; `confianca` = `baixa`.

**Ressalvas que o método diz em texto:**
1. Os casos de dias vizinhos compartilham pregões (as janelas de 5 se sobrepõem), então não são independentes; 38 casos valem menos que 38 observações soltas.
2. O histórico é recalculado com a cesta de ações de hoje (spec 174a): ação que saiu da bolsa no período não entra.
3. É o que aconteceu num ano, não uma previsão.

## Critérios de aceite
- [ ] `tests/test_aceite_183.py`, com `exigir_spec_done("183")`, sem internet:
  - **cálculo:** os dois exemplos de *Cálculos* dão os números escritos lá (inclusive `null` em `media` e `positivos` com 2 casos, e `+0,60`/`60`/`baixa` com 10); com 30 casos numa faixa, `confianca` = `moderada`; leitura sem `ibov` fica de fora; as cinco faixas aparecem sempre, na ordem de `FAIXAS`, e a soma dos `casos` delas é `todos.casos`;
  - **coletor:** com o Yahoo falso de `tests/yahoo_falso.py`, `calcular` grava `ibov` em cada leitura, igual ao fechamento do dicionário do Ibovespa naquele dia;
  - **snapshot antigo:** com um `mare_historico` cujas leituras não têm `ibov`, `paineis.mare.memoria` é `null`, `/mare` mostra "Memória em formação" e `paineis.mare.niveis` não muda;
  - **tela:** com um `mare_historico` sintético, `/mare` contém o título *Depois de cada faixa*, a frase da faixa de hoje com os números do snapshot no formato brasileiro (`+0,60%`), a marca "hoje" na linha certa, "poucos casos" na faixa com menos de 10, e o método com fonte, data, as três ressalvas e o grau de confiança;
  - **fragmento e página inicial:** `/mare/card?nivel=ondas` e `/` não contêm *Depois de cada faixa*.
- [ ] Checklist visual do `docs/DESIGN.md` em 390 px e 1440 px na `/mare`: a tabela não rola para o lado em 360 px.

## Invariantes de produção
- Quando `paineis.mare.memoria` não é `null`: `horizonte` = 5; `faixas` tem 5 itens, na ordem de `FAIXAS`; a soma dos `casos` das faixas é igual a `todos.casos`; `todos.casos` ≤ 247.
- Em cada faixa com `casos` ≥ 10, `positivos` está entre 0 e 100 e `confianca` é `baixa` ou `moderada`; com `casos` < 10, `media` e `positivos` são `null`.
- `memoria.ate` é anterior ao `ate` do `mare_historico` (o mesmo de `paineis.mare.niveis.ondas.ate`, quando `ondas` não é `null`; fica 5 leituras com `ibov` antes) e é dia útil da B3.
- `memoria.faixa_hoje` é um dos cinco nomes de `FAIXAS`.

## Fora do escopo
- Outros sinais (confluência de radares, apetite aqui e lá fora) e outros horizontes: fatias 2 e 3 do item *Os sinais do sistema têm memória* do `docs/BACKLOG.md`.
- Memória por nível (Ondas e Maré): condicionar à média de 21 ou 252 pregões é outra pergunta, com casos ainda mais sobrepostos.
- Histórico além de 252 pregões ou intervalo de confiança estatístico: spec própria, se a amostra pedir.
- Mostrar o bloco na página inicial ou dentro do card.
- Qualquer leitura preditiva ou recomendação a partir desses números.
