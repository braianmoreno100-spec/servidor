from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from ..database import get_db
from ..models.models import Orden

router = APIRouter()

# Máquinas válidas por tipo (None = cualquier valor permitido)
MAQUINAS_VALIDAS: dict[str, list[int] | None] = {
    'inyeccion':         [1, 2, 3, 4, 5, 6],
    'soplado':           None,
    'linea':             None,
    'acondicionamiento': [1, 2],
}

TIPOS_VALIDOS = list(MAQUINAS_VALIDAS.keys())


class OrdenCreate(BaseModel):
    numero_orden: str
    codigo_producto: str
    descripcion_producto: str
    cantidad_producir: int
    material: str
    tipo_maquina: str
    numero_maquina: str
    cavidades: int
    ciclos: float
    tiene_pigmento: bool
    numero_pigmento: Optional[str] = None
    descripcion_pigmento: Optional[str] = None
    cedula_lider: str
    nombre_lider: str


@router.post("/")
def crear_orden(data: OrdenCreate, db: Session = Depends(get_db)):
    # 1. Validar tipo_maquina
    if data.tipo_maquina not in TIPOS_VALIDOS:
        raise HTTPException(
            status_code=422,
            detail=f"tipo_maquina inválido: '{data.tipo_maquina}'. Debe ser uno de {TIPOS_VALIDOS}"
        )

    # 2. Validar numero_maquina según tipo
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
                detail=(
                    f"Para tipo '{data.tipo_maquina}' el número de máquina "
                    f"debe ser uno de {permitidos}. Recibido: {num}"
                )
            )

    orden = Orden(**data.model_dump())
    db.add(orden)
    db.commit()
    db.refresh(orden)
    return {"id": orden.id, "mensaje": "Orden creada correctamente"}


@router.get("/")
def listar_ordenes(db: Session = Depends(get_db)):
    ordenes = db.query(Orden).filter(Orden.activa == True).all()
    return ordenes


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