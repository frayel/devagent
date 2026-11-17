---
id: 174
titulo: A Maré em três níveis, marolas, ondas e maré
status: draft
esforco: G
gaveta: capacidade nova
aceite: tests/test_aceite_174.py
origem: nova
revisada: 2026-11-17
---

## Problema
Pedido do dono do produto em 17/11/2026: permitir ao usuário escolher o nível de tendência da Maré.

A Maré de hoje (spec 027) é uma leitura do pregão corrente: diz se o dia está em pânico ou em euforia, mas não se esse humor é uma oscilação de horas ou parte de um movimento de meses. Um 25 (Medo) num ano de 70 é uma marola; um 25 num ano de 30 é a maré. A pergunta que a spec responde: **o humor de hoje é marola, onda ou maré?**

Os três níveis seguem a teoria de Dow, com os nomes do pedido:

| Nível | Na teoria de Dow | Janela nesta spec |
|---|---|---|
| **Marolas** (padrão) | oscilações diárias | a leitura do pregão corrente, a de hoje |
| **Ondas** | tendência secundária, de correção (3 semanas a 3 meses) | média dos últimos 21 pregões completos (cerca de um mês) |
| **Maré** | tendência primária, de um ano ou mais, ciclo econômico e humor de longo prazo | média dos últimos 252 pregões completos (cerca de um ano) |

