from pydantic import field_validator
from pydantic_settings import BaseSettings
from typing import List
from typing import Optional
from sqlalchemy.engine import URL
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

class Settings(BaseSettings):
    DB_HOST: str = "localhost"
    DB_PORT: int = 3306
    DB_NAME: str = "customer_support_db"
    DB_USER: str = "root"
    DB_PASSWORD: str = ""
    DATABASE_URL: Optional[str] = None

    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    ALLOW_FIRST_USER_ADMIN: bool = False

    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000"

    @field_validator("SECRET_KEY")
    @classmethod
    def validate_secret_key(cls, value: str) -> str:
        if len(value) < 32 or value.startswith("Generate-a-local-"):
            raise ValueError("SECRET_KEY must be a local random secret of at least 32 characters")
        return value

    @field_validator("ALGORITHM")
    @classmethod
    def validate_jwt_algorithm(cls, value: str) -> str:
        if value != "HS256":
            raise ValueError("Only the explicitly configured HS256 JWT algorithm is supported")
        return value

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",")]

    @property
    def database_url(self) -> str:
        if self.DATABASE_URL:
            return self.DATABASE_URL
        return URL.create(
            "mysql+pymysql",
            username=self.DB_USER,
            password=self.DB_PASSWORD,
            host=self.DB_HOST,
            port=self.DB_PORT,
            database=self.DB_NAME,
        ).render_as_string(hide_password=False)

    model_config = {
        "env_file": PROJECT_ROOT / ".env",
        "extra": "ignore",
    }


settings = Settings()
