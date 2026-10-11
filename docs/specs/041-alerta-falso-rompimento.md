---
id: 041
titulo: Alerta de Falso Rompimento
status: done
esforco: M
---

## Problema
O investidor que acompanha o mercado intraday frequentemente cai em "bull traps" (armadilhas de alta), comprando ações que rompem a máxima do dia anterior logo após a abertura, apenas para ver o preço reverter e fechar em forte queda acompanhado de alto volume. Nenhum site mostra esse padrão de exaustão em tempo real.

## Comportamento esperado
Adicionar um novo painel à seção "Alertas Intraday" listando até 3 ações de alta liquidez que satisfaçam a condição. O painel deve usar as classes padrão da grade (ex: `span-4`) e ocultar-se via filtros se não houver dados. Se a API falhar, exibir "Dados indisponíveis". O contador da cadência de experiência deve ser zerado em `docs/STATE.md` se essa ideia de organização fosse implementada, mas como a escolhida é apenas um alerta, ele não será modificado no passo 7.

## Fontes de dados
- Yahoo Finance (`yfinance`) no endpoint `chart` (intervalo de 1 dia, range de 2 dias) para 30 tickers de alta liquidez.
- Limites de uso: nativo do yfinance, com cache obrigatório no banco SQLite (tabela `falso_rompimento_cache`).
- Plano B: degradação suave ("Dados indisponíveis").

## Cálculos
Para cada ticker:
1. Obter a máxima e o volume médio do dia anterior (D-1).
2. Obter a máxima, o preço atual (fechamento/último) e o volume do dia atual (D-0).
3. Condição: Máxima D-0 > Máxima D-1 E Preço Atual D-0 < Preço Fechamento D-1 E Volume D-0 > Volume Médio D-1.

## Critérios de aceite
- [ ] O script de coleta calcula corretamente o falso rompimento com base em um fixture mockado.
- [ ] A tabela no banco de dados armazena o símbolo e o volume relativo.
- [ ] O painel é renderizado apenas com CSS padrão (`tema.css`) e os dados aparecem corretamente.

## Invariantes de produção
- A chave `falso_rompimento` deve estar presente no dicionário `/api/snapshot`.
- O ativo listado no painel não pode ter variação percentual positiva no dia em fontes independentes.

## Fora do escopo
- Gráficos intraday de candlestick para ilustrar o rompimento.
- Notificações por e-mail, SMS ou WebSocket.
