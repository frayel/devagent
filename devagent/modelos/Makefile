# Contrato entre o núcleo devagent e este projeto.
# O CI, o guardião de PRs e o ciclo do agente só chamam estes alvos.
# Troque o conteúdo de cada alvo pelo que o seu stack precisa.

PY ?= python

.PHONY: install install-prod verify smoke audit

install:
	$(PY) -m pip install --upgrade pip
	$(PY) -m pip install -r requirements-dev.txt

install-prod:
	$(PY) -m pip install --upgrade pip
	$(PY) -m pip install -r requirements.txt

verify:
	ruff check .
	ruff format --check .
	pytest -q

smoke:
	SMOKE_START="$$($(PY) -m devagent.adaptadores.render_blueprint start)" \
	SMOKE_SAUDE="$$($(PY) -m devagent.adaptadores.render_blueprint saude)" \
	sh devagent/smoke.sh

audit:
	$(PY) -m auditoria.auditar $(ARGS)
