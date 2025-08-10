# Filing Parser Pipeline - Usage Guide

## Overview
The `filing_parser_pipeline.py` script is a comprehensive tool that combines the parsing logic from `parser.ipynb` with the JSON conversion from `convert_filing_json.py` to create structured JSON files from SEC 10-K filing text files.

## What It Does
1. **Parses** 10-K filing text files using delimiter-based splitting (╔═ § ═ for parts, ╭─ • ─ for sections)
2. **Creates** a structured folder hierarchy with parts and sections as separate text files
3. **Converts** the folder structure to JSON format
4. **Transforms** the JSON to a standardized array-based structure (following convert_filing_json.py logic)
5. **Outputs** a final structured JSON file ready for analysis

## Usage

### Basic Usage
```bash
python filing_parser_pipeline.py <input_txt_file>
```

### With Custom Output File
```bash
python filing_parser_pipeline.py <input_txt_file> [output_json_file]
```

### With Custom Company Name
```bash
python filing_parser_pipeline.py <input_txt_file> [output_json_file] [company_name]
```

## Examples

```bash
# Basic usage - automatically detects company name from filename
python filing_parser_pipeline.py AAPL_latest_10K.txt

# Custom output filename
python filing_parser_pipeline.py AAPL_latest_10K.txt apple_structured.json

# Custom company name and output file
python filing_parser_pipeline.py MSFT_10K.txt microsoft_output.json Microsoft_Corp
```

## Supported File Types
- Any .txt file containing SEC 10-K filings with standard delimiters
- Files should use the box-drawing character delimiters:
  - `╔═ § ═` for major parts (Part I, Part II, etc.)
  - `╭─ • ─` for sections within parts

## Output Files

### 1. Structured Folder Hierarchy
- `{Company_Name}_Parsed/` - Main folder
  - `Part_1_{Part_Name}/` - Part folders
    - `Section_1_{Section_Name}.txt` - Individual section files

### 2. Final JSON Structure
```json
{
  "company_name": "Apple Inc",
  "filing_type": "10-K",
  "created_date": "2025-08-09T18:31:30.993191",
  "parts": [
    {
      "part_name": "Part_1_PART_I",
      "sections": [
        {
          "file_name": "Section_1_Item_1._Business.txt",
          "content": "Full section content...",
          "section_id": "Section_1_Item_1._Business"
        }
      ]
    }
  ]
}
```

## Features

### Automatic Company Detection
The script automatically detects company names from filenames:
- AAPL/Apple → "Apple_Inc"
- MSFT/Microsoft → "Microsoft_Corp"
- META → "Meta_Platforms"
- Default → "Company"

### Content Cleaning
- Removes box-drawing characters from content
- Sanitizes filenames for Windows compatibility
- Preserves original content structure

### Error Handling
- Validates input file existence
- Handles encoding issues gracefully
- Provides detailed progress reporting

## Pipeline Steps

1. **📄 Parse Filing** - Split text file by delimiters
2. **📁 Create Folders** - Organize content into folder structure
3. **📋 Generate Initial JSON** - Convert folders to JSON
4. **🔄 Transform Structure** - Apply convert_filing_json.py logic
5. **💾 Save Final Output** - Write structured JSON file

## Integration

This script combines:
- **Parser logic** from `parser.ipynb` (cells 2-6)
- **JSON conversion** from `convert_filing_json.py`
- **File handling** and error management
- **Progress reporting** for large files

## Requirements
- Python 3.6+
- Standard library only (no external dependencies)
- Input files should be UTF-8 encoded

## Troubleshooting

### Common Issues
1. **File not found** - Check file path and permissions
2. **Encoding errors** - Ensure file is UTF-8 encoded
3. **Empty output** - Verify file contains proper delimiters
4. **Permission errors** - Check write permissions in output directory

### Success Indicators
- ✅ Folder structure created successfully
- ✅ All sections parsed and saved
- ✅ Final JSON generated with proper structure
- ✅ Total parts and sections reported

## Output Verification
After successful completion, you should see:
- Parsed folder structure with individual section files
- Final JSON file with array-based parts and sections
- Summary statistics (total parts, sections, etc.)

The resulting JSON file is ready for:
- Database import
- API consumption
- Further analysis
- Integration with other tools
