# Skill · Destravar um PR aberto

Use no Passo 2, quando `python -m devagent.estado_github` mostrar um PR do agente aberto, ou quando o guardião comentar `@jules` num PR seu.

Um PR aberto bloqueia todo o ciclo, porque só pode existir um de cada vez. Destravá-lo tem prioridade sobre qualquer trabalho novo.

## 1. Ir para a branch do PR

```bash
git fetch origin
git checkout -B <branch> origin/<branch>
```

Trabalhe **sempre nesta branch** e dê push nela. Nunca abra PR novo para o mesmo trabalho.

**Ambiente reiniciado.** Se as suas alterações sumiram, o diretório voltou para a `main` ou você não reconhece o estado do repositório, o trabalho não se perdeu: ele está na branch do PR, no GitHub. Rode os dois comandos acima e continue dali. Não recomece da `main`, não recrie a spec e não pergunte se deve continuar: ninguém vai responder, e a sessão fica parada até o guardião fechar o PR (ADR 009).

## 2. CI falhando

Reproduza exatamente o que o CI roda:

```bash
make install
make verify
# smoke: só dependências de produção, num ambiente limpo
python -m venv /tmp/prod && . /tmp/prod/bin/activate
make install-prod PY=python && make smoke PY=python
deactivate
```

Os alvos são o contrato do projeto (`Makefile`, seção `[verificacao]` do `devagent.toml`): o que cada um roda por dentro depende do stack.

Se o guardião colou o log da falha no PR, comece por ele. Corrija a causa, não o sintoma. Nunca apague nem desative teste. Rode tudo de novo antes do push.

**Formatação reprovada**: rode o formatador do stack (veja o `Makefile`) e faça commit. **Hook de pre-commit barrando o commit**: leia a mensagem do hook, corrija o que ele aponta e faça o commit de novo. Nunca use `--no-verify`.

## 3. Conflito com a `main`

Meça antes de resolver:

```bash
git merge --no-commit --no-ff origin/main
git diff --name-only --diff-filter=U        # arquivos em conflito
```

- **Pequeno** (até 3 arquivos e cerca de 40 linhas em conflito): resolva, rode a verificação completa da seção 2, faça commit do merge e dê push.
- **Grande**: `git merge --abort` e não resolva. O guardião fecha o PR na próxima varredura; a spec continua `ready` na `main` e o próximo ciclo refaz o trabalho sobre a `main` atual. Registre no relatório e encerre.

Na resolução, a versão da `main` vence em tudo que não for o objetivo do seu PR. Nunca reescreva um arquivo inteiro a partir da sua cópia: isso apaga o trabalho de outros PRs.

## 4. Comentários de revisão

Aplique as correções pedidas ou responda explicando por que não aplicou.

## 5. Se não conseguir dar push na branch do PR

Crie uma branch nova a partir da `main`, traga as mudanças do PR antigo (`git checkout origin/<branch-antiga> -- <arquivos>`), aplique a correção e abra um PR cujo corpo contenha `Substitui #N`. O guardião fecha o #N automaticamente. É a única exceção à regra de um PR por vez.

## 6. O que o guardião faz se nada disso acontecer

O workflow `pr-guardiao.yml` comenta `@jules` a cada falha de CI (até 3 vezes), fecha o PR se não houver commit novo em 3 horas depois da cobrança, fecha PRs com conflito grande e abre uma issue `tentativa-falhou` explicando o motivo. Antes de refazer um trabalho, leia essas issues (Passo 4).
