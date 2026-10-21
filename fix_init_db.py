import re

with open('app/database.py', 'r') as f:
    content = f.read()

# I deleted table creation for `motores_indice_cache`? Wait, I didn't list it in `tables` array!
# Ah, I see: I didn't patch `motores_indice_cache`. I shouldn't have deleted tables that weren't in `tables`.
# Wait, let's see what was removed.
print("Checking what was actually removed or if app.banco._db_initialized=False caused init_db to not run for sqlite in app/database.py")
