"""Número de spec repetido (#1025).

Em 23/11 duas sessões do Especificador reservaram o 194 com cinco minutos de
diferença; cada PR passou sozinho no CI e os dois entraram. `status_da_spec`
e `spec_na_main` liam o primeiro arquivo em ordem alfabética (a 194 que tinha
voltado para `draft`), e a revisão da outra travou.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from devagent import aceite
from devagent.conferir_pr import ids_repetidos
from devagent.guardiao_prs import numeros_ja_na_main


def _spec(numero: str, status: str) -> str:
    return f"---\nid: {numero}\nstatus: {status}\n---\n"


def test_escolhe_a_que_nao_e_draft() -> None:
    achadas = {
        "docs/specs/194-a.md": _spec("194", "draft"),
        "docs/specs/194-b.md": _spec("194", "ready"),
    }
    assert aceite.escolher_spec("194", achadas) == _spec("194", "ready")


def test_uma_so_e_todas_draft() -> None:
    assert aceite.escolher_spec("1", {}) is None
    so = {"a.md": _spec("1", "done")}
    assert aceite.escolher_spec("1", so) == _spec("1", "done")
    rascunhos = {"a.md": _spec("1", "draft"), "b.md": _spec("1", "draft")}
    assert aceite.escolher_spec("1", rascunhos) == _spec("1", "draft")


def test_duas_validas_levantam_erro() -> None:
    achadas = {"a.md": _spec("7", "ready"), "b.md": _spec("7", "done")}
    with pytest.raises(ValueError, match="spec 7 repetida"):
        aceite.escolher_spec("7", achadas)


def test_status_da_spec_le_a_que_vale(tmp_path: Path) -> None:
    pasta = tmp_path / "docs" / "specs"
    pasta.mkdir(parents=True)
    # Em ordem alfabética, a draft vem primeiro: era a que o código lia.
    (pasta / "194-depois.md").write_text(_spec("194", "draft"), encoding="utf-8")
    (pasta / "194-pesos.md").write_text(_spec("194", "done"), encoding="utf-8")
    assert aceite.status_da_spec("194", tmp_path) == "done"


def test_regra_13_acha_o_numero_repetido(tmp_path: Path) -> None:
    pasta = tmp_path / "docs" / "specs"
    (pasta / "done").mkdir(parents=True)
    (pasta / "035-a.md").write_text(_spec("035", "done"), encoding="utf-8")
    (pasta / "done" / "35-b.md").write_text(_spec("35", "done"), encoding="utf-8")
    (pasta / "035b-c.md").write_text(_spec("035b", "done"), encoding="utf-8")
    (pasta / "036-d.md").write_text(_spec("036", "ready"), encoding="utf-8")
    assert ids_repetidos(pasta, tmp_path) == {
        "35": ["docs/specs/035-a.md", "docs/specs/done/35-b.md"]
    }


def test_guardiao_barra_spec_nova_com_numero_da_main() -> None:
    na_main = {"docs/specs/194-pesos.md": "194", "docs/specs/193-x.md": "193"}
    novas = {
        "docs/specs/194-depois.md": _spec("194", "ready"),
        "docs/specs/195-y.md": _spec("195", "ready"),
    }
    repetidas = numeros_ja_na_main(novas, na_main)
    assert repetidas == [
        "docs/specs/194-depois.md (id 194, já em docs/specs/194-pesos.md)"
    ]


def test_guardiao_deixa_passar_numero_livre_e_letra() -> None:
    na_main = {"docs/specs/077a-x.md": "077a"}
    novas = {
        "docs/specs/077b-y.md": _spec("077b", "ready"),
        "docs/specs/078-z.md": _spec("078", "ready"),
    }
    assert numeros_ja_na_main(novas, na_main) == []
