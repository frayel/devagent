---
id: 085
titulo: Consultor explica por que não há opiniões, em vez de "Nenhuma opinião recente"
status: ready
esforco: P
gaveta: experiência
aceite: tests/test_aceite_085.py
revisada: 2026-10-24
---

## Problema

Pergunta do usuário: Por que a tabela de opiniões de especialistas do Consultor não mostra nenhuma opinião?

A tabela de opiniões de especialistas do Consultor mostra a linha "Nenhuma opinião recente." em qualquer situação: pipeline quebrado, chave ausente, cota esgotada, fila vazia ou extração que rejeitou tudo na validação. Quem olha não sabe se o produto funciona e simplesmente não há opinião, ou se há um defeito. O aviso que existe hoje (`dados.opinioes_status`) só aparece quando já há uma linha de status diferente de `ok`; antes da primeira extração, ou com status `ok` e zero opiniões, a tela não diz nada.

Depende da spec 084 (o pipeline precisa funcionar no Postgres para existir o que mostrar).

## Comportamento esperado

No lugar de "Nenhuma opinião recente.", a tabela mostra uma linha com o motivo e o que acontece a seguir, escolhido por esta ordem:

1. Sem `GEMINI_API_KEY`: "Extração desligada: falta a chave do Gemini."
2. Status `cota`: "Cota diária do Gemini esgotada (N de M chamadas). Volta amanhã."
3. Status `erro` ou `invalido`: "A última extração falhou às HH:MM (motivo)."
4. Nunca houve extração: "Aguardando a primeira extração. Há N matérias na fila."
5. Extração `ok`, fila com matérias a processar: "N matérias na fila, a próxima extração é na próxima rodada."
6. Extração `ok`, fila vazia, nenhuma opinião nos últimos 30 dias: "Nenhuma matéria dos feeds citou ativos do Ibovespa com opinião de casa de análise nos últimos 30 dias."
7. Houve opiniões e todas foram descartadas na validação (trecho ou preço-alvo ausente da matéria): "N opiniões extraídas foram descartadas porque o trecho citado não está na matéria."

Em todos os casos aparece abaixo da tabela a linha "Última extração: dd/mm HH:MM BRT · matérias processadas em 24 h: N · opiniões gravadas em 7 dias: N · descartadas: N".

"Recente" passa a ter definição: opiniões extraídas ou publicadas nos últimos 30 dias (a mesma janela de `get_opinioes_ativos`). `get_opinioes_recentes` respeita essa janela e o título da seção diz "últimos 30 dias".

Os contadores ficam em `consultor_opinioes_status` (colunas novas `ultima_extracao_em`, `materias_processadas`, `opinioes_gravadas`, `descartadas`), criadas nos dois backends e cobertas pelo teste de paridade da spec 084. `extrair_opinioes` atualiza os contadores a cada rodada, inclusive quando não há matérias.

## Fontes de dados

Só o banco do próprio Consultor. Nenhuma requisição nova.

## Critérios de aceite

- [ ] Para cada um dos sete casos, dado o estado fixture (variável de ambiente, linha de status, fila, opiniões), `GET /consultor` contém o texto do caso e não contém "Nenhuma opinião recente."
- [ ] Com opiniões nos últimos 30 dias, a tabela lista as opiniões e a linha de última extração aparece.
- [ ] Opinião com mais de 30 dias não aparece.
- [ ] `/api/consultor` devolve `opinioes_diagnostico` com o código do caso (`sem_chave`, `cota`, `erro`, `aguardando`, `fila`, `sem_materias`, `descartadas`) e os contadores.
- [ ] A tela em 390 px não tem rolagem horizontal (mensagem dentro da célula com `colspan`).

## Invariantes de produção

- `/consultor` nunca mostra a frase "Nenhuma opinião recente." (o texto deve ser sempre substituído por uma das 7 mensagens explicativas, nunca aparecendo com o sufixo ou complemento).

## Fora do escopo

- Reprocessar matérias descartadas.
- Mudar a validação das opiniões.
