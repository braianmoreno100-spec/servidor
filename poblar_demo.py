# poblar_demo.py — datos demo para demostración del dashboard
# Ejecutar: python poblar_demo.py

from app.database import SessionLocal
from app.models.models import Orden, Turno, RegistroProduccion, Parada, Desperdicio
from datetime import date, datetime, timedelta
import random

db = SessionLocal()

def limpiar_demo():
    # Borra solo datos demo (número de orden empieza con 'DEMO')
    ordenes = db.query(Orden).filter(Orden.numero_orden.like('DEMO%')).all()
    for o in ordenes:
        turnos = db.query(Turno).filter(Turno.orden_id == o.id).all()
        for t in turnos:
            db.query(RegistroProduccion).filter(RegistroProduccion.turno_id == t.id).delete()
            db.query(Parada).filter(Parada.turno_id == t.id).delete()
            db.query(Desperdicio).filter(Desperdicio.turno_id == t.id).delete()
            db.delete(t)
        db.delete(o)
    db.commit()
    print("Demo anterior limpiada")

def poblar():
    limpiar_demo()

    maquinas = [
        {"numero_orden": "DEMO001", "codigo": "3240330005", "descripcion": "FRASCO COPROLOGICO",     "tipo": "linea",     "maquina": 1, "ciclos": 11, "cavidades": 4, "material": "polietileno de alta densidad", "lider_ced": "1073512622", "lider_nom": "Sanchez Soler Diana Carolina"},
        {"numero_orden": "DEMO002", "codigo": "1020100012", "descripcion": "TAPA ROSCA 28MM",         "tipo": "inyeccion", "maquina": 2, "ciclos": 18, "cavidades": 8, "material": "polipropileno",                 "lider_ced": "1073512622", "lider_nom": "Sanchez Soler Diana Carolina"},
        {"numero_orden": "DEMO003", "codigo": "2030200008", "descripcion": "FRASCO SOPLADO 250ML",    "tipo": "soplado",   "maquina": 3, "ciclos": 22, "cavidades": 2, "material": "polietileno de alta densidad", "lider_ced": "1073512622", "lider_nom": "Sanchez Soler Diana Carolina"},
        {"numero_orden": "DEMO004", "codigo": "4050400015", "descripcion": "FRASCO ORINA 100ML",      "tipo": "linea",     "maquina": 4, "ciclos": 14, "cavidades": 4, "material": "polipropileno",                 "lider_ced": "1073512622", "lider_nom": "Sanchez Soler Diana Carolina"},
        {"numero_orden": "DEMO005", "codigo": "1020100020", "descripcion": "TAPA SEGURIDAD NIÑOS",    "tipo": "inyeccion", "maquina": 5, "ciclos": 15, "cavidades": 6, "material": "polipropileno",                 "lider_ced": "1073512622", "lider_nom": "Sanchez Soler Diana Carolina"},
        {"numero_orden": "DEMO006", "codigo": "2030200015", "descripcion": "FRASCO SOPLADO 500ML",    "tipo": "soplado",   "maquina": 6, "ciclos": 28, "cavidades": 2, "material": "polietileno de alta densidad", "lider_ced": "1073512622", "lider_nom": "Sanchez Soler Diana Carolina"},
        {"numero_orden": "DEMO007", "codigo": "3240330010", "descripcion": "FRASCO ORINA ADULTO",     "tipo": "linea",     "maquina": 7, "ciclos": 11, "cavidades": 4, "material": "polietileno de alta densidad", "lider_ced": "1073512622", "lider_nom": "Sanchez Soler Diana Carolina"},
        {"numero_orden": "DEMO008", "codigo": "1020100030", "descripcion": "TAPA FLIP TOP 24MM",      "tipo": "inyeccion", "maquina": 8, "ciclos": 12, "cavidades": 8, "material": "polipropileno",                 "lider_ced": "1073512622", "lider_nom": "Sanchez Soler Diana Carolina"},
    ]

    empleados = [
        ("1005280752", "Villalba Parra Miguel Andres"),
        ("1006540231", "Correa Hernandez Yulia Dayana"),
        ("1007891234", "Martinez Lopez Carlos Alberto"),
        ("1008123456", "Rodriguez Perez Ana Maria"),
        ("1009456789", "Gomez Torres Luis Eduardo"),
        ("1010789012", "Herrera Castillo Diana Patricia"),
        ("1011234567", "Vargas Mendez Jorge Andres"),
        ("1012567890", "Zapata Rios Maria Fernanda"),
    ]

    hoy = date.today()

    for i, maq in enumerate(maquinas):
        # Crear orden activa
        orden = Orden(
            numero_orden=maq["numero_orden"],
            codigo_producto=maq["codigo"],
            descripcion_producto=maq["descripcion"],
            cantidad_producir=random.randint(1500, 4000),
            material=maq["material"],
            tipo_maquina=maq["tipo"],
            numero_maquina=maq["maquina"],
            cavidades=maq["cavidades"],
            ciclos=maq["ciclos"],
            tiene_pigmento=False,
            numero_pigmento="",
            descripcion_pigmento="",
            cedula_lider=maq["lider_ced"],
            nombre_lider=maq["lider_nom"],
            fecha_creacion=datetime.now() - timedelta(days=random.randint(0, 3)),
            activa=True,
        )
        db.add(orden)
        db.flush()

        ced, nom = empleados[i % len(empleados)]

        # Crear turno ABIERTO (sin hora_fin) — turno actual
        turno = Turno(
            orden_id=orden.id,
            cedula_empleado=ced,
            nombre_empleado=nom,
            fecha=str(hoy),
            turno="A" if i % 2 == 0 else "B",
            hora_inicio="06:00",
            hora_fin=None,  # abierto
        )
        db.add(turno)
        db.flush()

        # Registros de producción por hora (simulando 8 horas trabajadas)
        horas_trabajadas = random.randint(6, 10)
        ciclo = maq["ciclos"]
        cav   = maq["cavidades"]
        prod_hora = int(3600 / ciclo * cav * random.uniform(0.88, 1.02))

        for h in range(horas_trabajadas):
            hora_str = f"{6 + h:02d}:00"
            cantidad = int(prod_hora * random.uniform(0.92, 1.05))
            reg = RegistroProduccion(
                turno_id=turno.id,
                hora=hora_str,
                cantidad=cantidad,
            )
            db.add(reg)

        # Paradas no programadas (1-3 por turno)
        causas_np = [
            (5,  "FALLA ELECTRICA"),
            (12, "ATASCO MATERIAL"),
            (8,  "AJUSTE MOLDE"),
            (15, "FALLA HIDRAULICA"),
            (10, "CAMBIO HERRAMIENTA"),
        ]
        num_paradas = random.randint(1, 3)
        for _ in range(num_paradas):
            cod, desc = random.choice(causas_np)
            minutos = random.randint(8, 35)
            parada = Parada(
                turno_id=turno.id,
                codigo=cod,
                descripcion=desc,
                minutos=minutos,
                programada=False,
            )
            db.add(parada)

        # Parada programada (almuerzo/descanso)
        parada_prog = Parada(
            turno_id=turno.id,
            codigo=1,
            descripcion="DESCANSO PROGRAMADO",
            minutos=30,
            programada=True,
        )
        db.add(parada_prog)

        # Desperdicios (1-2 por turno)
        tipos_desp = [(1, "REBABAS"), (2, "LLENADO INCOMPLETO"), (3, "PELLETS SIN FUNDIR")]
        num_desp = random.randint(1, 2)
        for _ in range(num_desp):
            cod, desc = random.choice(tipos_desp)
            desp = Desperdicio(
                turno_id=turno.id,
                codigo=cod,
                defecto=desc,
                cantidad=random.randint(5, 40),
            )
            db.add(desp)

        print(f"✅ Orden {maq['numero_orden']} — {maq['descripcion']} — turno abierto creado")

    # Turnos HISTÓRICOS (últimas 2 semanas) para OEE tendencia y empleados
    print("\nCreando histórico...")
    for dias_atras in range(1, 15):
        fecha_hist = hoy - timedelta(days=dias_atras)
        for j, maq in enumerate(maquinas[:4]):  # solo 4 máquinas en histórico
            # Buscar orden existente
            orden_hist = db.query(Orden).filter(
                Orden.numero_orden == maq["numero_orden"]
            ).first()
            if not orden_hist:
                continue

            ced, nom = empleados[j % len(empleados)]
            hora_fin_h = random.randint(17, 20)

            turno_hist = Turno(
                orden_id=orden_hist.id,
                cedula_empleado=ced,
                nombre_empleado=nom,
                fecha=str(fecha_hist),
                turno="A" if j % 2 == 0 else "B",
                hora_inicio="06:00",
                hora_fin=f"{hora_fin_h:02d}:00",
            )
            db.add(turno_hist)
            db.flush()

            # Registros producción histórico
            horas_trab = hora_fin_h - 6
            prod_hora = int(3600 / maq["ciclos"] * maq["cavidades"] * random.uniform(0.85, 1.0))
            for h in range(horas_trab):
                db.add(RegistroProduccion(
                    turno_id=turno_hist.id,
                    hora=f"{6+h:02d}:00",
                    cantidad=int(prod_hora * random.uniform(0.90, 1.05)),
                ))

            # Paradas histórico
            for _ in range(random.randint(1, 3)):
                cod, desc = random.choice(causas_np)
                db.add(Parada(
                    turno_id=turno_hist.id,
                    codigo=cod,
                    descripcion=desc,
                    minutos=random.randint(5, 40),
                    programada=False,
                ))
            db.add(Parada(
                turno_id=turno_hist.id,
                codigo=1,
                descripcion="DESCANSO PROGRAMADO",
                minutos=30,
                programada=True,
            ))

    db.commit()
    print("\n✅ Demo completo — 8 órdenes activas + 2 semanas de histórico")

if __name__ == "__main__":
    poblar()