#!/usr/bin/env python3
"""
Setup script to help configure Gemini API key.
"""

import os

def setup_gemini_api():
    print("🚀 Gemini API Setup")
    print("=" * 50)
    print()
    print("1. Go to https://makersuite.google.com/app/apikey")
    print("2. Sign in with your Google account")
    print("3. Click 'Create API key'")
    print("4. Copy the generated API key")
    print()
    
    api_key = input("Enter your Gemini API key: ").strip()
    
    if not api_key:
        print("❌ No API key entered")
        return False
    
    # Test the API key format (basic validation)
    if not api_key.startswith('AI'):
        print("⚠️  Warning: API key doesn't start with 'AI' - this might be incorrect")
    
    # For PowerShell on Windows
    print()
    print("To set the environment variable, run this command in PowerShell:")
    print(f"$env:GEMINI_API_KEY='{api_key}'")
    print()
    print("Or add it to your system environment variables for permanent use.")
    print()
    
    # Set for current session
    os.environ['GEMINI_API_KEY'] = api_key
    print("✅ API key set for current Python session")
    
    return True

if __name__ == "__main__":
    if setup_gemini_api():
        print("\n🎉 Setup complete! You can now run the Gemini processor.")
        print("\nNext steps:")
        print("1. Run: python test_gemini.py (to test the connection)")
        print("2. Run: python gemini_processor.py (to process all files)")
