from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List
import json


PRODUCTION_FRONTEND_ORIGIN = "https://student-risk-intelligence-platform.vercel.app"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/student_risk_db"
    SECRET_KEY: str = "dev-secret-key-change-in-production-must-be-32-chars-long"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480
    ENVIRONMENT: str = "development"
    CORS_ORIGINS: str = json.dumps([
        "http://localhost:5173",
        "http://localhost:3000",
        PRODUCTION_FRONTEND_ORIGIN,
    ])

    @property
    def cors_origins_list(self) -> List[str]:
        """Return normalized origins suitable for FastAPI CORSMiddleware."""
        try:
            parsed = json.loads(self.CORS_ORIGINS)
            if isinstance(parsed, str):
                parsed = [parsed]
            if not isinstance(parsed, list):
                raise ValueError("CORS_ORIGINS must be a JSON list")
            origins = [str(origin).strip().rstrip("/") for origin in parsed if str(origin).strip()]
            return origins
        except (TypeError, ValueError, json.JSONDecodeError):
            # Also accept a comma-separated value in hosting dashboards.
            return [origin.strip().rstrip("/") for origin in self.CORS_ORIGINS.split(",") if origin.strip()]


settings = Settings()
