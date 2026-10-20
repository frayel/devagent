---
id: 070b
titulo: Consultor · opiniões de casas de análise (extração, validação e exibição)
status: ready
esforco: M
---

## Problema
O usuário quer saber o que as casas de análise dizem sobre cada ação do Ibovespa, sem ler dezenas de matérias. Estas opiniões aparecem em portais de notícia, em texto livre. Esta spec (segunda parte da spec 070) é responsável por extrair as opiniões das matérias da fila usando LLM, validá-las e exibi-las na página do consultor.

## Comportamento esperado
- No `/consultor`, cada ativo com opiniões nos últimos 30 dias mostra uma lista: casa, recomendação (compra, neutro ou venda), preço-alvo quando houver, data da matéria, resumo de uma linha e link para a matéria original.
- Uma seção "Opiniões recentes" lista as últimas 20 opiniões extraídas, de todos os ativos.
- **Degradação:** se a extração não estiver disponível, as recomendações técnicas aparecem normalmente e o topo da página mostra um aviso sobre a indisponibilidade, sem quebras 500 ou página em branco.
- `/api/consultor` inclui `opinioes` por ativo e `fontes_opiniao`.

## Extração e Validação
- **Extração.** Lotes de até 10 matérias por chamada ao LLM (Gemini), com limites e schema estritos para evitar erros e estourar a cota.
- **Validação no código.** Descartar a opinião se: o ticker não está no universo; o `trecho` não aparece na matéria; o `preco_alvo` não aparece; ou a `casa` está vazia. Mapear sinônimos de recomendação para o formato padrão.
- **Duplicatas.** Mesma casa, ativo e recomendação na mesma matéria/dia viram uma única opinião, preservando links.

## Critérios de aceite
- [ ] Com uma resposta Gemini mockada, opiniões aparecem no `/api/consultor` do ativo correto, com as validações de exclusão de campos faltantes respeitadas.
- [ ] Sem chave, fora de cota ou erros do LLM: `/consultor` responde 200, mostrando aviso e recomendações técnicas apenas.
- [ ] Texto exibido atende a invariante de máximo 120 caracteres por opinião.
