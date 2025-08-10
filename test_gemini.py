#!/usr/bin/env python3
"""
Test script to verify Gemini API connection and basic processing.
"""

import os
import json
import google.generativeai as genai
from pathlib import Path

def test_gemini_connection():
    """Test if Gemini API is working."""
    try:
        # Configure API
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            print("❌ GEMINI_API_KEY environment variable not set")
            print("Please set it using: $env:GEMINI_API_KEY='your-api-key-here'")
            return False
        
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-pro')
        
        # Test simple generation
        response = model.generate_content("Hello, respond with just 'API working'")
        print(f"✅ Gemini API test successful: {response.text}")
        return True
        
    except Exception as e:
        print(f"❌ Gemini API test failed: {e}")
        return False

def test_section_classification():
    """Test section classification with sample data."""
    try:
        genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
        model = genai.GenerativeModel('gemini-pro')
        
        # Sample business section content
        sample_content = """
        Item 1. Business
        Company Background
        The Company designs, manufactures and markets smartphones, personal computers, tablets, wearables and accessories,
        and sells a variety of related services. The Company's fiscal year is the 52- or 53-week period that ends on the
        last Saturday of September. The Company is a California corporation established in 1977.
        """
        
        prompt = f"""
        You are an expert in SEC 10-K filing analysis. Analyze this section and return ONLY a JSON response:

        CONTENT: {sample_content}

        Return format:
        {{
            "part_name": "Part I: Business and Risk Factors",
            "item_name": "Item 1. Business",
            "confidence": "high"
        }}

        Valid parts: "Part I: Business and Risk Factors", "Part II: Financial Information", "Part III: Governance", "Part IV: Exhibits and Schedules"

        Valid items include: "Item 1. Business", "Item 1A. Risk Factors", "Item 2. Properties", etc.

        Respond with ONLY the JSON, no other text.
        """
        
        response = model.generate_content(prompt)
        result = json.loads(response.text.strip().replace('```json', '').replace('```', ''))
        
        print(f"✅ Classification test successful:")
        print(f"   Part: {result['part_name']}")
        print(f"   Item: {result['item_name']}")
        print(f"   Confidence: {result['confidence']}")
        return True
        
    except Exception as e:
        print(f"❌ Classification test failed: {e}")
        return False

if __name__ == "__main__":
    print("Testing Gemini API connection...")
    if test_gemini_connection():
        print("\nTesting section classification...")
        test_section_classification()
    else:
        print("Please set up your Gemini API key first.")
        print("1. Go to https://makersuite.google.com/app/apikey")
        print("2. Create an API key")
        print("3. Set it as environment variable: $env:GEMINI_API_KEY='your-key-here'")
