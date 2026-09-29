# Contrato entre o núcleo devagent e este projeto.
# O CI, o guardião de PRs e o ciclo do agente só chamam estes alvos
# (veja [verificacao] em devagent.toml). O que cada um faz é do projeto.

PY ?= python

.PHONY: install install-prod verify smoke audit

## Dependências de desenvolvimento (lint, tipos, testes).
install:
	$(PY) -m pip install --upgrade pip
	$(PY) -m pip install -r requirements-dev.txt

## Só as dependências de produção, como o Render instala.
install-prod:
	$(PY) -m pip install --upgrade pip
	$(PY) -m pip install -r requirements.txt

## Tudo que o CI exige antes do merge.
verify:
	ruff check .
	ruff format --check .
	mypy app
	pytest -q

## Sobe a aplicação com o startCommand do render.yaml e confere o health check.
smoke:
	SMOKE_START="$$($(PY) -m devagent.adaptadores.render_blueprint start)" \
	SMOKE_SAUDE="$$($(PY) -m devagent.adaptadores.render_blueprint saude)" \
	sh devagent/smoke.sh

## Audita produção. Ex.: make audit ARGS="--navegador --saida relatorio"
audit:
	$(PY) -m auditoria.auditar $(ARGS)
