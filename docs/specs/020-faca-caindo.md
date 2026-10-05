---
id: 020
titulo: Radar de Faca Caindo (Quedas Consecutivas)
status: done
esforco: P
---

## Problema
O investidor quer saber quais ações estão caindo consecutivamente sem nenhum repique, podendo indicar pânico ou capitulação. Isso responde à pergunta: "O que está derretendo há vários dias?"

## Comportamento esperado
Na tela inicial, um novo painel pequeno exibindo o top 3 das ações com mais dias consecutivos de queda. O painel deve usar as macros visuais já estabelecidas no `app/templates/componentes.html`.
Se nenhuma ação tiver 3 ou mais quedas consecutivas, exibir "Nenhuma ação em queda livre".

## Fontes de dados
- **yfinance:** Cotações diárias dos últimos 10 pregões para o universo de 30 ações de maior liquidez (reaproveitar lista).
- Plano B: se a fonte falhar, exibir estado "indisponível".

## Cálculos
- Para cada ação, contar quantos dias consecutivos o fechamento atual é menor que o fechamento anterior, começando de hoje para trás.
- Filtrar ações com >= 3 quedas consecutivas.
- Ordenar pelas que têm mais dias e, em caso de empate, pela maior variação negativa acumulada.

## Critérios de aceite
- [x] O banco de dados SQLite armazena o cache deste coletor (`faca_caindo_cache`).
- [x] Quando pelo menos um papel tem >= 3 quedas consecutivas, a lista mostra o papel e a quantidade de dias.
- [x] Falha da fonte yfinance captura a exceção, o componente exibe estado "indisponível" sem quebrar a página.

## Invariantes de produção
- A chave `faca_caindo` existe dentro de `paineis` no `/api/snapshot`.
- O valor possui `coletado_em`, `fonte` e a lista `alertas`.

## Fora do escopo
- Recomendar compra de ativos em queda.
- Enviar alertas de e-mail ou push.
