#!/usr/bin/env python3
"""
Script to replace 'part_name' with 'gemini_part_name' from sections in all JSON files in gemini_10k folder
"""

import json
import os
from pathlib import Path

def update_part_names(data):
    """
    Update part_name with gemini_part_name from the first section that has it
    """
    if not isinstance(data, dict):
        return
    
    # Recursively process nested dictionaries
    for key, value in data.items():
        if isinstance(value, dict):
            update_part_names(value)
        elif isinstance(value, list):
            for item in value:
                update_part_names(item)
    
    # Process parts array if it exists
    if 'parts' in data and isinstance(data['parts'], list):
        for part in data['parts']:
            if isinstance(part, dict) and 'sections' in part:
                # Look for gemini_part_name in any section of this part
                gemini_part_name = None
                
                if isinstance(part['sections'], list):
                    for section in part['sections']:
                        if isinstance(section, dict) and 'gemini_part_name' in section:
                            gemini_part_name = section['gemini_part_name']
                            break
                
                # Update part_name if we found a gemini_part_name
                if gemini_part_name and 'part_name' in part:
                    print(f"  Updating part_name from '{part['part_name']}' to '{gemini_part_name}'")
                    part['part_name'] = gemini_part_name

def process_json_file(file_path):
    """
    Process a single JSON file to update part names
    """
    try:
        print(f"Processing {file_path.name}...")
        
        # Read the JSON file
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Update part names
        update_part_names(data)
        
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
