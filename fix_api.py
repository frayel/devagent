with open("app/main.py", "r") as f:
    lines = f.readlines()

with open("app/main.py", "w") as f:
    for i, line in enumerate(lines):
        # Remove the rogue "else" and "resp" from lines 251 and 252 (0-indexed 250, 251)
        if i in [250, 251] and (
            "else:" in line or 'resp["paineis"]["atrasadas_rally"]' in line
        ):
            continue
        f.write(line)
