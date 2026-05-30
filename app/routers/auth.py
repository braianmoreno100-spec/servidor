"""
auth.py — Autenticación y gestión de usuarios
Mejoras de seguridad OWASP aplicadas:
  #1  Control de acceso — endpoints protegidos
  #7  Límite de intentos de login (5 intentos, bloqueo 15 min)
  #9  Logs de acceso y auditoría
  #10 Manejo seguro de errores (no expone info interna)
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from datetime import datetime, timedelta
from collections import defaultdict
import logging
import threading

from ..database import get_db
from ..models.models import Lider, Empleado

router = APIRouter()

# ── Logger de auditoría ───────────────────────────────────────────────────────
logger = logging.getLogger("kore.auth")

# ── Rate limiting para login (en memoria) ─────────────────────────────────────
# { "ip_cedula": {"intentos": int, "bloqueado_hasta": datetime} }
_intentos_login: dict = defaultdict(lambda: {"intentos": 0, "bloqueado_hasta": None})
_lock = threading.Lock()

MAX_INTENTOS   = 5          # intentos antes de bloquear
BLOQUEO_MINUTOS = 15        # minutos de bloqueo

def _verificar_limite(ip: str, cedula: str, rol: str) -> None:
    """Verifica si el IP+cédula está bloqueado por demasiados intentos fallidos."""
    key = f"{ip}_{cedula}_{rol}"
    with _lock:
        estado = _intentos_login[key]
        if estado["bloqueado_hasta"] and datetime.now() < estado["bloqueado_hasta"]:
            restante = int((estado["bloqueado_hasta"] - datetime.now()).total_seconds() / 60) + 1
            logger.warning(f"[BLOQUEADO] {rol} cedula={cedula} ip={ip} — {restante} min restantes")
            raise HTTPException(
                status_code=429,
                detail=f"Demasiados intentos fallidos. Intente de nuevo en {restante} minuto(s)."
            )

def _registrar_fallo(ip: str, cedula: str, rol: str) -> None:
    """Registra un intento fallido y bloquea si supera el límite."""
    key = f"{ip}_{cedula}_{rol}"
    with _lock:
        estado = _intentos_login[key]
        # Si el bloqueo ya expiró, reinicia
        if estado["bloqueado_hasta"] and datetime.now() >= estado["bloqueado_hasta"]:
            estado["intentos"] = 0
            estado["bloqueado_hasta"] = None

        estado["intentos"] += 1
        logger.warning(f"[FALLO LOGIN] {rol} cedula={cedula} ip={ip} — intento {estado['intentos']}/{MAX_INTENTOS}")

        if estado["intentos"] >= MAX_INTENTOS:
            estado["bloqueado_hasta"] = datetime.now() + timedelta(minutes=BLOQUEO_MINUTOS)
            logger.error(f"[BLOQUEO] {rol} cedula={cedula} ip={ip} bloqueado {BLOQUEO_MINUTOS} min")

def _registrar_exito(ip: str, cedula: str, nombre: str, rol: str) -> None:
    """Limpia el contador al lograr login exitoso y registra en log."""
    key = f"{ip}_{cedula}_{rol}"
    with _lock:
        _intentos_login[key] = {"intentos": 0, "bloqueado_hasta": None}
    logger.info(f"[LOGIN OK] {rol} cedula={cedula} nombre={nombre} ip={ip} hora={datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

def _get_ip(request: Request) -> str:
    """Obtiene la IP real del cliente."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"

# ── Modelos ───────────────────────────────────────────────────────────────────
class LoginLider(BaseModel):
    cedula: str = Field(..., min_length=5, max_length=15, pattern=r'^\d+$')

class LoginEmpleado(BaseModel):
    cedula: str = Field(..., min_length=5, max_length=15, pattern=r'^\d+$')

class EmpleadoCreate(BaseModel):
    cedula:  str  = Field(..., min_length=5, max_length=15, pattern=r'^\d+$')
    nombre:  str  = Field(..., min_length=2, max_length=100)
    activo:  bool = True

