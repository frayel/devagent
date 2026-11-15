---
id: 157
titulo: O Consultor também lê as opiniões dos canais públicos do Telegram
status: ready
esforco: M
gaveta: capacidade nova
aceite: tests/test_aceite_157.py
---

## Problema
O usuário perguntou: "o que as casas de análise dizem desta ação, além do que sai no Money Times e no InfoMoney?"

O dono do produto pediu, em 04/11/2026, três canais públicos do Telegram como fonte do Consultor: Clube Acionista, Repositório de Ações e Universo Antifrágil. A spec escrita naquele dia (então numerada 141, junto com Google News) ficou num ramo que nunca chegou à `main`, e o número 141 foi usado por outra spec. Em 15/11/2026 o pedido foi refeito: só os canais do Telegram, com as opiniões no `/consultor`.

Hoje `app/collectors/consultor_opinioes.py` lê dois feeds RSS (`FEEDS`). Cada matéria passa por `app/consultor/pre_filtro.py::filtrar_materia` e vai para a fila (`save_materia`), e o Gemini extrai a opinião (`extrair_opinioes`). Em 04/11, 17 dos 26 ativos com opinião tinham uma casa só e ficavam em "cobertura insuficiente" (mínimo de 2 casas em 30 dias).

## Comportamento esperado
As mensagens dos canais viram matérias na mesma fila e passam pelo mesmo `filtrar_materia` e pela mesma extração. A regra de decisão e a validação do trecho não mudam.

### Clube Acionista (`clubeacionista`)
Tem prévia pública, `https://t.me/s/clubeacionista`. Cada leitura traz as 20 mensagens mais recentes; as anteriores vêm com `?before=<id>`. Cada mensagem vira uma matéria:

- `guid` e `link`: `https://t.me/clubeacionista/<id>`, onde `<id>` sai de `data-post`;
- `titulo`: a primeira linha do texto, até 200 caracteres;
- `descricao`: vazia;
- `conteudo`: o texto inteiro, sem tags;
- `data_publicacao`: o `<time datetime>`, que vem em UTC.

A coleta pagina com `before` até alcançar o maior ID já salvo desse canal, com no máximo 5 páginas por rodada. Na primeira rodada, lê só uma página.

### Repositório de Ações (`RepositorioDeAcoes`) e Universo Antifrágil (`universoantifragil`)
Esses dois canais não têm a prévia `/s/` (ela redireciona para a página do canal). Para cada ID, o texto sai de `og:description` em `https://t.me/<canal>/<id>` e a data do `<time datetime>` em `https://t.me/<canal>/<id>?embed=1`. A matéria segue o formato do Clube Acionista.

A leitura vai do maior ID salvo do canal, em ordem crescente. Ela para depois de 3 IDs seguidos sem `<time>` (o fim do canal) ou depois de 30 IDs por rodada. Na primeira rodada, o ponto de partida é configurado em `TELEGRAM_INICIO = {"RepositorioDeAcoes": 159281, "universoantifragil": 3549}` (IDs vistos em 04/11/2026), sem busca do ID atual.

### Atribuição
A casa é a que o texto nomeia ("Ativa Investimentos recomenda COMPRA para RADL3"), nunca o canal. O prompt da extração diz isso, e uma opinião com `casa` igual ao nome de um dos canais é descartada antes de gravar. No Universo Antifrágil, a opinião costuma ser do próprio canal: ela cai nessa regra e é descartada, de propósito.

### O que se espera de cada canal
- **Clube Acionista:** é a fonte útil. Na amostra de 04/11, 3 de 20 mensagens traziam opinião atribuída a uma casa.
- **Repositório de Ações:** repassa títulos de documentos da CVM, e o `filtrar_materia` deve descartar quase tudo.
- **Universo Antifrágil:** posta pouco, e a `og:description` é curta.

Os três entram assim mesmo, porque o pedido é dos três. O `/sistema` mostra quantas matérias cada um gerou, e a próxima revisão de manutenção decide se algum sai.

### Tela (`/consultor`)
- A tabela de opiniões recentes ganha a coluna **Via**, com a origem da matéria: `Money Times`, `InfoMoney` ou `Telegram · Clube Acionista` (e assim por diante). A coluna **Link** aponta para a mensagem no Telegram.
- `fontes_opiniao.feeds` em `/api/consultor` lista os três canais junto com os dois feeds, cada um com `status` e `ultima_coleta` reais. Hoje esses campos são fixos (`"ok"` e vazio).
- A frase "Nenhuma matéria dos feeds citou..." passa a dizer "Nenhuma matéria das fontes citou...".

