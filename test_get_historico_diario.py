import re
with open('app/database.py', 'r') as f:
    content = f.read()

res = re.search(r'def get_historico_diario.*?def', content, re.DOTALL)
if res:
    print(res.group(0))
