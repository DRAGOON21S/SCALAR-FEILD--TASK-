#!/usr/bin/env python3
"""
8-K JSON Files Processor

This script processes 8-K JSON files from the companies directory structure:
- Finds each company's output_8k folder
- For each year, merges all JSON files for that year
- Wraps content with year information
- Creates final combined JSON per company
- Saves results in gemini_8k folder

Expected structure:
companies/
├── Company_Name/
│   └── output_8k/
│       ├── 2020/
│       │   ├── file1.json
│       │   └── file2.json
│       └── 2021/
│           └── file3.json

Output: gemini_8k/Company_Name_8k.json
"""

import json
import os
import sys
from pathlib import Path
from typing import Dict, Any, List
from collections import defaultdict

def load_json_file(json_file: Path) -> Dict[str, Any]:
    """
    Load and parse a JSON file.
    
    Args:
        json_file: Path to JSON file
        
    Returns:
        Dictionary with parsed JSON data, empty dict if error
    """
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            print(f"    ✓ Loaded: {json_file.name}")
            return data
    except json.JSONDecodeError as e:
        print(f"    ✗ JSON decode error in {json_file.name}: {e}")
        return {}
    except Exception as e:
        print(f"    ✗ Error loading {json_file.name}: {e}")
        return {}

def merge_year_files(year_folder: Path, year: str) -> Dict[str, Any]:
    """
    Merge all JSON files for a specific year.
    
    Args:
        year_folder: Path to year folder containing JSON files
        year: Year string
        
    Returns:
        Merged data for the year
    """
    print(f"  📅 Processing year: {year}")
    
    json_files = list(year_folder.glob("*.json"))
    if not json_files:
        print(f"    ⚠️ No JSON files found in {year}")
        return {}
    
    # Initialize the structure that we want for this year
    year_content = {
        "FORM": "8-K",
        "CATEGORIES": {}
    }
    
    for json_file in json_files:
        file_data = load_json_file(json_file)
        if file_data:
            # Extract the content from the nested structure
            # The structure is usually: {"Company Name": {"YEAR": {"FORM": ..., "CATEGORIES": {...}}}}
            if isinstance(file_data, dict):
                for company_key, company_data in file_data.items():
                    if isinstance(company_data, dict):
                        for year_key, year_data in company_data.items():
                            if isinstance(year_data, dict) and "CATEGORIES" in year_data:
                                # Merge categories from this file
                                categories = year_data.get("CATEGORIES", {})
                                for section_key, section_data in categories.items():
                                    if section_key not in year_content["CATEGORIES"]:
                                        year_content["CATEGORIES"][section_key] = section_data
                                    else:
                                        # Merge items within the same section
                                        if isinstance(section_data, dict) and "ITEMS" in section_data:
                                            if "ITEMS" not in year_content["CATEGORIES"][section_key]:
                                                year_content["CATEGORIES"][section_key]["ITEMS"] = {}
                                            year_content["CATEGORIES"][section_key]["ITEMS"].update(section_data.get("ITEMS", {}))
    
    return year_content

def process_company(company_dir: Path) -> bool:
    """
    Process a single company's 8-K files.
    
    Args:
        company_dir: Path to company directory
        
    Returns:
        True if successful, False otherwise
    """
    company_name = company_dir.name
    print(f"📁 Processing company: {company_name}")
    
    # Check for output_8k folder
    output_8k_dir = company_dir / "output_8k"
    if not output_8k_dir.exists():
        print(f"  ⚠️ No output_8k folder found for {company_name}")
        return False
    
    # Get all year folders
    year_folders = [d for d in output_8k_dir.iterdir() if d.is_dir() and d.name.isdigit()]
    if not year_folders:
        print(f"  ⚠️ No year folders found in output_8k for {company_name}")
        return False
    
    # Sort year folders
    year_folders.sort(key=lambda x: x.name)
    
    company_data = {}
    
    # Process each year
    for year_folder in year_folders:
        year = year_folder.name
        year_data = merge_year_files(year_folder, year)
        
        if year_data:
            company_data[year] = year_data
    
    if not company_data:
        print(f"  ✗ No valid data found for {company_name}")
        return False
    
    # Create final structure with company name
    final_data = {
        company_name.replace('_', ' '): company_data
    }
    
    return final_data

def main():
    """Main function to process all companies."""
    # Get the script directory
    script_dir = Path(__file__).parent
    companies_dir = script_dir / "proto-3" / "companies"
    
    if not companies_dir.exists():
        print(f"❌ Companies directory not found: {companies_dir}")
        sys.exit(1)
    
    # Create output directory
    output_dir = script_dir / "gemini_8k"
    output_dir.mkdir(exist_ok=True)
    print(f"📂 Output directory: {output_dir}")
    
    # Get all company directories
    company_dirs = [d for d in companies_dir.iterdir() if d.is_dir()]
    if not company_dirs:
        print(f"❌ No company directories found in {companies_dir}")
        sys.exit(1)
    
    print(f"🚀 Starting 8-K processing for {len(company_dirs)} companies\n")
    
    successful_companies = 0
    failed_companies = 0
    
    # Process each company
    for company_dir in sorted(company_dirs):
        try:
            result = process_company(company_dir)
            
            if result:
                company_name = company_dir.name
                output_file = output_dir / f"{company_name}_8k.json"
                
                # Save the result
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(result, f, indent=2, ensure_ascii=False)
                
                print(f"  ✅ Saved: {output_file.name}")
                print(f"  📊 Years included: {list(list(result.values())[0].keys())}")
                successful_companies += 1
            else:
                print(f"  ❌ Failed to process {company_dir.name}")
                failed_companies += 1
                
        except Exception as e:
            print(f"  ❌ Error processing {company_dir.name}: {e}")
            failed_companies += 1
        
        print()  # Add spacing between companies
    
    # Summary
    print("=" * 60)
    print("📋 PROCESSING SUMMARY")
    print("=" * 60)
    print(f"✅ Successfully processed: {successful_companies} companies")
    print(f"❌ Failed to process: {failed_companies} companies")
    print(f"📁 Output files saved in: {output_dir}")
    print(f"📄 File naming pattern: CompanyName_8k.json")
    
    if successful_companies > 0:
        print(f"\n🎉 Processing completed successfully!")
        print(f"📂 Check the '{output_dir.name}' folder for your combined 8-K JSON files.")
    
if __name__ == "__main__":
    main()
