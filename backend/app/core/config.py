from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    PROJECT_NAME: str = "Personal Budget Analyzer"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"

    DATABASE_URL: str = "postgresql://postgres:postgres@db:5432/budget_analyzer"

    BACKEND_CORS_ORIGINS: list = ["http://localhost:5173", "http://localhost:3000"]

    FIRST_SUPERUSER_EMAIL: str
    FIRST_SUPERUSER_PASSWORD: str
    FIRST_SUPERUSER_USERNAME: str
    FIRST_SUPERUSER_FULL_NAME: str | None = None

    COGNITO_USER_POOL_ID: str
    COGNITO_APP_CLIENT_ID: str
    COGNITO_REGION: str = "us-east-1"

    @property
    def COGNITO_JWKS_URL(self) -> str:
        return f"https://cognito-idp.{self.COGNITO_REGION}.amazonaws.com/{self.COGNITO_USER_POOL_ID}/.well-known/jwks.json"

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"


settings = Settings()
