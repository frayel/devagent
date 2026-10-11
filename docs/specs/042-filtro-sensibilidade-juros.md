---
id: 042
titulo: Filtro de Sensibilidade a Juros
status: done
esforco: M
---

## Problema
Quais ações da bolsa brasileira estão mais sensíveis aos movimentos diários da curva de juros futura (DI)? O investidor precisa saber quais ativos do varejo, construção e tecnologia (tipicamente dependentes de juros) reagem imediatamente a dias de forte alta ou queda no DI Futuro (DI1F27 ou similar). Isso ajuda a entender de onde vem o fluxo do mercado num dia de "juros estressados".

## Comportamento esperado
Adicionar um novo painel na grade, na visão "Sentimento & Risco", contendo uma pequena tabela. O painel lista o Top 3 de ações (dentre uma cesta focada em sensíveis a juros como varejo/construção/tech) que apresentaram a maior correlação inversa com os juros futuros nos últimos 30 pregões, juntamente com sua correlação atual.

## Fontes de dados
- Yahoo Finance (para ativos do Ibovespa e DI Futuro). Ticker sugerido para DI curto: `DI1F27.SA` (caso não ache, usar ETF fixo atrelado a juros tipo `B5MB11.SA` ou similar, ou taxa cambial como proxy estendida de risco se necessário).
- Se yfinance falhar, o painel exibe um aviso "dado indisponível", degradando de forma segura.

## Cálculos
Para os últimos 30 pregões, correlacionar os retornos percentuais diários (usando fechamentos) das principais ações do varejo/construção contra os retornos do ativo de juros.
- O Top 3 com maior correlação *inversa* (mais negativa) é exibido, mostrando o grau de sensibilidade.
- Coleta baseada no método do coletor de `dolar_correlation`.

## Critérios de aceite
- [ ] O coletor salva as maiores correlações negativas em um cache específico (`sensibilidade_juros_cache`).
- [ ] O banco de demonstração (seed) instancia dados fictícios de demonstração.
- [ ] A interface da página carrega os dados e a tabela mostra corretamente os símbolos e números (ex: `-0,85`).
- [ ] Quando a fonte falha (ex: usando `yahoo_falso.py` adaptado), o painel degrada sem quebrar a UI, mostrando "indisponível".
- [ ] O contrato `/api/snapshot` reflete os dados corretos no json (`sensibilidade_juros`).

## Invariantes de produção
- A chave do snapshot (`sensibilidade_juros`) não expõe erros ou traces na produção.
- Todos os números decimais estão no formato Pt-BR (ex: `-0,75`).
- O painel exibe as informações apenas de correlações inversas (menores que 0).

## Fora do escopo
Mapeamento de todos os contratos DI existentes. Vamos usar um contrato fixo de alta liquidez como proxy para juros futuros na B3.
