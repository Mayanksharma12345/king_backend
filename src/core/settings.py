"""
Application Configuration

Centralized configuration management using Pydantic settings.
Supports environment variables and .env files.
"""

from functools import lru_cache
from typing import List, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings"""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True
    )
    
    # Application
    APP_NAME: str = "medical-scribe-ai"
    APP_ENV: str = Field(default="development", pattern="^(development|staging|production)$")
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"
    
    # API
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    API_PREFIX: str = "/api/v1"
    
    # OpenAI Configuration (alternative to Azure)
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-4o"
    OPENAI_WHISPER_MODEL: str = "whisper-1"
    USE_OPENAI: bool = False
    
    # Azure OpenAI (Required if USE_OPENAI is False)
    LLM_PROVIDER: str = "azure_openai"
    AZURE_OPENAI_ENDPOINT: str
    AZURE_OPENAI_API_KEY: str
    AZURE_OPENAI_DEPLOYMENT_NAME: str
    AZURE_OPENAI_API_VERSION: str
    AZURE_WHISPER_DEPLOYMENT_NAME: str
    AZURE_OPENAI_API_VERSION_2: str
    
    # Supports both SQLite (local dev) and Azure SQL (production)
    # Azure SQL format: mssql+pyodbc://user:pass@server.database.windows.net:1433/db?driver=...
    DATABASE_URL: str = Field(
        default="sqlite:///./medicalscribe.db",
        description="Database connection string - supports SQLite, PostgreSQL, and Azure SQL Server"
    )
    DATABASE_POOL_SIZE: int = 5
    DATABASE_MAX_OVERFLOW: int = 10
    
    # Security
    SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # HIPAA Compliance
    AUDIT_LOG_ENABLED: bool = False
    AUDIT_LOG_RETENTION_DAYS: int = 365
    PHI_ENCRYPTION_ENABLED: bool = False
    
    # CORS
    CORS_ORIGINS: List[str] = Field(default_factory=lambda: ["http://localhost:3000"])
    CORS_ALLOW_CREDENTIALS: bool = True
    
    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        """Parse CORS origins from comma-separated string or list"""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v
    
    # Rate Limiting
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_PERIOD: int = 60
    
    # Feature Flags
    ENABLE_REAL_TIME_TRANSCRIPTION: bool = True
    ENABLE_ICD10_SUGGESTIONS: bool = True
    ENABLE_SOAP_GENERATION: bool = True
    
    # Medical NLP Models
    SPACY_MODEL: str = "en_core_sci_lg"
    MEDCAT_MODEL_PATH: Optional[str] = "./models/medcat"
    
    # Audio Processing
    MAX_AUDIO_FILE_SIZE_MB: int = 100
    SUPPORTED_AUDIO_FORMATS: List[str] = Field(
        default_factory=lambda: ["wav", "mp3", "m4a", "flac"]
    )
    
    @field_validator("SUPPORTED_AUDIO_FORMATS", mode="before")
    @classmethod
    def parse_audio_formats(cls, v):
        """Parse audio formats from comma-separated string or list"""
        if isinstance(v, str):
            return [fmt.strip() for fmt in v.split(",")]
        return v
    
    # Storage
    STORAGE_TYPE: str = "local"
    LOCAL_STORAGE_PATH: str = "./data/uploads"
    RECORDINGS_FOLDER: str = "./data/recordings"
    
    # Logging
    LOG_FORMAT: str = "json"
    LOG_FILE_PATH: str = "./logs/app.log"
    LOG_ROTATION: str = "1 day"
    LOG_RETENTION: str = "30 days"
    
    def is_production(self) -> bool:
        """Check if running in production environment"""
        return self.APP_ENV == "production"
    
    def is_development(self) -> bool:
        """Check if running in development environment"""
        return self.APP_ENV == "development"


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance.
    
    Uses LRU cache to avoid re-reading environment variables.
    """
    return Settings()
