---
id: 157
titulo: O Consultor também lê as opiniões dos canais públicos do Telegram
status: done
esforco: M
gaveta: capacidade nova
aceite: tests/test_aceite_157.py
revisada: 2026-11-15
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

A coleta pagina com `before` até alcançar o cursor do canal (ver *Cálculos*), com no máximo 5 páginas por rodada. Na primeira rodada (canal sem cursor), lê só uma página.

### Repositório de Ações (`RepositorioDeAcoes`) e Universo Antifrágil (`universoantifragil`)
Esses dois canais não têm a prévia `/s/` (ela redireciona para a página do canal). Para cada ID, o texto sai de `og:description` em `https://t.me/<canal>/<id>` e a data do `<time datetime>` em `https://t.me/<canal>/<id>?embed=1`. A matéria segue o formato do Clube Acionista.

A leitura começa no ID seguinte ao cursor do canal, em ordem crescente. Ela para depois de 3 IDs seguidos sem `<time>` (o fim do canal) ou depois de 30 IDs por rodada. Na primeira rodada (canal sem cursor), o ponto de partida é configurado em `TELEGRAM_INICIO = {"RepositorioDeAcoes": 159281, "universoantifragil": 3549}` (IDs vistos em 04/11/2026), sem busca do ID atual.

Limite conhecido: uma lacuna de 3 ou mais mensagens apagadas no meio do canal parece o fim, e o cursor fica parado antes dela. Quando a leitura para por 3 IDs vazios, o coletor registra um aviso no log com o canal e o ID, e o `/sistema` continua mostrando sucesso (as requisições respondem). Contornar a lacuna fica fora desta spec.

### Atribuição
A casa é a que o texto nomeia ("Ativa Investimentos recomenda COMPRA para RADL3"), nunca o canal. O prompt da extração diz isso, e uma opinião com `casa` igual ao nome de um dos canais é descartada antes de gravar. A comparação ignora maiúsculas, acentos e espaços nas pontas: "repositorio de acoes" e "Clube Acionista " também são descartadas. Os nomes vêm de `TELEGRAM_CANAIS = {"clubeacionista": "Clube Acionista", "RepositorioDeAcoes": "Repositório de Ações", "universoantifragil": "Universo Antifrágil"}` no coletor. No Universo Antifrágil, a opinião costuma ser do próprio canal: ela cai nessa regra e é descartada, de propósito.

### O que se espera de cada canal
- **Clube Acionista:** é a fonte útil. Na amostra de 04/11, 3 de 20 mensagens traziam opinião atribuída a uma casa.
- **Repositório de Ações:** repassa títulos de documentos da CVM, e o `filtrar_materia` deve descartar quase tudo.
- **Universo Antifrágil:** posta pouco, e a `og:description` é curta.

Os três entram assim mesmo, porque o pedido é dos três. O `/sistema` mostra quantas matérias cada um gerou, e a próxima revisão de manutenção decide se algum sai.

### Tela (`/consultor`)
- A tabela de opiniões recentes (hoje com 7 colunas, `app/templates/consultor.html`) ganha a coluna **Via**, com a origem da matéria: `Money Times`, `InfoMoney` ou `Telegram · Clube Acionista` (e assim por diante). A origem sai do `link` já gravado em `consultor_opinioes`: domínio `moneytimes.com.br` → `Money Times`, `infomoney.com.br` → `InfoMoney`, `t.me/<canal>/<id>` → `Telegram · ` + `TELEGRAM_CANAIS[<canal>]`; qualquer outro, o domínio. Sem coluna nova no banco. Os `colspan` das linhas de diagnóstico passam de 7 para 8. A coluna **Link** aponta para a mensagem no Telegram.
- `fontes_opiniao.feeds` em `/api/consultor` lista os três canais junto com os dois feeds, cada um com `url`, `nome`, `status` e `ultima_coleta` reais. Hoje esses campos são fixos (`"ok"` e vazio, `app/main.py`). O coletor guarda, na memória do processo, o resultado da última tentativa de cada fonte: `status` `"ok"` ou `"falha"`, `ultima_coleta` a hora ISO UTC dessa tentativa. Antes da primeira rodada depois de reiniciar, `status` é `"sem coleta"` e `ultima_coleta` é vazio. A `url` de um canal é `https://t.me/<canal>`.
- A frase "Nenhuma matéria dos feeds citou..." passa a dizer "Nenhuma matéria das fontes citou...". O `tests/test_aceite_085.py` confere a frase antiga e é atualizado no mesmo PR.

