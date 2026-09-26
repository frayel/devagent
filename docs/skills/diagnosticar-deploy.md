# Skill · Diagnosticar deploy quebrado no Render

Use no Passo 1 quando houver issue `deploy-falhou`, quando `scripts/render_status.py` sair com código 1, ou quando `/healthz` de produção não responder.

## 1. Juntar evidências

- Leia a issue `deploy-falhou` mais recente: ela traz `status`, `commit` e as últimas linhas de log.
- Se tiver `RENDER_API_KEY` e `RENDER_SERVICE_ID`, rode `python scripts/render_status.py` para ver o estado atual (o problema pode já ter mudado).
- Anote em qual fase falhou, pelo `status`:
  - `build_failed`: falhou o `buildCommand` (instalação de dependências, versão do Python).
  - `update_failed`: o build passou mas a aplicação não subiu ou não respondeu ao `healthCheckPath`.
  - `pre_deploy_failed`: falhou o comando de pré-deploy, se existir.

## 2. Reproduzir localmente

```bash
python3.12 -m venv /tmp/prod && . /tmp/prod/bin/activate
pip install -r requirements.txt          # só produção, como o Render
PORT=8000 <startCommand do render.yaml> &
curl -fsS localhost:8000/healthz && curl -fsS -o /dev/null localhost:8000/
```

## 3. Causas frequentes (confira antes de inventar hipóteses)

| Sintoma no log | Causa provável | Correção |
|---|---|---|
| `ModuleNotFoundError` | dependência só em `requirements-dev.txt` | mover para `requirements.txt` |
| erro de sintaxe ou de wheel na instalação | versão do Python diferente da esperada | fixar a versão (arquivo `.python-version` ou variável `PYTHON_VERSION` no `render.yaml`) |
| `No open ports detected` / timeout no health check | app não escuta em `0.0.0.0:$PORT` | ajustar `startCommand` |
| erro em import ao iniciar | código executado no import (ex.: acesso a banco ou rede no topo do módulo) | mover para o evento de startup ou para a função |
| `sqlite3.OperationalError` | caminho do banco não gravável ou disco efêmero | usar caminho configurável por variável; ver `docs/context/operacao.md` |
| campo desconhecido no Blueprint | chave obsoleta no `render.yaml` | conferir a documentação atual do Blueprint |

## 4. Corrigir e provar

- Escreva a correção e, se couber, um teste que falharia antes.
- Confirme que o job `smoke` do CI cobre o caso. Se não cobrir, melhore o job no mesmo PR.
- PR com prefixo `fix:` e `Closes #N`. O workflow `deploy-check.yml` fecha a issue sozinho quando o próximo deploy ficar `live`.

## 5. Quando não dá para corrigir pelo código

Se a causa estiver no painel do Render (variável ausente, plano, disco, região), comente na issue o ajuste exato que um humano precisa fazer, aplique o label `bloqueado` e encerre.

## 6. Aprender

Se a causa não estava na tabela da seção 3, acrescente uma linha a ela no mesmo PR.