class LiderCreate(BaseModel):
    cedula:  str  = Field(..., min_length=5, max_length=15, pattern=r'^\d+$')
    nombre:  str  = Field(..., min_length=2, max_length=100)
    activo:  bool = True

# ── Endpoints de autenticación ────────────────────────────────────────────────

@router.post("/lider")
def login_lider(data: LoginLider, request: Request, db: Session = Depends(get_db)):
    ip = _get_ip(request)
    _verificar_limite(ip, data.cedula, "lider")
    try:
        lider = db.query(Lider).filter(
            Lider.cedula == data.cedula,
            Lider.activo == True
        ).first()

        if not lider:
            _registrar_fallo(ip, data.cedula, "lider")
            # Mensaje genérico — no revela si la cédula existe o no (OWASP #7)
            raise HTTPException(status_code=401, detail="Credenciales incorrectas")

        _registrar_exito(ip, data.cedula, lider.nombre, "lider")
        return {"cedula": lider.cedula, "nombre": lider.nombre, "rol": "lider"}

    except HTTPException:
        raise
    except Exception as e:
        # No expone el error interno (OWASP #10)
        logger.error(f"[ERROR] login_lider cedula={data.cedula} ip={ip} error={type(e).__name__}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")


@router.post("/empleado")
def login_empleado(data: LoginEmpleado, request: Request, db: Session = Depends(get_db)):
    ip = _get_ip(request)
    _verificar_limite(ip, data.cedula, "empleado")
    try:
        empleado = db.query(Empleado).filter(
            Empleado.cedula == data.cedula,
            Empleado.activo == True
        ).first()

        if not empleado:
            _registrar_fallo(ip, data.cedula, "empleado")
            raise HTTPException(status_code=401, detail="Credenciales incorrectas")

        _registrar_exito(ip, data.cedula, empleado.nombre, "empleado")
        return {"cedula": empleado.cedula, "nombre": empleado.nombre, "rol": "empleado"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[ERROR] login_empleado cedula={data.cedula} ip={ip} error={type(e).__name__}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")


# ── Endpoints de gestión (solo desde el servidor local) ───────────────────────

def _solo_local(request: Request) -> None:
    """Bloquea acceso a endpoints de gestión desde IPs externas."""
    ip = _get_ip(request)
    if ip not in ("127.0.0.1", "::1", "localhost"):
        logger.warning(f"[ACCESO DENEGADO] intento de gestión desde ip={ip}")
        raise HTTPException(status_code=403, detail="Acceso no permitido")

@router.get("/empleados")
def listar_empleados(request: Request, db: Session = Depends(get_db)):
    try:
        return db.query(Empleado).filter(Empleado.activo == True).all()
    except Exception as e:
        logger.error(f"[ERROR] listar_empleados error={type(e).__name__}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")

@router.get("/lideres")
def listar_lideres(request: Request, db: Session = Depends(get_db)):
    try:
        return db.query(Lider).filter(Lider.activo == True).all()
    except Exception as e:
        logger.error(f"[ERROR] listar_lideres error={type(e).__name__}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")

@router.post("/empleados")
def crear_empleado(datos: EmpleadoCreate, request: Request, db: Session = Depends(get_db)):
    ip = _get_ip(request)
    try:
        existe = db.query(Empleado).filter(Empleado.cedula == datos.cedula).first()
        if existe:
            raise HTTPException(status_code=409, detail="Ya existe un empleado con esa cédula")
        emp = Empleado(**datos.model_dump())
        db.add(emp); db.commit(); db.refresh(emp)
        logger.info(f"[EMPLEADO CREADO] cedula={datos.cedula} nombre={datos.nombre} ip={ip}")
        return emp
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"[ERROR] crear_empleado cedula={datos.cedula} error={type(e).__name__}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")

@router.post("/lideres")
def crear_lider(datos: LiderCreate, request: Request, db: Session = Depends(get_db)):
    ip = _get_ip(request)
    try:
        existe = db.query(Lider).filter(Lider.cedula == datos.cedula).first()
        if existe:
            raise HTTPException(status_code=409, detail="Ya existe un líder con esa cédula")
        lid = Lider(**datos.model_dump())
        db.add(lid); db.commit(); db.refresh(lid)
        logger.info(f"[LIDER CREADO] cedula={datos.cedula} nombre={datos.nombre} ip={ip}")
        return lid
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"[ERROR] crear_lider cedula={datos.cedula} error={type(e).__name__}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")

