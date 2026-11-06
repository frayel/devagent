from datetime import datetime, timezone
import json
from app.database import (
    save_ibovespa_data,
    IbovespaData,
)


def test_timezone_regression_bug_764(monkeypatch):
    """
    Testa se o datetime de coleta gravado no banco está utilizando o timezone de BRT (UTC-3).
    A issue #764 mostrou que snapshots coletados após as 21:00 BRT eram registrados com
    a data do dia seguinte por estarem em UTC.
    """
    import app.banco

    called_with = {}

    def fake_gravar_snapshot(painel, data_referencia, estado, fonte, payload):
        called_with["data_referencia"] = data_referencia
        called_with["payload"] = payload

    monkeypatch.setattr(app.banco, "gravar_snapshot", fake_gravar_snapshot)

    # 2026-11-05 23:13:00 BRT (which is 2026-11-06 02:13:00 UTC)
    dt_utc = datetime(2026, 11, 6, 2, 13, tzinfo=timezone.utc)

    data = IbovespaData(
        timestamp=dt_utc,
        current_price=100.0,
        previous_close=90.0,
        history_json=json.dumps({"dates": [], "closes": []}),
        fonte="mock",
    )

    save_ibovespa_data(data)

    # 2026-11-05 23:13 BRT -> data de referencia deve ser 2026-11-05 e não 2026-11-06
    assert called_with["data_referencia"].isoformat() == "2026-11-05"
