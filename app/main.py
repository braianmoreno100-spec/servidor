from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import socketio
from .database import engine, Base
from .socket_manager import sio, get_sio
from .routers import auth, ordenes, produccion, excel_export, catalogos

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Sistema de Control de Producción")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(ordenes.router, prefix="/ordenes", tags=["ordenes"])
app.include_router(produccion.router, prefix="/produccion", tags=["produccion"])
app.include_router(excel_export.router, prefix="/reportes", tags=["reportes"])
app.include_router(catalogos.router, prefix="/catalogos", tags=["catalogos"])

socket_app = socketio.ASGIApp(sio, app)

@sio.event
async def connect(sid, environ):
    print(f"Cliente conectado: {sid}")

@sio.event
async def disconnect(sid):
    print(f"Cliente desconectado: {sid}")

@sio.event
async def unirse_orden(sid, data):
    orden_id = data.get("orden_id")
    await sio.enter_room(sid, f"orden_{orden_id}")
    print(f"Cliente {sid} unido a orden_{orden_id}")