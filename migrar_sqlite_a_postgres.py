print("Iniciando migración...")

import sqlite3
import psycopg2

sqlite_conn = sqlite3.connect("produccion.db")
sqlite_conn.row_factory = sqlite3.Row
sqlite_cur = sqlite_conn.cursor()

pg_conn = psycopg2.connect(
    dbname="produccion_db",
    user="postgres",
    password="inverfarma2026",
    host="localhost",
    port="5432"
)
pg_conn.autocommit = False
pg_cur = pg_conn.cursor()

# Columnas booleanas por tabla
BOOLEANOS = {
    "empleados":            ["activo"],
    "lideres":              ["activo"],
    "productos":            ["activo"],
    "causas_parada":        ["programada", "activa"],
    "tipos_desperdicio":    ["activa"],
    "ordenes":              ["activa", "tiene_pigmento"],
    "turnos":               [],
    "registros_produccion": [],
    "paradas":              ["programada"],
    "desperdicios":         [],
    "relevos":              [],
}

def convertir_fila(fila, columnas, bool_cols):
    resultado = []
    for col, val in zip(columnas, tuple(fila)):
        if col in bool_cols and val is not None:
            resultado.append(bool(val))
        else:
            resultado.append(val)
    return resultado

try:
    for tabla, bool_cols in BOOLEANOS.items():
        print(f"Migrando {tabla}...")
        sqlite_cur.execute(f"SELECT * FROM {tabla}")
        filas = sqlite_cur.fetchall()

        if not filas:
            print(f"  {tabla} vacía.")
            continue

        columnas = [desc[0] for desc in sqlite_cur.description]
        placeholders = ",".join(["%s"] * len(columnas))
        cols = ",".join(columnas)

        for fila in filas:
            fila_convertida = convertir_fila(fila, columnas, bool_cols)
            pg_cur.execute(
                f"INSERT INTO {tabla} ({cols}) VALUES ({placeholders}) ON CONFLICT DO NOTHING",
                fila_convertida
            )

        print(f"  {len(filas)} filas OK")

    pg_conn.commit()
    print("\n✅ Migración completa.")

except Exception as e:
    pg_conn.rollback()
    print(f"\n❌ Error: {e}")

finally:
    sqlite_conn.close()
    pg_conn.close()