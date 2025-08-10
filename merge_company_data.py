#!/usr/bin/env python3
"""
Script to merge company 10K data across multiple years.
For each company, combines all years of data into a single JSON file.
"""

import os
import json
import glob
import re
from pathlib import Path

def simplify_category_name(filename):
    """
    Convert verbose section filenames to simple category names.
    Example: "Section_1_Item_1._Business.txt" -> "business"
    """
    # Remove file extension
    name = filename.replace('.txt', '')
    
    # Extract the main category after the last underscore or dot
    if '_Item_' in name:
        # Handle format like "Section_1_Item_1._Business.txt"
        parts = name.split('_')
        for i, part in enumerate(parts):
            if 'Item' in part and i + 1 < len(parts):
                category_part = '_'.join(parts[i+1:])
                break
        else:
            category_part = parts[-1]
    else:
        # Handle other formats
        category_part = name.split('_')[-1]
    
    # Clean up the category name
    category_part = category_part.replace('_', ' ')
    category_part = re.sub(r'^[0-9A-Z]+\.?\s*', '', category_part)  # Remove leading numbers/letters
    category_part = category_part.strip('._')
    
    # Convert to lowercase and handle common cases
    category_mapping = {
        'business': 'business',
        'risk factors': 'risk_factors',
        'unresolved staff comments': 'unresolved_staff_comments',
        'properties': 'properties',
        'legal proceedings': 'legal_proceedings',
        'mine safety disclosures': 'mine_safety_disclosures',
        'market for registrant': 'market_info',
        'market for registrants common equity': 'market_info',
        'selected financial data': 'selected_financial_data',
        'management discussion': 'management_discussion',
        'quantitative and qualitative disclosures': 'market_risk_disclosures',
        'financial statements': 'financial_statements',
        'changes in and disagreements': 'auditor_changes',
        'controls and procedures': 'controls_procedures',
        'other information': 'other_information',
        'directors trustees': 'directors_officers',
        'executive compensation': 'executive_compensation',
        'security ownership': 'security_ownership',
        'certain relationships': 'related_party_transactions',
        'principal accounting': 'accounting_fees',
        'exhibits': 'exhibits',
        'form 10 k summary': 'form_summary'
    }
    
    category_lower = category_part.lower()
    
    # Try to find a match in the mapping
    for key, value in category_mapping.items():
        if key in category_lower:
            return value
    
    # If no match found, create a simplified version
    simplified = re.sub(r'[^a-zA-Z0-9\s]', '', category_lower)
    simplified = re.sub(r'\s+', '_', simplified.strip())
    
    return simplified if simplified else 'unknown_section'

def process_content_structure(content):
    """
    Process the content structure to rename file_name to category and simplify names.
    """
    if isinstance(content, dict):
        new_content = {}
        for key, value in content.items():
            if key == 'file_name':
                # Rename to category and simplify the name
                new_content['category'] = simplify_category_name(value)
            else:
                new_content[key] = process_content_structure(value)
        return new_content
    elif isinstance(content, list):
        return [process_content_structure(item) for item in content]
    else:
        return content

def merge_company_data():
    """
    Process all companies and merge their yearly 10K data into single files.
    """
    # Define paths
    companies_dir = Path(r"c:\Users\amrit\Desktop\SCALAR-FEILD--TASK-\proto-3\companies")
    output_dir = Path(r"c:\Users\amrit\Desktop\SCALAR-FEILD--TASK-\final_10k")
    
    # Create output directory if it doesn't exist
    output_dir.mkdir(exist_ok=True)
    
    print(f"Processing companies from: {companies_dir}")
    print(f"Output directory: {output_dir}")
    
    # Process each company
    for company_dir in companies_dir.iterdir():
        if not company_dir.is_dir():
            continue
            
        company_name = company_dir.name
        print(f"\nProcessing company: {company_name}")
        
        # Look for python_output_10k directory
        python_output_dir = company_dir / "python_output_10k"
        if not python_output_dir.exists():
            print(f"  No python_output_10k directory found for {company_name}")
            continue
        
        # Initialize company data structure
        company_data = {
            "company_name": company_name,
            "years_data": {}
        }
        
        # Process each year directory
        for year_dir in python_output_dir.iterdir():
            if not year_dir.is_dir():
                continue
                
            year = year_dir.name
            print(f"  Processing year: {year}")
            
            # Find JSON files in the year directory
            json_files = list(year_dir.glob("*.json"))
            
            if not json_files:
                print(f"    No JSON files found for year {year}")
                continue
            
            # Process each JSON file in the year (should typically be one)
            for json_file in json_files:
                print(f"    Processing file: {json_file.name}")
                
                try:
                    with open(json_file, 'r', encoding='utf-8') as f:
                        year_data = json.load(f)
                    
                    # Process the content structure to rename file_name to category
                    processed_data = process_content_structure(year_data)
                    
                    # Wrap the year data with year information
                    company_data["years_data"][year] = {
                        "year": year,
                        "content": processed_data
                    }
                    
                    print(f"    Successfully processed {json_file.name}")
                    
                except json.JSONDecodeError as e:
                    print(f"    Error parsing JSON in {json_file}: {e}")
                except Exception as e:
                    print(f"    Error processing {json_file}: {e}")
        
        # Save the merged company data
        if company_data["years_data"]:
            output_file = output_dir / f"{company_name}_10k.json"
            
            try:
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(company_data, f, indent=2, ensure_ascii=False)
                
                print(f"  ✅ Saved merged data to: {output_file}")
                print(f"     Years included: {list(company_data['years_data'].keys())}")
                
            except Exception as e:
                print(f"  ❌ Error saving merged data for {company_name}: {e}")
        else:
            print(f"  ⚠️  No valid data found for {company_name}")
    
    print(f"\n🎉 Processing complete! Check the '{output_dir}' directory for merged files.")

if __name__ == "__main__":
    merge_company_data()
