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

# Se a porta já responde antes de a aplicação subir, quem responderia ao
# smoke é outro servidor (talvez de um smoke anterior, com código antigo).
if curl -fsS -o /dev/null "http://127.0.0.1:$PORT$SAUDE" 2>/dev/null; then
  echo "porta $PORT ocupada por outro servidor: o smoke não conferiria esta aplicação"
  exit 1
fi

sh -c "$START" > server.log 2>&1 &
pid=$!

# Encerra o processo e todos os descendentes: matar só o `sh -c` deixava o
# servidor filho vivo, segurando a porta para o próximo smoke.
encerrar_arvore() {
  for filho in $(pgrep -P "$1" 2>/dev/null); do
    encerrar_arvore "$filho"
  done
  kill "$1" 2>/dev/null
}
parar() {
  encerrar_arvore "$pid"
  wait "$pid" 2>/dev/null
  # O servidor pode levar alguns segundos no encerramento gracioso: só sai
  # quando a porta deixar de responder, para o próximo smoke achá-la livre.
  j=0
  while [ "$j" -lt 20 ] && curl -fsS -o /dev/null "http://127.0.0.1:$PORT$SAUDE" 2>/dev/null; do
    j=$((j + 1))
    sleep 0.5
  done
}

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
