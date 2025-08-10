#!/usr/bin/env python3
"""
Script to fix remaining part_name issues and ensure all are properly updated
"""

import json
import os
from pathlib import Path

def update_part_names_fixed(data):
    """
    Update part_name with gemini_part_name from sections, with fallback for empty sections
    """
    if not isinstance(data, dict):
        return
    
    # Recursively process nested dictionaries
    for key, value in data.items():
        if isinstance(value, dict):
            update_part_names_fixed(value)
        elif isinstance(value, list):
            for item in value:
                update_part_names_fixed(item)
    
    # Process parts array if it exists
    if 'parts' in data and isinstance(data['parts'], list):
        for part in data['parts']:
            if isinstance(part, dict) and 'part_name' in part:
                current_part_name = part['part_name']
                
                # Skip if already properly formatted
                if current_part_name.startswith('Part I:') or current_part_name.startswith('Part II:') or \
                   current_part_name.startswith('Part III:') or current_part_name.startswith('Part IV:'):
                    continue
                
                # Look for gemini_part_name in any section of this part
                gemini_part_name = None
                
                if 'sections' in part and isinstance(part['sections'], list):
                    for section in part['sections']:
                        if isinstance(section, dict) and 'gemini_part_name' in section:
                            gemini_part_name = section['gemini_part_name']
                            break
                
                # If no gemini_part_name found, try to infer from part_name
                if not gemini_part_name:
                    if 'Part_1_' in current_part_name or 'Part_I' in current_part_name:
                        gemini_part_name = 'Part I: Business and Risk Factors'
                    elif 'Part_2_' in current_part_name or 'Part_II' in current_part_name:
                        gemini_part_name = 'Part II: Financial Information'
                    elif 'Part_3_' in current_part_name or 'Part_III' in current_part_name:
                        gemini_part_name = 'Part III: Governance'
                    elif 'Part_4_' in current_part_name or 'Part_5_' in current_part_name or 'Part_IV' in current_part_name:
                        gemini_part_name = 'Part IV: Exhibits and Schedules'
                
                # Update part_name if we found or inferred a gemini_part_name
                if gemini_part_name:
                    print(f"  Updating part_name from '{current_part_name}' to '{gemini_part_name}'")
                    part['part_name'] = gemini_part_name
                else:
                    print(f"  ⚠️  Could not determine part name for: '{current_part_name}'")

def process_json_file_fixed(file_path):
    """
    Process a single JSON file to fix remaining part name issues
    """
    try:
        print(f"Processing {file_path.name}...")
        
        # Read the JSON file
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Update part names
        update_part_names_fixed(data)
        
        # Write back to the same file
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Successfully processed {file_path.name}")
        
    except Exception as e:
        print(f"❌ Error processing {file_path.name}: {str(e)}")

def main():
    """
    Main function to fix remaining part name issues in all JSON files
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
    
    print("\nFixing remaining part name issues...")
    
    # Process each JSON file
    for file_path in json_files:
        process_json_file_fixed(file_path)
    
    print(f"\n🎉 Completed processing {len(json_files)} files!")

if __name__ == "__main__":
    main()
