---
id: 141
titulo: Opiniões de casas também do Telegram e do Google News
status: ready
esforco: M
gaveta: capacidade nova
aceite: tests/test_aceite_141.py
---

## Problema
O consultor só lê dois feeds RSS (Money Times e InfoMoney). Em 04/11/2026, 17 dos 26 ativos com opinião tinham uma casa só e ficaram em `cobertura insuficiente` (o mínimo é 2 casas em 30 dias). O dono do produto pediu mais fontes: os canais públicos do Telegram Clube Acionista, Repositório de Ações e Universo Antifrágil, e o Google News. O `robots.txt` deixou de bloquear fontes em 04/11/2026 (`PRODUTO.md`, seção 5). Formatos e amostras verificados estão em `docs/context/fontes-de-dados.md`.

Depende da spec 140: sem ela, as opiniões novas também seriam descartadas pela data.

## Comportamento esperado
Todas as fontes novas viram "matérias" na mesma fila (`save_materia`) e passam pelo mesmo `filtrar_materia` e pela mesma extração do Gemini. Nada muda na decisão nem na validação do trecho.

- **Clube Acionista** (`https://t.me/s/clubeacionista`): lê as mensagens da prévia pública. Cada mensagem vira uma matéria com `guid` e `link` `https://t.me/clubeacionista/<id>`, `titulo` igual à primeira linha do texto (até 200 caracteres), `conteudo` igual ao texto inteiro e `data_publicacao` vinda do `<time datetime>`. Pagina com `?before=<menor id lido>` até alcançar o maior ID já salvo dessa fonte, com no máximo 5 páginas por rodada.
- **Repositório de Ações** e **Universo Antifrágil**: a prévia `/s/` está desativada. O coletor parte do maior ID salvo do canal (na primeira rodada, o ID atual menos 50) e lê `https://t.me/<canal>/<id>` em ordem crescente: texto em `og:description`, data no `<time datetime>` de `https://t.me/<canal>/<id>?embed=1`. Para depois de 3 IDs seguidos sem `<time>` ou após 60 IDs por rodada. O ID atual é achado por busca binária só na primeira rodada.
- **Google News**: uma busca RSS por grupo de até 8 tickers da carteira, `q=(T1 OR T2 ...) (recomendação OR "preço-alvo" OR carteira) when:7d`, `hl=pt-BR&gl=BR&ceid=BR:pt-419`. Cada item vira uma matéria com `titulo` igual ao `<title>`, `conteudo` vazio, `link` do item e `data_publicacao` do `<pubDate>`. Itens com mais de 7 dias são descartados. A casa precisa estar no título; a validação do trecho já garante isso.
- **Atribuição.** A casa é a que o texto nomeia ("Ativa Investimentos recomenda COMPRA..."), nunca o canal ou o portal. O prompt de extração diz isso, e um registro com `casa` igual ao nome do canal é descartado.
- **Ritmo.** Telegram a cada 30 min junto com os feeds; Google News a cada 2 h. 1 requisição a cada 2 s por domínio, User-Agent `Consultor/1.0`. `registro_fontes.FONTES` ganha `t.me` (Telegram) e `news.google.com` (Google News), para a página `/sistema` mostrar o estado de cada uma.
- **Falhas.** Uma fonte fora do ar ou com HTML diferente registra falha em `registro_fontes` e não impede as outras. Nenhuma exceção sobe para o agendador.
- **Tela.** `fontes_opiniao.feeds` em `/api/consultor` lista as novas fontes com status e horário da última coleta.

## Fontes de dados
Ver `docs/context/fontes-de-dados.md`, seções Telegram e Google News RSS.

## Cálculos
Nenhum novo.

## Critérios de aceite
- [ ] Fixture HTML da prévia do Clube Acionista (salvar a página real de 04/11/2026) gera 20 matérias com `guid` `https://t.me/clubeacionista/<id>`, data ISO e texto sem tags; das 20, `filtrar_materia` mantém as que citam RADL3 e ITUB4 com opinião.
- [ ] Segunda rodada com o mesmo HTML não grava nada novo.
- [ ] Fixture de post do Repositório de Ações (`og:description` + widget com `<time>`) gera uma matéria; 3 IDs seguidos sem `<time>` encerram a leitura.
- [ ] Fixture RSS do Google News com um item de 9 dias e um de 2 dias grava só o de 2 dias, com `conteudo` vazio.
- [ ] Opinião extraída com `casa` "Clube Acionista" é descartada.
- [ ] Com `t.me` respondendo 500, os feeds RSS e o Google News continuam gravando e `registro_fontes` mostra a falha do Telegram.
- [ ] Nenhum teste faz requisição de rede (tudo com fixture).
- Arquivos tocados: `app/collectors/consultor_opinioes.py` (ou novos `consultor_telegram.py` e `consultor_google_news.py`), `app/services/consultor_opinioes.py` (prompt), `app/collectors/registro_fontes.py`, `app/agendador.py`, `tests/fixtures/` e o novo `tests/test_aceite_141.py`.

## Invariantes de produção
- `/sistema` mostra Telegram e Google News com ao menos um sucesso nas últimas 24 h de pregão.
- O número diário de chamadas ao Gemini continua abaixo de `GEMINI_MAX_CHAMADAS_DIA`.

## Fora do escopo
- Consenso do Yahoo (spec 142).
- Documentos da CVM como sinal de evento corporativo (o Repositório de Ações só repassa títulos da CVM; uma fonte direta fica para o backlog).
- Ler imagens dos posts.
