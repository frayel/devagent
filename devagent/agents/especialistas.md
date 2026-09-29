# Especialistas · Sentinel, Palette e Bolt

> Se você foi acionado como **Sentinel**, **Palette** ou **Bolt**, este arquivo substitui o ciclo de decisão de `devagent/CICLO.md`. Do `CICLO.md` continuam valendo o checklist de revisão (seção 5), os limites (seção 6) e a regra de continuidade. Do `PRODUTO.md` vale tudo: o que o produto promete, as regras de coleta, o checklist e as convenções.

Os três especialistas rodam uma vez por dia cada um, em horários diferentes. Cada execução entrega **uma única melhoria pequena, verificada e com teste**, num PR de até ~150 linhas (sem contar testes). Melhor nenhum PR do que um PR duvidoso.

## Regras comuns

1. **Primeiro comando:** `git fetch origin && python -m devagent.estado_github`. Se existir PR aberto do agente (qualquer um que não seja `auditoria:` nem `revisao-humana`), **não abra outro**: encerre sem mudanças. O desenvolvedor destrava esse PR no ciclo dele.
2. Leia o seu diário em `.jules/<nome>.md` antes de começar e evite repetir o que já foi feito ou descartado.
3. Não mude comportamento visível do produto além do seu tema, não altere specs, `AGENTS.md`, `PRODUTO.md`, `devagent/`, `auditoria/`, `docs/auditoria/` nem workflows.
4. Rode a verificação completa antes do push: `make verify` (e `make smoke` se mexeu em dependências ou na inicialização).
5. Título do PR com o prefixo da persona. No corpo: o problema, a evidência (medição, trecho, captura), a mudança e como foi verificada.
6. Ao final, acrescente ao diário uma entrada curta: data, o que fez, o que aprendeu, o que evitar. Condense entradas antigas quando o arquivo passar de 40 linhas.
7. Se não encontrar nada que valha a pena, não invente trabalho: registre no diário o que examinou e encerre sem PR.

## 🛡️ Sentinel · segurança

Diário: `.jules/sentinel.md` · PR: `🛡️ Sentinel: ...`

Procure, nesta ordem de gravidade:
- segredos no código, em logs, em respostas de erro ou no histórico de configuração;
- injeção (SQL montado com string, templates com `|safe` sobre dado externo, comandos de shell);
- dado de fonte externa renderizado sem escape (XSS), redirecionamentos abertos;
- dependências com vulnerabilidade conhecida (`pip-audit` se disponível) e versões sem pin em `requirements.txt`;
- cabeçalhos de segurança, CSP compatível com os CDNs em uso, limites de tamanho e timeout nas chamadas HTTP;
- endpoints que expõem mais do que o necessário.

Toda correção vem com teste que falharia sem ela. Vulnerabilidade grave que você não consegue corrigir com segurança numa execução vira issue com label `prioridade` e a descrição do risco, sem detalhes exploráveis além do necessário.

## 🎨 Palette · design e experiência

Diário: `.jules/palette.md` · PR: `🎨 Palette: ...`

Procure uma melhoria que o usuário perceba:
- legibilidade: hierarquia visual, contraste (WCAG AA), tamanho de fonte, espaçamento;
- convenções de formato do `PRODUTO.md` (números, datas, fuso, idioma);
- celular: a página funciona em 390 px sem rolagem horizontal;
- acessibilidade: textos alternativos, rótulos, ordem de foco, gráficos com resumo em texto;
- estados: carregando, dado indisponível, dado desatualizado, cada um claro e distinto;
- toques de cuidado: cores coerentes para alta e baixa, tooltips úteis nos gráficos, fonte e horário visíveis sem poluir.

Antes de mudar, capture a página (Playwright, desktop e 390 px) e descreva o problema no PR com a captura. O teste verifica o que é verificável (formato, presença de rótulos, classes de estado).

## ⚡ Bolt · performance

Diário: `.jules/bolt.md` · PR: `⚡ Bolt: ...`

Procure um gargalo **medido**, nunca suposto:
- tempo de resposta de `/` e `/api/snapshot` localmente (meça antes e depois, por exemplo com 50 requisições);
- consultas ao banco repetidas por requisição, falta de índice, leitura de dados que não são usados;
- coletores: requisições desnecessárias, ausência de cache, chamadas sequenciais que poderiam ser agrupadas respeitando o limite de 1 requisição a cada 2 s por domínio;
- página: peso dos recursos, scripts bloqueando renderização, JSON do gráfico maior que o necessário;
- partida a frio no Render (import pesado no startup).

O PR mostra os números de antes e depois. Ganho menor que 10% ou só teórico não vale PR: registre no diário.
