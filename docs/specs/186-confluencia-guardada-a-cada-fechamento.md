---
id: 186
titulo: A confluência de cada pregão fica guardada depois que os radares somem
status: ready
esforco: M
gaveta: capacidade nova
aceite: tests/test_aceite_186.py
origem: Os sinais do sistema têm memória
---

## Problema
O card **"Em vários radares"** (spec 155) responde "qual ação aparece em mais de um radar agora?". A pergunta seguinte, a do item *Os sinais do sistema têm memória* do `docs/BACKLOG.md`, é: **quando uma ação esteve em 3 ou mais radares antes, o que ela fez nos pregões seguintes?** Para responder, o sistema precisa saber quais ações estavam em vários radares em cada pregão passado.

Hoje ele esquece. A confluência é calculada na hora, a cada requisição (`radares_servico.confluencia` em `app/main.py`), a partir dos snapshots dos 20 radares. Esses snapshots vivem 30 datas: `remover_snapshots_antigos(30)` (`app/banco.py:876`, chamado em `app/agendador.py:190`) apaga o resto. Diferente da Maré (spec 183), a confluência não dá para recalcular de preços antigos: ela depende do que cada radar acusou naquele dia, com as regras que ele tinha. **Cada pregão que passa sem guardar a confluência é uma linha a menos na memória, para sempre.** Hoje ainda há até 30 pregões recuperáveis no banco.

Esta é a fatia 2a do item: guardar a confluência de cada pregão fechado num snapshot que acumula, recuperar os pregões que ainda estão no banco e dizer no card quantos pregões já estão guardados. Mostrar o que veio depois (retorno das ações nos 5 pregões seguintes) é a fatia 2b, quando houver amostra.

## Comportamento esperado
1. **Função pura `registro_do_pregao(payloads, data)` em `app/services/radares.py`.** Recebe os payloads dos radares de um pregão (o mesmo dicionário que `_payloads_radares()` devolve) e a data. Chama `confluencia(payloads, agora, is_historical=True, limite=None)` e devolve:
   ```json
   {"data": "2026-11-18", "lidos": 17,
    "acoes": [{"ticker": "PETR4", "radares": ["Radar de volume", "Variação Súbita", "Radar de Faca Caindo"]},
              {"ticker": "VALE3", "radares": ["Radar de volume", "Radar de Faca Caindo"]}]}
   ```
   Devolve `None` quando `lidos == 0` (nenhum radar com snapshot naquele pregão): pregão sem leitura não é pregão sem confluência, e gravar `acoes: []` nele seria falso.
2. **`confluencia` ganha o parâmetro `limite: int | None = MAX_LINHAS_CONFLUENCIA`.** Com `None`, `acoes` traz todas as linhas e `excedentes` é 0. O card e o `/api/snapshot` continuam chamando sem o parâmetro e não mudam.
3. **Função pura `acumular(anterior, novos, maximo=252)` em `app/services/radares.py`.** Junta os registros de `anterior` (lista, pode ser vazia) com `novos`, um por data (se a data se repete, vale o de `novos`), em ordem crescente de data, e mantém só os `maximo` mais recentes.
4. **Coletor `app/collectors/confluencia_historico.py`**, com `collect_and_save()`, no molde de `mare_historico.py`:
   - `agora = datetime.now(timezone.utc)`; `ultimo = calendario.ultimo_pregao_fechado(agora)`;
   - `pregoes`: `ultimo` e os 29 anteriores (`calendario.pregao_anterior` em sequência), 30 ao todo, a mesma janela que `remover_snapshots_antigos` preserva;
   - lê o snapshot `confluencia_historico` mais recente (`app.banco.ler_snapshot("confluencia_historico")`, sem data) e toma `registros` dele, ou `[]`;
   - para cada data de `pregoes` que **não** está em `registros`: `with app.banco.lendo_pregao(d): payloads = _payloads_radares()` e `registro_do_pregao(payloads, d)`; os que não são `None` vão para `novos`. `_payloads_radares` é importado de `app.main` **dentro** da função (o coletor roda no mesmo processo do web service, e o import no topo do módulo criaria ciclo). Mover a função para fora do `app/main.py` é do item *Radares do snapshot num laço* da Fila, não desta spec;
   - grava `gravar_snapshot("confluencia_historico", ultimo, "final", "composto", payload)` com `payload = {"registros": acumular(registros, novos), "de": <data do primeiro registro>, "ate": <data do último>, "fonte": "composto", "coletado_em": agora.isoformat()}`;
   - sem nenhum registro (nem antigo nem novo), não grava e devolve `False`.
   Uma data que já está em `registros` nunca é recalculada: o registro do pregão é o que os radares tinham quando ele foi guardado.
