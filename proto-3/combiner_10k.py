#!/usr/bin/env python3
"""
JSON Merger Script for Company Financial Data

This script traverses a directory structure containing company financial data
organized by year and merges all JSON files for each company into a single
consolidated JSON file.

Expected directory structure:
- companies/
  - Company_Name/
    - output_10k/
      - 2020/
        - *.json
      - 2021/
        - *.json
    - output_8k/
      - 2020/
        - *.json

Output: Creates merged_data.json in each company's root folder
"""

import json
import os
import sys
from pathlib import Path
from typing import Dict, Any, List
import argparse
from collections import defaultdict


def find_json_files(directory: Path) -> List[Path]:
    """
    Recursively find all JSON files in the given directory.
    
    Args:
        directory: Path object pointing to the directory to search
        
    Returns:
        List of Path objects pointing to JSON files
    """
    json_files = []
    if directory.exists() and directory.is_dir():
        json_files = list(directory.rglob('*.json'))
    return json_files


def extract_year_from_path(json_file: Path, base_path: Path) -> str:
    """
    Extract year from the file path structure.
    
    Args:
        json_file: Path to the JSON file
        base_path: Base company directory path
        
    Returns:
        Year as string, or 'unknown' if can't be determined
    """
    try:
        # Get relative path from company base to json file
        relative_path = json_file.relative_to(base_path)
        
        # Look for year pattern in path parts (4-digit number starting with 20)
        for part in relative_path.parts:
            if part.isdigit() and len(part) == 4 and part.startswith('20'):
                return part
                
        # Try to extract from filename if not found in path
        filename = json_file.stem
        for part in filename.split('_'):
            if part.isdigit() and len(part) == 4 and part.startswith('20'):
                return part
                
        return 'unknown'
    except Exception:
        return 'unknown'


def load_json_file(json_file: Path) -> Dict[str, Any]:
    """
    Safely load a JSON file.
    
    Args:
        json_file: Path to the JSON file
        
    Returns:
        Dictionary containing JSON data, empty dict if failed
    """
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            print(f"✓ Loaded: {json_file.name}")
            return data
    except json.JSONDecodeError as e:
        print(f"✗ JSON decode error in {json_file.name}: {e}")
        return {}
    except Exception as e:
        print(f"✗ Error loading {json_file.name}: {e}")
        return {}


def merge_company_data(company_data: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """
    Merge data for a single company across all years.
    
    Args:
        company_data: Dictionary with years as keys and company data as values
        
    Returns:
        Merged company data structure
    """
    if not company_data:
        return {}
    
    # Get company name from first available data
    company_name = None
    for year_data in company_data.values():
        if isinstance(year_data, dict):
            company_name = list(year_data.keys())[0] if year_data else None
            if company_name:
                break
    
    if not company_name:
        return {}
    
    merged_data = {company_name: {}}
    
    # Merge all year data under the company name
    for year, year_data in sorted(company_data.items()):
        if isinstance(year_data, dict) and company_name in year_data:
            merged_data[company_name][year] = year_data[company_name]
        elif isinstance(year_data, dict) and year_data:
            # Handle cases where the structure might be different
            merged_data[company_name][year] = year_data
    
    return merged_data


def process_company_directory(company_dir: Path) -> bool:
    """
    Process a single company directory and create merged JSON.
    
    Args:
        company_dir: Path to company directory
        
    Returns:
        True if successful, False otherwise
    """
    company_name = company_dir.name
    print(f"\n📁 Processing company: {company_name}")
    
    # Find all JSON files in the company directory
    json_files = find_json_files(company_dir)
    
    if not json_files:
        print(f"  No JSON files found for {company_name}")
        return False
    
    print(f"  Found {len(json_files)} JSON file(s)")
    
    # Group files by year
    year_data = defaultdict(list)
    
    for json_file in json_files:
        year = extract_year_from_path(json_file, company_dir)
        year_data[year].append(json_file)
    
    # Process each year's data
    company_merged_data = {}
    
    for year, files in year_data.items():
        print(f"  📅 Processing year: {year}")
        
        year_merged = {}
        for json_file in files:
            data = load_json_file(json_file)
            if data:
                # Merge data for this year
                if isinstance(data, dict):
                    for key, value in data.items():
                        if key not in year_merged:
                            year_merged[key] = value
                        else:
                            # If key exists, try to merge intelligently
                            if isinstance(year_merged[key], dict) and isinstance(value, dict):
                                year_merged[key].update(value)
                            else:
                                year_merged[key] = value
        
        if year_merged:
            company_merged_data[year] = year_merged
    
    if not company_merged_data:
        print(f"  ✗ No valid data found for {company_name}")
        return False
    
    # Create final merged structure
    final_merged = merge_company_data(company_merged_data)
    
    if not final_merged:
        print(f"  ✗ Failed to merge data for {company_name}")
        return False
    
    # Save merged data
    output_file = company_dir / 'merged_data.json'
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(final_merged, f, indent=2, ensure_ascii=False)
        
        print(f"  ✅ Merged data saved to: {output_file}")
        print(f"  📊 Years included: {list(company_merged_data.keys())}")
        return True
        
    except Exception as e:
        print(f"  ✗ Error saving merged data: {e}")
        return False


def main():
    """Main function to handle command line arguments and process directories."""
    parser = argparse.ArgumentParser(
        description='Merge JSON files by year for each company',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python combiner_10k.py /path/to/companies
  python combiner_10k.py "C:\\Users\\user\\companies"
        """
    )
    
    parser.add_argument(
        'directory',
        help='Path to the directory containing company folders'
    )
    
    parser.add_argument(
        '--output-name',
        default='merged_data.json',
        help='Name of the output JSON file (default: merged_data.json)'
    )
    
    args = parser.parse_args()
    
    # Convert to Path object
    root_dir = Path(args.directory).resolve()
    
    if not root_dir.exists():
        print(f"❌ Error: Directory '{root_dir}' does not exist")
        sys.exit(1)
    
    if not root_dir.is_dir():
        print(f"❌ Error: '{root_dir}' is not a directory")
        sys.exit(1)
    
    print(f"🚀 Starting JSON merger for directory: {root_dir}")
    
    # Find all company directories
    company_dirs = [d for d in root_dir.iterdir() if d.is_dir()]
    
    if not company_dirs:
        print(f"❌ No subdirectories found in {root_dir}")
        sys.exit(1)
    
    print(f"📂 Found {len(company_dirs)} company directories")
    
    # Process each company
    successful = 0
    failed = 0
    
    for company_dir in sorted(company_dirs):
        try:
            if process_company_directory(company_dir):
                successful += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ Unexpected error processing {company_dir.name}: {e}")
            failed += 1
    
    # Summary
    print(f"\n📋 Summary:")
    print(f"  ✅ Successfully processed: {successful} companies")
    print(f"  ❌ Failed to process: {failed} companies")
    print(f"  📁 Output files saved as: merged_data.json in each company folder")
    
    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
