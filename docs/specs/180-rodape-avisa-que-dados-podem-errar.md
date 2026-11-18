---
id: 180
titulo: O rodapé avisa que os dados podem conter erros
status: ready
esforco: P
gaveta: experiência
aceite: tests/test_aceite_180.py
origem: O rodapé avisa que os dados podem conter erros
---

## Problema
Pedido do dono do produto em 17/11/2026. A pergunta do usuário: **posso confiar cegamente nestes números?**

Hoje o rodapé de todas as páginas (`app/templates/base.html:90`, `<p class="aviso-legal">`) diz só "Conteúdo informativo gerado automaticamente. Não constitui recomendação de investimento." Nada avisa que os números vêm de fontes gratuitas (Yahoo, MT5, RSS e canais públicos) e podem estar errados ou atrasados. Caso de 17/11: o heatmap da Maré parecia dar volume grande a PRIO3, TIMS3 e BPAC11 (PR #942), e quem olhou não tinha como saber que o número podia estar errado.

## Comportamento esperado
1. Logo abaixo do `<p class="aviso-legal">` do `<footer>` de `app/templates/base.html`, entra um segundo parágrafo:

   ```html
   <p class="aviso-dados">Os números vêm de fontes gratuitas e podem conter erros ou atrasos. Confira na fonte antes de decidir.</p>
   ```

2. O `<p class="aviso-legal">` **não muda** em nada: o texto dele é item protegido do `PRODUTO.md` (seção *Transparência*), e os testes 146, 156, 173 e 174b o procuram literalmente (o 173 conta exatamente uma ocorrência em `/mare`). Por isso a frase nova é um parágrafo à parte, não um acréscimo ao mesmo `<p>`.
3. O parágrafo novo aparece em todas as páginas que estendem `base.html`: `/`, `/mare`, `/sistema`, `/consultor` e `/novidades`. Ele não aparece no fragmento `GET /mare/card` (`mare_card.html` não estende o `base.html`; o `tests/test_aceite_174b.py:189` já afirma que o aviso legal não está lá).
4. Estilo: o de `footer p` (`app/static/tema.css:217`), sem regra nova. Mesmo tamanho e cor do aviso legal. Em 390 px a frase quebra linha dentro do rodapé, sem rolagem horizontal.
5. O bloco `rodape_extra` (link de Novidades) segue antes dos dois avisos, como hoje.

## Fontes de dados
Nenhuma. Texto fixo no template.

## Cálculos
Nenhum.

## Critérios de aceite
- [ ] `tests/test_aceite_180.py`, com `exigir_spec_done("180")`, sem internet (`TestClient` com os fixtures e mocks de rota de `tests/test_aceite_173.py` e `tests/test_aceite_146.py`):
  - em `GET /`, `/mare`, `/sistema`, `/consultor` e `/novidades`, o HTML contém exatamente uma vez `<p class="aviso-dados">Os números vêm de fontes gratuitas e podem conter erros ou atrasos. Confira na fonte antes de decidir.</p>`, dentro do `<footer>`;
  - nas mesmas páginas, o texto "Conteúdo informativo gerado automaticamente. Não constitui recomendação de investimento." continua aparecendo exatamente uma vez, e o `aviso-dados` vem depois dele no HTML;
  - `GET /mare/card` não contém `aviso-dados`.
- [ ] `tests/test_aceite_146.py`, `tests/test_aceite_156.py`, `tests/test_aceite_173.py` e `tests/test_aceite_174b.py` seguem verdes sem alteração.
- Arquivos tocados: `app/templates/base.html` e o novo `tests/test_aceite_180.py`. Hoje `grep -rl "aviso-legal" app tests` dá só `app/templates/base.html`.

## Invariantes de produção
- O HTML de `/` publicado contém o texto "podem conter erros ou atrasos" dentro do `<footer>`, junto com o aviso legal protegido, que segue com o texto exato do `PRODUTO.md`.

## Fora do escopo
- Mudar o texto do aviso legal protegido ou o `PRODUTO.md`.
- Listar as fontes no rodapé (cada card já mostra a sua no rodapé `Fonte ... · horário`; uma lista fixa no rodapé ficaria desatualizada a cada coletor novo).
- Aviso por card quando uma fonte está em pausa ou caiu (o backlog tem "O radar vazio diz há quanto tempo e por quê" e "O gráfico diz quando a CDN não carregou").
- Mudar `docs/DESIGN.md` ou `docs/design/referencia.html`.
