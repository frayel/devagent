with open('docs/STATE.md', 'r') as f:
    text = f.read()

# Since it modifies a section, does it count?
# "inclusive os contadores das cadências do Passo 7: o de experiência, se a spec acrescenta um painel, seção ou tela"
# The spec does not add a panel, section or screen. It replaces a generic message in an existing section.
# So we do not increment the experience counter.
