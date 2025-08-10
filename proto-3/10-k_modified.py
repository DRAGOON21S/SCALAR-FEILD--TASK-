import os
import json
import google.generativeai as genai
from pathlib import Path
import argparse
import sys
from datetime import datetime
import re

class TenKProcessor:
    def __init__(self, api_key=None, max_tokens_per_chunk=800000):
        """
        Initialize the 10-K processor with Gemini API
        
        Args:
            api_key (str): Google Gemini API key. If None, will look for GEMINI_API_KEY env variable
            max_tokens_per_chunk (int): Maximum tokens per chunk for processing
        """
        if api_key is None:
            api_key = 'AIzaSyCg2t8_IljYhBfFirTGZNtIsarWj8jgxSY'
            if not api_key:
                raise ValueError("API key must be provided either as parameter or GEMINI_API_KEY environment variable")
        
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-2.5-pro')
        self.max_tokens_per_chunk = max_tokens_per_chunk
        
        # 10-K section patterns for extraction
        self.section_patterns = {
            'Item 1': r'Item\s+1\.?\s+Business',
            'Item 1A': r'Item\s+1A\.?\s+Risk\s+Factors',
            'Item 1B': r'Item\s+1B\.?\s+Unresolved\s+Staff\s+Comments',
            'Item 2': r'Item\s+2\.?\s+Properties',
            'Item 3': r'Item\s+3\.?\s+Legal\s+Proceedings',
            'Item 4': r'Item\s+4\.?\s+Mine\s+Safety\s+Disclosures',
            'Item 5': r'Item\s+5\.?\s+Market\s+for\s+Registrant',
            'Item 6': r'Item\s+6\.?\s+\[?Reserved\]?',
            'Item 7': r'Item\s+7\.?\s+Management\'s\s+Discussion\s+and\s+Analysis',
            'Item 7A': r'Item\s+7A\.?\s+Quantitative\s+and\s+Qualitative\s+Disclosures',
            'Item 8': r'Item\s+8\.?\s+Financial\s+Statements',
            'Item 9': r'Item\s+9\.?\s+Changes\s+in\s+and\s+Disagreements',
            'Item 9A': r'Item\s+9A\.?\s+Controls\s+and\s+Procedures',
            'Item 9B': r'Item\s+9B\.?\s+Other\s+Information',
            'Item 9C': r'Item\s+9C\.?\s+Disclosure\s+Regarding\s+Foreign',
            'Item 10': r'Item\s+10\.?\s+Directors',
            'Item 11': r'Item\s+11\.?\s+Executive\s+Compensation',
            'Item 12': r'Item\s+12\.?\s+Security\s+Ownership',
            'Item 13': r'Item\s+13\.?\s+Certain\s+Relationships',
            'Item 14': r'Item\s+14\.?\s+Principal\s+Accountant',
            'Item 15': r'Item\s+15\.?\s+Exhibits',
            'Item 16': r'Item\s+16\.?\s+Form\s+10-K\s+Summary'
        }
        
        # Mapping sections to categories
        self.section_to_category = {
            'Item 1': 'Part I: Business and Risk Factors',
            'Item 1A': 'Part I: Business and Risk Factors',
            'Item 1B': 'Part I: Business and Risk Factors',
            'Item 2': 'Part I: Business and Risk Factors',
            'Item 3': 'Part I: Business and Risk Factors',
            'Item 4': 'Part I: Business and Risk Factors',
            'Item 5': 'Part II: Financial Information',
            'Item 6': 'Part II: Financial Information',
            'Item 7': 'Part II: Financial Information',
            'Item 7A': 'Part II: Financial Information',
            'Item 8': 'Part II: Financial Information',
            'Item 9': 'Part II: Financial Information',
            'Item 9A': 'Part II: Financial Information',
            'Item 9B': 'Part II: Financial Information',
            'Item 9C': 'Part II: Financial Information',
            'Item 10': 'Part III: Governance',
            'Item 11': 'Part III: Governance',
            'Item 12': 'Part III: Governance',
            'Item 13': 'Part III: Governance',
            'Item 14': 'Part III: Governance',
            'Item 15': 'Part IV: Exhibits and Schedules',
            'Item 16': 'Part IV: Exhibits and Schedules'
        }
        
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

    def estimate_token_count(self, text):
        """
        Estimate token count for text (rough approximation)
        
        Args:
            text (str): Text to count tokens for
            
        Returns:
            int: Estimated token count
        """
        # Rough approximation: 1 token ≈ 4 characters for English text
        return len(text) // 4

    def extract_company_info(self, document_content):
        """
        Extract company name and year from document
        
        Args:
            document_content (str): Full document content
            
        Returns:
            tuple: (company_name, year)
        """
        company_name = "COMPANY_NAME"
        year = "YEAR"
        
        # Try to extract company name - improved patterns
        company_patterns = [
            r'^\s*([A-Za-z][A-Za-z0-9\s&\.,\-]+(?:Inc\.?|Corp\.?|Corporation|Company|LLC|Ltd\.?))\s*$',
            r'COMPANY\s+NAME:\s*(.+?)(?:\n|$)',
            r'REGISTRANT:\s*(.+?)(?:\n|$)',
            r'^\s*(.+?)\s*\(Exact\s+name\s+of\s+[Rr]egistrant',
            r'FORM\s+10-K.*?(?:FOR|OF)\s+(.+?)(?:\n|COMMISSION)',
            r'^\s*(Meta\s+Platforms,?\s+Inc\.?)\s*$',  # Specific for Meta
            r'^\s*(Apple\s+Inc\.?)\s*$',  # Specific for Apple
            r'Commission\s+File\s+Number:.*?\n.*?\n.*?([A-Za-z][A-Za-z0-9\s&\.,\-]+(?:Inc\.?|Corp\.?|Corporation|Company|LLC|Ltd\.?))\s*(?:\n|$)'
        ]
        
        for pattern in company_patterns:
            matches = re.finditer(pattern, document_content[:5000], re.IGNORECASE | re.MULTILINE)
            for match in matches:
                candidate = match.group(1).strip()
                # Skip if too short or contains unwanted text
                if (len(candidate) > 5 and 
                    not re.search(r'(SECURITIES|EXCHANGE|COMMISSION|WASHINGTON|FORM|PURSUANT|UNITED\s+STATES)', candidate, re.IGNORECASE)):
                    company_name = candidate
                    # Clean up company name but preserve important parts
                    company_name = re.sub(r'\s+', ' ', company_name)  # Normalize spaces
                    company_name = company_name.replace(' ', '_').replace(',', '').replace('.', '')
                    print(f"  Found company name: {company_name}")
                    break
            if company_name != "COMPANY_NAME":
                break
        
        # Try to extract year - improved patterns
        year_patterns = [
            r'FOR\s+THE\s+FISCAL\s+YEAR\s+ENDED.*?(\d{4})',
            r'For\s+the\s+fiscal\s+year\s+ended.*?(\d{4})',
            r'FORM\s+10-K.*?(\d{4})',
            r'December\s+31,\s+(\d{4})',  # Common fiscal year end
            r'YEAR\s+ENDED.*?(\d{4})'
        ]
        
        for pattern in year_patterns:
            match = re.search(pattern, document_content[:3000], re.IGNORECASE)
            if match:
                year = match.group(1)
                print(f"  Found year: {year}")
                break
        
        return company_name, year

    def detect_section_boundaries(self, document_content):
        """
        Dynamically detect section boundaries using multiple strategies
        
        Args:
            document_content (str): Full 10-K document content
            
        Returns:
            list: List of section boundaries with positions and metadata
        """
        print("🔍 Detecting section boundaries dynamically...")
        
        boundaries = []
        
        # Multiple detection strategies for different formatting styles
        strategies = [
            # Strategy 1: Boxed headers (like Microsoft format)
            {
                'name': 'boxed_headers',
                'pattern': r'[│┃║]\s*ITEM\s+(\d+[A-C]?)\.\s*([^│┃║\n]+?)\s*[│┃║]',
                'confidence': 0.9
            },
            # Strategy 2: Bold/uppercase headers
            {
                'name': 'bold_headers', 
                'pattern': r'(?:^|\n)\s*ITEM\s+(\d+[A-C]?)\.\s*([A-Z][A-Z\s,\'\-]+?)(?:\s*\n|$)',
                'confidence': 0.8
            },
            # Strategy 3: Standard formatted headers
            {
                'name': 'standard_headers',
                'pattern': r'(?:^|\n)\s*Item\s+(\d+[A-C]?)\.\s*([A-Z][A-Za-z\s,\'\-]+?)(?:\s*\n|$)',
                'confidence': 0.7
            },
            # Strategy 4: Table of contents entries
            {
                'name': 'toc_entries',
                'pattern': r'(?:^|\n)\s*Item\s+(\d+[A-C]?)\.\s*([A-Za-z][A-Za-z\s,\'\-]+?)\s+(\d+)\s*(?:\n|$)',
                'confidence': 0.6
            },
            # Strategy 5: Part headers
            {
                'name': 'part_headers',
                'pattern': r'(?:^|\n)\s*(?:PART\s+[IVX]+|Part\s+[IVX]+)\s*(?:\n|$)',
                'confidence': 0.5
            }
        ]
        
        # Apply each strategy
        for strategy in strategies:
            pattern = strategy['pattern']
            confidence = strategy['confidence']
            
            matches = list(re.finditer(pattern, document_content, re.IGNORECASE | re.MULTILINE))
            
            for match in matches:
                if strategy['name'] == 'part_headers':
                    # Part headers don't have item numbers
                    item_num = None
                    title = match.group().strip()
                else:
                    try:
                        item_num = match.group(1)
                        title = match.group(2).strip()
                    except:
                        continue
                
                boundaries.append({
                    'strategy': strategy['name'],
                    'confidence': confidence,
                    'position': match.start(),
                    'end_position': match.end(),
                    'item_number': item_num,
                    'title': title,
                    'full_match': match.group(),
                    'context_before': document_content[max(0, match.start()-100):match.start()],
                    'context_after': document_content[match.end():match.end()+100]
                })
        
        # Sort by position and remove duplicates with improved logic
        boundaries.sort(key=lambda x: x['position'])
        
        # Remove duplicates with improved filtering
        filtered_boundaries = []
        seen_items = {}  # Track best boundary for each item
        
        for boundary in boundaries:
            if boundary['item_number']:
                # For items with numbers, use the item number as key
                boundary_key = boundary['item_number']
                
                # If we haven't seen this item, or this one has higher confidence, keep it
                if (boundary_key not in seen_items or 
                    boundary['confidence'] > seen_items[boundary_key]['confidence']):
                    # Remove old entry if exists
                    if boundary_key in seen_items:
                        filtered_boundaries.remove(seen_items[boundary_key])
                    
                    # Add new entry
                    filtered_boundaries.append(boundary)
                    seen_items[boundary_key] = boundary
                    
            else:
                # For PART headers, be more selective
                part_title = boundary['title'].strip().upper()
                
                # Only keep first occurrence of each PART with content
                if part_title not in seen_items:
                    # Additional filter: only keep if it has substantial content after it
                    next_content = document_content[boundary['position']:boundary['position']+1000]
                    
                    # Check if this PART header is followed by actual content
                    has_content = len(re.sub(r'[│┃║\s\n\-=_]', '', next_content)) > 100
                    
                    if has_content:
                        filtered_boundaries.append(boundary)
                        seen_items[part_title] = boundary
        
        # Final sorting by document position (not confidence)
        filtered_boundaries.sort(key=lambda x: x['position'])
        
        # Additional filtering: remove sections that are too close together (likely duplicates)
        final_boundaries = []
        for boundary in filtered_boundaries:
            is_too_close = False
            for existing in final_boundaries:
                if abs(boundary['position'] - existing['position']) < 200:  # Within 200 characters
                    is_too_close = True
                    break
            
            if not is_too_close:
                final_boundaries.append(boundary)
        
        filtered_boundaries = final_boundaries
        
        print(f"📋 Found {len(filtered_boundaries)} potential section boundaries")
        for boundary in filtered_boundaries[:10]:  # Show first 10
            print(f"  {boundary['item_number'] or 'PART'}: {boundary['title'][:50]}... (confidence: {boundary['confidence']}) at pos {boundary['position']}")
        
        return filtered_boundaries

    def create_processing_chunks(self, document_content, boundaries, max_input_tokens=750000, max_output_tokens=8000):
        """
        Create processing chunks that respect token limits and section boundaries
        
        Args:
            document_content (str): Full document content
            boundaries (list): Section boundaries from detect_section_boundaries
            max_input_tokens (int): Maximum input tokens per request
            max_output_tokens (int): Maximum expected output tokens per request
            
        Returns:
            list: List of processing chunks with metadata
        """
        print("📦 Creating processing chunks with token monitoring...")
        
        chunks = []
        current_chunk = {
            'start_pos': 0,
            'end_pos': 0,
            'sections': [],
            'estimated_input_tokens': 0,
            'estimated_output_tokens': 0
        }
        
        # Reserve tokens for system prompt
        system_prompt_tokens = self.estimate_token_count(self.system_prompt) if hasattr(self, 'system_prompt') else 2000
        available_tokens = max_input_tokens - system_prompt_tokens - 1000  # 1000 buffer
        
        print(f"  System prompt tokens: {system_prompt_tokens:,}")
        print(f"  Available tokens per chunk: {available_tokens:,}")
        
        for i, boundary in enumerate(boundaries):
            # Calculate section content
            next_boundary_pos = boundaries[i + 1]['position'] if i + 1 < len(boundaries) else len(document_content)
            section_content = document_content[boundary['position']:next_boundary_pos]
            section_tokens = self.estimate_token_count(section_content)
            
            # Estimate output tokens (rough approximation: 10% of input for structured JSON)
            estimated_output = section_tokens * 0.1
            
            # Special handling for very large sections
            if section_tokens > available_tokens * 0.8:  # If section is more than 80% of available tokens
                print(f"    ⚠️ Large section detected: Item {boundary['item_number']} ({section_tokens:,} tokens)")
                
                # Finalize current chunk if it has content
                if current_chunk['sections']:
                    current_chunk['end_pos'] = boundary['position']
                    chunks.append(current_chunk)
                    print(f"    Chunk {len(chunks)}: {len(current_chunk['sections'])} sections, "
                          f"{current_chunk['estimated_input_tokens']:,} input tokens")
                
                # Create dedicated chunk for large section
                large_section_chunk = {
                    'start_pos': boundary['position'],
                    'end_pos': next_boundary_pos,
                    'sections': [{
                        'item_number': boundary['item_number'],
                        'title': boundary['title'] + ' [LARGE SECTION]',
                        'position': boundary['position'],
                        'end_position': next_boundary_pos,
                        'estimated_tokens': section_tokens,
                        'confidence': boundary['confidence']
                    }],
                    'estimated_input_tokens': section_tokens,
                    'estimated_output_tokens': estimated_output
                }
                
                chunks.append(large_section_chunk)
                print(f"    Chunk {len(chunks)}: 1 large section ({section_tokens:,} tokens)")
                
                # Start new chunk
                current_chunk = {
                    'start_pos': next_boundary_pos,
                    'end_pos': 0,
                    'sections': [],
                    'estimated_input_tokens': 0,
                    'estimated_output_tokens': 0
                }
                continue
            
            # Check if adding this section would exceed limits
            would_exceed_input = (current_chunk['estimated_input_tokens'] + section_tokens) > available_tokens
            would_exceed_output = (current_chunk['estimated_output_tokens'] + estimated_output) > max_output_tokens
            
            if would_exceed_input or would_exceed_output:
                # Finalize current chunk if it has content
                if current_chunk['sections']:
                    current_chunk['end_pos'] = boundary['position']
                    chunks.append(current_chunk)
                    print(f"    Chunk {len(chunks)}: {len(current_chunk['sections'])} sections, "
                          f"{current_chunk['estimated_input_tokens']:,} input tokens, "
                          f"{current_chunk['estimated_output_tokens']:.0f} estimated output tokens")
                
                # Start new chunk
                current_chunk = {
                    'start_pos': boundary['position'],
                    'end_pos': 0,
                    'sections': [],
                    'estimated_input_tokens': 0,
                    'estimated_output_tokens': 0
                }
            
            # Add section to current chunk
            current_chunk['sections'].append({
                'item_number': boundary['item_number'],
                'title': boundary['title'],
                'position': boundary['position'],
                'end_position': next_boundary_pos,
                'estimated_tokens': section_tokens,
                'confidence': boundary['confidence']
            })
            
            current_chunk['estimated_input_tokens'] += section_tokens
            current_chunk['estimated_output_tokens'] += estimated_output
        
        # Add final chunk
        if current_chunk['sections']:
            current_chunk['end_pos'] = len(document_content)
            chunks.append(current_chunk)
            print(f"    Chunk {len(chunks)}: {len(current_chunk['sections'])} sections, "
                  f"{current_chunk['estimated_input_tokens']:,} input tokens, "
                  f"{current_chunk['estimated_output_tokens']:.0f} estimated output tokens")
        
        print(f"📊 Created {len(chunks)} processing chunks")
        return chunks

    def extract_sections_dynamic(self, document_content):
        """
        Dynamic section extraction that works across different 10-K formats
        
        Args:
            document_content (str): Full 10-K document content
            
        Returns:
            list: List of processing chunks ready for Gemini
        """
        # Step 1: Detect section boundaries dynamically
        boundaries = self.detect_section_boundaries(document_content)
        
        if not boundaries:
            print("⚠️ No section boundaries found, will process as single document")
            return [{
                'content': document_content,
                'sections': [{'item_number': 'ALL', 'title': 'Complete Document'}],
                'chunk_id': 1
            }]
        
        # Step 2: Create processing chunks
        chunks = self.create_processing_chunks(document_content, boundaries)
        
        # Step 3: Extract actual content for each chunk
        processing_chunks = []
        for i, chunk in enumerate(chunks):
            chunk_content = document_content[chunk['start_pos']:chunk['end_pos']]
            
            processing_chunks.append({
                'chunk_id': i + 1,
                'content': chunk_content,
                'sections': chunk['sections'],
                'estimated_input_tokens': chunk['estimated_input_tokens'],
                'estimated_output_tokens': chunk['estimated_output_tokens'],
                'start_pos': chunk['start_pos'],
                'end_pos': chunk['end_pos']
            })
        
        return processing_chunks

    def create_chunk_prompt(self, chunk_data, company_name=None, year=None, is_first_chunk=False, previous_sections=None):
        """
        Create a targeted prompt for processing a chunk of sections
        
        Args:
            chunk_data (dict): Chunk data with content and section metadata
            company_name (str): Company name if available
            year (str): Year if available
            is_first_chunk (bool): Whether this is the first chunk being processed
            previous_sections (list): List of sections completed in previous chunks
            
        Returns:
            str: Formatted prompt for the chunk
        """
        # Build sections list for this chunk
        sections_list = []
        for section in chunk_data['sections']:
            if section['item_number']:
                sections_list.append(f"Item {section['item_number']}: {section['title']}")
            else:
                sections_list.append(section['title'])
        
        sections_text = "\n".join([f"  - {s}" for s in sections_list])
        
        # Build context about previous processing
        previous_context = ""
        if previous_sections and not is_first_chunk:
            prev_list = "\n".join([f"  - {s}" for s in previous_sections])
            previous_context = f"""
## PREVIOUS PROCESSING CONTEXT
The following sections have already been processed in previous chunks:
{prev_list}

Continue processing from where the previous chunk left off.
"""

        prompt = f"""# 10-K Incremental Processor - Chunk {chunk_data['chunk_id']}

You are processing a chunk of a 10-K form incrementally. Extract and structure ONLY the content for the sections in this chunk.

## CHUNK INFORMATION
- **Chunk ID**: {chunk_data['chunk_id']}
- **Company**: {company_name or 'COMPANY_NAME'}
- **Year**: {year or 'YEAR'}
- **Estimated Input Tokens**: {chunk_data.get('estimated_input_tokens', 'Unknown'):,}
- **Sections in this chunk**:
{sections_text}
{previous_context}

## CRITICAL PROCESSING REQUIREMENTS

### Token Management
- Monitor your output carefully to stay within limits
- If you approach token limits, complete the current section and indicate where you stopped
- Use the format: `"processing_status": "completed_through_item_X"` in your response
- DO NOT start a section you cannot complete within token limits

### Data Processing Rules
1. **Preserve ALL Data**: Never remove numbers, dates, financial figures, names, or legal references
2. **Clean Formatting**: Remove excessive whitespace, fix broken text across lines, clean up table formatting
3. **Maintain Structure**: Keep headers, subheaders, tables, and lists properly formatted
4. **JSON Compliance**: Ensure all strings are properly escaped and valid JSON syntax

### Section Processing Strategy
1. Process sections in the order they appear in the document
2. For each section, extract ALL content completely
3. If a section is too large, break it into logical subsections
4. Always indicate completion status in your response

## REQUIRED JSON OUTPUT FORMAT
```json
{{
  "chunk_id": {chunk_data['chunk_id']},
  "company": "{company_name or 'COMPANY_NAME'}",
  "year": "{year or 'YEAR'}",
  "processing_status": "completed|partial_item_X|stopped_at_item_X",
  "sections": {{
    "Item X. Title": {{
      "content": "[Full cleaned and formatted content]",
      "subsections": {{
        "[subsection_name]": "[subsection content]"
      }},
      "data_quality": {{
        "original_length": number,
        "processed_length": number,
        "formatting_applied": ["list", "of", "improvements"]
      }}
    }}
  }},
  "chunk_metadata": {{
    "sections_attempted": ["list of sections"],
    "sections_completed": ["list of completed sections"],
    "next_expected_item": "Item X or null if finished"
  }}
}}
```

## SECTION CLASSIFICATION
Map each section to the appropriate category:
- **Part I: Business and Risk Factors**: Items 1, 1A, 1B, 2, 3, 4
- **Part II: Financial Information**: Items 5, 6, 7, 7A, 8, 9, 9A, 9B, 9C
- **Part III: Governance**: Items 10, 11, 12, 13, 14
- **Part IV: Exhibits and Schedules**: Items 15, 16

## DATA QUALITY STANDARDS
- Financial numbers: Preserve exactly as written
- Tables: Clean formatting but maintain all data
- Legal language: Keep intact with proper escaping
- References: Maintain all file numbers, dates, citations
- Names: Preserve exactly (companies, people, products)

## CHUNK CONTENT TO PROCESS:

{chunk_data['content']}"""
        
        return prompt

    def process_chunk_with_backtrack(self, chunk_data, company_name=None, year=None, is_first_chunk=False, previous_sections=None, max_retries=3):
        """
        Process a chunk with backtracking capability if token limits are exceeded
        
        Args:
            chunk_data (dict): Chunk data to process
            company_name (str): Company name
            year (str): Year  
            is_first_chunk (bool): Whether this is the first chunk
            previous_sections (list): Previously completed sections
            max_retries (int): Maximum retry attempts with backtracking
            
        Returns:
            dict: Processing result with completion status
        """
        retry_count = 0
        current_chunk = chunk_data.copy()
        
        while retry_count < max_retries:
            try:
                # Create prompt for current chunk
                prompt = self.create_chunk_prompt(
                    current_chunk, 
                    company_name, 
                    year, 
                    is_first_chunk, 
                    previous_sections
                )
                
                # Check input token count
                estimated_tokens = self.estimate_token_count(prompt)
                print(f"  📏 Chunk {current_chunk['chunk_id']} attempt {retry_count + 1}: {estimated_tokens:,} tokens")
                
                if estimated_tokens > self.max_tokens_per_chunk:
                    print(f"  ⚠️ Input tokens exceed limit, reducing chunk size...")
                    current_chunk = self.reduce_chunk_size(current_chunk)
                    retry_count += 1
                    continue
                
                # Process with Gemini
                print(f"  📤 Processing chunk {current_chunk['chunk_id']} ({len(current_chunk['sections'])} sections)...")
                response = self.model.generate_content(prompt)
                
                if response.text:
                    try:
                        # Parse JSON response
                        result = json.loads(response.text)
                        
                        # Check if processing was completed or partial
                        status = result.get('processing_status', 'unknown')
                        
                        if status.startswith('completed'):
                            print(f"  ✅ Chunk {current_chunk['chunk_id']} completed successfully")
                            return {
                                'success': True,
                                'result': result,
                                'completed_sections': result.get('chunk_metadata', {}).get('sections_completed', []),
                                'next_item': result.get('chunk_metadata', {}).get('next_expected_item'),
                                'retry_count': retry_count
                            }
                        elif status.startswith('partial') or status.startswith('stopped'):
                            # Partial completion - extract completed sections and backtrack
                            print(f"  ⚠️ Partial completion detected: {status}")
                            completed_sections = result.get('chunk_metadata', {}).get('sections_completed', [])
                            
                            if completed_sections:
                                # Create new chunk with remaining sections
                                remaining_sections = [s for s in current_chunk['sections'] 
                                                    if f"Item {s['item_number']}" not in completed_sections]
                                
                                if remaining_sections:
                                    # Continue with remaining sections in next iteration
                                    print(f"  🔄 Backtracking: {len(remaining_sections)} sections remaining")
                                    return {
                                        'success': True,
                                        'result': result,
                                        'completed_sections': completed_sections,
                                        'remaining_chunk': {
                                            **current_chunk,
                                            'sections': remaining_sections,
                                            'chunk_id': f"{current_chunk['chunk_id']}_continued"
                                        },
                                        'partial': True,
                                        'retry_count': retry_count
                                    }
                                else:
                                    # All sections completed
                                    return {
                                        'success': True,
                                        'result': result,
                                        'completed_sections': completed_sections,
                                        'next_item': None,
                                        'retry_count': retry_count
                                    }
                            else:
                                # No sections completed, reduce chunk size
                                current_chunk = self.reduce_chunk_size(current_chunk)
                                retry_count += 1
                                continue
                        else:
                            print(f"  ❓ Unknown processing status: {status}")
                            return {
                                'success': True,
                                'result': result,
                                'completed_sections': [],
                                'retry_count': retry_count
                            }
                            
                    except json.JSONDecodeError as e:
                        print(f"  ⚠️ JSON decode error: {str(e)}")
                        if retry_count < max_retries - 1:
                            current_chunk = self.reduce_chunk_size(current_chunk)
                            retry_count += 1
                            continue
                        else:
                            return {
                                'success': False,
                                'error': f'JSON decode error after {retry_count + 1} attempts',
                                'raw_response': response.text[:1000] + "..." if len(response.text) > 1000 else response.text
                            }
                else:
                    raise Exception("Empty response from Gemini")
                    
            except Exception as e:
                print(f"  ❌ Error in chunk processing attempt {retry_count + 1}: {str(e)}")
                if retry_count < max_retries - 1:
                    current_chunk = self.reduce_chunk_size(current_chunk)
                    retry_count += 1
                    continue
                else:
                    return {
                        'success': False,
                        'error': str(e),
                        'retry_count': retry_count
                    }
        
        return {
            'success': False,
            'error': f'Failed after {max_retries} attempts',
            'retry_count': retry_count
        }

    def reduce_chunk_size(self, chunk_data):
        """
        Reduce chunk size by removing sections or splitting large sections
        
        Args:
            chunk_data (dict): Current chunk data
            
        Returns:
            dict: Reduced chunk data
        """
        sections = chunk_data['sections']
        
        if len(sections) > 1:
            # Remove last section(s)
            reduced_sections = sections[:len(sections)//2]
            print(f"    🔻 Reducing chunk from {len(sections)} to {len(reduced_sections)} sections")
        else:
            # Split the single large section
            section = sections[0]
            section_content = chunk_data['content'][section['position']:section['end_position']]
            
            # Split content in half
            mid_point = len(section_content) // 2
            # Find a good break point (end of paragraph)
            for i in range(mid_point - 100, mid_point + 100):
                if i < len(section_content) and section_content[i:i+2] == '\n\n':
                    mid_point = i
                    break
            
            reduced_content = section_content[:mid_point]
            reduced_sections = [{
                **section,
                'title': section['title'] + ' (Part 1)',
                'end_position': section['position'] + mid_point
            }]
            print(f"    ✂️ Splitting large section into smaller part")
        
        # Update chunk with reduced content
        if reduced_sections:
            start_pos = reduced_sections[0]['position']
            end_pos = reduced_sections[-1]['end_position']
            reduced_content = chunk_data['content'][start_pos - chunk_data['start_pos']:end_pos - chunk_data['start_pos']]
        else:
            reduced_content = chunk_data['content'][:len(chunk_data['content'])//2]
        
        return {
            **chunk_data,
            'sections': reduced_sections,
            'content': reduced_content,
            'estimated_input_tokens': self.estimate_token_count(reduced_content),
            'chunk_id': f"{chunk_data['chunk_id']}_reduced"
        }

    def test_section_detection(self, document_content, preview_only=True):
        """
        Test the dynamic section detection without processing
        
        Args:
            document_content (str): Full document content
            preview_only (bool): If True, only show detection results without processing
            
        Returns:
            dict: Detection results and chunks information
        """
        print("🧪 Testing dynamic section detection...")
        
        # Step 1: Detect boundaries
        boundaries = self.detect_section_boundaries(document_content)
        
        # Step 2: Create chunks
        chunks = self.create_processing_chunks(document_content, boundaries)
        
        # Step 3: Show preview
        test_results = {
            'total_boundaries': len(boundaries),
            'total_chunks': len(chunks),
            'boundaries': boundaries,
            'chunks': []
        }
        
        print(f"\n📊 DETECTION SUMMARY:")
        print(f"  Total boundaries found: {len(boundaries)}")
        print(f"  Total processing chunks: {len(chunks)}")
        
        print(f"\n📋 BOUNDARIES DETECTED:")
        for i, boundary in enumerate(boundaries):
            confidence_bar = "█" * int(boundary['confidence'] * 10)
            print(f"  {i+1:2d}. Item {boundary['item_number'] or 'PART':<3} | {boundary['title'][:50]:<50} | {confidence_bar} ({boundary['confidence']:.1f})")
        
        print(f"\n📦 PROCESSING CHUNKS:")
        for chunk in chunks:
            chunk_info = {
                'chunk_id': chunk['chunk_id'],
                'sections': [f"Item {s['item_number']}" for s in chunk['sections'] if s['item_number']],
                'estimated_input_tokens': chunk['estimated_input_tokens'],
                'estimated_output_tokens': chunk['estimated_output_tokens'],
                'content_preview': chunk['content'][:200] + "..." if len(chunk['content']) > 200 else chunk['content']
            }
            test_results['chunks'].append(chunk_info)
            
            sections_text = ", ".join(chunk_info['sections']) or "PARTS"
            print(f"  Chunk {chunk['chunk_id']}: {sections_text}")
            print(f"    Input tokens: {chunk['estimated_input_tokens']:,}")
            print(f"    Output tokens: {chunk['estimated_output_tokens']:.0f}")
            print(f"    Sections: {len(chunk['sections'])}")
        
        if not preview_only:
            print(f"\n🔍 CONTENT PREVIEW (first chunk):")
            if chunks:
                preview = chunks[0]['content'][:1000]
                print(preview + "..." if len(chunks[0]['content']) > 1000 else preview)
        
        return test_results

    def process_with_gemini(self, document_content):
        """
        Process document using incremental chunk-based approach with backtracking
        
        Args:
            document_content (str): Content of the 10-K document
            
        Returns:
            str: Combined JSON response
        """
        try:
            print("� Starting incremental processing with token monitoring...")
            
            # Step 1: Extract company info
            company_name, year = self.extract_company_info(document_content)
            print(f"📋 Company: {company_name}, Year: {year}")
            
            # Step 2: Create processing chunks dynamically
            processing_chunks = self.extract_sections_dynamic(document_content)
            
            if not processing_chunks:
                print("⚠️ No chunks created, falling back to full document processing")
                return self.process_full_document(document_content)
            
            # Step 3: Process chunks incrementally with backtracking
            all_results = []
            completed_sections = []
            chunk_queue = processing_chunks.copy()
            
            chunk_num = 0
            while chunk_queue:
                chunk_num += 1
                current_chunk = chunk_queue.pop(0)
                
                print(f"\n� Processing chunk {chunk_num}/{chunk_num + len(chunk_queue)} (ID: {current_chunk['chunk_id']})")
                print(f"  📊 Sections: {[s.get('item_number', 'PART') for s in current_chunk['sections']]}")
                print(f"  📏 Estimated tokens: {current_chunk.get('estimated_input_tokens', 0):,}")
                
                # Process chunk with backtracking
                result = self.process_chunk_with_backtrack(
                    current_chunk,
                    company_name,
                    year,
                    is_first_chunk=(chunk_num == 1),
                    previous_sections=completed_sections
                )
                
                if result['success']:
                    all_results.append(result['result'])
                    completed_sections.extend(result.get('completed_sections', []))
                    
                    # Check if there are remaining sections to process
                    if result.get('partial') and result.get('remaining_chunk'):
                        print(f"  🔄 Adding remaining sections to queue...")
                        chunk_queue.insert(0, result['remaining_chunk'])
                    
                    print(f"  ✅ Processed successfully (attempt {result.get('retry_count', 0) + 1})")
                    print(f"  📝 Completed sections so far: {len(completed_sections)}")
                    
                else:
                    print(f"  ❌ Failed to process chunk: {result.get('error', 'Unknown error')}")
                    # Save partial results for failed chunk
                    failed_chunk_info = {
                        'chunk_id': f"FAILED_{current_chunk['chunk_id']}",
                        'error': result.get('error'),
                        'sections': current_chunk['sections'],
                        'raw_response': result.get('raw_response', '')
                    }
                    all_results.append(failed_chunk_info)
            
            # Step 4: Combine all results into final structure
            final_json = self.combine_incremental_results(all_results, company_name, year)
            
            # Convert to JSON string
            json_response = json.dumps(final_json, indent=2, ensure_ascii=False)
            
            print(f"\n🎉 Incremental processing completed!")
            print(f"  📊 Total chunks processed: {len(all_results)}")
            print(f"  📝 Total sections completed: {len(completed_sections)}")
            print(f"  📄 Final JSON size: {len(json_response):,} characters")
            
            return json_response
                
        except Exception as e:
            print(f"❌ Error in incremental processing: {str(e)}")
            print("🔄 Falling back to full document processing...")
            return self.process_full_document(document_content)

    def combine_incremental_results(self, chunk_results, company_name=None, year=None):
        """
        Combine incremental chunk results into final JSON structure
        
        Args:
            chunk_results (list): List of chunk processing results
            company_name (str): Company name
            year (str): Year
            
        Returns:
            dict: Final combined JSON structure
        """
        print("🔧 Combining incremental results into final structure...")
        
        # Initialize the final structure
        final_json = {
            company_name or "COMPANY_NAME": {
                year or "YEAR": {
                    "FORM": "10-K",
                    "CATEGORIES": {
                        "Part I: Business and Risk Factors": {},
                        "Part II: Financial Information": {},
                        "Part III: Governance": {},
                        "Part IV: Exhibits and Schedules": {}
                    },
                    "PROCESSING_METADATA": {
                        "processing_method": "incremental_with_backtracking",
                        "chunks_processed": len(chunk_results),
                        "timestamp": datetime.now().isoformat(),
                        "failed_chunks": []
                    }
                }
            }
        }
        
        company_key = list(final_json.keys())[0]
        year_key = list(final_json[company_key].keys())[0]
        categories = final_json[company_key][year_key]["CATEGORIES"]
        processing_metadata = final_json[company_key][year_key]["PROCESSING_METADATA"]
        
        # Process each chunk result
        for chunk_result in chunk_results:
            if 'error' in chunk_result:
                # Handle failed chunks
                processing_metadata["failed_chunks"].append({
                    'chunk_id': chunk_result.get('chunk_id'),
                    'error': chunk_result.get('error'),
                    'sections_attempted': [s.get('item_number', s.get('title', 'Unknown')) 
                                        for s in chunk_result.get('sections', [])]
                })
                continue
            
            # Extract sections from successful chunks
            sections_data = chunk_result.get('sections', {})
            
            for section_name, section_data in sections_data.items():
                # Determine category for this section
                category = self.determine_section_category(section_name)
                
                # Add to appropriate category
                categories[category][section_name] = section_data
        
        # Add processing statistics
        total_sections = sum(len(cat.keys()) for cat in categories.values())
        processing_metadata.update({
            "total_sections_extracted": total_sections,
            "sections_by_category": {
                cat: len(sections.keys()) for cat, sections in categories.items()
            }
        })
        
        print(f"  ✅ Combined {total_sections} sections across {len(categories)} categories")
        return final_json

    def determine_section_category(self, section_name):
        """
        Determine the category for a section based on its name
        
        Args:
            section_name (str): Full section name (e.g., "Item 1. Business")
            
        Returns:
            str: Category name
        """
        # Extract item number from section name
        item_match = re.search(r'Item\s+(\d+[A-C]?)', section_name, re.IGNORECASE)
        if item_match:
            item_key = f"Item {item_match.group(1)}"
            return self.section_to_category.get(item_key, "Part I: Business and Risk Factors")
        
        # Default category for non-standard sections
        return "Part I: Business and Risk Factors"

    def process_full_document(self, document_content):
        """
        Fallback method: process entire document at once (original approach)
        
        Args:
            document_content (str): Content of the 10-K document
            
        Returns:
            str: Gemini's response
        """
        try:
            # Combine system prompt with document content
            full_prompt = self.system_prompt + "\n\n" + document_content
            
            print("📤 Sending full document to Gemini...")
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
    parser.add_argument('-t', '--max-tokens', type=int, default=800000, help='Maximum tokens per chunk (default: 800000)')
    
    args = parser.parse_args()
    
    # Validate input arguments
    if not args.input_file and not args.content:
        parser.error("Either input_file or --content must be provided")
    
    if args.input_file and args.content:
        parser.error("Provide either input_file OR --content, not both")
    
    try:
        # Initialize processor
        processor = TenKProcessor(api_key=args.api_key, max_tokens_per_chunk=args.max_tokens)
        
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