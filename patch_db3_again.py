import re

with open("app/database.py", "r") as f:
    content = f.read()

dataclass_code = """
@dataclass
class RelogioVolatilidadeData:
    id: int
    timestamp: datetime
    alertas_json: str
    fonte: str
"""
if "@dataclass\\nclass RelogioVolatilidadeData" not in content:
    content = re.sub(
        r"(@dataclass\nclass ScannerCapitulacaoData:)",
        dataclass_code + r"\n\n\1",
        content,
    )
else:
    content = content.replace(dataclass_code, "")
    content = re.sub(
        r"(@dataclass\nclass ScannerCapitulacaoData:)",
        dataclass_code + r"\n\n\1",
        content,
    )

with open("app/database.py", "w") as f:
    f.write(content)
