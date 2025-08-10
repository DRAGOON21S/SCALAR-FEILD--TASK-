# Gemini 10K Processing System

This system processes 10K filing data through Google's Gemini AI to automatically classify and restructure sections according to SEC standards.

## 🚀 Quick Start

### Step 1: Set up Gemini API Key

1. **Get API Key:**

   - Go to [Google AI Studio](https://makersuite.google.com/app/apikey)
   - Sign in with your Google account
   - Click "Create API key"
   - Copy the generated key

2. **Set Environment Variable:**

   ```powershell
   $env:GEMINI_API_KEY='your-api-key-here'
   ```

3. **Or run the setup script:**
   ```powershell
   python setup_gemini.py
   ```

### Step 2: Test Connection

```powershell
python test_gemini.py
```

This will verify:

- ✅ API key is working
- ✅ Gemini can classify sections correctly

### Step 3: Process All Files

```powershell
python gemini_processor.py
```

This will:

- Read all JSON files from `final_10k/` directory
- Send each section to Gemini for classification
- Save restructured files to `gemini_10k/` directory

## 📁 Directory Structure

```
├── final_10k/                    # Input: Original merged company files
│   ├── Apple_Inc_10k.json
│   ├── NVIDIA_CORP_10k.json
│   └── ...
├── gemini_10k/                   # Output: Gemini-processed files
│   ├── Apple_Inc_10k.json
│   ├── NVIDIA_CORP_10k.json
│   └── ...
├── gemini_processor.py           # Main processing script
├── test_gemini.py               # API connection test
├── setup_gemini.py              # API key setup helper
└── README_Gemini_Processing.md  # This file
```

## 🔄 Processing Flow

1. **Input**: Original sections with simplified categories (e.g., "business", "risk_factors")
2. **Gemini Analysis**: AI analyzes content and determines proper classification
3. **Output**: Enhanced sections with official SEC part/item classifications

### Example Transformation:

**Before (simplified category):**

```json
{
  "category": "business",
  "content": "Item 1. Business\nThe Company designs...",
  "section_id": "Section_1_Item_1._Business"
}
```

**After (Gemini-enhanced):**

```json
{
  "category": "business",
  "content": "Item 1. Business\nThe Company designs...",
  "section_id": "Section_1_Item_1._Business",
  "gemini_part_name": "Part I: Business and Risk Factors",
  "gemini_item_name": "Item 1. Business",
  "gemini_confidence": "high"
}
```

## 📊 Classification Standards

### Valid Parts:

- **Part I: Business and Risk Factors**
- **Part II: Financial Information**
- **Part III: Governance**
- **Part IV: Exhibits and Schedules**

### Valid Items:

- Item 1. Business
- Item 1A. Risk Factors
- Item 1B. Unresolved Staff Comments
- Item 2. Properties
- Item 3. Legal Proceedings
- Item 4. Mine Safety Disclosures
- Item 5. Market for Registrant's Common Equity...
- Item 6. [Reserved]
- Item 7. Management's Discussion and Analysis (MD&A)
- Item 7A. Quantitative and Qualitative Disclosures About Market Risk
- Item 8. Financial Statements and Supplementary Data
- Item 9. Changes in and Disagreements With Accountants
- Item 9A. Controls and Procedures
- Item 9B. Other Information
- Item 9C. Disclosure Regarding Foreign Jurisdictions
- Item 10. Directors, Executive Officers and Corporate Governance
- Item 11. Executive Compensation
- Item 12. Security Ownership
- Item 13. Certain Relationships and Related Transactions
- Item 14. Principal Accountant Fees and Services
- Item 15. Exhibits, Financial Statement Schedules
- Item 16. Form 10-K Summary

## ⚙️ Features

- **Intelligent Classification**: Gemini AI analyzes content to determine proper SEC classifications
- **Batch Processing**: Processes all companies automatically
- **Error Handling**: Includes retry logic and fallback classifications
- **Rate Limiting**: Built-in delays to respect API limits
- **Progress Tracking**: Detailed console output shows processing progress
- **Validation**: Ensures all classifications match official SEC standards

## 🔧 Configuration

### Rate Limiting

The script includes 1-second delays between API calls to avoid rate limits. You can adjust this in `gemini_processor.py`:

```python
time.sleep(1)  # Adjust delay as needed
```

### Retry Logic

Failed classifications are retried up to 3 times with exponential backoff.

### Default Fallbacks

If Gemini classification fails, the system uses intelligent defaults based on the original category names.

## 📈 Expected Results

After processing, each company file will have:

- ✅ Original structure preserved
- ✅ New Gemini classifications added
- ✅ Confidence scores for each classification
- ✅ Proper SEC part/item assignments

## 🎯 Usage Tips

1. **API Limits**: Free tier has daily limits. Monitor usage at [Google AI Studio](https://makersuite.google.com/app/apikey)
2. **Large Files**: Processing may take time due to rate limiting
3. **Validation**: Check confidence scores - "low" scores may need manual review
4. **Backup**: Original files remain unchanged in `final_10k/`

## 🚨 Troubleshooting

### Common Issues:

**"API key not set"**

- Solution: Run `python setup_gemini.py` or set `$env:GEMINI_API_KEY`

**"Rate limit exceeded"**

- Solution: Wait and retry, or increase delay in script

**"JSON decode error"**

- Solution: Script will retry automatically with fallback classification

**"No JSON files found"**

- Solution: Ensure files exist in `final_10k/` directory

### Getting Help:

1. Run `python test_gemini.py` to verify setup
2. Check API key at [Google AI Studio](https://makersuite.google.com/app/apikey)
3. Review console output for specific error messages

## 🎉 Success Metrics

- ✅ All companies processed
- ✅ High confidence scores (>80% "high" confidence)
- ✅ Proper SEC classifications assigned
- ✅ No data loss during processing
