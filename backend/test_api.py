# test_api.py - Updated version
from dotenv import load_dotenv
import os
from google import genai

load_dotenv()
api_key = os.getenv('GEMINI_API_KEY')
print(f"API Key: {api_key[:10]}..." if api_key else "No API key!")

if not api_key:
    exit(1)

client = genai.Client(api_key=api_key)

# Try multiple models in order
models_to_try = [
    "gemini-2.0-flash-lite",  # Most likely to work
    "gemini-1.5-flash",       # Alternative
    "gemini-1.5-flash-002"    # Specific version
]

for model_name in models_to_try:
    print(f"\nTrying model: {model_name}")
    try:
        response = client.models.generate_content(
            model=model_name,
            contents="Say 'Hello' in one word only."
        )
        print(f"✅ SUCCESS with {model_name}: {response.text}")
        print(f"🎯 Use this model in your app.py!")
        break  # Stop after first success
    except Exception as e:
        if "429" in str(e):
            print(f"❌ Quota exhausted for {model_name}")
        elif "404" in str(e):
            print(f"❌ Model not found: {model_name}")
        else:
            print(f"❌ Error: {str(e)[:100]}")