from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from devagent.adaptadores import jules


def test_merges_do_desenvolvimento_inclui_pessoas_e_filtra_outras_raias(
    monkeypatch,
) -> None:
    """Com github_get falso devolvendo 3 PRs mesclados de desenvolvimento

    (um do bot, um de pessoa, um de outra raia), merges_do_desenvolvimento
    devolve os 2 de desenvolvimento.
    """
    desde = datetime(2026, 11, 1, 0, 0, tzinfo=timezone.utc)
    prs_mock = [
        {
            "number": 101,
            "title": "feat: alteração do bot",
            "user": {"login": "google-labs-jules[bot]"},
            "merged_at": "2026-11-02T10:00:00Z",
            "updated_at": "2026-11-02T10:00:00Z",
        },
        {
            "number": 102,
            "title": "fix: correção de pessoa",
            "user": {"login": "feliperayel"},
            "merged_at": "2026-11-02T11:00:00Z",
            "updated_at": "2026-11-02T11:00:00Z",
        },
        {
            "number": 103,
            "title": "spec: outra raia",
            "user": {"login": "google-labs-jules[bot]"},
            "merged_at": "2026-11-02T12:00:00Z",
            "updated_at": "2026-11-02T12:00:00Z",
        },
    ]

    monkeypatch.setattr(
        jules, "github_get", lambda url: prs_mock if "page=1" in url else []
    )
    resultado = jules.merges_do_desenvolvimento(desde)
    numeros = [pr["number"] for pr in resultado]
    assert numeros == [102, 101]


def test_paginacao_merges_e_parada_em_pagina_anterior_a_desde(monkeypatch) -> None:
    """Com 60 PRs fictícios em 2 páginas, todos os mesclados depois de desde

    aparecem; a busca para na primeira página inteira anterior a desde.
    """
    desde = datetime(2026, 11, 2, 0, 0, tzinfo=timezone.utc)
    paginas_chamadas: list[int] = []

    def mock_get(url: str) -> list[dict[str, Any]]:
        for p in range(1, 6):
            if f"page={p}" in url:
                paginas_chamadas.append(p)
                if p == 1:
                    # 50 PRs atualizados e mesclados em 2026-11-03 (após desde)
                    return [
                        {
                            "number": i,
                            "title": f"feat: pr {i}",
                            "merged_at": "2026-11-03T10:00:00Z",
                            "updated_at": "2026-11-03T10:00:00Z",
                        }
                        for i in range(1, 51)
                    ]
                if p == 2:
                    # 10 PRs: todos atualizados antes de desde (2026-10-31)
                    return [
                        {
                            "number": i,
                            "title": f"feat: pr {i}",
                            "merged_at": "2026-10-31T10:00:00Z",
                            "updated_at": "2026-10-31T10:00:00Z",
                        }
                        for i in range(51, 61)
                    ]
                return []
        return []

    monkeypatch.setattr(jules, "github_get", mock_get)
    resultado = jules.merges_do_desenvolvimento(desde)
    # Todos os 50 da página 1 (mesclados depois de desde) aparecem
    assert len(resultado) == 50
    # A busca chamou a página 1 e parou na página 2 (que é anterior a desde), sem pedir a 3
    assert paginas_chamadas == [1, 2]


