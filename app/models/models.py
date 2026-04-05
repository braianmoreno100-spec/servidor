from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from ..database import Base

class Lider(Base):
    __tablename__ = "lideres"
    id = Column(Integer, primary_key=True, index=True)
    cedula = Column(String, unique=True, index=True)
    nombre = Column(String)
    activo = Column(Boolean, default=True)

class Empleado(Base):
    __tablename__ = "empleados"
    id = Column(Integer, primary_key=True, index=True)
    cedula = Column(String, unique=True, index=True)
    nombre = Column(String)
    activo = Column(Boolean, default=True)

class Producto(Base):
    __tablename__ = "productos"
    id = Column(Integer, primary_key=True, index=True)
    codigo = Column(String, unique=True, index=True)
    descripcion = Column(String)
    material = Column(String)
    ciclos = Column(Float)
    cavidades = Column(Integer)
    activo = Column(Boolean, default=True)

class Orden(Base):
    __tablename__ = "ordenes"
    id = Column(Integer, primary_key=True, index=True)
    numero_orden = Column(String, index=True)
    codigo_producto = Column(String)
    descripcion_producto = Column(String)
    cantidad_producir = Column(Integer)
    material = Column(String)
    tipo_maquina = Column(String)
    numero_maquina = Column(String)
    cavidades = Column(Integer)
    ciclos = Column(Float)
    tiene_pigmento = Column(Boolean, default=False)
    numero_pigmento = Column(String, nullable=True)
    descripcion_pigmento = Column(String, nullable=True)
    cedula_lider = Column(String)
    nombre_lider = Column(String)
    fecha_creacion = Column(DateTime, default=datetime.utcnow)
    activa = Column(Boolean, default=True)
    turnos = relationship("Turno", back_populates="orden")

class Turno(Base):
    __tablename__ = "turnos"
    id = Column(Integer, primary_key=True, index=True)
    orden_id = Column(Integer, ForeignKey("ordenes.id"))
    cedula_empleado = Column(String)
    nombre_empleado = Column(String)
    fecha = Column(String)
    turno = Column(String)
    hora_inicio = Column(String)
    hora_fin = Column(String, nullable=True)
    orden = relationship("Orden", back_populates="turnos")
    registros_produccion = relationship("RegistroProduccion", back_populates="turno")
    paradas = relationship("Parada", back_populates="turno")
    desperdicios = relationship("Desperdicio", back_populates="turno")
    relevos = relationship("Relevo", back_populates="turno")

class RegistroProduccion(Base):
    __tablename__ = "registros_produccion"
    id = Column(Integer, primary_key=True, index=True)
    turno_id = Column(Integer, ForeignKey("turnos.id"))
    hora = Column(String)
    cantidad = Column(Integer)
    turno = relationship("Turno", back_populates="registros_produccion")

class Parada(Base):
    __tablename__ = "paradas"
    id = Column(Integer, primary_key=True, index=True)
    turno_id = Column(Integer, ForeignKey("turnos.id"))
    codigo = Column(Integer)
    descripcion = Column(String)
    minutos = Column(Integer)
    programada = Column(Boolean)
    turno = relationship("Turno", back_populates="paradas")

class Desperdicio(Base):
    __tablename__ = "desperdicios"
    id = Column(Integer, primary_key=True, index=True)
    turno_id = Column(Integer, ForeignKey("turnos.id"))
    codigo = Column(Integer)
    defecto = Column(String)
    cantidad = Column(Integer)
    turno = relationship("Turno", back_populates="desperdicios")

class Relevo(Base):
    __tablename__ = "relevos"
    id = Column(Integer, primary_key=True, index=True)
    turno_id = Column(Integer, ForeignKey("turnos.id"))
    cedula_empleado = Column(String)
    nombre_empleado = Column(String)
    hora_inicio = Column(String)
    hora_fin = Column(String, nullable=True)
    turno = relationship("Turno", back_populates="relevos")