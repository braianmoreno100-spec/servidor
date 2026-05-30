from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator
from datetime import datetime
import time
import socketio

from ..database import get_db
from ..models import Turno, RegistroProduccion, Parada, Desperdicio, Relevo, Orden
from ..socket_manager import get_sio

router = APIRouter(tags=["produccion"])

TURNOS_VALIDOS = [
    '6:00 am - 6:00 pm',
    '6:00 pm - 6:00 am',
    '6:30 am - 2:00 pm',
    '6:00 am - 4:00 pm',
]

# ─────────────────────────────────────────────
# SCHEMAS CON VALIDACIÓN
# ─────────────────────────────────────────────

class IniciarTurnoRequest(BaseModel):
    orden_id:        int = Field(..., gt=0)
    cedula_empleado: str = Field(..., min_length=5, max_length=20)
    nombre_empleado: str = Field(..., min_length=2, max_length=100)
    turno:           str = Field(..., description="Turno válido del sistema")
    hora_inicio:     str = Field(..., min_length=4, max_length=20)
    fecha:           str = Field(..., min_length=8, max_length=12)

    @field_validator('cedula_empleado')
    @classmethod
    def cedula_solo_numeros(cls, v: str) -> str:
        if not v.strip().isdigit():
            raise ValueError('La cédula del empleado debe contener solo números')
        return v.strip()

    @field_validator('turno')
    @classmethod
    def turno_valido(cls, v: str) -> str:
        if v not in TURNOS_VALIDOS:
            raise ValueError(f"Turno inválido. Debe ser uno de {TURNOS_VALIDOS}")
        return v

    @field_validator('fecha')
    @classmethod
    def fecha_valida(cls, v: str) -> str:
        # Acepta formato DD/MM/YYYY o YYYY-MM-DD
        v = v.strip()
        try:
            if '-' in v:
                datetime.strptime(v, '%Y-%m-%d')
            elif '/' in v:
                datetime.strptime(v, '%d/%m/%Y')
            else:
                raise ValueError()
        except ValueError:
            raise ValueError('Formato de fecha inválido. Use DD/MM/YYYY o YYYY-MM-DD')
        return v


class IniciarTurnoResponse(BaseModel):
    turno_id: int
    mensaje:  str


class CerrarTurnoRequest(BaseModel):
    turno_id: int = Field(..., gt=0)
    hora_fin: str = Field(..., min_length=4, max_length=20)


class RegistroProduccionRequest(BaseModel):
    turno_id: int = Field(..., gt=0)
    hora:     str = Field(..., min_length=4, max_length=20)
    cantidad: int = Field(..., gt=0, le=500_000, description="Entre 1 y 500.000 unidades por hora")


class RegistroProduccionResponse(BaseModel):
    id:       int
    turno_id: int
    hora:     str
    cantidad: int


class ParadaRequest(BaseModel):
    turno_id:    int  = Field(..., gt=0)
    codigo:      int  = Field(..., ge=1, le=999)
    descripcion: str  = Field(..., min_length=2, max_length=200)
    minutos:     int  = Field(..., ge=1, le=480, description="Entre 1 y 480 minutos (1 turno)")
    programada:  bool


class ParadaIniciarRequest(BaseModel):
    turno_id:         int  = Field(..., gt=0)
    codigo:           int  = Field(..., ge=1, le=999)
    descripcion:      str  = Field(..., min_length=2, max_length=200)
    programada:       bool
    timestamp_inicio: int  = Field(..., gt=0, description="Epoch ms válido")

    @field_validator('timestamp_inicio')
    @classmethod
    def timestamp_razonable(cls, v: int) -> int:
        ahora_ms = int(time.time() * 1000)
        # No puede ser más de 5 minutos en el futuro ni más de 24h en el pasado
        if v > ahora_ms + 300_000:
            raise ValueError('timestamp_inicio no puede ser en el futuro')
        if v < ahora_ms - 86_400_000:
            raise ValueError('timestamp_inicio no puede ser mayor a 24 horas en el pasado')
        return v


class ParadaFinalizarRequest(BaseModel):
    timestamp_fin: int = Field(..., gt=0, description="Epoch ms válido")

    @field_validator('timestamp_fin')
    @classmethod
    def timestamp_razonable(cls, v: int) -> int:
        ahora_ms = int(time.time() * 1000)
        if v > ahora_ms + 60_000:
            raise ValueError('timestamp_fin no puede ser en el futuro')
        return v


