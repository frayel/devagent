---
id: 081
titulo: Rastreador de Correlação com Juros Futuros (DI)
status: ready
esforco: M
---

## Problema
O Ibovespa frequentemente reage ou antecipa movimentos na curva de juros futuros (DI). O investidor não consegue ver de forma consolidada se o rali atual do mercado é suportado por uma queda nos juros ou se os dois estão descorrelacionados (sinal de alerta macro).

## Comportamento esperado
Adicionar um novo painel na página inicial que mostra a correlação intradiária e dos últimos 5 pregões entre o Ibovespa e o DI (contrato longo, ex: F27/F29). O painel exibirá o status "Correlacionado" (quando se movem inversamente de forma consistente) ou "Descolado" (divergência), acompanhado de um indicador visual de força.

## Fontes de dados
- Yahoo Finance ou Brapi (para o ticker correspondente do DI, a definir na implementação).
- Se a fonte falhar, o painel oculta o indicador e não derruba o resto da página.

## Cálculos
Cálculo de correlação de Pearson sobre os retornos (fechamentos ou preços atuais) nos períodos definidos. Uma correlação negativa forte (<-0.7) indica comportamento normal (juro sobe, bolsa cai), enquanto valores próximos de 0 ou positivos apontam divergência.

## Critérios de aceite
- [ ] O backend coleta e armazena os dados do DI.
- [ ] O serviço calcula a correlação com o Ibovespa.
- [ ] O painel é renderizado na tela e ocultado adequadamente quando os dados estiverem indisponíveis.
- [ ] O novo indicador é exposto no JSON do contrato `/api/snapshot`.

## Invariantes de produção
- A chave do painel `correlacao_di` deve existir no `/api/snapshot`.

## Fora do escopo
- Construção de gráficos dinâmicos da curva inteira de juros.
