"""Encounter management endpoints"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
from uuid import uuid4
from pydantic import BaseModel
from typing import Optional

from src.core.database import get_db
from src.models.medical import Encounter, EncounterType, SOAPNote
import json
from src.services.soap_service import SOAPService

router = APIRouter()


class EncounterCreate(BaseModel):
    """Encounter creation schema"""
    physician_id: str
    patient_id_hash: str
    chief_complaint: str
    encounter_type: EncounterType = EncounterType.OFFICE_VISIT
    transcription: Optional[str] = None  # Added transcription field to receive actual transcribed text
    generate_soap: bool = False


class SOAPNoteDetail(BaseModel):
    """SOAP Note detail schema"""
    id: str
    subjective: Optional[str]
    objective: Optional[str]
    assessment: Optional[str]
    plan: Optional[str]
    icd10_codes: Optional[str]
    cpt_codes: Optional[str]
    generated_by: Optional[str]
    completeness_score: Optional[float]
    
    class Config:
        from_attributes = True


class EncounterResponse(BaseModel):
    """Encounter response schema"""
    id: str
    physician_id: str
    chief_complaint: str
    encounter_type: str
    transcription: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True


class EncounterDetailResponse(BaseModel):
    """Detailed encounter response with SOAP notes"""
    id: str
    physician_id: str
    patient_id_hash: str
    chief_complaint: str
    encounter_type: str
    encounter_date: datetime
    transcription: Optional[str]
    audio_duration_seconds: Optional[int]
    soap_note: Optional[dict]  # Return full SOAP note dict with ICD codes
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


@router.post("/", response_model=EncounterResponse)
async def create_encounter(
    encounter: EncounterCreate,
    db: Session = Depends(get_db)
):
    """Create a new encounter and optionally generate SOAP notes"""
    
    print(f"\n{'='*60}")
    print(f"[v0] CREATE ENCOUNTER REQUEST")
    print(f"{'='*60}")
    print(f"[v0] Physician ID: {encounter.physician_id}")
    print(f"[v0] Chief Complaint: {encounter.chief_complaint}")
    print(f"[v0] Transcription: {encounter.transcription[:100] if encounter.transcription else 'None'}...")
    print(f"[v0] Generate SOAP: {encounter.generate_soap}")
    print(f"{'='*60}\n")
    
    enc = Encounter(
        id=f"enc_{uuid4().hex[:12]}",
        physician_id=encounter.physician_id,
        patient_id_hash=encounter.patient_id_hash,
        chief_complaint=encounter.chief_complaint,
        encounter_type=encounter.encounter_type,
        encounter_date=datetime.utcnow(),
        transcription=encounter.transcription
    )
    
    db.add(enc)
    db.commit()
    db.refresh(enc)
    
    print(f"[v0] ✓ Encounter {enc.id} saved to database")
    print(f"[v0] Transcription saved: {len(enc.transcription) if enc.transcription else 0} chars")
    
    if encounter.generate_soap:
        if not encounter.transcription:
            print(f"[v0] ✗ SOAP generation skipped - no transcription provided")
        else:
            try:
                print(f"\n{'='*60}")
                print(f"[v0] STARTING SOAP GENERATION")
                print(f"{'='*60}")
                
                soap_service = SOAPService()
                print(f"[v0] SOAPService initialized")
                
                # Generate SOAP notes
                print(f"[v0] Calling Azure OpenAI for SOAP generation...")
                soap_data = await soap_service.generate_soap_note(
                    transcription=encounter.transcription,
                    chief_complaint=encounter.chief_complaint
                )
                
                print(f"\n[v0] ✓ SOAP generation completed successfully!")
                print(f"[v0] SOAP Data Structure:")
                print(f"  - Subjective: {len(soap_data.get('subjective', ''))} chars")
                print(f"  - Objective: {len(soap_data.get('objective', ''))} chars")
                print(f"  - Assessment: {len(soap_data.get('assessment', ''))} chars")
                print(f"  - Plan: {len(soap_data.get('plan', ''))} chars")
                print(f"  - ICD-10 Codes: {soap_data.get('icd10_codes', [])}")
                print(f"  - CPT Codes: {soap_data.get('cpt_codes', [])}")
                print(f"  - Completeness: {soap_data.get('completeness_score', 0):.2f}")
                
                # Create SOAP note record in database
                print(f"\n[v0] Creating SOAP note database record...")
                soap = SOAPNote(
                    id=f"soap_{uuid4().hex[:12]}",
                    encounter_id=enc.id,
                    subjective=soap_data.get("subjective"),
                    objective=soap_data.get("objective"),
                    assessment=soap_data.get("assessment"),
                    plan=soap_data.get("plan"),
                    icd10_codes=json.dumps(soap_data.get("icd10_codes", [])),
                    cpt_codes=json.dumps(soap_data.get("cpt_codes", [])),
                    generated_by="azure-gpt-4",
                    completeness_score=soap_data.get("completeness_score", 0.0)
                )
                
                db.add(soap)
                db.commit()
                db.refresh(soap)
                
                print(f"[v0] ✓ SOAP note {soap.id} saved to database!")
                print(f"{'='*60}\n")
                
            except Exception as e:
                print(f"\n{'='*60}")
                print(f"[v0] ✗✗✗ SOAP GENERATION ERROR ✗✗✗")
                print(f"{'='*60}")
                print(f"[v0] Error Type: {type(e).__name__}")
                print(f"[v0] Error Message: {str(e)}")
                print(f"\n[v0] Full Traceback:")
                import traceback
                traceback.print_exc()
                print(f"{'='*60}\n")
                # Don't fail the whole request if SOAP generation fails
    
    return enc


@router.get("/{encounter_id}", response_model=EncounterDetailResponse)
async def get_encounter(
    encounter_id: str,
    db: Session = Depends(get_db)
):
    """Get encounter details with SOAP notes and ICD codes"""
    
    encounter = db.query(Encounter).filter(Encounter.id == encounter_id).first()
    if not encounter:
        raise HTTPException(status_code=404, detail="Encounter not found")
    
    response_data = {
        "id": encounter.id,
        "physician_id": encounter.physician_id,
        "patient_id_hash": encounter.patient_id_hash,
        "chief_complaint": encounter.chief_complaint,
        "encounter_type": encounter.encounter_type.value,
        "encounter_date": encounter.encounter_date,
        "transcription": encounter.transcription,
        "audio_duration_seconds": encounter.audio_duration_seconds,
        "soap_note": None,
        "created_at": encounter.created_at,
        "updated_at": encounter.updated_at
    }
    
    if encounter.soap_note:
        response_data["soap_note"] = {
            "id": encounter.soap_note.id,
            "subjective": encounter.soap_note.subjective,
            "objective": encounter.soap_note.objective,
            "assessment": encounter.soap_note.assessment,
            "plan": encounter.soap_note.plan,
            "icd10_codes": encounter.soap_note.icd10_codes,
            "cpt_codes": encounter.soap_note.cpt_codes,
            "completeness_score": encounter.soap_note.completeness_score
        }
    
    return response_data


@router.get("/")
async def list_encounters(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """List encounters with pagination and SOAP note preview"""
    
    encounters = db.query(Encounter).order_by(
        Encounter.created_at.desc()
    ).offset(skip).limit(limit).all()
    
    total = db.query(Encounter).count()
    
    formatted_encounters = []
    for enc in encounters:
        enc_dict = {
            "id": enc.id,
            "physician_id": enc.physician_id,
            "chief_complaint": enc.chief_complaint,
            "encounter_type": enc.encounter_type.value,
            "created_at": enc.created_at,
            "soap_note": None
        }
        
        if enc.soap_note:
            enc_dict["soap_note"] = {
                "id": enc.soap_note.id,
                "icd10_codes": enc.soap_note.icd10_codes,
                "cpt_codes": enc.soap_note.cpt_codes
            }
        
        formatted_encounters.append(enc_dict)
    
    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "encounters": formatted_encounters
    }
