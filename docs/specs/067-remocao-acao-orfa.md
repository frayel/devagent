---
id: 067
titulo: Poda do Painel Ação Órfã
status: ready
esforco: P
gaveta: poda
---

## Problema
O painel "Ação Órfã" (criado na Spec 038) visa identificar papéis que não registraram negócios recentes. No entanto, por analisar principalmente ações de alta liquidez, a lista resultante é quase sempre vazia, poluindo a interface com um estado nulo inútil e exigindo coleta e validação desnecessária da renderização no backend.

## Comportamento esperado
- O painel "Ação Órfã" é removido da aba "Alertas Intraday" do frontend (`app/templates/index.html`).
- O bloco correspondente no `/api/snapshot` é removido e os métodos de carregamento de dados não são mais chamados no `app/main.py` (`get_latest_detector_acao_orfa_data`).
- Componentes associados localizados via `grep -r "acao_orfa" app/` são excluídos ou não referenciados na `app/main.py`.

## Fontes de dados
Nenhuma (apenas remoção).

## Cálculos
Nenhum.

## Critérios de aceite
- [ ] O componente "Ação Órfã" não aparece na página inicial.
- [ ] O `/api/snapshot` não inclui a chave correspondente.
- [ ] Os testes associados a esse painel são removidos e a suite passa com sucesso.

## Invariantes de produção
- A chave correspondente (se existir) não será checada no auditor ou deve ser removida das verificações dele num PR futuro e independente.

## Fora do escopo
Remoção imediata da checagem na auditoria caso exista (deve ocorrer em um PR do auditor).
