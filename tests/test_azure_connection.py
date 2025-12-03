import os
from openai import AzureOpenAI
from dotenv import load_dotenv

load_dotenv()

print("=" * 60)
print("Azure OpenAI Connection Diagnostics")
print("=" * 60)

# Read config
endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
api_key = os.getenv("AZURE_OPENAI_API_KEY")
deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")
api_version = os.getenv("AZURE_OPENAI_API_VERSION")
whisper_deployment = os.getenv("AZURE_WHISPER_DEPLOYMENT_NAME")

print(f"\nConfiguration:")
print(f"  Endpoint: {endpoint}")
print(f"  API Key: {'*' * 20}{api_key[-8:] if api_key else 'NOT SET'}")
print(f"  GPT Deployment: {deployment}")
print(f"  Whisper Deployment: {whisper_deployment}")
print(f"  API Version: {api_version}")

# Test connection
try:
    print(f"\n{'='*60}")
    print("Testing GPT-4 Connection...")
    print("=" * 60)
    
    client = AzureOpenAI(
        api_key=api_key,
        api_version=api_version,
        azure_endpoint=endpoint
    )
    
    response = client.chat.completions.create(
        model=deployment,
        messages=[
            {"role": "user", "content": "Say 'Hello, Azure!'"}
        ],
        max_tokens=10
    )
    
    print(f"✓ SUCCESS!")
    print(f"  Response: {response.choices[0].message.content}")
    print(f"\nYour Azure OpenAI GPT-4 connection is working correctly!")
    
except Exception as e:
    print(f"✗ FAILED!")
    print(f"  Error Type: {type(e).__name__}")
    print(f"  Error Message: {str(e)}")
    print(f"\n{'='*60}")
    print("Troubleshooting Steps:")
    print("=" * 60)
    print("1. Go to https://oai.azure.com/ → Deployments")
    print("2. Verify your deployment name matches exactly (case-sensitive)")
    print(f"   Current: {deployment}")
    print("3. Check your API endpoint URL format")
    print(f"   Current: {endpoint}")
    print("   Should be: https://YOUR-RESOURCE-NAME.openai.azure.com/")
    print("4. Verify API version is correct")
    print(f"   Current: {api_version}")
    print("   Try: 2024-02-15-preview or 2024-08-01-preview")
    print("5. Check API key is correct (Keys and Endpoint page)")