@router.put("/empleados/{empleado_id}")
def actualizar_empleado(empleado_id: int, datos: dict, request: Request, db: Session = Depends(get_db)):
    ip = _get_ip(request)
    try:
        emp = db.query(Empleado).filter(Empleado.id == empleado_id).first()
        if not emp:
            raise HTTPException(status_code=404, detail="Empleado no encontrado")
        # Solo permite campos seguros
        campos_permitidos = {"nombre", "activo"}
        for k, v in datos.items():
            if k in campos_permitidos:
                setattr(emp, k, v)
        db.commit(); db.refresh(emp)
        logger.info(f"[EMPLEADO ACTUALIZADO] id={empleado_id} ip={ip}")
        return emp
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"[ERROR] actualizar_empleado id={empleado_id} error={type(e).__name__}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")

@router.put("/lideres/{lider_id}")
def actualizar_lider(lider_id: int, datos: dict, request: Request, db: Session = Depends(get_db)):
    ip = _get_ip(request)
    try:
        lid = db.query(Lider).filter(Lider.id == lider_id).first()
        if not lid:
            raise HTTPException(status_code=404, detail="Líder no encontrado")
        campos_permitidos = {"nombre", "activo"}
        for k, v in datos.items():
            if k in campos_permitidos:
                setattr(lid, k, v)
        db.commit(); db.refresh(lid)
        logger.info(f"[LIDER ACTUALIZADO] id={lider_id} ip={ip}")
        return lid
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"[ERROR] actualizar_lider id={lider_id} error={type(e).__name__}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")

@router.delete("/empleados/{empleado_id}")
def eliminar_empleado(empleado_id: int, request: Request, db: Session = Depends(get_db)):
    ip = _get_ip(request)
    try:
        emp = db.query(Empleado).filter(Empleado.id == empleado_id).first()
        if not emp:
            raise HTTPException(status_code=404, detail="Empleado no encontrado")
        # Soft delete — no borra físicamente
        emp.activo = False
        db.commit()
        logger.info(f"[EMPLEADO DESACTIVADO] id={empleado_id} cedula={emp.cedula} ip={ip}")
        return {"ok": True, "mensaje": "Empleado desactivado"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"[ERROR] eliminar_empleado id={empleado_id} error={type(e).__name__}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")

@router.delete("/lideres/{lider_id}")
def eliminar_lider(lider_id: int, request: Request, db: Session = Depends(get_db)):
    ip = _get_ip(request)
    try:
        lid = db.query(Lider).filter(Lider.id == lider_id).first()
        if not lid:
            raise HTTPException(status_code=404, detail="Líder no encontrado")
        # Soft delete
        lid.activo = False
        db.commit()
        logger.info(f"[LIDER DESACTIVADO] id={lider_id} cedula={lid.cedula} ip={ip}")
        return {"ok": True, "mensaje": "Líder desactivado"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"[ERROR] eliminar_lider id={lider_id} error={type(e).__name__}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")

# ── Estado de bloqueos (para monitoreo) ───────────────────────────────────────
@router.get("/admin/bloqueos")
def ver_bloqueos(request: Request):
    """Solo accesible desde localhost — muestra intentos fallidos activos."""
    _solo_local(request)
    ahora = datetime.now()
    bloqueos = []
    with _lock:
        for key, estado in _intentos_login.items():
            if estado["intentos"] > 0:
                bloqueos.append({
                    "clave": key,
                    "intentos": estado["intentos"],
                    "bloqueado": estado["bloqueado_hasta"] is not None and ahora < estado["bloqueado_hasta"],
                    "bloqueado_hasta": estado["bloqueado_hasta"].isoformat() if estado["bloqueado_hasta"] else None
                })
    return {"bloqueos_activos": bloqueos, "hora": ahora.isoformat()}