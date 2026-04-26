from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql://postgres:inverfarma2026@localhost:5432/produccion_db"
    SECRET_KEY: str = "clave_secreta_cambiar_en_produccion"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480

settings = Settings()
