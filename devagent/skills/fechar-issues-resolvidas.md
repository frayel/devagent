# Skill · Fechar issues resolvidas ("issues fantasmas")

Use no Passo 6, quando investigar uma issue aberta e perceber que ela já foi resolvida (o código em `main` já contempla a solução ou não existe mais bug reportado), mas a issue continua aberta no repositório.

## O problema

- Se uma issue é sanada em um PR que não a citou com `Closes #N`, ela fica pendente.
- Como o agente não tem autorização (ou CLI) para fechar a issue diretamente, e commits vazios com `Closes #N` se perdem no squash merge do GitHub Actions (impedindo o fechamento automático da issue), é preciso um PR real.

## Procedimento para fechamento seguro

1. Verifique na branch atual (`main`) se o problema relatado pela issue de fato não ocorre ou se a documentação/especificação foi devidamente alterada no passado.
2. Não tente criar "commits vazios" (`git commit --allow-empty -m "Closes #N"`). Eles são descartados pelo `automerge.yml`.
3. Abra um PR com prefixo `docs:` que resolve a questão. O caminho mais direto e seguro sem alterar o comportamento do sistema é aproveitar o relatório da própria execução:
   - Garanta que as suas conclusões estejam detalhadas na seção de O que foi feito/Retrospectiva no relatório `docs/runs/AAAA-MM-DD-HHMM.md`.
   - Adicione o relatório ao commit.
4. O corpo do PR deve conter a diretriz `Closes #N`.
5. Se for possível/adequado, você pode complementar a ação atualizando outro documento `docs/` para consolidar o porquê de estar fechando (ex: aprimorando `docs/STATE.md`).

Assim, o PR `docs:` carregará um commit válido (a adição de um arquivo markdown real), e ao passar pelo `automerge.yml`, a issue será corretamente fechada pela plataforma.