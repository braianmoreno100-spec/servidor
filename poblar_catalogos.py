import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'produccion.db')

CAUSAS_INYECCION = [
    (1,  'AVERIA MOLDE',                       1, 'inyeccion'),
    (2,  'DAÑO RESISTENCIAS CAÑON',            1, 'inyeccion'),
    (3,  'DAÑO ELECTRICO',                     1, 'inyeccion'),
    (4,  'DAÑO MECANICO',                      1, 'inyeccion'),
    (5,  'DAÑO SISTEMA CALIENTE MOLDE',        1, 'inyeccion'),
    (6,  'FALLA REFRIGERACION',                1, 'inyeccion'),
    (7,  'FALLA AIRE COMPRIMIDO',              1, 'inyeccion'),
    (8,  'FALLA SISTEMA HIDRAULICO',           1, 'inyeccion'),
    (9,  'ESPERA DE MANTENIMIENTO',            1, 'inyeccion'),
    (10, 'FALTA DE ACEITE HIDRAULICO',         1, 'inyeccion'),
    (11, 'DAÑO MEZCLADOR',                     1, 'inyeccion'),
    (12, 'FALLA EN EL SISTEMA DE LUBRICACION', 1, 'inyeccion'),
    (13, 'CAMBIO DE MOLDE',                    0, 'inyeccion'),
    (14, 'MANTENIMIENTO PREVENTIVO',           0, 'inyeccion'),
    (15, 'REUNION',                            0, 'inyeccion'),
    (16, 'PAUSAS ACTIVAS',                     0, 'inyeccion'),
    (17, 'CAMBIO DE COLOR',                    0, 'inyeccion'),
    (18, 'MANTENIMIENTO PLANTA ELECTRICA',     0, 'inyeccion'),
    (19, 'LIMPIEZA Y DESINFECCION',            0, 'inyeccion'),
    (20, 'DESAYUNO ALMUERZO, CENA',            0, 'inyeccion'),
    (21, 'FALTA DE OPERARIO',                  0, 'inyeccion'),
    (22, 'FALTA DE MATERIAL EXTERNO',          0, 'inyeccion'),
    (23, 'FALLA PLANTA ELECTRICA',             0, 'inyeccion'),
    (24, 'LIMPIEZA DE BOQUILLA Y/O PURGA',     0, 'inyeccion'),
    (25, 'CALENTAMIENTO CAÑON',                0, 'inyeccion'),
    (26, 'TERMINA ORDEN',                      0, 'inyeccion'),
    (27, 'OPERARIO EN OTRA ACTIVIDAD',         0, 'inyeccion'),
    (28, 'PRUEBA DE MATERIAL',                 0, 'inyeccion'),
    (29, 'LIDER OCUPADO',                      0, 'inyeccion'),
    (30, 'EMPEZAR ORDEN',                      0, 'inyeccion'),
    (31, 'OPERARIO EN REPROCESO',              0, 'inyeccion'),
    (32, 'MOLER MATERIAL',                     0, 'inyeccion'),
    (33, 'PRUEBA SOPLADORA',                   0, 'inyeccion'),
    (34, 'PARO MAQUINA C. CALIDAD',            0, 'inyeccion'),
    (35, 'AJUSTE PROCESO',                     0, 'inyeccion'),
    (36, 'PICO DE ENERGIA',                    0, 'inyeccion'),
    (37, 'CORTE ENERGIA EXTERIOR',             0, 'inyeccion'),
    (38, 'MALA LIMPIEZA DE CAÑON',             0, 'inyeccion'),
    (39, 'FALTA DE MATERIAL INTERNO',          0, 'inyeccion'),
    (40, 'ERROR EN LA MEZCLA',                 0, 'inyeccion'),
]

