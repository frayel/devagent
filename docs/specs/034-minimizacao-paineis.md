---
id: 034
titulo: Minimização de Painéis Indisponíveis (Revisão de Experiência)
status: ready
esforco: P
---

## Problema
Consigo achar o que preciso, rápido? Atualmente, os painéis como "Concentração Setorial" e "Concentração de Ganhos" ocupam grande espaço na tela, exibindo apenas "Dado indisponível agora" quando falham ou ainda não há dados suficientes, empurrando informações relevantes (como a Anomalia de Peso, que no caso só precisa de um pouco mais de espaço se estiver preenchida) ou desbalanceando a página e forçando rolagem inútil.

## Comportamento esperado
Os painéis da interface que recebem "Dado indisponível agora" (em especial Concentração Setorial e Concentração de Ganhos) devem ser ocultados usando uma classe CSS especial (`display: none`) ou devem ser simplificados para um estado minimizado.
Decisão: Em vez de ocultá-los totalmente (o que mudaria os Invariantes de que eles *devem* estar lá quando chamados no `/api/snapshot`), iremos aplicar uma classe CSS `.indisponivel` ao componente que, via JS/CSS, reduz sua altura visual, e não renderizará seu conteúdo de `O mercado opera em alta...` usando o bloco principal que gasta muito espaço com margens vazias, exibindo uma tarja cinza simples, permitindo mais informação na tela.
Dado que a macro `painel` em `app/templates/componentes.html` possui lógica para isso, vamos ajustar como a degradação "Dados indisponíveis" é mostrada quando a variável passada for `None`. A especificação mais limpa será simplesmente não gerar o `div.painel` inteiro, ou aplicar uma tag HTMX/CSS `style="display: none;"` se a variável do painel (ex: `concentracao`, `concentracao_setorial`) for vazia ou inválida. Como `/api/snapshot` é independente do HTML gerado nos painéis não preenchidos (se implementarmos para que continue gerando os links vazios na API mas não no front).

MUDANÇA ESCOLHIDA: Ajustar `app/templates/index.html` e a macro `painel` para que, se um painel essencial de ranking ou alertas (ex: Concentração Setorial, Concentração de Ganhos, Anomalia de Peso) não tiver dados (a variável é `None`), ele aplique uma classe CSS (ex: `escondido`) que dá `display: none` nele, não gerando poluição visual, apenas ocultando.

## Fontes de dados
Nenhuma nova fonte. Reorganização visual/CSS da view.

## Cálculos
Sem novos cálculos.

## Critérios de aceite
- [ ] A página `index.html` oculta painéis específicos (Concentração Setorial, Concentração de Ganhos) quando os dados não estão disponíveis (ex. `concentracao_setorial is none`), usando uma classe css `escondido` que tenha `display: none`.
- [ ] As telas de screenshot (via `make telas`) não devem quebrar a renderização, pois o grid se refaz automaticamente.
- [ ] Os invariantes de `/api/snapshot` permanecem ilesos (o JSON continua devolvendo chaves vazias ou adequadas, pois isso ocorre em `main.py`).

## Invariantes de produção
- A página continua rendendo 200 OK e passa nos testes do `make audit`.
- `/api/snapshot` não sofre alteração e continua passando nos testes, a modificação é exclusivamente visual via classe CSS ou condicional de template.

## Fora do escopo
Não alteraremos a estrutura JSON do `/api/snapshot`.
