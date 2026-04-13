from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel

from ..database import get_db
from ..models import CausaParada, TiposDesperdicio

router = APIRouter(tags=["catalogos"])


# ─────────────────────────────────────────────
# SCHEMAS
# ─────────────────────────────────────────────

class CausaParadaResponse(BaseModel):
    id: int
    codigo: int
    descripcion: str
    programada: bool
    tipo_maquina: str
    activa: bool

class CausaParadaCreate(BaseModel):
    codigo: int
    descripcion: str
    programada: bool
    tipo_maquina: str

class CausaParadaUpdate(BaseModel):
    descripcion: Optional[str] = None
    activa: Optional[bool] = None

class TiposDesperdicioResponse(BaseModel):
    id: int
    codigo: int
    descripcion: str
    activa: bool

class TiposDesperdicioCreate(BaseModel):
    codigo: int
    descripcion: str

class TiposDesperdicioUpdate(BaseModel):
    descripcion: Optional[str] = None
    activa: Optional[bool] = None


# ─────────────────────────────────────────────
# ENDPOINTS CAUSAS DE PARADA
# ─────────────────────────────────────────────

@router.get("/causas-parada", response_model=List[CausaParadaResponse])
def listar_causas_parada(
    tipo_maquina: Optional[str] = None,
    programada: Optional[bool] = None,
    solo_activas: bool = True,
    db: Session = Depends(get_db)
):
    """Lista causas de parada. Filtra por tipo_maquina (inyeccion/soplado/linea), programada y estado."""
    query = db.query(CausaParada)
    if solo_activas:
        query = query.filter(CausaParada.activa == True)
    if tipo_maquina:
        query = query.filter(CausaParada.tipo_maquina == tipo_maquina)
    if programada is not None:
        query = query.filter(CausaParada.programada == programada)
    return query.order_by(CausaParada.codigo).all()


@router.post("/causas-parada", response_model=CausaParadaResponse, status_code=status.HTTP_201_CREATED)
def crear_causa_parada(data: CausaParadaCreate, db: Session = Depends(get_db)):
    """Crea una nueva causa de parada."""
    existente = db.query(CausaParada).filter(
        CausaParada.codigo == data.codigo,
        CausaParada.tipo_maquina == data.tipo_maquina
    ).first()
    if existente:
        raise HTTPException(
            status_code=400,
            detail=f"Ya existe una causa con código {data.codigo} para {data.tipo_maquina}"
        )
    causa = CausaParada(**data.model_dump())
    db.add(causa)
    db.commit()
    db.refresh(causa)
    return causa


@router.put("/causas-parada/{causa_id}", response_model=CausaParadaResponse)
def actualizar_causa_parada(causa_id: int, data: CausaParadaUpdate, db: Session = Depends(get_db)):
    """Actualiza descripción o estado activo de una causa de parada."""
    causa = db.query(CausaParada).filter(CausaParada.id == causa_id).first()
    if not causa:
        raise HTTPException(status_code=404, detail="Causa no encontrada")
    if data.descripcion is not None:
        causa.descripcion = data.descripcion
    if data.activa is not None:
        causa.activa = data.activa
    db.commit()
    db.refresh(causa)
    return causa


# ─────────────────────────────────────────────
# ENDPOINTS TIPOS DE DESPERDICIO
# ─────────────────────────────────────────────

@router.get("/tipos-desperdicio", response_model=List[TiposDesperdicioResponse])
def listar_tipos_desperdicio(
    solo_activas: bool = True,
    db: Session = Depends(get_db)
):
    """Lista todos los tipos de desperdicio."""
    query = db.query(TiposDesperdicio)
    if solo_activas:
        query = query.filter(TiposDesperdicio.activa == True)
    return query.order_by(TiposDesperdicio.codigo).all()


@router.post("/tipos-desperdicio", response_model=TiposDesperdicioResponse, status_code=status.HTTP_201_CREATED)
def crear_tipo_desperdicio(data: TiposDesperdicioCreate, db: Session = Depends(get_db)):
    """Crea un nuevo tipo de desperdicio."""
    existente = db.query(TiposDesperdicio).filter(TiposDesperdicio.codigo == data.codigo).first()
    if existente:
        raise HTTPException(status_code=400, detail=f"Ya existe un tipo con código {data.codigo}")
    tipo = TiposDesperdicio(**data.model_dump())
    db.add(tipo)
    db.commit()
    db.refresh(tipo)
    return tipo


@router.put("/tipos-desperdicio/{tipo_id}", response_model=TiposDesperdicioResponse)
def actualizar_tipo_desperdicio(tipo_id: int, data: TiposDesperdicioUpdate, db: Session = Depends(get_db)):
    """Actualiza descripción o estado activo de un tipo de desperdicio."""
    tipo = db.query(TiposDesperdicio).filter(TiposDesperdicio.id == tipo_id).first()
    if not tipo:
        raise HTTPException(status_code=404, detail="Tipo de desperdicio no encontrado")
    if data.descripcion is not None:
        tipo.descripcion = data.descripcion
    if data.activa is not None:
        tipo.activa = data.activa
    db.commit()
    db.refresh(tipo)
    return tipo