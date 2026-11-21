"""Aceite da spec 189: o quadro do Consultor mostra com cor o que está defasado.

Sem rede: `calcular_consultor` e `construir_informacoes_de` são trocados por
dublês, para fixar os estados sem depender do relógio (o molde de
`test_aceite_165.py`).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import app.consultor.informacoes
import app.main
from app.main import app as fastapi_app
from devagent.aceite import exigir_spec_done
from tests.test_classes_com_estilo import SEM_ESTILO_CONHECIDAS, classes_dos_templates

RAIZ = Path(__file__).resolve().parent.parent
CLASSES_REMOVIDAS = {
    "badge",
    "badge-positivo",
    "badge-negativo",
    "status-neutro",
    "lista-opinioes",
    "rodape-painel",
    "tabela-sem-sinal",
}


@pytest.fixture(autouse=True)
def _so_com_spec_done():
    exigir_spec_done("189")


def _pagina(monkeypatch, estado_sinais: str, estado_opinioes: str) -> str:
    monkeypatch.delenv("CONSULTOR_SENHA", raising=False)

    def mock_calc():
        return {
            "resultados": {
                "Comprar": [],
                "Vender": [],
                "Aguardar": [],
                "No radar": [],
                "Sem sinal": [],
            },
            "opinioes_recentes": [],
            "opinioes_por_ativo": [],
            "opinioes_status": {
                "status": "ok",
                "motivo": "",
                "desde": "",
                "ultima_extracao_em": "2026-11-18T13:00:00+00:00",
                "materias_processadas": 3,
                "opinioes_gravadas": 0,
                "descartadas": 0,
            },
            "ativos_avaliados": 0,
        }

    def dubl(_dados):
        return {
            "estado_sinais": estado_sinais,
            "frase_sinais": "Os sinais técnicos são de um pregão antigo.",
            "sinais_pregao": "18/11/2026",
            "sinais_coletado_em": "18/11/2026 18:30 BRT",
            "estado_opinioes": estado_opinioes,
            "frase_opinioes": "As opiniões foram extraídas há 29 h.",
            "opinioes_extraidas_em": "18/11/2026 10:00 BRT",
            "opinioes_materia_mais_recente": "18/11/2026",
            "composicao_conferida_em": "01/09/2026",
        }

    monkeypatch.setattr(app.main, "calcular_consultor", mock_calc)
    monkeypatch.setattr(app.consultor.informacoes, "construir_informacoes_de", dubl)
    resposta = TestClient(fastapi_app).get("/consultor")
    assert resposta.status_code == 200
    return resposta.text


def _bloco(html: str, titulo: str) -> str:
    casamento = re.search(
        rf"<h4>{re.escape(titulo)}</h4>\s*<div class=\"info-conteudo\">(.*?)</div>",
        html,
        re.S,
    )
    assert casamento, f"bloco {titulo!r} não encontrado"
    return casamento.group(1)


def test_selo_ok_e_selo_atencao(monkeypatch):
    html = _pagina(monkeypatch, "Atualizado", "Defasado")
    assert '<span class="selo ok">Atualizado</span>' in _bloco(html, "Sinais técnicos")
    assert '<span class="selo atencao">Defasado</span>' in _bloco(
        html, "Opiniões de especialistas"
    )
    assert 'id="alerta-opinioes-defasado"' in html


def test_dois_defasados_sem_selo_ok(monkeypatch):
    html = _pagina(monkeypatch, "Defasado", "Defasado")
    for titulo in ("Sinais técnicos", "Opiniões de especialistas"):
        bloco = _bloco(html, titulo)
        assert "selo ok" not in bloco
        assert '<span class="selo atencao">Defasado</span>' in bloco
    assert 'id="alerta-sinais-defasado"' in html


def test_composicao_com_selo_ok(monkeypatch):
    html = _pagina(monkeypatch, "Atualizado", "Atualizado")
    assert '<span class="selo ok">Atualizado</span>' in _bloco(
        html, "Composição do Ibovespa"
    )


def test_titulo_opinioes_recentes_sem_classe(monkeypatch):
    html = _pagina(monkeypatch, "Atualizado", "Atualizado")
    assert "<h3>Opiniões Recentes</h3>" in html
    assert re.search(r"<h3[^>]*class=[^>]*>\s*Opiniões Recentes", html) is None


def test_ultima_extracao_dentro_de_fonte_dado(monkeypatch):
    html = _pagina(monkeypatch, "Atualizado", "Atualizado")
    assert re.search(r'<div class="fonte-dado">\s*Última extração:', html)


def test_classes_removidas_do_template():
    texto = (RAIZ / "app" / "templates" / "consultor.html").read_text(encoding="utf-8")
    usadas = set(classes_dos_templates({"consultor.html": texto}))
    assert not usadas & CLASSES_REMOVIDAS


def test_lista_de_excecoes_encolheu():
    assert not set(SEM_ESTILO_CONHECIDAS) & CLASSES_REMOVIDAS
    assert len(SEM_ESTILO_CONHECIDAS) <= 25
