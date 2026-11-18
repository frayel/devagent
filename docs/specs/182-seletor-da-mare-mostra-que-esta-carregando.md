---
id: 182
titulo: O seletor da Maré mostra que está carregando
status: ready
esforco: P
gaveta: experiência
aceite: tests/test_aceite_182.py
origem: nova
---

## Problema
Pedido do dono do produto em 18/11/2026: ao clicar em Marolas, Ondas ou Maré, nada na tela responde até o card novo chegar.

O clique (spec 174b, `app/static/ui.js:283-310`) chama `evento.preventDefault()` e busca `/mare/card?nivel=...`. Enquanto o pedido corre, a opção clicada não muda, o card não muda e não há indicador. Medido em 18/11 às 10h57 BRT: `curl` de `https://devagent-vb52.onrender.com/mare/card?nivel=ondas` levou 2,09 s. São dois segundos em que o usuário não sabe se o clique pegou, e clica de novo, disparando outro pedido.

A pergunta que a spec responde: **o meu clique foi aceito?**

## Comportamento esperado
1. **Na hora do clique** (no mesmo quadro, antes de o pedido sair):
   - a opção clicada passa a ser a ativa (`aria-current="true"` sai da anterior e vai para ela), com o destaque de hoje (`.mare-nivel a[aria-current="true"]` em `app/static/tema.css`);
   - a opção clicada recebe `aria-busy="true"` e a classe `carregando`, que mostra um indicador de carga ao lado do nome: um anel de 12 px desenhado só com CSS (borda com `var(--destaque)`, girando), sem imagem e sem estilo inline (o CSP `style-src` só aceita `'self'` e dois hashes);
   - o `.mare-corpo` recebe `aria-busy="true"`.
2. **Card esmaecido só se demorar.** Se a resposta não chegar em 150 ms, o conteúdo do card abaixo do seletor (gauge, barras, heatmap, gráfico) fica com opacidade reduzida (classe no `.mare-corpo`, sugestão `atualizando`) até a troca. Abaixo de 150 ms nada esmaece, para não piscar.
3. **Ao chegar a resposta**, o card novo substitui o antigo como hoje, sem `aria-busy` e sem `carregando`.
4. **Clique durante a carga.** Um clique em outra opção cancela o pedido em curso (`AbortController`) e começa o novo, passando o destaque e o indicador para ela; só a resposta do último clique é desenhada. Um clique de novo na opção que já está carregando é ignorado.
5. **Erro e demora.** Se o pedido falhar, ou não responder em 8 s, o comportamento é o de hoje no erro: navegar para o `href` da opção (recarga completa com `?nivel=`). O indicador fica até a navegação.
6. **Movimento reduzido.** Com `prefers-reduced-motion: reduce`, o anel não gira (fica parado e semitransparente) e o esmaecimento não tem transição.
7. **Leitor de tela.** Uma região `aria-live="polite"` dentro do card, invisível na tela, anuncia `Carregando Ondas` no clique e, quando o card chega, `Ondas: 36, Medo` (o nome do nível, o valor do gauge e a faixa do card novo). Em formação, `Ondas: histórico em formação`.
8. **Sem JavaScript**, nada muda: os links recarregam a página, como na 174b.

Vale igual no painel geral (`/`) e em `/mare`: o seletor e o código são os mesmos.

## Fontes de dados
Nenhuma.

## Cálculos
Nenhum. Constantes nomeadas em `ui.js`: 150 ms para o esmaecimento e 8.000 ms para desistir.

## Critérios de aceite
- [ ] `tests/test_aceite_182.py`, com `exigir_spec_done("182")`, no padrão de navegador de `tests/test_aceite_146.py` (Chromium do ambiente, sem rede externa), servindo `/mare` com a leitura e o histórico mockados como em `tests/test_aceite_174b.py` e interceptando `/mare/card` com `page.route` para atrasar a resposta:
  - **feedback imediato:** com a resposta atrasada em 1 s, até 100 ms depois do clique em `Ondas` o link de Ondas tem `aria-current="true"`, `aria-busy="true"` e a classe `carregando`; o de Marolas não tem `aria-current`; o `.mare-corpo` tem `aria-busy="true"`;
  - **esmaecimento só depois de 150 ms:** com a resposta atrasada em 50 ms, a classe de esmaecimento nunca aparece (observador de mutação no `.mare-corpo`); com 1 s, aparece;
  - **fim da carga:** depois da resposta, nenhum elemento do card tem `aria-busy` nem `carregando`, e o gauge mostra o valor de Ondas do mock;
  - **último clique vence:** clicar em `Ondas` e, 100 ms depois, em `Maré`, com Ondas atrasada em 1 s e Maré em 200 ms: o card final é o de Maré, Maré tem `aria-current="true"` e o pedido de Ondas foi abortado (`request.failure()` não é `None` ou a resposta não foi desenhada);
  - **clique repetido:** dois cliques seguidos em `Ondas` geram um pedido só a `/mare/card`;
  - **erro:** com `/mare/card` respondendo 500, a página navega para `?nivel=ondas`;
  - **movimento reduzido:** com `reduced_motion="reduce"` no contexto, o `animation-name` calculado do indicador é `none`;
  - **anúncio:** a região `aria-live` contém `Carregando Ondas` logo depois do clique e `Ondas: <valor>, <faixa>` depois da troca.
- [ ] `tests/test_aceite_174b.py` continua verde sem mudar asserções.
- [ ] Nenhum `style=` novo em template e nenhum estilo inline criado por `ui.js` (as classes ficam em `tema.css`).

## Invariantes de produção
- Em `/mare`, o HTML publicado tem a região `aria-live` dentro do card da Maré.
- `GET /mare/card?nivel=ondas` responde em menos de 8 s (o limite do item 5); acima disso o usuário vê a recarga completa.

## Fora do escopo
- Deixar `/mare/card` mais rápido (cache do fragmento, pré-carga dos três níveis ao abrir a página). Se o tempo medido continuar perto de 2 s, é outra spec, com a medida de onde o tempo vai.
- Transições animadas entre os valores do gauge.
- Indicador de carga em outros controles do painel (seletor de data, abas).
