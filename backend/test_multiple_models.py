# test_multiple_models.py
from google import genai
import os
import time
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv('GEMINI_API_KEY')
client = genai.Client(api_key=api_key)

# Models to test - focusing on ones you haven't tried
models_to_test = [
    "gemini-2.5-flash",
    "gemini-2.5-pro",
    "gemini-flash-latest",
    "gemini-2.5-flash-lite",
    "gemini-exp-1206",
    "gemini-2.5-flash-preview-09-2025"
]

print("🧪 Testing different models for available quota:")
print("=" * 60)

working_models = []

for i, model_name in enumerate(models_to_test, 1):
    print(f"\n{i}. Testing: {model_name}")
    
    try:
        # Very short test to check quota
        response = client.models.generate_content(
            model=model_name,
            contents="Respond with just 'OK'"
        )
        
        if response.text.strip() == "OK":
            print(f"   ✅ WORKS! Quota available")
            working_models.append(model_name)
        else:
            print(f"   ⚠️ Responded but not 'OK': {response.text[:30]}")
            
    except Exception as e:
        error_str = str(e)
        if "429" in error_str:
            print(f"   ❌ Quota exhausted for this model")
        elif "404" in error_str:
            print(f"   ❌ Model not found (use exact name)")
        else:
            print(f"   ❌ Error: {error_str[:60]}...")
    
    # Brief pause between requests
    if i < len(models_to_test):
        time.sleep(1)

print("\n" + "=" * 60)
if working_models:
    print(f"🎯 SUCCESS! Working models: {working_models}")
    print(f"👉 Update app.py to use: model='{working_models[0]}'")
else:
    print("⚠️ No models worked. Your free tier quota may be fully exhausted.")
    print("   Next steps:")
    print("   1. Wait 24h for daily reset")
    print("   2. Create new Google account for fresh API key")
    print("   3. Set up billing ($10-20 credit for development)")

# Also test if ANY model works with a different approach
print("\n🔍 Testing 'gemini-flash-latest' (auto-updates to newest):")
try:
    response = client.models.generate_content(
        model="gemini-flash-latest",
        contents="Say 'Test successful'"
    )
    print(f"   ✅ gemini-flash-latest: {response.text}")
    working_models.append("gemini-flash-latest")
except Exception as e:
    print(f"   ❌ gemini-flash-latest also exhausted")