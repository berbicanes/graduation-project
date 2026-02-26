from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://healthcare:healthcare_secret@localhost:5432/auth_db"
    JWT_SECRET: str = "change-me-to-a-random-secret-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    CORS_ORIGINS: list[str] = ["http://localhost:3000"]

    model_config = {"env_prefix": "", "env_file": ".env"}


settings = Settings()
