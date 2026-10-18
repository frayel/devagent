---
id: 065
titulo: Análise de Assimetria Risco/Retorno
status: ready
esforco: P
---

## Problema
Qual ativo está mais próximo do seu fundo dos últimos 30 dias do que do seu topo? O usuário quer encontrar assimetria onde a perda teórica até o suporte recente é muito menor que o ganho até a máxima recente.

## Comportamento esperado
Adicionar um novo painel na interface que mostre o top 3 ativos que estão mais próximos percentualmente de sua mínima dos últimos 30 dias do que da sua máxima (distância da mínima <= 2% e distância da máxima >= 10%).

## Fontes de dados
Banco de Dados Histórico Local (Cache/Proxy) `historico_diario_cache` ou fallback para yfinance (endpoint spark 30d).

## Cálculos
Para os ativos de alta liquidez:
- Obter mínima de 30 dias (min_30) e máxima de 30 dias (max_30).
- Verificar se `(atual - min_30) / min_30 <= 0.02`.
- Verificar se `(max_30 - atual) / atual >= 0.10`.
- Ordenar os que atendem aos critérios pelo menor distanciamento da mínima.

## Critérios de aceite
- [ ] O painel é exibido no frontend corretamente com as ações identificadas.
- [ ] O endpoint `/api/snapshot` inclui a chave `assimetria_risco_retorno`.
- [ ] Testes unitários para validar a lógica matemática de seleção e distância.

## Invariantes de produção
- A chave `assimetria_risco_retorno` no JSON deve conter no máximo 3 itens e cada item deve representar um ativo que realmente esteve próximo da sua mínima nos últimos 30 dias.

## Fora do escopo
Criar novos gráficos visuais neste painel (será apenas uma lista em texto ou tabela simples).
