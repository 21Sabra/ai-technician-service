from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    """Application settings"""
    
    # Database
    DB_DRIVER: str = "ODBC Driver 18 for SQL Server"
    DB_SERVER: str = "localhost"
    DB_PORT: int = 1433
    DB_NAME: str = "CarMaintenanceDB"
    DB_USER: str = "sa"
    DB_PASSWORD: str
    DB_TRUST_CERTIFICATE: str = "yes"
    
    # API
    API_KEY: str
    API_PORT: int = 5000
    API_HOST: str = "0.0.0.0"
    
    # Environment
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    
    # Logging
    LOG_LEVEL: str = "DEBUG"
    
    # Scoring Weights
    WEIGHT_SPECIALIZATION: float = 0.40
    WEIGHT_PERFORMANCE: float = 0.30
    WEIGHT_RATING: float = 0.20
    WEIGHT_AVAILABILITY: float = 0.10
    
    @property
    def database_url_pyodbc(self) -> str:
        """Get pyodbc connection string"""
        return (
            f"DRIVER={{{self.DB_DRIVER}}};"
            f"SERVER={self.DB_SERVER},{self.DB_PORT};"
            f"DATABASE={self.DB_NAME};"
            f"UID={self.DB_USER};"
            f"PWD={self.DB_PASSWORD};"
            f"TrustServerCertificate={self.DB_TRUST_CERTIFICATE};"
        )
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()