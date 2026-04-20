"""
poblar_demo.py
Limpia órdenes/turnos demo y repuebla con datos realistas de todas las máquinas,
incluyendo Acondicionamiento 1 y 2 (2025).

Ejecutar con venv activo:
  python poblar_demo.py
"""

import sqlite3
import os
import random
from datetime import date, timedelta

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'produccion.db')

# ─── Rango de fechas demo ─────────────────────────────────────────────────────
HOY        = date.today()
INICIO     = HOY - timedelta(days=14)   # 2 semanas atrás
FECHAS     = [(INICIO + timedelta(days=i)).isoformat() for i in range(15)]

# ─── Órdenes demo ─────────────────────────────────────────────────────────────
# (numero_orden, codigo_producto, descripcion, cantidad, material,
#  tipo_maquina, numero_maquina, cavidades, ciclos, lider_cedula, lider_nombre)
ORDENES_DEMO = [
    # Inyectoras 1-7
    ('ORD-D-001', '3240330001', 'FRASCO COPROLOGICO CONJUNTO INV',       50000, 'Polipropileno',   'inyeccion', '1', 4, 14,   '11111111', 'CARLOS MENDEZ'),
    ('ORD-D-002', '3260330007', 'FRASCO ORINA',                          80000, 'Polipropileno',   'inyeccion', '2', 12, 19,  '11111111', 'CARLOS MENDEZ'),
    ('ORD-D-003', '3240330005', 'FRASCO COPROLOGICO CONJUNTO ICOM',      40000, 'Polietileno',     'inyeccion', '3', 4, 16,   '11111111', 'CARLOS MENDEZ'),
    ('ORD-D-004', '3170070002', 'INHALOCA MARA ICOM ADULTO',             5000,  'PVC médico',      'inyeccion', '4', 2, 60,   '11111111', 'CARLOS MENDEZ'),
    ('ORD-D-005', '3170280013', 'INHALOCA MARA PEDIATRICA OXIS',         3500,  'PVC médico',      'inyeccion', '5', 2, 58,   '11111111', 'CARLOS MENDEZ'),
    ('ORD-D-006', '4160270002', 'GUANTE EXA NITRILO AZUL INV T M PAR',  8000,  'Nitrilo',         'inyeccion', '6', 1, 22,   '11111111', 'CARLOS MENDEZ'),
    ('ORD-D-007', '4270330006', 'ZAPATON POLAINA AZUL PAR INVERFARMA',   5000,  'Polietileno',     'inyeccion', '7', 2, 30,   '11111111', 'CARLOS MENDEZ'),
    # Soplado 1
    ('ORD-D-008', '3260330007', 'FRASCO ORINA SOPLADO',                  60000, 'HDPE',            'soplado',   '1', 6, 19,   '22222222', 'ANA GARCIA'),
    # Línea Copro (maquina 1) y Orina (maquina 2)
    ('ORD-D-009', '3240330001', 'FRASCO COPROLOGICO LÍNEA',              30000, 'Polipropileno',   'linea',     '1', 4, 14,   '33333333', 'PEDRO LOPEZ'),
    ('ORD-D-010', '3260330007', 'FRASCO ORINA LÍNEA',                    45000, 'Polipropileno',   'linea',     '2', 12, 19,  '33333333', 'PEDRO LOPEZ'),
    # Acondicionamiento 1 y 2
    ('ORD-D-011', '4300070040', 'TAPABOCAS AZUL EMP IND FARMATODO',      3000,  'N/A',             'acondicionamiento', '1', 1, 68,  '44444444', 'MARIA TORRES'),
    ('ORD-D-012', '4270330006', 'ZAPATON POLAINA AZUL PAR INVERFARMA',   5000,  'N/A',             'acondicionamiento', '2', 1, 235, '44444444', 'MARIA TORRES'),
]

# ─── Empleados demo ───────────────────────────────────────────────────────────
EMPLEADOS_DEMO = [
    ('10000001', 'JUAN PEREZ'),
    ('10000002', 'MARIA RODRIGUEZ'),
    ('10000003', 'CARLOS GOMEZ'),
    ('10000004', 'ANA MARTINEZ'),
    ('10000005', 'LUIS GARCIA'),
    ('10000006', 'SOFIA LOPEZ'),
    ('10000007', 'PEDRO SANCHEZ'),
    ('10000008', 'LUCIA TORRES'),
]

