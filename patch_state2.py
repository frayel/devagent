with open("docs/STATE.md", "r") as f:
    content = f.read()

impl = """## Implementado

- Spec 078 (Histórico dos últimos 5 pregões):
  - Adicionado seletor de datas ao topo da página e `/consultor` permitindo navegação via HTMX entre os últimos pregões.
  - Implementada política de retenção de 30 pregões de snapshots com limpeza agendada diária.
  - Funções de acesso de painéis adaptadas para suportar `data_referencia`.
"""

content = content.replace("## Implementado\n", impl)

with open("docs/STATE.md", "w") as f:
    f.write(content)
