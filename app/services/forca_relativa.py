import json
from app.database import get_latest_forca_relativa_data


def get_forca_relativa_view_data() -> dict | None:
    data = get_latest_forca_relativa_data()
    if not data:
        return None

    try:
        maior = json.loads(data.maior_json)
        menor = json.loads(data.menor_json)
    except json.JSONDecodeError:
        return None

    return {
        "maior": maior,
        "menor": menor,
        "timestamp": data.timestamp,
        "fonte": data.fonte,
    }