CAUSAS_SOPLADO = [
    (1,  'AVERIA MOLDE',                       1, 'soplado'),
    (2,  'DAÑO RESISTENCIAS CAÑON',            1, 'soplado'),
    (3,  'DAÑO ELECTRICO',                     1, 'soplado'),
    (4,  'DAÑO MECANICO',                      1, 'soplado'),
    (5,  'DAÑO TROQUEL',                       1, 'soplado'),
    (6,  'FALLA REFRIGERACION',                1, 'soplado'),
    (7,  'FALLA AIRE COMPRIMIDO',              1, 'soplado'),
    (8,  'FALLA SISTEMA HIDRAULICO',           1, 'soplado'),
    (9,  'ESPERA DE MANTENIMIENTO',            1, 'soplado'),
    (10, 'FALTA DE ACEITE HIDRAULICO',         1, 'soplado'),
    (11, 'FALLAS EN EL CARGADOR',              1, 'soplado'),
    (12, 'FALLA EN EL SISTEMA DE LUBRICACION', 1, 'soplado'),
    (13, 'CAMBIO DE MOLDE',                    0, 'soplado'),
    (14, 'MANTENIMIENTO PREVENTIVO',           0, 'soplado'),
    (15, 'REUNION',                            0, 'soplado'),
    (16, 'PAUSAS ACTIVAS',                     0, 'soplado'),
    (17, 'CAMBIO DE COLOR',                    0, 'soplado'),
    (18, 'MANTENIMIENTO PLANTA ELECTRICA',     0, 'soplado'),
    (19, 'LIMPIEZA Y DESINFECCION',            0, 'soplado'),
    (20, 'DESAYUNO ALMUERZO, CENA',            0, 'soplado'),
    (21, 'FALTA DE OPERARIO',                  0, 'soplado'),
    (22, 'FALTA DE MATERIAL EXTERNO',          0, 'soplado'),
    (23, 'FALLA PLANTA ELECTRICA',             0, 'soplado'),
    (24, 'LIMPIEZA DE BOQUILLA Y/O PURGA',     0, 'soplado'),
    (25, 'CALENTAMIENTO CAÑON',                0, 'soplado'),
    (26, 'TERMINA ORDEN',                      0, 'soplado'),
    (27, 'OPERARIO EN OTRA ACTIVIDAD',         0, 'soplado'),
    (28, 'PRUEBA DE MATERIAL',                 0, 'soplado'),
    (29, 'LIDER OCUPADO',                      0, 'soplado'),
    (30, 'EMPEZAR ORDEN',                      0, 'soplado'),
    (31, 'OPERARIO EN REPROCESO',              0, 'soplado'),
    (32, 'MOLER MATERIAL',                     0, 'soplado'),
    (33, 'PRUEBA SOPLADORA',                   0, 'soplado'),
    (34, 'PARO MAQUINA C. CALIDAD',            0, 'soplado'),
    (35, 'AJUSTE PROCESO',                     0, 'soplado'),
    (36, 'PICO DE ENERGIA',                    0, 'soplado'),
    (37, 'CORTE ENERGIA EXTERIOR',             0, 'soplado'),
    (38, 'MALA LIMPIEZA DE CAÑON',             0, 'soplado'),
    (39, 'FALTA DE MATERIAL INTERNO',          0, 'soplado'),
    (40, 'ERROR EN LA MEZCLA',                 0, 'soplado'),
    (41, 'LIMPIEZA DEL PIN DE SOPLADO',        0, 'soplado'),
    (42, 'MATERIAL CONTAMINADO',               0, 'soplado'),
    (43, 'DAÑADAS POR OPERARIO',               0, 'soplado'),
    (44, 'AJUSTE PROCESO MANTENIMIENTO',       0, 'soplado'),
]

CAUSAS_LINEA = [
    (1,  'FALLAS EN LA TAPADORA',              1, 'linea'),
    (2,  'FALLA SELLADORA',                    1, 'linea'),
    (3,  'FALLA DE CORTE',                     1, 'linea'),
    (4,  'DAÑO ELECTRICO',                     1, 'linea'),
    (5,  'DAÑO MECANICO',                      1, 'linea'),
    (6,  'FALLA AIRE COMPRIMIDO',              1, 'linea'),
    (7,  'FALLA PLANTA ELECTRICA',             1, 'linea'),
    (8,  'FALLA DEL CONTADOR',                 1, 'linea'),
    (9,  'FALLA DE ETIQUETADORA',              1, 'linea'),
    (10, 'FALLA EN EL TAMBOR',                 1, 'linea'),
    (11, 'BIOPP QUEMADO',                      1, 'linea'),
    (12, 'AIRE CONTAMINADO CON AGUA',          1, 'linea'),
    (13, 'ROTURA DE CADENA ALIMENTACION TAPA', 0, 'linea'),
    (14, 'FALTA DE TAPA',                      0, 'linea'),
    (15, 'TAPA DEFECTUOSA',                    0, 'linea'),
    (16, 'FALLA EN LA PELICULA',               0, 'linea'),
    (17, 'FALTA DE MATERIAL',                  0, 'linea'),
    (18, 'PICO DE ENERGIA',                    0, 'linea'),
    (19, 'CORTE ENERGIA EXTERIOR',             0, 'linea'),
    (20, 'MAL LOTE DE ETIQUETA',               0, 'linea'),
    (21, 'BIOPP DEFECTUOSO',                   0, 'linea'),
    (22, 'ERROR DE EMPAQUE',                   0, 'linea'),
    (23, 'PRUEBAS DE BIOPP',                   0, 'linea'),
    (24, 'FALLAS Y CALIBRACION BALANZA',       0, 'linea'),
    (25, 'OPERARIO EN OTRA ACTIVIDAD',         0, 'linea'),
    (26, 'CAMBIO DE BOBINA',                   0, 'linea'),
    (27, 'MANTENIMIENTO PREVENTIVO',           0, 'linea'),
    (28, 'REUNION',                            0, 'linea'),
    (29, 'PAUSAS ACTIVAS',                     0, 'linea'),
    (30, 'MANTENIMIENTO PLANTA ELECTRICA',     0, 'linea'),
    (31, 'LIMPIEZA Y DESINFECCION',            0, 'linea'),
    (32, 'DESAYUNO ALMUERZO, CENA',            0, 'linea'),
    (33, 'FALTA DE OPERARIO',                  0, 'linea'),
    (34, 'CAMBIO DE ORDEN',                    0, 'linea'),
    (35, 'TEC. MTTO. OCUPADO',                 0, 'linea'),
    (36, 'FRASCO DEFECTUOSO',                  0, 'linea'),
    (37, 'TERMINA ORDEN',                      0, 'linea'),
    (38, 'ALISTAMIENTO INICIO ORDEN',          0, 'linea'),
    (39, 'PARADAS POR OPERARIO',               0, 'linea'),
    (40, 'LIMPIEZA DE TAMBOR',                 0, 'linea'),
    (41, 'LLENADO DE CAJAS',                   0, 'linea'),
    (42, 'AJUSTE MECANICO DE PROCESO',         0, 'linea'),
]

