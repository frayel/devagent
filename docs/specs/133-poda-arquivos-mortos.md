---
id: 133
titulo: Poda de arquivos mortos e configuração de log na importação
status: ready
esforco: P
gaveta: poda
aceite: tests/test_aceite_133.py
---

## Problema
A revisão de 28/10/2026 achou código e arquivos que não servem a nada e confundem quem lê:

- `app/agendador_patched.py`: cópia do agendador sem a janela `fechamento`, importada por ninguém. Quem procura a lógica de coleta acha duas versões divergentes.
- Em `app/main.py`, `security = HTTPBasic()` e `verificar_credenciais`: nunca usados (as rotas usam `exigir_senha`).
- Na raiz, versionados: `test.db`, `commit_body.txt`, `commit_description.txt`, `generate_plan.sh`, `screenshot_desktop.png`, `telas_desktop.png` e `verification.png`, que são restos de sessões.
- 21 módulos de `app/` chamam `logging.basicConfig(level=logging.INFO)` na importação, o que configura o log global como efeito colateral de importar um coletor.

## Comportamento esperado
- Os arquivos e símbolos listados saem. Antes de apagar cada arquivo da raiz, confirmar com `grep -rn <nome>` que nada o referencia (workflow, Makefile, docs ativos).
- O log é configurado num único lugar, no início de `app/main.py`. Os módulos só fazem `logger = logging.getLogger(__name__)`.
- `.gitignore` passa a ignorar `*.db` e `*.png` na raiz, e `commit_*.txt`.

## Fontes de dados
Nenhuma.

## Cálculos
Nenhum.

## Critérios de aceite
- [ ] `tests/test_aceite_133.py` reprova se existir `app/agendador_patched.py`, se `app/main.py` definir `verificar_credenciais`, ou se algum arquivo de `app/` (fora de `app/main.py`) contiver `logging.basicConfig`.
- [ ] O mesmo teste reprova se `test.db` ou `commit_body.txt` estiverem versionados (`git ls-files`).
- [ ] `make verify` continua verde.
- Arquivos tocados: `app/agendador_patched.py` (remoção), `app/main.py`, os 21 módulos com `basicConfig` (uma linha cada), `.gitignore`, os arquivos da raiz e o novo `tests/test_aceite_133.py`.

## Invariantes de produção
- Os logs do Render continuam com nível INFO e o nome do módulo em cada linha.

## Fora do escopo
- Código morto dentro de coletores (issue #557, tratada à parte).
- `__pycache__` (já ignorado).
