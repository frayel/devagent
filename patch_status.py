with open("docs/specs/078-historico-cinco-pregoes.md", "r") as f:
    content = f.read()

content = content.replace("status: ready", "status: done")

with open("docs/specs/078-historico-cinco-pregoes.md", "w") as f:
    f.write(content)
