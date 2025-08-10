# JSON Company Data Merger

A Python script that automatically traverses company directories and merges JSON files by year into consolidated datasets.

## Overview

This script is designed to work with financial data JSON files organized in a directory structure by company and year. It automatically finds all JSON files, groups them by year, and creates a single merged JSON file for each company containing all their data across all available years.

## Directory Structure

The script expects the following directory structure:

```
companies/
├── Apple_Inc/
│   ├── output_10k/
│   │   ├── 2020/
│   │   │   ├── file1_structured.json
│   │   │   └── file2_structured.json
│   │   ├── 2021/
│   │   │   ├── file3_structured.json
│   │   │   └── file4_structured.json
│   │   └── ...
│   ├── output_8k/
│   │   ├── 2020/
│   │   │   └── file5_structured.json
│   │   └── ...
│   └── merged_data.json  ← Output file created here
├── Microsoft_Corp/
│   └── ... (similar structure)
└── Other_Company/
    └── ... (similar structure)
```

## Usage

### Basic Usage

```bash
python combiner_10k.py path/to/companies
```

### With Custom Output Filename

```bash
python combiner_10k.py path/to/companies --output-name custom_merged.json
```

### Get Help

```bash
python combiner_10k.py --help
```

## Features

- **Automatic Directory Traversal**: Recursively finds all JSON files in company directories
- **Year Detection**: Automatically extracts year information from directory structure or filenames
- **Intelligent Merging**: Combines multiple JSON files for the same year intelligently
- **Error Handling**: Gracefully handles malformed JSON files and reports errors
- **Progress Reporting**: Shows detailed progress including loaded files and final statistics
- **UTF-8 Support**: Properly handles unicode characters in JSON files

## Output Format

The script creates a `merged_data.json` file in each company's root directory with the following structure:

```json
{
  "Company Name": {
    "2020": {
      // All 2020 data merged here
    },
    "2021": {
      // All 2021 data merged here
    },
    "2022": {
      // All 2022 data merged here
    }
    // ... more years
  }
}
```

## Example Output

When you run the script, you'll see output like this:

```
🚀 Starting JSON merger for directory: /path/to/companies
📂 Found 10 company directories

📁 Processing company: Apple_Inc
  Found 47 JSON file(s)
  📅 Processing year: 2020
  ✓ Loaded: output_file1_structured.json
  ✓ Loaded: output_file2_structured.json
  📅 Processing year: 2021
  ✓ Loaded: output_file3_structured.json
  ✅ Merged data saved to: /path/to/companies/Apple_Inc/merged_data.json
  📊 Years included: ['2020', '2021', '2022', '2023', '2024', '2025']

📋 Summary:
  ✅ Successfully processed: 9 companies
  ❌ Failed to process: 1 companies
  📁 Output files saved as: merged_data.json in each company folder
```

## Working with Merged Data

After running the script, you can load and work with the merged data:

```python
import json

# Load merged data for a company
with open('companies/Apple_Inc/merged_data.json', 'r', encoding='utf-8') as f:
    apple_data = json.load(f)

# Get company name and available years
company_name = list(apple_data.keys())[0]
years = list(apple_data[company_name].keys())
print(f"Company: {company_name}")
print(f"Available years: {years}")

# Access specific year data
data_2021 = apple_data[company_name]["2021"]
print(f"2021 data available: {list(data_2021.keys())}")
```

## Requirements

- Python 3.6 or higher
- Standard library modules only (no external dependencies)

## Error Handling

The script handles various error conditions:

- **Missing directories**: Reports if the specified directory doesn't exist
- **Malformed JSON**: Skips invalid JSON files and reports errors
- **File access errors**: Handles permission issues gracefully
- **Unicode issues**: Properly handles UTF-8 encoding

## Advanced Features

### Year Detection Logic

The script uses intelligent year detection:

1. First looks for 4-digit years (starting with "20") in the directory path
2. If not found in path, searches the filename
3. Falls back to "unknown" category if year cannot be determined

### Merging Strategy

When multiple JSON files exist for the same year:

1. Files are loaded sequentially
2. Dictionary data is merged intelligently (deeper dictionaries are updated)
3. Conflicts are resolved by taking the last loaded value
4. Non-dictionary data replaces previous values

## Troubleshooting

### Common Issues

1. **"No JSON files found"**: Check that your directory structure matches the expected format
2. **"JSON decode error"**: One or more JSON files are malformed - check the error output for specific files
3. **"Permission denied"**: Ensure the script has read access to input files and write access to output directory
4. **"UnicodeDecodeError"**: The script uses UTF-8 encoding by default; if you have files in other encodings, they may need conversion

### Getting More Information

Run with Python's verbose flag for more detailed error information:

```bash
python -v combiner_10k.py path/to/companies
```

## Example Scripts

See `usage_examples.py` for additional examples of how to use this script programmatically and work with the merged data.