# ─── Paradas demo por tipo de máquina ────────────────────────────────────────
PARADAS_NP = {
    'inyeccion':         [(1,'AVERIA MOLDE'), (3,'DAÑO ELECTRICO'), (9,'ESPERA DE MANTENIMIENTO')],
    'soplado':           [(1,'AVERIA MOLDE'), (5,'DAÑO TROQUEL'), (7,'FALLA AIRE COMPRIMIDO')],
    'linea':             [(1,'FALLAS EN LA TAPADORA'), (2,'FALLA SELLADORA'), (4,'DAÑO ELECTRICO')],
    'acondicionamiento': [(2,'FALLO EN TIJERAS'), (9,'FALLA DE MAQUINA CODIFICADORA'), (29,'CAMBIO DE ROLLO')],
}
PARADAS_P = {
    'inyeccion':         [(14,'MANTENIMIENTO PREVENTIVO'), (20,'DESAYUNO ALMUERZO, CENA'), (19,'LIMPIEZA Y DESINFECCION')],
    'soplado':           [(14,'MANTENIMIENTO PREVENTIVO'), (20,'DESAYUNO ALMUERZO, CENA'), (19,'LIMPIEZA Y DESINFECCION')],
    'linea':             [(27,'MANTENIMIENTO PREVENTIVO'), (32,'DESAYUNO ALMUERZO, CENA'), (31,'LIMPIEZA Y DESINFECCION')],
    'acondicionamiento': [(48,'INICIO DE ORDEN'), (50,'ALISTAMIENTO DE PRODUCTO'), (45,'CODIFICAR EMPAQUE')],
}
DESPERDICIOS_TIPO = {
    'inyeccion':         [(1,'REBABAS'), (6,'BURBUJAS'), (10,'RECHUPES')],
    'soplado':           [(1,'REBABAS'), (4,'QUEMADAS (DIESEL)'), (2,'LLENADO INCOMPLETO')],
    'linea':             [(1,'REBABAS'), (15,'CONTAMINACION'), (17,'DEFORMACION POR EXPULSION')],
    'acondicionamiento': [(25,'DEFECTOS'), (38,'EMPAQUE DEFECTUOSO'), (40,'VENCIDOS')],
}


def limpiar_demo(cur):
    """Elimina solo órdenes demo (ORD-D-*) y sus turnos asociados."""
    cur.execute("SELECT id FROM ordenes WHERE numero_orden LIKE 'ORD-D-%'")
    orden_ids = [r[0] for r in cur.fetchall()]
    if not orden_ids:
        return
    ids_str = ','.join(str(i) for i in orden_ids)
    cur.execute("SELECT id FROM turnos WHERE orden_id IN (%s)" % ids_str)
    turno_ids = [r[0] for r in cur.fetchall()]
    if turno_ids:
        t_str = ','.join(str(i) for i in turno_ids)
        cur.execute("DELETE FROM registros_produccion WHERE turno_id IN (%s)" % t_str)
        cur.execute("DELETE FROM paradas WHERE turno_id IN (%s)" % t_str)
        cur.execute("DELETE FROM desperdicios WHERE turno_id IN (%s)" % t_str)
        cur.execute("DELETE FROM relevos WHERE turno_id IN (%s)" % t_str)
        cur.execute("DELETE FROM turnos WHERE id IN (%s)" % t_str)
    cur.execute("DELETE FROM ordenes WHERE numero_orden LIKE 'ORD-D-%'")
    print(f"  🗑  {len(orden_ids)} órdenes demo eliminadas")


def insertar_orden(cur, o):
    cur.execute("""
        INSERT INTO ordenes
            (numero_orden, codigo_producto, descripcion_producto, cantidad_producir,
             material, tipo_maquina, numero_maquina, cavidades, ciclos,
             tiene_pigmento, cedula_lider, nombre_lider, activa)
        VALUES (?,?,?,?,?,?,?,?,?,0,?,?,1)
    """, (o[0],o[1],o[2],o[3],o[4],o[5],o[6],o[7],o[8],o[9],o[10]))
    return cur.lastrowid


def insertar_turno(cur, orden_id, fecha, empleado, hora_inicio, hora_fin=None):
    cedula, nombre = empleado
    cur.execute("""
        INSERT INTO turnos
            (orden_id, cedula_empleado, nombre_empleado, fecha, turno, hora_inicio, hora_fin)
        VALUES (?,?,?,?,?,?,?)
    """, (orden_id, cedula, nombre, fecha, '1', hora_inicio, hora_fin))
    return cur.lastrowid


def insertar_registros(cur, turno_id, horas, base_por_hora):
    for hora in horas:
        variacion = random.uniform(0.80, 1.10)
        cantidad  = max(1, int(base_por_hora * variacion))
        cur.execute("INSERT INTO registros_produccion (turno_id, hora, cantidad) VALUES (?,?,?)",
                    (turno_id, hora, cantidad))


