---
id: 069
titulo: Consultor · confiança medida pelo histórico de cada regra
status: ready
esforco: M
---

## Problema
O `PRODUTO.md` exige grau de confiança em toda recomendação, e a spec 068 entrega todas como "baixa: sem histórico medido". O usuário precisa saber, antes de decidir, o que costumou acontecer nas outras vezes em que a mesma regra disparou.

## Comportamento esperado
- Ao lado de cada recomendação do `/consultor`, uma linha de histórico, por exemplo: "Nas 134 vezes em que R5 disparou em ativos do Ibovespa nos últimos 2 anos, o ativo superou o Ibovespa em 58% dos casos nos 20 pregões seguintes (mediana +1,8 p.p.)."
- O grau de confiança passa a vir dessa medida (tabela em *Cálculos*), com o tamanho da amostra sempre visível.
- A seção "Como o consultor decide" ganha uma tabela com o histórico de cada regra.
- `/api/consultor` inclui, por regra: `n`, `taxa_acerto`, `excesso_mediano`, `janela_inicio`, `janela_fim`, `confianca`.

## Fontes de dados
- Histórico diário de 2 anos (`range=2y`) de cada ativo do universo e do `^BVSP`, pelo mesmo caminho da spec 068 (MT5 entrega 300 barras; para 2 anos, a reserva Yahoo `chart`). Recalculado uma vez por semana, no fim de semana, com cache no SQLite.
- Plano B: sem histórico de 2 anos, usa o que houver e mostra a janela real. Com `n < 30`, a confiança fica "baixa: amostra pequena (n = X)".

## Cálculos
- Para cada ativo e cada pregão `t` da janela com pelo menos 220 pregões anteriores, calcular os indicadores da spec 068 usando só dados até `t` (sem olhar o futuro) e aplicar as regras na mesma ordem.
- Evento: a regra disparou em `t` e não tinha disparado em `t-1` para o mesmo ativo (conta a entrada, não cada dia de permanência).
- Resultado do evento: retorno do ativo de `t` a `t+20` menos o retorno do Ibovespa no mesmo período. Eventos sem 20 pregões à frente ficam de fora.
- Acerto: para Comprar, excesso > 0; para Vender, excesso < 0; para Aguardar, mede-se o gatilho: percentual de eventos em que o gatilho foi atingido em até 20 pregões, e o excesso nos 20 pregões após o gatilho.
- Confiança: **alta** com `n ≥ 100` e taxa de acerto ≥ 60%; **média** com `n ≥ 30` e taxa ≥ 55%; **baixa** nos demais casos. Os limiares são constantes nomeadas.
- Registrar no texto que eventos de ativos diferentes no mesmo dia não são independentes.

## Critérios de aceite
- [ ] Com um fixture sintético em que R5 dispara 3 vezes e os retornos futuros são conhecidos, `n`, `taxa_acerto` e `excesso_mediano` batem com os valores calculados no teste.
- [ ] Um evento a menos de 20 pregões do fim da série não entra na contagem.
- [ ] Um teste prova a ausência de olhar o futuro: alterar preços posteriores a `t` não muda a decisão em `t`.
- [ ] Com `n = 12`, a confiança exibida é "baixa: amostra pequena (n = 12)".
- [ ] Com a coleta de 2 anos falhando, a página responde 200, as recomendações aparecem e a linha de histórico diz "histórico indisponível".

## Invariantes de produção
- Toda recomendação Comprar, Vender ou Aguardar no `/api/consultor` tem `n` e `confianca` preenchidos.
- `janela_fim` é no máximo 7 dias corridos anterior à data atual.

## Fora do escopo
- Otimizar limiares das regras com base no histórico (risco de sobreajuste; se feito no futuro, exige amostra de validação separada).
- Custos de corretagem e impostos.
- Placar das recomendações efetivamente emitidas pelo consultor (spec 072).
