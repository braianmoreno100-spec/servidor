import sqlite3, os

DB_PATH = os.path.join(os.path.dirname(__file__), "produccion.db")
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

cursor.execute("PRAGMA table_info(productos)")
columnas = [row[1] for row in cursor.fetchall()]

if "peso_pieza" not in columnas:
    cursor.execute("ALTER TABLE productos ADD COLUMN peso_pieza REAL")
    conn.commit()
    print("✅ Columna peso_pieza agregada")
else:
    print("ℹ️  Ya existe, no se hizo nada")

conn.close()