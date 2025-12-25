# list_models_fixed.py
from google import genai
import os
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv('GEMINI_API_KEY')

if not api_key:
    print("❌ ERROR: GEMINI_API_KEY not found!")
    exit(1)

client = genai.Client(api_key=api_key)

print("🔍 Listing ALL available models:")
print("=" * 70)

try:
    models = client.models.list()
    print(f"✅ Total models found: {len(models)}\n")
    
    # Count models by type
    gemini_count = 0
    embedding_count = 0
    other_count = 0
    
    print("📋 GEMINI MODELS (for text generation):")
    print("-" * 40)
    
    for model in models:
        model_name = model.name
        
        # Check if it's a Gemini model (for text generation)
        if "gemini" in model_name.lower() and "embedding" not in model_name.lower():
            gemini_count += 1
            
            # Get supported actions safely
            supported = []
            try:
                if hasattr(model, 'supported_actions'):
                    supported = model.supported_actions
            except:
                supported = ["unknown"]
            
            # Check if it supports generateContent
            if "generateContent" in supported:
                status = "✅ CAN USE"
            else:
                status = "❌ Not for chat"
            
            print(f"{gemini_count}. {status}")
            print(f"   Name: {model_name}")
            
            # Try to get base_model_id if it exists
            try:
                if hasattr(model, 'base_model_id'):
                    print(f"   Simple Name: {model.base_model_id}")
            except:
                pass
                
            print(f"   Supported: {', '.join(supported) if supported else 'unknown'}")
            print()
    
    print(f"\n📊 Summary: Found {gemini_count} Gemini models")
    
except Exception as e:
    print(f"❌ Error: {type(e).__name__}: {e}")