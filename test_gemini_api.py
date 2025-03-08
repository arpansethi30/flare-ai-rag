#!/usr/bin/env python
"""
Simple test script to verify if the Gemini API key is working properly.
"""

import os
import google.generativeai as genai
from dotenv import load_dotenv

def test_gemini_api():
    # Load environment variables from .env file
    load_dotenv()
    
    # Get API key from environment variable
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("ERROR: No API key found. Make sure GEMINI_API_KEY is set in your .env file.")
        return False
    
    print(f"Using API key: {api_key[:5]}...{api_key[-4:]}")
    
    try:
        # Configure the Gemini API
        genai.configure(api_key=api_key)
        
        # List available models to verify connection
        print("Checking available models...")
        models = genai.list_models()
        gemini_models = [model.name for model in models if "gemini" in model.name.lower()]
        print(f"Available Gemini models: {gemini_models}")
        
        # Test with a simple prompt
        model = genai.GenerativeModel('gemini-1.5-flash')
        print("\nSending a test prompt to Gemini...")
        response = model.generate_content("Hello, please respond with a simple 'Hello, world!' message.")
        
        print("\nResponse from Gemini API:")
        print(response.text)
        
        print("\n✅ SUCCESS: Gemini API is working correctly!")
        return True
        
    except Exception as e:
        print(f"\n❌ ERROR: Failed to connect to Gemini API: {str(e)}")
        return False

if __name__ == "__main__":
    test_gemini_api() 