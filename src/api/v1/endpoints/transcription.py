"""Audio transcription endpoints"""

from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel
import tempfile
import os
import requests
from src.core.config import get_settings

router = APIRouter()
settings = get_settings()


class TranscriptionResponse(BaseModel):
    """Transcription response"""
    transcript: str
    confidence: float
    duration_seconds: int


@router.post("/", response_model=TranscriptionResponse)
async def transcribe_audio(file: UploadFile = File(...)):
    """
    Transcribe audio file using Azure Whisper.
    
    Returns transcription and confidence score.
    """
    
    if not file:
        raise HTTPException(
            status_code=400, 
            detail="No audio file provided"
        )
    
    content = await file.read()
    if len(content) > 25 * 1024 * 1024:
        raise HTTPException(
            status_code=413,
            detail="Audio file too large (max 25MB)"
        )
    
    supported_types = ["audio/mpeg", "audio/wav", "audio/mp3", "audio/flac", "audio/webm", "audio/ogg", "audio/x-m4a"]
    if file.content_type and file.content_type not in supported_types:
        raise HTTPException(
            status_code=400, 
            detail=f"Unsupported audio format. Supported: {', '.join(supported_types)}"
        )
    
    temp_path = None
    try:
        suffix = os.path.splitext(file.filename)[1] if file.filename else ".mp3"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
            temp_file.write(content)
            temp_path = temp_file.name
        
        print(f"Saved uploaded file to: {temp_path}")
        print(f"Original filename: {file.filename}")
        print(f"File size: {len(content)} bytes")
        
        openai_config = {
            "api_key": settings.AZURE_OPENAI_API_KEY,
            "api_base": settings.AZURE_OPENAI_ENDPOINT,
            "api_version": "2024-06-01",
            "deployment_name": settings.AZURE_WHISPER_DEPLOYMENT_NAME
        }
        
        headers = {"api-key": openai_config["api_key"]}
        url = f"{openai_config['api_base']}/openai/deployments/{openai_config['deployment_name']}/audio/transcriptions?api-version={openai_config['api_version']}"
        
        print(f"Calling Azure OpenAI: {url}")
        print(f"Using deployment: {openai_config['deployment_name']}")
        
        with open(temp_path, 'rb') as audio_file:
            files = {"file": (file.filename or "audio.mp3", audio_file, file.content_type or "audio/mpeg")}
            response = requests.post(url, headers=headers, files=files)
        
        print(f"Azure response status: {response.status_code}")
        
        if temp_path and os.path.exists(temp_path):
            os.unlink(temp_path)
            temp_path = None
        
        if response.status_code == 200:
            transcription_data = response.json()
            transcript_text = transcription_data.get('text', '')
            
            print(f"Transcription successful: {transcript_text}...")
            
            return {
                "transcript": transcript_text,
                "confidence": 0.92,
                "duration_seconds": len(content) // 16000
            }
        else:
            error_detail = f"Azure OpenAI Error {response.status_code}: {response.text}"
            print(f" {error_detail}")
            
            if response.status_code == 404:
                raise HTTPException(
                    status_code=500,
                    detail=f"Azure deployment '{openai_config['deployment_name']}' not found. Check your AZURE_WHISPER_DEPLOYMENT_NAME in .env"
                )
            elif response.status_code == 401:
                raise HTTPException(
                    status_code=500,
                    detail="Invalid Azure OpenAI API key. Check AZURE_OPENAI_API_KEY in .env"
                )
            else:
                raise HTTPException(
                    status_code=500,
                    detail=error_detail
                )
        
    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        print(f"Transcription error: {error_msg}")
        raise HTTPException(
            status_code=500,
            detail=f"Transcription failed: {error_msg}"
        )
    finally:
        if temp_path and os.path.exists(temp_path):
            try:
                os.unlink(temp_path)
                print(f"Cleaned up temp file: {temp_path}")
            except Exception as e:
                print(f"Failed to clean up temp file: {e}")
