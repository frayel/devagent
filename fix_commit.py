import subprocess
print("Changing commit message...")
subprocess.run(["git", "commit", "--amend", "-m", "O pedido está errado ou o servidor falhou? Detalhar falhas no registro (090a)\n\nImplementa a spec."], check=True)
