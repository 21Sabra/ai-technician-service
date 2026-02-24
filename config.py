from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # API
    API_KEY: str
    API_PORT: int = 5000
    API_HOST: str = "0.0.0.0"

    # Environment
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    LOG_LEVEL: str = "DEBUG"

    # .NET Backend
    DOTNET_BACKEND_URL: Optional[str] = None

    # Scoring Weights
    WEIGHT_SPECIALIZATION: float = 0.40
    WEIGHT_PERFORMANCE: float = 0.30
    WEIGHT_RATING: float = 0.20
    WEIGHT_AVAILABILITY: float = 0.10

    model_config = {
        "env_file": ".env",
        "case_sensitive": False,
        "extra": "ignore"  # ✅ بيتجاهل أي variables زيادة في الـ .env
    }


settings = Settings()