TIPOS_DESPERDICIO = [
    (1,  'REBABAS'),
    (2,  'LLENADO INCOMPLETO'),
    (3,  'PELLETS SIN FUNDIR'),
    (4,  'QUEMADAS (DIESEL)'),
    (5,  'DELAMINACION'),
    (6,  'BURBUJAS'),
    (7,  'GRIETAS'),
    (8,  'LINEAS DE FLUJO'),
    (9,  'LINEA DE UNION'),
    (10, 'RECHUPES'),
    (11, 'ALABEO'),
    (12, 'MALA DISPERSION DEL COLOR'),
    (13, 'FLUJO LIBRE'),
    (14, 'RAFAGAS'),
    (15, 'CONTAMINACION'),
    (16, 'MARCAS DE EXPULSION'),
    (17, 'DEFORMACION POR EXPULSION'),
    (18, 'PIEZA CON GRASA'),
    (19, 'COLOR FUERA DE ESTANDAR'),
    (20, 'MOLDE RAYADO'),
    (21, 'OXIDO'),
    (22, 'PARTIDOS DE MAQUINA'),
    (23, 'FUGA DE AGUA'),
    (24, 'FRASCO OVALADO'),
]

def poblar():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Agregar columna tipo_maquina si no existe
    try:
        cur.execute("ALTER TABLE causas_parada ADD COLUMN tipo_maquina TEXT NOT NULL DEFAULT 'linea'")
        print("✅ Columna tipo_maquina agregada")
    except sqlite3.OperationalError:
        print("ℹ️  Columna tipo_maquina ya existe")

    # Recrear tabla sin UNIQUE constraint en codigo
    cur.execute("DROP TABLE IF EXISTS causas_parada_nueva")
    cur.execute("""
        CREATE TABLE causas_parada_nueva (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo INTEGER NOT NULL,
            descripcion TEXT NOT NULL,
            programada INTEGER NOT NULL DEFAULT 0,
            tipo_maquina TEXT NOT NULL DEFAULT 'linea',
            activa INTEGER NOT NULL DEFAULT 1
        )
    """)
    cur.execute("DROP TABLE causas_parada")
    cur.execute("ALTER TABLE causas_parada_nueva RENAME TO causas_parada")
    print("✅ Tabla causas_parada recreada sin UNIQUE constraint")

    # Insertar todas las causas
    cur.executemany(
        "INSERT INTO causas_parada (codigo, descripcion, programada, tipo_maquina, activa) VALUES (?,?,?,?,1)",
        CAUSAS_INYECCION + CAUSAS_SOPLADO + CAUSAS_LINEA
    )
    total = len(CAUSAS_INYECCION) + len(CAUSAS_SOPLADO) + len(CAUSAS_LINEA)
    print(f"✅ {total} causas insertadas ({len(CAUSAS_INYECCION)} inyección, {len(CAUSAS_SOPLADO)} soplado, {len(CAUSAS_LINEA)} línea)")

    # Limpiar y repoblar desperdicios
    cur.execute("DELETE FROM tipos_desperdicio")
    cur.executemany(
        "INSERT INTO tipos_desperdicio (codigo, descripcion, activa) VALUES (?,?,1)",
        TIPOS_DESPERDICIO
    )
    print(f"✅ {len(TIPOS_DESPERDICIO)} tipos de desperdicio insertados")

    conn.commit()
    conn.close()
    print("\n✅ Catálogos poblados correctamente")

if __name__ == "__main__":
    poblar()