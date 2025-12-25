# debug_models.py
import os
import sys
from dotenv import load_dotenv

print("🔍 Starting debug...")
print(f"Python version: {sys.version}")
print(f"Current directory: {os.getcwd()}")

# Load environment variables
load_dotenv()
api_key = os.getenv('GEMINI_API_KEY')

if api_key:
    print(f"✅ API Key found: {api_key[:10]}...")
else:
    print("❌ ERROR: GEMINI_API_KEY not found!")
    print("Checking .env file...")
    if os.path.exists(".env"):
        print("✅ .env file exists")
        with open(".env", "r") as f:
            content = f.read()
            print(f"Content: {content}")
    else:
        print("❌ .env file NOT found in current directory!")

# Try to import and list models
try:
    from google import genai
    print("✅ google-genai import successful")
    
    if api_key:
        client = genai.Client(api_key=api_key)
        print("✅ Client created successfully")
        
        print("\n🔍 Attempting to list models...")
        models = client.models.list()
        
        if models:
            print(f"✅ Found {len(models)} model(s):")
            for i, model in enumerate(models, 1):
                print(f"\n{i}. Name: {model.name}")
                print(f"   Base Model ID: {model.base_model_id}")
                print(f"   Version: {model.version}")
                print(f"   Supported: {', '.join(model.supported_actions)}")
        else:
            print("❌ No models returned (empty list)")
            
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Try: pip install google-genai")
except Exception as e:
    print(f"❌ Other error: {type(e).__name__}: {e}")