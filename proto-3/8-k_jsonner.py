import google.generativeai as genai
import json
import os
import sys
import argparse
from pathlib import Path
import time
from datetime import datetime

class FinancialDataProcessor:
    def __init__(self, api_key):
        """Initialize the processor with Google Gemini API key"""
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-2.5-pro')
        
        # System prompt for financial data organization
        self.system_prompt = """# System Prompt: 8-K Financial Data Organization Expert

You are an extremely experienced and detail-oriented financial analyst with decades of expertise in SEC filings, particularly 8-K forms. Your task is to organize unstructured 8-K financial data into a precise, hierarchical JSON structure.

## Core Instructions

### Role & Expertise
- Act as a senior financial analyst with comprehensive knowledge of SEC reporting requirements
- Apply deep understanding of 8-K form structure, content, and regulatory compliance
- Demonstrate expertise in financial terminology, accounting principles, and corporate disclosure requirements

### Primary Objective
Transform the provided unstructured 8-K financial data into a well-organized JSON structure following the exact hierarchy and categorization requirements specified below.

## JSON Structure Requirements

### Hierarchy
The JSON must follow this exact structure:
```json
{
  "COMPANY_NAME": {
    "YEAR": {
      "FORM": "8-K",
      "CATEGORIES": {
        "CATEGORY_NAME": {
          "ITEMS": {
            "ITEM_CODE": {
              "content": "actual_text_from_document",
              "subsections": {
                "subsection_name": "subsection_content"
              }
            }
          }
        }
      }
    }
  }
}
```

### Mandatory Categories (Use ONLY these)
You must categorize content using ONLY these predefined categories:

1. "Section 1 - Registrant's Business and Operations"
2. "Section 2 - Financial Information" 
3. "Section 3 - Securities and Trading Markets"
4. "Section 4 - Matters Related to Accountants and Financial Statements"
5. "Section 5 - Corporate Governance and Management"
6. "Section 6 - Asset-Backed Securities"
7. "Section 7 - Regulation FD"
8. "Section 8 - Other Events"
9. "Section 9 - Financial Statements and Exhibits"

### Mandatory Items (Use ONLY these)
Map content to the appropriate items from this exhaustive list:

**Section 1 Items:**
- "Item 1.01 - Entry into a Material Definitive Agreement"
- "Item 1.02 - Termination of a Material Definitive Agreement"
- "Item 1.03 - Bankruptcy or Receivership"
- "Item 1.04 - Mine Safety - Reporting of Shutdowns and Patterns of Violations"
- "Item 1.05 - Material Cybersecurity Incidents"

**Section 2 Items:**
- "Item 2.01 - Completion of Acquisition or Disposition of Assets"
- "Item 2.02 - Results of Operations and Financial Condition"
- "Item 2.03 - Creation of a Direct Financial Obligation or an Obligation under an Off-Balance Sheet Arrangement of a Registrant"
- "Item 2.04 - Triggering Events That Accelerate or Increase a Direct Financial Obligation or an Obligation under an Off-Balance Sheet Arrangement"
- "Item 2.05 - Costs Associated with Exit or Disposal Activities"
- "Item 2.06 - Material Impairments"

**Section 3 Items:**
- "Item 3.01 - Notice of Delisting or Failure to Satisfy a Continued Listing Rule or Standard; Transfer of Listing"
- "Item 3.02 - Unregistered Sales of Equity Securities"
- "Item 3.03 - Material Modification to Rights of Security Holders"

**Section 4 Items:**
- "Item 4.01 - Changes in Registrant's Certifying Accountant"
- "Item 4.02 - Non-Reliance on Previously Issued Financial Statements or a Related Audit Report or Completed Interim Review"

**Section 5 Items:**
- "Item 5.01 - Changes in Control of Registrant"
- "Item 5.02 - Departure of Directors or Certain Officers; Election of Directors; Appointment of Certain Officers; Compensatory Arrangements of Certain Officers"
- "Item 5.03 - Amendments to Articles of Incorporation or Bylaws; Change in Fiscal Year"
- "Item 5.04 - Temporary Suspension of Trading Under Registrant's Employee Benefit Plans"
- "Item 5.05 - Amendment to Registrant's Code of Ethics, or Waiver of a Provision of the Code of Ethics"
- "Item 5.06 - Change in Shell Company Status"
- "Item 5.07 - Submission of Matters to a Vote of Security Holders"
- "Item 5.08 - Shareholder Director Nominations"

**Section 6 Items:**
- "Item 6.01 - ABS Informational and Computational Material"
- "Item 6.02 - Change of Servicer or Trustee"
- "Item 6.03 - Change in Credit Enhancement or Other External Support"
- "Item 6.04 - Failure to Make a Required Distribution"
- "Item 6.05 - Securities Act Updating Disclosure"

**Section 7 Items:**
- "Item 7.01 - Regulation FD Disclosure"

**Section 8 Items:**
- "Item 8.01 - Other Events"

**Section 9 Items:**
- "Item 9.01 - Financial Statements and Exhibits"

## Critical Processing Rules

### Data Integrity
1. **NO HALLUCINATION**: Include ONLY information explicitly present in the source document
2. **NO FABRICATION**: Do not create, infer, or add any data not found in the original text
3. **PRESERVE ACCURACY**: Maintain the factual integrity of all financial figures, dates, and disclosures

### Content Processing
1. **Minimal Rephrasing**: Keep original text largely intact; only make minor edits for clarity and readability
2. **Logical Segmentation**: Break content into logical subsections when appropriate
3. **Preserve Context**: Maintain the relationship between related pieces of information
4. **Include All Relevant Data**: Capture all pertinent information from each section

### Categorization Logic
1. **Precise Mapping**: Map each piece of content to the most appropriate category and item
2. **Single Assignment**: Each piece of content should appear in only one location unless it genuinely relates to multiple items
3. **Comprehensive Coverage**: Ensure all substantive content from the 8-K is included in the JSON

### Text Formatting
1. **Clean Structure**: Remove excessive formatting while preserving meaning
2. **Maintain Readability**: Ensure text flows logically and is easy to understand
3. **Preserve Financial Data**: Keep all numerical data, percentages, dates, and financial figures exactly as stated

## Quality Assurance Checklist

Before finalizing the JSON, verify:
- [ ] All categories used are from the approved list
- [ ] All items used are from the approved list  
- [ ] No information has been hallucinated or fabricated
- [ ] All significant content from the source document is included
- [ ] JSON structure follows the exact hierarchy specified
- [ ] Financial figures and dates are preserved accurately
- [ ] Text is appropriately segmented and readable

## Output Format

Return ONLY the complete JSON structure with no additional commentary, explanations, or text outside the JSON. The JSON should be properly formatted, valid, and ready for immediate use.

## Final Reminder

You are processing sensitive financial regulatory data. Accuracy, completeness, and adherence to the specified structure are paramount. Do not take creative liberties with the content or structure."""

    def read_file(self, file_path):
        """Read the content of the text file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()
            print(f"✓ Successfully read file: {file_path}")
            print(f"  File size: {len(content)} characters")
            return content
        except FileNotFoundError:
            raise FileNotFoundError(f"File not found: {file_path}")
        except Exception as e:
            raise Exception(f"Error reading file: {str(e)}")

    def clean_json_response(self, response_text):
        """Clean and extract JSON from the response"""
        # Remove markdown code blocks if present
        if '```json' in response_text:
            start = response_text.find('```json') + 7
            end = response_text.find('```', start)
            response_text = response_text[start:end].strip()
        elif '```' in response_text:
            start = response_text.find('```') + 3
            end = response_text.rfind('```')
            response_text = response_text[start:end].strip()
        
        # Try to find JSON content if there's additional text
        try:
            # Look for the first { and last }
            start_brace = response_text.find('{')
            end_brace = response_text.rfind('}')
            if start_brace != -1 and end_brace != -1:
                json_content = response_text[start_brace:end_brace + 1]
                return json_content
        except:
            pass
        
        return response_text.strip()

    def process_with_gemini(self, file_content):
        """Send content to Gemini and get structured JSON response"""
        try:
            # Combine system prompt with the file content
            full_prompt = f"{self.system_prompt}\n\n---\n\n8-K FINANCIAL DATA TO PROCESS:\n\n{file_content}"
            
            print("🔄 Sending data to Google Gemini...")
            print(f"  Prompt length: {len(full_prompt)} characters")
            
            # Generate response with Gemini
            response = self.model.generate_content(
                full_prompt,
                generation_config={
                    'temperature': 0.1,
                    'top_p': 0.8,
                    'top_k': 40,
                    'max_output_tokens': 8192,
                }
            )
            
            print("✓ Received response from Gemini")
            return response.text
            
        except Exception as e:
            raise Exception(f"Error processing with Gemini: {str(e)}")

    def save_json(self, json_data, output_file):
        """Save the structured data to a JSON file"""
        try:
            # Clean the response to extract JSON
            cleaned_json = self.clean_json_response(json_data)
            
            # Parse JSON to validate it
            parsed_data = json.loads(cleaned_json)
            
            # Save to file with proper formatting
            with open(output_file, 'w', encoding='utf-8') as file:
                json.dump(parsed_data, file, indent=2, ensure_ascii=False)
            
            print(f"✓ Successfully saved structured data to: {output_file}")
            return parsed_data
            
        except json.JSONDecodeError as e:
            print(f"❌ Error: Invalid JSON response from Gemini")
            print(f"JSONDecodeError: {str(e)}")
            # Save raw response for debugging
            debug_file = output_file.replace('.json', '_raw_response.txt')
            with open(debug_file, 'w', encoding='utf-8') as file:
                file.write(json_data)
            print(f"Raw response saved to: {debug_file}")
            raise
        except Exception as e:
            raise Exception(f"Error saving JSON: {str(e)}")

    def process_file(self, input_file_path, output_file_path=None):
        """Main method to process the entire workflow"""
        try:
            # Generate output filename if not provided
            if output_file_path is None:
                input_path = Path(input_file_path)
                output_file_path = input_path.parent / f"{input_path.stem}_structured.json"
            
            print("🚀 Starting 8-K Financial Data Processing...")
            print(f"  Input file: {input_file_path}")
            print(f"  Output file: {output_file_path}")
            print("-" * 50)
            
            # Step 1: Read the input file
            file_content = self.read_file(input_file_path)
            
            # Step 2: Process with Gemini
            gemini_response = self.process_with_gemini(file_content)
            
            # Step 3: Save structured JSON
            structured_data = self.save_json(gemini_response, output_file_path)
            
            print("-" * 50)
            print("🎉 Processing completed successfully!")
            print(f"📊 Structured data contains {len(str(structured_data))} characters")
            
            return output_file_path
            
        except Exception as e:
            print(f"❌ Processing failed: {str(e)}")
            raise

    def process_content(self, document_content, output_file_path=None):
        """Process 8-K content directly without reading from file"""
        try:
            # Generate output filename if not provided
            if output_file_path is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_file_path = f"8k_processed_{timestamp}.json"
            
            print("🚀 Starting 8-K Financial Data Processing...")
            print(f"  Input: Direct document content ({len(document_content):,} characters)")
            print(f"  Output file: {output_file_path}")
            print("-" * 50)
            
            # Step 1: Process with Gemini
            gemini_response = self.process_with_gemini(document_content)
            
            # Step 2: Save structured JSON
            structured_data = self.save_json(gemini_response, output_file_path)
            
            print("-" * 50)
            print("🎉 Processing completed successfully!")
            print(f"📊 Structured data contains {len(str(structured_data))} characters")
            
            return output_file_path
            
        except Exception as e:
            print(f"❌ Processing failed: {str(e)}")
            raise

def main():
    """
    Command line interface for the 8-K processor
    """
    import argparse
    
    parser = argparse.ArgumentParser(description='Process 8-K forms using Google Gemini')
    parser.add_argument('input_file', nargs='?', help='Path to the 8-K text file (optional if using --content)')
    parser.add_argument('-c', '--content', help='Direct document content as string')
    parser.add_argument('-o', '--output', help='Output JSON file path (optional)')
    parser.add_argument('-k', '--api-key', help='Google Gemini API key (optional if using default in script)')
    
    args = parser.parse_args()
    
    # Validate input arguments
    if not args.input_file and not args.content:
        parser.error("Either input_file or --content must be provided")
    
    if args.input_file and args.content:
        parser.error("Provide either input_file OR --content, not both")
    
    try:
        # Use provided API key or default
        api_key = args.api_key if args.api_key else "AIzaSyCg2t8_IljYhBfFirTGZNtIsarWj8jgxSY"
        
        # Initialize processor
        processor = FinancialDataProcessor(api_key)
        
        # Process the document
        if args.content:
            output_path = processor.process_content(
                document_content=args.content, 
                output_file_path=args.output
            )
        else:
            output_path = processor.process_file(args.input_file, args.output)
        
        print(f"\n✅ Success! Processed file saved to: {output_path}")
        
        # Try to load and show summary of processed data
        try:
            import json
            with open(output_path, 'r', encoding='utf-8') as f:
                result = json.load(f)
            
            print("\n📋 Processing Summary:")
            if isinstance(result, dict):
                for company in result.keys():
                    print(f"  Company: {company}")
                    for year in result[company].keys():
                        print(f"  Year: {year}")
                        if 'CATEGORIES' in result[company][year]:
                            categories = list(result[company][year]['CATEGORIES'].keys())
                            print(f"  Categories found: {len(categories)}")
                            for cat in categories:
                                print(f"    - {cat}")
        except Exception as e:
            print(f"Note: Could not load summary from output file: {str(e)}")
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import sys
        sys.exit(1)
        
        print("\n📋 Processing Summary:")
        if isinstance(result, dict):
            for company in result.keys():
                print(f"  Company: {company}")
                for year in result[company].keys():
                    print(f"  Year: {year}")
                    if 'CATEGORIES' in result[company][year]:
                        categories = list(result[company][year]['CATEGORIES'].keys())
                        print(f"  Categories found: {len(categories)}")
                        for cat in categories:
                            print(f"    - {cat}")
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import sys
        sys.exit(1)

# Example usage function
def process_financial_data(api_key, input_file_path, output_file_path=None):
    """Convenient function to process financial data"""
    processor = FinancialDataProcessor(api_key)
    return processor.process_file(input_file_path, output_file_path)

if __name__ == "__main__":
    main()


# Alternative usage as a module:
"""
# Example usage in other scripts:
from "8-K-JSONNER" import FinancialDataProcessor

# Initialize with API key
processor = FinancialDataProcessor(api_key="your_gemini_api_key")

# Method 1: Process from file path
output_file = processor.process_file("path/to/8k_document.txt", "output.json")

# Method 2: Process direct document content
document_text = "Your 8-K document content here..."
output_file = processor.process_content(document_text, "output.json")

# Method 3: Using the convenience function
from "8-K-JSONNER" import process_financial_data
result = process_financial_data("your_api_key", "input_file.txt", "output.json")
"""