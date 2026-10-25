with open("docs/specs/088-seletor-de-pregao-pagina-inicial.md", "r") as f:
    content = f.read()

content = content.replace("status: ready", "status: done")

with open("docs/specs/088-seletor-de-pregao-pagina-inicial.md", "w") as f:
    f.write(content)
