#!/bin/sh
# Sobe a aplicação com o comando de produção e confere o health check e a
# página inicial. Rode num ambiente com só as dependências de produção.
#
#   SMOKE_START   comando que sobe a aplicação (obrigatório; pode usar $PORT)
#   SMOKE_SAUDE   caminho do health check (padrão /healthz)
#   PORT          porta (padrão 8000)
set -u
PORT="${PORT:-8000}"
export PORT
START="${SMOKE_START:?defina SMOKE_START}"
SAUDE="${SMOKE_SAUDE:-/healthz}"

sh -c "$START" > server.log 2>&1 &
pid=$!
parar() { kill "$pid" 2>/dev/null; }

i=0
while [ "$i" -lt 30 ]; do
  if curl -fsS "http://127.0.0.1:$PORT$SAUDE"; then
    echo; echo "health check ok"
    if curl -fsS -o /dev/null "http://127.0.0.1:$PORT/"; then
      echo "página inicial ok"; parar; exit 0
    fi
    echo "página inicial falhou"; cat server.log; parar; exit 1
  fi
  i=$((i + 1))
  sleep 1
done
echo "A aplicação não respondeu em $SAUDE. Log:"
cat server.log
parar
exit 1
