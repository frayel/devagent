# ADR 016 · O ciclo lê a página de saúde do produto

- **Data:** 2026-10-19 · **Status:** aceita
- **Complementa:** ADR 002 (correções no Passo 1)

## Contexto

O Passo 1 confere produção por três sinais: issues `deploy-falhou`, o status da plataforma e `make audit`. Eles respondem se o deploy subiu e se o dado exibido está certo. Não respondem se a operação em volta continua de pé. Em 19/10 a auditoria de produção, agendada para rodar a cada 30 min, estava sem execução agendada desde o dia anterior, porque o GitHub descarta crons quando está sobrecarregado. Nenhum sinal do ciclo via isso.

O produto passou a publicar uma página de saúde com integrações, coleta, deploy, workflows e o fluxo do agente, cada item com nível: problema, atenção, ok ou inativo.

## Decisão

- O núcleo define um contrato mínimo de saúde (`devagent/saude.py`): um JSON com `geral.nivel` e `geral.pendentes`, cada pendente com nível, grupo, nome, resumo e detalhe, e um `parcial` opcional enquanto o produto não terminou a primeira leitura. O caminho fica em `[saude]` no `devagent.toml`; a senha, em `SAUDE_SENHA`. O núcleo não interpreta os itens, só os níveis.
- `estado_github`, o primeiro comando de toda execução, mostra o resumo da página.
- O `auditoria-producao.yml` lê a página depois de cada deploy e nos horários da auditoria. Problema abre ou atualiza uma issue `sistema-com-problema`; sem problema, a issue fecha. A issue só fecha pela verificação, nunca pelo `Closes #N` de um PR.
- No Passo 1, o agente corrige o que tem causa no repositório. O que depende de configuração externa recebe a descrição exata do ajuste e o label `bloqueado`, e o ciclo segue. Quando a lista de problemas muda, o workflow tira o `bloqueado`, porque o bloqueio anterior não cobre os problemas novos.
- Itens em atenção não bloqueiam o ciclo: são a primeira medida da rodada de manutenção.

## Consequências

- Falhas silenciosas de operação (agendamento perdido, integração caída, relógio externo parado) passam a chegar ao agente como qualquer outra falha de produção.
- Um problema fora do alcance do agente não trava o ciclo: fica bloqueado à espera de uma pessoa, com o ajuste descrito.
- Ler a página acorda o serviço hibernado. A leitura acontece só junto da auditoria e no início das sessões, que já acordavam o serviço.
- Projetos sem página de saúde deixam `[saude] caminho` vazio e nada muda.
