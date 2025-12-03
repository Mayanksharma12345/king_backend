import json
import requests
import re
from typing import Dict, Any
from src.core.config import get_settings

settings = get_settings()

class SOAPService:
    def __init__(self):
        self.api_key = settings.AZURE_OPENAI_API_KEY
        self.model = settings.AZURE_OPENAI_DEPLOYMENT_NAME
        base_url = settings.AZURE_OPENAI_ENDPOINT.rstrip('/')
        self.api_version = settings.AZURE_OPENAI_API_VERSION_2
        self.endpoint = f"{base_url}/openai/deployments/{self.model}/chat/completions?api-version={self.api_version}"
        
        print(f"[v0] SOAPService initialized - Azure OpenAI only")
        print(f"[v0] - Base URL: {base_url}")
        print(f"[v0] - Deployment: {self.model}")
        print(f"[v0] - API Version: {self.api_version}")
    
    async def generate_soap_note(
        self,
        transcription: str,
        chief_complaint: str
    ) -> Dict[str, Any]:
        """
        Generate SOAP note with ICD-10 and CPT codes using Azure OpenAI
        """
        print(f"[v0] SOAPService: Starting generation with {len(transcription)} chars of transcription")
        print(f"[v0] SOAPService: Using model: {self.model}")
        print(f"[v0] SOAPService: Provider: Azure OpenAI")
        print(f"[v0] SOAPService: Endpoint: {self.endpoint}")
        
        try:
            prompt = f"""You are a medical documentation AI. Based on this patient encounter transcription, generate a comprehensive SOAP note.

Chief Complaint: {chief_complaint}

Transcription:
{transcription}

Generate a structured SOAP note with:
1. Subjective: Patient's symptoms, history, complaints
2. Objective: Physical exam findings, vital signs, test results  
3. Assessment: Diagnosis and medical evaluation
4. Plan: Treatment plan, medications, follow-up

Also provide:
- ICD-10 codes: List of diagnosis codes (as array)
- CPT codes: List of procedure codes (as array)

CRITICAL: Return ONLY raw JSON without any markdown formatting or code blocks. Do NOT use backticks or ```json.

Return in this exact format:
{{
  "subjective": "text here",
  "objective": "text here", 
  "assessment": "text here",
  "plan": "text here",
  "icd10_codes": ["K21.9", "R10.9"],
  "cpt_codes": ["99213", "99214"]
}}"""
            
            headers = {
                "Content-Type": "application/json",
                "api-key": self.api_key
            }
            
            payload = {
                "messages": [
                    {"role": "system", "content": "You are a medical documentation assistant that generates accurate SOAP notes with proper medical coding. Always return raw JSON without markdown formatting."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.3,
                "max_tokens": 2000
            }
            
            
            print(f"[v0] SOAPService: Calling Azure OpenAI API...")
            print(f"[v0] SOAPService: URL: {self.endpoint}")

            response = requests.post(
                self.endpoint,
                headers=headers,
                json=payload,
                timeout=60
            )
            
            print(f"[v0] SOAPService: Response status: {response.status_code}")
            
            if response.status_code != 200:
                error_detail = response.text
                print(f"[v0] SOAPService ERROR: API returned {response.status_code}")
                print(f"[v0] SOAPService ERROR: {error_detail}")
                raise Exception(f"API error {response.status_code}: {error_detail}")
            
            response_data = response.json()
            content = response_data["choices"][0]["message"]["content"].strip()
            print(f"[v0] SOAPService: Got response from API - length: {len(content)} chars")
            print(f"[v0] SOAPService: Raw content - first 300 chars: {content[:300]}")
            
            # Pattern matches: optional whitespace + backticks + optional "json" + newline + content + newline + backticks
            pattern = r'^\s*```(?:json)?\s*\n?(.*?)\n?\s*```\s*$'
            match = re.match(pattern, content, re.DOTALL | re.IGNORECASE)
            
            if match:
                content = match.group(1).strip()
                print(f"[v0] SOAPService: Stripped markdown code blocks using regex")
            else:
                print(f"[v0] SOAPService: No markdown code blocks detected, using content as-is")
            
            print(f"[v0] SOAPService: Cleaned content - length: {len(content)} chars")
            print(f"[v0] SOAPService: Cleaned content - first 200 chars: {content[:200]}")
            print(f"[v0] SOAPService: Cleaned content - last 200 chars: {content[-200:]}")
            
            try:
                soap_data = json.loads(content)
            except json.JSONDecodeError as e:
                print(f"[v0] SOAPService ERROR: Failed to parse JSON - {str(e)}")
                print(f"[v0] SOAPService ERROR: Full cleaned content:\n{content}")
                raise Exception(f"Failed to parse SOAP note JSON: {str(e)}")
            
            print(f"[v0] SOAPService: Successfully parsed JSON")
            
            sections_filled = sum([
                1 if soap_data.get("subjective") else 0,
                1 if soap_data.get("objective") else 0,
                1 if soap_data.get("assessment") else 0,
                1 if soap_data.get("plan") else 0,
                1 if soap_data.get("icd10_codes") else 0,
                1 if soap_data.get("cpt_codes") else 0
            ])
            completeness_score = (sections_filled / 6.0) * 100
            
            result = {
                "subjective": soap_data.get("subjective", ""),
                "objective": soap_data.get("objective", ""),
                "assessment": soap_data.get("assessment", ""),
                "plan": soap_data.get("plan", ""),
                "icd10_codes": soap_data.get("icd10_codes", []),
                "cpt_codes": soap_data.get("cpt_codes", []),
                "completeness_score": completeness_score
            }
            
            print(f"[v0] SOAPService: Generated SOAP note with {len(result.get('icd10_codes', []))} ICD-10 codes and {len(result.get('cpt_codes', []))} CPT codes")
            return result
            
        except json.JSONDecodeError as e:
            print(f"[v0] SOAPService ERROR: Failed to parse JSON - {str(e)}")
            print(f"[v0] SOAPService ERROR: Raw content: {content[:500] if 'content' in locals() else 'No content'}")
            raise Exception(f"Failed to parse SOAP note JSON: {str(e)}")
        except Exception as e:
            print(f"[v0] SOAPService ERROR: {type(e).__name__} - {str(e)}")
            import traceback
            traceback.print_exc()
            raise Exception(f"SOAP generation failed: {str(e)}")
