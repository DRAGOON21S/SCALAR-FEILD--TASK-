#!/usr/bin/env python3
"""
Auto 10-Q Parser Script
Automatically finds all 10-Q filings in companies directories and processes them through the 10-Q parser pipeline
"""

import os
import sys
import json
import shutil
import tempfile
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Tuple
import logging

# Add the current directory to the path so we can import the Filing10QParserPipeline
sys.path.append(str(Path(__file__).parent))

# Try to import the Filing10QParserPipeline from the existing script
try:
    from filing_parser_10q_pipeline import Filing10QParserPipeline
except ImportError:
    print("❌ Error: Could not import Filing10QParserPipeline. Make sure filing_parser_10q_pipeline.py is in the same directory.")
    sys.exit(1)


class Auto10QProcessor:
    """
    Automated processor for finding and parsing all 10-Q filings in companies directories
    """
    
    def __init__(self, companies_root_dir: str = r"C:\Users\shrey\Desktop\ScalerField-Quant\proto-3\companies"):
        self.companies_root = Path(companies_root_dir).resolve()
        self.processed_files = []
        self.failed_files = []
        self.setup_logging()
        
    def setup_logging(self):
        """Setup logging for the process"""
        log_filename = f"10q_processing_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_filename, encoding='utf-8'),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger(__name__)
        self.logger.info(f"Starting Auto 10-Q Processing - Log file: {log_filename}")
    
    def extract_company_info(self, file_path: Path) -> Dict[str, str]:
        """Extract company name, quarter, and year from file path"""
        parts = file_path.parts
        
        # Find company name (should be in companies directory)
        company_idx = None
        for i, part in enumerate(parts):
            if part == "companies" and i + 1 < len(parts):
                company_idx = i + 1
                break
        
        if company_idx is None:
            company_name = "Unknown"
        else:
            company_name = parts[company_idx]
        
        # Find year and quarter from path or filename
        year = "Unknown"
        quarter = "Unknown"
        
        # Check path parts for year
        for part in parts[company_idx + 1:] if company_idx else parts:
            if part.isdigit() and len(part) == 4 and part.startswith('20'):
                year = part
                break
        
        # Check filename for quarter and year patterns
        filename = file_path.stem.upper()
        
        # Extract quarter from filename
        if 'Q1' in filename or '_Q1_' in filename or 'FIRST' in filename:
            quarter = "Q1"
        elif 'Q2' in filename or '_Q2_' in filename or 'SECOND' in filename:
            quarter = "Q2"
        elif 'Q3' in filename or '_Q3_' in filename or 'THIRD' in filename:
            quarter = "Q3"
        elif 'Q4' in filename or '_Q4_' in filename or 'FOURTH' in filename:
            quarter = "Q4"
        
        # Extract year from filename if not found in path
        if year == "Unknown":
            import re
            year_match = re.search(r'20\d{2}', filename)
            if year_match:
                year = year_match.group()
            else:
                year = str(datetime.now().year)
        
        # Default quarter if not found
        if quarter == "Unknown":
            quarter = "Q2"  # Default assumption
        
        return {"company": company_name, "quarter": quarter, "year": year}
    
    def find_all_10q_files(self) -> List[Path]:
        """Find all 10-Q filing text files in the companies directory"""
        self.logger.info(f"🔍 Searching for 10-Q files in: {self.companies_root}")
        
        if not self.companies_root.exists():
            self.logger.error(f"Companies directory not found: {self.companies_root}")
            return []
        
        # Find all .txt files in 10-Q subdirectories
        filing_files = []
        
        for company_dir in self.companies_root.iterdir():
            if not company_dir.is_dir():
                continue
                
            self.logger.info(f"  📁 Scanning company: {company_dir.name}")
            
            # Look for 10-Q directories at any level under the company
            for ten_q_dir in company_dir.rglob("10-Q"):
                if ten_q_dir.is_dir():
                    self.logger.info(f"    📂 Found 10-Q directory: {ten_q_dir}")
                    
                    # Find all .txt files in this 10-Q directory
                    txt_files = list(ten_q_dir.glob("*.txt"))
                    for txt_file in txt_files:
                        filing_files.append(txt_file)
                        self.logger.info(f"      📄 Found filing: {txt_file.name}")
            
            # Also look for 10-Q files directly in quarterly directories
            for quarter_dir in company_dir.iterdir():
                if quarter_dir.is_dir() and any(q in quarter_dir.name.upper() for q in ['Q1', 'Q2', 'Q3', 'Q4', 'QUARTER']):
                    self.logger.info(f"    📂 Found quarterly directory: {quarter_dir}")
                    txt_files = list(quarter_dir.glob("*.txt"))
                    for txt_file in txt_files:
                        if '10-Q' in txt_file.name.upper() or '10Q' in txt_file.name.upper():
                            filing_files.append(txt_file)
                            self.logger.info(f"      📄 Found 10-Q filing: {txt_file.name}")
        
        self.logger.info(f"✅ Found {len(filing_files)} 10-Q filing files total")
        return filing_files
    
    def create_output_directory(self, company_name: str, quarter: str, year: str) -> Path:
        """Create output directory for parsed results"""
        company_dir = self.companies_root / company_name
        output_dir = company_dir / "python_output_10q" / f"{quarter}_{year}"
        output_dir.mkdir(parents=True, exist_ok=True)
        return output_dir
    
    def process_single_filing(self, filing_path: Path) -> bool:
        """Process a single 10-Q filing through the parser pipeline"""
        try:
            # Extract company info from path
            info = self.extract_company_info(filing_path)
            company_name = info["company"]
            quarter = info["quarter"]
            year = info["year"]
            
            self.logger.info(f"📄 Processing: {filing_path.name}")
            self.logger.info(f"   🏢 Company: {company_name}")
            self.logger.info(f"   📅 Period: {quarter} {year}")
            
            # Create output directory
            output_dir = self.create_output_directory(company_name, quarter, year)
            
            # Create unique JSON output name
            filing_stem = filing_path.stem
            json_output_name = f"{filing_stem}_{quarter}_{year}_structured.json"
            json_output_path = str(output_dir / json_output_name)
            
            # Create a temporary directory for intermediate files that we'll clean up
            with tempfile.TemporaryDirectory(prefix="temp_10q_parsing_") as temp_dir:
                # Set up pipeline with temporary directory for intermediate files
                # Use a unique name within temp_dir to avoid conflicts
                temp_parsing_dir = os.path.join(temp_dir, f"parsing_{company_name}_{quarter}_{year}")
                pipeline = Filing10QParserPipeline(
                    input_file_path=str(filing_path),
                    output_dir=temp_parsing_dir,
                    company_name=company_name,
                    quarter=quarter,
                    year=year
                )
                
                # Run the pipeline - this will create the final JSON in the temp directory
                # and we'll move it to the final location
                temp_json_path = os.path.join(temp_dir, json_output_name)
                final_json_path = pipeline.run_pipeline(temp_json_path)
                
                # Move the JSON from temp directory to final location
                shutil.move(temp_json_path, json_output_path)
                
                # The temp_dir with folder structure will be automatically cleaned up
            
            # Verify the JSON file was created
            if not Path(json_output_path).exists():
                raise FileNotFoundError(f"Expected JSON output not created: {json_output_path}")
            
            # Record success
            self.processed_files.append({
                "input_file": str(filing_path),
                "company": company_name,
                "quarter": quarter,
                "year": year,
                "json_output": json_output_path,
                "status": "success"
            })
            
            self.logger.info(f"✅ Successfully processed: {filing_path.name}")
            self.logger.info(f"    📋 JSON saved to: {json_output_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Error processing {filing_path.name}: {str(e)}")
            
            # Record failure
            self.failed_files.append({
                "input_file": str(filing_path),
                "company": info.get("company", "Unknown"),
                "quarter": info.get("quarter", "Unknown"),
                "year": info.get("year", "Unknown"),
                "error": str(e),
                "status": "failed"
            })
            return False
    
    def process_all_filings(self, max_files: int = None) -> Dict[str, Any]:
        """Process all found 10-Q filings"""
        filing_files = self.find_all_10q_files()
        
        if not filing_files:
            self.logger.warning("No 10-Q filing files found!")
            return {"total": 0, "processed": 0, "failed": 0}
        
        # Limit files if specified
        if max_files and max_files > 0:
            filing_files = filing_files[:max_files]
            self.logger.info(f"🔄 Processing first {max_files} files only")
        
        total_files = len(filing_files)
        self.logger.info(f"🚀 Starting to process {total_files} 10-Q filing files")
        self.logger.info("=" * 80)
        
        # Process each file
        for i, filing_path in enumerate(filing_files, 1):
            self.logger.info(f"\n📊 Progress: {i}/{total_files}")
            self.logger.info("-" * 60)
            
            success = self.process_single_filing(filing_path)
            
            if success:
                self.logger.info(f"✅ File {i}/{total_files} completed successfully")
            else:
                self.logger.info(f"❌ File {i}/{total_files} failed")
        
        # Generate summary
        summary = {
            "total_files_found": total_files,
            "successfully_processed": len(self.processed_files),
            "failed_to_process": len(self.failed_files),
            "success_rate": len(self.processed_files) / total_files * 100 if total_files > 0 else 0,
            "processed_files": self.processed_files,
            "failed_files": self.failed_files
        }
        
        return summary
    
    def save_processing_report(self, summary: Dict[str, Any]) -> str:
        """Save a detailed processing report"""
        report_filename = f"10q_processing_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        # Add timestamp to summary
        summary["processing_date"] = datetime.now().isoformat()
        summary["companies_directory"] = str(self.companies_root)
        
        # Save report
        with open(report_filename, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        
        return report_filename
    
    def print_summary(self, summary: Dict[str, Any]):
        """Print a formatted summary of processing results"""
        print("\n" + "=" * 80)
        print("🎯 AUTO 10-Q PROCESSING SUMMARY")
        print("=" * 80)
        print(f"📁 Companies Directory: {self.companies_root}")
        print(f"📊 Total Files Found: {summary['total_files_found']}")
        print(f"✅ Successfully Processed: {summary['successfully_processed']}")
        print(f"❌ Failed to Process: {summary['failed_to_process']}")
        print(f"📈 Success Rate: {summary['success_rate']:.1f}%")
        print("=" * 80)
        
        # Show breakdown by company and quarter
        if self.processed_files:
            print("\n📋 PROCESSING BREAKDOWN BY COMPANY:")
            company_stats = {}
            for file_info in self.processed_files:
                company = file_info["company"]
                quarter = file_info["quarter"]
                year = file_info["year"]
                period = f"{quarter} {year}"
                
                if company not in company_stats:
                    company_stats[company] = {"processed": 0, "periods": set()}
                company_stats[company]["processed"] += 1
                company_stats[company]["periods"].add(period)
            
            for company, stats in sorted(company_stats.items()):
                periods_str = ", ".join(sorted(stats["periods"]))
                print(f"  🏢 {company}: {stats['processed']} filings ({periods_str})")
        
        # Show failed files if any
        if self.failed_files:
            print("\n❌ FAILED FILES:")
            for file_info in self.failed_files:
                period = f"{file_info['quarter']} {file_info['year']}"
                print(f"  • {file_info['input_file']} ({period}): {file_info['error']}")
        
        print("\n" + "=" * 80)


def main():
    """Main function for command line usage"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Automatically find and process all 10-Q filings in companies directories',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python auto_10q.py
  python auto_10q.py --companies-dir "C:\\path\\to\\companies"
  python auto_10q.py --max-files 5
  python auto_10q.py --companies-dir companies --max-files 10
        """
    )
    
    parser.add_argument(
        '--companies-dir', 
        default=r'C:\Users\shrey\Desktop\ScalerField-Quant\proto-3\companies',
        help='Path to the companies directory (default: C:\\Users\\shrey\\Desktop\\ScalerField-Quant\\proto-3\\companies)'
    )
    
    parser.add_argument(
        '--max-files',
        type=int,
        help='Maximum number of files to process (for testing)'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Only find files, don\'t process them'
    )
    
    args = parser.parse_args()
    
    try:
        # Create processor
        processor = Auto10QProcessor(args.companies_dir)
        
        if args.dry_run:
            # Just find files and show what would be processed
            filing_files = processor.find_all_10q_files()
            print(f"\n📋 DRY RUN - Found {len(filing_files)} files that would be processed:")
            for i, file_path in enumerate(filing_files, 1):
                info = processor.extract_company_info(file_path)
                period = f"{info['quarter']} {info['year']}"
                print(f"  {i:2d}. {info['company']} ({period}) - {file_path.name}")
            return 0
        
        # Process all filings
        summary = processor.process_all_filings(max_files=args.max_files)
        
        # Save report
        report_file = processor.save_processing_report(summary)
        
        # Print summary
        processor.print_summary(summary)
        print(f"📄 Detailed report saved to: {report_file}")
        
        # Return appropriate exit code
        return 0 if summary['failed_to_process'] == 0 else 1
        
    except KeyboardInterrupt:
        print("\n⚠️  Processing interrupted by user")
        return 130
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
