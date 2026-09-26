# Skill · Destravar um PR aberto

Use no Passo 2, quando `python scripts/estado_github.py` mostrar um PR do agente aberto, ou quando o guardião comentar `@jules` num PR seu.

Um PR aberto bloqueia todo o ciclo, porque só pode existir um de cada vez. Destravá-lo tem prioridade sobre qualquer trabalho novo.

## 1. Ir para a branch do PR

```bash
git fetch origin
git checkout -B <branch> origin/<branch>
```

Trabalhe **sempre nesta branch** e dê push nela. Nunca abra PR novo para o mesmo trabalho.

## 2. CI falhando

Reproduza exatamente o que o CI roda:

```bash
pip install -r requirements-dev.txt
ruff check . && ruff format --check .
mypy app
pytest -q
# smoke: só dependências de produção
python -m venv /tmp/prod && /tmp/prod/bin/pip install -q -r requirements.txt
PORT=8000 /tmp/prod/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 &
sleep 3 && curl -fsS localhost:8000/healthz && curl -fsS -o /dev/null localhost:8000/
```

Se o guardião colou o log da falha no PR, comece por ele. Corrija a causa, não o sintoma. Nunca apague nem desative teste. Rode tudo de novo antes do push.

**Formatação reprovada** (`ruff format --check`): rode `ruff format .` e faça commit. **Hook de pre-commit barrando o commit**: leia a mensagem do hook, corrija o que ele aponta e faça o commit de novo. Nunca use `--no-verify`.

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
