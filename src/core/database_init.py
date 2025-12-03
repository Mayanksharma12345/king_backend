"""
Database initialization script - creates all tables for fresh setup
Run once to initialize the database with required tables.
"""

from src.core.database import engine
from src.models.base import Base
from src.models import base, medical, user
import structlog

logger = structlog.get_logger(__name__)


def init_database():
    """Initialize database - create all tables"""
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
        
        # Insert sample ICD-10 codes
        from sqlalchemy.orm import Session
        db = Session(engine)
        
        try:
            from src.models.medical import ICD10Code, CPTCode
            
            # Check if already populated
            existing = db.query(ICD10Code).first()
            if not existing:
                sample_codes = [
                    ("I10", "Essential hypertension", "Cardiovascular"),
                    ("E11.9", "Type 2 diabetes mellitus without complications", "Endocrine"),
                    ("E78.5", "Hyperlipidemia, unspecified", "Metabolic"),
                    ("J06.9", "Acute upper respiratory infection, unspecified", "Respiratory"),
                    ("M54.5", "Low back pain", "Musculoskeletal"),
                    ("F41.1", "Generalized anxiety disorder", "Psychiatric"),
                    ("E66.9", "Obesity, unspecified", "Metabolic"),
                    ("M79.3", "Panniculitis, unspecified", "Musculoskeletal"),
                ]
                
                for code, desc, category in sample_codes:
                    db.add(ICD10Code(
                        code=code,
                        description=desc,
                        category=category,
                        is_billable=True
                    ))
                
                db.commit()
                logger.info("Sample ICD-10 codes inserted")
            
            # Insert sample CPT codes
            existing_cpt = db.query(CPTCode).first()
            if not existing_cpt:
                sample_cpts = [
                    ("99213", "Office visit - Established patient, low complexity", "Office Visit"),
                    ("99214", "Office visit - Established patient, moderate complexity", "Office Visit"),
                    ("99204", "Office visit - New patient, moderate complexity", "Office Visit"),
                    ("99205", "Office visit - New patient, high complexity", "Office Visit"),
                ]
                
                for code, desc, category in sample_cpts:
                    db.add(CPTCode(
                        code=code,
                        description=desc,
                        category=category
                    ))
                
                db.commit()
                logger.info("Sample CPT codes inserted")
        
        finally:
            db.close()
            
    except Exception as e:
        logger.error("Failed to initialize database", error=str(e))
        raise


if __name__ == "__main__":
    init_database()
    print("Database initialized successfully!")
