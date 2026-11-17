---
id: 174b
titulo: O seletor Marolas, Ondas e Maré no card da Maré
status: done
esforco: M
gaveta: capacidade nova
aceite: tests/test_aceite_174b.py
origem: nova
revisada: 2026-11-17
---

## Problema
Segunda parte da spec 174 (pedido do dono do produto em 17/11/2026). Depende da **174a**, que grava `mare_historico` e calcula os níveis; só entra no desenvolvimento depois de a 174a estar `done`.

Um 25 (Medo) num ano de 70 é uma marola; um 25 num ano de 30 é a maré. A pergunta desta parte: **o humor de hoje é marola, onda ou maré?** O usuário escolhe o nível no próprio card e vê o valor, os componentes e o heatmap daquela janela.

## Comportamento esperado
1. **Seletor no card.** Logo abaixo do título do card da Maré, três opções lado a lado: `Marolas`, `Ondas`, `Maré`, cada uma com a janela em letra menor (`hoje`, `21 pregões`, `252 pregões`). A opção ativa tem `aria-current="true"` e o destaque dos tokens de `tema.css`. O seletor vive na macro da Maré de `app/templates/componentes.html` (spec 173), então aparece igual no painel geral (`/`) e em `/mare`.
2. **Padrão: Marolas.** Sem escolha, o card é exatamente o de hoje (mesmo valor, componentes, heatmap, legenda e sparkline).
3. **Como se escolhe.** Cada opção é um `<a href>` para a página atual com `nivel=marolas|ondas|mare` na query, preservando os outros parâmetros (`data`, `aba`). Funciona sem JavaScript (recarrega a página). Com JavaScript, `app/static/ui.js` intercepta o clique, busca o fragmento `GET /mare/card?nivel=<nivel>[&data=<data>]` (a mesma macro, sem página em volta), troca o conteúdo do card e atualiza a URL com `history.replaceState`. Sem htmx (a spec 172 o tirou do produto). Valor de `nivel` desconhecido vale `marolas`.
4. **O que muda com o nível** (os números vêm de `niveis.<nivel>` da 174a, pela mesma função de `app/services/mare.py`, para tela e `/api/snapshot` nunca divergirem):
   - **Gauge e faixa:** `valor` e `faixa` do nível.
   - **Barras dos componentes:** as médias do nível, com o peso visível de `_peso_visivel` (spec 144) sobre os `pesos` do nível; componente ausente aparece como hoje na leitura parcial.
   - **Heatmap:** `heatmap_ondas` ou `heatmap_mare`. A legenda diz a janela: hoje é `Área: volume financeiro do dia, entre os 10 maiores da cesta de 30 ações · cor: variação do preço`; em Ondas passa a `Área: volume financeiro dos últimos 21 pregões, ...` e em Maré `dos últimos 252 pregões`.
   - **Linha de contexto** abaixo do gauge, só em Ondas e Maré: `média de N pregões completos, de dd/mm a dd/mm`, com `pregoes`, `de` e `ate` do nível. *Exemplo:* `pregoes` 21, `de` 2026-10-17, `ate` 2026-11-14 → `média de 21 pregões completos, de 17/10 a 14/11`.
   - **Sparkline:** continua a de hoje em todos os níveis até a spec 175.
5. **Histórico em formação.** Com o nível `null` (menos leituras que o mínimo da 174a), o card mostra o seletor e, no lugar do gauge, `Histórico da maré em formação: N de 189 pregões` (ou `de 15`, em Ondas), com N = quantidade de `leituras` gravadas (0 sem snapshot). Marolas nunca depende do histórico longo.
6. **Data passada.** No painel geral com `?data=`, Ondas e Maré usam `ler_snapshot("mare_historico", data)`; sem registro dessa data, o estado `sem_registro` da macro `estado`, só dentro do card.
7. **Método.** O texto do botão `i` ganha um parágrafo com a tabela dos níveis da 174a, a fórmula do valor (média dos valores diários, com o exemplo 20 × 50 + 61 → 51) e o aviso de que a soma ponderada das barras pode diferir do gauge em alguns pontos quando algum dia teve componente ausente.

## Fontes de dados
Nenhuma nova: `mare_historico` (174a) para Ondas e Maré, a leitura atual da 027 para Marolas.

## Cálculos
Nenhum novo; todos estão na 174a, com exemplos. A tela só formata: valor inteiro, pesos em % inteiro, datas `dd/mm` em BRT.

## Critérios de aceite
- [ ] `tests/test_aceite_174b.py`, com `exigir_spec_done("174b")`, sem internet, com um `mare_historico` sintético gravado no banco de teste:
  - **rota e seletor:** `GET /mare` sem parâmetro mostra o seletor com `Marolas` em `aria-current="true"` e o mesmo valor de hoje; `GET /mare?nivel=ondas` mostra o valor de `niveis.ondas.valor` e `Ondas` ativo; `GET /mare?nivel=xyz` vale Marolas; `GET /mare/card?nivel=mare` devolve só o card (sem `<html`, sem aviso legal) com o valor de Maré; `GET /?nivel=ondas` mostra Ondas no card do painel geral;
  - **links sem JS:** cada opção é um `<a href>` que preserva `data` quando presente;
  - **contexto e legenda:** em Ondas aparecem a linha `média de 21 pregões completos, de dd/mm a dd/mm` e a legenda `dos últimos 21 pregões`; em Marolas, nenhuma das duas;
  - **em formação:** sem `mare_historico`, `?nivel=ondas` mostra `Histórico da maré em formação: 0 de 15 pregões` e Marolas segue normal;
  - **data passada:** `/?data=<dia sem mare_historico>&nivel=mare` mostra o estado `sem_registro` no card, e o resto da página carrega.
- [ ] Teste de navegador no padrão de `tests/test_aceite_146.py`: em `/mare`, clicar em `Ondas` troca o número do gauge sem recarregar a página (uma variável posta em `window` antes do clique continua lá depois) e a URL passa a ter `nivel=ondas`.

## Invariantes de produção
- `/mare?nivel=ondas` mostra no gauge o mesmo `paineis.mare.niveis.ondas.valor` de `/api/snapshot` (ou a mensagem de formação, quando ele é `null`).
- `/mare` e `/` sem `nivel` mostram no gauge o mesmo `paineis.mare.valor` de antes desta spec.
- Em 360 px de largura, as três opções do seletor cabem na linha sem rolagem horizontal (`make telas`).

## Fora do escopo
- Gráfico no tempo do nível: spec 175.
- Lembrar o nível escolhido entre visitas (cookie ou `localStorage`).
- Qualquer mudança no coletor ou nos cálculos: spec 174a.
