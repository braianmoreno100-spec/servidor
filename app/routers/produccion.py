from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from ..database import get_db
from ..models import Turno, RegistroProduccion, Parada, Desperdicio, Relevo, Orden

router = APIRouter(tags=["produccion"])


# ─────────────────────────────────────────────
# SCHEMAS
# ─────────────────────────────────────────────

class IniciarTurnoRequest(BaseModel):
    orden_id: int
    cedula_empleado: str
    nombre_empleado: str
    turno: str          # "A", "B" o "C"
    hora_inicio: str    # "HH:MM"
    fecha: str          # "YYYY-MM-DD"

class IniciarTurnoResponse(BaseModel):
    turno_id: int
    mensaje: str

class CerrarTurnoRequest(BaseModel):
    turno_id: int
    hora_fin: str       # "HH:MM"

class RegistroProduccionRequest(BaseModel):
    turno_id: int
    hora: str           # "HH:MM"
    cantidad: int

class RegistroProduccionResponse(BaseModel):
    id: int
    turno_id: int
    hora: str
    cantidad: int

class ParadaRequest(BaseModel):
    turno_id: int
    codigo: int
    descripcion: str
    minutos: int
    programada: bool

class ParadaResponse(BaseModel):
    id: int
    turno_id: int
    codigo: int
    descripcion: str
    minutos: int
    programada: bool

class DesperdicioRequest(BaseModel):
    turno_id: int
    codigo: int
    defecto: str
    cantidad: int

class DesperdicioResponse(BaseModel):
    id: int
    turno_id: int
    codigo: int
    defecto: str
    cantidad: int

class RelevaRequest(BaseModel):
    turno_id: int
    cedula_empleado: str
    nombre_empleado: str
    hora_inicio: str    # "HH:MM"

class RelevaResponse(BaseModel):
    id: int
    turno_id: int
    cedula_empleado: str
    nombre_empleado: str
    hora_inicio: str
    hora_fin: Optional[str]

class ResumenTurnoResponse(BaseModel):
    turno_id: int
    orden_id: int
    cedula_empleado: str
    nombre_empleado: str
    fecha: str
    turno: str
    hora_inicio: str
    hora_fin: Optional[str]
    total_produccion: int
    total_paradas_min: int
    total_desperdicio: int
    registros_produccion: List[RegistroProduccionResponse]
    paradas: List[ParadaResponse]
    desperdicios: List[DesperdicioResponse]
    relevos: List[RelevaResponse]


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def get_turno_or_404(turno_id: int, db: Session) -> Turno:
    turno = db.query(Turno).filter(Turno.id == turno_id).first()
    if not turno:
        raise HTTPException(status_code=404, detail="Turno no encontrado")
    return turno


# ─────────────────────────────────────────────
# ENDPOINTS TURNO
# ─────────────────────────────────────────────

@router.post("/turno/iniciar", response_model=IniciarTurnoResponse, status_code=status.HTTP_201_CREATED)
def iniciar_turno(data: IniciarTurnoRequest, db: Session = Depends(get_db)):
    """Inicia un nuevo turno para una orden de producción."""

    # Verificar que la orden existe y está activa
    orden = db.query(Orden).filter(Orden.id == data.orden_id, Orden.activa == True).first()
    if not orden:
        raise HTTPException(status_code=404, detail="Orden no encontrada o no está activa")

    # Verificar que no haya un turno abierto para este empleado en esta orden hoy
    turno_abierto = db.query(Turno).filter(
        Turno.orden_id == data.orden_id,
        Turno.cedula_empleado == data.cedula_empleado,
        Turno.fecha == data.fecha,
        Turno.hora_fin == None
    ).first()
    if turno_abierto:
        raise HTTPException(
            status_code=400,
            detail=f"Ya existe un turno abierto (ID: {turno_abierto.id}) para este empleado en esta orden hoy"
        )

    turno = Turno(
        orden_id=data.orden_id,
        cedula_empleado=data.cedula_empleado,
        nombre_empleado=data.nombre_empleado,
        fecha=data.fecha,
        turno=data.turno,
        hora_inicio=data.hora_inicio,
        hora_fin=None
    )
    db.add(turno)
    db.commit()
    db.refresh(turno)

    return IniciarTurnoResponse(turno_id=turno.id, mensaje="Turno iniciado correctamente")


