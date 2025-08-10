#!/usr/bin/env python3
"""
Script to replace 'category' field with 'gemini_item_name' value in all JSON files in gemini_10k folder
"""

import json
import os
from pathlib import Path

def replace_category_with_gemini_item_name(obj):
    """
    Recursively replace 'category' field with 'gemini_item_name' value in nested dictionaries and lists
    """
    if isinstance(obj, dict):
        # If this dict has both category and gemini_item_name, replace category
        if 'category' in obj and 'gemini_item_name' in obj:
            print(f"    Replacing category '{obj['category']}' with '{obj['gemini_item_name']}'")
            obj['category'] = obj['gemini_item_name']
        
        # Recursively process all values
        for key, value in obj.items():
            replace_category_with_gemini_item_name(value)
    
    elif isinstance(obj, list):
        # Recursively process all items in list
        for item in obj:
            replace_category_with_gemini_item_name(item)

def process_json_file(file_path):
    """
    Process a single JSON file to replace category with gemini_item_name
    """
    try:
        print(f"Processing {file_path.name}...")
        
        # Read the JSON file
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Replace category fields with gemini_item_name values
        replace_category_with_gemini_item_name(data)
        
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
