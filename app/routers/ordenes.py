from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field, field_validator
from typing import Optional
from ..database import get_db
from ..models.models import Orden, Turno

router = APIRouter()

MAQUINAS_VALIDAS: dict[str, list[int] | None] = {
    'inyeccion':         [1, 2, 3, 4, 5, 6, 7],
    'soplado':           None,
    'linea':             None,
    'acondicionamiento': [1, 2],
}

TIPOS_VALIDOS = list(MAQUINAS_VALIDAS.keys())


class OrdenCreate(BaseModel):
    numero_orden:         str   = Field(..., min_length=1, max_length=50, description="Número de orden")
    codigo_producto:      str   = Field(..., min_length=1, max_length=50)
    descripcion_producto: str   = Field(..., min_length=1, max_length=200)
    cantidad_producir:    int   = Field(..., gt=0, le=10_000_000, description="Debe ser mayor a 0")
    material:             str   = Field(..., min_length=1, max_length=100)
    tipo_maquina:         str   = Field(..., description="Tipo de máquina válido")
    numero_maquina:       str   = Field(..., min_length=1, max_length=10)
    cavidades:            int   = Field(..., gt=0, le=128, description="Entre 1 y 128")
    ciclos:               float = Field(..., gt=0, le=99999, description="Debe ser mayor a 0")
    tiene_pigmento:       bool
    numero_pigmento:      Optional[str] = Field(None, max_length=50)
    descripcion_pigmento: Optional[str] = Field(None, max_length=200)
    cedula_lider:         str   = Field(..., min_length=5, max_length=20)
    nombre_lider:         str   = Field(..., min_length=2, max_length=100)

    @field_validator('numero_orden', 'codigo_producto')
    @classmethod
    def no_espacios_extremos(cls, v: str) -> str:
        return v.strip()

    @field_validator('cedula_lider')
    @classmethod
    def cedula_solo_numeros(cls, v: str) -> str:
        if not v.strip().isdigit():
            raise ValueError('La cédula del líder debe contener solo números')
        return v.strip()

    @field_validator('tipo_maquina')
    @classmethod
    def tipo_valido(cls, v: str) -> str:
        if v not in TIPOS_VALIDOS:
            raise ValueError(f"tipo_maquina inválido. Debe ser uno de {TIPOS_VALIDOS}")
        return v

    @field_validator('numero_pigmento', 'descripcion_pigmento', mode='before')
    @classmethod
    def limpiar_opcional(cls, v):
        if v == '':
            return None
        return v


@router.post("/")
def crear_orden(data: OrdenCreate, db: Session = Depends(get_db)):
    # Validar numero_maquina según tipo
    permitidos = MAQUINAS_VALIDAS[data.tipo_maquina]
    if permitidos is not None:
        try:
            num = int(data.numero_maquina)
        except (ValueError, TypeError):
            raise HTTPException(
                status_code=422,
                detail=f"numero_maquina debe ser un entero para tipo '{data.tipo_maquina}'"
            )
        if num not in permitidos:
            raise HTTPException(
                status_code=422,
                detail=f"Para tipo '{data.tipo_maquina}' el número debe ser uno de {permitidos}. Recibido: {num}"
            )

    # Validar pigmento: si tiene_pigmento=True, los campos son obligatorios
    if data.tiene_pigmento:
        if not data.numero_pigmento or not data.numero_pigmento.strip():
            raise HTTPException(status_code=422, detail="numero_pigmento es obligatorio cuando tiene_pigmento=True")
        if not data.descripcion_pigmento or not data.descripcion_pigmento.strip():
            raise HTTPException(status_code=422, detail="descripcion_pigmento es obligatorio cuando tiene_pigmento=True")

    orden = Orden(**data.model_dump())
    db.add(orden)
    db.commit()
    db.refresh(orden)
    return {"id": orden.id, "mensaje": "Orden creada correctamente"}


@router.get("/")
def listar_ordenes(db: Session = Depends(get_db)):
    ordenes = db.query(Orden).order_by(Orden.id.desc()).all()
    return ordenes


@router.get("/verificar/{numero_orden}")
def verificar_numero_orden(numero_orden: str, db: Session = Depends(get_db)):
    orden = db.query(Orden).filter(Orden.numero_orden == numero_orden).first()

    if not orden:
        return {"existe": False}

    if not orden.activa:
        return {"existe": True, "activa": False}

    turno_activo = db.query(Turno).filter(
        Turno.orden_id == orden.id,
        Turno.hora_fin == None  # noqa: E711
    ).first()

    return {
        "existe":               True,
        "activa":               True,
        "orden_id":             orden.id,
        "turno_activo_id":      turno_activo.id if turno_activo else None,
        "codigo_producto":      orden.codigo_producto,
        "descripcion_producto": orden.descripcion_producto,
        "cantidad_producir":    orden.cantidad_producir,
        "material":             orden.material or "",
        "tipo_maquina":         orden.tipo_maquina,
        "numero_maquina":       orden.numero_maquina,
        "cavidades":            orden.cavidades,
        "ciclos":               orden.ciclos,
        "tiene_pigmento":       orden.tiene_pigmento,
        "numero_pigmento":      orden.numero_pigmento or "",
        "descripcion_pigmento": orden.descripcion_pigmento or "",
        "cedula_lider":         orden.cedula_lider,
        "nombre_lider":         orden.nombre_lider,
    }


@router.get("/{orden_id}")
def obtener_orden(orden_id: int, db: Session = Depends(get_db)):
    orden = db.query(Orden).filter(Orden.id == orden_id).first()
    if not orden:
        raise HTTPException(status_code=404, detail="Orden no encontrada")
    return orden


@router.put("/{orden_id}/cerrar")
def cerrar_orden(orden_id: int, db: Session = Depends(get_db)):
    orden = db.query(Orden).filter(Orden.id == orden_id).first()
    if not orden:
        raise HTTPException(status_code=404, detail="Orden no encontrada")
    orden.activa = False
    db.commit()
    return {"mensaje": "Orden cerrada correctamente"}