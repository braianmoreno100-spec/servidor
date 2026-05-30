from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
import socketio
import os
import time
import logging
import logging.handlers
from collections import defaultdict
from .database import engine, Base
from .socket_manager import sio, get_sio
from .routers import auth, ordenes, produccion, excel_export, catalogos, reporte_pptx

Base.metadata.create_all(bind=engine)

# ── Configuración de logs ─────────────────────────────────────────────────────
# Los logs se guardan en la carpeta 'logs' junto al ejecutable
LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "kore.log")

# Formato del log: fecha hora | nivel | módulo | mensaje
LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s"
LOG_DATE   = "%Y-%m-%d %H:%M:%S"

# Rotación automática: máximo 5MB por archivo, guarda los últimos 10 archivos
file_handler = logging.handlers.RotatingFileHandler(
    LOG_FILE, maxBytes=5*1024*1024, backupCount=10, encoding="utf-8"
)
file_handler.setFormatter(logging.Formatter(LOG_FORMAT, LOG_DATE))
file_handler.setLevel(logging.INFO)

# Logger raíz — captura todos los loggers de la app
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)
root_logger.addHandler(file_handler)

# Logger específico de Kore
logger = logging.getLogger("kore.main")
logger.info("=" * 60)
logger.info("KORE SISTEM — Servidor iniciando")
logger.info(f"Archivo de log: {LOG_FILE}")
logger.info("=" * 60)

app = FastAPI(title="Sistema de Control de Producción")

# ── CORS ──────────────────────────────────────────────────────────────────────
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*").split(",")

if ALLOWED_ORIGINS == ["*"]:
    cors_origins = ["*"]
else:
    cors_origins = [o.strip() for o in ALLOWED_ORIGINS]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Rate Limiting ─────────────────────────────────────────────────────────────
RATE_LIMIT     = int(os.getenv("RATE_LIMIT", "300"))
RATE_WINDOW    = int(os.getenv("RATE_WINDOW", "60"))
RATE_WHITELIST = os.getenv("RATE_WHITELIST", "127.0.0.1").split(",")

_rate_store: dict = defaultdict(list)

def _get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"

def _check_rate_limit(ip: str) -> bool:
    if ip in RATE_WHITELIST:
        return True
    now = time.time()
    window_start = now - RATE_WINDOW
    _rate_store[ip] = [t for t in _rate_store[ip] if t > window_start]
    if len(_rate_store[ip]) >= RATE_LIMIT:
        logger.warning(f"[RATE LIMIT] IP bloqueada temporalmente: {ip}")
        return False
    _rate_store[ip].append(now)
    return True

@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    if request.url.path in ["/health", "/favicon.ico", "/favicon.svg"]:
        return await call_next(request)
    if request.url.path.startswith("/assets"):
        return await call_next(request)

    ip = _get_client_ip(request)
    if not _check_rate_limit(ip):
        return JSONResponse(
            status_code=429,
            content={"detail": f"Demasiadas solicitudes. Límite: {RATE_LIMIT} req/{RATE_WINDOW}s"}
        )
    return await call_next(request)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(auth.router,         prefix="/auth",       tags=["auth"])
app.include_router(ordenes.router,      prefix="/ordenes",    tags=["ordenes"])
app.include_router(produccion.router,   prefix="/produccion", tags=["produccion"])
app.include_router(excel_export.router, prefix="/reportes",   tags=["reportes"])
app.include_router(catalogos.router,    prefix="/catalogos",  tags=["catalogos"])
app.include_router(reporte_pptx.router, prefix="/reportes",   tags=["reporte-pptx"])

# ── Health check ──────────────────────────────────────────────────────────────
@app.get("/health")
def health():
    return {"status": "ok"}

# ── Socket.IO ─────────────────────────────────────────────────────────────────
socket_app = socketio.ASGIApp(sio, app)

@sio.event
async def connect(sid, environ):
    logger.info(f"[SOCKET] Cliente conectado: {sid}")

@sio.event
async def disconnect(sid):
    logger.info(f"[SOCKET] Cliente desconectado: {sid}")

@sio.event
async def unirse_orden(sid, data):
    orden_id = data.get("orden_id")
    await sio.enter_room(sid, f"orden_{orden_id}")
    logger.info(f"[SOCKET] Cliente {sid} unido a orden_{orden_id}")

# ── Archivos estáticos (dashboard React) ──────────────────────────────────────
STATIC_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")

if os.path.exists(STATIC_DIR):
    assets_dir = os.path.join(STATIC_DIR, "assets")
    if os.path.exists(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/favicon.ico")
    async def favicon():
        f = os.path.join(STATIC_DIR, "favicon.ico")
        return FileResponse(f) if os.path.exists(f) else FileResponse(os.path.join(STATIC_DIR, "favicon.svg"))

    @app.get("/favicon.svg")
    async def favicon_svg():
        return FileResponse(os.path.join(STATIC_DIR, "favicon.svg"))

    @app.get("/logo_inverfarma.png")
    async def logo():
        return FileResponse(os.path.join(STATIC_DIR, "logo_inverfarma.png"))

    @app.get("/kore_icon.png")
    async def kore_icon():
        f = os.path.join(STATIC_DIR, "kore_icon.png")
        return FileResponse(f) if os.path.exists(f) else FileResponse(os.path.join(STATIC_DIR, "logo_inverfarma.png"))

    @app.get("/")
    async def serve_root():
        return FileResponse(os.path.join(STATIC_DIR, "index.html"))

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        return FileResponse(os.path.join(STATIC_DIR, "index.html"))