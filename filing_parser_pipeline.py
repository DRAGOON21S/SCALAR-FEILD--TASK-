#!/usr/bin/env python3
"""
Filing Parser Pipeline
Combines 10-K filing parsing from parser.ipynb with JSON conversion from convert_filing_json.py
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

class FilingParserPipeline:
    """
    Complete pipeline for parsing 10-K filings and converting to structured JSON
    """
    
    def __init__(self, input_file_path: str, output_dir: str = None, company_name: str = None):
        self.input_file = Path(input_file_path)
        self.company_name = company_name or self._extract_company_name()
        self.output_dir = output_dir or f"{self.company_name}_Parsed"
        self.temp_json_path = Path("temp_filing_structure.json")
        
    def _extract_company_name(self) -> str:
        """Extract company name from filename or use default"""
        filename = self.input_file.stem
        if 'AAPL' in filename or 'Apple' in filename:
            return "Apple_Inc"
        elif 'MSFT' in filename or 'Microsoft' in filename:
            return "Microsoft_Corp"
        elif 'META' in filename:
            return "Meta_Platforms"
        else:
            return "Company"
    
    def sanitize_filename(self, filename: str) -> str:
        """Sanitize filename by removing invalid characters"""
        filename = re.sub(r'[<>:"/\\|?*]', '', filename)
        filename = re.sub(r'\s+', '_', filename)
        filename = re.sub(r'[^\w\-_.]', '', filename)
        filename = filename.strip('._')
        if len(filename) > 100:
            filename = filename[:100]
        return filename if filename else "unnamed"
    
    def parse_filing_to_folders(self) -> Path:
        """
        Parse 10-K filing into folder structure (from parser.ipynb logic)
        """
        print(f"📄 Parsing {self.input_file.name} into folder structure...")
        
        # Clean previous output if exists
        if os.path.exists(self.output_dir):
            shutil.rmtree(self.output_dir)
        
        # Read the 10-K filing
        with open(self.input_file, 'r', encoding='utf-8') as file:
            content = file.read()
        
        # Create main company folder
        company_dir = Path(self.output_dir)
        company_dir.mkdir(parents=True, exist_ok=True)
        
        print("🔍 Starting to parse 10-K filing...")
        
        # Split by major part delimiter
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
                if clean_line and len(clean_line) > 3 and 'PART' in clean_line.upper():
                    part_title = clean_line
                    break
            
            # Sanitize part title for folder name
            clean_part_title = self.sanitize_filename(part_title)
            part_folder = company_dir / f"Part_{part_counter}_{clean_part_title}"
            part_folder.mkdir(exist_ok=True)
            
            print(f"  📁 Processing {part_title}")
            
            # Split part by section delimiter
            sections = part.split('╭─ • ─')
            
            section_counter = 1
            for j, section in enumerate(sections):
                if not section.strip():
                    continue
                    
                # Extract section title
                section_lines = section.split('\n')[:5]
                section_title = f"Section_{section_counter}"
                
                for line in section_lines:
                    clean_line = re.sub(r'[╮│╰─\s]+', ' ', line).strip()
                    if clean_line and len(clean_line) > 3:
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
                
                # Only save if there's substantial content
                if len(final_content.strip()) > 100:
                    # Sanitize section title for filename
                    clean_section_title = self.sanitize_filename(section_title)
                    section_file = part_folder / f"Section_{section_counter}_{clean_section_title}.txt"
                    
                    try:
                        with open(section_file, 'w', encoding='utf-8') as f:
                            f.write(final_content)
                        print(f"    📄 Created: {section_file.name}")
                        section_counter += 1
                    except Exception as e:
                        print(f"    ❌ Error creating file: {e}")
            
            part_counter += 1
        
        print(f"✅ Parsing completed! Files saved in: {company_dir}")
        return company_dir
    
    def create_json_from_folders(self, parsed_folder: Path) -> Json:
        """
        Convert parsed folder structure to JSON (simplified version from notebook)
        """
        print(f"📋 Converting folder structure to JSON...")
        
        company_data = {
            'company_name': self.company_name.replace('_', ' '),
            'filing_type': '10-K',
            'created_date': datetime.now().isoformat(),
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
                        'content': content
                    }
                    print(f"    📄 Added: {section_file.name}")
                    
                except Exception as e:
                    part_data['sections'][section_file.stem] = {
                        'file_name': section_file.name,
                        'error': str(e),
                        'content': ''
                    }
            
            company_data['parts'][part_name] = part_data
        
        return company_data
    
    def transform_sections(self, sections_obj: Any) -> List[Json]:
        """
        Convert a 'sections' mapping to a list of objects (from convert_filing_json.py)
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
                    result.append({**value, "section_id": key})
                else:
                    result.append({"section_id": key, "value": value})
            return result
        
        return []
    
    def transform_parts(self, parts_obj: Any) -> List[Json]:
        """
        Convert 'parts' mapping to a list of part objects (from convert_filing_json.py)
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
                    out.append(base)
                else:
                    out.append({"part_name": key, "value": value, "sections": []})
            return out
        
        return []
    
    def transform_document(self, doc: Json) -> Json:
        """
        Transform a single filing document (from convert_filing_json.py)
        """
        top = {k: v for k, v in doc.items() if k != "parts"}
        parts = self.transform_parts(doc.get("parts"))
        top["parts"] = parts
        return top
    
    def run_pipeline(self, output_json_path: str = None) -> str:
        """
        Run the complete pipeline: parse -> create JSON -> transform JSON
        """
        if not self.input_file.exists():
            raise FileNotFoundError(f"Input file not found: {self.input_file}")
        
        output_json_path = output_json_path or f"{self.company_name}_final_structured.json"
        
        print("🚀 Starting Filing Parser Pipeline")
        print("=" * 50)
        print(f"📄 Input file: {self.input_file}")
        print(f"🏢 Company: {self.company_name}")
        print(f"📁 Output folder: {self.output_dir}")
        print(f"📋 Final JSON: {output_json_path}")
        print("=" * 50)
        
        # Step 1: Parse filing into folder structure
        parsed_folder = self.parse_filing_to_folders()
        
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
        print("\n" + "=" * 60)
        print("🎯 PIPELINE COMPLETED SUCCESSFULLY!")
        print("=" * 60)
        
        total_parts = len(transformed_json.get('parts', []))
        total_sections = sum(len(part.get('sections', [])) for part in transformed_json.get('parts', []))
        
        print(f"✅ Parsed folder structure created: {parsed_folder}")
        print(f"✅ Final structured JSON created: {final_output_path}")
        print(f"📊 Total parts: {total_parts}")
        print(f"📊 Total sections: {total_sections}")
        print("=" * 60)
        
        return str(final_output_path)


def main():
    """Main function for command line usage"""
    if len(sys.argv) < 2:
        print("Usage: python filing_parser_pipeline.py <input_txt_file> [output_json_file] [company_name]")
        print("\nExample:")
        print("  python filing_parser_pipeline.py AAPL_latest_10K.txt")
        print("  python filing_parser_pipeline.py AAPL_latest_10K.txt apple_structured.json Apple_Inc")
        return 1
    
    input_file = sys.argv[1]
    output_json = sys.argv[2] if len(sys.argv) > 2 else None
    company_name = sys.argv[3] if len(sys.argv) > 3 else None
    
    try:
        # Create and run pipeline
        pipeline = FilingParserPipeline(input_file, company_name=company_name)
        final_json_path = pipeline.run_pipeline(output_json)
        
        print(f"\n🎉 SUCCESS! Final structured JSON saved to: {final_json_path}")
        return 0
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
