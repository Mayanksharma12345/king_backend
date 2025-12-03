"""SOAP note generation endpoints"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from uuid import uuid4
from datetime import datetime
import json

from src.core.database import get_db
from src.models.medical import SOAPNote, Encounter
from src.services.soap_service import SOAPService

router = APIRouter()

soap_service = SOAPService()


class SOAPGenerationRequest(BaseModel):
    """SOAP note generation request"""
    encounter_id: str = Field(..., description="Encounter ID")
    transcription: str = Field(..., description="Transcription text")
    chief_complaint: str = Field(default="", description="Chief complaint (optional)")


class SOAPNoteResponse(BaseModel):
    """SOAP note response"""
    id: str
    subjective: str
    objective: str
    assessment: str
    plan: str
    icd10_codes: list
    cpt_codes: list
    completeness_score: float
    
    class Config:
        from_attributes = True


@router.post("/generate", response_model=SOAPNoteResponse)
async def generate_soap_note(
    request: SOAPGenerationRequest,
    db: Session = Depends(get_db)
):
    """
    Generate SOAP note from transcription using Azure OpenAI GPT-4.
    
    Args:
        request: SOAPGenerationRequest with encounter_id and transcription
        db: Database session
        
    Returns:
        Generated SOAP note with medical codes
        
    Raises:
        HTTPException: 400 if validation fails, 404 if encounter not found
    """
    
    if not request.encounter_id or not request.encounter_id.strip():
        raise HTTPException(
            status_code=400,
            detail="Encounter ID is required"
        )
    
    if not request.transcription or not request.transcription.strip():
        raise HTTPException(
            status_code=400,
            detail="Transcription text is required"
        )
    
    # Verify encounter exists
    try:
        encounter = db.query(Encounter).filter(
            Encounter.id == request.encounter_id
        ).first()
        
        if not encounter:
            raise HTTPException(
                status_code=404,
                detail=f"Encounter '{request.encounter_id}' not found"
            )
    except Exception as e:
        if isinstance(e, HTTPException):
            raise
        raise HTTPException(
            status_code=500,
            detail=f"Database error: {str(e)}"
        )
    
    try:
        # Generate SOAP note using Azure OpenAI GPT-4
        soap_data = await soap_service.generate_soap_note(
            transcription=request.transcription,
            chief_complaint=request.chief_complaint or encounter.chief_complaint or "General consultation"
        )
        
        # Calculate completeness score based on content quality
        completeness = 0
        if soap_data.get("subjective"): completeness += 25
        if soap_data.get("objective"): completeness += 25
        if soap_data.get("assessment"): completeness += 25
        if soap_data.get("plan"): completeness += 25
        
        # Create SOAP note in database
        soap = SOAPNote(
            id=f"soap_{uuid4().hex[:12]}",
            encounter_id=request.encounter_id,
            subjective=soap_data.get("subjective", ""),
            objective=soap_data.get("objective", ""),
            assessment=soap_data.get("assessment", ""),
            plan=soap_data.get("plan", ""),
            icd10_codes=json.dumps(soap_data.get("icd10_codes", [])),
            cpt_codes=json.dumps(soap_data.get("cpt_codes", [])),
            generated_by="azure-gpt-4" if not soap_service.use_openai else "openai-gpt-4",
            completeness_score=float(completeness)
        )
        
        db.add(soap)
        db.commit()
        db.refresh(soap)
        
        return soap
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate SOAP note: {str(e)}"
        )


@router.get("/{soap_id}", response_model=SOAPNoteResponse)
async def get_soap_note(
    soap_id: str,
    db: Session = Depends(get_db)
):
    """
    Get SOAP note by ID.
    
    Args:
        soap_id: SOAP note ID
        db: Database session
        
    Returns:
        SOAP note details
        
    Raises:
        HTTPException: 404 if not found
    """
    
    if not soap_id or not soap_id.strip():
        raise HTTPException(
            status_code=400,
            detail="SOAP note ID is required"
        )
    
    soap = db.query(SOAPNote).filter(SOAPNote.id == soap_id).first()
    if not soap:
        raise HTTPException(
            status_code=404,
            detail=f"SOAP note '{soap_id}' not found"
        )
    
    return soap
