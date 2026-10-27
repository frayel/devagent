---
id: 093
titulo: Resolução guiada para alertas da página de sistema
status: draft
esforco: M
gaveta: saúde técnica
aceite: tests/test_aceite_093.py
revisada: 2026-10-25
---

## Problema

Como o dono do produto descobre o que fazer com os alertas da página de sistema e acompanha a resolução?

A página `/sistema` lista alertas, mas deixa o dono do produto adivinhar o que fazer. Na leitura de 23/10/2026 havia quatro ao mesmo tempo: `consultor_opinioes: relation "consultor_llm_uso" does not exist`, Yahoo Finance com 404, brapi com 400 e Gemini *Inativo*. Para cada um, a tela dá o texto do erro (às vezes só a URL) e mais nada: não diz se o defeito é do pedido ou do servidor externo, nem o que seria preciso fazer, nem se o ciclo do agente já está tratando.

Duas lacunas no ciclo:

- `devagent/saude.py` só abre a issue `sistema-com-problema` para itens de nível *Problema*. Item em *Atenção* pode ficar semanas na tela sem que nenhum passo do ciclo o veja (foi o caso dos quatro acima, todos em *Atenção* ou *Inativo*).
- A issue não diz quando o alerta nasceu nem há quanto tempo persiste.

As causas dos quatro alertas de hoje têm specs próprias (084, 090, 091, 092). Esta spec é o mecanismo para que o próximo alerta não precise ser percebido por acaso.

## Comportamento esperado

### 1. Todo item pendente diz causa e ação

`Item` (`app/services/sistema.py`) ganha os campos `causa` e `acao`, curtos (uma frase cada), e o JSON de `/api/sistema` (que `devagent/saude.py` lê) os repete. A página os mostra abaixo do resumo, em *Atenção* e *Problema*. Regras de preenchimento, com a origem do defeito dita explicitamente:

- **Pedido errado** (HTTP 400, 404 em símbolo específico, 422): causa "pedido inválido ou ativo desconhecido (HTTP N)", ação "corrigir o pedido no coletor X; o servidor está respondendo".
- **Fonte fora do ar** (rede, 5xx, 429, 401, 403): causa "fonte indisponível ou recusando a chave (HTTP N)", ação "aguardar, ou conferir a chave no Render".
- **Banco ou esquema** (erro com `relation`, `column`, `does not exist`): causa "esquema do banco incompleto", ação "falta migração; ver spec do Consultor".
- **Integração sem chamadas**: causa "configurada, mas nunca chamada", ação "verificar o pipeline que a usa".
- Erro desconhecido: causa "causa não classificada", ação "ver o detalhe e abrir issue".

### 2. Há quanto tempo

Cada item pendente mostra "desde dd/mm HH:MM" (primeira leitura em que apareceu com esse nível). O monitor (`app/collectors/sistema.py`) guarda essa primeira vez por chave do item (grupo e nome) na memória do processo e no banco de dados (usando a tabela unificada `snapshots_paineis` sob o painel `sistema_alertas` para persistência), para sobreviver a um reinício. Item que volta a *OK* é removido da persistência.

### 3. O ciclo do agente enxerga *Atenção* persistente

`devagent/saude.py` passa a tratar como pendente de ação, além dos *Problema*, todo item em *Atenção* ou *Inativo-inesperado* que persiste por 24 h (campo `desde`). A issue `sistema-com-problema` lista esses itens separados dos problemas, com causa, ação e idade. A chave que decide se há issue nova considera o conjunto de itens e continua estável entre leituras (o texto muda, a chave não). Item de *Atenção* abaixo de 24 h só aparece no resumo, sem issue. A regra de "Inativo esperado" (variável opcional ausente) não vira issue.

### 4. Os alertas somem quando o defeito some

Depois de uma correção, o item deixa de aparecer na leitura seguinte; a issue é fechada pelo caminho já existente quando o conjunto de pendências zera. O corpo da issue diz a spec que trata cada item quando houver uma (campo opcional `spec` do item, preenchido pela implementação das 084, 090, 091 e 092).

## Fontes de dados

Só dados que `/sistema` já tem. Nenhuma requisição nova.

## Critérios de aceite

- [ ] Cada categoria de falha (pedido errado, fonte fora do ar, esquema, sem chamadas, desconhecido) recebe causa e ação esperadas (testes com itens de fixture).
- [ ] `/sistema` mostra causa, ação e "desde dd/mm HH:MM" para itens em *Atenção* e *Problema*, sem rolagem horizontal em 390 px.
- [ ] `/api/sistema` traz `causa`, `acao` e `desde` por pendência, e o núcleo (`devagent/saude.py`) continua lendo contratos antigos sem esses campos.
- [ ] Item em *Atenção* há 25 h gera pendência de ação na issue; há 23 h, não.
- [ ] A chave da issue não muda quando só o texto ou a hora do erro mudam.
- [ ] Item que volta a *OK* é removido da persistência em `snapshots_paineis`; um reinício mantém o `desde` dos que continuam.
- [ ] Nenhum segredo aparece nos novos campos.

## Invariantes de produção

- Nenhum item de `/sistema` em *Atenção* ou *Problema* aparece sem causa e ação.
- Item em *Atenção* há mais de 24 h está citado em uma issue `sistema-com-problema` aberta.

## Fora do escopo

- Corrigir a causa de cada alerta (specs 084, 090, 091 e 092).
- Notificar por e-mail ou celular.
- Resolver automaticamente alertas sem spec.


## Revisão

A spec era grande demais (tocava em `test_sistema.py`, `test_api_snapshot.py`, `test_banco.py`, e `devagent/test_saude.py`) e foi dividida no Passo 4 em:
- **122**: Causa e ação no painel do sistema
- **123**: Idade dos alertas
- **124**: Agente enxerga alertas persistentes
