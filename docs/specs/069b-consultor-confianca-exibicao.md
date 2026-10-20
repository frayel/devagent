---
id: 069b
titulo: Consultor confiança · integração no frontend e API
status: done
esforco: P
---

## Problema
A tabela calculada com o histórico de confiança do consultor (spec 069a) precisa chegar até a visualização final do usuário e a API.

## Comportamento esperado
- A UI do `/consultor` e o JSON do `/api/consultor` adicionam para cada regra e recomendação a métrica histórica de confiança extraída da tabela criada na spec 069a (`n`, `taxa_acerto`, `excesso_mediano`, `janela_inicio`, `janela_fim`, `confianca`).
- A seção "Como o consultor decide" na interface ganha uma coluna ou tabela para os valores precalculados.
- Ao lado de cada recomendação do `/consultor`, surge uma linha de histórico, por exemplo: "Nas 134 vezes em que R5 disparou em ativos do Ibovespa nos últimos 2 anos, o ativo superou o Ibovespa em 58% dos casos nos 20 pregões seguintes (mediana +1,8 p.p.)."
- Confiança é: alta (n >= 100, taxa >= 60%), média (n >= 30, taxa >= 55%), e baixa no resto.
- Se `n < 30`, a confiança fica "baixa: amostra pequena (n = X)".
- Se o banco de dados de histórico falha, a linha deve dizer "histórico indisponível" e responder HTTP 200.

## Invariantes de produção
- Toda recomendação (Comprar, Vender ou Aguardar) em `/api/consultor` tem `n` e `confianca`.
- `janela_fim` não é mais que 7 dias corridos anteriores ao atual.

## Critérios de aceite
- [ ] O `/api/consultor` emite a chave `confianca` e metadados no dict de todas as recomendações.
- [ ] A UI exibe corretamente a mensagem de fallback de histórico se os dados falham.
- [ ] A tela exibe o aviso formatado sobre as métricas dos últimos X anos da regra correspondente.
