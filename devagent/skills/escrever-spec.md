# Skill · Escrever uma boa especificação

Use no Passo 7, ao transformar uma issue em spec (Passo 6) e ao dividir uma spec grande. Spec nascida de issue traz o link da issue no *Problema*.

- **Ideia grande, entrega pequena.** Uma ideia ousada pode mudar o produto, mas a spec descreve só a primeira fatia visível dela. O resto da visão vai para o backlog, com link na seção *Fora do escopo*.
- **Uma pergunta do usuário por spec.** Se o título precisa de "e", provavelmente são duas.
- **Cabe em um PR de ~400 linhas** (sem testes e fixtures). Se não couber, divida antes de marcar `ready`.
- **Critérios de aceite testáveis sem internet.** "Mostra a variação em %" vira "dado o fixture X, a página contém `+1,23%`".
- **Fontes com plano B.** Toda fonte tem reserva ou degradação explícita ("se falhar, o painel mostra 'dado indisponível' e o resto da página funciona").
- **Números com contexto.** Toda probabilidade ou recomendação especifica tamanho de amostra, janela e método.
- **Fora do escopo explícito.** Diga o que não será feito, para a implementação não crescer.
- **Leia o contexto de domínio** indicado no índice do `PRODUTO.md` para evitar as armadilhas conhecidas.
- Numere com o próximo `NNN` livre em `docs/specs/`.

## Modelo

```markdown
---
id: NNN
titulo: ...
status: draft | ready | in-progress | done
esforco: P | M | G
---

## Problema
Qual pergunta do usuário isto responde.

## Comportamento esperado
O que aparece na tela, onde, e como se atualiza.

## Fontes de dados
URL, formato, frequência de coleta, limites de uso, plano B se a fonte cair.

## Cálculos
Fórmulas, janelas, tratamento de dados ausentes.

## Critérios de aceite
- [ ] verificáveis por teste automatizado
- [ ] ...

## Invariantes de produção
O que tem de ser verdade no site publicado, verificável sem ler o código.
Ex.: "valor a no máximo 1,5% de uma fonte independente", "soma dos pesos = 100%",
"última data do gráfico = dia útil mais recente". O auditor transforma cada
item numa checagem.

## Fora do escopo
```
