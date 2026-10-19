---
id: 071
titulo: Consultor · decisão final cruzando técnico e casas de análise
status: ready
esforco: M
---

## Problema
Com os sinais técnicos (068) e as opiniões das casas (070) lado a lado, o usuário ainda tem de conciliar os dois. O valor do consultor está justamente no conflito: quando as casas recomendam compra e o preço continua caindo, a resposta útil é "aguardar", com o gatilho que destrava a decisão.

## Comportamento esperado
- Cada ativo do `/consultor` mostra uma **decisão final** (Comprar, Vender, Aguardar, No radar ou Sem sinal) e, abaixo, duas colunas: "Técnico" (regra, motivo, gatilho, confiança da spec 069) e "Casas" (consenso, preço-alvo mediano, faixa e potencial).
- A página passa a agrupar pela decisão final. "No radar" é um grupo novo, entre Aguardar e Sem sinal.
- Quando a decisão final difere da técnica, uma frase diz o porquê, por exemplo: "3 de 4 casas recomendam compra, mas o preço segue abaixo da MM200. Aguardar fechamento acima de R$ 38,20."
- Sem opiniões disponíveis (spec 070 em degradação ou ativo sem cobertura), a decisão final é a técnica, marcada "sem opinião de casas", sem erro.

## Fontes de dados
Nenhuma nova. Usa as saídas das specs 068, 069 e 070.

## Cálculos
**Consenso das casas** por ativo, só com a opinião mais recente de cada casa nos últimos 30 dias:
- Válido apenas com pelo menos 2 casas distintas; abaixo disso, "cobertura insuficiente".
- Contagem compra, neutro e venda. Consenso **compra** se compra ≥ 2/3 das casas; **venda** se venda ≥ 2/3; senão **dividido**.
- Preço-alvo mediano, mínimo e máximo, só com opiniões que trazem alvo; potencial = alvo mediano / preço atual − 1.

**Matriz de decisão** (constantes nomeadas em `app/consultor/sintese.py`):

| Técnico | Casas | Decisão final |
|---|---|---|
| Comprar | compra ou insuficiente | Comprar |
| Comprar | dividido | Comprar, com nota "casas divididas" |
| Comprar | venda | Aguardar: gatilho "nova opinião de casa ou fechamento acima da máxima de 20 pregões" |
| Vender | venda ou insuficiente | Vender |
| Vender | dividido | Vender, com nota "casas divididas" |
| Vender | compra | Aguardar: gatilho técnico de reversão (fechamento acima da `MM200`) |
| Aguardar | qualquer | Aguardar, mantendo o gatilho técnico e mostrando o consenso |
| Sem sinal | compra, com ≥ 3 casas e potencial ≥ 15% | No radar: gatilho "fechamento acima da `MM21` (R$ valor)" |
| Sem sinal | demais | Sem sinal |

## Critérios de aceite
- [ ] Um teste por linha da matriz, com fixtures de técnico e opiniões, produz a decisão final e a frase de justificativa esperadas.
- [ ] Com uma única casa opinando, o consenso é "cobertura insuficiente" e a decisão segue o técnico.
- [ ] Com duas opiniões da mesma casa, só a mais recente conta.
- [ ] Com o status das opiniões diferente de `ok` e nenhuma opinião guardada, todos os ativos mostram "sem opinião de casas" e a página responde 200.
- [ ] O potencial exibido é `+15,0%` para alvo mediano de R$ 46,00 e preço de R$ 40,00.

## Invariantes de produção
- Todo ativo em "No radar" tem pelo menos 3 casas e potencial ≥ 15% exibidos.
- Todo ativo cuja decisão final difere da técnica exibe a frase de justificativa.

## Fora do escopo
- Pesos diferentes por casa conforme o histórico de acerto (depende da spec 072; vai para o backlog).
- Sugestão de tamanho de posição, stop ou alocação.
