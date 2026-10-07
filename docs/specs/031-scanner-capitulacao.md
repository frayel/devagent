---
id: 031
titulo: Scanner de Capitulação por Clímax de Volume
status: ready
esforco: G
---

## Problema
Em dias de forte queda, o investidor frequentemente tenta adivinhar o fundo (pegar a faca caindo). A pergunta real é: "Uma queda abrupta já achou um piso momentâneo de absorção?". Nenhum painel atual procura por clímax de volume intraday como sinal claro de capitulação no curtíssimo prazo.

## Comportamento esperado
Adicionar um novo painel à seção "Alertas Intraday" que lista ativos em queda acentuada intraday (>2%), mas que apresentaram nas últimas horas um pico extremo de volume associado a uma barra com longa cauda inferior (sinal de absorção por compradores).
O painel exibirá uma tabela curta contendo o Ticker, a queda percentual e um texto curto sobre o horário e o multiplicador do pico de volume recente.

## Fontes de dados
A fonte prioritária será `yfinance`, utilizando a API intraday (`interval=15m`, `range=1d`) das 30 ações de maior liquidez (mesma cesta base dos alertas de volume).
Se falhar ou retornar erros, degradar suavemente não exibindo nenhuma tabela, marcando como indisponível.

## Cálculos
Para os ativos rastreados, extrair os candles de 15m do dia:
- Filtrar ativos onde o preço atual está pelo menos 2% abaixo do fechamento de ontem.
- Calcular a média de volume das barras de 15m daquele ativo para o dia.
- Identificar se uma das barras mais recentes (últimas 2 horas) possui um volume pelo menos 3 vezes maior que a média do dia, e cuja diferença entre a mínima e o fechamento daquela barra (sombra inferior) represente a maior parte do corpo total da barra.
- Ativos que passarem nesse crivo de "Capitulação" entram na tabela de alerta.

## Critérios de aceite
- [ ] O script de coleta é testável e simula corretamente o cenário de capitulação offline usando mock respx (dados com clímax de volume e longa sombra inferior resultam na inclusão do ativo).
- [ ] Cenário onde não há capitulação retorna uma lista vazia e a UI mostra a mensagem adequada ("Nenhum clímax de capitulação detectado hoje").
- [ ] O novo painel é renderizado via macro `painel` dentro da tag respectiva na aba "Alertas Intraday".

## Invariantes de produção
A chave `scanner_capitulacao` será incluída em `/api/snapshot`.
O auditor validará que a chave existe e, se não vazia, apresentará o ativo que possui capitulação recente identificada pelo backend.

## Fora do escopo
Mostrar o gráfico de candles em 15 minutos dentro do dashboard. A indicação será estritamente tabular e textual.
