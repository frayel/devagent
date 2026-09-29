# PRODUTO.md · NOME DO PRODUTO

> **Camada do projeto.** Este arquivo diz **o que** você constrói. **Como** você trabalha está em `devagent/CICLO.md`. Em caso de dúvida, o `CICLO.md` manda no processo e este arquivo manda no produto.

## 1. O produto

Para quem é, que perguntas responde, o que o diferencia.

### Escopo aberto

O que o agente pode mudar sem pedir permissão, e até onde vai a ousadia.

### Transparência (protegido)

O que toda informação exibida precisa mostrar (fonte, data, método, confiança) e qualquer aviso obrigatório no rodapé.

## 2. Stack

| Camada | Escolha | Motivo |
|---|---|---|

Mudanças de stack exigem um ADR em `docs/decisions/` antes do código.

**Contrato com o núcleo.** O que `make verify`, `make smoke` e `make audit` fazem neste stack.

## 3. Estrutura do código

## 4. Roteiro inicial

A primeira spec (`001-...`) é o MVP e deve conter uma única informação, mais a fundação: health check, template com o aviso obrigatório, configuração de deploy, CI e `/api/snapshot`.

Sugestões de incrementos (ponto de partida, não plano).

## 5. Regras de coleta de dados (protegido)

## 6. Checklist do produto

Soma-se ao checklist de `devagent/CICLO.md`.

## 7. Convenções

Formato de números, datas, fuso, idioma, cores.

## 8. Onde procurar ideias

Territórios do domínio e concorrentes para testar originalidade.

## 9. Auditoria: o que é verdade neste domínio

Fontes independentes, perguntas do domínio, um exemplo de bom achado e a agenda dos workflows de auditoria.

## 10. Configuração do produto

| Variável | Onde | Uso |
|---|---|---|

## 11. Índice do projeto e itens protegidos

| Arquivo | Para que serve | Leia quando |
|---|---|---|

Itens deste arquivo que só podem ser mantidos ou reforçados: a transparência da seção 1 e as regras de coleta da seção 5.
