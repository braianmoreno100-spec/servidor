from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from ..database import get_db
from ..models.models import Lider, Empleado

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