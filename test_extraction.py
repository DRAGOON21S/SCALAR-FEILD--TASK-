"""
Test script to debug the filing extraction issue
"""

import sqlite3
import logging
from edgar import Company, set_identity
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Set identity
set_identity("shreybansal1165@gmail.com")

def test_filing_extraction():
    """Test filing extraction for a single company"""
    
    # Connect to database
    conn = sqlite3.connect("sec_filings.db")
    cursor = conn.cursor()
    
    try:
        # Test with Apple
        ticker = 'AAPL'
        company = Company(ticker)
        
        print(f"Testing extraction for {ticker}")
        print(f"Company: {company.name}")
        print(f"CIK: {company.cik}")
        
        # Get recent 10-K filings (limit to 2 for testing)
        filings = company.get_filings(form='10-K')
        print(f"Found {len(filings)} 10-K filings")
        
        # Try to insert first 2 filings
        for i, filing in enumerate(filings[:2]):
            print(f"\nProcessing filing {i+1}:")
            print(f"  Form: {filing.form}")
            print(f"  Date: {filing.filing_date}")
            print(f"  Accession: {filing.accession_no}")
            
            # Prepare filing data
            filing_data = {
                'accession_number': filing.accession_no,
                'cik': filing.cik,
                'form_type': filing.form,
                'filing_date': filing.filing_date,
                'period_of_report': filing.period_of_report if hasattr(filing, 'period_of_report') else None,
                'file_number': filing.file_number if hasattr(filing, 'file_number') else None,
                'acceptance_datetime': filing.acceptance_datetime if hasattr(filing, 'acceptance_datetime') else None,
                'filing_url': filing.homepage_url,
                'primary_document': str(filing.document) if hasattr(filing, 'document') and filing.document else None
            }
            
            print(f"  Filing data prepared: {filing_data}")
            
            # Try to insert
            try:
                cursor.execute("""
                    INSERT OR IGNORE INTO filings 
                    (accession_number, cik, form_type, filing_date, 
                     period_of_report, file_number, acceptance_datetime,
                     filing_url, primary_document)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    filing_data['accession_number'],
                    filing_data['cik'],
                    filing_data['form_type'],
                    filing_data['filing_date'],
                    filing_data.get('period_of_report'),
                    filing_data.get('file_number'),
                    filing_data.get('acceptance_datetime'),
                    filing_data.get('filing_url'),
                    filing_data.get('primary_document')
                ))
                
                conn.commit()
                print(f"  ✓ Successfully inserted filing")
                
            except Exception as e:
                print(f"  ✗ Error inserting filing: {e}")
                conn.rollback()
    
    except Exception as e:
        print(f"Error in test extraction: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Check final count
        cursor.execute("SELECT COUNT(*) FROM filings")
        count = cursor.fetchone()[0]
        print(f"\nFinal filings count: {count}")
        
        if count > 0:
            cursor.execute("SELECT form_type, filing_date, accession_number FROM filings LIMIT 5")
            results = cursor.fetchall()
            print("Sample filings:")
            for row in results:
                print(f"  {row[0]} - {row[1]} - {row[2]}")
        
        conn.close()

if __name__ == "__main__":
    test_filing_extraction()