### Ritmo e falhas
- Os canais entram na mesma rodada dos feeds (`collect_and_save`), com 2 s entre requisições ao `t.me` e o mesmo User-Agent dos feeds.
- `registro_fontes.FONTES` ganha `("t.me", "Telegram")`, e as chamadas passam a ser contadas para o `/sistema` mostrar o estado da fonte.
- Um canal fora do ar ou com HTML diferente registra falha e não impede os outros nem os feeds. Nenhuma exceção sobe para o agendador.

## Fontes de dados
Os três canais são públicos e não exigem login. `https://t.me/robots.txt` respondia 404 em 04/11/2026, e o `PRODUTO.md` (seção 5) já não segue `robots.txt` desde então. O formato verificado em 04/11 se perdeu com aquele ramo; o PR de implementação o registra de novo numa seção Telegram do `docs/context/fontes-de-dados.md`. Plano B: canal fora do ar, nada novo nessa rodada, e as opiniões já gravadas continuam. A tela não muda, salvo o `status` do canal em `fontes_opiniao`.

## Cálculos
Nenhum cálculo novo. O ID salvo de cada canal é o maior `guid` daquele canal na tabela de matérias. Não há estado novo no banco.

### Exemplo de ponta a ponta
A prévia do Clube Acionista traz `data-post="clubeacionista/41230"`, `<time datetime="2026-11-04T13:05:00+00:00">` e o texto "🔔 RADL3 - Ativa Investimentos recomenda COMPRA para Raia Drogasil, com preço-alvo de R$ 32,00".

1. A matéria fica com `guid` `https://t.me/clubeacionista/41230`, `titulo` igual ao texto (menos de 200 caracteres) e `data_publicacao` `2026-11-04T13:05:00+00:00`.
2. `filtrar_materia` acha "recomend" e "RADL3" e devolve `["RADL3"]`. A matéria vai para a fila.
3. O Gemini extrai `{"ticker": "RADL3", "casa": "Ativa Investimentos", "recomendacao": "compra", "preco_alvo": 32.0}`, e o trecho citado está no texto.
4. O `/consultor` mostra a linha `RADL3 · Ativa Investimentos · compra · R$ 32,00 · 04/11 · Via: Telegram · Clube Acionista`, com o link para `https://t.me/clubeacionista/41230`.

Na rodada seguinte, com o mesmo HTML, o maior ID salvo é 41230 e nada é gravado de novo.

## Critérios de aceite
- [ ] Fixture HTML da prévia do Clube Acionista, com 20 mensagens salvas da página real, gera 20 matérias com `guid` no formato acima, data ISO em UTC e texto sem tags. As que citam ativo com opinião passam pelo `filtrar_materia`.
- [ ] Segunda rodada com a mesma fixture não grava matéria nova.
- [ ] Fixtures de post e de widget do Repositório de Ações geram uma matéria. Três IDs seguidos sem `<time>` encerram a leitura, e o teto de 30 IDs é respeitado.
- [ ] Opinião extraída com `casa` igual a "Clube Acionista", "Repositório de Ações" ou "Universo Antifrágil" não é gravada.
- [ ] Com `t.me` respondendo 500, os dois feeds RSS continuam gravando, `registro_fontes` mostra a falha do Telegram e `collect_and_save` não levanta exceção.
- [ ] O `/consultor` com uma opinião vinda do Telegram mostra a coluna Via com `Telegram · Clube Acionista` e o link `https://t.me/clubeacionista/<id>`.
- [ ] `/api/consultor` traz em `fontes_opiniao.feeds` os três canais, com `status` e `ultima_coleta`.
- [ ] `tests/test_aceite_157.py` usa `exigir_spec_done("157")` e nenhum teste abre rede.
- [ ] O `app/novidades.json` da spec 156 ganha uma entrada `novidade` para esta spec, com `onde` `{"pagina": "/consultor", "painel": "Opiniões recentes"}`, se a 156 já estiver `done`.

## Invariantes de produção
- Toda opinião com link `t.me` no `/api/consultor` tem `casa` diferente dos nomes dos canais.
- Durante o pregão, o `/sistema` mostra o Telegram com pelo menos um sucesso nas últimas 24 h.
- As chamadas diárias ao Gemini continuam abaixo de `GEMINI_MAX_CHAMADAS_DIA`.

## Fora do escopo
- Google News, que fazia parte do pedido de 04/11 e fica para outra spec, se o dono quiser.
- Ler imagens dos posts.
- Canais privados ou grupos, que exigem conta e a API do Telegram.
- Usar os comunicados da CVM que o Repositório de Ações repassa como sinal de evento corporativo. A fonte direta da CVM vai para o backlog.
