from datetime import datetime, timezone
from fastapi.testclient import TestClient

from app.database import HighlightsData, save_highlights_data
from app.main import app
from app.services.highlights import get_highlights_view_data
from app.services.manchete import (
    ALTA_AMPLA,
    INDISPONIVEL,
    MISTO,
    gerar_manchete,
)
from devagent.aceite import exigir_spec_done

client = TestClient(app)


def test_aceite_140_spec_done():
    exigir_spec_done("140")


def test_criterio_1_ibov_alta_poucas_altas_humor_misto():
    """Fixture Ibovespa +1,00%, revisao_variacao falso, up_count=2, down_count=28, total_count=30,

    três motores negativos, mesmo pregão: humor misto, frase contém sinal de alta,
    contagens 2 e 30, e não contém 'otimismo generalizado' nem 'alta ampla'.
    """
    ibov = {
        "variacao_pct": 1.0,
        "is_positive": True,
        "revisao_variacao": False,
        "pregao": "2026-11-05",
    }
    highs = {
        "up_count": 2,
        "down_count": 28,
        "total_count": 30,
        "pregao": "2026-11-05",
    }
    motores = [
        {"nome": "Financeiro", "variacao": -1.2},
        {"nome": "Commodities", "variacao": -0.8},
        {"nome": "Doméstico", "variacao": -0.5},
    ]

    manchete = gerar_manchete(ibov, highs, None, motores_data=motores)

    assert manchete.humor == MISTO
    texto_lower = manchete.texto.lower()
    assert "alta" in texto_lower
    assert "2" in manchete.texto
    assert "30" in manchete.texto
    assert "otimismo generalizado" not in texto_lower
    assert "alta ampla" not in texto_lower


def test_criterio_2_revisao_variacao_humor_misto():
    """O mesmo fixture com revisao_variacao verdadeiro: humor misto e frase contém 'revisão'."""
    ibov = {
        "variacao_pct": 1.0,
        "is_positive": True,
        "revisao_variacao": True,
        "pregao": "2026-11-05",
    }
    highs = {
        "up_count": 2,
        "down_count": 28,
        "total_count": 30,
        "pregao": "2026-11-05",
    }
    motores = [
        {"nome": "Financeiro", "variacao": -1.2},
        {"nome": "Commodities", "variacao": -0.8},
        {"nome": "Doméstico", "variacao": -0.5},
    ]

    manchete = gerar_manchete(ibov, highs, None, motores_data=motores)

    assert manchete.humor == MISTO
    texto_lower = manchete.texto.lower()
    assert "revisão" in texto_lower or "revisao" in texto_lower
    assert "otimismo generalizado" not in texto_lower
    assert "pessimismo generalizado" not in texto_lower
    assert "forte tomada de risco" not in texto_lower
    assert "alta ampla" not in texto_lower
    assert "queda generalizada" not in texto_lower


def test_criterio_3_alta_ampla_otimismo_generalizado():
    """Ibovespa +1,00%, up_count=20, down_count=8, total_count=30, motores positivos,

    apetite 'Tomando risco', sem revisão: humor alta_ampla e a frase da spec 022.
    """
    ibov = {
        "variacao_pct": 1.0,
        "is_positive": True,
        "revisao_variacao": False,
        "pregao": "2026-11-05",
    }
    highs = {
        "up_count": 20,
        "down_count": 8,
        "total_count": 30,
        "pregao": "2026-11-05",
    }
    motores = [
        {"nome": "Financeiro", "variacao": 1.0},
        {"nome": "Commodities", "variacao": 0.8},
        {"nome": "Doméstico", "variacao": 0.5},
    ]
    risco = {"estado": "Tomando risco"}

    manchete = gerar_manchete(ibov, highs, risco, motores_data=motores)

    assert manchete.humor == ALTA_AMPLA
    assert manchete == "Dia de otimismo generalizado com forte tomada de risco."


def test_criterio_4_dois_motores_negativos_humor_misto():
    """Ibovespa +1,00%, up_count=20, down_count=8, total_count=30, dois motores negativos: humor misto."""
    ibov = {
        "variacao_pct": 1.0,
        "is_positive": True,
        "revisao_variacao": False,
        "pregao": "2026-11-05",
    }
    highs = {
        "up_count": 20,
        "down_count": 8,
        "total_count": 30,
        "pregao": "2026-11-05",
    }
    motores = [
        {"nome": "Financeiro", "variacao": -0.8},
        {"nome": "Commodities", "variacao": -0.5},
        {"nome": "Doméstico", "variacao": 0.5},
    ]
    risco = {"estado": "Tomando risco"}

    manchete = gerar_manchete(ibov, highs, risco, motores_data=motores)

    assert manchete.humor == MISTO


