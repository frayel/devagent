---
id: 027
titulo: Maré do mercado (índice de otimismo)
status: ready
esforco: G
depende_de: 026
---

## Problema
Pedido do dono do produto em 05/10/2026: um índice de 0 a 100 que diga, num relance, o humor do mercado, medido por volume, volatilidade e fluxo de ordens.

A pergunta que ele responde: **"Hoje o dinheiro está entrando com calma, saindo com pressa ou só olhando?"**

### Por que "Maré"
Os três componentes se comportam como a água: o **volume** é a quantidade de água que se move, a **volatilidade** é a agitação das ondas e o **fluxo** é a direção da correnteza. Maré cheia e mar calmo com correnteza para dentro é otimismo; mar agitado e correnteza para fora é pânico. O nome é curto, em português e não colide com índices conhecidos.

## Comportamento esperado
Um painel **"Maré do mercado"**, `span-4`, ao lado do Ibovespa, acima da dobra em 1440×900 (DESIGN.md, seção 3). A Tendência e a Dispersão, que hoje dividem essa coluna, descem para a linha 4 do guia.

- **Gauge protagonista** (macro `gauge` da spec 026) de 0 a 100, com as cinco faixas no anel externo e agulha. No centro, o valor inteiro em `--fs-hero` e o nome da faixa embaixo:

| Valor | Faixa | Cor do segmento |
|---|---|---|
| 0 a 19 | Pânico | `--baixa` |
| 20 a 39 | Medo | `--baixa-fundo` |
| 40 a 59 | Neutro | `--texto-3` |
| 60 a 79 | Confiança | `--alta-fundo` |
| 80 a 100 | Otimismo extremo | `--alta` |

  Os limites inferiores pertencem à faixa de cima: 20 é Medo, 80 é Otimismo extremo.
- **Os três componentes** abaixo do gauge, cada um como barra fina de 0 a 100 com o valor ao lado: Fluxo, Volatilidade (calma) e Volume. Assim o leitor vê *por que* o índice está onde está.
- **Sparkline de 48px** com a Maré dos últimos 21 pregões e o texto "há 5 pregões: 54 · Neutro" ao lado.
- Selo `parcial` em `--alerta` quando um componente faltou na coleta (ver Cálculos).
- Botão ⓘ com o método resumido e a frase: "A Maré descreve o humor do momento. Não é recomendação de compra ou venda." O rodapé legal continua valendo (PRODUTO.md, seção 1).
- A manchete dinâmica (spec 022) pode citar a faixa da Maré ("Maré em Confiança"); isso é opcional neste PR.

## Fontes de dados
Todas já usadas pelo projeto; nenhum domínio novo.

- **Amostra de ações:** a cesta `TICKERS` de `app/collectors/highlights.py`, via Yahoo `v7/finance/spark` com `range=3mo&interval=1d` (fechamento e volume diários), em lotes de 15, respeitando `fetch_with_retry` e o intervalo por domínio (PRODUTO.md, seção 5).
- **Ibovespa:** Yahoo `v8/finance/chart/^BVSP?range=2y&interval=1d` (fechamentos diários). Plano B: brapi `^BVSP` com `range=2y`.
- **Frequência:** a mesma do agendador (15 min no pregão, espaçada fora dele).
- **Plano B geral:** se a amostra falhar inteira, o painel mostra `estado('indisponivel')` e o resto da página segue normal. Se só o Ibovespa falhar, o componente de volatilidade fica ausente e o índice sai `parcial`.

### Sobre "fluxo de ordens"
O fluxo de ordens de verdade (agressões de compra e venda no livro, tick a tick) não existe em fonte gratuita e estável. A Maré usa uma aproximação honesta e conhecida, o **volume em alta**: quanto do dinheiro negociado hoje foi em ações que estão subindo. O método no ⓘ diz isso com essas palavras. Se um dia surgir fonte de agressão por lado, ela substitui este componente numa spec própria.

## Cálculos
Todos os componentes ficam em 0 a 100, onde 100 é o lado otimista.

**1. Fluxo (peso 40%)**
`volume financeiro_i = volume_i × preço_i` para cada ação da amostra no dia.
`Fluxo = Σ volume financeiro das ações com variação > 0 / Σ volume financeiro de todas com variação ≠ 0 × 100`.

**2. Volatilidade, lida como calma (peso 35%)**
`σ10 = desvio-padrão dos 10 últimos retornos logarítmicos diários do Ibovespa × √252` (o retorno de hoje entra com o preço corrente).
Calcule o mesmo σ10 em janela móvel para cada um dos 252 pregões anteriores.
`Calma = 100 − percentil de σ10 de hoje dentro desses 252 valores`. Volatilidade baixa para o histórico recente vira número alto.

