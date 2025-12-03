"""
Medical Data Models

Core medical data structures for encounters, SOAP notes, and medical records.
"""

from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, Text, Boolean, Float, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
import enum

from src.models.base import Base, TimestampMixin


class EncounterType(str, enum.Enum):
    """Types of medical encounters"""
    OFFICE_VISIT = "office_visit"
    TELEHEALTH = "telehealth"
    FOLLOW_UP = "follow_up"
    CONSULTATION = "consultation"


class Encounter(Base, TimestampMixin):
    """Medical encounter record"""
    __tablename__ = "encounters"
    
    id = Column(String(50), primary_key=True)
    physician_id = Column(String(100), nullable=False, index=True)
    patient_id_hash = Column(String(64), nullable=False, index=True)  # Hashed for privacy
    
    encounter_type = Column(SQLEnum(EncounterType), default=EncounterType.OFFICE_VISIT)
    encounter_date = Column(DateTime, nullable=False, index=True)
    
    # Audio and transcription
    audio_file_path = Column(String(500), nullable=True)
    audio_duration_seconds = Column(Integer, nullable=True)
    transcription = Column(Text, nullable=True)
    transcription_confidence = Column(Float, nullable=True)
    
    # Chief complaint and diagnosis
    chief_complaint = Column(String(500), nullable=True)
    primary_diagnosis = Column(String(200), nullable=True)
    
    # Status
    is_complete = Column(Boolean, default=False)
    is_signed = Column(Boolean, default=False)
    signed_at = Column(DateTime, nullable=True)
    
    # Relationships
    soap_note = relationship("SOAPNote", back_populates="encounter", uselist=False, cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Encounter {self.id}>"


class SOAPNote(Base, TimestampMixin):
    """SOAP (Subjective, Objective, Assessment, Plan) note"""
    __tablename__ = "soap_notes"
    
    id = Column(String(50), primary_key=True)
    encounter_id = Column(String(50), ForeignKey("encounters.id"), nullable=False, index=True)
    
    # SOAP components
    subjective = Column(Text, nullable=True)
    objective = Column(Text, nullable=True)
    assessment = Column(Text, nullable=True)
    plan = Column(Text, nullable=True)
    
    # Medical codes
    icd10_codes = Column(Text, nullable=True)  # JSON array: ["I10", "E11.9"]
    cpt_codes = Column(Text, nullable=True)    # JSON array
    
    # Generation metadata
    generated_by = Column(String(50), default="gpt-4")  # AI model used
    generation_time_seconds = Column(Float, nullable=True)
    
    # Edit tracking
    edited = Column(Boolean, default=False)
    edited_at = Column(DateTime, nullable=True)
    edit_count = Column(Integer, default=0)
    
    # Quality metrics
    completeness_score = Column(Float, nullable=True)  # 0-100
    accuracy_score = Column(Float, nullable=True)
    
    # Relationships
    encounter = relationship("Encounter", back_populates="soap_note")
    
    def __repr__(self):
        return f"<SOAPNote {self.id}>"


class ICD10Code(Base):
    """ICD-10 diagnosis codes reference"""
    __tablename__ = "icd10_codes"
    
    code = Column(String(10), primary_key=True)
    description = Column(String(500), nullable=False)
    category = Column(String(100), nullable=True)
    is_billable = Column(Boolean, default=True)
    parent_code = Column(String(10), nullable=True)
    
    def __repr__(self):
        return f"<ICD10Code {self.code}>"


class CPTCode(Base):
    """CPT (Current Procedural Terminology) codes reference"""
    __tablename__ = "cpt_codes"
    
    code = Column(String(10), primary_key=True)
    description = Column(String(500), nullable=False)
    category = Column(String(100), nullable=True)
    typical_cost = Column(Float, nullable=True)
    
    def __repr__(self):
        return f"<CPTCode {self.code}>"
