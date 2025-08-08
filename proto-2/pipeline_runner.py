#!/usr/bin/env python3
"""
Complete Pipeline Runner for SEC Filings MongoDB System
Orchestrates the entire data pipeline from ingestion to analysis.
"""

import sys
import time
import argparse
from datetime import datetime
from pathlib import Path
import subprocess
import logging
from typing import List, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('pipeline_run.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class PipelineRunner:
    """Orchestrates the complete SEC filings pipeline."""
    
    def __init__(self):
        """Initialize pipeline runner."""
        self.start_time = None
        self.steps_completed = []
        self.errors = []
    
    def run_complete_pipeline(self, 
                            tickers: List[str] = ["AAPL", "MSFT"],
                            years: List[int] = [2024, 2023],
                            skip_ingestion: bool = False,
                            skip_embeddings: bool = False,
                            skip_export: bool = False,
                            start_api: bool = False,
                            start_dashboard: bool = False):
        """
        Run the complete pipeline.
        
        Args:
            tickers: List of tickers to process
            years: List of years to process
            skip_ingestion: Skip data ingestion step
            skip_embeddings: Skip embeddings generation
            skip_export: Skip data export
            start_api: Start FastAPI server
            start_dashboard: Start Streamlit dashboard
        """
        self.start_time = datetime.now()
        logger.info("="*60)
        logger.info("SEC FILINGS PIPELINE - STARTING")
        logger.info("="*60)
        logger.info(f"Tickers: {', '.join(tickers)}")
        logger.info(f"Years: {', '.join(map(str, years))}")
        logger.info("")
        
        # Step 1: Check MongoDB
        if not self.check_mongodb():
            logger.error("MongoDB is not running. Please start MongoDB first.")
            return False
        
        # Step 2: Data Ingestion
        if not skip_ingestion:
            if not self.run_ingestion(tickers, years):
                logger.error("Data ingestion failed")
                return False
        
        # Step 3: Verify Data
        if not self.verify_data(tickers):
            logger.warning("Data verification showed issues")
        
        # Step 4: Generate Embeddings
        if not skip_embeddings:
            if not self.generate_embeddings():
                logger.warning("Embeddings generation had issues")
        
        # Step 5: Export Data
        if not skip_export:
            if not self.export_data():
                logger.warning("Data export had issues")
        
        # Step 6: Start API Server
        if start_api:
            self.start_api_server()
        
        # Step 7: Start Dashboard
        if start_dashboard:
            self.start_dashboard()
        
        # Final Report
        self.print_final_report()
        
        return True
    
    def check_mongodb(self) -> bool:
        """Check if MongoDB is running."""
        logger.info("Step 1: Checking MongoDB connection...")
        
        try:
            from pymongo import MongoClient
            client = MongoClient('mongodb://localhost:27017/', serverSelectionTimeoutMS=5000)
            client.admin.command('ping')
            logger.info("  ✅ MongoDB is running")
            self.steps_completed.append("MongoDB Check")
            return True
        except Exception as e:
            logger.error(f"  ❌ MongoDB connection failed: {e}")
            self.errors.append(f"MongoDB: {str(e)}")
            return False
    
    def run_ingestion(self, tickers: List[str], years: List[int]) -> bool:
        """Run data ingestion pipeline."""
        logger.info("\nStep 2: Running data ingestion...")
        
        try:
            from shrey_god import SECFilingsPipeline
            
            pipeline = SECFilingsPipeline()
            
            for ticker in tickers:
                logger.info(f"  Processing {ticker}...")
                pipeline.process_company(ticker, "10-K", years)
                time.sleep(2)  # Rate limiting
            
            # Get statistics
            stats = pipeline.get_statistics()
            logger.info(f"  ✅ Ingestion complete:")
            logger.info(f"     Documents: {stats['total_documents']}")
            logger.info(f"     Chunks: {stats['total_chunks']}")
            logger.info(f"     Metrics: {stats['total_financial_metrics']}")
            
            self.steps_completed.append("Data Ingestion")
            return True
            
        except Exception as e:
            logger.error(f"  ❌ Ingestion failed: {e}")
            self.errors.append(f"Ingestion: {str(e)}")
            return False
    
    def verify_data(self, tickers: List[str]) -> bool:
        """Verify ingested data."""
        logger.info("\nStep 3: Verifying data...")
        
        try:
            from mongodb_query_interface import SECFilingsQuery
            
            query = SECFilingsQuery()
            
            all_good = True
            for ticker in tickers:
                filings = query.get_company_filings(ticker, "10-K")
                if filings:
                    logger.info(f"  ✅ {ticker}: {len(filings)} filings found")
                else:
                    logger.warning(f"  ⚠️  {ticker}: No filings found")
                    all_good = False
            
            self.steps_completed.append("Data Verification")
            return all_good
            
        except Exception as e:
            logger.error(f"  ❌ Verification failed: {e}")
            self.errors.append(f"Verification: {str(e)}")
            return False
    
    def generate_embeddings(self) -> bool:
        """Generate embeddings for semantic search."""
        logger.info("\nStep 4: Generating embeddings...")
        
        try:
            from embeddings_module import EmbeddingsManager
            
            manager = EmbeddingsManager()
            manager.update_chunk_embeddings(batch_size=50)
            
            logger.info("  ✅ Embeddings generated")
            self.steps_completed.append("Embeddings Generation")
            return True
            
        except ImportError:
            logger.warning("  ⚠️  Embeddings module not available (optional)")
            return True
        except Exception as e:
            logger.error(f"  ❌ Embeddings generation failed: {e}")
            self.errors.append(f"Embeddings: {str(e)}")
            return False
    
    def export_data(self) -> bool:
        """Export data in various formats."""
        logger.info("\nStep 5: Exporting data...")
        
        try:
            from data_export_utilities import DataExporter
            
            exporter = DataExporter()
            
            # Export to JSON
            export_path = exporter.export_all("json")
            logger.info(f"  ✅ Data exported: {export_path}")
            
            self.steps_completed.append("Data Export")
            return True
            
        except Exception as e:
            logger.error(f"  ❌ Export failed: {e}")
            self.errors.append(f"Export: {str(e)}")
            return False
    
    def start_api_server(self):
        """Start FastAPI server."""
        logger.info("\nStep 6: Starting API server...")
        
        try:
            # Check if FastAPI is installed
            import fastapi
            import uvicorn
            
            logger.info("  Starting FastAPI server on http://localhost:8000")
            logger.info("  API docs available at http://localhost:8000/docs")
            logger.info("  Press Ctrl+C to stop")
            
            # Start in subprocess
            subprocess.Popen([
                sys.executable, "-m", "uvicorn",
                "fastapi_server:app",
                "--host", "0.0.0.0",
                "--port", "8000"
            ])
            
            self.steps_completed.append("API Server")
            time.sleep(3)  # Give server time to start
            
        except ImportError:
            logger.warning("  ⚠️  FastAPI not installed (optional)")
        except Exception as e:
            logger.error(f"  ❌ API server failed: {e}")
            self.errors.append(f"API: {str(e)}")
    
    def start_dashboard(self):
        """Start Streamlit dashboard."""
        logger.info("\nStep 7: Starting dashboard...")
        
        try:
            # Check if Streamlit is installed
            import streamlit
            
            logger.info("  Starting Streamlit dashboard on http://localhost:8501")
            logger.info("  Press Ctrl+C to stop")
            
            # Start in subprocess
            subprocess.Popen([
                sys.executable, "-m", "streamlit", "run",
                "visualization_dashboard.py"
            ])
            
            self.steps_completed.append("Dashboard")
            time.sleep(3)  # Give dashboard time to start
            
        except ImportError:
            logger.warning("  ⚠️  Streamlit not installed (optional)")
        except Exception as e:
            logger.error(f"  ❌ Dashboard failed: {e}")
            self.errors.append(f"Dashboard: {str(e)}")
    
    def print_final_report(self):
        """Print final execution report."""
        duration = datetime.now() - self.start_time
        
        logger.info("\n" + "="*60)
        logger.info("PIPELINE EXECUTION REPORT")
        logger.info("="*60)
        
        logger.info(f"\nExecution Time: {duration}")
        
        logger.info(f"\nSteps Completed ({len(self.steps_completed)}):")
        for step in self.steps_completed:
            logger.info(f"  ✅ {step}")
        
        if self.errors:
            logger.info(f"\nErrors Encountered ({len(self.errors)}):")
            for error in self.errors:
                logger.info(f"  ❌ {error}")
        else:
            logger.info("\n✅ Pipeline completed successfully with no errors!")
        
        # Print useful commands
        logger.info("\n" + "="*60)
        logger.info("USEFUL COMMANDS")
        logger.info("="*60)
        logger.info("\nQuery data:")
        logger.info("  python mongodb_query_interface.py")
        logger.info("\nRun tests:")
        logger.info("  python test_verification.py")
        logger.info("\nExport data:")
        logger.info("  python data_export_utilities.py --format excel")
        logger.info("\nStart API:")
        logger.info("  python fastapi_server.py")
        logger.info("\nStart dashboard:")
        logger.info("  streamlit run visualization_dashboard.py")
        logger.info("\nConnect to MongoDB:")
        logger.info("  mongosh sec_filings_db")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Run SEC Filings MongoDB Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run complete pipeline for AAPL and MSFT
  python run_pipeline.py
  
  # Run for specific companies
  python run_pipeline.py --tickers AAPL MSFT GOOGL
  
  # Run for specific years
  python run_pipeline.py --years 2024 2023 2022
  
  # Skip ingestion (use existing data)
  python run_pipeline.py --skip-ingestion
  
  # Start with API and dashboard
  python run_pipeline.py --with-api --with-dashboard
  
  # Quick test run
  python run_pipeline.py --tickers AAPL --years 2024 --quick
        """
    )
    
    parser.add_argument(
        "--tickers",
        nargs="+",
        default=["AAPL", "MSFT"],
        help="Tickers to process"
    )
    
    parser.add_argument(
        "--years",
        nargs="+",
        type=int,
        default=[2024, 2023],
        help="Years to process"
    )
    
    parser.add_argument(
        "--skip-ingestion",
        action="store_true",
        help="Skip data ingestion (use existing data)"
    )
    
    parser.add_argument(
        "--skip-embeddings",
        action="store_true",
        help="Skip embeddings generation"
    )
    
    parser.add_argument(
        "--skip-export",
        action="store_true",
        help="Skip data export"
    )
    
    parser.add_argument(
        "--with-api",
        action="store_true",
        help="Start API server after pipeline"
    )
    
    parser.add_argument(
        "--with-dashboard",
        action="store_true",
        help="Start dashboard after pipeline"
    )
    
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Quick run with minimal processing"
    )
    
    args = parser.parse_args()
    
    # Quick mode adjustments
    if args.quick:
        args.skip_embeddings = True
        args.skip_export = True
        if len(args.tickers) > 1:
            args.tickers = [args.tickers[0]]
        if len(args.years) > 1:
            args.years = [args.years[0]]
    
    # Run pipeline
    runner = PipelineRunner()
    success = runner.run_complete_pipeline(
        tickers=args.tickers,
        years=args.years,
        skip_ingestion=args.skip_ingestion,
        skip_embeddings=args.skip_embeddings,
        skip_export=args.skip_export,
        start_api=args.with_api,
        start_dashboard=args.with_dashboard
    )
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()