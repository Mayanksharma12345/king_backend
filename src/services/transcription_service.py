import os
import tempfile
from typing import Optional
from src.core.config import get_settings

settings = get_settings()

class TranscriptionService:
    def __init__(self):
        if settings.USE_OPENAI and settings.OPENAI_API_KEY:
            from openai import OpenAI
            self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
            self.model = settings.OPENAI_WHISPER_MODEL
            self.use_openai = True
        else:
            from openai import AzureOpenAI
            self.client = AzureOpenAI(
                api_key=settings.AZURE_OPENAI_API_KEY,
                api_version=settings.AZURE_OPENAI_API_VERSION,
                azure_endpoint=settings.AZURE_OPENAI_ENDPOINT
            )
            self.model = settings.AZURE_WHISPER_DEPLOYMENT_NAME
            self.use_openai = False
    
    async def transcribe_audio(
        self,
        audio_file_path: str,
        language: Optional[str] = None
    ) -> dict:
        """
        Transcribe audio file using OpenAI or Azure OpenAI Whisper API
        """
        try:
            with open(audio_file_path, "rb") as audio_file:
                transcript = self.client.audio.transcriptions.create(
                    model=self.model,
                    file=audio_file,
                    language=language
                )
            
            return {
                "text": transcript.text,
                "language": language or "en",
                "confidence": 0.95
            }
        except Exception as e:
            raise Exception(f"Transcription failed: {str(e)}")