@router.patch("/turno/{turno_id}/cerrar")
def cerrar_turno(turno_id: int, data: CerrarTurnoRequest, db: Session = Depends(get_db)):
    """Cierra un turno registrando la hora de fin."""
    turno = get_turno_or_404(turno_id, db)

    if turno.hora_fin:
        raise HTTPException(status_code=400, detail="El turno ya fue cerrado")

    turno.hora_fin = data.hora_fin
    db.commit()
    return {"mensaje": "Turno cerrado correctamente", "turno_id": turno_id, "hora_fin": data.hora_fin}


@router.get("/turno/{turno_id}/resumen", response_model=ResumenTurnoResponse)
def resumen_turno(turno_id: int, db: Session = Depends(get_db)):
    """Devuelve el resumen completo de un turno con toda su data."""
    turno = get_turno_or_404(turno_id, db)

    total_produccion = sum(r.cantidad for r in turno.registros_produccion)
    total_paradas_min = sum(p.minutos for p in turno.paradas)
    total_desperdicio = sum(d.cantidad for d in turno.desperdicios)

    return ResumenTurnoResponse(
        turno_id=turno.id,
        orden_id=turno.orden_id,
        cedula_empleado=turno.cedula_empleado,
        nombre_empleado=turno.nombre_empleado,
        fecha=turno.fecha,
        turno=turno.turno,
        hora_inicio=turno.hora_inicio,
        hora_fin=turno.hora_fin,
        total_produccion=total_produccion,
        total_paradas_min=total_paradas_min,
        total_desperdicio=total_desperdicio,
        registros_produccion=[
            RegistroProduccionResponse(id=r.id, turno_id=r.turno_id, hora=r.hora, cantidad=r.cantidad)
            for r in turno.registros_produccion
        ],
        paradas=[
            ParadaResponse(id=p.id, turno_id=p.turno_id, codigo=p.codigo,
                           descripcion=p.descripcion, minutos=p.minutos, programada=p.programada)
            for p in turno.paradas
        ],
        desperdicios=[
            DesperdicioResponse(id=d.id, turno_id=d.turno_id, codigo=d.codigo,
                                defecto=d.defecto, cantidad=d.cantidad)
            for d in turno.desperdicios
        ],
        relevos=[
            RelevaResponse(id=r.id, turno_id=r.turno_id, cedula_empleado=r.cedula_empleado,
                           nombre_empleado=r.nombre_empleado, hora_inicio=r.hora_inicio, hora_fin=r.hora_fin)
            for r in turno.relevos
        ]
    )


@router.get("/turno/orden/{orden_id}", response_model=List[ResumenTurnoResponse])
def turnos_por_orden(orden_id: int, db: Session = Depends(get_db)):
    """Lista todos los turnos de una orden."""
    turnos = db.query(Turno).filter(Turno.orden_id == orden_id).all()
    resultado = []
    for turno in turnos:
        total_produccion = sum(r.cantidad for r in turno.registros_produccion)
        total_paradas_min = sum(p.minutos for p in turno.paradas)
        total_desperdicio = sum(d.cantidad for d in turno.desperdicios)
        resultado.append(ResumenTurnoResponse(
            turno_id=turno.id,
            orden_id=turno.orden_id,
            cedula_empleado=turno.cedula_empleado,
            nombre_empleado=turno.nombre_empleado,
            fecha=turno.fecha,
            turno=turno.turno,
            hora_inicio=turno.hora_inicio,
            hora_fin=turno.hora_fin,
            total_produccion=total_produccion,
            total_paradas_min=total_paradas_min,
            total_desperdicio=total_desperdicio,
            registros_produccion=[
                RegistroProduccionResponse(id=r.id, turno_id=r.turno_id, hora=r.hora, cantidad=r.cantidad)
                for r in turno.registros_produccion
            ],
            paradas=[
                ParadaResponse(id=p.id, turno_id=p.turno_id, codigo=p.codigo,
                               descripcion=p.descripcion, minutos=p.minutos, programada=p.programada)
                for p in turno.paradas
            ],
            desperdicios=[
                DesperdicioResponse(id=d.id, turno_id=d.turno_id, codigo=d.codigo,
                                    defecto=d.defecto, cantidad=d.cantidad)
                for d in turno.desperdicios
            ],
            relevos=[
                RelevaResponse(id=r.id, turno_id=r.turno_id, cedula_empleado=r.cedula_empleado,
                               nombre_empleado=r.nombre_empleado, hora_inicio=r.hora_inicio, hora_fin=r.hora_fin)
                for r in turno.relevos
            ]
        ))
    return resultado