**3. Volume (peso 25%)**
Volume sozinho não tem direção: muito volume num dia de queda é pânico, num dia de alta é euforia. Por isso ele amplifica a direção.
- `ritmo = volume financeiro da amostra hoje / (média dos 21 pregões anteriores × fração do pregão decorrida)`. Fração decorrida = minutos desde 10:00 BRT / 420, entre 0,1 e 1. Fora do pregão, fração = 1. (Sem esse ajuste, toda manhã pareceria volume fraco.)
- `intensidade = limitar((ritmo − 0,5) / 1,5, 0, 1)`: 0,5× da média ou menos vale 0; 2× ou mais vale 1.
- `direção = 2 × (ações em alta / ações com variação ≠ 0) − 1`, de −1 a +1.
- `Volume = 50 + 50 × intensidade × direção`.

**Índice**
`Maré = arredondar(0,40 × Fluxo + 0,35 × Calma + 0,25 × Volume)`, inteiro de 0 a 100.

**Dados ausentes**
- Ação com menos de 80% dos pregões da janela é ignorada. Com menos de 20 ações válidas, Fluxo e Volume ficam ausentes.
- Componente ausente sai da conta e os pesos restantes são reescalados para somar 1; o painel ganha o selo `parcial` e o ⓘ diz qual faltou.
- Com menos de dois componentes, o painel fica `indisponivel`.

**Histórico (sparkline)**
O mesmo cálculo aplicado a cada um dos 21 pregões anteriores com os dados diários já baixados (fração do pregão = 1). Não precisa de coleta extra. Os valores ficam no cache para a página não recalcular.

**Constantes** (pesos, janelas, limites de ritmo, cortes das faixas) ficam num só lugar, no topo do serviço, com comentário do porquê. Calibrar depois é uma spec nova com evidência, não um ajuste solto.

## Implementação
1. Coletor `app/collectors/mare.py` seguindo `docs/skills/criar-coletor.md`, com cache `mare_cache` no SQLite.
2. Serviço `app/services/mare.py` com funções puras: `componente_fluxo`, `componente_calma`, `componente_volume`, `indice`, `faixa`, testáveis sem rede.
3. Painel em `index.html` com as macros `painel`, `gauge`, `estado`; sparkline via `Painel.grafico` (altura 48px, sem eixos).
4. Chave `mare` no `/api/snapshot` e entrada no `auditoria/README.md`.
5. Atualizar o contador de painéis da cadência de experiência em `docs/STATE.md`.
6. Se passar de ~400 linhas, divida em 027a (coletor, serviço, testes e chave no snapshot) e 027b (painel, sparkline e telas).

## Critérios de aceite
- [ ] Com um fixture em que todo o volume está em ações em alta, `componente_fluxo` = 100; com tudo em queda, 0; meio a meio, 50.
- [ ] Com σ10 de hoje igual ao menor da janela, `componente_calma` = 100; igual ao maior, 0.
- [ ] Ritmo 2× com 100% das ações em alta dá Volume = 100; ritmo 2× com 100% em queda dá 0; ritmo 0,5× dá 50 em qualquer direção.
- [ ] Às 11:00 BRT (fração 1/7), um volume igual a 1/7 da média dá ritmo 1,0.
- [ ] `faixa(19)` = "Pânico", `faixa(20)` = "Medo", `faixa(59)` = "Neutro", `faixa(60)` = "Confiança", `faixa(80)` = "Otimismo extremo", `faixa(100)` = "Otimismo extremo".
- [ ] Sem os dados do Ibovespa, o índice sai com pesos 40/(40+25) e 25/(40+25), e o snapshot traz `parcial: true` e `ausentes: ["calma"]`.
- [ ] Falha total das fontes não quebra a página: o painel mostra o estado `indisponivel` e os outros painéis renderizam.
- [ ] Testes sem internet, com mock do httpx.
- [ ] `make telas` mostra a Maré acima da dobra em 1440×900, e o PR traz o checklist visual respondido.

## Invariantes de produção
- `paineis.mare` existe no `/api/snapshot` com `coletado_em`, `fonte`, `valor`, `faixa`, `componentes` (`fluxo`, `calma`, `volume`), `pesos`, `parcial`, `ausentes` e `historico` (até 21 pares data/valor).
- `0 ≤ valor ≤ 100` e cada componente presente também.
- `faixa` é coerente com `valor` pela tabela acima.
- A soma dos pesos usados é 1 (tolerância 0,001).
- `valor` é igual à média ponderada dos componentes presentes, arredondada (tolerância 1).
- O último ponto do `historico` é o pregão anterior ao dia da coleta.

## Fora do escopo
- Fluxo de ordens real (agressão por lado) e dados de book.
- Maré por setor ou por ação.
- Alertas ou notificações quando a faixa muda.
- Backtest do índice contra retornos futuros (fica como ideia no backlog; sem ele, o painel não sugere que a Maré prevê nada).