class ParadaResponse(BaseModel):
    id:               int
    turno_id:         int
    codigo:           int
    descripcion:      str
    minutos:          int
    programada:       bool
    activa:           bool           = False
    timestamp_inicio: Optional[int] = None
    timestamp_fin:    Optional[int] = None


class ParadaActivaResponse(BaseModel):
    hay_parada_activa: bool
    parada_id:         Optional[int]  = None
    codigo:            Optional[int]  = None
    descripcion:       Optional[str]  = None
    programada:        Optional[bool] = None
    timestamp_inicio:  Optional[int]  = None
    segundos_activa:   Optional[int]  = None


class DesperdicioRequest(BaseModel):
    turno_id: int = Field(..., gt=0)
    codigo:   int = Field(..., ge=1, le=999)
    defecto:  str = Field(..., min_length=2, max_length=200)
    cantidad: int = Field(..., gt=0, le=100_000, description="Entre 1 y 100.000 unidades")


class DesperdicioResponse(BaseModel):
    id:       int
    turno_id: int
    codigo:   int
    defecto:  str
    cantidad: int


class RelevaRequest(BaseModel):
    turno_id:        int = Field(..., gt=0)
    cedula_empleado: str = Field(..., min_length=5, max_length=20)
    nombre_empleado: str = Field(..., min_length=2, max_length=100)
    hora_inicio:     str = Field(..., min_length=4, max_length=20)

    @field_validator('cedula_empleado')
    @classmethod
    def cedula_solo_numeros(cls, v: str) -> str:
        if not v.strip().isdigit():
            raise ValueError('La cédula del empleado debe contener solo números')
        return v.strip()


class RelevaResponse(BaseModel):
    id:              int
    turno_id:        int
    cedula_empleado: str
    nombre_empleado: str
    hora_inicio:     str
    hora_fin:        Optional[str]


class ResumenTurnoResponse(BaseModel):
    turno_id:             int
    orden_id:             int
    cedula_empleado:      str
    nombre_empleado:      str
    fecha:                str
    turno:                str
    hora_inicio:          str
    hora_fin:             Optional[str]
    total_produccion:     int
    total_paradas_min:    int
    total_desperdicio:    int
    registros_produccion: List[RegistroProduccionResponse]
    paradas:              List[ParadaResponse]
    desperdicios:         List[DesperdicioResponse]
    relevos:              List[RelevaResponse]


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def get_turno_or_404(turno_id: int, db: Session) -> Turno:
    turno = db.query(Turno).filter(Turno.id == turno_id).first()
    if not turno:
        raise HTTPException(status_code=404, detail="Turno no encontrado")
    return turno

def parada_to_response(p: Parada) -> ParadaResponse:
    return ParadaResponse(
        id=p.id, turno_id=p.turno_id, codigo=p.codigo,
        descripcion=p.descripcion, minutos=p.minutos, programada=p.programada,
        activa=p.activa or False,
        timestamp_inicio=p.timestamp_inicio,
        timestamp_fin=p.timestamp_fin,
    )


# ─────────────────────────────────────────────
# ENDPOINTS TURNO
# ─────────────────────────────────────────────