### Ritmo e falhas
- Os canais entram na mesma rodada dos feeds (`collect_and_save`), com 2 s entre requisições ao `t.me` e o mesmo User-Agent dos feeds.
- `registro_fontes.FONTES` ganha `("t.me", "Telegram")`. O `fetch_with_retry` do coletor (`app/collectors/consultor_opinioes.py`) hoje não anota nada no registro: ele passa a chamar `registro_fontes.sucesso` ou `registro_fontes.falha` com o resultado final de cada URL, feeds e `t.me`. Assim o `/sistema` mostra Money Times, InfoMoney e Telegram com dados reais.
- Um canal fora do ar ou com HTML diferente registra falha e não impede os outros nem os feeds. Nenhuma exceção sobe para o agendador.

## Fontes de dados
Os três canais são públicos e não exigem login. `https://t.me/robots.txt` respondia 404 em 04/11/2026, e o `PRODUTO.md` (seção 5) já não segue `robots.txt` desde então. O formato verificado em 04/11 se perdeu com aquele ramo; o PR de implementação o registra de novo numa seção Telegram do `docs/context/fontes-de-dados.md`. Plano B: canal fora do ar, nada novo nessa rodada, e as opiniões já gravadas continuam. A tela não muda, salvo o `status` do canal em `fontes_opiniao`.

## Cálculos
Nenhum cálculo novo, mas há um estado novo: o cursor de cada canal.

O cursor **não** pode sair de `consultor_fila_materias`, por três motivos: a fila só recebe as mensagens que passam no `filtrar_materia` (no Repositório de Ações, quase nenhuma), ela apaga linhas com mais de 3 dias, e o `guid` é `TEXT`, em que `MAX` compara como texto (`"9999"` > `"41230"`). Com a fila como cursor, o Repositório de Ações releria os mesmos 30 IDs a cada rodada sem nunca avançar.

Por isso a spec cria a tabela `consultor_telegram_cursor (canal TEXT PRIMARY KEY, ultimo_id INTEGER NOT NULL, atualizado_em TEXT NOT NULL)`, nos dois ramos (SQLite e Postgres) do `init_db` de `app/consultor/armazenamento.py`. Ao fim da leitura de um canal, `ultimo_id` passa a ser o maior ID numérico lido com `<time>` (Clube Acionista: o maior `data-post` da rodada), tenha a mensagem passado no filtro ou não; sem mensagem nova, o `ultimo_id` fica igual e só o `atualizado_em` é regravado. Canal com falha na rodada não mexe no cursor.

### Exemplo de ponta a ponta
A prévia do Clube Acionista traz `data-post="clubeacionista/41230"`, `<time datetime="2026-11-04T13:05:00+00:00">` e o texto "🔔 RADL3 - Ativa Investimentos recomenda COMPRA para Raia Drogasil, com preço-alvo de R$ 32,00".

1. A matéria fica com `guid` `https://t.me/clubeacionista/41230`, `titulo` igual ao texto (menos de 200 caracteres) e `data_publicacao` `2026-11-04T13:05:00+00:00`.
2. `filtrar_materia` acha "recomend" e "RADL3" e devolve `["RADL3"]`. A matéria vai para a fila.
3. O Gemini extrai `{"ticker": "RADL3", "casa": "Ativa Investimentos", "recomendacao": "compra", "preco_alvo": 32.0}`, e o trecho citado está no texto.
4. O `/consultor` mostra a linha `RADL3 · Ativa Investimentos · compra · R$ 32,00 · 04/11 · Via: Telegram · Clube Acionista`, com o link para `https://t.me/clubeacionista/41230`.

