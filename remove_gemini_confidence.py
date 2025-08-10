#!/usr/bin/env python3
"""
Script to remove 'gemini_confidence' field from all JSON files in gemini_10k folder
"""

import json
import os
from pathlib import Path

def remove_gemini_confidence_recursive(obj):
    """
    Recursively remove 'gemini_confidence' field from nested dictionaries and lists
    """
    if isinstance(obj, dict):
        # Remove gemini_confidence if it exists
        if 'gemini_confidence' in obj:
            del obj['gemini_confidence']
        
        # Recursively process all values
        for key, value in obj.items():
            remove_gemini_confidence_recursive(value)
    
    elif isinstance(obj, list):
        # Recursively process all items in list
        for item in obj:
            remove_gemini_confidence_recursive(item)

def process_json_file(file_path):
    """
    Process a single JSON file to remove gemini_confidence fields
    """
    try:
        print(f"Processing {file_path.name}...")
        
        # Read the JSON file
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Remove gemini_confidence fields recursively
        remove_gemini_confidence_recursive(data)
        
        # Write back to the same file
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Successfully processed {file_path.name}")
        
    except Exception as e:
        print(f"❌ Error processing {file_path.name}: {str(e)}")

def main():
    """
    Main function to process all JSON files in gemini_10k folder
    """
    gemini_10k_path = Path("gemini_10k")
    
    if not gemini_10k_path.exists():
        print("❌ gemini_10k folder not found!")
        return
    
    # Get all JSON files in the folder
    json_files = list(gemini_10k_path.glob("*.json"))
    
    if not json_files:
        print("❌ No JSON files found in gemini_10k folder!")
        return
    
    print(f"Found {len(json_files)} JSON files to process:")
    for file_path in json_files:
        print(f"  - {file_path.name}")
    
    print("\nProcessing files...")
    
    # Process each JSON file
    for file_path in json_files:
        process_json_file(file_path)
    
    print(f"\n🎉 Completed processing {len(json_files)} files!")

if __name__ == "__main__":
    main()
