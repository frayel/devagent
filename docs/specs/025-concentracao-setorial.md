---
id: 025
titulo: Índice de Concentração Setorial
status: in-progress
esforco: M
---

## Problema
O capital está fluindo para um único setor hoje? O investidor precisa saber se a alta do índice é puxada por um setor específico (como commodities ou bancos) ou se é um movimento generalizado.

## Comportamento esperado
No painel de visão macro, exibe o setor com maior volume financeiro e o setor com maior variação percentual positiva no dia.
- Exibe o nome do setor líder.
- Exibe a variação percentual média dos ativos daquele setor.

## Fontes de dados
- **brapi.dev:** Consulta a lista de ações ativas e agrupa por setor (ou utiliza uma lista estática de mapeamento de tickers por setor se a API não fornecer o setor diretamente).
- **yfinance:** Consulta os dados de variação diária caso a API da brapi falhe.
- Plano B: degrada graciosamente e não exibe o alerta de concentração setorial.

## Cálculos
- Mapeia os 30 principais ativos de alta liquidez para seus respectivos setores.
- Coleta a variação diária atual para esses tickers.
- Calcula a média simples da variação para cada grupo setorial.
- Identifica o setor com a maior variação média positiva.

## Critérios de aceite
- [ ] O banco de dados SQLite armazena o cache deste coletor (`concentracao_setorial_cache`).
- [ ] Quando um setor se destaca, exibe o nome do setor e sua variação média.
- [ ] Falha das fontes (brapi.dev e yfinance) captura a exceção, não quebra a página e exibe painel vazio ou com erro amigável.
- [ ] Testes sem internet usando mock do httpx verificam o cálculo da concentração.

## Invariantes de produção
- A chave `concentracao_setorial` existe dentro de `paineis` no `/api/snapshot`.
- O valor possui `coletado_em`, `fonte`, setor em destaque e a variação setorial.

## Fora do escopo
- Acompanhamento tick a tick em tempo real (apenas o snapshot da coleta periódica).
- Mostrar todos os setores (apenas o líder/destaque).
