# Achados do auditor

Um arquivo por defeito, com nome `AAAA-MM-DD-slug.md`. Depois do merge, o workflow `auditoria-achados.yml` abre uma issue para cada achado com `status: aberto` (severidade `alta` recebe o label `producao-incorreta`).

O auditor muda `status` para `resolvido` quando confirma a correção em produção. O desenvolvedor não edita estes arquivos: ele corrige o código e fecha a issue com `Closes #N`.

## Modelo

```markdown
---
id: 2026-09-28-ibovespa-dado-de-teste
severidade: alta | media | baixa
painel: ibovespa
status: aberto | resolvido
visto_em: 2026-09-28T14:37-03:00
---

# Ibovespa exibe 130.000 pontos, valor do fixture de teste

## O que o investidor vê
Valor, texto ou comportamento, copiado da página, com horário.

## O que deveria ver
O valor correto e de onde ele vem: duas fontes independentes, com URL e horário.

## Evidência
Números lado a lado, screenshot ou trecho do HTML, arquivo do repositório relacionado.

## Como reproduzir
Comando ou passos para ver o defeito.

## Invariante proposta
Regra verificável por código que teria pego este defeito, ou "não se aplica".
```
