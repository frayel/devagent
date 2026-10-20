from app.consultor.regras import calcular_ifr14, calcular_mm
import app.consultor.calculador
from fastapi.testclient import TestClient
from app.main import app as fastapi_app
import app.main

client = TestClient(fastapi_app)


def test_pagina_consultor_sem_senha(monkeypatch):
    monkeypatch.delenv("CONSULTOR_SENHA", raising=False)
    response = client.get("/consultor")
    assert response.status_code == 200
    assert "Consultor de Investimentos" in response.text


def test_api_consultor_sem_senha(monkeypatch):
    monkeypatch.delenv("CONSULTOR_SENHA", raising=False)
    response = client.get("/api/consultor")
    assert response.status_code == 200
    assert "ativos_avaliados" in response.json()


def test_snapshot_consultor_metadados():
    response = client.get("/api/snapshot")
    assert response.status_code == 200
    data = response.json()
    assert "consultor" in data
    assert "ativos_avaliados" in data["consultor"]
    assert "composicao_vigente_ate" in data["consultor"]


def test_consultor_com_senha_sem_auth(monkeypatch):
    monkeypatch.setenv("CONSULTOR_SENHA", "senha_secreta")
    response = client.get("/consultor")
    assert response.status_code == 401
    response = client.get("/api/consultor")
    assert response.status_code == 401


def test_consultor_com_senha_auth_valida(monkeypatch):
    monkeypatch.setenv("CONSULTOR_SENHA", "senha_secreta")
    response = client.get("/consultor", auth=("consultor", "senha_secreta"))
    assert response.status_code == 200
    response = client.get("/api/consultor", auth=("consultor", "senha_secreta"))
    assert response.status_code == 200


def test_pagina_consultor_desatualizada(monkeypatch):
    monkeypatch.delenv("CONSULTOR_SENHA", raising=False)

    def mock_hoje():
        return True

    monkeypatch.setattr(app.main, "composicao_esta_desatualizada", mock_hoje)

    def mock_calc():
        return {
            "resultados": {
                "Comprar": [],
                "Vender": [],
                "Aguardar": [],
                "Sem sinal": [],
            },
            "opinioes_recentes": [],
            "opinioes_status": {"status": "ok", "motivo": "", "desde": ""},
            "ativos_avaliados": 10,
            "regras_limiares": {
                "R1_QUEDAS": 999,
                "R1_GATILHO_VOL": 1.5,
                "R3_IFR_MAX": 70,
                "R3_IFR_RECUO": 60,
                "R4_DISTANCIA_MM200": 0.03,
                "R4_GATILHO_VOL": 1.0,
                "R5_IFR_MIN": 40,
                "R5_IFR_MAX": 65,
            },
        }

    monkeypatch.setattr(app.main, "calcular_consultor", mock_calc)
    response = client.get("/consultor")
    assert response.status_code == 200
    assert "Composição do Ibovespa possivelmente desatualizada" in response.text


def test_calculos_ifr_mm():
    closes = [
        100.0,
        102.0,
        101.0,
        103.0,
        105.0,
        104.0,
        106.0,
        108.0,
        107.0,
        109.0,
        110.0,
        112.0,
        111.0,
        113.0,
        115.0,
        114.0,
        116.0,
        118.0,
        117.0,
        119.0,
        120.0,
    ]
    ifr = calcular_ifr14(closes)
    assert abs(ifr - 81.49) < 0.1
    closes_200 = list(range(1, 201))
    mm200 = calcular_mm(closes_200, 200)
    assert abs(mm200 - 100.5) < 0.01


def test_consultor_fallback(monkeypatch):
    monkeypatch.delenv("CONSULTOR_SENHA", raising=False)

    def mock_calc():
        raise Exception("Erro de coleta")

    monkeypatch.setattr(app.main, "calcular_consultor", mock_calc)
    response = client.get("/consultor")
    assert response.status_code == 200
    assert "Dados do consultor indisponíveis" in response.text
    response_api = client.get("/api/consultor")
    assert response_api.status_code == 200
    assert response_api.json()["ativos_avaliados"] == 0


