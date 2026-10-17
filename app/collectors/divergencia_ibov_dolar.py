import logging
from datetime import datetime, timezone
import math
from app.collectors.utils import fetch_with_retry
from app.database import save_divergencia_ibov_dolar

logger = logging.getLogger(__name__)


def collect_and_save() -> bool:
    try:
        data_ibov_response = fetch_with_retry(
            "https://query2.finance.yahoo.com/v8/finance/chart/^BVSP",
            params={"interval": "5m", "range": "1d"},
        )
        data_dolar_response = fetch_with_retry(
            "https://query2.finance.yahoo.com/v8/finance/chart/BRL=X",
            params={"interval": "5m", "range": "1d"},
        )

        data_ibov = data_ibov_response.json()
        data_dolar = data_dolar_response.json()

        if not data_ibov or not data_dolar:
            return False

        try:
            res_ibov = data_ibov.get("chart", {}).get("result", [])[0]
            timestamps_ibov = res_ibov.get("timestamp", [])
            closes_ibov = (
                res_ibov.get("indicators", {}).get("quote", [{}])[0].get("close", [])
            )

            res_dolar = data_dolar.get("chart", {}).get("result", [])[0]
            timestamps_dolar = res_dolar.get("timestamp", [])
            closes_dolar = (
                res_dolar.get("indicators", {}).get("quote", [{}])[0].get("close", [])
            )
        except (IndexError, TypeError, AttributeError):
            return False

        if (
            not timestamps_ibov
            or not closes_ibov
            or not timestamps_dolar
            or not closes_dolar
        ):
            return False

        ibov_dict = {
            t: c for t, c in zip(timestamps_ibov, closes_ibov) if c is not None
        }
        dolar_dict = {
            t: c for t, c in zip(timestamps_dolar, closes_dolar) if c is not None
        }

        common_timestamps = sorted(list(set(ibov_dict.keys()) & set(dolar_dict.keys())))

        # Consider the last hour (approx 12 points of 5m data)
        common_timestamps = common_timestamps[-12:]

        if len(common_timestamps) < 2:
            return False

        ibov_vals = [ibov_dict[t] for t in common_timestamps]
        dolar_vals = [dolar_dict[t] for t in common_timestamps]

        # Calculate returns to avoid non-stationarity
        ibov_returns = [
            (ibov_vals[i] - ibov_vals[i - 1]) / ibov_vals[i - 1]
            for i in range(1, len(ibov_vals))
        ]
        dolar_returns = [
            (dolar_vals[i] - dolar_vals[i - 1]) / dolar_vals[i - 1]
            for i in range(1, len(dolar_vals))
        ]

        n = len(ibov_returns)
        if n < 2:
            return False

        mean_ibov = sum(ibov_returns) / n
        mean_dolar = sum(dolar_returns) / n

        num = sum(
            (i - mean_ibov) * (d - mean_dolar)
            for i, d in zip(ibov_returns, dolar_returns)
        )
        den_ibov = sum((i - mean_ibov) ** 2 for i in ibov_returns)
        den_dolar = sum((d - mean_dolar) ** 2 for d in dolar_returns)

        if den_ibov == 0 or den_dolar == 0:
            corr = 0.0
        else:
            corr = num / math.sqrt(den_ibov * den_dolar)

        divergencia_detectada = corr > 0.3  # If correlation is noticeably positive

        save_divergencia_ibov_dolar(
            divergencia_detectada, corr, datetime.now(timezone.utc)
        )
        return True

    except Exception as e:
        logger.exception("Erro ao coletar divergencia ibov dolar: %s", e)
        return False
