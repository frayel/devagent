---
id: 182
titulo: O seletor da Maré mostra que está carregando
status: done
esforco: P
gaveta: experiência
aceite: tests/test_aceite_182.py
origem: nova
revisada: 2026-11-18
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
2. **Card esmaecido só se demorar.** Se a resposta não chegar em 150 ms, o conteúdo do card abaixo do seletor (gauge, barras, heatmap, gráfico) fica com opacidade reduzida (classe no `.mare-corpo`, sugestão `atualizando`) até a troca. Abaixo de 150 ms nada esmaece, para não piscar. Atenção: o `.mare-corpo` tem `display: contents` (`app/static/tema.css`, spec 174b) e não gera caixa, então `opacity` nele não tem efeito; a regra precisa mirar os filhos, por exemplo `.mare-corpo.atualizando > :not(.mare-nivel) { opacity: .5 }`, deixando o seletor com opacidade cheia.
3. **Ao chegar a resposta**, o card novo substitui o antigo como hoje, sem `aria-busy` e sem `carregando`.
4. **Clique durante a carga.** Um clique em outra opção cancela o pedido em curso (`AbortController`) e começa o novo, passando o destaque e o indicador para ela; só a resposta do último clique é desenhada. Um clique de novo na opção que já está carregando é ignorado.
5. **Erro e demora.** Se o pedido falhar, ou não responder em 8 s, o comportamento é o de hoje no erro: navegar para o `href` da opção (recarga completa com `?nivel=`). O indicador fica até a navegação.
6. **Movimento reduzido.** Com `prefers-reduced-motion: reduce`, o anel não gira (fica parado e semitransparente) e o esmaecimento não tem transição.
7. **Leitor de tela.** Uma região `aria-live="polite"` dentro do card, invisível na tela, anuncia `Carregando Ondas` no clique e, quando o card chega, `Ondas: 36, Medo` (o nome do nível, o valor do gauge e a faixa do card novo; a faixa é o `faixa` que `app/services/mare.py` já devolve, de `FAIXAS`). Em formação, `Ondas: histórico em formação`.
   - A região fica **fora** do `.mare-corpo`, como irmã dele dentro do painel (`card_mare` em `app/templates/componentes.html`, só quando há `seletor`). O `ui.js` troca o `.mare-corpo` inteiro com `replaceWith`; uma região viva que nasce já com texto, dentro do nó novo, não é anunciada de forma confiável. Por isso ela persiste e só o texto dela muda.
   - O texto do anúncio vem do servidor, não é montado lendo o DOM do gauge (o gauge da Maré não mostra o nome da faixa): o `.mare-corpo` do fragmento leva `data-anuncio="Ondas: 51, Neutro"` (ou `Ondas: histórico em formação`), e o `ui.js` copia esse atributo para a região depois da troca.
   - A região usa uma classe de ocultação visual em `tema.css` (o `tema.css` de hoje não tem nenhuma; criar, por exemplo `.so-leitor`, com o padrão `clip`/`position: absolute`/1 px), nunca `display: none` nem `hidden`, que a calam.
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
  - **anúncio:** a região `aria-live` contém `Carregando Ondas` logo depois do clique e, depois da troca, `Ondas: 51, Neutro` (no mock da 174b, `ONDAS = 51`, e 51 cai na faixa 40-59, `Neutro`); é o mesmo nó antes e depois da troca (marcar o nó com uma propriedade JS antes do clique e conferir que ela continua lá);
  - **esmaecimento visível:** com a resposta atrasada em 1 s e a classe já aplicada, o `opacity` calculado do `.g-centro` (dentro do gauge) é menor que 1 e o de `.mare-nivel` é 1.
- [ ] `tests/test_aceite_174b.py` continua verde sem mudar asserções.
- [ ] Nenhum `style=` novo em template e nenhum estilo inline criado por `ui.js` (as classes ficam em `tema.css`).

## Invariantes de produção
- Em `/mare`, o HTML publicado tem a região `aria-live` dentro do card da Maré e fora do `.mare-corpo`.
- `GET /mare/card?nivel=ondas` traz `data-anuncio` no `.mare-corpo`, começando por `Ondas:`.
- `GET /mare/card?nivel=ondas` responde em menos de 8 s (o limite do item 5); acima disso o usuário vê a recarga completa.

## Fora do escopo
- Deixar `/mare/card` mais rápido (cache do fragmento, pré-carga dos três níveis ao abrir a página). Se o tempo medido continuar perto de 2 s, é outra spec, com a medida de onde o tempo vai.
- Transições animadas entre os valores do gauge.
- Indicador de carga em outros controles do painel (seletor de data, abas).

## Revisão
2026-11-18 (Revisor). Aprovada com três correções de texto, todas de compatibilidade com o código da `main`:
- o esmaecimento no `.mare-corpo` não funcionaria como escrito, porque o elemento tem `display: contents`; o item 2 agora diz para mirar os filhos, e há um critério que mede o `opacity` calculado;
- a região `aria-live` dentro do `.mare-corpo` seria destruída a cada troca; o item 7 a põe fora dele, persistente;
- o card não exibe o nome da faixa, então o anúncio vem de `data-anuncio` gerado no servidor. O exemplo do critério passou a usar o mock da 174b (`Ondas: 51, Neutro`).
Sem fórmula, o exemplo numérico de ponta a ponta não se aplica. Tamanho: `ui.js`, `tema.css`, `componentes.html` e um teste novo.