## Comportamento esperado
1. **Seletor no card.** Logo abaixo do título do card da Maré, três opções lado a lado: `Marolas`, `Ondas`, `Maré`, cada uma com a janela em letra menor (`hoje`, `21 pregões`, `252 pregões`). A opção ativa tem `aria-current="true"` e o destaque dos tokens de `tema.css`. O seletor vive na macro da Maré da spec 173, então aparece igual no painel geral (`/`) e em `/mare`.
2. **Padrão: Marolas.** Sem escolha, o card é exatamente o de hoje (mesmo valor, componentes, heatmap e sparkline).
3. **Como se escolhe.** Cada opção é um link `<a href>` para a página atual com `nivel=marolas|ondas|mare` na query, preservando os outros parâmetros (`data`, `aba`). Funciona sem JavaScript (recarrega a página). Com JavaScript, `ui.js` intercepta o clique, busca o fragmento `GET /mare/card?nivel=<nivel>[&data=<data>]` (a mesma macro, sem página em volta), troca o conteúdo do card e atualiza a URL com `history.replaceState`. Sem htmx: a spec 172 o remove do produto. Valor de `nivel` desconhecido vale `marolas`.
4. **O que muda com o nível.**
   - **Gauge e faixa:** o valor do nível (ver *Cálculos*) e a faixa de `mare.faixa()`.
   - **Barras dos componentes:** a média de Fluxo, Calma e Volume na janela, com o peso nominal da 027 (40/35/25) reescalado entre os presentes, como na 144.
   - **Heatmap:** as 10 ações da cesta com maior volume financeiro **somado na janela**, área por esse volume, cor pela variação do preço **na janela** (fechamento do último pregão completo contra o fechamento do pregão anterior ao início da janela). A legenda do treemap (PR #942) diz a janela: `Área: volume financeiro dos últimos 21 pregões, entre os 10 maiores ...` (ou `do dia`, em Marolas).
   - **Linha de contexto** abaixo do gauge, só em Ondas e Maré: `média de N pregões completos, de dd/mm a dd/mm`.
   - **Sparkline:** continua a de hoje em todos os níveis até a spec 175, que a faz seguir o nível.
5. **Histórico em formação.** Com menos leituras que o mínimo do nível (ver *Cálculos*), o card mostra o seletor e, no lugar do gauge, `Histórico da maré em formação: N de 189 pregões` (ou `de 15`, em Ondas). Marolas nunca depende do histórico longo.
6. **Data passada.** No painel geral com `?data=`, Ondas e Maré usam o histórico longo gravado para aquela data; sem registro dela, o estado `sem_registro` da macro `estado`, só no card.
7. **Método.** O texto do botão `i` ganha um parágrafo com a tabela dos níveis acima e as fórmulas do item *Cálculos*.

## Fontes de dados
A mesma do coletor da Maré (`app/collectors/mare.py`): Yahoo `/v8/finance/chart`, com o MT5 como fonte efetiva quando disponível (`mt5.fonte_efetiva`).

**Histórico longo, uma vez por pregão.** A leitura de Marolas continua como hoje (cesta com `range=3mo`, a cada rodada). Para Ondas e Maré, uma função nova no coletor (sugestão: `coletar_historico_longo`) baixa a cesta e o Ibovespa com `range=2y&interval=1d` e grava o snapshot `mare_historico` (por `gravar_snapshot`, `data_referencia` = último pregão completo) com:
- `leituras`: lista dos até 252 pregões completos mais recentes, `{data, valor, fluxo, calma, volume}`, calculada por `_Calculadora.leitura(dia, 1.0)` (sem cálculo novo de componente);
- `heatmap_ondas` e `heatmap_mare`: as 10 ações de cada janela, `{ticker, variacao, financeiro, peso}`, no formato do heatmap de hoje.

Roda na primeira rodada do agendador em que não existe `mare_historico` para o último pregão completo (na prática, uma vez depois das 18h15 BRT, `FIM_PREGAO` em `app/agendador.py`, e na partida a frio). São 30 requisições de cerca de 500 pontos cada, uma vez por dia, contra 30 de cerca de 63 pontos a cada 15 minutos que o coletor já faz.

**Por que 2 anos bastam:** a Calma de um dia pede ao menos 120 volatilidades anteriores (`MINIMO_PERCENTIL`) mais 10 retornos; com cerca de 500 pregões de Ibovespa, o mais antigo dos 252 dias tem perto de 240 volatilidades antes dele. O Volume de um dia pede 21 pregões antes; a cesta de 2 anos cobre 252 + 21 com folga.

**Plano B:** se o Yahoo falhar, o snapshot anterior continua valendo (`ler_snapshot("mare_historico")` devolve o mais recente) e a linha de contexto mostra até que data vai a janela. Ação com menos de 80% dos pregões da janela de 2 anos sai da amostra (`COBERTURA_MINIMA`, regra atual); com menos de 20 ações, Fluxo e Volume ficam ausentes nos dias afetados, como hoje. Nada disso afeta Marolas.

## Cálculos
- **Valor do nível** (Ondas: N = 21; Maré: N = 252): média aritmética dos `valor` das leituras dos N pregões completos mais recentes de `mare_historico`, arredondada meio para cima (`_arredondar`). Escolhida a média dos valores, e não o índice das médias dos componentes, para que o gauge seja a própria linha de média do gráfico da spec 175.
- **Mínimo de leituras:** Ondas 15 de 21; Maré 189 de 252 (75%). Abaixo disso, item 5.
- **Componente do nível:** média do componente nos dias da janela em que ele está presente; com presença em menos de 75% dos dias, o componente fica `ausente` no nível. Peso visível: `indice()` sobre as médias presentes, como a 144 faz na leitura do dia. Como o valor é a média dos valores diários, a soma ponderada das barras pode diferir do gauge em alguns pontos nos períodos em que algum dia teve componente ausente: o método diz isso.
- **Heatmap da janela:** variação = `fech(último pregão completo) / fech(pregão anterior ao primeiro da janela) − 1`, em %; financeiro = soma de `fechamento × volume` nos pregões da janela; peso = financeiro / soma dos 10. Ação sem fechamento no pregão anterior à janela fica de fora.
- **Marolas:** sem mudança, a leitura atual da 027.

## Critérios de aceite
- [ ] `tests/test_aceite_174.py`, com `exigir_spec_done("174")`, sem internet:
  - **cálculo:** com `leituras` sintéticas (21 valores de 40 a 60, 252 valores de 30 a 70), o valor de Ondas e de Maré é a média arredondada; com 14 leituras, Ondas devolve "em formação"; com 188, Maré também;
  - **componentes:** um componente presente em 70% dos dias da janela fica `ausente` no nível, e os pesos visíveis dos presentes somam 100;
  - **heatmap:** com séries sintéticas de 3 ações, a variação de 21 pregões e a ordem por financeiro somado batem com a conta à mão;
  - **coletor:** com respostas do Yahoo mockadas por `respx` (fixtures em `tests/fixtures/`, cesta e Ibovespa de `range=2y`), `coletar_historico_longo` grava `mare_historico` com no máximo 252 leituras, todas de pregões anteriores ou iguais ao último completo, em ordem crescente de data;
  - **agendamento:** a função roda quando não há `mare_historico` para o último pregão completo e não roda de novo na rodada seguinte do mesmo dia;
  - **rota e seletor:** `GET /mare` sem parâmetro mostra o seletor com `Marolas` em `aria-current="true"` e o mesmo valor de hoje; `GET /mare?nivel=ondas` mostra o valor de Ondas e `Ondas` ativo; `GET /mare?nivel=xyz` vale Marolas; `GET /mare/card?nivel=mare` devolve só o card (sem `<html`, sem aviso legal) com o valor de Maré; `GET /?nivel=ondas` mostra Ondas no card do painel geral;
  - **links sem JS:** cada opção do seletor é um `<a href>` que preserva `data` quando presente;
  - **plano B:** sem `mare_historico`, `?nivel=ondas` mostra "em formação" e Marolas segue normal.
- [ ] Teste de navegador no padrão de `tests/test_aceite_146.py`: em `/mare`, clicar em `Ondas` troca o número do gauge sem recarregar a página (uma variável posta em `window` antes do clique continua lá depois) e a URL passa a ter `nivel=ondas`.
- [ ] `/api/snapshot`: `paineis.mare` ganha `niveis.ondas` e `niveis.mare`, cada um com `valor`, `faixa`, `pregoes` (quantas leituras entraram), `de` e `ate` (datas ISO) ou `null` em formação. Teste no mesmo arquivo.

## Invariantes de produção
- `paineis.mare.niveis.ondas.pregoes` está entre 15 e 21, e `paineis.mare.niveis.mare.pregoes` entre 189 e 252, quando não são `null`.
- `paineis.mare.niveis.<nivel>.ate` é um dia útil da B3 anterior ou igual ao pregão corrente, e no máximo um pregão antes do último pregão completo (o histórico longo não envelhece mais de um dia).
- `valor` de cada nível está entre 0 e 100 e a `faixa` é a de `mare.faixa(valor)`.
- `/mare?nivel=ondas` mostra no gauge o mesmo `paineis.mare.niveis.ondas.valor`.

## Fora do escopo
- Gráfico no tempo do nível (horas, dias, meses): spec 175.
- Classificar a tendência (alta, baixa, lateral) por topos e fundos, como na teoria de Dow clássica; aqui o nível é só a janela da média do índice.
- Lembrar o nível escolhido entre visitas (cookie ou `localStorage`).
- Calibrar as janelas (21 e 252) ou os mínimos com evidência: spec nova, como manda o cabeçalho de `app/services/mare.py`.
- Se o Revisor julgar grande demais, a divisão natural é **174a** (histórico longo gravado e visível em `/api/snapshot`) e **174b** (seletor, níveis no card e fragmento).

## Revisão
Dividida em 17/11/2026 pelo Revisor, por tamanho (esforço G: coletor novo, agendador, serviço, rotas, macro, `ui.js`, `/api/snapshot`, método e teste de navegador numa sessão só):
- **174a** (`174a-mare-historico-longo.md`): histórico longo gravado uma vez por pregão, cálculo dos níveis e `paineis.mare.niveis` em `/api/snapshot`.
- **174b** (`174b-mare-seletor-de-nivel.md`): seletor no card, fragmento `/mare/card`, legenda do heatmap, linha de contexto, estado em formação e método. Depende da 174a.

O que mudou na divisão: o histórico longo virou um coletor próprio (`mare_historico`) com a janela `"diario"` no `_coletar`, porque o agendador força `_data_referencia_snapshot` para o pregão corrente durante o pregão e a checagem "não existe snapshot do último pregão completo" pela função dentro do coletor `mare` rodaria a cada 15 min (o mesmo tipo de defeito da issue #919); os testes usam `tests/yahoo_falso.py` (já atende `range=2y`) em vez de fixtures novas de 30 ações; toda fórmula ganhou exemplo numérico de ponta a ponta, com as unidades do Yahoo. As referências da spec 175 a "spec 174" valem para as duas partes: `mare_historico.leituras` é da 174a, `/mare/card` da 174b.

