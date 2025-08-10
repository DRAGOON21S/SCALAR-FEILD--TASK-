# Auto 10-K Parser Script

A comprehensive Python script that automatically discovers and processes all 10-K filing text files in your companies directory structure using the filing parser pipeline.

## Overview

This script solves the problem of bulk processing 10-K filings by:

1. **Automatically discovering** all 10-K filing text files across all companies in your directory structure
2. **Processing each filing** through the advanced parser pipeline (from `filing_parser_pipeline.py`)
3. **Organizing outputs** in a clean directory structure within each company's folder
4. **Providing detailed logging** and progress reporting
5. **Generating reports** of all processing results

## Prerequisites

- Python 3.6 or higher
- `filing_parser_pipeline.py` must be in the same directory
- Your companies directory structure should follow this pattern:

```
companies/
├── Company_Name/
│   ├── YYYY/
│   │   ├── 10-K/
│   │   │   ├── output_*.txt  ← 10-K filing files
│   │   │   └── ...
│   │   └── ...
│   └── ...
└── ...
```

## Usage

### Basic Usage

Process all 10-K filings found in the default companies directory:

```bash
python auto_10k_python.py
```

### Specify Custom Companies Directory

```bash
python auto_10k_python.py --companies-dir "C:\path\to\your\companies"
```

### Process Limited Number of Files (for testing)

```bash
python auto_10k_python.py --max-files 5
```

### Dry Run (see what would be processed without actually processing)

```bash
python auto_10k_python.py --dry-run
```

### Combined Options

```bash
python auto_10k_python.py --companies-dir proto-3\companies --max-files 10
```

## Command Line Options

| Option | Description | Default |
|--------|-------------|---------|
| `--companies-dir` | Path to the companies directory | `companies` |
| `--max-files` | Maximum number of files to process (useful for testing) | Process all files |
| `--dry-run` | Only discover files, don't process them | False |
| `--help` | Show help message | - |

## Output Structure

For each processed 10-K filing, the script creates:

```
Company_Name/
├── python_output_10k/
│   ├── YYYY/
│   │   ├── filing_name_parsed/          ← Parsed folder structure
│   │   │   ├── Part_1_PART_I/
│   │   │   │   ├── Section_1_Item_1._Business.txt
│   │   │   │   ├── Section_2_Item_1A._Risk_Factors.txt
│   │   │   │   └── ...
│   │   │   ├── Part_2_PART_II/
│   │   │   │   └── ...
│   │   │   └── ...
│   │   └── filing_name_structured.json  ← Final structured JSON
│   └── ...
└── ...
```

## Example Output

When you run the script, you'll see detailed progress output:

```
🚀 Starting to process 45 10-K filing files
================================================================================

📊 Progress: 1/45
------------------------------------------------------------
📄 Processing: output_0000320193_20_000096.txt
   🏢 Company: Apple_Inc
   📅 Year: 2020

🚀 Starting Filing Parser Pipeline
==================================================
📄 Input file: .../Apple_Inc/2020/10-K/output_0000320193_20_000096.txt
🏢 Company: Apple_Inc
📁 Output folder: .../Apple_Inc/python_output_10k/2020/output_0000320193_20_000096_parsed
📋 Final JSON: .../Apple_Inc/python_output_10k/2020/output_0000320193_20_000096_structured.json
==================================================

📄 Parsing output_0000320193_20_000096.txt into folder structure...
🔍 Starting to parse 10-K filing...
  📁 Processing PART I
    📄 Created: Section_1_Item_1._Business.txt
    📄 Created: Section_2_Item_1A._Risk_Factors.txt
    📄 Created: Section_3_Item_2._Properties.txt
    📄 Created: Section_4_Item_3._Legal_Proceedings.txt
  📁 Processing PART II
    📄 Created: Section_1_Item_5._Market_for_Registrants_Common_Equity...
    ... (more sections)
  📁 Processing PART III
    ... (more sections)
  📁 Processing PART IV
    ... (more sections)
✅ Parsing completed!

📋 Converting folder structure to JSON...
  📁 Processing Part_1_PART_I...
    📄 Added: Section_1_Item_1._Business.txt
    ... (more sections)
✅ Final structured JSON created

🎯 PIPELINE COMPLETED SUCCESSFULLY!
✅ Successfully processed: output_0000320193_20_000096.txt
✅ File 1/45 completed successfully

... (continues for all files)

================================================================================
🎯 AUTO 10-K PROCESSING SUMMARY
================================================================================
📁 Companies Directory: C:\path\to\companies
📊 Total Files Found: 45
✅ Successfully Processed: 43
❌ Failed to Process: 2
📈 Success Rate: 95.6%
================================================================================

📋 PROCESSING BREAKDOWN BY COMPANY:
  🏢 Apple_Inc: 5 files (2020, 2021, 2022, 2023, 2024)
  🏢 DoorDash_Inc: 5 files (2021, 2022, 2023, 2024, 2025)
  🏢 MICROSOFT_CORP: 5 files (2021, 2022, 2023, 2024, 2025)
  ... (more companies)

📄 Detailed report saved to: 10k_processing_report_20250809_210138.json
```

