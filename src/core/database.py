"""
Database Configuration and Connection Management

Supports:
- SQLite (development)
- Azure SQL Server with pyodbc (production)
"""

from typing import Generator
from sqlalchemy import create_engine, event, Engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool, NullPool
import structlog

from src.core.config import get_settings

logger = structlog.get_logger(__name__)

settings = get_settings()

# Determine database type
is_sql_server = settings.DATABASE_URL.startswith('mssql')

if is_sql_server:
    # Check if using pyodbc or pymssql
    use_pyodbc = 'pyodbc' in settings.DATABASE_URL
    
    connect_args = {}
    if use_pyodbc:
        # pyodbc with ODBC Driver 18 for SQL Server
        connect_args = {
            "timeout": 30
        }
    else:
        # pymssql settings (fallback)
        connect_args = {
            "tds_version": "7.4",
            "charset": "UTF-8"
        }
    
    # Azure SQL Server configuration
    engine = create_engine(
        settings.DATABASE_URL,
        pool_size=settings.DATABASE_POOL_SIZE,
        max_overflow=settings.DATABASE_MAX_OVERFLOW,
        echo=settings.DEBUG,
        poolclass=NullPool if settings.APP_ENV == "testing" else None,
        pool_pre_ping=True,  # Verify connections before using them
        connect_args=connect_args
    )
    driver_info = "pyodbc (ODBC Driver 18)" if use_pyodbc else "pymssql (no ODBC driver)"
    logger.info(f"Connected to Azure SQL Server database using {driver_info}")
else:
    # SQLite configuration (development)
    engine = create_engine(
        settings.DATABASE_URL,
        pool_size=settings.DATABASE_POOL_SIZE,
        max_overflow=settings.DATABASE_MAX_OVERFLOW,
        echo=settings.DEBUG,
        poolclass=StaticPool if settings.APP_ENV == "testing" else None,
        connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {}
    )
    
    # Enable foreign key constraints for SQLite
    @event.listens_for(Engine, "connect")
    def set_sqlite_pragma(dbapi_conn, connection_record):
        if not is_sql_server:
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()
    
    logger.info("Connected to SQLite database")

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """
    Database session dependency for FastAPI.
    
    Usage:
        @app.get("/items/")
        def read_items(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize database with all models"""
    from src.models.base import Base
    
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created successfully")


def test_connection():
    """Test database connection"""
    try:
        with engine.connect() as conn:
            if is_sql_server:
                result = conn.execute(text("SELECT @@VERSION"))
                version = result.fetchone()[0]
                logger.info("Azure SQL Server connection successful", version=version[:50])
            else:
                result = conn.execute(text("SELECT sqlite_version()"))
                version = result.fetchone()[0]
                logger.info("SQLite connection successful", version=version)
        return True
    except Exception as e:
        logger.error("Database connection failed", error=str(e))
        return False