def test_consultor_regras_html(monkeypatch):
    monkeypatch.delenv("CONSULTOR_SENHA", raising=False)

    def mock_calc():
        import app.consultor.regras as regras_module

        return {
            "resultados": {
                "Comprar": [],
                "Vender": [],
                "Aguardar": [],
                "Sem sinal": [],
            },
            "opinioes_recentes": [],
            "opinioes_status": {"status": "ok", "motivo": "", "desde": ""},
            "ativos_avaliados": 10,
            "regras_limiares": {
                "R1_QUEDAS": 999,
                "R1_GATILHO_VOL": regras_module.R1_GATILHO_VOL,
                "R3_IFR_MAX": regras_module.R3_IFR_MAX,
                "R3_IFR_RECUO": regras_module.R3_IFR_RECUO,
                "R4_DISTANCIA_MM200": regras_module.R4_DISTANCIA_MM200,
                "R4_GATILHO_VOL": regras_module.R4_GATILHO_VOL,
                "R5_IFR_MIN": regras_module.R5_IFR_MIN,
                "R5_IFR_MAX": regras_module.R5_IFR_MAX,
            },
        }

    monkeypatch.setattr(app.main, "calcular_consultor", mock_calc)
    import app.consultor.regras as regras

    monkeypatch.setattr(regras, "R1_QUEDAS", 999)
    response = client.get("/consultor")
    assert response.status_code == 200
    assert "QUEDAS_SEGUIDAS &gt;= 999" in response.text


def test_api_consultor_comprar_invalidation(monkeypatch):
    monkeypatch.delenv("CONSULTOR_SENHA", raising=False)

    def mock_calc():
        import app.consultor.regras as regras_module

        return {
            "resultados": {
                "Comprar": [
                    {
                        "ticker": "PETR4",
                        "fechamento": 35.0,
                        "regra": "R5 Tendência de alta saudável",
                        "motivo": "Teste",
                        "gatilho": "Fechamento abaixo da MM200 (R$ 30.00)",
                        "fonte": "test",
                        "timestamp": "test",
                        "confianca": "alta",
                        "n": 100,
                        "mensagem_confianca": "Nas 100 vezes...",
                    }
                ],
                "Vender": [],
                "Aguardar": [],
                "Sem sinal": [],
            },
            "opinioes_recentes": [],
            "opinioes_status": {"status": "ok", "motivo": "", "desde": ""},
            "ativos_avaliados": 1,
            "regras_limiares": {
                "R1_QUEDAS": 999,
                "R1_GATILHO_VOL": regras_module.R1_GATILHO_VOL,
                "R3_IFR_MAX": regras_module.R3_IFR_MAX,
                "R3_IFR_RECUO": regras_module.R3_IFR_RECUO,
                "R4_DISTANCIA_MM200": regras_module.R4_DISTANCIA_MM200,
                "R4_GATILHO_VOL": regras_module.R4_GATILHO_VOL,
                "R5_IFR_MIN": regras_module.R5_IFR_MIN,
                "R5_IFR_MAX": regras_module.R5_IFR_MAX,
            },
        }

    monkeypatch.setattr(app.main, "calcular_consultor", mock_calc)
    response = client.get("/api/consultor")
    assert response.status_code == 200
    data = response.json()
    assert (
        "Fechamento abaixo da MM200 (R$ 30.00)"
        == data["resultados"]["Comprar"][0]["gatilho"]
    )


def test_regras_1_ao_4_fixture():
    from app.consultor.regras import avaliar_ativo

    closes_r1 = [100.0 - i for i in range(250)]
    volumes = [1000 for _ in range(250)]
    ibov_closes = [100.0 for _ in range(250)]
    av_r1 = avaliar_ativo("TICK1", closes_r1, volumes, ibov_closes)
    assert av_r1["regra"] == "R1 Faca caindo"
    assert av_r1["decisao"] == "Aguardar"

    closes_r2 = []
    for i in range(250):
        if i % 2 == 0:
            closes_r2.append(90.0)
        else:
            closes_r2.append(91.0)
    closes_r2[-21:] = [80.0 for _ in range(21)]
    closes_r2[-1] = 79.0
    ibov_closes_r2 = [100.0 for _ in range(250)]
    av_r2 = avaliar_ativo("TICK2", closes_r2, volumes, ibov_closes_r2)
    assert av_r2["regra"] == "R2 Tendência de baixa"
    assert av_r2["decisao"] == "Vender"

    closes_r3 = [50.0 for _ in range(200)]
    pump = 100.0
    for i in range(50):
        pump += 2.0
        closes_r3.append(pump)
    av_r3 = avaliar_ativo("TICK3", closes_r3, volumes, ibov_closes)
    assert av_r3["regra"] == "R3 Esticada"
    assert av_r3["decisao"] == "Aguardar"

    closes_r4 = [100.0] * 222
    closes_r4[-21:] = [90.0] * 16 + [101.0] * 4 + [99.0]
    av_r4 = avaliar_ativo("TICK4", closes_r4, volumes, ibov_closes)
    assert av_r4["regra"] == "R4 Rompimento pendente"
    assert av_r4["decisao"] == "Aguardar"
