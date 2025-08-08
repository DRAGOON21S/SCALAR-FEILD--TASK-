"""
SEC Filings Database System
A comprehensive system for extracting and storing SEC filings data using edgartools
"""

import sqlite3
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import pandas as pd
from pathlib import Path
import json
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Company list with tickers and names
COMPANIES = {
    # Technology
    'AAPL': 'Apple Inc.',
    'MSFT': 'Microsoft Corporation', 
    'GOOGL': 'Alphabet Inc.',
    'AMZN': 'Amazon.com Inc.',
    'NVDA': 'NVIDIA Corporation',
    # Financial Services
    'JPM': 'JPMorgan Chase & Co.',
    'BAC': 'Bank of America Corporation',
    'WFC': 'Wells Fargo & Company',
    # Healthcare
    'JNJ': 'Johnson & Johnson',
    'PFE': 'Pfizer Inc.',
    # Consumer/Retail
    'WMT': 'Walmart Inc.',
    'HD': 'The Home Depot Inc.',
    # Energy
    'XOM': 'Exxon Mobil Corporation',
    # Industrial
    'BA': 'The Boeing Company',
    # Telecommunications
    'VZ': 'Verizon Communications Inc.'
}

class SECFilingsDatabase:
    """Main class for managing SEC filings database operations"""
    
    def __init__(self, db_path: str = "sec_filings.db"):
        """Initialize database connection and create schema"""
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.cursor = self.conn.cursor()
        self.create_schema()
        
    def create_schema(self):
        """Create the complete database schema"""
        
        # Enable foreign key constraints
        self.cursor.execute("PRAGMA foreign_keys = ON")
        
        # Companies table
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS companies (
                cik INTEGER PRIMARY KEY,
                company_name TEXT NOT NULL,
                ticker_symbol TEXT,
                sic_code INTEGER,
                state_of_incorporation TEXT,
                industry_sector TEXT,
                fiscal_year_end TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create index on ticker for fast lookups
        self.cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_companies_ticker 
            ON companies(ticker_symbol)
        """)
        
        # Filings table
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS filings (
                accession_number TEXT PRIMARY KEY,
                cik INTEGER NOT NULL,
                form_type TEXT NOT NULL,
                filing_date DATE NOT NULL,
                period_of_report DATE,
                file_number TEXT,
                acceptance_datetime TIMESTAMP,
                filing_url TEXT,
                primary_document TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (cik) REFERENCES companies(cik)
            )
        """)
        
        # Create indices for common queries
        self.cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_filings_cik 
            ON filings(cik)
        """)
        self.cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_filings_form_type 
            ON filings(form_type)
        """)
        self.cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_filings_date 
            ON filings(filing_date)
        """)
        
        # Documents table
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                document_id INTEGER PRIMARY KEY AUTOINCREMENT,
                accession_number TEXT NOT NULL,
                sequence_number INTEGER,
                filename TEXT NOT NULL,
                document_type TEXT,
                description TEXT,
                size_bytes INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (accession_number) 
                    REFERENCES filings(accession_number) ON DELETE CASCADE
            )
        """)
        
        # Financial Facts table (for XBRL data)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS financial_facts (
                fact_id INTEGER PRIMARY KEY AUTOINCREMENT,
                accession_number TEXT NOT NULL,
                concept TEXT NOT NULL,
                label TEXT,
                value DECIMAL,
                unit TEXT,
                period_end_date DATE,
                period_type TEXT CHECK(period_type IN ('instant', 'duration')),
                dimensions_hash TEXT,
                segment TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (accession_number) 
                    REFERENCES filings(accession_number) ON DELETE CASCADE
            )
        """)
        
        # Create indices for financial facts
        self.cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_facts_concept 
            ON financial_facts(concept)
        """)
        self.cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_facts_period 
            ON financial_facts(period_end_date)
        """)
        self.cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_facts_accession 
            ON financial_facts(accession_number)
        """)
        
        # Insiders table
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS insiders (
                insider_cik INTEGER PRIMARY KEY,
                insider_name TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Transactions table (for Forms 3, 4, 5)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS insider_transactions (
                transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
                accession_number TEXT NOT NULL,
                insider_cik INTEGER NOT NULL,
                company_cik INTEGER NOT NULL,
                transaction_date DATE NOT NULL,
                transaction_code TEXT,
                security_title TEXT,
                shares DECIMAL,
                price_per_share DECIMAL,
                transaction_value DECIMAL,
                is_derivative BOOLEAN DEFAULT FALSE,
                ownership_type TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (accession_number) 
                    REFERENCES filings(accession_number) ON DELETE CASCADE,
                FOREIGN KEY (insider_cik) REFERENCES insiders(insider_cik),
                FOREIGN KEY (company_cik) REFERENCES companies(cik)
            )
        """)
        
        # Risk Factors table (extracted from 10-K/10-Q)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS risk_factors (
                risk_id INTEGER PRIMARY KEY AUTOINCREMENT,
                accession_number TEXT NOT NULL,
                risk_category TEXT,
                risk_title TEXT,
                risk_description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (accession_number) 
                    REFERENCES filings(accession_number) ON DELETE CASCADE
            )
        """)
        
        # Executive Compensation table (from DEF 14A)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS executive_compensation (
                compensation_id INTEGER PRIMARY KEY AUTOINCREMENT,
                accession_number TEXT NOT NULL,
                executive_name TEXT,
                position TEXT,
                fiscal_year INTEGER,
                salary DECIMAL,
                bonus DECIMAL,
                stock_awards DECIMAL,
                option_awards DECIMAL,
                other_compensation DECIMAL,
                total_compensation DECIMAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (accession_number) 
                    REFERENCES filings(accession_number) ON DELETE CASCADE
            )
        """)
        
        self.conn.commit()
        logger.info("Database schema created successfully")
    
    def insert_company(self, company_data: Dict):
        """Insert or update company information"""
        try:
            self.cursor.execute("""
                INSERT OR REPLACE INTO companies 
                (cik, company_name, ticker_symbol, sic_code, 
                 state_of_incorporation, industry_sector, fiscal_year_end)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                company_data['cik'],
                company_data['company_name'],
                company_data.get('ticker_symbol'),
                company_data.get('sic_code'),
                company_data.get('state_of_incorporation'),
                company_data.get('industry_sector'),
                company_data.get('fiscal_year_end')
            ))
            self.conn.commit()
            logger.info(f"Inserted company: {company_data['company_name']}")
        except Exception as e:
            logger.error(f"Error inserting company: {e}")
            self.conn.rollback()
    
    def insert_filing(self, filing_data: Dict):
        """Insert filing information"""
        try:
            self.cursor.execute("""
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
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error inserting filing: {e}")
            self.conn.rollback()
            return False
    
    def insert_financial_facts(self, facts_data: List[Dict]):
        """Bulk insert financial facts"""
        try:
            self.cursor.executemany("""
                INSERT OR IGNORE INTO financial_facts 
                (accession_number, concept, label, value, unit, 
                 period_end_date, period_type, dimensions_hash, segment)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, [
                (
                    fact['accession_number'],
                    fact['concept'],
                    fact.get('label'),
                    fact.get('value'),
                    fact.get('unit'),
                    fact.get('period_end_date'),
                    fact.get('period_type'),
                    fact.get('dimensions_hash'),
                    fact.get('segment')
                ) for fact in facts_data
            ])
            self.conn.commit()
            logger.info(f"Inserted {len(facts_data)} financial facts")
        except Exception as e:
            logger.error(f"Error inserting financial facts: {e}")
            self.conn.rollback()
    
    def insert_documents(self, documents_data: List[Dict]):
        """Insert document information"""
        try:
            self.cursor.executemany("""
                INSERT OR IGNORE INTO documents 
                (accession_number, sequence_number, filename, 
                 document_type, description, size_bytes)
                VALUES (?, ?, ?, ?, ?, ?)
            """, [
                (
                    doc['accession_number'],
                    doc.get('sequence_number'),
                    doc['filename'],
                    doc.get('document_type'),
                    doc.get('description'),
                    doc.get('size_bytes')
                ) for doc in documents_data
            ])
            self.conn.commit()
        except Exception as e:
            logger.error(f"Error inserting documents: {e}")
            self.conn.rollback()
    
    def close(self):
        """Close database connection"""
        self.conn.close()


