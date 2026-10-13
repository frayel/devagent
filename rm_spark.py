import re

with open("tests/test_mare.py", "r") as f:
    content = f.read()

content = re.sub(r'def _spark\(cesta, lote\):.*?\}\n    \}\n\n', '', content, flags=re.DOTALL)

with open("tests/test_mare.py", "w") as f:
    f.write(content)
