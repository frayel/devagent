import json
from datetime import datetime, timezone

from app.database import VolumeAlertsData, save_volume_alerts_data
from app.services.volume_alerts import get_volume_alerts_view_data


def test_get_volume_alerts_view_data_none(setup_db):
    assert get_volume_alerts_view_data() is None


def test_get_volume_alerts_view_data_formatting(setup_db):
    alerts = [
        {"ticker": "PETR4", "ratio": 2.5, "price": 35.50},
        {"ticker": "VALE3", "ratio": 1.6, "price": 60.00},
    ]

    data = VolumeAlertsData(
        timestamp=datetime(2026, 9, 30, 10, 0, 0, tzinfo=timezone.utc),
        alerts_json=json.dumps(alerts),
        fonte="yfinance",
    )
    save_volume_alerts_data(data)

    view_data = get_volume_alerts_view_data()
    assert view_data is not None
    assert view_data["fonte"] == "yfinance"
    assert view_data["time"] == "30/09/2026 10:00:00 UTC"

    formatted = view_data["alerts"]
    assert len(formatted) == 2

    # 2.5 ratio means 250% according to the logic implemented
    assert formatted[0]["ticker"] == "PETR4"
    assert formatted[0]["ratio_formatted"] == "+250%"
    assert formatted[0]["price_formatted"] == "R$ 35,50"

    # 1.6 ratio means 160%
    assert formatted[1]["ticker"] == "VALE3"
    assert formatted[1]["ratio_formatted"] == "+160%"
    assert formatted[1]["price_formatted"] == "R$ 60,00"
