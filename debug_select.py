import sqlite3

conn = sqlite3.connect("data.db")
c = conn.cursor()
c.execute(
    "SELECT status, motivo, desde, ultima_extracao_em, materias_processadas, opinioes_gravadas, descartadas FROM consultor_opinioes_status LIMIT 1"
)
print("SUCCESS")
conn.close()
