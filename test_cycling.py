#!/usr/bin/env python3
"""
Test script to verify Gemini API key and model cycling functionality
"""
import os
import time
from itertools import cycle
from dotenv import load_dotenv
import google.generativeai as genai

# Load environment variables
load_dotenv()

# API Keys setup (same as in re-ra_specific_02.py)
API_KEYS = [
    os.getenv("GEMINI_API_KEY1"),
    os.getenv("GEMINI_API_KEY2"),
    os.getenv("GEMINI_API_KEY3"),
    os.getenv("GEMINI_API_KEY4"),
    os.getenv("GEMINI_API_KEY5"),
    os.getenv("GEMINI_API_KEY6"),
    os.getenv("GEMINI_API_KEY7"),
    os.getenv("GEMINI_API_KEY8"),
    os.getenv("GEMINI_API_KEY9"),
    os.getenv("GEMINI_API_KEY10"),
    os.getenv("GEMINI_API_KEY11"),
    os.getenv("GEMINI_API_KEY12"),
    os.getenv("GEMINI_API_KEY13"),
]

# Filter out None values
API_KEYS = [key for key in API_KEYS if key is not None]

print(f"🔑 Found {len(API_KEYS)} API keys")
for i, key in enumerate(API_KEYS, 1):
    print(f"   Key {i}: ...{key[-4:] if key else 'None'}")

# Models setup
gemini_models = ["gemini-2.5-flash-lite", "gemini-2.5-flash", "gemini-2.5-pro"]
print(f"\n🤖 Available models: {gemini_models}")

# Create cycles
api_key_cycle = cycle(API_KEYS)
model_cycle = cycle(gemini_models)

# Initialize
current_api_key = next(api_key_cycle)
current_model = next(model_cycle)

def configure_gemini(api_key: str):
    """Configure Gemini with the given API key."""
    genai.configure(api_key=api_key)
    print(f"🔧 Configured Gemini with API key ending in {api_key[-4:]}")

def test_api_call(prompt_text, max_attempts: int = 3):
    """Test API call with cycling functionality"""
    global current_api_key, current_model
    
    print(f"\n🧪 Testing with model: {current_model}")
    print(f"🔑 Using API key ending in: {current_api_key[-4:]}")
    
    for attempt in range(max_attempts):
        try:
            model = genai.GenerativeModel(current_model)
            resp = model.generate_content(prompt_text, generation_config={"temperature": 0.0})
            result = getattr(resp, "text", str(resp))
            print(f"✅ Success! Response: {result[:100]}...")
            return result

        except Exception as e:
            error_msg = str(e).lower()
            print(f"❌ Attempt {attempt + 1} failed: {e}")

            if "quota" in error_msg or "429" in error_msg or "exceeded" in error_msg:
                print(f"🔄 Quota exceeded for key ending in {current_api_key[-4:]}. Switching to next key...")
                current_api_key = next(api_key_cycle)
                configure_gemini(current_api_key)
                print(f"🔄 Also switching to next model...")
                current_model = next(model_cycle)
                time.sleep(2)
            else:
                print(f"⚠️ Unexpected error: {e}")
                if attempt == max_attempts - 1:
                    raise e

    raise RuntimeError("All attempts exhausted.")

def test_cycling():
    """Test the cycling functionality"""
    global current_api_key, current_model
    print("🚀 Starting cycling test...\n")
    
    # Initial configuration
    configure_gemini(current_api_key)
    
    # Test prompts
    test_prompts = [
        "Write a short review about a medical device in 20 words.",
        "Rate this review from 1-5: 'This product works well.'",
        "Generate a brief product description for orthopedic equipment.",
    ]
    
    for i, prompt in enumerate(test_prompts, 1):
        print(f"\n{'='*50}")
        print(f"🧪 Test {i}/3: {prompt}")
        print('='*50)
        
        try:
            result = test_api_call(prompt)
            print(f"✅ Test {i} completed successfully")
            
            # Simulate cycling by switching keys and models
            print(f"\n🔄 Manually cycling to next key and model...")
            current_api_key = next(api_key_cycle)
            current_model = next(model_cycle)
            configure_gemini(current_api_key)
            
        except Exception as e:
            print(f"❌ Test {i} failed: {e}")
        
        time.sleep(1)  # Brief pause between tests

if __name__ == "__main__":
    if not API_KEYS:
        print("❌ No API keys found! Please check your .env file.")
        exit(1)
    
    test_cycling()
    print(f"\n🎉 Cycling test completed!")