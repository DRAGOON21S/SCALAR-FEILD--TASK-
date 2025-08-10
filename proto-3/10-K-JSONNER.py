import os
import json
import google.generativeai as genai
from pathlib import Path
import argparse
import sys
from datetime import datetime

class TenKProcessor:
    def __init__(self, api_key=None):
        """
        Initialize the 10-K processor with Gemini API
        
        Args:
            api_key (str): Google Gemini API key. If None, will look for GEMINI_API_KEY env variable
        """
        if api_key is None:
            api_key = 'AIzaSyCg2t8_IljYhBfFirTGZNtIsarWj8jgxSY'
            if not api_key:
                raise ValueError("API key must be provided either as parameter or GEMINI_API_KEY environment variable")
        
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-2.5-pro')
        
        # System prompt from the artifact we created
        self.system_prompt = """# 10-K Form Financial Data Parser System Prompt

You are an extremely experienced financial analyst and SEC filing expert with over 20 years of experience in analyzing 10-K forms, financial statements, and corporate disclosures. Your expertise includes deep knowledge of SEC regulations, GAAP accounting principles, and corporate financial reporting standards.

## PRIMARY OBJECTIVE
Parse the provided 10-K form document and organize ALL content into a structured JSON format with precise categorization and hierarchical organization.

## DATA CLEANING AND FORMATTING REQUIREMENTS
When processing the document content, apply intelligent formatting improvements to make data more RAG-friendly:

### Text Formatting Rules:
1. **Remove Excessive Whitespace**: Clean up large gaps of spaces while preserving intentional formatting
2. **Fix Broken Text**: Repair text that spans multiple lines awkwardly (e.g., "Plat-\\nforms" → "Platforms")
3. **Standardize Line Breaks**: Use consistent line breaks for readability
4. **Clean Table Formatting**: Improve table structure while preserving all data
5. **Remove Gibberish**: Filter out formatting artifacts (like repeated underscores, random characters)
6. **Preserve All Data**: NEVER remove actual content, dates, numbers, or meaningful text

### Critical Data Preservation:
- **Maintain ALL numerical data**: Keep every number, percentage, date, and financial figure exactly as stated
- **Preserve legal language**: Keep all regulatory terms, disclaimers, and legal phrases intact
- **Retain all names**: Company names, person names, product names must be preserved exactly
- **Keep all references**: File numbers, exhibit numbers, page references, etc.

### Example Transformation:
BEFORE (messy):
```
Class A                                                   \\n  4.1         Common Stock           10-K                   001-35551         4.1    February 3, 2022              \\n              Certificate.                                                      
```

AFTER (cleaned):
```
4.1 Class A Common Stock Certificate - Form 10-K, File No. 001-35551, Exhibit 4.1, dated February 3, 2022
```

### When NOT to Clean:
- If content is already well-formatted and readable, leave it unchanged
- If uncertain whether something is gibberish or meaningful data, preserve it
- Financial statements and tables that are already properly structured

## JSON STRUCTURE REQUIREMENTS

### Mandatory Hierarchy
```json
{
  "{COMPANY_NAME}": {
    "{YEAR}": {
      "FORM": "10-K",
      "CATEGORIES": {
        "Part I: Business and Risk Factors": {
          "items": {}
        },
        "Part II: Financial Information": {
          "items": {}
        },
        "Part III: Governance": {
          "items": {}
        },
        "Part IV: Exhibits and Schedules": {
          "items": {}
        }
      }
    }
  }
}
```

### Category Definitions
Map content ONLY to these four categories:
- **Part I: Business and Risk Factors**
- **Part II: Financial Information** 
- **Part III: Governance**
- **Part IV: Exhibits and Schedules**

### Item Classifications
Extract and organize content under these specific items ONLY:

**Part I Items:**
- Item 1. Business
- Item 1A. Risk Factors
- Item 1B. Unresolved Staff Comments
- Item 2. Properties
- Item 3. Legal Proceedings
- Item 4. Mine Safety Disclosures

**Part II Items:**
- Item 5. Market for Registrant's Common Equity, Related Stockholder Matters and Issuer Purchases of Equity Securities
- Item 6. [Reserved]
- Item 7. Management's Discussion and Analysis of Financial Condition and Results of Operations (MD&A)
- Item 7A. Quantitative and Qualitative Disclosures About Market Risk
- Item 8. Financial Statements and Supplementary Data
- Item 9. Changes in and Disagreements With Accountants on Accounting and Financial Disclosure
- Item 9A. Controls and Procedures
- Item 9B. Other Information
- Item 9C. Disclosure Regarding Foreign Jurisdictions that Prevent Inspections

**Part III Items:**
- Item 10. Directors, Executive Officers and Corporate Governance
- Item 11. Executive Compensation
- Item 12. Security Ownership of Certain Beneficial Owners and Management and Related Stockholder Matters
- Item 13. Certain Relationships and Related Transactions, and Director Independence
- Item 14. Principal Accountant Fees and Services

**Part IV Items:**
- Item 15. Exhibits, Financial Statement Schedules
- Item 16. Form 10-K Summary

## PROCESSING INSTRUCTIONS

### Content Extraction Rules
1. **NO HALLUCINATION**: Include ONLY content that exists in the provided document
2. **INTELLIGENT FORMATTING**: Clean up messy formatting while preserving all data
3. **COMPLETE EXTRACTION**: Capture ALL relevant content from each identified section
4. **ACCURATE MAPPING**: Ensure content is placed under the correct category and item
5. **MAINTAIN STRUCTURE**: Preserve tables, lists, and formatting where possible

### Text Processing Guidelines
- Apply formatting improvements to make content more readable and RAG-friendly
- Clean up excessive whitespace, broken text, and formatting artifacts
- Maintain numerical data exactly as presented (no changes to figures, dates, percentages)
- Preserve financial figures, dates, and percentages without modification
- Retain legal language and regulatory terminology exactly
- Keep section headers and subheaders intact
- Structure tabular data clearly while preserving all information

### Handling Missing Items
- If an item is not present in the document, do not create an entry for it
- If an item is marked as "[Reserved]" or similar, include it with that notation
- If content exists but doesn't clearly map to a specific item, place it in the most appropriate category with a descriptive key

### JSON Formatting Requirements
- Use proper JSON syntax with correct escaping
- Ensure all strings are properly quoted
- Maintain consistent indentation and formatting
- Include all necessary commas and brackets
- Escape special characters appropriately

## OUTPUT SPECIFICATIONS

### Final JSON Structure Example
```json
{
  "APPLE_INC": {
    "2023": {
      "FORM": "10-K",
      "CATEGORIES": {
        "Part I: Business and Risk Factors": {
          "Item 1. Business": {
            "content": "[Full original text from Item 1]",
            "subsections": {
              "General": "[content]",
              "Products": "[content]",
              "Competition": "[content]"
            }
          },
          "Item 1A. Risk Factors": {
            "content": "[Full original text from Item 1A]"
          }
        },
        "Part II: Financial Information": {
          "Item 7. Management's Discussion and Analysis": {
            "content": "[Full MD&A content]",
            "financial_highlights": "[specific data]"
          }
        }
      }
    }
  }
}
```

### Quality Assurance Checklist
Before finalizing output, verify:
- [ ] All content from original document is captured
- [ ] No fabricated or hallucinated information included
- [ ] Proper category and item classification
- [ ] Valid JSON syntax
- [ ] Complete hierarchical structure
- [ ] Original text preservation

## CRITICAL REQUIREMENTS
- **ACCURACY FIRST**: Precision in content extraction is paramount
- **COMPLETE COVERAGE**: Ensure no relevant content is omitted
- **STRICT CATEGORIZATION**: Use only the specified categories and items
- **NO INTERPRETATION**: Present information as-is without analysis or commentary
- **MAINTAIN INTEGRITY**: Preserve the document's original meaning and context

Begin processing the 10-K document and return the complete JSON structure following these specifications exactly.

---
NOTE : ONLY RETURN THE JSON , NO COMMENTS , NO TAG 
## DOCUMENT TO PROCESS:
"""

    def read_text_file(self, file_path):
        """
        Read content from a text file
        
        Args:
            file_path (str): Path to the text file
            
        Returns:
            str: Content of the file
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()
            print(f"✓ Successfully read file: {file_path}")
            print(f"  File size: {len(content):,} characters")
            return content
        except FileNotFoundError:
            raise FileNotFoundError(f"File not found: {file_path}")
        except Exception as e:
            raise Exception(f"Error reading file {file_path}: {str(e)}")

    def process_with_gemini(self, document_content):
        """
        Send document content to Gemini with system prompt
        
        Args:
            document_content (str): Content of the 10-K document
            
        Returns:
            str: Gemini's response
        """
        try:
            # Combine system prompt with document content
            full_prompt = self.system_prompt + "\n\n" + document_content
            
            print("📤 Sending request to Gemini...")
            print(f"  Total prompt length: {len(full_prompt):,} characters")
            
            # Generate response from Gemini
            response = self.model.generate_content(full_prompt)
            
            if response.text:
                print("✓ Received response from Gemini")
                return response.text
            else:
                raise Exception("Empty response received from Gemini")
                
        except Exception as e:
            raise Exception(f"Error processing with Gemini: {str(e)}")

    def save_json_response(self, response_text, output_path):
        """
        Save Gemini response to JSON file
        
        Args:
            response_text (str): Response from Gemini
            output_path (str): Path to save the JSON file
        """
        try:
            # Try to parse as JSON first to validate
            json_data = json.loads(response_text)
            
            # Save with proper formatting
            with open(output_path, 'w', encoding='utf-8') as file:
                json.dump(json_data, file, indent=2, ensure_ascii=False)
            
            print(f"✓ Successfully saved JSON to: {output_path}")
            
        except json.JSONDecodeError as e:
            # If response isn't valid JSON, save as text file with JSON extension
            print(f"⚠️  Response is not valid JSON. Saving as raw text...")
            with open(output_path, 'w', encoding='utf-8') as file:
                file.write(response_text)
            print(f"✓ Saved raw response to: {output_path}")
            
        except Exception as e:
            raise Exception(f"Error saving file {output_path}: {str(e)}")

    def process_tenk_document(self, document_content=None, input_file_path=None, output_file_path=None):
        """
        Complete processing pipeline: process document content OR read file -> process with Gemini -> save JSON
        
        Args:
            document_content (str): Direct 10-K document content (optional)
            input_file_path (str): Path to input 10-K text file (optional)
            output_file_path (str): Path to output JSON file (optional)
            
        Returns:
            str: Path to the output file
            
        Note: Either document_content OR input_file_path must be provided
        """
        if document_content is None and input_file_path is None:
            raise ValueError("Either document_content or input_file_path must be provided")
        
        if document_content is not None and input_file_path is not None:
            raise ValueError("Provide either document_content OR input_file_path, not both")
        
        # Generate output filename if not provided
        if output_file_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            if input_file_path:
                input_path = Path(input_file_path)
                output_file_path = f"{input_path.stem}_processed_{timestamp}.json"
            else:
                output_file_path = f"tenk_processed_{timestamp}.json"
        
        print(f"🚀 Starting 10-K processing pipeline...")
        if input_file_path:
            print(f"  Input file: {input_file_path}")
        else:
            print(f"  Input: Direct document content ({len(document_content):,} characters)")
        print(f"  Output file: {output_file_path}")
        
        try:
            # Step 1: Get document content (either from file or direct input)
            if document_content is None:
                document_content = self.read_text_file(input_file_path)
            else:
                print(f"✓ Using provided document content ({len(document_content):,} characters)")
            
            # Step 2: Process with Gemini
            gemini_response = self.process_with_gemini(document_content)
            
            # Step 3: Save JSON response
            self.save_json_response(gemini_response, output_file_path)
            
            print(f"🎉 Processing completed successfully!")
            return output_file_path
            
        except Exception as e:
            print(f"❌ Error during processing: {str(e)}")
            raise

    def process_tenk_file(self, input_file_path, output_file_path=None):
        """
        Legacy method for backward compatibility - processes from file path
        
        Args:
            input_file_path (str): Path to input 10-K text file
            output_file_path (str): Path to output JSON file (optional)
            
        Returns:
            str: Path to the output file
        """
        return self.process_tenk_document(input_file_path=input_file_path, output_file_path=output_file_path)


def main():
    """
    Command line interface for the 10-K processor
    """
    parser = argparse.ArgumentParser(description='Process 10-K forms using Google Gemini')
    parser.add_argument('input_file', nargs='?', help='Path to the 10-K text file (optional if using --content)')
    parser.add_argument('-c', '--content', help='Direct document content as string')
    parser.add_argument('-o', '--output', help='Output JSON file path (optional)')
    parser.add_argument('-k', '--api-key', help='Google Gemini API key (optional if set in environment)')
    
    args = parser.parse_args()
    
    # Validate input arguments
    if not args.input_file and not args.content:
        parser.error("Either input_file or --content must be provided")
    
    if args.input_file and args.content:
        parser.error("Provide either input_file OR --content, not both")
    
    try:
        # Initialize processor
        processor = TenKProcessor(api_key=args.api_key)
        
        # Process the document
        if args.content:
            output_path = processor.process_tenk_document(
                document_content=args.content, 
                output_file_path=args.output
            )
        else:
            output_path = processor.process_tenk_document(
                input_file_path=args.input_file, 
                output_file_path=args.output
            )
        
        print(f"\n✅ Success! Processed file saved to: {output_path}")
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()


# Alternative usage as a module:
"""
# Example usage in other scripts:
from tenk_processor import TenKProcessor

# Initialize with API key
processor = TenKProcessor(api_key="your_gemini_api_key")

# Or use environment variable GEMINI_API_KEY
processor = TenKProcessor()

# Method 1: Process from file path
output_file = processor.process_tenk_document(input_file_path="path/to/10k_document.txt", output_file_path="output.json")

# Method 2: Process direct document content
document_text = "Your 10-K document content here..."
output_file = processor.process_tenk_document(document_content=document_text, output_file_path="output.json")

# Method 3: Legacy file processing (backward compatibility)
output_file = processor.process_tenk_file("path/to/10k_document.txt", "output.json")
"""