from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from ..database import get_db
from ..models.models import Lider, Empleado
from app.models import Lider, Empleado
from sqlalchemy.orm import Session
from app.database import get_db
from fastapi import Depends, HTTPException

router = APIRouter()

class LoginLider(BaseModel):
    cedula: str

class LoginEmpleado(BaseModel):
    cedula: str

@router.post("/lider")
def login_lider(data: LoginLider, db: Session = Depends(get_db)):
    lider = db.query(Lider).filter(
        Lider.cedula == data.cedula,
        Lider.activo == True
    ).first()
    if not lider:
        raise HTTPException(status_code=404, detail="Líder no encontrado")
    return {"cedula": lider.cedula, "nombre": lider.nombre}

@router.post("/empleado")
def login_empleado(data: LoginEmpleado, db: Session = Depends(get_db)):
    empleado = db.query(Empleado).filter(
        Empleado.cedula == data.cedula,
        Empleado.activo == True
    ).first()
    if not empleado:
        raise HTTPException(status_code=404, detail="Empleado no encontrado")
    return {"cedula": empleado.cedula, "nombre": empleado.nombre}

    # GET listar todos los empleados
@router.get("/empleados")
def listar_empleados(db: Session = Depends(get_db)):
    return db.query(Empleado).all()

# GET listar todos los líderes
@router.get("/lideres")
def listar_lideres(db: Session = Depends(get_db)):
    return db.query(Lider).all()

# PUT actualizar empleado
@router.put("/empleados/{empleado_id}")
def actualizar_empleado(empleado_id: int, datos: dict, db: Session = Depends(get_db)):
    emp = db.query(Empleado).filter(Empleado.id == empleado_id).first()
    if not emp:
        raise HTTPException(status_code=404, detail="Empleado no encontrado")
    for k, v in datos.items():
        setattr(emp, k, v)
    db.commit()
    db.refresh(emp)
    return emp

# PUT actualizar líder
@router.put("/lideres/{lider_id}")
def actualizar_lider(lider_id: int, datos: dict, db: Session = Depends(get_db)):
    lid = db.query(Lider).filter(Lider.id == lider_id).first()
    if not lid:
        raise HTTPException(status_code=404, detail="Líder no encontrado")
    for k, v in datos.items():
        setattr(lid, k, v)
    db.commit()
    db.refresh(lid)
    return lid

    # POST crear empleado
@router.post("/empleados")
def crear_empleado(datos: dict, db: Session = Depends(get_db)):
    emp = Empleado(**datos)
    db.add(emp)
    db.commit()
    db.refresh(emp)
    return emp

# DELETE empleado
@router.delete("/empleados/{empleado_id}")
def eliminar_empleado(empleado_id: int, db: Session = Depends(get_db)):
    emp = db.query(Empleado).filter(Empleado.id == empleado_id).first()
    if not emp:
        raise HTTPException(status_code=404, detail="No encontrado")
    db.delete(emp)
    db.commit()
    return {"ok": True}

# POST crear líder
@router.post("/lideres")
def crear_lider(datos: dict, db: Session = Depends(get_db)):
    lid = Lider(**datos)
    db.add(lid)
    db.commit()
    db.refresh(lid)
    return lid

# DELETE líder
@router.delete("/lideres/{lider_id}")
def eliminar_lider(lider_id: int, db: Session = Depends(get_db)):
    lid = db.query(Lider).filter(Lider.id == lider_id).first()
    if not lid:
        raise HTTPException(status_code=404, detail="No encontrado")
    db.delete(lid)
    db.commit()
    return {"ok": True}