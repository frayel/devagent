---
id: 160
titulo: Apetite a risco aqui e lá fora não usam o mesmo nome
status: ready
esforco: P
gaveta: experiência
aceite: tests/test_aceite_160.py
revisada: 2026-11-16
---

## Problema
O usuário perguntou: "o mercado está tomando risco ou não? A página diz as duas coisas."

Revisão de experiência de 15/11/2026 (cadência de experiência vencida: 3 de 3), feita sobre as capturas de `make telas` (`telas/desktop.png` e `telas/celular.png`). Na Visão Geral, acima da dobra em 1440×900, o card **Maré do mercado** mostra o gauge "Apetite a Risco (SMLL - IBOV)" com o estado **Defensivo** em vermelho. Logo abaixo, o card **Clima Global** abre com a linha **"Apetite a Risco"**, sem cor, seguida de S&P 500 Fut +1,00% e VIX −3,00%. Lida de cima para baixo, a tela afirma "Apetite a Risco: Defensivo" e depois "Apetite a Risco", e o investidor não tem como saber que são duas medidas diferentes:

- `apetite_risco` (`app/collectors/apetite_risco.py`): small caps (SMAL11) menos Ibovespa no dia; `> +0,1 p.p.` = "Tomando risco", `< −0,1 p.p.` = "Defensivo", senão "Neutro". É o apetite **aqui**.
- `clima_global` (`app/collectors/clima_global.py`): S&P 500 futuro e VIX; VIX `> +3%` e S&P `< −0,5%` = "Aversão a Risco"; VIX `< −2%` e S&P `> +0,5%` = "Apetite a Risco"; senão "Neutro". É o apetite **lá fora**.

O mesmo nome para duas medidas é o defeito. A divergência entre elas (exterior comprando risco, small caps brasileiras ficando para trás) é justamente a informação útil, e hoje ela parece contradição. Somam-se dois desvios do guia: o estado do Clima Global sai com a classe `destaque alta|baixa|neutra`, que não tem estilo em `app/static/tema.css` (a captura mostra texto branco, sem cor nem seta), e o card não tem ⓘ, então os cortes de VIX e S&P não aparecem em lugar nenhum (transparência do `PRODUTO.md`: método).

## Comportamento esperado
Só apresentação, em `app/templates/index.html`; coletores, cortes e banco não mudam.

1. **Maré do mercado**: o rótulo do gauge passa de "Apetite a Risco (SMLL - IBOV)" para **"Apetite aqui (SMLL − IBOV)"**. Estado, cores e gauge não mudam.
2. **Clima Global**: o estado gravado é exibido com o mesmo vocabulário do apetite local, sob o rótulo **"Apetite lá fora"**:

   | `clima_global.status` gravado | Texto exibido | Classe |
   |---|---|---|
   | `Apetite a Risco` | Tomando risco | `texto-alta` |
   | `Aversão a Risco` | Defensivo | `texto-baixa` |
   | `Neutro` (ou qualquer outro valor) | Neutro | `texto-neutro` |

   O estado sai pela macro `kpi` de `app/templates/componentes.html`, como o apetite local (sem a classe `destaque`), com os KPIs de S&P 500 Fut e VIX logo abaixo, como hoje.
3. **ⓘ do Clima Global**: o terceiro argumento de `painel(...)` deixa de ser vazio e diz o método: S&P 500 futuro (`ES=F`) e VIX (`^VIX`), variação do último fechamento sobre o anterior; "Tomando risco" quando o VIX cai mais de 2% e o S&P sobe mais de 0,5%; "Defensivo" quando o VIX sobe mais de 3% e o S&P cai mais de 0,5%; "Neutro" no resto. Uma frase final diz que o apetite lá fora e o apetite aqui (card Maré do mercado) são medidas diferentes e podem divergir.

A string literal "Apetite a Risco" não aparece mais em nenhum rótulo visível da Visão Geral.

## Fontes de dados
As atuais, sem coleta nova. Plano B herdado: sem snapshot de `clima_global` o card recebe `escondido` e mostra o estado `indisponivel`/`sem_registro`, como hoje; sem `apetite_risco`, o gauge local não aparece. Um card não depende do outro.

