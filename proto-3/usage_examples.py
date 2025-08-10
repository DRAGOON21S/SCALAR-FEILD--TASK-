#!/usr/bin/env python3
"""
Example usage of the JSON Combiner Script

This script demonstrates different ways to use the combiner_10k.py script
"""

import subprocess
import sys
import os
from pathlib import Path


def run_combiner_example():
    """Example of how to run the combiner script programmatically."""
    
    # Example 1: Basic usage
    print("🔨 Example 1: Basic usage")
    print("Command: python combiner_10k.py /path/to/companies")
    print("This will merge all JSON files in company subdirectories by year")
    print()
    
    # Example 2: Using custom output filename
    print("🔨 Example 2: Custom output filename")
    print("Command: python combiner_10k.py /path/to/companies --output-name custom_merged.json")
    print("This will create custom_merged.json instead of merged_data.json")
    print()
    
    # Example 3: Help information
    print("🔨 Example 3: Get help")
    print("Command: python combiner_10k.py --help")
    print("This will show all available options")
    print()
    
    # Example 4: Actual execution (commented out for safety)
    print("🔨 Example 4: Actual execution")
    current_dir = Path(__file__).parent
    companies_dir = current_dir / "companies"
    
    if companies_dir.exists():
        print(f"Command that would be run: python combiner_10k.py \"{companies_dir}\"")
        print("(Uncomment the lines below to actually run the script)")
        
        # Uncomment these lines to actually run the script:
        # try:
        #     result = subprocess.run([
        #         sys.executable, 
        #         "combiner_10k.py", 
        #         str(companies_dir)
        #     ], capture_output=True, text=True, cwd=current_dir)
        #     
        #     print("Output:")
        #     print(result.stdout)
        #     
        #     if result.stderr:
        #         print("Errors:")
        #         print(result.stderr)
        #         
        # except Exception as e:
        #     print(f"Error running combiner: {e}")
    else:
        print(f"Companies directory not found at: {companies_dir}")
    
    print()
    print("📊 Expected output structure after running:")
    print("companies/")
    print("├── Apple_Inc/")
    print("│   ├── merged_data.json  ← Consolidated data for all years")
    print("│   ├── 2020/")
    print("│   ├── 2021/")
    print("│   └── ...")
    print("├── Microsoft_Corp/")
    print("│   ├── merged_data.json  ← Consolidated data for all years")
    print("│   └── ...")
    print("└── ...")


def load_merged_data_example():
    """Example of how to load and work with the merged data."""
    
    print("\n🔍 Example: Working with merged data")
    
    example_code = '''
import json
from pathlib import Path

# Load merged data for a company
def load_company_data(company_name, companies_dir="companies"):
    company_path = Path(companies_dir) / company_name / "merged_data.json"
    
    if not company_path.exists():
        print(f"No merged data found for {company_name}")
        return None
    
    try:
        with open(company_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data
    except Exception as e:
        print(f"Error loading data for {company_name}: {e}")
        return None

# Example usage:
apple_data = load_company_data("Apple_Inc")
if apple_data:
    company_name = list(apple_data.keys())[0]
    years = list(apple_data[company_name].keys())
    print(f"Company: {company_name}")
    print(f"Available years: {years}")
    
    # Access specific year data
    if "2021" in apple_data[company_name]:
        data_2021 = apple_data[company_name]["2021"]
        print(f"2021 data keys: {list(data_2021.keys())}")

# Compare data across years
def compare_years(company_data, year1, year2):
    company_name = list(company_data.keys())[0]
    
    if year1 in company_data[company_name] and year2 in company_data[company_name]:
        data1 = company_data[company_name][year1]
        data2 = company_data[company_name][year2]
        
        print(f"Comparing {year1} vs {year2}:")
        print(f"  {year1} data size: {len(str(data1))} characters")
        print(f"  {year2} data size: {len(str(data2))} characters")
        
        # Add your comparison logic here
        return data1, data2
    else:
        print(f"Data not available for comparison between {year1} and {year2}")
        return None, None
'''
    
    print("Python code for working with merged data:")
    print(example_code)


if __name__ == "__main__":
    print("📋 JSON Combiner Usage Examples")
    print("=" * 50)
    
    run_combiner_example()
    load_merged_data_example()
    
    print("\n✅ Examples complete!")
    print("Copy and modify these examples for your specific use case.")