5. O cursor `clubeacionista` passa a 41230 (supondo que 41230 é o maior `data-post` da página), mesmo que as outras 19 mensagens não tenham passado no filtro.

Na rodada seguinte, com o mesmo HTML, o cursor é 41230, nenhuma mensagem é mais nova e nada é gravado de novo.

No Repositório de Ações, com cursor 159281 e posts 159282 a 159290 publicados, a rodada lê 159282 a 159290 (9 pares post + widget), mais 159291, 159292 e 159293 sem `<time>`, para, e grava o cursor 159290, mesmo que o `filtrar_materia` descarte as 9.

## Critérios de aceite
- [ ] Fixture HTML da prévia do Clube Acionista, com 20 mensagens salvas da página real, gera 20 matérias com `guid` no formato acima, data ISO em UTC e texto sem tags. As que citam ativo com opinião passam pelo `filtrar_materia`.
- [ ] Segunda rodada com a mesma fixture não grava matéria nova, e o cursor do canal fica no maior `data-post` da fixture.
- [ ] Com mensagens que nenhuma passa no `filtrar_materia`, o cursor avança assim mesmo (a fila fica vazia e a rodada seguinte começa depois do último ID lido).
- [ ] Fixtures de post e de widget do Repositório de Ações geram uma matéria. Três IDs seguidos sem `<time>` encerram a leitura, e o teto de 30 IDs é respeitado.
- [ ] Opinião extraída com `casa` igual a "Clube Acionista", "Repositório de Ações" ou "Universo Antifrágil" não é gravada, também em minúsculas e sem acento.
- [ ] Com `t.me` respondendo 500, os dois feeds RSS continuam gravando, `registro_fontes` mostra a falha do Telegram e o sucesso de Money Times e InfoMoney, o cursor dos canais não muda e `collect_and_save` não levanta exceção.
- [ ] O `/consultor` com uma opinião vinda do Telegram mostra a coluna Via com `Telegram · Clube Acionista` e o link `https://t.me/clubeacionista/<id>`.
- [ ] `/api/consultor` traz em `fontes_opiniao.feeds` cinco entradas (dois feeds e três canais), com `status` e `ultima_coleta`; antes de qualquer rodada, `status` é `"sem coleta"`, e depois da rodada com `t.me` em 500, os canais têm `"falha"` e os feeds `"ok"`.
- [ ] `tests/test_aceite_157.py` usa `exigir_spec_done("157")` e nenhum teste abre rede.
- [ ] O `app/novidades.json` (a spec 156 já está `done`) ganha uma entrada `tipo` `novidade` com `"spec": "157"` e `onde` `{"pagina": "/consultor", "pagina_nome": "Consultor", "painel": "Opiniões recentes"}`.

## Invariantes de produção
- Toda opinião com link `t.me` no `/api/consultor` tem `casa` diferente dos nomes dos canais.
- Durante o pregão, o `/sistema` mostra o Telegram com pelo menos um sucesso nas últimas 24 h.
- As chamadas diárias ao Gemini continuam abaixo de `GEMINI_MAX_CHAMADAS_DIA`.
- Para cada canal com cursor, `consultor_telegram_cursor.atualizado_em` tem menos de 24 h durante a semana de pregão (o cursor avança ou ao menos é regravado a cada rodada sem falha).

## Fora do escopo
- Google News, que fazia parte do pedido de 04/11 e fica para outra spec, se o dono quiser.
- Ler imagens dos posts.
- Canais privados ou grupos, que exigem conta e a API do Telegram.
- Contornar lacunas de 3 ou mais mensagens apagadas nos canais lidos por ID.
- Usar os comunicados da CVM que o Repositório de Ações repassa como sinal de evento corporativo. A fonte direta da CVM vai para o backlog.
