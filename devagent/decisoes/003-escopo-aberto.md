# ADR 003 · Escopo aberto e Passo 7 criativo

**Data:** 2026-09-27 · **Status:** aceito

## Contexto

O Passo 7 pedia ideias ordenadas por valor dividido por esforço. Na prática, isso favorece incrementos previsíveis e empurra o produto para o que todo painel financeiro já faz. O dono do projeto quer que o agente trate o sistema como produto próprio, com liberdade para mudar o escopo e propor funcionalidades originais.

## Decisão

- A seção 2 do `AGENTS.md` ganha o item *Escopo aberto*: o agente pode mudar o escopo, criar e expandir funcionalidades sem pedir permissão.
- O Passo 7 passa a exigir que pelo menos metade das ideias seja original, e a escolha da próxima pode seguir valor, originalidade, aprendizado ou potencial de transformar o produto.
- Ideias grandes entram como visão no backlog e são entregues em fatias, a primeira delas visível.
- Nova skill `docs/skills/descobrir-ideias.md`.

## O que não muda

Ciclos curtos, testes, a regra de continuidade, as regras de coleta, o aviso legal e a independência do auditor continuam protegidos (seção 13).

## Consequências

Mais variação no produto e specs mais ambiciosas. O risco é o agente abrir frentes demais: a regra de uma spec `ready` por vez e as fatias pequenas limitam isso, e a retrospectiva de cada execução registra o critério usado na escolha.
