---
id: 141
titulo: Cada card diz de qual pregão é o número
status: ready
esforco: M
gaveta: experiência
aceite: tests/test_aceite_141.py
revisada: 2026-11-06
brief: P0-4
depende_de: 077, 134
---

## Problema
O usuário perguntou: "estes cards são do mesmo pregão?"

Em 05/11/2026 o Ibovespa foi observado com carimbo 04/11, a Maré e a Dispersão com 05/11 por volta de 15:50, e outros cards por volta de 18:56–18:58 BRT. É observação histórica. A hipótese de jobs independentes ou cache velho não está confirmada; o código tem coletores separados e um carimbo por painel em `/api/snapshot` (`coletado_em`), o que torna a mistura possível, sem provar a causa daquele dia.

Hoje o cabeçalho (`app/templates/base.html`) mostra o horário do Ibovespa quando o pregão está aberto, ou o fechamento de `data_referencia`. A macro `painel` só escreve o rodapé se recebe fonte e horário. "Motores do Índice" passa horário vazio, então não tem rodapé. O guia (`docs/DESIGN.md`) já pede `Fonte · dd/mm/aaaa HH:MM BRT` e o selo `desatualizado` depois de 30 minutos durante o pregão. O auditor usa 45 minutos para `ibov.coleta_recente` (`auditoria/auditar.py`). Esta spec não mexe nesse limite.

## Comportamento esperado
Fuso de exibição: `America/Sao_Paulo`. Um helper único formata o carimbo. O deslocamento fixo de −3 horas só permanece se passar por esse fuso; o Brasil não usa horário de verão, e a spec não trata o −3 como a causa do dia 05/11.

- Cabeçalho: a data do pregão em leitura e um as-of. Cards críticos para a narrativa: Ibovespa, Maré, Dispersão (highlights) e Motores. Se as datas de pregão desses quatro divergirem, o cabeçalho diz "pregões mistos" e cada card conserva a própria data. Nenhum carimbo de D−1 é reescrito como D0.
- Rodapé de todo card com dado: fonte e `dd/mm/aaaa HH:MM BRT` da coleta que produziu o número. Sem os dois, o card usa `estado('indisponivel')` ou `sem_registro` no modo histórico, em vez de um número sem origem. Motores passa a ter os dois.
- Durante o pregão (dia útil no calendário de `auditoria/calendario.py`, entre 10:00 e 17:00 BRT), idade maior que o TTL marca `estado` desatualizado, no token `--alerta`, sem apagar o número. TTL padrão: 30 minutos, o do guia. Constante por chave de painel, para quem precisar de outro valor sem espalhar número mágico.
- Fora do pregão, fim de semana e feriado: a idade sozinha não vira "desatualizado". O rótulo é o da sessão ("Fechamento de dd/mm/aaaa"), no caminho que a spec 077 já congelou. Se a sessão gravada é anterior ao último pregão esperado, o rótulo diz que é pregão anterior.
- Falha parcial: o coletor que falha registra aviso com o nome da fonte e o tipo da exceção, sem segredo (`MT5_API_KEY`, `DATABASE_URL`, token). O card mantém o snapshot anterior com o carimbo original, e o selo se o TTL estourou. `coletado_em` não avança numa coleta que não gravou. Os outros cards continuam.

`paineis.ibovespa`, `mare` e `altas_baixas` ganham `pregao` (`AAAA-MM-DD`) além de `coletado_em`. `paineis.motores_indice` hoje é a lista crua (`app/main.py` grava `json.loads(motores_json)`). Passa a ser objeto `{pregao, coletado_em, fonte, motores}`, e `motores` é essa lista. Quem lia a lista é atualizado na mesma entrega.

## Fontes de dados
Os mesmos coletores. Plano B: fonte fora do ar deixa o card no último snapshot rotulado, ou indisponível se nunca houve snapshot. Cache velho não ganha carimbo novo.

## Cálculos
Idade = agora em `America/Sao_Paulo` menos `coletado_em` convertido a esse fuso. Pregão do número = data da última barra usada na variação, não a data do relógio. TTL em minutos, inteiro, por chave, padrão 30 no pregão aberto.

## Critérios de aceite
- [ ] Snapshot com Ibovespa `pregao=2026-11-04` e Dispersão `pregao=2026-11-05`: o HTML do cabeçalho contém "pregões mistos", o rodapé do Ibovespa contém `04/11/2026` e o da Dispersão contém `05/11/2026`.
- [ ] Coleta do Ibovespa às 15:10 BRT de 04/11 lida às 18:56 BRT de 05/11, pregão de 05/11 já encerrado: o card não é "Ao vivo" e não mostra 18:56 como hora do número.
- [ ] Durante um pregão de fixture, `coletado_em` com 31 minutos: o card traz o selo de desatualizado e conserva o valor. Com 30 minutos: não traz o selo.
- [ ] Sábado ou feriado do calendário, dado do último pregão: sem selo de desatualizado só pela idade, e o cabeçalho diz o fechamento daquela data.
- [ ] Motores com timestamp e fonte: o HTML contém o rodapé. Motores sem timestamp: estado indisponível, não um percentual solto.
- [ ] Coletor que lança exceção: o teste do log não contém a string de uma chave fictícia passada no ambiente, e `coletado_em` do snapshot anterior permanece.
- [ ] `tests/test_aceite_141.py` usa `exigir_spec_done("141")` e não abre rede.

## Invariantes de produção
- Nenhum card crítico exibe número de pregão anterior sem a data desse pregão no rodapé.
- No mesmo carregamento, ou os quatro cards críticos compartilham `pregao`, ou o cabeçalho diz que os pregões estão mistos.
- Durante o pregão, card crítico com coleta mais velha que o TTL da chave não aparece sem o selo de desatualizado.

## Fora do escopo
- Reescrever o agendador (specs 126, 126a, 126b).
- Alterar `IDADE_MAXIMA_NO_PREGAO` (45 minutos) do auditor.
- Provar que a mistura de 04/11 e 05/11 veio de cache ou de jobs independentes.
- Unificar o horário dos radares que não entram na manchete, além da regra geral do rodapé da macro.

## Plano de validação
`pytest -q tests/test_aceite_141.py` sem internet. O PR de implementação mostra o cabeçalho e os quatro rodapés de manhã e de tarde do mesmo pregão. Esta spec não traz essa captura. Criar o arquivo não marca o frescor de produção como corrigido.