# ─────────────────────────────────────────────
# ENDPOINTS REGISTRO PRODUCCIÓN (por hora)
# ─────────────────────────────────────────────

@router.post("/registro", response_model=RegistroProduccionResponse, status_code=status.HTTP_201_CREATED)
def agregar_registro(data: RegistroProduccionRequest, db: Session = Depends(get_db)):
    """Agrega un registro de producción horario al turno."""
    turno = get_turno_or_404(data.turno_id, db)

    if turno.hora_fin:
        raise HTTPException(status_code=400, detail="No se puede registrar producción en un turno cerrado")

    registro = RegistroProduccion(
        turno_id=data.turno_id,
        hora=data.hora,
        cantidad=data.cantidad
    )
    db.add(registro)
    db.commit()
    db.refresh(registro)

    return RegistroProduccionResponse(
        id=registro.id,
        turno_id=registro.turno_id,
        hora=registro.hora,
        cantidad=registro.cantidad
    )


@router.get("/registro/turno/{turno_id}", response_model=List[RegistroProduccionResponse])
def registros_del_turno(turno_id: int, db: Session = Depends(get_db)):
    """Lista todos los registros de producción de un turno."""
    get_turno_or_404(turno_id, db)
    registros = db.query(RegistroProduccion).filter(RegistroProduccion.turno_id == turno_id).all()
    return [
        RegistroProduccionResponse(id=r.id, turno_id=r.turno_id, hora=r.hora, cantidad=r.cantidad)
        for r in registros
    ]


