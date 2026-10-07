from datetime import timezone, timedelta
from app.database import get_latest_forca_relativa_data
from app.services.sparkline import build_sparkline


def get_forca_relativa_view_data() -> dict | None:
    data = get_latest_forca_relativa_data()
    if not data:
        return None

    try:
        import json

        maior = json.loads(data.maior_json)
        menor = json.loads(data.menor_json)
        maior["sparkline_svg"] = build_sparkline(maior.get("sparkline", []))
        menor["sparkline_svg"] = build_sparkline(menor.get("sparkline", []))
    except json.JSONDecodeError:
        return None

    return {
        "maior": maior,
        "menor": menor,
        "time": data.timestamp.astimezone(timezone(timedelta(hours=-3))).strftime(
            "%d/%m/%Y %H:%M:%S BRT"
        ),
        "timestamp": data.timestamp,
        "fonte": data.fonte,
    }
