from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    PROJECT_NAME: str = "Personal Budget Analyzer"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"

    # Database
    DATABASE_URL: str = "postgresql://postgres:postgres@db:5432/budget_analyzer"

    # Redis
    REDIS_URL: str = "redis://redis:6379/0"

    # Security
    SECRET_KEY: str = "your-secret-key-change-this-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    PASSWORD_RESET_TOKEN_EXPIRE_MINUTES: int = 30
    FIRST_SUPERUSER_EMAIL: str = "admin@example.com"
    FIRST_SUPERUSER_PASSWORD: str = "admin123"
    FIRST_SUPERUSER_USERNAME: str = "admin"
    FIRST_SUPERUSER_FULL_NAME: Optional[str] = "Administrator"

    # CORS
    BACKEND_CORS_ORIGINS: list = ["http://localhost:5173", "http://localhost:3000"]

    # Frontend
    FRONTEND_URL: str = "http://localhost:5173"
    PASSWORD_RESET_PATH: str = "/reset-password"

    # Email (Resend SMTP)
    MAIL_FROM: Optional[str] = None
    MAIL_FROM_NAME: Optional[str] = None
    MAIL_USERNAME: Optional[str] = None
    MAIL_PASSWORD: Optional[str] = None
    MAIL_SERVER: str = "smtp.resend.com"
    MAIL_PORT: int = 465
    MAIL_STARTTLS: bool = False
    MAIL_SSL_TLS: bool = True
    MAIL_TIMEOUT: int = 30

    # Optional External APIs
    PLAID_CLIENT_ID: Optional[str] = None
    PLAID_SECRET: Optional[str] = None
    PLAID_ENV: str = "sandbox"

    GOOGLE_CLOUD_VISION_API_KEY: Optional[str] = None

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