def test_sensores_marcados_e_no_inicio_do_prompt(monkeypatch) -> None:
    """Um PR que altera auditoria/auditar.py, e um que troca

    VARIACAO_DIARIA_MAXIMA = 12.0 por 20.0 no patch, saem marcados [sensor] e no
    início do prompt.
    """
    merges = [
        {"number": 1, "title": "feat: comum 1", "merged_at": "2026-11-03T12:00:00Z"},
        {
            "number": 2,
            "title": "refactor: auditoria",
            "merged_at": "2026-11-03T11:00:00Z",
        },
        {"number": 3, "title": "feat: comum 2", "merged_at": "2026-11-03T10:00:00Z"},
        {"number": 4, "title": "fix: novo limite", "merged_at": "2026-11-03T09:00:00Z"},
    ]

    def mock_files(url: str) -> list[dict[str, Any]]:
        if "/pulls/2/files" in url:
            return [{"filename": "auditoria/auditar.py", "patch": "@@ -1 +1 @@"}]
        if "/pulls/4/files" in url:
            return [
                {
                    "filename": "app/collectors/ibovespa.py",
                    "patch": "@@ -50,1 +50,1 @@\n-VARIACAO_DIARIA_MAXIMA = 12.0\n+VARIACAO_DIARIA_MAXIMA = 20.0\n",
                }
            ]
        return [{"filename": "app/main.py", "patch": "@@ -1 +1 @@"}]

    monkeypatch.setattr(jules, "github_get", mock_files)
    prompt = jules.prompt_do_verificador(merges)

    # Ambos saem marcados com [sensor]
    assert "#2 [sensor] (refactor: auditoria)" in prompt
    assert "#4 [sensor] (fix: novo limite)" in prompt
    # E no início do prompt (antes dos comuns #1 e #3)
    pos_2 = prompt.index("#2 [sensor]")
    pos_4 = prompt.index("#4 [sensor]")
    pos_1 = prompt.index("#1 (feat: comum 1)")
    pos_3 = prompt.index("#3 (feat: comum 2)")
    assert pos_2 < pos_1 and pos_2 < pos_3
    assert pos_4 < pos_1 and pos_4 < pos_3


def test_sem_corte_silencioso_traz_sensor_e_indica_omitidos(monkeypatch) -> None:
    """Com 20 PRs e 1 [sensor] antigo, o prompt traz 15 recentes + o sensor e

    termina com +4 PRs omitidos.
    """
    # 20 PRs: PR 20 é o mais antigo e é um [sensor]
    merges = [
        {
            "number": i,
            "title": f"feat: pr {i}",
            "merged_at": f"2026-11-03T{20 - i:02d}:00:00Z",
        }
        for i in range(1, 21)
    ]

    def mock_files(url: str) -> list[dict[str, Any]]:
        if "/pulls/20/files" in url:
            return [{"filename": "auditoria/auditar.py", "patch": "@@ -1 +1 @@"}]
        return [{"filename": "app/main.py", "patch": "@@ -1 +1 @@"}]

    monkeypatch.setattr(jules, "github_get", mock_files)
    prompt = jules.prompt_do_verificador(merges)

    # O sensor antigo #20 está presente e no início
    assert "#20 [sensor]" in prompt
    # Os 15 mais recentes estão presentes
    for i in range(1, 16):
        assert f"#{i} (" in prompt
    # PRs 16, 17, 18, 19 foram omitidos (total 4)
    for i in range(16, 20):
        assert f"#{i} (" not in prompt
    assert "+4 PRs omitidos" in prompt
    assert prompt.endswith("+4 PRs omitidos; liste com git log --merges.")


def test_falha_simulada_em_files_nao_derruba_e_marca_nao_consultados(
    monkeypatch,
) -> None:
    """Falha simulada em /files de um PR:

    o prompt contém arquivos não consultados para ele e a função não levanta exceção.
    """
    merges = [
        {
            "number": 42,
            "title": "feat: falha em files",
            "merged_at": "2026-11-03T10:00:00Z",
        }
    ]

    def mock_files(url: str) -> list[dict[str, Any]]:
        raise OSError("conexão falhou")

    monkeypatch.setattr(jules, "github_get", mock_files)
    prompt = jules.prompt_do_verificador(merges)

    assert "#42" in prompt
    assert "arquivos não consultados" in prompt
    assert "[sensor]" not in prompt


def test_raias_md_e_adr_031_no_ciclo():
    """devagent/agents/raias.md contém os rótulos Verdade do número e Sensores;

    o ADR 031 existe e está no índice do CICLO.md.
    """
    raias_md = Path("devagent/agents/raias.md").read_text(encoding="utf-8")
    assert "Verdade do número" in raias_md
    assert "Sensores" in raias_md

    ciclo_md = Path("devagent/CICLO.md").read_text(encoding="utf-8")
    assert "031" in ciclo_md
    assert "verificador vê todo merge" in ciclo_md

    adr_path = Path("devagent/decisoes/031-verificador-ve-todo-merge-e-todo-sensor.md")
    assert adr_path.exists()
    conteudo_adr = adr_path.read_text(encoding="utf-8")
    assert "+12,87%" in conteudo_adr