def test_criterio_5_pregoes_diferentes_indisponivel():
    """Pregão do Ibovespa 2026-11-04 e pregão da dispersão 2026-11-05: humor indisponivel

    e a frase de painéis em pregões diferentes.
    """
    ibov = {
        "variacao_pct": 1.0,
        "is_positive": True,
        "pregao": "2026-11-04",
    }
    highs = {
        "up_count": 20,
        "down_count": 10,
        "total_count": 30,
        "pregao": "2026-11-05",
    }

    manchete = gerar_manchete(ibov, highs, None)

    assert manchete.humor == INDISPONIVEL
    assert (
        manchete
        == "Os painéis não estão no mesmo pregão; a leitura do dia fica suspensa."
    )
    assert "alta ampla" not in manchete.lower()
    assert "baixa ampla" not in manchete.lower()


def test_criterio_6_motores_ausentes():
    """Motores ausentes, dispersão presente, índice +1% e fracao_em_alta=0,70:

    a frase não inventa sinal de motor e diz que os motores faltaram; o humor não é alta_ampla
    só por isso se o apetite também faltar. Com apetite 'Tomando risco' e o item 6 satisfeito,
    alta_ampla é permitido e a frase não cita motor.
    """
    ibov = {
        "variacao_pct": 1.0,
        "is_positive": True,
        "revisao_variacao": False,
    }
    highs = {
        "up_count": 21,
        "down_count": 9,
        "total_count": 30,
        "fracao_em_alta": 0.70,
    }

    # Caso A: apetite faltante / neutro
    manchete_sem_risco = gerar_manchete(ibov, highs, None, motores_data=None)
    assert manchete_sem_risco.humor == MISTO
    texto_a = manchete_sem_risco.texto.lower()
    assert "motor" in texto_a and ("ausente" in texto_a or "falta" in texto_a)

    # Caso B: apetite "Tomando risco" e item 6 satisfeito
    manchete_com_risco = gerar_manchete(
        ibov, highs, {"estado": "Tomando risco"}, motores_data=None
    )
    assert manchete_com_risco.humor == ALTA_AMPLA
    assert (
        manchete_com_risco == "Dia de otimismo generalizado com forte tomada de risco."
    )
    assert "motor" not in manchete_com_risco.lower()


def test_criterio_7_gauge_e_legenda_dispersao_com_neutros():
    """up_count=2, down_count=8, total_count=20 (10 neutros): o gauge mostra 20% (2 / (2 + 8)),

    não 10% (2 / 20), a legenda mostra 2 subiram e 8 caíram, e o ⓘ diz que o gauge exclui
    quem ficou em zero.
    """
    record = HighlightsData(
        timestamp=datetime.now(timezone.utc),
        highs_json="[]",
        lows_json="[]",
        up_count=2,
        down_count=8,
        total_count=20,
        fonte="yfinance",
    )
    save_highlights_data(record)

    view_data = get_highlights_view_data()
    assert view_data is not None
    assert view_data["dispersion_pct"] == 20.0
    assert view_data["neutral_count"] == 10

    resp = client.get("/")
    assert resp.status_code == 200
    html = resp.text
    assert "2 subiram" in html
    assert "8 caíram" in html
    assert "exclui quem ficou em zero" in html


def test_snapshot_publica_paineis_manchete():
    """Snapshot /api/snapshot publica paineis.manchete com humor, texto, coletado_em, fonte."""
    resp = client.get("/api/snapshot")
    assert resp.status_code == 200
    data = resp.json()
    assert "paineis" in data
    assert "manchete" in data["paineis"]
    manchete = data["paineis"]["manchete"]
    assert manchete["humor"] in {
        "alta_ampla",
        "baixa_ampla",
        "misto",
        "sem_direcao",
        "indisponivel",
    }
    assert isinstance(manchete["texto"], str)
    assert "coletado_em" in manchete
    assert "fonte" in manchete