## Logging and Reports

### Log Files

The script creates detailed log files with timestamps:
- `10k_processing_YYYYMMDD_HHMMSS.log` - Contains all processing details

### JSON Reports

Detailed processing reports are saved as JSON files:
- `10k_processing_report_YYYYMMDD_HHMMSS.json` - Contains complete processing results

### Report Structure

The JSON report contains:

```json
{
  "total_files_found": 45,
  "successfully_processed": 43,
  "failed_to_process": 2,
  "success_rate": 95.6,
  "processing_date": "2025-08-09T21:01:38.469000",
  "companies_directory": "/path/to/companies",
  "processed_files": [
    {
      "input_file": "/path/to/input/file.txt",
      "company": "Apple_Inc",
      "year": "2020",
      "parsed_folder": "/path/to/parsed/folder",
      "json_output": "/path/to/output.json",
      "status": "success"
    }
    // ... more files
  ],
  "failed_files": [
    {
      "input_file": "/path/to/failed/file.txt",
      "company": "Company_Name",
      "year": "2021",
      "error": "Error description",
      "status": "failed"
    }
    // ... more failures
  ]
}
```

## Features

### Automatic Discovery
- Recursively searches all company directories
- Finds 10-K subdirectories at any level
- Identifies all `.txt` files within 10-K directories

### Intelligent Processing
- Extracts company name and year from file paths
- Creates organized output directory structure
- Uses the full filing parser pipeline for each file

### Error Handling
- Graceful handling of malformed files
- Detailed error reporting
- Continues processing even if individual files fail

### Progress Monitoring
- Real-time progress updates
- Detailed logging of each processing step
- Summary statistics at completion

### Flexible Options
- Dry-run mode for testing
- Ability to limit processing for testing
- Custom directory specification

## Testing

### Test with Limited Files

Before processing all files, test with a small subset:

```bash
# Test with just 2 files
python auto_10k_python.py --max-files 2

# See what would be processed without actually processing
python auto_10k_python.py --dry-run
```

### Test with Specific Directory

```bash
# Test with a specific companies directory
python auto_10k_python.py --companies-dir "test_companies" --max-files 5
```

## Troubleshooting

### Common Issues

1. **"Could not import FilingParserPipeline"**
   - Ensure `filing_parser_pipeline.py` is in the same directory as `auto_10k_python.py`

2. **"No 10-K filing files found!"**
   - Check that your directory structure follows the expected pattern
   - Use `--dry-run` to see what the script is looking for
   - Verify the companies directory path

3. **Files failing to process**
   - Check the log files for specific error messages
   - Some files may have formatting issues that prevent parsing
   - The script will continue processing other files

4. **Permission errors**
   - Ensure you have write permissions to the companies directory
   - Run from a location where you can create output folders

### Getting More Information

Use the log files and JSON reports to understand processing results:

```bash
# View the latest log file
type 10k_processing_*.log

# Check the JSON report for detailed results
python -m json.tool 10k_processing_report_*.json
```

## Advanced Usage

### Process All Files

Once you've tested with a few files, process everything:

```bash
python auto_10k_python.py --companies-dir proto-3\companies
```

### Integration with Other Scripts

The processed JSON files can be used with other scripts in your pipeline:

```python
import json
from pathlib import Path

# Load processed 10-K data
def load_processed_10k_data(company_name, year):
    json_files = Path(f"companies/{company_name}/python_output_10k/{year}").glob("*_structured.json")
    for json_file in json_files:
        with open(json_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None

# Example usage
apple_2020_data = load_processed_10k_data("Apple_Inc", "2020")
if apple_2020_data:
    print(f"Loaded data with {len(apple_2020_data.get('parts', []))} parts")
```

## Performance Notes

- Processing time depends on file size and complexity
- Each file typically takes 1-5 seconds to process
- Large batches may take significant time (45 files ≈ 2-10 minutes)
- Use `--max-files` for testing to avoid long waits

## Summary

This script provides a complete automation solution for processing 10-K filings at scale. It handles discovery, processing, organization, logging, and reporting - everything you need to parse your entire collection of 10-K filings efficiently and reliably.
