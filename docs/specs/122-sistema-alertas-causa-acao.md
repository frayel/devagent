---
id: 122
titulo: Causa e ação no painel do sistema
status: ready
esforco: P
gaveta: saúde técnica
aceite: tests/test_aceite_122.py
---

## Problema

Como o dono do produto descobre o que fazer com os alertas da página de sistema e acompanha a resolução?

A página `/sistema` lista alertas, mas deixa o dono do produto adivinhar o que fazer. Na leitura de 23/10/2026 havia quatro ao mesmo tempo. Para cada um, a tela dá o texto do erro e mais nada: não diz se o defeito é do pedido ou do servidor externo, nem o que seria preciso fazer.

## Comportamento esperado

### Todo item pendente diz causa e ação

`Item` (`app/services/sistema.py`) ganha os campos `causa` e `acao`, curtos (uma frase cada), e o JSON de `/api/sistema` (que `devagent/saude.py` lê) os repete. A página os mostra abaixo do resumo, em *Atenção* e *Problema*. Regras de preenchimento, com a origem do defeito dita explicitamente:

- **Pedido errado** (HTTP 400, 404 em símbolo específico, 422): causa "pedido inválido ou ativo desconhecido (HTTP N)", ação "corrigir o pedido no coletor X; o servidor está respondendo".
- **Fonte fora do ar** (rede, 5xx, 429, 401, 403): causa "fonte indisponível ou recusando a chave (HTTP N)", ação "aguardar, ou conferir a chave no Render".
- **Banco ou esquema** (erro com `relation`, `column`, `does not exist`): causa "esquema do banco incompleto", ação "falta migração; ver spec do Consultor".
- **Integração sem chamadas**: causa "configurada, mas nunca chamada", ação "verificar o pipeline que a usa".
- Erro desconhecido: causa "causa não classificada", ação "ver o detalhe e abrir issue".

## Fontes de dados

Só dados que `/sistema` já tem. Nenhuma requisição nova.

## Critérios de aceite

- [ ] Cada categoria de falha (pedido errado, fonte fora do ar, esquema, sem chamadas, desconhecido) recebe causa e ação esperadas (testes com itens de fixture).
- [ ] `/sistema` mostra causa e ação para itens em *Atenção* e *Problema*, sem rolagem horizontal em 390 px.
- [ ] `/api/sistema` traz `causa` e `acao` por pendência, e o núcleo (`devagent/saude.py`) continua lendo contratos antigos sem esses campos.
- [ ] Nenhum segredo aparece nos novos campos.

## Invariantes de produção

- Nenhum item de `/sistema` em *Atenção* ou *Problema* aparece sem causa e ação.

## Fora do escopo

- Monitorar idade dos alertas (spec 123).
- Agente abrir issue com a causa (spec 124).
- Corrigir a causa de cada alerta (specs 084, 090, 091 e 092).
