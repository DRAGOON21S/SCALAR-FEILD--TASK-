#!/usr/bin/env python3
"""
10-Q Filing Parser Pipeline
Specialized parser for 10-Q quarterly reports with structure tailored for quarterly filings
Based on filing_parser_pipeline.py but adapted for 10-Q specific sections and content
"""

import os
import re
import sys
import json
import shutil
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List, Union

Json = Dict[str, Any]

class Filing10QParserPipeline:
    """
    Complete pipeline for parsing 10-Q quarterly filings and converting to structured JSON
    """
    
    def __init__(self, input_file_path: str, output_dir: str = None, company_name: str = None, quarter: str = None, year: str = None):
        self.input_file = Path(input_file_path)
        self.company_name = company_name or self._extract_company_name()
        self.quarter = quarter or self._extract_quarter()
        self.year = year or self._extract_year()
        self.output_dir = output_dir or f"{self.company_name}_10Q_{self.quarter}_{self.year}_Parsed"
        self.temp_json_path = Path("temp_10q_structure.json")
        
    def _extract_company_name(self) -> str:
        """Extract company name from filename or use default"""
        filename = self.input_file.stem
        if 'AAPL' in filename or 'Apple' in filename:
            return "Apple_Inc"
        elif 'MSFT' in filename or 'Microsoft' in filename:
            return "Microsoft_Corp"
        elif 'GOOGL' in filename or 'Google' in filename:
            return "Alphabet_Inc"
        elif 'META' in filename:
            return "Meta_Platforms"
        elif 'TSLA' in filename or 'Tesla' in filename:
            return "Tesla_Inc"
        else:
            return "Company"
    
    def _extract_quarter(self) -> str:
        """Extract quarter from filename or content"""
        filename = self.input_file.stem.upper()
        if 'Q1' in filename or '_01_' in filename or '_03_' in filename:
            return "Q1"
        elif 'Q2' in filename or '_04_' in filename or '_06_' in filename:
            return "Q2"
        elif 'Q3' in filename or '_07_' in filename or '_09_' in filename:
            return "Q3"
        else:
            return "Q2"  # Default assumption
    
    def _extract_year(self) -> str:
        """Extract year from filename"""
        filename = self.input_file.stem
        year_match = re.search(r'20\d{2}', filename)
        return year_match.group() if year_match else str(datetime.now().year)
    
    def sanitize_filename(self, filename: str) -> str:
        """Sanitize filename by removing invalid characters"""
        filename = re.sub(r'[<>:"/\\|?*]', '', filename)
        filename = re.sub(r'\s+', '_', filename)
        filename = re.sub(r'[^\w\-_.]', '', filename)
        filename = filename.strip('._')
        if len(filename) > 100:
            filename = filename[:100]
        return filename if filename else "unnamed"
    
    def _identify_10q_sections(self, content: str) -> Dict[str, str]:
        """
        Identify common 10-Q sections and items
        10-Q forms typically have:
        - Part I: Financial Information
          - Item 1: Financial Statements
          - Item 2: Management's Discussion and Analysis
          - Item 3: Quantitative and Qualitative Disclosures About Market Risk
          - Item 4: Controls and Procedures
        - Part II: Other Information
          - Item 1: Legal Proceedings
          - Item 2: Unregistered Sales of Equity Securities
          - Item 3: Defaults Upon Senior Securities
          - Item 4: Mine Safety Disclosures
          - Item 5: Other Information
          - Item 6: Exhibits
        """
        sections = {}
        
        # Common 10-Q patterns - Following standard SEC 10-Q structure
        patterns = {
            # Part I: Financial Information
            'Item 1. Financial Statements': r'Item\s+1\.\s*Financial\s+Statements',
            'Item 2. Management Discussion and Analysis': r'Item\s+2\.\s*Management.*Discussion\s+and\s+Analysis',
            'Item 3. Quantitative and Qualitative Disclosures': r'Item\s+3\.\s*Quantitative\s+and\s+Qualitative\s+Disclosures',
            'Item 4. Controls and Procedures': r'Item\s+4\.\s*Controls\s+and\s+Procedures',
            # Part II: Other Information  
            'Part II Other Information': r'PART\s+II[^\n]*OTHER\s+INFORMATION',
            'Item 1. Legal Proceedings': r'Item\s+1\.\s*Legal\s+Proceedings',
            'Item 1A. Risk Factors': r'Item\s+1A\.\s*Risk\s+Factors',
            'Item 2. Unregistered Sales': r'Item\s+2\.\s*Unregistered\s+Sales',
            'Item 3. Defaults Upon Senior Securities': r'Item\s+3\.\s*Defaults\s+Upon\s+Senior\s+Securities',
            'Item 4. Mine Safety Disclosures': r'Item\s+4\.\s*Mine\s+Safety\s+Disclosures',
            'Item 5. Other Information': r'Item\s+5\.\s*Other\s+Information',
            'Item 6. Exhibits': r'Item\s+6\.\s*Exhibits',
        }
        
        for section_name, pattern in patterns.items():
            match = re.search(pattern, content, re.IGNORECASE | re.MULTILINE)
            if match:
                sections[section_name] = match.group()
        
        return sections
    
    def _validate_10q_structure(self, company_data: Json) -> Json:
        """
        Validate and ensure the 10-Q structure follows SEC standards
        """
        print("🔍 Validating 10-Q structure against SEC standards...")
        
        # Define expected 10-Q structure
        expected_structure = {
            "Part I: Financial Information": [
                "Item 1. Financial Statements",
                "Item 2. Management's Discussion and Analysis", 
                "Item 3. Quantitative and Qualitative Disclosures About Market Risk",
                "Item 4. Controls and Procedures"
            ],
            "Part II: Other Information": [
                "Item 1. Legal Proceedings",
                "Item 1A. Risk Factors", 
                "Item 2. Unregistered Sales of Equity Securities",
                "Item 3. Defaults Upon Senior Securities",
                "Item 4. Mine Safety Disclosures", 
                "Item 5. Other Information",
                "Item 6. Exhibits"
            ]
        }
        
        # Add validation metadata
        validation_results = {
            "structure_compliance": "partial",
            "missing_standard_items": [],
            "non_standard_items": [],
            "total_expected_items": 11,  # 4 in Part I + 7 in Part II
            "total_found_items": 0
        }
        
        found_items = []
        for part_name, part_data in company_data.get('parts', {}).items():
            if isinstance(part_data, dict):
                for section_name in part_data.get('sections', {}):
                    found_items.append(section_name)
                    validation_results["total_found_items"] += 1
        
        # Check for missing standard items
        all_expected = []
        for items in expected_structure.values():
            all_expected.extend(items)
            
        # Update validation status
        if validation_results["total_found_items"] >= 7:
            validation_results["structure_compliance"] = "good"
        if validation_results["total_found_items"] >= 9:
            validation_results["structure_compliance"] = "excellent"
            
        company_data["validation"] = validation_results
        print(f"✅ Structure validation complete: {validation_results['structure_compliance']}")
        
        return company_data
    
    
    def parse_10q_to_folders(self) -> Path:
        """
        Parse 10-Q filing into folder structure optimized for quarterly reports
        """
        print(f"📄 Parsing {self.input_file.name} ({self.quarter} {self.year}) into folder structure...")
        
        # Clean previous output if exists
        if os.path.exists(self.output_dir):
            shutil.rmtree(self.output_dir)
        
        # Read the 10-Q filing
        with open(self.input_file, 'r', encoding='utf-8') as file:
            content = file.read()
        
        # Create main company folder with quarter/year structure
        company_dir = Path(self.output_dir)
        company_dir.mkdir(parents=True, exist_ok=True)
        
        print(f"🔍 Starting to parse 10-Q filing for {self.quarter} {self.year}...")
        
        # Identify 10-Q specific sections
        identified_sections = self._identify_10q_sections(content)
        print(f"🎯 Identified {len(identified_sections)} standard 10-Q sections")
        
        # Split by major part delimiter (same as 10-K)
        major_parts = content.split('╔═ § ═')
        
        part_counter = 1
        for i, part in enumerate(major_parts):
            if not part.strip() or i == 0:  # Skip empty parts and content before first delimiter
                continue
                
            # Extract part title from the first few lines
            lines = part.split('\n')[:10]
            part_title = f"Part_{part_counter}"
            
            for line in lines:
                clean_line = re.sub(r'[═║╗╚│─\s]+', ' ', line).strip()
                if clean_line and len(clean_line) > 3:
                    if 'PART I' in clean_line.upper() and 'FINANCIAL' in clean_line.upper():
                        part_title = "PART_I_FINANCIAL_INFORMATION"
                    elif 'PART II' in clean_line.upper() and 'OTHER' in clean_line.upper():
                        part_title = "PART_II_OTHER_INFORMATION"
                    elif 'PART' in clean_line.upper():
                        part_title = clean_line
                    break
            
            # Sanitize part title for folder name
            clean_part_title = self.sanitize_filename(part_title)
            part_folder = company_dir / f"Part_{part_counter}_{clean_part_title}"
            part_folder.mkdir(exist_ok=True)
            
            print(f"  📁 Processing {part_title}")
            
            # Split part by section delimiter or Item patterns
            if '╭─ • ─' in part:
                sections = part.split('╭─ • ─')
            else:
                # Fallback: split by Item patterns common in 10-Q
                item_pattern = r'\n\s*Item\s+\d+[A-Za-z]?\.'
                sections = re.split(item_pattern, part, flags=re.MULTILINE)
            
            section_counter = 1
            for j, section in enumerate(sections):
                if not section.strip():
                    continue
                    
                # Extract section title with 10-Q specific handling
                section_lines = section.split('\n')[:8]
                section_title = f"Section_{section_counter}"
                
                for line in section_lines:
                    clean_line = re.sub(r'[╮│╰─\s]+', ' ', line).strip()
                    if clean_line and len(clean_line) > 3:
                        # Check for specific 10-Q items following standard SEC structure
                        if 'Financial Statements' in clean_line:
                            section_title = "Item_1_Financial_Statements"
                        elif 'Management' in clean_line and 'Discussion' in clean_line:
                            section_title = "Item_2_Management_Discussion_Analysis"
                        elif 'Quantitative' in clean_line and 'Qualitative' in clean_line:
                            section_title = "Item_3_Market_Risk_Disclosures"
                        elif 'Controls' in clean_line and 'Procedures' in clean_line:
                            section_title = "Item_4_Controls_Procedures"
                        # Part II - Other Information items
                        elif 'Legal Proceedings' in clean_line and 'Item 1.' in clean_line:
                            section_title = "Item_1_Legal_Proceedings"
                        elif 'Risk Factors' in clean_line and 'Item 1A' in clean_line:
                            section_title = "Item_1A_Risk_Factors"  
                        elif 'Unregistered Sales' in clean_line and ('Item 2' in clean_line):
                            section_title = "Item_2_Unregistered_Sales"
                        elif 'Defaults Upon Senior Securities' in clean_line:
                            section_title = "Item_3_Defaults_Senior_Securities"
                        elif 'Mine Safety' in clean_line:
                            section_title = "Item_4_Mine_Safety_Disclosures"
                        elif 'Other Information' in clean_line and 'Item 5' in clean_line:
                            section_title = "Item_5_Other_Information"
                        elif 'Exhibits' in clean_line and 'Item 6' in clean_line:
                            section_title = "Item_6_Exhibits"
                        else:
                            section_title = clean_line
                        break
                
                # Clean the section content
                content_lines = []
                for line in section.split('\n'):
                    # Remove box drawing characters
                    cleaned_line = re.sub(r'^[╔╗╚╝║│╭╮╰╯─═•\s]*', '', line)
                    cleaned_line = re.sub(r'[╔╗╚╝║│╭╮╰╯─═•\s]*$', '', cleaned_line)
                    if cleaned_line.strip():
                        content_lines.append(cleaned_line.strip())
                
                final_content = '\n'.join(content_lines)
                
                # Save with lower threshold for 10-Q sections (they can be shorter)
                if len(final_content.strip()) > 50:
                    # Sanitize section title for filename
                    clean_section_title = self.sanitize_filename(section_title)
                    section_file = part_folder / f"Section_{section_counter:02d}_{clean_section_title}.txt"
                    
                    try:
                        with open(section_file, 'w', encoding='utf-8') as f:
                            f.write(final_content)
                        print(f"    📄 Created: {section_file.name}")
                        section_counter += 1
                    except Exception as e:
                        print(f"    ❌ Error creating file: {e}")
            
            part_counter += 1
        
        print(f"✅ 10-Q parsing completed! Files saved in: {company_dir}")
        return company_dir
    
    def create_json_from_folders(self, parsed_folder: Path) -> Json:
        """
        Convert parsed 10-Q folder structure to JSON with quarterly-specific metadata
        """
        print(f"📋 Converting 10-Q folder structure to JSON...")
        
        company_data = {
            'company_name': self.company_name.replace('_', ' '),
            'filing_type': '10-Q',
            'quarter': self.quarter,
            'year': self.year,
            'created_date': datetime.now().isoformat(),
            'source_file': str(self.input_file.name),
            'parts': {}
        }
        
        # Process each part folder
        part_folders = [d for d in parsed_folder.iterdir() if d.is_dir()]
        part_folders.sort()
        
        for part_folder in part_folders:
            part_name = part_folder.name
            print(f"  📁 Processing {part_name}...")
            
            part_data = {
                'part_name': part_name,
                'sections': {}
            }
            
            # Process each section file
            section_files = [f for f in part_folder.iterdir() if f.is_file() and f.suffix == '.txt']
            section_files.sort()
            
            for section_file in section_files:
                try:
                    with open(section_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    section_name = section_file.stem
                    part_data['sections'][section_name] = {
                        'file_name': section_file.name,
                        'content': content,
                        'content_length': len(content),
                        'line_count': len(content.split('\n'))
                    }
                    print(f"    📄 Added: {section_file.name} ({len(content)} chars)")
                    
                except Exception as e:
                    part_data['sections'][section_file.stem] = {
                        'file_name': section_file.name,
                        'error': str(e),
                        'content': ''
                    }
            
            company_data['parts'][part_name] = part_data
        
        # Validate 10-Q structure compliance
        company_data = self._validate_10q_structure(company_data)
        
        return company_data
    
    def transform_sections(self, sections_obj: Any) -> List[Json]:
        """
        Convert a 'sections' mapping to a list of objects with 10-Q specific enhancements
        """
        if isinstance(sections_obj, list):
            out = []
            for idx, sec in enumerate(sections_obj):
                if isinstance(sec, dict):
                    if "section_id" not in sec:
                        sec = {**sec, "section_id": f"section_{idx}"}
                    out.append(sec)
            return out
        
        if isinstance(sections_obj, dict):
            result: List[Json] = []
            for key, value in sections_obj.items():
                if isinstance(value, dict):
                    section_data = {**value, "section_id": key}
                    # Add 10-Q specific metadata if available
                    if 'content' in value:
                        content = value['content']
                        section_data['word_count'] = len(content.split())
                        section_data['has_financial_data'] = bool(re.search(r'\$\s*\d+(?:,\d{3})*(?:\.\d{2})?', content))
                        section_data['has_tables'] = '|' in content or '\t' in content
                    result.append(section_data)
                else:
                    result.append({"section_id": key, "value": value})
            return result
        
        return []
    
    def transform_parts(self, parts_obj: Any) -> List[Json]:
        """
        Convert 'parts' mapping to a list of part objects with 10-Q enhancements
        """
        out: List[Json] = []
        
        if isinstance(parts_obj, list):
            for part in parts_obj:
                if not isinstance(part, dict):
                    continue
                part_name = part.get("part_name")
                sections = self.transform_sections(part.get("sections"))
                base = {k: v for k, v in part.items() if k not in ("sections",)}
                base["sections"] = sections
                base["section_count"] = len(sections)
                if not base.get("part_name"):
                    base["part_name"] = part_name or "Part"
                out.append(base)
            return out
        
        if isinstance(parts_obj, dict):
            for key, value in parts_obj.items():
                if isinstance(value, dict):
                    part_name = value.get("part_name") or key
                    sections = self.transform_sections(value.get("sections"))
                    base = {k: v for k, v in value.items() if k not in ("sections",)}
                    base["part_name"] = part_name
                    base["sections"] = sections
                    base["section_count"] = len(sections)
                    # Identify part type for 10-Q
                    if 'FINANCIAL' in part_name.upper():
                        base["part_type"] = "financial_information"
                    elif 'OTHER' in part_name.upper():
                        base["part_type"] = "other_information"
                    else:
                        base["part_type"] = "unknown"
                    out.append(base)
                else:
                    out.append({
                        "part_name": key, 
                        "value": value, 
                        "sections": [],
                        "section_count": 0,
                        "part_type": "unknown"
                    })
            return out
        
        return []
    
    def transform_document(self, doc: Json) -> Json:
        """
        Transform a single 10-Q filing document with quarterly-specific enhancements
        """
        top = {k: v for k, v in doc.items() if k != "parts"}
        parts = self.transform_parts(doc.get("parts"))
        top["parts"] = parts
        
        # Add 10-Q specific summary statistics
        total_sections = sum(part.get("section_count", 0) for part in parts)
        
        # Categorize sections by part type
        part_i_sections = 0
        part_ii_sections = 0
        for part in parts:
            if part.get("part_type") == "financial_information":
                part_i_sections = part.get("section_count", 0)
            elif part.get("part_type") == "other_information":
                part_ii_sections = part.get("section_count", 0)
        
        top["summary"] = {
            "total_parts": len(parts),
            "total_sections": total_sections,
            "part_i_sections": part_i_sections,
            "part_ii_sections": part_ii_sections,
            "filing_period": f"{self.quarter} {self.year}",
            "processing_timestamp": datetime.now().isoformat(),
            "sec_form_type": "10-Q",
            "structure_notes": {
                "part_i": "Financial Information (Items 1-4)",
                "part_ii": "Other Information (Items 1, 1A, 2-6)"
            }
        }
        
        return top
    
    def run_pipeline(self, output_json_path: str = None) -> str:
        """
        Run the complete 10-Q pipeline: parse -> create JSON -> transform JSON
        """
        if not self.input_file.exists():
            raise FileNotFoundError(f"Input file not found: {self.input_file}")
        
        output_json_path = output_json_path or f"{self.company_name}_10Q_{self.quarter}_{self.year}_structured.json"
        
        print("🚀 Starting 10-Q Filing Parser Pipeline")
        print("=" * 60)
        print(f"📄 Input file: {self.input_file}")
        print(f"🏢 Company: {self.company_name}")
        print(f"📅 Period: {self.quarter} {self.year}")
        print(f"📁 Output folder: {self.output_dir}")
        print(f"📋 Final JSON: {output_json_path}")
        print("=" * 60)
        
        # Step 1: Parse 10-Q filing into folder structure
        parsed_folder = self.parse_10q_to_folders()
        
        # Step 2: Convert folders to initial JSON structure
        initial_json = self.create_json_from_folders(parsed_folder)
        
        # Save temporary JSON
        with open(self.temp_json_path, 'w', encoding='utf-8') as f:
            json.dump(initial_json, f, indent=2, ensure_ascii=False)
        
        print(f"💾 Saved temporary JSON: {self.temp_json_path}")
        
        # Step 3: Transform JSON to final structured format
        print("🔄 Transforming JSON to final structured format...")
        transformed_json = self.transform_document(initial_json)
        
        # Step 4: Save final JSON
        final_output_path = Path(output_json_path)
        with open(final_output_path, 'w', encoding='utf-8') as f:
            json.dump(transformed_json, f, ensure_ascii=False, indent=2)
        
        # Clean up temporary file
        if self.temp_json_path.exists():
            self.temp_json_path.unlink()
        
        # Print summary
        print("\n" + "=" * 70)
        print("🎯 10-Q PIPELINE COMPLETED SUCCESSFULLY!")
        print("=" * 70)
        
        summary = transformed_json.get('summary', {})
        total_parts = summary.get('total_parts', 0)
        total_sections = summary.get('total_sections', 0)
        
        print(f"✅ Parsed folder structure created: {parsed_folder}")
        print(f"✅ Final structured JSON created: {final_output_path}")
        print(f"📊 Filing period: {self.quarter} {self.year}")
        print(f"📊 Total parts: {total_parts}")
        print(f"📊 Total sections: {total_sections}")
        print("=" * 70)
        
        return str(final_output_path)


def main():
    """Main function for command line usage"""
    if len(sys.argv) < 2:
        print("Usage: python filing_parser_10q_pipeline.py <input_txt_file> [output_json_file] [company_name] [quarter] [year]")
        print("\nExample:")
        print("  python filing_parser_10q_pipeline.py AAPL_Q2_2022_10Q.txt")
        print("  python filing_parser_10q_pipeline.py AAPL_Q2_2022_10Q.txt apple_q2_2022.json Apple_Inc Q2 2022")
        return 1
    
    input_file = sys.argv[1]
    output_json = sys.argv[2] if len(sys.argv) > 2 else None
    company_name = sys.argv[3] if len(sys.argv) > 3 else None
    quarter = sys.argv[4] if len(sys.argv) > 4 else None
    year = sys.argv[5] if len(sys.argv) > 5 else None
    
    try:
        # Create and run 10-Q pipeline
        pipeline = Filing10QParserPipeline(
            input_file, 
            company_name=company_name,
            quarter=quarter,
            year=year
        )
        final_json_path = pipeline.run_pipeline(output_json)
        
        print(f"\n🎉 SUCCESS! Final structured 10-Q JSON saved to: {final_json_path}")
        return 0
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
