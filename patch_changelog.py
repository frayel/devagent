with open("CHANGELOG.md", "r") as f:
    content = f.read()

content = content.replace("## [Unreleased]", "## [Unreleased]\n- Histórico dos últimos 5 pregões na página inicial e consultor, permitindo navegar em snapshots passados via URL (`/?data=AAAA-MM-DD`) e consultar o diário do consultor (spec 078).")

with open("CHANGELOG.md", "w") as f:
    f.write(content)
