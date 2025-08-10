#!/usr/bin/env python3
"""
Script to process 10K data through Gemini AI for restructuring.
Sends each section to Gemini to get proper part names and categories.
"""

import os
import json
import time
from pathlib import Path
import google.generativeai as genai
from typing import Dict, Any, List, Optional

# Configure Gemini API
# You'll need to set your API key as an environment variable: GEMINI_API_KEY
genai.configure(api_key=os.getenv('GEMINI_API_KEY'))

class GeminiProcessor:
    def __init__(self):
        self.model = genai.GenerativeModel('gemini-2.5-flash')
        
        self.valid_parts = [
            "Part I: Business and Risk Factors",
            "Part II: Financial Information", 
            "Part III: Governance",
            "Part IV: Exhibits and Schedules"
        ]
        
        self.valid_items = [
            "Item 1. Business",
            "Item 1A. Risk Factors",
            "Item 1B. Unresolved Staff Comments",
            "Item 2. Properties",
            "Item 3. Legal Proceedings",
            "Item 4. Mine Safety Disclosures",
            "Item 5. Market for Registrant's Common Equity, Related Stockholder Matters and Issuer Purchases of Equity Securities",
            "Item 6. [Reserved]",
            "Item 7. Management's Discussion and Analysis of Financial Condition and Results of Operations (MD&A)",
            "Item 7A. Quantitative and Qualitative Disclosures About Market Risk",
            "Item 8. Financial Statements and Supplementary Data",
            "Item 9. Changes in and Disagreements With Accountants on Accounting and Financial Disclosure",
            "Item 9A. Controls and Procedures",
            "Item 9B. Other Information",
            "Item 9C. Disclosure Regarding Foreign Jurisdictions that Prevent Inspections",
            "Item 10. Directors, Executive Officers and Corporate Governance",
            "Item 11. Executive Compensation",
            "Item 12. Security Ownership of Certain Beneficial Owners and Management and Related Stockholder Matters",
            "Item 13. Certain Relationships and Related Transactions, and Director Independence",
            "Item 14. Principal Accountant Fees and Services",
            "Item 15. Exhibits, Financial Statement Schedules",
            "Item 16. Form 10-K Summary"
        ]

    def create_prompt(self, section_content: str, current_category: str) -> str:
        """Create a prompt for Gemini to analyze and restructure the section."""
        
        prompt = f"""
You are an expert in SEC 10-K filing analysis. Please analyze the following 10-K section content and provide the appropriate classification.

CURRENT CATEGORY: {current_category}

SECTION CONTENT:
{section_content[:3000]}{"..." if len(section_content) > 3000 else ""}

Please analyze this content and return ONLY a JSON response with the following structure:
{{
    "part_name": "one of the four valid parts listed below",
    "item_name": "the most appropriate item from the list below",
    "confidence": "high/medium/low"
}}

VALID PARTS (choose exactly one):
- "Part I: Business and Risk Factors"
- "Part II: Financial Information"
- "Part III: Governance" 
- "Part IV: Exhibits and Schedules"

VALID ITEMS (choose the most appropriate one):
{json.dumps(self.valid_items, indent=2)}

Guidelines:
1. Part I typically contains business overview, risk factors, properties, legal proceedings
2. Part II contains financial data, MD&A, financial statements, controls
3. Part III contains governance, directors, compensation, ownership
4. Part IV contains exhibits and schedules

Respond with ONLY the JSON object, no additional text or explanation.
"""
        return prompt

    def process_section(self, section_content: str, current_category: str) -> Dict[str, Any]:
        """Process a single section through Gemini."""
        try:
            prompt = self.create_prompt(section_content, current_category)
            
            # Send to Gemini with retry logic
            for attempt in range(3):
                try:
                    response = self.model.generate_content(prompt)
                    
                    # Parse the JSON response
                    response_text = response.text.strip()
                    
                    # Clean up the response if it has markdown formatting
                    if response_text.startswith('```json'):
                        response_text = response_text.replace('```json', '').replace('```', '').strip()
                    
                    result = json.loads(response_text)
                    
                    # Validate the response
                    if (result.get('part_name') in self.valid_parts and 
                        result.get('item_name') in self.valid_items):
                        return result
                    else:
                        print(f"  Invalid response from Gemini: {result}")
                        continue
                        
                except json.JSONDecodeError as e:
                    print(f"  JSON decode error (attempt {attempt + 1}): {e}")
                    print(f"  Raw response: {response.text[:200]}...")
                    continue
                except Exception as e:
                    print(f"  Gemini API error (attempt {attempt + 1}): {e}")
                    time.sleep(2)  # Wait before retry
                    continue
            
            # If all attempts failed, return default classification
            print(f"  Failed to get valid response, using default classification")
            return self.get_default_classification(current_category)
            
        except Exception as e:
            print(f"  Error processing section: {e}")
            return self.get_default_classification(current_category)

    def get_default_classification(self, current_category: str) -> Dict[str, Any]:
        """Provide default classification based on current category."""
        category_mapping = {
            'business': {
                'part_name': 'Part I: Business and Risk Factors',
                'item_name': 'Item 1. Business',
                'confidence': 'low'
            },
            'risk_factors': {
                'part_name': 'Part I: Business and Risk Factors',
                'item_name': 'Item 1A. Risk Factors',
                'confidence': 'low'
            },
            'properties': {
                'part_name': 'Part I: Business and Risk Factors',
                'item_name': 'Item 2. Properties',
                'confidence': 'low'
            },
            'legal_proceedings': {
                'part_name': 'Part I: Business and Risk Factors',
                'item_name': 'Item 3. Legal Proceedings',
                'confidence': 'low'
            },
            'selected_financial_data': {
                'part_name': 'Part II: Financial Information',
                'item_name': 'Item 6. [Reserved]',
                'confidence': 'low'
            },
            'management_discussion': {
                'part_name': 'Part II: Financial Information',
                'item_name': 'Item 7. Management\'s Discussion and Analysis of Financial Condition and Results of Operations (MD&A)',
                'confidence': 'low'
            },
            'financial_statements': {
                'part_name': 'Part II: Financial Information',
                'item_name': 'Item 8. Financial Statements and Supplementary Data',
                'confidence': 'low'
            },
            'controls_procedures': {
                'part_name': 'Part II: Financial Information',
                'item_name': 'Item 9A. Controls and Procedures',
                'confidence': 'low'
            },
            'directors_officers': {
                'part_name': 'Part III: Governance',
                'item_name': 'Item 10. Directors, Executive Officers and Corporate Governance',
                'confidence': 'low'
            },
            'executive_compensation': {
                'part_name': 'Part III: Governance',
                'item_name': 'Item 11. Executive Compensation',
                'confidence': 'low'
            },
            'exhibits': {
                'part_name': 'Part IV: Exhibits and Schedules',
                'item_name': 'Item 15. Exhibits, Financial Statement Schedules',
                'confidence': 'low'
            }
        }
        
        return category_mapping.get(current_category, {
            'part_name': 'Part I: Business and Risk Factors',
            'item_name': 'Item 1. Business',
            'confidence': 'low'
        })

