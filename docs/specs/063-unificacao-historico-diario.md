---
id: 063
titulo: Saúde Técnica: Unificação de Histórico Diário
status: done
esforco: M
gaveta: saúde técnica
---

## Problema
Os coletores atuais repetem as mesmas requisições para a série histórica dos ativos, gerando redundância e sobrecarga nas APIs externas e diminuindo a saúde técnica. A telemetria já foi adicionada na Spec 056 e Spec 062, porém ainda não há dados suficientes nas tabelas de banco para realizar podas com base em estatísticas. Precisamos resolver a redundância de coleta que afeta os tempos medidos.

## Comportamento esperado
O sistema criará um cache compartilhado para cotações (intraday/diário), de forma que múltiplos coletores (ex. para Ibovespa, ativos comuns) consultem primeiramente essa fonte antes de efetuarem novas chamadas de API, garantindo menor duplicidade nas requisições ao `yfinance`. O painel não mudará visivelmente.

## Fontes de dados
Banco de Dados SQLite (Proxy local).

## Cálculos
Proxy: Caso um dado da série intraday já tenha sido puxado nos últimos X minutos, o coletor consome a versão em banco. Se não, atualiza-a.

## Critérios de aceite
- [ ] Implementar a tabela de banco de proxy de cotações para unificação no `database.py`.
- [ ] Atualizar ou abstrair um método comum no módulo `collectors.utils` para utilizar este cache histórico, retornando DataFrame em conformidade.
- [ ] O teste unitário deve garantir que não ocorram chamadas repetidas à API quando os dados estão em cache.

## Invariantes de produção
- A resposta em `/api/snapshot` e na renderização dos componentes front-end permanece exatamente a mesma; nenhuma funcionalidade visível muda, os tempos na instrumentação podem cair.

## Fora do escopo
Migrar todos os coletores de uma vez nesta spec inicial; apenas a primeira fatia que implementa a estrutura base (proxy/cache) e adapta um pequeno grupo de coletores de maior volume.
