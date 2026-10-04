---
id: 019
titulo: Modo Só Sinais (Experiência)
status: ready
esforco: P
---

## Problema
Como ver rapidamente se o mercado está verde ou vermelho no celular, sem gráficos? O redesign foca na tomada de decisão em 5 segundos, escondendo o ruído analítico.

## Comportamento esperado
Adicionar um botão "Só Sinais" no filtro superior (junto com Todos, Macro, Micro). Quando ativado, os gráficos e tabelas detalhadas somem, dando lugar a uma interface de alto contraste exibindo apenas o pulso do mercado:
- O card do Ibovespa exibe apenas o valor e variação em fonte enorme.
- O card de Tendência exibe os sinais (▲ Alta, ▼ Baixa) centralizados.
- O Apetite a Risco exibe apenas o texto de status (ex: Tomando Risco, Defensivo).
Toda a lógica usa CSS (`display: none` para o ruído, alteração de layout) e JavaScript simples baseado na classe do container (semelhante ao filtro Macro/Micro).

## Fontes de dados
Nenhuma fonte nova, utiliza os dados já cacheados (Ibovespa, Tendência e Apetite a Risco).
Fallback: se faltarem os dados subjacentes, o layout de erro padrão dos componentes já lida com o estado.

## Cálculos
Nenhum cálculo adicional necessário, é estritamente uma camada de apresentação.

## Critérios de aceite
- [ ] O botão 'Só Sinais' existe no grupo de filtros.
- [ ] Ao clicar no botão, a interface esconde os gráficos de linha do Ibovespa e tabelas.
- [ ] O card de Apetite a Risco aumenta o tamanho do status quando no modo 'Só Sinais'.
- [ ] Verificável por captura de tela usando a configuração 'celular' do playwright.

## Invariantes de produção
- A soma dos pesos do filtro se mantém a mesma.
- As informações no contrato do JSON de snapshot `/api/snapshot` permanecem inalteradas.

## Fora do escopo
Não altera a lógica de coleta de nenhum dado no backend. Não altera o visual do modo desktop.