class EdgarDataExtractor:
    """Extract data from SEC EDGAR using edgartools with PyArrow compatibility fixes"""
    
    def __init__(self, db: SECFilingsDatabase):
        self.db = db
        
    def extract_company_data(self, ticker: str, company_name: str) -> Optional[Dict]:
        """Extract and store company data"""
        try:
            from edgar import Company
            
            # Get company by ticker
            company = Company(ticker)
            
            company_data = {
                'cik': company.cik,
                'company_name': company.name,
                'ticker_symbol': ticker,
                'sic_code': company.sic if hasattr(company, 'sic') else None,
                'state_of_incorporation': None,
                'industry_sector': self._get_industry_sector(ticker),
                'fiscal_year_end': company.fiscal_year_end if hasattr(company, 'fiscal_year_end') else None
            }
            
            # Insert company data
            self.db.insert_company(company_data)
            
            return company_data
            
        except Exception as e:
            logger.error(f"Error extracting company data for {ticker}: {e}")
            return None
    
    def extract_filings(self, ticker: str, forms: List[str] = None, 
                       start_date: str = None, end_date: str = None, 
                       limit: int = None):
        """
        Extract filings for a company with PyArrow compatibility fixes
        
        Args:
            ticker: Company ticker symbol
            forms: List of form types to extract
            start_date: Start date for filings (YYYY-MM-DD)
            end_date: End date for filings (YYYY-MM-DD)
            limit: Maximum number of filings per form (None for all)
        """
        try:
            from edgar import Company
            
            if forms is None:
                forms = ['10-K', '10-Q', '8-K', 'DEF 14A', '4']
            
            company = Company(ticker)
            
            for form_type in forms:
                logger.info(f"Extracting {form_type} filings for {ticker}")
                
                # Determine appropriate limit based on form type
                if limit is None:
                    # Set reasonable limits based on filing frequency
                    form_limits = {
                        '10-K': 10,      # Annual reports (10 years)
                        '10-Q': 40,      # Quarterly reports (10 years)
                        '8-K': 200,      # Current reports (can be frequent)
                        'DEF 14A': 10,   # Annual proxy statements
                        '4': 500,        # Insider transactions (very frequent)
                        '3': 50,         # Initial insider ownership
                        '5': 50          # Annual insider ownership
                    }
                    form_limit = form_limits.get(form_type, 100)
                else:
                    form_limit = limit
                
                # Get filings without date filtering first (to avoid issues)
                try:
                    filings = company.get_filings(form=form_type)
                    
                    logger.info(f"Found {len(filings)} {form_type} filings for {ticker}")
                    
                    # Process filings with PyArrow compatibility
                    self._process_filings_safe(filings, form_limit, company)
                    
                except Exception as e:
                    logger.error(f"Error getting {form_type} filings for {ticker}: {e}")
                    continue
                        
        except Exception as e:
            logger.error(f"Error extracting filings for {ticker}: {e}")
    
    def _process_filings_safe(self, filings, limit=None, company=None):
        """Safely process filings with PyArrow compatibility"""
        try:
            # Access the underlying data directly to avoid PyArrow issues
            data = filings.data
            
            # Get the length
            total_filings = len(data)
            
            if limit and total_filings > limit:
                process_count = limit
            else:
                process_count = total_filings
            
            logger.info(f"Processing {process_count} filings")
            
            for i in range(process_count):
                try:
                    # Extract data safely using indices with correct field names
                    filing_data = {
                        'accession_number': self._safe_get_value(data['accession_number'], i),
                        'cik': company.cik,  # Get CIK from company object
                        'form_type': self._safe_get_value(data['form'], i),
                        'filing_date': self._safe_get_value(data['filing_date'], i),
                        'period_of_report': self._safe_get_value(data.get('reportDate'), i) if 'reportDate' in data else None,
                        'file_number': self._safe_get_value(data.get('fileNumber'), i) if 'fileNumber' in data else None,
                        'acceptance_datetime': self._safe_get_value(data.get('acceptanceDateTime'), i) if 'acceptanceDateTime' in data else None,
                        'filing_url': f"https://www.sec.gov/Archives/edgar/data/{company.cik}/{self._safe_get_value(data['accession_number'], i).replace('-', '')}/{self._safe_get_value(data['primaryDocument'], i)}" if 'primaryDocument' in data and self._safe_get_value(data['primaryDocument'], i) else None,
                        'primary_document': self._safe_get_value(data.get('primaryDocument'), i) if 'primaryDocument' in data else None
                    }
                    
                    # Insert filing
                    if self.db.insert_filing(filing_data):
                        logger.info(f"Successfully inserted filing: {filing_data['accession_number']}")
                        
                        # Extract additional data based on form type
                        if filing_data['form_type'] in ['10-K', '10-Q']:
                            self._extract_financial_data_safe(filing_data['accession_number'], company)
                            self._extract_risk_factors(filing_data['accession_number'])
                        elif filing_data['form_type'] == '4':
                            self._extract_insider_transactions(filing_data['accession_number'])
                        elif filing_data['form_type'] == 'DEF 14A':
                            self._extract_executive_compensation(filing_data['accession_number'])
                        
                        # Extract documents
                        self._extract_documents_safe(filing_data['accession_number'])
                    
                    # Add delay to avoid rate limiting
                    time.sleep(0.1)
                    
                except Exception as e:
                    logger.error(f"Error processing filing {i}: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Error in _process_filings_safe: {e}")
    
    def _safe_get_value(self, chunked_array, index):
        """Safely get value from PyArrow ChunkedArray"""
        try:
            if chunked_array is None:
                return None
            
            # For newer PyArrow versions, use to_pylist()
            if hasattr(chunked_array, 'to_pylist'):
                values = chunked_array.to_pylist()
                return values[index] if index < len(values) else None
            
            # Fallback for older versions
            elif hasattr(chunked_array, 'as_py'):
                return chunked_array[index].as_py()
            
            # Last resort - try to convert to pandas and get value
            else:
                return chunked_array.to_pandas().iloc[index]
                
        except Exception as e:
            logger.debug(f"Error getting value at index {index}: {e}")
            return None
    
    def _extract_financial_data_safe(self, accession_number: str, company):
        """Extract XBRL financial data from filing with better error handling"""
        try:
            from edgar import Filing
            
            # Get the filing object
            filing = Filing(company.cik, accession_number.replace('-', ''))
            
            # Check if filing has XBRL data
            try:
                xbrl = filing.xbrl()
                if not xbrl:
                    logger.debug(f"No XBRL data found for {accession_number}")
                    return
            except Exception as e:
                logger.debug(f"Could not get XBRL for {accession_number}: {e}")
                return
            
            facts_data = []
            
            try:
                # Extract facts
                facts = xbrl.facts
                
                # Convert to DataFrame for easier processing
                if hasattr(facts, 'to_pandas'):
                    facts_df = facts.to_pandas()
                else:
                    facts_df = facts
                
                for idx, fact in facts_df.iterrows():
                    fact_data = {
                        'accession_number': accession_number,
                        'concept': fact.get('concept'),
                        'label': fact.get('label'),
                        'value': fact.get('value'),
                        'unit': fact.get('unit'),
                        'period_end_date': fact.get('period'),
                        'period_type': fact.get('period_type', 'instant'),
                        'dimensions_hash': None,
                        'segment': fact.get('segment')
                    }
                    facts_data.append(fact_data)
                
                if facts_data:
                    self.db.insert_financial_facts(facts_data)
                    logger.info(f"Extracted {len(facts_data)} financial facts for {accession_number}")
                    
            except Exception as e:
                logger.debug(f"Error processing XBRL facts for {accession_number}: {e}")
                
        except Exception as e:
            logger.debug(f"Could not extract XBRL data for {accession_number}: {e}")
    
    def _extract_documents_safe(self, accession_number: str):
        """Extract document information from filing with better error handling"""
        try:
            # This is a placeholder - actual implementation would need to
            # fetch the filing and extract document information
            logger.debug(f"Document extraction not implemented for {accession_number}")
                
        except Exception as e:
            logger.debug(f"Could not extract documents for {accession_number}: {e}")
    
    def _extract_risk_factors(self, accession_number: str):
        """Extract risk factors from 10-K/10-Q filings"""
        # Implementation would extract Item 1A from 10-K
        # This is a placeholder for actual text extraction logic
        logger.debug(f"Risk factor extraction not implemented for {accession_number}")
    
    def _extract_insider_transactions(self, accession_number: str):
        """Extract insider transaction data from Form 4"""
        # Implementation would parse Form 4 XML data
        logger.debug(f"Insider transaction extraction not implemented for {accession_number}")
    
    def _extract_executive_compensation(self, accession_number: str):
        """Extract executive compensation from proxy statements"""
        # Implementation would parse DEF 14A compensation tables
        logger.debug(f"Executive compensation extraction not implemented for {accession_number}")
    
    def _get_industry_sector(self, ticker: str) -> str:
        """Get industry sector for a ticker"""
        sectors = {
            'AAPL': 'Technology', 'MSFT': 'Technology', 'GOOGL': 'Technology',
            'AMZN': 'Technology', 'NVDA': 'Technology',
            'JPM': 'Financial Services', 'BAC': 'Financial Services', 
            'WFC': 'Financial Services',
            'JNJ': 'Healthcare', 'PFE': 'Healthcare',
            'WMT': 'Consumer/Retail', 'HD': 'Consumer/Retail',
            'XOM': 'Energy', 'BA': 'Industrial', 'VZ': 'Telecommunications'
        }
        return sectors.get(ticker, 'Other')