@router.delete("/registro/{registro_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_registro(registro_id: int, db: Session = Depends(get_db)):
    """Elimina un registro de producción (corrección de error)."""
    registro = db.query(RegistroProduccion).filter(RegistroProduccion.id == registro_id).first()
    if not registro:
        raise HTTPException(status_code=404, detail="Registro no encontrado")
    db.delete(registro)
    db.commit()


# ─────────────────────────────────────────────
# ENDPOINTS PARADAS
# ─────────────────────────────────────────────

@router.post("/parada", response_model=ParadaResponse, status_code=status.HTTP_201_CREATED)
def agregar_parada(data: ParadaRequest, db: Session = Depends(get_db)):
    """Registra una parada en el turno."""
    turno = get_turno_or_404(data.turno_id, db)

    if turno.hora_fin:
        raise HTTPException(status_code=400, detail="No se puede registrar una parada en un turno cerrado")

    parada = Parada(
        turno_id=data.turno_id,
        codigo=data.codigo,
        descripcion=data.descripcion,
        minutos=data.minutos,
        programada=data.programada
    )
    db.add(parada)
    db.commit()
    db.refresh(parada)

    return ParadaResponse(
        id=parada.id,
        turno_id=parada.turno_id,
        codigo=parada.codigo,
        descripcion=parada.descripcion,
        minutos=parada.minutos,
        programada=parada.programada
    )


@router.get("/parada/turno/{turno_id}", response_model=List[ParadaResponse])
def paradas_del_turno(turno_id: int, db: Session = Depends(get_db)):
    """Lista todas las paradas de un turno."""
    get_turno_or_404(turno_id, db)
    paradas = db.query(Parada).filter(Parada.turno_id == turno_id).all()
    return [
        ParadaResponse(id=p.id, turno_id=p.turno_id, codigo=p.codigo,
                       descripcion=p.descripcion, minutos=p.minutos, programada=p.programada)
        for p in paradas
    ]


@router.delete("/parada/{parada_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_parada(parada_id: int, db: Session = Depends(get_db)):
    """Elimina una parada registrada."""
    parada = db.query(Parada).filter(Parada.id == parada_id).first()
    if not parada:
        raise HTTPException(status_code=404, detail="Parada no encontrada")
    db.delete(parada)
    db.commit()


# ─────────────────────────────────────────────
# ENDPOINTS DESPERDICIOS
# ─────────────────────────────────────────────

@router.post("/desperdicio", response_model=DesperdicioResponse, status_code=status.HTTP_201_CREATED)
def agregar_desperdicio(data: DesperdicioRequest, db: Session = Depends(get_db)):
    """Registra un desperdicio en el turno."""
    turno = get_turno_or_404(data.turno_id, db)

    if turno.hora_fin:
        raise HTTPException(status_code=400, detail="No se puede registrar desperdicio en un turno cerrado")

    desperdicio = Desperdicio(
        turno_id=data.turno_id,
        codigo=data.codigo,
        defecto=data.defecto,
        cantidad=data.cantidad
    )
    db.add(desperdicio)
    db.commit()
    db.refresh(desperdicio)

    return DesperdicioResponse(
        id=desperdicio.id,
        turno_id=desperdicio.turno_id,
        codigo=desperdicio.codigo,
        defecto=desperdicio.defecto,
        cantidad=desperdicio.cantidad
    )


@router.get("/desperdicio/turno/{turno_id}", response_model=List[DesperdicioResponse])
def desperdicios_del_turno(turno_id: int, db: Session = Depends(get_db)):
    """Lista todos los desperdicios de un turno."""
    get_turno_or_404(turno_id, db)
    desperdicios = db.query(Desperdicio).filter(Desperdicio.turno_id == turno_id).all()
    return [
        DesperdicioResponse(id=d.id, turno_id=d.turno_id, codigo=d.codigo,
                            defecto=d.defecto, cantidad=d.cantidad)
        for d in desperdicios
    ]


@router.delete("/desperdicio/{desperdicio_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_desperdicio(desperdicio_id: int, db: Session = Depends(get_db)):
    """Elimina un desperdicio registrado."""
    desperdicio = db.query(Desperdicio).filter(Desperdicio.id == desperdicio_id).first()
    if not desperdicio:
        raise HTTPException(status_code=404, detail="Desperdicio no encontrado")
    db.delete(desperdicio)
    db.commit()


# ─────────────────────────────────────────────
# ENDPOINTS RELEVOS
# ─────────────────────────────────────────────

@router.post("/relevo", response_model=RelevaResponse, status_code=status.HTTP_201_CREATED)
def agregar_relevo(data: RelevaRequest, db: Session = Depends(get_db)):
    """Registra un relevo de empleado en el turno."""
    turno = get_turno_or_404(data.turno_id, db)

    if turno.hora_fin:
        raise HTTPException(status_code=400, detail="No se puede registrar un relevo en un turno cerrado")

    relevo = Relevo(
        turno_id=data.turno_id,
        cedula_empleado=data.cedula_empleado,
        nombre_empleado=data.nombre_empleado,
        hora_inicio=data.hora_inicio,
        hora_fin=None
    )
    db.add(relevo)
    db.commit()
    db.refresh(relevo)

    return RelevaResponse(
        id=relevo.id,
        turno_id=relevo.turno_id,
        cedula_empleado=relevo.cedula_empleado,
        nombre_empleado=relevo.nombre_empleado,
        hora_inicio=relevo.hora_inicio,
        hora_fin=relevo.hora_fin
    )


@router.patch("/relevo/{relevo_id}/cerrar")
def cerrar_relevo(relevo_id: int, hora_fin: str, db: Session = Depends(get_db)):
    """Cierra un relevo registrando la hora de fin."""
    relevo = db.query(Relevo).filter(Relevo.id == relevo_id).first()
    if not relevo:
        raise HTTPException(status_code=404, detail="Relevo no encontrado")
    if relevo.hora_fin:
        raise HTTPException(status_code=400, detail="El relevo ya fue cerrado")

    relevo.hora_fin = hora_fin
    db.commit()
    return {"mensaje": "Relevo cerrado", "relevo_id": relevo_id, "hora_fin": hora_fin}


@router.get("/relevo/turno/{turno_id}", response_model=List[RelevaResponse])
def relevos_del_turno(turno_id: int, db: Session = Depends(get_db)):
    """Lista todos los relevos de un turno."""
    get_turno_or_404(turno_id, db)
    relevos = db.query(Relevo).filter(Relevo.turno_id == turno_id).all()
    return [
        RelevaResponse(id=r.id, turno_id=r.turno_id, cedula_empleado=r.cedula_empleado,
                       nombre_empleado=r.nombre_empleado, hora_inicio=r.hora_inicio, hora_fin=r.hora_fin)
        for r in relevos
    ]