from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from ..database import get_db
from ..models.models import Orden

router = APIRouter()

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