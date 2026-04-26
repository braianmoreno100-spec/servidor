import sqlite3

conn = sqlite3.connect("produccion.db")
cursor = conn.cursor()

try:
    cursor.execute("ALTER TABLE ordenes ADD COLUMN numero_operarios INTEGER")
    conn.commit()
    print("✅ Columna numero_operarios agregada correctamente.")
except Exception as e:
    print(f"⚠️ {e}")
finally:
    conn.close()
    