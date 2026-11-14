# Contrato entre o núcleo devagent e este projeto.
# O CI, o guardião de PRs e o ciclo do agente só chamam estes alvos
# (veja [verificacao] em devagent.toml). O que cada um faz é do projeto.

PY ?= python

.PHONY: install install-prod verify smoke audit telas

## Atualizar o pip é melhor esforço: o pip de um Python do sistema (Debian)
## não se desinstala ("RECORD file not found") e não pode impedir a instalação
## das dependências fixadas, que é o que o `make verify` precisa.
PIP_UPGRADE = $(PY) -m pip install --upgrade pip || echo "make: pip não atualizado; seguindo com o pip instalado"

## Dependências de desenvolvimento (lint, tipos, testes).
install:
	$(PIP_UPGRADE)
	$(PY) -m pip install -r requirements-dev.txt

## Só as dependências de produção, como o Render instala.
install-prod:
	$(PIP_UPGRADE)
	$(PY) -m pip install -r requirements.txt

## Tudo que o CI exige antes do merge.
## As ferramentas rodam como módulos do $(PY), o mesmo em que `make install`
## instalou as versões fixadas: um binário solto no PATH (ex.: um ruff mais novo
## em ~/.local/bin) não entra no lugar e não acusa erros falsos.
verify:
	$(PY) -m ruff check .
	$(PY) -m ruff format --check .
	$(PY) -m mypy app
	$(PY) -m pytest -m "not rede" -q

## Sobe a aplicação com o startCommand do render.yaml e confere o health check.
smoke:
	SMOKE_START="$$($(PY) -m devagent.adaptadores.render_blueprint start)" \
	SMOKE_SAUDE="$$($(PY) -m devagent.adaptadores.render_blueprint saude)" \
	sh devagent/smoke.sh

## Audita produção. Ex.: make audit ARGS="--navegador --saida relatorio"
audit:
	$(PY) -m auditoria.auditar $(ARGS)

## Capturas da interface (1440 e 390 px) em telas/, com dados de demonstração.
## Obrigatório em PR que muda a interface (docs/DESIGN.md, seção 8).
telas:
	$(PY) -m playwright install chromium
	$(PY) scripts/telas.py --saida telas
