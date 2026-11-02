# Imagem do Painel B3 para o deploy em Kubernetes (k8s/, deploy-k8s.yml).
# O Render continua usando render.yaml e não lê este arquivo.
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8000

WORKDIR /code

COPY requirements.txt .
RUN pip install -r requirements.txt

# O app lê devagent.toml, .github/workflows e docs/specs em tempo de execução
# (página /sistema), por isso a imagem leva o repositório inteiro, sem o que
# o .dockerignore exclui.
COPY . .

# Commit da imagem, mostrado em /sistema (o Render usa RENDER_GIT_COMMIT).
ARG GIT_COMMIT=""
ENV GIT_COMMIT=${GIT_COMMIT}

RUN useradd --uid 10001 --no-create-home app && chown -R app /code
USER 10001

EXPOSE 8000
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT} --proxy-headers --forwarded-allow-ips='*'"]
