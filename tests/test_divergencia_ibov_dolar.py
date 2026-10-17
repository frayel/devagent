import pytest
import respx
from app.collectors.divergencia_ibov_dolar import collect_and_save
from app.database import get_divergencia_ibov_dolar


@pytest.fixture
def mock_divergencia_sucesso():
    with respx.mock(assert_all_called=False) as mock:
        mock.get("https://query2.finance.yahoo.com/v8/finance/chart/^BVSP").respond(
            json={
                "chart": {
                    "result": [
                        {
                            "timestamp": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13],
                            "indicators": {
                                "quote": [
                                    {
                                        "close": [
                                            100,
                                            101,
                                            102,
                                            103,
                                            104,
                                            105,
                                            106,
                                            107,
                                            108,
                                            109,
                                            110,
                                            111,
                                            112,
                                        ]
                                    }
                                ]
                            },
                        }
                    ]
                }
            }
        )
        mock.get("https://query1.finance.yahoo.com/v8/finance/chart/^BVSP").respond(
            json={
                "chart": {
                    "result": [
                        {
                            "timestamp": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13],
                            "indicators": {
                                "quote": [
                                    {
                                        "close": [
                                            100,
                                            101,
                                            102,
                                            103,
                                            104,
                                            105,
                                            106,
                                            107,
                                            108,
                                            109,
                                            110,
                                            111,
                                            112,
                                        ]
                                    }
                                ]
                            },
                        }
                    ]
                }
            }
        )
        mock.get("https://query2.finance.yahoo.com/v8/finance/chart/BRL=X").respond(
            json={
                "chart": {
                    "result": [
                        {
                            "timestamp": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13],
                            "indicators": {
                                "quote": [
                                    {
                                        "close": [
                                            5.0,
                                            5.1,
                                            5.2,
                                            5.3,
                                            5.4,
                                            5.5,
                                            5.6,
                                            5.7,
                                            5.8,
                                            5.9,
                                            6.0,
                                            6.1,
                                            6.2,
                                        ]
                                    }
                                ]
                            },
                        }
                    ]
                }
            }
        )
        mock.get("https://query1.finance.yahoo.com/v8/finance/chart/BRL=X").respond(
            json={
                "chart": {
                    "result": [
                        {
                            "timestamp": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13],
                            "indicators": {
                                "quote": [
                                    {
                                        "close": [
                                            5.0,
                                            5.1,
                                            5.2,
                                            5.3,
                                            5.4,
                                            5.5,
                                            5.6,
                                            5.7,
                                            5.8,
                                            5.9,
                                            6.0,
                                            6.1,
                                            6.2,
                                        ]
                                    }
                                ]
                            },
                        }
                    ]
                }
            }
        )
        yield mock


@pytest.fixture
def mock_divergencia_falha():
    with respx.mock(assert_all_called=False) as mock:
        mock.get("https://query2.finance.yahoo.com/v8/finance/chart/^BVSP").respond(
            status_code=500
        )
        mock.get("https://query1.finance.yahoo.com/v8/finance/chart/^BVSP").respond(
            status_code=500
        )
        yield mock


def test_divergencia_sucesso(mock_divergencia_sucesso):
    assert collect_and_save() is True
    data = get_divergencia_ibov_dolar()
    assert data is not None
    assert data["divergencia_detectada"] is True
    assert data["correlacao"] > 0


def test_divergencia_falha(mock_divergencia_falha):
    assert collect_and_save() is False
    assert get_divergencia_ibov_dolar() is None
