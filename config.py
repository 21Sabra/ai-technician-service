from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    DB_SERVER: str
    DB_PORT: int = 1433
    DB_NAME: str
    DB_USER: str
    DB_PASSWORD: str
    DB_TRUST_CERTIFICATE: str = "yes"
    
    API_KEY: str
    API_PORT: int = 5000
    API_HOST: str = "0.0.0.0"
    
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    LOG_LEVEL: str = "DEBUG"
    
    DOTNET_BACKEND_URL: Optional[str] = None
    
    WEIGHT_SPECIALIZATION: float = 0.40
    WEIGHT_PERFORMANCE: float = 0.30
    WEIGHT_RATING: float = 0.20
    WEIGHT_AVAILABILITY: float = 0.10

    model_config = {"env_file": ".env", "case_sensitive": False}


settings = Settings()