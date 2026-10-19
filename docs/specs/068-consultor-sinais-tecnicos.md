---
id: 068
titulo: Consultor · página própria com sinais técnicos do Ibovespa
status: ready
esforco: G
---

## Problema
Pedido do dono do produto (ADR 005): "o que eu faço com cada ação do Ibovespa hoje?". O painel mostra indicadores soltos; falta uma página que diga, por ativo, comprar, vender ou aguardar, e no caso de aguardar, o que precisa acontecer antes de agir. Esta é a primeira fatia do consultor: página própria, privável, com recomendações vindas só de regras técnicas. Opiniões de casas de análise, confiança histórica e placar vêm nas specs 069 a 072.

Se não couber em um PR de ~400 linhas, divida em 068a (rota, privacidade, universo e coleta) e 068b (regras e exibição), como manda o `devagent/CICLO.md`.

## Comportamento esperado
- Nova página `GET /consultor`, com o template base, o aviso legal do rodapé e um link "Consultor" no topo da página inicial, fora da barra de abas atual. Ela não é uma aba de `index.html`: precisa poder ficar privada sozinha.
- `GET /api/consultor` devolve em JSON tudo o que a página exibe.
- **Privacidade:** com `CONSULTOR_SENHA` definida, as duas rotas exigem HTTP Basic (usuário `consultor`), comparando com `secrets.compare_digest`, e respondem 401 com `WWW-Authenticate` sem credencial válida. Sem a variável, ficam públicas.
- **Universo:** `app/consultor/universo.py` com a lista da carteira teórica vigente do Ibovespa (fonte: página da carteira teórica no site da B3), a data de início e fim da vigência e o link da fonte. Se a data de hoje passar do fim da vigência, a página mostra "Composição do Ibovespa possivelmente desatualizada (vigência até dd/mm/aaaa)" e segue funcionando. O módulo também guarda um mapa nome da empresa → tickers, que a spec 070 usa.
- **Agrupamento na página**, nesta ordem: Comprar, Vender, Aguardar e Sem sinal (este recolhido por padrão). Cada linha mostra ticker, preço, regra disparada, motivo com os números que a acionaram, gatilho (para Aguardar) ou condição de invalidação (para Comprar e Vender), fonte do dado e horário da coleta.
- Uma seção recolhível "Como o consultor decide" lista as regras e os limiares, gerada a partir das constantes do módulo de regras (sem texto duplicado à mão).
- Grau de confiança nesta fatia: "Baixa: regra ainda sem histórico medido". A spec 069 substitui pelo histórico real.
- `/api/snapshot` ganha a chave `consultor` só com metadados: `atualizado_em`, `ativos_avaliados`, `composicao_vigente_ate`. Nenhum ticker com recomendação aparece no snapshot.

## Fontes de dados
- Histórico diário de cada ativo do universo e do `^BVSP`: o caminho já existente (`fetch_with_retry`, MT5 preferencial, Yahoo `chart` como reserva), com pelo menos 220 pregões. Coleta uma vez por dia após o fechamento e ao subir o serviço, com cache no SQLite.
- Último preço: a cada rodada do agendador, em lote pelo `spark`, como os painéis atuais.
- Respeitar 1 requisição a cada 2 s por domínio: com cerca de 85 ativos, a coleta diária pelo Yahoo leva perto de 3 minutos; ela roda em segundo plano e não bloqueia as demais.
- Plano B: ativo sem histórico suficiente vai para "Sem sinal" com o motivo "dados insuficientes". Falha total da coleta mostra "Dados do consultor indisponíveis" na página, sem afetar a página inicial.

## Cálculos
Indicadores por ativo, usando só dados até o último pregão fechado (o preço intradiário entra apenas na exibição):
- `MM21`, `MM200`: médias simples dos fechamentos.
- `IFR14`: índice de força relativa de Wilder, 14 pregões.
- `FR20`: retorno do ativo em 20 pregões menos o retorno do Ibovespa no mesmo período, em pontos percentuais.
- `VOL_REL`: volume do último pregão dividido pela média de volume dos 20 anteriores.
- `QUEDAS_SEGUIDAS`: fechamentos consecutivos abaixo do fechamento anterior.

