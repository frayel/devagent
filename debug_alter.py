import sqlite3

conn = sqlite3.connect("data.db")
try:
    conn.execute(
        "ALTER TABLE consultor_opinioes_status ADD COLUMN ultima_extracao_em TEXT"
    )
except Exception as e:
    print("FAILED:", e)
conn.close()