## Cálculos
Nenhum novo. O mapeamento da tabela acima é só de texto. O `/api/snapshot` continua publicando `paineis.clima_global.status` com o valor gravado ("Apetite a Risco", "Aversão a Risco" ou "Neutro") e `paineis.apetite_risco.estado` como hoje: o contrato de `auditoria/README.md` e as checagens `checar_clima_global` e `checar_apetite_risco` não mudam.

### Exemplo de ponta a ponta
Do dado bruto: o chart do Yahoo entrega fechamentos em pontos. `ES=F` com penúltimo fechamento 5000,00 e último 5050,00 dá (5050 − 5000) / 5000 × 100 = **+1,00** (percentual, gravado como `sp500_pct = 1.0`); `^VIX` com 20,00 e 19,40 dá (19,40 − 20,00) / 20,00 × 100 = **−3,00** (`vix_pct = -3.0`). Como −3,00 < −2 e +1,00 > +0,5, o coletor grava `status = "Apetite a Risco"`, que a tabela acima exibe como "Tomando risco".

Snapshot de `clima_global` com `sp500_pct = 1.0`, `vix_pct = -3.0`, `status = "Apetite a Risco"`; snapshot de `apetite_risco` com `diferenca = -0.80`, `estado = "Defensivo"`. A Visão Geral mostra:

- na Maré: "Apetite aqui (SMLL − IBOV)", **Defensivo** em vermelho, gauge −0,80 p.p.;
- no Clima Global: "Apetite lá fora", **Tomando risco** em verde (`texto-alta`), S&P 500 Fut ▲ +1,00%, VIX ▼ −3,00%.

Contraexemplo: `sp500_pct = 0.3`, `vix_pct = -3.0` gravado como `Neutro` mostra **Neutro** com `texto-neutro`, sem seta de estado.

## Critérios de aceite
- [ ] Com os dois snapshots do exemplo, o HTML de `/` contém "Apetite aqui" e "Apetite lá fora", contém "Tomando risco" dentro do card `painel-clima-global` com a classe `texto-alta`, e não contém a string "Apetite a Risco" em texto visível (fora de atributos e comentários).
- [ ] `status = "Aversão a Risco"` mostra "Defensivo" com `texto-baixa` no card do Clima Global; `status = "Neutro"` e um valor desconhecido (`"xyz"`) mostram "Neutro" com `texto-neutro`.
- [ ] O ⓘ do card do Clima Global existe e o texto contém `2%`, `3%` e `0,5%` (os cortes), `ES=F` e `^VIX`.
- [ ] O card do Clima Global não usa mais a classe `destaque`.
- [ ] `GET /api/snapshot` com o mesmo banco devolve `paineis.clima_global.status == "Apetite a Risco"` e `paineis.apetite_risco.estado == "Defensivo"` (contrato inalterado).
- [ ] Sem snapshot de `clima_global`: o card segue com `escondido` e o estado de indisponível; a Maré continua com "Apetite aqui".
- [ ] `tests/test_aceite_160.py` usa `exigir_spec_done("160")` e não abre rede. `tests/test_clima_global.py` continua verde sem alteração.
- [ ] `make telas` não gera em `/` nenhum `PROBLEMA:` que a `main` antes do PR não gerasse (a issue #885, de largura em celular, já está fechada), e o PR mostra as capturas de desktop e celular da Visão Geral.

## Invariantes de produção
- A Visão Geral publicada não tem dois rótulos com o texto "Apetite a Risco".
- O estado exibido no Clima Global corresponde ao `paineis.clima_global.status` do `/api/snapshot` pela tabela desta spec (Apetite a Risco → Tomando risco; Aversão a Risco → Defensivo; resto → Neutro).
- O card do Clima Global tem ⓘ com os cortes de VIX e S&P.

## Fora do escopo
- Mudar os cortes de qualquer um dos dois indicadores ou a janela do Clima Global (a ideia "`clima_global` coleta uma vez por manhã" segue no backlog).
- Fundir os dois cards ou criar um indicador combinado "aqui × lá fora" (fica no backlog como *Capacidade nova: divergência de apetite aqui × lá fora*).
- Renomear chaves ou valores do `/api/snapshot`.
- Problemas de largura em celular de `/` e `/consultor` (issue #885, já fechada; regressão nova vai para issue própria).
- O espaço vazio no card Ibovespa hoje abaixo das médias móveis (ideia própria no backlog, rodada de 15/11/2026 5).