def process_company_file(processor: GeminiProcessor, input_file: Path, output_file: Path):
    """Process a single company's JSON file."""
    print(f"Processing {input_file.name}...")
    
    try:
        # Load the input file
        with open(input_file, 'r', encoding='utf-8') as f:
            company_data = json.load(f)
        
        company_name = company_data['company_name']
        print(f"  Company: {company_name}")
        
        # Process each year
        for year, year_data in company_data['years_data'].items():
            print(f"  Processing year: {year}")
            
            content = year_data['content']
            
            # Process each part
            for part in content.get('parts', []):
                part_name = part.get('part_name', 'Unknown')
                print(f"    Processing part: {part_name}")
                
                # Process each section in the part
                for section in part.get('sections', []):
                    current_category = section.get('category', 'unknown')
                    section_content = section.get('content', '')
                    
                    print(f"      Processing section: {current_category}")
                    
                    # Skip if no content
                    if not section_content.strip():
                        continue
                    
                    # Process through Gemini
                    gemini_result = processor.process_section(section_content, current_category)
                    
                    # Update the section with Gemini's classification
                    section['gemini_part_name'] = gemini_result['part_name']
                    section['gemini_item_name'] = gemini_result['item_name']
                    section['gemini_confidence'] = gemini_result['confidence']
                    
                    print(f"        → {gemini_result['part_name']} | {gemini_result['item_name']} | {gemini_result['confidence']}")
                    
                    # Small delay to avoid rate limiting
                    time.sleep(1)
        
        # Save the processed file
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(company_data, f, indent=2, ensure_ascii=False)
        
        print(f"  ✅ Completed {company_name}")
        
    except Exception as e:
        print(f"  ❌ Error processing {input_file.name}: {e}")

def main():
    """Main processing function."""
    # Check for API key
    if not os.getenv('GEMINI_API_KEY'):
        print("❌ Please set the GEMINI_API_KEY environment variable")
        print("   You can get an API key from: https://makersuite.google.com/app/apikey")
        return
    
    # Define paths
    input_dir = Path(r"c:\Users\amrit\Desktop\SCALAR-FEILD--TASK-\final_10k")
    output_dir = Path(r"c:\Users\amrit\Desktop\SCALAR-FEILD--TASK-\gemini_10k")
    
    # Create output directory
    output_dir.mkdir(exist_ok=True)
    
    print(f"Input directory: {input_dir}")
    print(f"Output directory: {output_dir}")
    
    # Initialize processor
    processor = GeminiProcessor()
    
    # Find all JSON files (excluding the example file)
    json_files = [f for f in input_dir.glob("*.json") if not f.name.startswith("example")]
    
    if not json_files:
        print("❌ No JSON files found in the input directory")
        return
    
    print(f"Found {len(json_files)} files to process")
    
    # Process each file
    for json_file in json_files:
        output_file = output_dir / json_file.name
        process_company_file(processor, json_file, output_file)
        print()  # Empty line between companies
    
    print(f"🎉 Processing complete! Check the '{output_dir}' directory for results.")

if __name__ == "__main__":
    main()
