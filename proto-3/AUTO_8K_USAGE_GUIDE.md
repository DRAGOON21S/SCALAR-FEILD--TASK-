# Auto 8-K Processor - Usage Guide

## Overview
The `auto_8k.py` script automatically processes all 8-K filing documents in your directory structure using Google Gemini AI to convert them into structured JSON format.

## Features
- **Automatic Discovery**: Scans the entire directory structure to find all 8-K files
- **Parallel Processing**: Uses multithreading for faster processing (configurable)
- **Smart Skip Logic**: Automatically skips already processed files (unless forced)
- **Comprehensive Logging**: Detailed logging with progress tracking
- **Filtering Options**: Process specific companies or years only
- **Output Organization**: Creates organized output directory structure
- **Error Handling**: Robust error handling with detailed reporting

## Directory Structure
The script expects this directory structure:
```
proto-3/
├── companies/
│   ├── Apple_Inc/
│   │   ├── 2020/
│   │   │   └── 8-K/
│   │   │       ├── output_file1.txt
│   │   │       └── output_file2.txt
│   │   ├── 2021/
│   │   │   └── 8-K/
│   │   │       └── ...
│   │   └── output_8k/          # Auto-created output folder
│   │       ├── 2020/
│   │       └── 2021/
│   │           ├── output_file1_structured.json
│   │           └── output_file2_structured.json
│   ├── Microsoft_Corp/
│   └── ...other companies
├── auto_8k.py
└── 8-k_jsonner.py
```

## Usage Examples

### Basic Usage
```bash
# Process all 8-K files for all companies
python auto_8k.py

# Dry run to see what would be processed
python auto_8k.py --dry-run
```

### Filtering Options
```bash
# Process only Apple Inc files
python auto_8k.py -c "Apple_Inc"

# Process only 2021 files
python auto_8k.py -y "2021"

# Process Apple Inc files from 2021 only
python auto_8k.py -c "Apple_Inc" -y "2021"
```

### Processing Control
```bash
# Force reprocess already processed files
python auto_8k.py -f

# Use more workers for faster processing (be careful with API limits)
python auto_8k.py -w 3

# Use custom API key
python auto_8k.py -k "your_gemini_api_key"
```

### Advanced Examples
```bash
# Process all Microsoft files with 2 workers and custom API key
python auto_8k.py -c "MICROSOFT_CORP" -w 2 -k "your_api_key"

# Force reprocess all Apple files from 2020-2022
python auto_8k.py -c "Apple_Inc" -f
```

## Output Format
Each processed file generates a structured JSON with this hierarchy:
```json
{
  "COMPANY_NAME": {
    "YEAR": {
      "FORM": "8-K",
      "CATEGORIES": {
        "Section X - Category Name": {
          "ITEMS": {
            "Item X.XX - Item Description": {
              "content": "main content",
              "subsections": {
                "subsection_name": "subsection content"
              }
            }
          }
        }
      }
    }
  }
}
```

## Command Line Options
- `-k, --api-key`: Google Gemini API key
- `-d, --directory`: Base directory containing companies folder
- `-w, --workers`: Number of parallel processing threads (default: 2)
- `-f, --force`: Force reprocessing of already processed files
- `-c, --company`: Process files only for this company
- `-y, --year`: Process files only for this year
- `--dry-run`: Show what would be processed without actually processing

## Output Files
- **JSON Files**: `companies/{COMPANY}/output_8k/{YEAR}/{filename}_structured.json`
- **Log Files**: `8k_processing_YYYYMMDD_HHMMSS.log`
- **Report Files**: `8k_processing_report_YYYYMMDD_HHMMSS.json`

## Performance Tips
1. **API Rate Limits**: Use fewer workers (1-2) to avoid hitting Gemini API limits
2. **Large Datasets**: Process by company or year to manage large datasets
3. **Resume Processing**: The script automatically skips processed files, so you can stop and resume
4. **Error Recovery**: Check the log files for any failed files and reprocess them

## Monitoring Progress
The script provides real-time progress updates:
- Current file being processed
- Success/failure counts
- Overall progress percentage
- Processing time estimates

## Error Handling
- **Failed Files**: Listed in the final report with error details
- **Corrupted Output**: Automatically detected and marked for reprocessing
- **API Errors**: Logged with detailed error messages
- **File Access**: Handles file permission and access issues

## Example Session
```bash
$ python auto_8k.py -c "Apple_Inc" -y "2021" -w 1
2025-08-09 14:54:06,312 - INFO - Scanning for 8-K files...
2025-08-09 14:54:06,329 - INFO - Found 397 8-K files to process
2025-08-09 14:54:06,330 - INFO - Filtered to company: Apple_Inc (42 files)
2025-08-09 14:54:06,330 - INFO - Filtered to year: 2021 (9 files)
2025-08-09 14:54:06,330 - INFO - Starting processing of 9 files with 1 workers
2025-08-09 14:54:25,871 - INFO - Progress: 1/9 (11.1%) - Success: 1, Failed: 0
...
============================================================
PROCESSING COMPLETE - FINAL REPORT
============================================================
Total processing time: 0:05:23
Files processed successfully: 9
Files failed: 0
Companies processed: 1
  Apple_Inc: 9/9 files
```

## Troubleshooting
- **Import Errors**: Ensure `8-k_jsonner.py` is in the same directory
- **API Errors**: Check your Gemini API key and rate limits
- **Permission Errors**: Ensure write access to the output directories
- **Unicode Errors**: These are cosmetic logging issues and don't affect processing
