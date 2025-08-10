import os
import json
import sys
import time
import threading
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging
from typing import List, Tuple, Dict
import subprocess
import importlib.util

class Auto8KProcessor:
    def __init__(self, api_key: str, base_directory: str = None, max_workers: int = 3):
        """
        Initialize the automatic 8-K processor
        
        Args:
            api_key: Google Gemini API key
            base_directory: Base directory containing companies folder (defaults to current directory)
            max_workers: Maximum number of parallel processing threads
        """
        self.api_key = api_key
        self.base_directory = Path(base_directory) if base_directory else Path(__file__).parent
        self.companies_dir = self.base_directory / "companies"
        self.max_workers = max_workers
        
        # Setup logging first
        self.setup_logging()
        
        # Import the processor from 8-k_jsonner.py
        self.processor = self._import_processor()
        
        # Thread lock for file operations
        self.file_lock = threading.Lock()
        
        # Processing statistics
        self.stats = {
            'total_files': 0,
            'processed_files': 0,
            'failed_files': 0,
            'skipped_files': 0,
            'companies_processed': set(),
            'start_time': None,
            'end_time': None
        }

    def _import_processor(self):
        """Import FinancialDataProcessor from 8-k_jsonner.py"""
        try:
            # Get the path to 8-k_jsonner.py
            jsonner_path = self.base_directory / "8-k_jsonner.py"
            if not jsonner_path.exists():
                raise FileNotFoundError(f"8-k_jsonner.py not found at {jsonner_path}")
            
            # Import the module
            spec = importlib.util.spec_from_file_location("jsonner", str(jsonner_path))
            jsonner_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(jsonner_module)
            
            # Return an instance of the processor
            return jsonner_module.FinancialDataProcessor(self.api_key)
        except Exception as e:
            self.logger.error(f"Failed to import FinancialDataProcessor: {e}")
            raise

    def setup_logging(self):
        """Setup logging configuration"""
        log_filename = f"8k_processing_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_filename),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger(__name__)

    def find_all_8k_files(self) -> List[Tuple[str, str, str, str]]:
        """
        Find all 8-K files in the directory structure
        
        Returns:
            List of tuples: (company_name, year, file_path, output_path)
        """
        files_found = []
        
        if not self.companies_dir.exists():
            self.logger.error(f"Companies directory not found: {self.companies_dir}")
            return files_found
        
        self.logger.info(f"Scanning for 8-K files in: {self.companies_dir}")
        
        for company_dir in self.companies_dir.iterdir():
            if not company_dir.is_dir():
                continue
                
            company_name = company_dir.name
            self.logger.info(f"Processing company: {company_name}")
            
            # Create output directory for this company
            output_base = company_dir / "output_8k"
            output_base.mkdir(exist_ok=True)
            
            for year_dir in company_dir.iterdir():
                if not year_dir.is_dir() or not year_dir.name.isdigit():
                    continue
                    
                year = year_dir.name
                eight_k_dir = year_dir / "8-K"
                
                if not eight_k_dir.exists():
                    self.logger.debug(f"No 8-K directory found for {company_name}/{year}")
                    continue
                
                # Create year-specific output directory
                year_output_dir = output_base / year
                year_output_dir.mkdir(exist_ok=True)
                
                # Find all .txt files in the 8-K directory
                for file_path in eight_k_dir.glob("*.txt"):
                    output_filename = f"{file_path.stem}_structured.json"
                    output_path = year_output_dir / output_filename
                    
                    files_found.append((company_name, year, str(file_path), str(output_path)))
        
        self.stats['total_files'] = len(files_found)
        self.logger.info(f"Found {len(files_found)} 8-K files to process")
        return files_found

    def should_skip_file(self, output_path: str, force_reprocess: bool = False) -> bool:
        """
        Check if file should be skipped (already processed)
        
        Args:
            output_path: Path to the output JSON file
            force_reprocess: If True, reprocess even if output exists
            
        Returns:
            True if file should be skipped
        """
        if force_reprocess:
            return False
            
        if os.path.exists(output_path):
            # Check if the output file is valid JSON and not empty
            try:
                with open(output_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if data and len(str(data)) > 100:  # Basic validation
                        return True
            except (json.JSONDecodeError, Exception):
                # If file is corrupted, reprocess it
                self.logger.warning(f"Corrupted output file found, will reprocess: {output_path}")
                
        return False

    def process_single_file(self, company_name: str, year: str, input_path: str, output_path: str) -> Dict:
        """
        Process a single 8-K file
        
        Args:
            company_name: Name of the company
            year: Year of the filing
            input_path: Path to the input 8-K text file
            output_path: Path for the output JSON file
            
        Returns:
            Dictionary with processing result
        """
        result = {
            'company': company_name,
            'year': year,
            'input_file': input_path,
            'output_file': output_path,
            'status': 'unknown',
            'error': None,
            'processing_time': 0,
            'file_size': 0
        }
        
        start_time = time.time()
        
        try:
            # Get file size
            result['file_size'] = os.path.getsize(input_path)
            
            self.logger.info(f"Processing: {company_name}/{year}/{os.path.basename(input_path)}")
            
            # Use thread lock to prevent conflicts
            with self.file_lock:
                # Process the file using the existing processor
                self.processor.process_file(input_path, output_path)
            
            # Verify the output was created and is valid
            if os.path.exists(output_path):
                with open(output_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if data:
                        result['status'] = 'success'
                        self.stats['processed_files'] += 1
                        self.stats['companies_processed'].add(company_name)
                        self.logger.info(f"✓ Successfully processed: {os.path.basename(input_path)}")
                    else:
                        result['status'] = 'failed'
                        result['error'] = 'Empty JSON output'
                        self.stats['failed_files'] += 1
            else:
                result['status'] = 'failed'
                result['error'] = 'Output file not created'
                self.stats['failed_files'] += 1
                
        except Exception as e:
            result['status'] = 'failed'
            result['error'] = str(e)
            self.stats['failed_files'] += 1
            self.logger.error(f"❌ Failed to process {input_path}: {str(e)}")
            
        finally:
            result['processing_time'] = time.time() - start_time
            
        return result

    def process_all_files(self, force_reprocess: bool = False, filter_company: str = None, filter_year: str = None):
        """
        Process all 8-K files found in the directory structure
        
        Args:
            force_reprocess: If True, reprocess files even if output already exists
            filter_company: If provided, only process files for this company
            filter_year: If provided, only process files for this year
        """
        self.stats['start_time'] = datetime.now()
        
        # Find all 8-K files
        files_to_process = self.find_all_8k_files()
        
        if not files_to_process:
            self.logger.warning("No 8-K files found to process")
            return
        
        # Apply filters
        if filter_company:
            files_to_process = [f for f in files_to_process if f[0].lower() == filter_company.lower()]
            self.logger.info(f"Filtered to company: {filter_company} ({len(files_to_process)} files)")
            
        if filter_year:
            files_to_process = [f for f in files_to_process if f[1] == filter_year]
            self.logger.info(f"Filtered to year: {filter_year} ({len(files_to_process)} files)")
        
        # Filter out files that should be skipped
        if not force_reprocess:
            original_count = len(files_to_process)
            files_to_process = [f for f in files_to_process if not self.should_skip_file(f[3], force_reprocess)]
            skipped_count = original_count - len(files_to_process)
            self.stats['skipped_files'] = skipped_count
            if skipped_count > 0:
                self.logger.info(f"Skipping {skipped_count} already processed files")
        
        if not files_to_process:
            self.logger.info("All files have already been processed")
            return
        
        self.logger.info(f"Starting processing of {len(files_to_process)} files with {self.max_workers} workers")
        
        # Process files using ThreadPoolExecutor
        results = []
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all tasks
            future_to_file = {
                executor.submit(self.process_single_file, company, year, input_path, output_path): 
                (company, year, input_path, output_path)
                for company, year, input_path, output_path in files_to_process
            }
            
            # Process completed tasks
            for future in as_completed(future_to_file):
                result = future.result()
                results.append(result)
                
                # Progress update
                completed = len(results)
                total = len(files_to_process)
                progress = (completed / total) * 100
                
                self.logger.info(f"Progress: {completed}/{total} ({progress:.1f}%) - "
                               f"Success: {self.stats['processed_files']}, "
                               f"Failed: {self.stats['failed_files']}")
        
        self.stats['end_time'] = datetime.now()
        self.generate_processing_report(results)

    def generate_processing_report(self, results: List[Dict]):
        """Generate a comprehensive processing report"""
        self.logger.info("="*60)
        self.logger.info("PROCESSING COMPLETE - FINAL REPORT")
        self.logger.info("="*60)
        
        # Time statistics
        processing_time = self.stats['end_time'] - self.stats['start_time']
        self.logger.info(f"Total processing time: {processing_time}")
        
        # File statistics
        self.logger.info(f"Total files found: {self.stats['total_files']}")
        self.logger.info(f"Files processed successfully: {self.stats['processed_files']}")
        self.logger.info(f"Files failed: {self.stats['failed_files']}")
        self.logger.info(f"Files skipped (already processed): {self.stats['skipped_files']}")
        
        # Company statistics
        self.logger.info(f"Companies processed: {len(self.stats['companies_processed'])}")
        for company in sorted(self.stats['companies_processed']):
            company_files = [r for r in results if r['company'] == company]
            successful = len([r for r in company_files if r['status'] == 'success'])
            total = len(company_files)
            self.logger.info(f"  {company}: {successful}/{total} files")
        
        # Error summary
        if self.stats['failed_files'] > 0:
            self.logger.info("\nFAILED FILES:")
            for result in results:
                if result['status'] == 'failed':
                    self.logger.error(f"  {result['input_file']}: {result['error']}")
        
        # Save detailed report to JSON
        report_file = f"8k_processing_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        report_data = {
            'summary': {k: (v if not isinstance(v, set) else list(v)) for k, v in self.stats.items()},
            'detailed_results': results,
            'processing_time_seconds': processing_time.total_seconds()
        }
        
        try:
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(report_data, f, indent=2, default=str)
            self.logger.info(f"Detailed report saved to: {report_file}")
        except Exception as e:
            self.logger.error(f"Failed to save report: {e}")

def main():
    """Main function with command line interface"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Automatically process all 8-K files in directory structure')
    parser.add_argument('-k', '--api-key', 
                       default="AIzaSyCg2t8_IljYhBfFirTGZNtIsarWj8jgxSY",
                       help='Google Gemini API key')
    parser.add_argument('-d', '--directory', 
                       help='Base directory containing companies folder (default: current directory)')
    parser.add_argument('-w', '--workers', type=int, default=2,
                       help='Maximum number of parallel processing threads (default: 2)')
    parser.add_argument('-f', '--force', action='store_true',
                       help='Force reprocessing of already processed files')
    parser.add_argument('-c', '--company',
                       help='Process files only for this company (case-insensitive)')
    parser.add_argument('-y', '--year',
                       help='Process files only for this year')
    parser.add_argument('--dry-run', action='store_true',
                       help='Show what would be processed without actually processing')
    
    args = parser.parse_args()
    
    try:
        # Initialize the processor
        processor = Auto8KProcessor(
            api_key=args.api_key,
            base_directory=args.directory,
            max_workers=args.workers
        )
        
        if args.dry_run:
            # Just find and list files
            files = processor.find_all_8k_files()
            print(f"\nDry run - Found {len(files)} files to process:")
            
            # Group by company for better display
            by_company = {}
            for company, year, input_path, output_path in files:
                if company not in by_company:
                    by_company[company] = []
                
                skip_reason = ""
                if processor.should_skip_file(output_path, args.force):
                    skip_reason = " (would be skipped - already processed)"
                
                by_company[company].append((year, os.path.basename(input_path), skip_reason))
            
            for company, file_list in by_company.items():
                print(f"\n  {company}:")
                for year, filename, skip_reason in file_list:
                    print(f"    {year}: {filename}{skip_reason}")
            return
        
        # Process all files
        processor.process_all_files(
            force_reprocess=args.force,
            filter_company=args.company,
            filter_year=args.year
        )
        
    except KeyboardInterrupt:
        print("\n🛑 Processing interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()

# Example usage:
"""
# Basic usage - process all files
python auto_8k.py

# Process only Apple Inc files
python auto_8k.py -c "Apple_Inc"

# Process only 2021 files
python auto_8k.py -y "2021"

# Force reprocess all files (even if already processed)
python auto_8k.py -f

# Use more workers for faster processing (be careful not to overwhelm the API)
python auto_8k.py -w 3

# Dry run to see what would be processed
python auto_8k.py --dry-run

# Process specific company and year with custom API key
python auto_8k.py -c "Apple_Inc" -y "2021" -k "your_api_key"
"""