def insertar_paradas(cur, turno_id, tipo_maquina, n_np=2, n_p=2):
    np_opciones = PARADAS_NP.get(tipo_maquina, PARADAS_NP['inyeccion'])
    p_opciones  = PARADAS_P.get(tipo_maquina, PARADAS_P['inyeccion'])

    seleccionadas_np = random.sample(np_opciones, min(n_np, len(np_opciones)))
    for cod, desc in seleccionadas_np:
        minutos = random.choice([10, 15, 20, 25, 30])
        cur.execute("INSERT INTO paradas (turno_id, codigo, descripcion, minutos, programada) VALUES (?,?,?,?,0)",
                    (turno_id, cod, desc, minutos))

    seleccionadas_p = random.sample(p_opciones, min(n_p, len(p_opciones)))
    for cod, desc in seleccionadas_p:
        minutos = random.choice([10, 15, 20])
        cur.execute("INSERT INTO paradas (turno_id, codigo, descripcion, minutos, programada) VALUES (?,?,?,?,1)",
                    (turno_id, cod, desc, minutos))


def insertar_desperdicios(cur, turno_id, tipo_maquina):
    opciones = DESPERDICIOS_TIPO.get(tipo_maquina, DESPERDICIOS_TIPO['inyeccion'])
    seleccionados = random.sample(opciones, min(2, len(opciones)))
    for cod, defecto in seleccionados:
        cantidad = random.randint(1, 15)
        cur.execute("INSERT INTO desperdicios (turno_id, codigo, defecto, cantidad) VALUES (?,?,?,?)",
                    (turno_id, cod, defecto, cantidad))


def poblar():
    conn = sqlite3.connect(DB_PATH)
    cur  = conn.cursor()

    print("🧹 Limpiando datos demo anteriores...")
    limpiar_demo(cur)

    print("📦 Insertando órdenes demo...")
    orden_ids = {}
    for o in ORDENES_DEMO:
        oid = insertar_orden(cur, o)
        orden_ids[o[0]] = (oid, o[5], o[7], o[8])   # id, tipo, cavidades, ciclos
        print(f"  ✅ {o[0]} — {o[2][:40]} ({o[5]} #{o[6]})")

    print("\n📋 Generando turnos históricos (2 semanas)...")
    total_turnos = 0

    for fecha in FECHAS:
        for numero_orden, (orden_id, tipo_maquina, cavidades, ciclos) in orden_ids.items():
            # Saltamos algunos días aleatoriamente para simular realidad
            if random.random() < 0.15:
                continue

            empleado  = random.choice(EMPLEADOS_DEMO)
            h_inicio  = f"0{random.randint(6,8)}:00" if random.random() > 0.5 else "07:00"
            h_fin     = "15:00" if "07" in h_inicio else "16:00"

            turno_id = insertar_turno(cur, orden_id, fecha, empleado, h_inicio, h_fin)

            # Producción por hora basada en ciclos (und/hora)
            if ciclos > 0:
                base_hora = (3600 / ciclos) * cavidades
            else:
                base_hora = 60

            horas = [f"{h:02d}:00" for h in range(int(h_inicio[:2]), int(h_inicio[:2]) + 8)]
            insertar_registros(cur, turno_id, horas, base_hora)
            insertar_paradas(cur, turno_id, tipo_maquina,
                             n_np=random.randint(1, 3),
                             n_p=random.randint(1, 2))
            insertar_desperdicios(cur, turno_id, tipo_maquina)
            total_turnos += 1

    print(f"\n  ✅ {total_turnos} turnos históricos generados")

    # ── Turno activo por máquina (sin hora_fin) ───────────────────────────────
    print("\n⚡ Generando turnos activos (sin hora_fin) para tiempo real...")
    activos = 0
    for numero_orden, (orden_id, tipo_maquina, cavidades, ciclos) in orden_ids.items():
        empleado = random.choice(EMPLEADOS_DEMO)
        turno_id = insertar_turno(cur, orden_id, HOY.isoformat(), empleado, "07:00", None)

        if ciclos > 0:
            base_hora = (3600 / ciclos) * cavidades
        else:
            base_hora = 60

        # Registros de las horas transcurridas hoy
        hora_actual = __import__('datetime').datetime.now().hour
        horas_trabajadas = max(1, min(hora_actual - 7, 8))
        horas = [f"{h:02d}:00" for h in range(7, 7 + horas_trabajadas)]
        insertar_registros(cur, turno_id, horas, base_hora)
        insertar_paradas(cur, turno_id, tipo_maquina, n_np=1, n_p=1)
        activos += 1

    print(f"  ✅ {activos} turnos activos (tiempo real)")

    conn.commit()
    conn.close()

    print(f"""
╔══════════════════════════════════════════════════════════╗
║              DATOS DEMO POBLADOS CORRECTAMENTE           ║
╠══════════════════════════════════════════════════════════╣
║  Órdenes:   {len(ORDENES_DEMO):3d}  (7 inyectoras, 1 soplado,         ║
║             2 líneas, 2 acondicionamiento)               ║
║  Histórico: {total_turnos:3d}  turnos (últimas 2 semanas)           ║
║  Activos:   {activos:3d}  turnos sin hora_fin (tiempo real)     ║
╚══════════════════════════════════════════════════════════╝
    """)


if __name__ == "__main__":
    poblar()