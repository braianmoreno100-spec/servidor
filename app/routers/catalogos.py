from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import Column, Integer, String, text
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime
from app.models import CausaParada, TiposDesperdicio, Producto
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

# ── Historial ─────────────────────────────────
class HistorialCreate(BaseModel):
    usuario:       str
    catalogo:      str
    accion:        str
    entidad_id:    Optional[int]  = None
    entidad_label: Optional[str]  = None
    campo:         Optional[str]  = None
    valor_antes:   Optional[str]  = None
    valor_despues: Optional[str]  = None
    detalle:       Optional[str]  = None

class HistorialResponse(BaseModel):
    id:            int
    fecha:         str
    usuario:       str
    catalogo:      str
    accion:        str
    entidad_id:    Optional[int]
    entidad_label: Optional[str]
    campo:         Optional[str]
    valor_antes:   Optional[str]
    valor_despues: Optional[str]
    detalle:       Optional[str]


# ─────────────────────────────────────────────
# ENDPOINTS HISTORIAL
# ─────────────────────────────────────────────

@router.post("/historial", response_model=HistorialResponse, status_code=status.HTTP_201_CREATED)
def registrar_historial(data: HistorialCreate, db: Session = Depends(get_db)):
    """Registra un cambio en cualquier catálogo."""
    fecha = datetime.now().isoformat(timespec='seconds')
    result = db.execute(text("""
        INSERT INTO historial_catalogo
            (fecha, usuario, catalogo, accion, entidad_id, entidad_label, campo, valor_antes, valor_despues, detalle)
        VALUES
            (:fecha, :usuario, :catalogo, :accion, :entidad_id, :entidad_label, :campo, :valor_antes, :valor_despues, :detalle)
    """), {
        'fecha':         fecha,
        'usuario':       data.usuario,
        'catalogo':      data.catalogo,
        'accion':        data.accion,
        'entidad_id':    data.entidad_id,
        'entidad_label': data.entidad_label,
        'campo':         data.campo,
        'valor_antes':   data.valor_antes,
        'valor_despues': data.valor_despues,
        'detalle':       data.detalle,
    })
    db.commit()
    new_id = result.lastrowid
    row = db.execute(text("SELECT * FROM historial_catalogo WHERE id = :id"), {'id': new_id}).fetchone()
    return HistorialResponse(**dict(row._mapping))


@router.get("/historial", response_model=List[HistorialResponse])
def listar_historial(
    catalogo:  Optional[str] = None,
    usuario:   Optional[str] = None,
    limite:    int = 200,
    db: Session = Depends(get_db)
):
    """Devuelve el historial de cambios ordenado por fecha descendente."""
    filtros = []
    params: dict = {'limite': limite}
    if catalogo:
        filtros.append("catalogo = :catalogo")
        params['catalogo'] = catalogo
    if usuario:
        filtros.append("usuario LIKE :usuario")
        params['usuario'] = f'%{usuario}%'
    where = ('WHERE ' + ' AND '.join(filtros)) if filtros else ''
    sql = f"SELECT * FROM historial_catalogo {where} ORDER BY id DESC LIMIT :limite"
    rows = db.execute(text(sql), params).fetchall()
    return [HistorialResponse(**dict(r._mapping)) for r in rows]


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
    query = db.query(TiposDesperdicio)
    if solo_activas:
        query = query.filter(TiposDesperdicio.activa == True)
    return query.order_by(TiposDesperdicio.codigo).all()


@router.post("/tipos-desperdicio", response_model=TiposDesperdicioResponse, status_code=status.HTTP_201_CREATED)
def crear_tipo_desperdicio(data: TiposDesperdicioCreate, db: Session = Depends(get_db)):
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


# ─────────────────────────────────────────────
# ENDPOINTS PRODUCTOS
# ─────────────────────────────────────────────

from app.models import Producto

@router.get("/productos")
def listar_productos(db: Session = Depends(get_db)):
    return db.query(Producto).all()

@router.get("/productos/{codigo}")
def obtener_producto_por_codigo(codigo: str, db: Session = Depends(get_db)):
    producto = (
        db.query(Producto)
        .filter(Producto.codigo == codigo.upper())
        .first()
    )
    if not producto:
        raise HTTPException(status_code=404, detail=f"Producto '{codigo}' no encontrado")
    return producto

@router.put("/productos/{producto_id}")
def actualizar_producto(producto_id: int, datos: dict, db: Session = Depends(get_db)):
    prod = db.query(Producto).filter(Producto.id == producto_id).first()
    if not prod:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    for k, v in datos.items():
        setattr(prod, k, v)
    db.commit()
    db.refresh(prod)
    return prod

@router.post("/productos")
def crear_producto(datos: dict, db: Session = Depends(get_db)):
    prod = Producto(**datos)
    db.add(prod)
    db.commit()
    db.refresh(prod)
    return prod

@router.delete("/productos/{producto_id}")
def eliminar_producto(producto_id: int, db: Session = Depends(get_db)):
    prod = db.query(Producto).filter(Producto.id == producto_id).first()
    if not prod:
        raise HTTPException(status_code=404, detail="No encontrado")
    db.delete(prod)
    db.commit()
    return {"ok": True}


# ─────────────────────────────────────────────
# ENDPOINTS DELETE CATÁLOGOS
# ─────────────────────────────────────────────

@router.delete("/causas-parada/{causa_id}")
def eliminar_causa(causa_id: int, db: Session = Depends(get_db)):
    causa = db.query(CausaParada).filter(CausaParada.id == causa_id).first()
    if not causa:
        raise HTTPException(status_code=404, detail="No encontrado")
    db.delete(causa)
    db.commit()
    return {"ok": True}

@router.delete("/tipos-desperdicio/{tipo_id}")
def eliminar_desperdicio(tipo_id: int, db: Session = Depends(get_db)):
    tipo = db.query(TiposDesperdicio).filter(TiposDesperdicio.id == tipo_id).first()
    if not tipo:
        raise HTTPException(status_code=404, detail="No encontrado")
    db.delete(tipo)
    db.commit()
    return {"ok": True}