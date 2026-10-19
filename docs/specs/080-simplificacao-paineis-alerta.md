---
id: 080
titulo: Poda: Simplificação de Painéis de Alerta
status: ready
esforco: P
gaveta: poda
---

## Problema
A seção "Alertas Intraday" pode ficar muito extensa e poluída visualmente, exibindo múltiplas tabelas vazias (ex: "Nenhum ativo...") quando não há alertas, o que desrespeita o princípio de "experiência limpa e objetiva".

## Comportamento esperado
Os painéis da aba/seção "Alertas Intraday" que dependem de listas e se encontram vazios não devem renderizar a estrutura completa do card e da tabela. Eles devem ser fundidos visualmente ou simplificados, ocultando a interface se não houver dados, ou substituídos por um único aviso consolidado "Sem alertas ativos no momento".

## Fontes de dados
Nenhuma nova.

## Cálculos
Nenhum cálculo adicional. Avaliação condicional (if lista vazia) na renderização do template Jinja2.

## Critérios de aceite
- [ ] Quando um radar de alerta (ex: Radar de Faca Caindo, Short Squeeze) retorna lista vazia, o card associado fica oculto (ou sumarizado).
- [ ] O componente obedece os testes de design vigentes.
- [ ] A API /api/snapshot ainda retorna a chave normalmente para o contrato do auditor, apenas o HTML deve mudar.

## Invariantes de produção
- A chave de cada painel de alerta continua no `/api/snapshot`.
- O layout não quebra ao ocultar os painéis no `make telas`.

## Fora do escopo
Remover ou alterar a lógica de coleta de dados de alertas no backend.