5. **Agendador:** `"confluencia_historico": "diario"` em `janelas` de `_coletar` (`app/agendador.py`), e o nome entra no **fim** da tupla de coletores, depois de `consultor_yahoo`. Com a janela `diario`, ele roda uma vez por pregão fechado, com o mercado fechado e só se ainda não há snapshot `confluencia_historico` daquele pregão. No fim da tupla, na rodada logo depois do fechamento, ele lê os snapshots que os radares acabaram de gravar como `final` na mesma rodada. A primeira execução depois do deploy recupera os até 30 pregões que o banco ainda tem.
6. **Card "Em vários radares"**, abaixo da linha "de N radares lidos agora" (`app/templates/index.html`, `confluencia-lidos`): uma linha `<div class="confluencia-memoria">` com o texto **"Guardada a cada fechamento: N pregões, desde DD/MM/AAAA."** (`N` = número de registros, singular "1 pregão"; a data é a `de` do snapshot). Sem snapshot `confluencia_historico` ou com leitura que falha, a linha não aparece e o resto do card fica como hoje. Em data histórica (`?data=`) a linha também não aparece. A classe segue `.confluencia-lidos` em `app/static/tema.css` (`font-size: var(--fs-meta)`, `color: var(--texto-3)`) e acrescenta `overflow-wrap: anywhere`, para a frase não vazar em 390 px.
7. **`/api/snapshot`:** `paineis.confluencia_historico` com `{"pregoes": N, "de": "AAAA-MM-DD", "ate": "AAAA-MM-DD", "ultimo": <o registro mais recente, completo>, "fonte": "composto", "coletado_em": <o coletado_em do snapshot>}`. Sem snapshot: `{"pregoes": 0, "de": null, "ate": null, "ultimo": null, "fonte": "composto", "coletado_em": <agora>}`. Todo painel publica `fonte` e `coletado_em` (contrato de `auditoria/README.md`, issue #872). A lista completa de registros **não** vai para o `/api/snapshot`.

## Fontes de dados
Nenhuma fonte externa. Lê os snapshots dos 20 radares de `RADARES` já gravados no banco (Postgres em produção, SQLite nos testes) e grava um snapshot novo. Plano B: leitura de um pregão que falha (exceção em `_payloads_radares` ou no banco) é registrada no log e pula só aquele pregão, que volta a ser tentado no dia seguinte enquanto estiver entre os 30; o card e o `/api/snapshot` seguem sem a linha de memória.

Tamanho: um registro com 10 ações em 3 radares ocupa ~0,6 kB de JSON; 252 registros ficam abaixo de 200 kB num único snapshot por dia, que o próprio `remover_snapshots_antigos` limpa (o snapshot de hoje carrega a lista inteira).

## Cálculos
Os mesmos da spec 155, sem o corte de 10 linhas: uma ação entra no registro quando está em 2 ou mais radares no estado `com_alertas`; ticker normalizado por `_ticker` (sem espaços, maiúsculo, sem `.SA`); radares na ordem de `RADARES`; linhas ordenadas por número de radares (decrescente) e depois ticker. `lidos` = radares em `com_alertas` ou `sem_alertas`. Em pregão fechado não há radar `desatualizado` (`is_historical=True`).

**Exemplo de ponta a ponta.** Banco com os snapshots do pregão 18/11/2026:
- `volume_alerts`: `{"alerts": [{"ticker": "PETR4.SA"}, {"ticker": "VALE3"}], "timestamp": ...}`
- `variacao_subita`: `{"alertas": [{"ticker": "PETR4"}], ...}`
- `faca_caindo`: `{"alertas": [{"ticker": " petr4 "}, {"ticker": "VALE3"}, {"ticker": "ITUB4"}], ...}`
- 14 outros radares com `alertas: []`; 3 radares sem snapshot nesse dia.

`_ticker` leva `PETR4.SA` e ` petr4 ` a `PETR4`. Contagem: PETR4 em 3 radares, VALE3 em 2, ITUB4 em 1 (fica fora, mínimo 2). `lidos` = 3 + 14 = 17. Registro:
`{"data": "2026-11-18", "lidos": 17, "acoes": [{"ticker": "PETR4", "radares": ["Radar de volume", "Variação Súbita", "Radar de Faca Caindo"]}, {"ticker": "VALE3", "radares": ["Radar de volume", "Radar de Faca Caindo"]}]}`.

Com um snapshot `confluencia_historico` anterior com registros de 13/11, 14/11 e 17/11 e este novo, o card mostra **"Guardada a cada fechamento: 4 pregões, desde 13/11/2026."** e o `/api/snapshot` traz `pregoes: 4`, `de: "2026-11-13"`, `ate: "2026-11-18"` e `ultimo` igual ao registro acima.

## Critérios de aceite
`tests/test_aceite_186.py`, com `devagent.aceite.exigir_spec_done("186")`, sem rede, com SQLite temporário:
- [ ] `registro_do_pregao` com os payloads do exemplo devolve exatamente o registro do exemplo; com todos os 20 payloads `None`, devolve `None`.
- [ ] `confluencia(..., limite=None)` com 12 ações em 2 ou mais radares devolve as 12 em `acoes` e `excedentes == 0`; sem o parâmetro, devolve 10 e `excedentes == 2` (como hoje).
- [ ] `acumular` com data repetida fica com a de `novos`, devolve em ordem crescente e, com `maximo=3` e 5 registros, mantém os 3 mais recentes.
- [ ] `collect_and_save` com snapshots de radares gravados em 3 pregões (um deles só com radares sem snapshot) e o relógio congelado num dia útil às 19h BRT grava `confluencia_historico` com 2 registros; rodado de novo com um registro já guardado e os snapshots daquele pregão trocados, não recalcula o registro guardado.
- [ ] Sem nenhum snapshot de radar e sem histórico anterior, `collect_and_save` devolve `False` e não grava.
- [ ] `app/agendador.py` declara `"confluencia_historico": "diario"` e o nome é o último da tupla de coletores de `_coletar`.
- [ ] `/` com o histórico do exemplo e radares com confluência mostra "Guardada a cada fechamento: 4 pregões, desde 13/11/2026." dentro de `painel-confluencia`; com 1 registro, "1 pregão"; sem snapshot, a classe `confluencia-memoria` não aparece; em `/?data=2026-11-18`, também não.
- [ ] `/api/snapshot` traz `paineis.confluencia_historico` com `pregoes`, `de`, `ate`, `ultimo`, `fonte` e `coletado_em` do exemplo; sem snapshot, `pregoes == 0` e `ultimo is None`.
- [ ] `tests/test_aceite_155.py` continua verde sem alteração.

## Invariantes de produção
- `paineis.confluencia_historico` existe no `/api/snapshot` e tem `fonte` e `coletado_em`.
- Depois do primeiro pregão fechado após o deploy, `pregoes >= 1`, `ate` é o último pregão fechado (dia útil da B3) ou o anterior a ele, e `de <= ate`.
- `ultimo.lidos` está entre 1 e 20; toda ação em `ultimo.acoes` tem 2 ou mais radares, todos nomes da aba Alertas, sem repetição.
- `pregoes` nunca diminui de um dia para o outro enquanto for menor que 252.
- Quando o card "Em vários radares" mostra a linha "Guardada a cada fechamento", o `N` dela é o `pregoes` do `/api/snapshot`.

## Fora do escopo
- Mostrar o que veio depois: retorno das ações em 3 ou mais radares nos 5 pregões seguintes, com casos, média e janela à vista (fatia 2b do item *Os sinais do sistema têm memória*, quando houver 20 pregões guardados).
- Guardar a confluência intradiária (várias leituras por pregão): só o estado dos radares quando o pregão é guardado.
- Recalcular registros antigos quando um radar muda de regra.
- Mover `_payloads_radares` para fora de `app/main.py` (item *Radares do snapshot num laço*).
- Mudar a retenção de `remover_snapshots_antigos`.