Regras, avaliadas nesta ordem; a primeira que se aplica decide. Limiares como constantes nomeadas em `app/consultor/regras.py`:

| Regra | Condição | Decisão | Gatilho ou invalidação |
|---|---|---|---|
| R1 Faca caindo | `QUEDAS_SEGUIDAS ≥ 5` | Aguardar | primeiro fechamento em alta com `VOL_REL ≥ 1,5` |
| R2 Tendência de baixa | fechamento < `MM200`, `MM21 < MM200` e `FR20 < 0` | Vender | invalida com fechamento acima da `MM200` (R$ valor) |
| R3 Esticada | fechamento > `MM200`, `MM21 > MM200` e `IFR14 > 70` | Aguardar | recuo até a `MM21` (R$ valor) ou `IFR14` abaixo de 60 |
| R4 Rompimento pendente | fechamento até 3% abaixo da `MM200` e `MM21` de hoje maior que a de 5 pregões atrás | Aguardar | fechamento acima de R$ `MM200` com `VOL_REL ≥ 1` |
| R5 Tendência de alta saudável | fechamento > `MM200`, `MM21 > MM200`, `40 ≤ IFR14 ≤ 65` e `FR20 > 0` | Comprar | invalida com fechamento abaixo da `MM200` (R$ valor) |
| R0 Sem sinal | nenhuma das anteriores | Sem sinal | nenhum |

Dados ausentes: menos de 220 pregões ou volume ausente nos últimos 20 pregões leva a "Sem sinal: dados insuficientes".

## Critérios de aceite
- [ ] Dado um fixture de histórico em que o ativo atende R5, `/api/consultor` o lista em "comprar" com regra `R5` e invalidação contendo o valor da `MM200` formatado em R$.
- [ ] Um fixture para cada regra R1 a R4 produz a decisão e o gatilho da tabela; um ativo que atende R1 e R2 sai como R1 (ordem de avaliação).
- [ ] `IFR14` e `MM200` batem, com tolerância de 0,01, com valores calculados à mão num fixture pequeno documentado no teste.
- [ ] Com `CONSULTOR_SENHA` definida, `GET /consultor` e `GET /api/consultor` sem credencial retornam 401; com a credencial correta, 200. Sem a variável, 200.
- [ ] `/api/snapshot` contém `consultor.ativos_avaliados` e não contém nenhum ticker do universo dentro da chave `consultor`.
- [ ] Com a vigência da composição vencida no teste (data simulada), a página contém o aviso de composição desatualizada e responde 200.
- [ ] Com o coletor do consultor falhando, a página inicial responde 200 com seus painéis e `/consultor` mostra "Dados do consultor indisponíveis".
- [ ] A seção "Como o consultor decide" mostra os limiares lidos das constantes (o teste altera uma constante e confere a página).
- [ ] A página funciona em 390 px sem rolagem horizontal (checklist visual do `docs/DESIGN.md`).

## Invariantes de produção
- O preço exibido de cada ativo no `/api/consultor` fica a no máximo 1,5% de uma fonte independente no mesmo horário.
- Todo ativo em "comprar" tem fechamento acima da própria `MM200` exibida; todo ativo em "vender", abaixo.
- A soma dos ativos nos quatro grupos é igual a `ativos_avaliados` e ao tamanho do universo vigente.
- Com `CONSULTOR_SENHA` definida em produção, `/consultor` sem credencial responde 401.

## Fora do escopo
- Opiniões de casas de análise (spec 070) e cruzamento com o técnico (spec 071).
- Confiança histórica por regra (spec 069) e placar das recomendações (spec 072).
- Ativos fora do Ibovespa, fundos imobiliários, BDRs.
- Qualquer dado da carteira pessoal do usuário.
