---
id: 146
titulo: A página inicial não esconde erro de execução
status: ready
esforco: M
gaveta: experiência
aceite: tests/test_aceite_146.py
brief: P1-5
---

## Problema
O usuário perguntou: "a página abriu com erro no console; o número que eu vejo ainda é válido?"

Em 05/11/2026 foram observados dois erros no console na carga da home. As mensagens não foram inspecionadas. Esta spec não inventa texto, stack nem causa. Os scripts da home estão em `app/templates/base.html`: htmx, Plotly na CDN, `app/static/graficos.js` e `app/static/ui.js`. Qualquer um deles, ou uma extensão, pode ter sido a origem. Isso fica para o PR de implementação registrar, com reprodução, antes de corrigir.

## Comportamento esperado
- O PR que implementar esta spec cola as duas mensagens observadas, a URL e se elas se repetem numa janela sem extensão. Se não reproduzirem, o PR diz isso e não atribui a correção a uma mensagem que ninguém viu.
- Erro de runtime do código da aplicação na home, com fixture e sem extensão, é defeito. Erro de CDN, de extensão ou de rede não entra nessa conta; o PR separa os dois.
- Painel sem dado usa `estado('indisponivel')`, ou `sem_registro` quando a página é histórica. Não fica em branco e não mostra percentual zero no lugar de base ausente (a base ausente do Ibovespa é da spec 134).
- Falha de fonte no coletor: log com o nome da fonte e o tipo da exceção, sem `MT5_API_KEY`, `DATABASE_URL` nem token. O card correspondente fica indisponível ou no último snapshot rotulado (spec 141). O restante da home responde.

## Fontes de dados
Nenhuma fonte nova. Plano B de cada card é o estado indisponível, que já é o contrato do `PRODUTO.md` quando uma fonte cai.

## Cálculos
Não há. O teste de console da aplicação não depende de cotação.

## Critérios de aceite
- [ ] `tests/test_aceite_146.py` renderiza `GET /` com fixture completo e com cada um dos quatro cards críticos ausente (Ibovespa, Maré, Dispersão, Motores). O HTML do ausente contém o estado indisponível e não contém um KPI numérico vazio no lugar dele.
- [ ] O mesmo teste executa a inicialização de `app/static/ui.js` sobre esse HTML num DOM com `Plotly.newPlot` substituído por função que não lança, sem carregar htmx nem a CDN. Exceção vinda de `ui.js` ou de `graficos.js` falha o teste. O teste não contém, no código, uma mensagem de console inventada para "os dois erros".
- [ ] Um coletor de fixture que falha grava log sem a senha colocada no ambiente do teste, e a home ainda devolve 200.
- [ ] `exigir_spec_done("146")`. Sem internet.

## Invariantes de produção
- A home publicada devolve 200 com o aviso legal no rodapé mesmo quando um painel está indisponível.
- Card crítico sem snapshot não mostra variação numérica.
- Log de falha de coleta acessível em `/api/coleta` ou no registrador do processo não inclui segredo. A checagem automática olha o teste; o auditor não precisa abrir o console do navegador.

## Fora do escopo
- Nomear ou "corrigir" os dois erros de 05/11/2026 antes de capturá-los.
- Silenciar `console.error` de terceiros.
- Trocar Plotly ou htmx de CDN.
- Suite de navegador permanente. O PR de implementação pode anexar o console real; o aceite desta spec é o DOM sem rede.

## Plano de validação
`pytest -q tests/test_aceite_146.py` sem internet. O PR de implementação inclui o recorte do console da home, de manhã ou de tarde de um pregão, separado em erro da aplicação e ruído externo. Esta rodada não fabrica esse recorte. A spec aberta não significa que o console já foi limpo.