def main():
    """Main execution function"""
    from edgar import set_identity
    set_identity("shreybansal1165@gmail.com")   
    # Configuration
    config = {
        'start_date': '2015-01-01',  # 10 years of data
        'end_date': '2024-12-31',
        'forms': {
            'financial': ['10-K', '10-Q'],  # Financial reports
            'events': ['8-K'],               # Current events
            'proxy': ['DEF 14A'],            # Proxy statements
            'insider': ['4'],                # Insider transactions
        },
        'batch_size': 5,  # Process companies in batches
        'delay': 0.5      # Delay between requests
    }
    
    # Initialize database
    db = SECFilingsDatabase("sec_filings.db")
    extractor = EdgarDataExtractor(db)
    
    # Process companies in batches to manage memory and API limits
    company_list = list(COMPANIES.items())
    
    for batch_idx in range(0, len(company_list), config['batch_size']):
        batch = company_list[batch_idx:batch_idx + config['batch_size']]
        
        logger.info(f"\n{'='*60}")
        logger.info(f"Processing Batch {batch_idx//config['batch_size'] + 1}")
        logger.info(f"Companies: {[ticker for ticker, _ in batch]}")
        logger.info(f"{'='*60}")
        
        for ticker, company_name in batch:
            logger.info(f"\n{'-'*50}")
            logger.info(f"Processing {ticker} - {company_name}")
            logger.info(f"{'-'*50}")
            
            # Extract company data
            company_data = extractor.extract_company_data(ticker, company_name)
            
            if company_data:
                # Extract financial filings (most important)
                logger.info(f"Extracting financial filings for {ticker}...")
                extractor.extract_filings(
                    ticker=ticker,
                    forms=config['forms']['financial'],
                    start_date=config['start_date'],
                    end_date=config['end_date'],
                    limit=None  # Get all available
                )
                
                # Extract current reports
                logger.info(f"Extracting current reports for {ticker}...")
                extractor.extract_filings(
                    ticker=ticker,
                    forms=config['forms']['events'],
                    start_date=config['start_date'],
                    end_date=config['end_date'],
                    limit=None
                )
                
                # Extract proxy statements
                logger.info(f"Extracting proxy statements for {ticker}...")
                extractor.extract_filings(
                    ticker=ticker,
                    forms=config['forms']['proxy'],
                    start_date=config['start_date'],
                    end_date=config['end_date'],
                    limit=None
                )
                
                # Extract insider transactions (limit these as they can be numerous)
                logger.info(f"Extracting insider transactions for {ticker}...")
                extractor.extract_filings(
                    ticker=ticker,
                    forms=config['forms']['insider'],
                    start_date=config['start_date'],
                    end_date=config['end_date'],
                    limit=None
                )
            
            # Add delay between companies
            time.sleep(config['delay'])
        
        # Longer delay between batches
        if batch_idx + config['batch_size'] < len(company_list):
            logger.info(f"\nCompleted batch. Waiting before next batch...")
            time.sleep(2)
    
    logger.info("\nData extraction complete!")
    
    # Run some sample queries to verify data
    cursor = db.cursor
    
    # Count companies
    cursor.execute("SELECT COUNT(*) FROM companies")
    company_count = cursor.fetchone()[0]
    logger.info(f"Total companies: {company_count}")
    
    # Count filings by type
    cursor.execute("""
        SELECT form_type, COUNT(*) as count 
        FROM filings 
        GROUP BY form_type 
        ORDER BY count DESC
    """)
    filings_summary = cursor.fetchall()
    logger.info("\nFilings summary by type:")
    for form_type, count in filings_summary:
        logger.info(f"  {form_type}: {count}")
    
    # Count financial facts
    cursor.execute("SELECT COUNT(*) FROM financial_facts")
    facts_count = cursor.fetchone()[0]
    logger.info(f"\nTotal financial facts: {facts_count}")
    
    db.close()


if __name__ == "__main__":
    main()