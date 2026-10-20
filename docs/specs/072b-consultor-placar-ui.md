---
id: 072b
titulo: Consultor · placar de acertos e avaliações na UI
status: ready
esforco: M
---

## Problema
Complementa a spec 072a. Agora que o histórico é gravado, precisamos calcular a performance das recomendações passadas e exibi-las para o usuário ganhar confiança nas decisões do consultor.

## Comportamento esperado
- Nova seção "Placar" no `/consultor`, com três tabelas:
  - **Consultor:** por decisão final (Comprar, Vender, Aguardar, No radar): número de recomendações avaliadas, taxa de acerto, excesso mediano sobre o Ibovespa em 5 e 20 pregões.
  - **Regras técnicas:** o mesmo, por regra R1 a R5, com as recomendações emitidas de fato.
  - **Casas de análise:** por casa com pelo menos 5 opiniões avaliadas: taxa de acerto e excesso mediano em 20 pregões.
- Em cada linha, o tamanho da amostra; com `n < 10`, "amostra insuficiente" no lugar da taxa.
- Para Aguardar: percentual de gatilhos atingidos em até 20 pregões e o excesso nos 20 pregões após o gatilho.
- Se a API indicar `armazenamento` como `sqlite_efemero`, a seção "Placar" mostra: "Histórico efêmero: o placar recomeça a cada reinício do servidor."
- A resposta de `/api/consultor` inclui os dados do `placar`.

## Fontes de dados
- Os registros armazenados (Postgres ou SQLite) pela lógica da spec 072a.

## Cálculos
- **Avaliação.** Para cada registro de mudança com pelo menos 5 ou 20 pregões à frente: excesso = retorno do ativo − retorno do Ibovespa entre o fechamento da data do registro e o fechamento 5 ou 20 pregões depois. Acerto: Comprar e No radar com excesso > 0; Vender com excesso < 0; opinião de casa: compra com excesso > 0, venda com excesso < 0, neutro com |excesso| ≤ 2 p.p.

## Critérios de aceite
- [ ] Com um fixture de 3 mudanças de decisão e preços futuros conhecidos, a taxa de acerto e o excesso mediano batem com os valores calculados no teste.
- [ ] Uma casa com 4 opiniões avaliadas não aparece na tabela de casas.
- [ ] Se o armazenamento for `sqlite_efemero`, o HTML inclui o texto de aviso de histórico efêmero.

## Invariantes de produção
- Toda linha do placar mostra `n`, e nenhuma taxa é exibida com `n < 10`.
- Se `armazenamento` for `sqlite_efemero`, o aviso de histórico efêmero aparece na página.

## Fora do escopo
- Lógica de persistência ou conexão unificada (feita na spec 072a).