@router.post("/turno/iniciar", response_model=IniciarTurnoResponse, status_code=status.HTTP_201_CREATED)
async def iniciar_turno(
    data: IniciarTurnoRequest,
    db: Session = Depends(get_db),
    sio: socketio.AsyncServer = Depends(get_sio)
):
    orden = db.query(Orden).filter(Orden.id == data.orden_id, Orden.activa == True).first()
    if not orden:
        raise HTTPException(status_code=404, detail="Orden no encontrada o no está activa")

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

    turno_otra_orden = (
        db.query(Turno)
        .join(Orden, Turno.orden_id == Orden.id)
        .filter(
            Turno.cedula_empleado == data.cedula_empleado,
            Turno.hora_fin == None,
            Turno.orden_id != data.orden_id,
            Orden.activa == True
        )
        .first()
    )
    if turno_otra_orden:
        orden_activa = db.query(Orden).filter(Orden.id == turno_otra_orden.orden_id).first()
        numero = orden_activa.numero_orden if orden_activa else str(turno_otra_orden.orden_id)
        raise HTTPException(
            status_code=400,
            detail=f"El empleado ya tiene un turno activo en la orden {numero}. Debe cerrarlo antes de iniciar otro."
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

    await sio.emit("turno_iniciado", {
        "turno_id": turno.id, "orden_id": data.orden_id,
        "empleado": data.nombre_empleado, "turno": data.turno,
        "hora_inicio": data.hora_inicio, "fecha": data.fecha
    }, room=f"orden_{data.orden_id}")

    return IniciarTurnoResponse(turno_id=turno.id, mensaje="Turno iniciado correctamente")


@router.patch("/turno/{turno_id}/cerrar")
async def cerrar_turno(
    turno_id: int,
    data: CerrarTurnoRequest,
    db: Session = Depends(get_db),
    sio: socketio.AsyncServer = Depends(get_sio)
):
    turno = get_turno_or_404(turno_id, db)
    if turno.hora_fin:
        raise HTTPException(status_code=400, detail="El turno ya fue cerrado")

    parada_activa = db.query(Parada).filter(
        Parada.turno_id == turno_id,
        Parada.activa == True
    ).first()
    if parada_activa:
        ts_fin = int(time.time() * 1000)
        minutos = max(1, round((ts_fin - (parada_activa.timestamp_inicio or ts_fin)) / 60000))
        parada_activa.activa = False
        parada_activa.timestamp_fin = ts_fin
        parada_activa.minutos = minutos

    turno.hora_fin = data.hora_fin
    db.commit()

    await sio.emit("turno_cerrado", {
        "turno_id": turno_id, "orden_id": turno.orden_id, "hora_fin": data.hora_fin
    }, room=f"orden_{turno.orden_id}")

    return {"mensaje": "Turno cerrado correctamente", "turno_id": turno_id, "hora_fin": data.hora_fin}


@router.get("/turno/{turno_id}/resumen", response_model=ResumenTurnoResponse)
def resumen_turno(turno_id: int, db: Session = Depends(get_db)):
    turno = get_turno_or_404(turno_id, db)
    total_produccion  = sum(r.cantidad for r in turno.registros_produccion)
    total_paradas_min = sum(p.minutos for p in turno.paradas)
    total_desperdicio = sum(d.cantidad for d in turno.desperdicios)
    return ResumenTurnoResponse(
        turno_id=turno.id, orden_id=turno.orden_id,
        cedula_empleado=turno.cedula_empleado, nombre_empleado=turno.nombre_empleado,
        fecha=turno.fecha, turno=turno.turno,
        hora_inicio=turno.hora_inicio, hora_fin=turno.hora_fin,
        total_produccion=total_produccion, total_paradas_min=total_paradas_min,
        total_desperdicio=total_desperdicio,
        registros_produccion=[RegistroProduccionResponse(id=r.id, turno_id=r.turno_id, hora=r.hora, cantidad=r.cantidad) for r in turno.registros_produccion],
        paradas=[parada_to_response(p) for p in turno.paradas],
        desperdicios=[DesperdicioResponse(id=d.id, turno_id=d.turno_id, codigo=d.codigo, defecto=d.defecto, cantidad=d.cantidad) for d in turno.desperdicios],
        relevos=[RelevaResponse(id=r.id, turno_id=r.turno_id, cedula_empleado=r.cedula_empleado, nombre_empleado=r.nombre_empleado, hora_inicio=r.hora_inicio, hora_fin=r.hora_fin) for r in turno.relevos]
    )


@router.get("/turno/orden/{orden_id}", response_model=List[ResumenTurnoResponse])
def turnos_por_orden(orden_id: int, db: Session = Depends(get_db)):
    turnos = db.query(Turno).filter(Turno.orden_id == orden_id).all()
    resultado = []
    for turno in turnos:
        total_produccion  = sum(r.cantidad for r in turno.registros_produccion)
        total_paradas_min = sum(p.minutos for p in turno.paradas)
        total_desperdicio = sum(d.cantidad for d in turno.desperdicios)
        resultado.append(ResumenTurnoResponse(
            turno_id=turno.id, orden_id=turno.orden_id,
            cedula_empleado=turno.cedula_empleado, nombre_empleado=turno.nombre_empleado,
            fecha=turno.fecha, turno=turno.turno,
            hora_inicio=turno.hora_inicio, hora_fin=turno.hora_fin,
            total_produccion=total_produccion, total_paradas_min=total_paradas_min,
            total_desperdicio=total_desperdicio,
            registros_produccion=[RegistroProduccionResponse(id=r.id, turno_id=r.turno_id, hora=r.hora, cantidad=r.cantidad) for r in turno.registros_produccion],
            paradas=[parada_to_response(p) for p in turno.paradas],
            desperdicios=[DesperdicioResponse(id=d.id, turno_id=d.turno_id, codigo=d.codigo, defecto=d.defecto, cantidad=d.cantidad) for d in turno.desperdicios],
            relevos=[RelevaResponse(id=r.id, turno_id=r.turno_id, cedula_empleado=r.cedula_empleado, nombre_empleado=r.nombre_empleado, hora_inicio=r.hora_inicio, hora_fin=r.hora_fin) for r in turno.relevos]
        ))
    return resultado


# ─────────────────────────────────────────────
# ENDPOINTS REGISTRO PRODUCCIÓN
# ─────────────────────────────────────────────

@router.post("/registro", response_model=RegistroProduccionResponse, status_code=status.HTTP_201_CREATED)
async def agregar_registro(
    data: RegistroProduccionRequest,
    db: Session = Depends(get_db),
    sio: socketio.AsyncServer = Depends(get_sio)
):
    turno = get_turno_or_404(data.turno_id, db)
    if turno.hora_fin:
        raise HTTPException(status_code=400, detail="No se puede registrar producción en un turno cerrado")

    registro = RegistroProduccion(turno_id=data.turno_id, hora=data.hora, cantidad=data.cantidad)
    db.add(registro)
    db.commit()
    db.refresh(registro)

    await sio.emit("registro_agregado", {
        "id": registro.id, "turno_id": registro.turno_id,
        "orden_id": turno.orden_id, "hora": registro.hora, "cantidad": registro.cantidad
    }, room=f"orden_{turno.orden_id}")

    return RegistroProduccionResponse(id=registro.id, turno_id=registro.turno_id, hora=registro.hora, cantidad=registro.cantidad)


@router.get("/registro/turno/{turno_id}", response_model=List[RegistroProduccionResponse])
def registros_del_turno(turno_id: int, db: Session = Depends(get_db)):
    get_turno_or_404(turno_id, db)
    registros = db.query(RegistroProduccion).filter(RegistroProduccion.turno_id == turno_id).all()
    return [RegistroProduccionResponse(id=r.id, turno_id=r.turno_id, hora=r.hora, cantidad=r.cantidad) for r in registros]


@router.delete("/registro/{registro_id}", status_code=status.HTTP_204_NO_CONTENT)
async def eliminar_registro(
    registro_id: int,
    db: Session = Depends(get_db),
    sio: socketio.AsyncServer = Depends(get_sio)
):
    registro = db.query(RegistroProduccion).filter(RegistroProduccion.id == registro_id).first()
    if not registro:
        raise HTTPException(status_code=404, detail="Registro no encontrado")
    turno    = get_turno_or_404(registro.turno_id, db)
    orden_id = turno.orden_id
    db.delete(registro)
    db.commit()
    await sio.emit("registro_eliminado", {"id": registro_id, "turno_id": registro.turno_id, "orden_id": orden_id}, room=f"orden_{orden_id}")


# ─────────────────────────────────────────────
# ENDPOINTS PARADAS
# ─────────────────────────────────────────────

@router.post("/parada", response_model=ParadaResponse, status_code=status.HTTP_201_CREATED)
async def agregar_parada(
    data: ParadaRequest,
    db: Session = Depends(get_db),
    sio: socketio.AsyncServer = Depends(get_sio)
):
    turno = get_turno_or_404(data.turno_id, db)
    if turno.hora_fin:
        raise HTTPException(status_code=400, detail="No se puede registrar una parada en un turno cerrado")

    parada = Parada(
        turno_id=data.turno_id, codigo=data.codigo,
        descripcion=data.descripcion, minutos=data.minutos,
        programada=data.programada, activa=False,
    )
    db.add(parada)
    db.commit()
    db.refresh(parada)

    await sio.emit("parada_agregada", {
        "id": parada.id, "turno_id": parada.turno_id, "orden_id": turno.orden_id,
        "codigo": parada.codigo, "descripcion": parada.descripcion,
        "minutos": parada.minutos, "programada": parada.programada, "activa": False,
    }, room=f"orden_{turno.orden_id}")

    return parada_to_response(parada)


@router.post("/parada/iniciar", response_model=ParadaResponse, status_code=status.HTTP_201_CREATED)
async def iniciar_parada(
    data: ParadaIniciarRequest,
    db: Session = Depends(get_db),
    sio: socketio.AsyncServer = Depends(get_sio)
):
    turno = get_turno_or_404(data.turno_id, db)
    if turno.hora_fin:
        raise HTTPException(status_code=400, detail="No se puede registrar una parada en un turno cerrado")

    parada_existente = db.query(Parada).filter(
        Parada.turno_id == data.turno_id,
        Parada.activa == True
    ).first()
    if parada_existente:
        raise HTTPException(status_code=400, detail="Ya hay una parada activa en este turno")

    parada = Parada(
        turno_id=data.turno_id, codigo=data.codigo,
        descripcion=data.descripcion, minutos=0,
        programada=data.programada, activa=True,
        timestamp_inicio=data.timestamp_inicio, timestamp_fin=None,
    )
    db.add(parada)
    db.commit()
    db.refresh(parada)

    await sio.emit("parada_iniciada", {
        "id": parada.id, "turno_id": parada.turno_id, "orden_id": turno.orden_id,
        "codigo": parada.codigo, "descripcion": parada.descripcion,
        "programada": parada.programada, "activa": True,
        "timestamp_inicio": parada.timestamp_inicio,
    }, room=f"orden_{turno.orden_id}")

    return parada_to_response(parada)


@router.patch("/parada/{parada_id}/finalizar", response_model=ParadaResponse)
async def finalizar_parada(
    parada_id: int,
    data: ParadaFinalizarRequest,
    db: Session = Depends(get_db),
    sio: socketio.AsyncServer = Depends(get_sio)
):
    parada = db.query(Parada).filter(Parada.id == parada_id).first()
    if not parada:
        raise HTTPException(status_code=404, detail="Parada no encontrada")
    if not parada.activa:
        raise HTTPException(status_code=400, detail="Esta parada ya fue finalizada")

    turno = get_turno_or_404(parada.turno_id, db)

    ts_inicio = parada.timestamp_inicio or data.timestamp_fin
    minutos   = max(1, round((data.timestamp_fin - ts_inicio) / 60000))

    parada.activa        = False
    parada.timestamp_fin = data.timestamp_fin
    parada.minutos       = minutos
    db.commit()
    db.refresh(parada)

    await sio.emit("parada_finalizada", {
        "id": parada.id, "turno_id": parada.turno_id, "orden_id": turno.orden_id,
        "codigo": parada.codigo, "descripcion": parada.descripcion,
        "minutos": parada.minutos, "programada": parada.programada,
        "activa": False, "timestamp_fin": parada.timestamp_fin,
    }, room=f"orden_{turno.orden_id}")

    await sio.emit("parada_agregada", {
        "id": parada.id, "turno_id": parada.turno_id, "orden_id": turno.orden_id,
        "codigo": parada.codigo, "descripcion": parada.descripcion,
        "minutos": parada.minutos, "programada": parada.programada, "activa": False,
    }, room=f"orden_{turno.orden_id}")

    return parada_to_response(parada)


@router.get("/turno/{turno_id}/parada_activa", response_model=ParadaActivaResponse)
def parada_activa_turno(turno_id: int, db: Session = Depends(get_db)):
    get_turno_or_404(turno_id, db)
    parada = db.query(Parada).filter(
        Parada.turno_id == turno_id, Parada.activa == True
    ).first()

    if not parada:
        return ParadaActivaResponse(hay_parada_activa=False)

    ts_ahora = int(time.time() * 1000)
    segundos = max(0, round((ts_ahora - (parada.timestamp_inicio or ts_ahora)) / 1000))

    return ParadaActivaResponse(
        hay_parada_activa=True, parada_id=parada.id,
        codigo=parada.codigo, descripcion=parada.descripcion,
        programada=parada.programada, timestamp_inicio=parada.timestamp_inicio,
        segundos_activa=segundos,
    )


@router.get("/parada/turno/{turno_id}", response_model=List[ParadaResponse])
def paradas_del_turno(turno_id: int, db: Session = Depends(get_db)):
    get_turno_or_404(turno_id, db)
    paradas = db.query(Parada).filter(Parada.turno_id == turno_id).all()
    return [parada_to_response(p) for p in paradas]


@router.delete("/parada/{parada_id}", status_code=status.HTTP_204_NO_CONTENT)
async def eliminar_parada(
    parada_id: int,
    db: Session = Depends(get_db),
    sio: socketio.AsyncServer = Depends(get_sio)
):
    parada = db.query(Parada).filter(Parada.id == parada_id).first()
    if not parada:
        raise HTTPException(status_code=404, detail="Parada no encontrada")
    turno    = get_turno_or_404(parada.turno_id, db)
    orden_id = turno.orden_id
    db.delete(parada)
    db.commit()
    await sio.emit("parada_eliminada", {"id": parada_id, "turno_id": parada.turno_id, "orden_id": orden_id}, room=f"orden_{orden_id}")


# ─────────────────────────────────────────────
# ENDPOINTS DESPERDICIOS
# ─────────────────────────────────────────────

@router.post("/desperdicio", response_model=DesperdicioResponse, status_code=status.HTTP_201_CREATED)
async def agregar_desperdicio(
    data: DesperdicioRequest,
    db: Session = Depends(get_db),
    sio: socketio.AsyncServer = Depends(get_sio)
):
    turno = get_turno_or_404(data.turno_id, db)
    if turno.hora_fin:
        raise HTTPException(status_code=400, detail="No se puede registrar desperdicio en un turno cerrado")

    desperdicio = Desperdicio(
        turno_id=data.turno_id, codigo=data.codigo,
        defecto=data.defecto, cantidad=data.cantidad
    )
    db.add(desperdicio)
    db.commit()
    db.refresh(desperdicio)

    await sio.emit("desperdicio_agregado", {
        "id": desperdicio.id, "turno_id": desperdicio.turno_id, "orden_id": turno.orden_id,
        "codigo": desperdicio.codigo, "defecto": desperdicio.defecto, "cantidad": desperdicio.cantidad
    }, room=f"orden_{turno.orden_id}")

    return DesperdicioResponse(
        id=desperdicio.id, turno_id=desperdicio.turno_id,
        codigo=desperdicio.codigo, defecto=desperdicio.defecto, cantidad=desperdicio.cantidad
    )


@router.get("/desperdicio/turno/{turno_id}", response_model=List[DesperdicioResponse])
def desperdicios_del_turno(turno_id: int, db: Session = Depends(get_db)):
    get_turno_or_404(turno_id, db)
    desperdicios = db.query(Desperdicio).filter(Desperdicio.turno_id == turno_id).all()
    return [DesperdicioResponse(id=d.id, turno_id=d.turno_id, codigo=d.codigo, defecto=d.defecto, cantidad=d.cantidad) for d in desperdicios]


@router.delete("/desperdicio/{desperdicio_id}", status_code=status.HTTP_204_NO_CONTENT)
async def eliminar_desperdicio(
    desperdicio_id: int,
    db: Session = Depends(get_db),
    sio: socketio.AsyncServer = Depends(get_sio)
):
    desperdicio = db.query(Desperdicio).filter(Desperdicio.id == desperdicio_id).first()
    if not desperdicio:
        raise HTTPException(status_code=404, detail="Desperdicio no encontrado")
    turno    = get_turno_or_404(desperdicio.turno_id, db)
    orden_id = turno.orden_id
    db.delete(desperdicio)
    db.commit()
    await sio.emit("desperdicio_eliminado", {"id": desperdicio_id, "turno_id": desperdicio.turno_id, "orden_id": orden_id}, room=f"orden_{orden_id}")


# ─────────────────────────────────────────────
# ENDPOINTS RELEVOS
# ─────────────────────────────────────────────

@router.post("/relevo", response_model=RelevaResponse, status_code=status.HTTP_201_CREATED)
async def agregar_relevo(
    data: RelevaRequest,
    db: Session = Depends(get_db),
    sio: socketio.AsyncServer = Depends(get_sio)
):
    turno = get_turno_or_404(data.turno_id, db)
    if turno.hora_fin:
        raise HTTPException(status_code=400, detail="No se puede registrar un relevo en un turno cerrado")

    relevo = Relevo(
        turno_id=data.turno_id, cedula_empleado=data.cedula_empleado,
        nombre_empleado=data.nombre_empleado, hora_inicio=data.hora_inicio, hora_fin=None
    )
    db.add(relevo)
    db.commit()
    db.refresh(relevo)

    await sio.emit("relevo_agregado", {
        "id": relevo.id, "turno_id": relevo.turno_id, "orden_id": turno.orden_id,
        "cedula_empleado": relevo.cedula_empleado, "nombre_empleado": relevo.nombre_empleado,
        "hora_inicio": relevo.hora_inicio
    }, room=f"orden_{turno.orden_id}")

    return RelevaResponse(
        id=relevo.id, turno_id=relevo.turno_id, cedula_empleado=relevo.cedula_empleado,
        nombre_empleado=relevo.nombre_empleado, hora_inicio=relevo.hora_inicio, hora_fin=relevo.hora_fin
    )


@router.patch("/relevo/{relevo_id}/cerrar")
async def cerrar_relevo(
    relevo_id: int,
    hora_fin: str,
    db: Session = Depends(get_db),
    sio: socketio.AsyncServer = Depends(get_sio)
):
    relevo = db.query(Relevo).filter(Relevo.id == relevo_id).first()
    if not relevo:
        raise HTTPException(status_code=404, detail="Relevo no encontrado")
    if relevo.hora_fin:
        raise HTTPException(status_code=400, detail="El relevo ya fue cerrado")

    turno = get_turno_or_404(relevo.turno_id, db)
    relevo.hora_fin = hora_fin
    db.commit()

    await sio.emit("relevo_cerrado", {
        "id": relevo_id, "turno_id": relevo.turno_id,
        "orden_id": turno.orden_id, "hora_fin": hora_fin
    }, room=f"orden_{turno.orden_id}")

    return {"mensaje": "Relevo cerrado", "relevo_id": relevo_id, "hora_fin": hora_fin}


@router.get("/relevo/turno/{turno_id}", response_model=List[RelevaResponse])
def relevos_del_turno(turno_id: int, db: Session = Depends(get_db)):
    get_turno_or_404(turno_id, db)
    relevos = db.query(Relevo).filter(Relevo.turno_id == turno_id).all()
    return [RelevaResponse(
        id=r.id, turno_id=r.turno_id, cedula_empleado=r.cedula_empleado,
        nombre_empleado=r.nombre_empleado, hora_inicio=r.hora_inicio, hora_fin=r.hora_fin
    ) for r in relevos]


# ─────────────────────────────────────────────
# ENDPOINT OEE TURNO
# ─────────────────────────────────────────────

class OeeTurnoResponse(BaseModel):
    turno_id:         int
    orden_id:         int
    oee:              float
    disponibilidad:   float
    eficiencia:       float
    calidad:          float
    contador:         int
    prod_planeada:    float
    prod_real:        int
    rechazadas:       int
    paradas_np_min:   int
    paradas_prog_min: int
    t_trabajado_h:    float
    t_real_h:         float
    hora_inicio:      str
    hora_fin:         Optional[str]


@router.get("/turno/{turno_id}/oee", response_model=OeeTurnoResponse)
def oee_turno(turno_id: int, db: Session = Depends(get_db)):
    from ..oee_calc import calcular_oee_turno

    turno = get_turno_or_404(turno_id, db)
    orden = db.query(Orden).filter(Orden.id == turno.orden_id).first()
    if not orden:
        raise HTTPException(status_code=404, detail="Orden no encontrada")

    kpis = calcular_oee_turno(turno, orden)

    return OeeTurnoResponse(
        turno_id         = turno.id,
        orden_id         = turno.orden_id,
        oee              = kpis["oee"],
        disponibilidad   = kpis["disponibilidad"],
        eficiencia       = kpis["eficiencia"],
        calidad          = kpis["calidad"],
        contador         = kpis["contador"],
        prod_planeada    = kpis["prod_planeada"],
        prod_real        = kpis["prod_real"],
        rechazadas       = kpis["rechazadas"],
        paradas_np_min   = kpis["paradas_np_min"],
        paradas_prog_min = kpis["paradas_prog_min"],
        t_trabajado_h    = kpis["t_trabajado_h"],
        t_real_h         = kpis["t_real_h"],
        hora_inicio      = turno.hora_inicio,
        hora_fin         = turno.hora_fin,
    )