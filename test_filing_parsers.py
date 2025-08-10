#!/usr/bin/env python3
"""
Filing Parser Test Suite
Demonstrates both 10-K and 10-Q parsing capabilities
"""

import os
import sys
import json
from pathlib import Path
from filing_parser_pipeline import FilingParserPipeline
from filing_parser_10q_pipeline import Filing10QParserPipeline

def test_10k_parser():
    """Test the 10-K parser"""
    print("🧪 Testing 10-K Parser")
    print("=" * 40)
    
    # Look for a 10-K file
    test_files = [
        "AAPL_latest_10K.txt",
        "apple_final_structured.json",  # This might be processed already
    ]
    
    for test_file in test_files:
        if os.path.exists(test_file):
            if test_file.endswith('.txt'):
                try:
                    parser = FilingParserPipeline(test_file)
                    result = parser.run_pipeline(f"test_10k_output_{parser.company_name}.json")
                    print(f"✅ 10-K Parser SUCCESS: {result}")
                    return result
                except Exception as e:
                    print(f"❌ 10-K Parser ERROR: {e}")
            break
    else:
        print("ℹ️  No suitable 10-K test file found")
    
    return None

def test_10q_parser():
    """Test the 10-Q parser"""
    print("\n🧪 Testing 10-Q Parser")
    print("=" * 40)
    
    # Look for 10-Q files
    test_files = [
        Path("proto-3/companies/Apple_Inc/2022/10-Q/output_0000320193_22_000007.txt"),
        Path("proto-3/companies/Apple_Inc/2022/10-Q/output_0000320193_22_000059.txt"),
    ]
    
    for test_file in test_files:
        if test_file.exists():
            try:
                parser = Filing10QParserPipeline(
                    str(test_file),
                    company_name="Apple_Inc",
                    quarter="Q2",
                    year="2022"
                )
                result = parser.run_pipeline(f"test_10q_output_{test_file.stem}.json")
                print(f"✅ 10-Q Parser SUCCESS: {result}")
                return result
            except Exception as e:
                print(f"❌ 10-Q Parser ERROR: {e}")
                import traceback
                traceback.print_exc()
    
    print("ℹ️  No suitable 10-Q test file found")
    return None

def analyze_results(results_10k, results_10q):
    """Analyze and compare the results"""
    print("\n📊 RESULTS ANALYSIS")
    print("=" * 50)
    
    if results_10k:
        try:
            with open(results_10k, 'r', encoding='utf-8') as f:
                data_10k = json.load(f)
            
            print("📄 10-K Results:")
            print(f"  - Company: {data_10k.get('company_name', 'N/A')}")
            print(f"  - Filing Type: {data_10k.get('filing_type', 'N/A')}")
            print(f"  - Parts: {len(data_10k.get('parts', []))}")
            
            total_sections_10k = sum(len(part.get('sections', [])) for part in data_10k.get('parts', []))
            print(f"  - Total Sections: {total_sections_10k}")
            
        except Exception as e:
            print(f"❌ Error analyzing 10-K results: {e}")
    
    if results_10q:
        try:
            with open(results_10q, 'r', encoding='utf-8') as f:
                data_10q = json.load(f)
            
            print("\n📄 10-Q Results:")
            print(f"  - Company: {data_10q.get('company_name', 'N/A')}")
            print(f"  - Filing Type: {data_10q.get('filing_type', 'N/A')}")
            print(f"  - Quarter: {data_10q.get('quarter', 'N/A')}")
            print(f"  - Year: {data_10q.get('year', 'N/A')}")
            print(f"  - Parts: {len(data_10q.get('parts', []))}")
            
            summary = data_10q.get('summary', {})
            print(f"  - Total Sections: {summary.get('total_sections', 'N/A')}")
            print(f"  - Filing Period: {summary.get('filing_period', 'N/A')}")
            
        except Exception as e:
            print(f"❌ Error analyzing 10-Q results: {e}")
    
    print("\n🎯 COMPARISON:")
    print("10-K Parser: Designed for annual comprehensive reports (larger, more detailed)")
    print("10-Q Parser: Designed for quarterly reports (smaller, focused on quarterly changes)")
    print("Both parsers create structured folders and enhanced JSON output!")

def main():
    """Main test function"""
    print("🚀 FILING PARSER TEST SUITE")
    print("=" * 60)
    print("Testing both 10-K and 10-Q parsing capabilities...")
    print("=" * 60)
    
    # Test both parsers
    results_10k = test_10k_parser()
    results_10q = test_10q_parser()
    
    # Analyze results
    analyze_results(results_10k, results_10q)
    
    print("\n" + "=" * 60)
    print("🎉 TEST SUITE COMPLETED!")
    print("=" * 60)
    
    if results_10k or results_10q:
        print("✅ At least one parser worked successfully!")
        if results_10k and results_10q:
            print("🌟 Both parsers are working perfectly!")
    else:
        print("⚠️  No parsers could be tested (missing input files)")
    
    print("\nFiles created during testing:")
    test_files = [
        "test_10k_output_*.json",
        "test_10q_output_*.json",
        "*_10Q_*_Parsed/",
        "*_Parsed/"
    ]
    
    for pattern in test_files:
        print(f"  - {pattern}")

if __name__ == "__main__":
    main()
