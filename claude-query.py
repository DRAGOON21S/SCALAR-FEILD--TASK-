"""
SEC Database Query and Analysis Utilities
Advanced queries and analysis functions for the SEC filings database
"""

import sqlite3
import pandas as pd
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import numpy as np


class SECDatabaseAnalyzer:
    """Advanced query and analysis functions for SEC database"""
    
    def __init__(self, db_path: str = "sec_filings.db"):
        """Initialize database connection"""
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        
    def get_revenue_trends(self, tickers: List[str] = None, 
                          start_date: str = None, end_date: str = None) -> pd.DataFrame:
        """
        Get revenue trends for companies
        Question 1: Primary revenue drivers and evolution
        """
        query = """
            SELECT 
                c.ticker_symbol,
                c.company_name,
                f.filing_date,
                ff.period_end_date,
                ff.label,
                ff.value as revenue,
                ff.unit
            FROM financial_facts ff
            JOIN filings f ON ff.accession_number = f.accession_number
            JOIN companies c ON f.cik = c.cik
            WHERE ff.concept LIKE '%Revenue%'
                AND ff.value IS NOT NULL
        """
        
        params = []
        if tickers:
            placeholders = ','.join(['?' for _ in tickers])
            query += f" AND c.ticker_symbol IN ({placeholders})"
            params.extend(tickers)
        
        if start_date:
            query += " AND ff.period_end_date >= ?"
            params.append(start_date)
            
        if end_date:
            query += " AND ff.period_end_date <= ?"
            params.append(end_date)
            
        query += " ORDER BY c.ticker_symbol, ff.period_end_date"
        
        return pd.read_sql_query(query, self.conn, params=params)
    
    def compare_rd_spending(self, industry_sector: str = None) -> pd.DataFrame:
        """
        Compare R&D spending trends across companies
        Question 2: R&D spending trends and innovation strategies
        """
        query = """
            SELECT 
                c.ticker_symbol,
                c.company_name,
                c.industry_sector,
                STRFTIME('%Y', ff.period_end_date) as year,
                SUM(CASE WHEN ff.concept LIKE '%ResearchAndDevelopment%' 
                    THEN ff.value ELSE 0 END) as rd_expense,
                SUM(CASE WHEN ff.concept LIKE '%Revenue%' 
                    THEN ff.value ELSE 0 END) as revenue,
                CASE 
                    WHEN SUM(CASE WHEN ff.concept LIKE '%Revenue%' THEN ff.value ELSE 0 END) > 0
                    THEN (SUM(CASE WHEN ff.concept LIKE '%ResearchAndDevelopment%' THEN ff.value ELSE 0 END) * 100.0 / 
                          SUM(CASE WHEN ff.concept LIKE '%Revenue%' THEN ff.value ELSE 0 END))
                    ELSE 0 
                END as rd_intensity_pct
            FROM financial_facts ff
            JOIN filings f ON ff.accession_number = f.accession_number
            JOIN companies c ON f.cik = c.cik
            WHERE (ff.concept LIKE '%ResearchAndDevelopment%' 
                   OR ff.concept LIKE '%Revenue%')
                AND ff.value IS NOT NULL
        """
        
        params = []
        if industry_sector:
            query += " AND c.industry_sector = ?"
            params.append(industry_sector)
            
        query += """
            GROUP BY c.ticker_symbol, c.company_name, c.industry_sector, 
                     STRFTIME('%Y', ff.period_end_date)
            ORDER BY year DESC, rd_intensity_pct DESC
        """
        
        return pd.read_sql_query(query, self.conn, params=params)
    
    def analyze_working_capital(self, sector: str = 'Financial Services') -> pd.DataFrame:
        """
        Analyze working capital changes
        Question 3: Working capital changes for financial services
        """
        query = """
            SELECT 
                c.ticker_symbol,
                c.company_name,
                ff.period_end_date,
                MAX(CASE WHEN ff.concept LIKE '%CurrentAssets%' 
                    THEN ff.value END) as current_assets,
                MAX(CASE WHEN ff.concept LIKE '%CurrentLiabilities%' 
                    THEN ff.value END) as current_liabilities,
                MAX(CASE WHEN ff.concept LIKE '%CurrentAssets%' THEN ff.value END) -
                MAX(CASE WHEN ff.concept LIKE '%CurrentLiabilities%' THEN ff.value END) 
                    as working_capital,
                MAX(CASE WHEN ff.concept LIKE '%CashAndCashEquivalents%' 
                    THEN ff.value END) as cash,
                MAX(CASE WHEN ff.concept LIKE '%AccountsReceivable%' 
                    THEN ff.value END) as receivables,
                MAX(CASE WHEN ff.concept LIKE '%Inventory%' 
                    THEN ff.value END) as inventory
            FROM financial_facts ff
            JOIN filings f ON ff.accession_number = f.accession_number
            JOIN companies c ON f.cik = c.cik
            WHERE c.industry_sector = ?
                AND ff.period_type = 'instant'
                AND ff.value IS NOT NULL
            GROUP BY c.ticker_symbol, c.company_name, ff.period_end_date
            ORDER BY c.ticker_symbol, ff.period_end_date DESC
        """
        
        return pd.read_sql_query(query, self.conn, params=[sector])
    
    def get_risk_factors_analysis(self) -> pd.DataFrame:
        """
        Analyze commonly cited risk factors
        Question 4: Most common risk factors across industries
        """
        query = """
            SELECT 
                c.industry_sector,
                c.ticker_symbol,
                c.company_name,
                rf.risk_category,
                rf.risk_title,
                COUNT(*) as mention_count
            FROM risk_factors rf
            JOIN filings f ON rf.accession_number = f.accession_number
            JOIN companies c ON f.cik = c.cik
            WHERE f.form_type = '10-K'
            GROUP BY c.industry_sector, c.ticker_symbol, 
                     c.company_name, rf.risk_category
            ORDER BY c.industry_sector, mention_count DESC
        """
        
        return pd.read_sql_query(query, self.conn)
    
    def analyze_climate_risks(self) -> pd.DataFrame:
        """
        Analyze climate-related risk disclosures
        Question 5: Climate-related risks by industry
        """
        query = """
            SELECT 
                c.industry_sector,
                c.ticker_symbol,
                c.company_name,
                f.filing_date,
                rf.risk_title,
                rf.risk_description
            FROM risk_factors rf
            JOIN filings f ON rf.accession_number = f.accession_number
            JOIN companies c ON f.cik = c.cik
            WHERE (LOWER(rf.risk_title) LIKE '%climate%' 
                   OR LOWER(rf.risk_title) LIKE '%environmental%'
                   OR LOWER(rf.risk_title) LIKE '%carbon%'
                   OR LOWER(rf.risk_title) LIKE '%sustainability%')
                AND f.form_type = '10-K'
            ORDER BY c.industry_sector, f.filing_date DESC
        """
        
        return pd.read_sql_query(query, self.conn)
    
    def get_executive_compensation_trends(self) -> pd.DataFrame:
        """
        Analyze executive compensation changes
        Question 6: Executive compensation trends
        """
        query = """
            SELECT 
                c.ticker_symbol,
                c.company_name,
                c.industry_sector,
                ec.fiscal_year,
                ec.executive_name,
                ec.position,
                ec.salary,
                ec.bonus,
                ec.stock_awards,
                ec.option_awards,
                ec.total_compensation,
                LAG(ec.total_compensation) OVER (
                    PARTITION BY c.ticker_symbol, ec.executive_name 
                    ORDER BY ec.fiscal_year
                ) as prev_year_comp,
                CASE 
                    WHEN LAG(ec.total_compensation) OVER (
                        PARTITION BY c.ticker_symbol, ec.executive_name 
                        ORDER BY ec.fiscal_year
                    ) > 0
                    THEN ((ec.total_compensation - LAG(ec.total_compensation) OVER (
                        PARTITION BY c.ticker_symbol, ec.executive_name 
                        ORDER BY ec.fiscal_year
                    )) * 100.0 / LAG(ec.total_compensation) OVER (
                        PARTITION BY c.ticker_symbol, ec.executive_name 
                        ORDER BY ec.fiscal_year
                    ))
                    ELSE NULL
                END as yoy_change_pct
            FROM executive_compensation ec
            JOIN filings f ON ec.accession_number = f.accession_number
            JOIN companies c ON f.cik = c.cik
            ORDER BY c.ticker_symbol, ec.fiscal_year DESC, ec.total_compensation DESC
        """
        
        return pd.read_sql_query(query, self.conn)
    
    def analyze_insider_trading(self, min_value: float = 1000000) -> pd.DataFrame:
        """
        Analyze significant insider trading activity
        Question 7: Significant insider trading patterns
        """
        query = """
            SELECT 
                c.ticker_symbol,
                c.company_name,
                i.insider_name,
                it.transaction_date,
                it.transaction_code,
                it.security_title,
                it.shares,
                it.price_per_share,
                it.transaction_value,
                CASE 
                    WHEN it.transaction_code IN ('P', 'M') THEN 'Buy'
                    WHEN it.transaction_code IN ('S', 'F') THEN 'Sell'
                    ELSE 'Other'
                END as transaction_type,
                SUM(it.transaction_value) OVER (
                    PARTITION BY c.ticker_symbol 
                    ORDER BY it.transaction_date 
                    ROWS BETWEEN 30 PRECEDING AND CURRENT ROW
                ) as rolling_30d_volume
            FROM insider_transactions it
            JOIN insiders i ON it.insider_cik = i.insider_cik
            JOIN companies c ON it.company_cik = c.cik
            WHERE ABS(it.transaction_value) >= ?
            ORDER BY it.transaction_date DESC, ABS(it.transaction_value) DESC
        """
        
        return pd.read_sql_query(query, self.conn, params=[min_value])
    
    def analyze_ai_positioning(self) -> pd.DataFrame:
        """
        Analyze AI and automation positioning
        Question 8: Company positioning on AI and automation
        """
        # This would require text analysis of filings
        # Placeholder for NLP-based analysis
        query = """
            SELECT 
                c.ticker_symbol,
                c.company_name,
                c.industry_sector,
                f.form_type,
                f.filing_date,
                COUNT(*) as filing_count
            FROM filings f
            JOIN companies c ON f.cik = c.cik
            WHERE f.form_type IN ('10-K', '10-Q')
            GROUP BY c.ticker_symbol, c.company_name, c.industry_sector, f.form_type
            ORDER BY c.ticker_symbol, f.filing_date DESC
        """
        
        return pd.read_sql_query(query, self.conn)
    
    def get_ma_activity(self) -> pd.DataFrame:
        """
        Identify M&A activity from 8-K filings
        Question 9: Recent M&A activity
        """
        query = """
            SELECT 
                c.ticker_symbol,
                c.company_name,
                f.filing_date,
                f.form_type,
                f.filing_url,
                COUNT(*) OVER (
                    PARTITION BY c.ticker_symbol 
                    ORDER BY f.filing_date 
                    ROWS BETWEEN 365 PRECEDING AND CURRENT ROW
                ) as annual_8k_count
            FROM filings f
            JOIN companies c ON f.cik = c.cik
            WHERE f.form_type = '8-K'
            ORDER BY f.filing_date DESC
        """
        
        return pd.read_sql_query(query, self.conn)
    
    def analyze_competitive_advantages(self) -> pd.DataFrame:
        """
        Analyze competitive advantages themes
        Question 10: Competitive advantages by company
        """
        query = """
            SELECT 
                c.ticker_symbol,
                c.company_name,
                c.industry_sector,
                MAX(CASE WHEN ff.concept LIKE '%GrossProfit%' 
                    THEN ff.value END) as gross_profit,
                MAX(CASE WHEN ff.concept LIKE '%Revenue%' 
                    THEN ff.value END) as revenue,
                CASE 
                    WHEN MAX(CASE WHEN ff.concept LIKE '%Revenue%' THEN ff.value END) > 0
                    THEN (MAX(CASE WHEN ff.concept LIKE '%GrossProfit%' THEN ff.value END) * 100.0 / 
                          MAX(CASE WHEN ff.concept LIKE '%Revenue%' THEN ff.value END))
                    ELSE NULL
                END as gross_margin_pct,
                MAX(CASE WHEN ff.concept LIKE '%OperatingIncome%' 
                    THEN ff.value END) as operating_income,
                CASE 
                    WHEN MAX(CASE WHEN ff.concept LIKE '%Revenue%' THEN ff.value END) > 0
                    THEN (MAX(CASE WHEN ff.concept LIKE '%OperatingIncome%' THEN ff.value END) * 100.0 / 
                          MAX(CASE WHEN ff.concept LIKE '%Revenue%' THEN ff.value END))
                    ELSE NULL
                END as operating_margin_pct
            FROM financial_facts ff
            JOIN filings f ON ff.accession_number = f.accession_number
            JOIN companies c ON f.cik = c.cik
            WHERE f.form_type IN ('10-K', '10-Q')
                AND ff.period_type = 'duration'
            GROUP BY c.ticker_symbol, c.company_name, c.industry_sector, ff.period_end_date
            ORDER BY gross_margin_pct DESC
        """
        
        return pd.read_sql_query(query, self.conn)
    
    def generate_summary_report(self) -> Dict:
        """Generate comprehensive summary statistics"""
        
        summary = {}
        
        # Database statistics
        stats_queries = {
            'total_companies': "SELECT COUNT(*) FROM companies",
            'total_filings': "SELECT COUNT(*) FROM filings",
            'total_facts': "SELECT COUNT(*) FROM financial_facts",
            'total_documents': "SELECT COUNT(*) FROM documents",
            'total_insiders': "SELECT COUNT(*) FROM insiders",
            'total_transactions': "SELECT COUNT(*) FROM insider_transactions"
        }
        
        for key, query in stats_queries.items():
            cursor = self.conn.execute(query)
            summary[key] = cursor.fetchone()[0]
        
        # Filings by type
        cursor = self.conn.execute("""
            SELECT form_type, COUNT(*) as count 
            FROM filings 
            GROUP BY form_type 
            ORDER BY count DESC
        """)
        summary['filings_by_type'] = dict(cursor.fetchall())
        
        # Companies by sector
        cursor = self.conn.execute("""
            SELECT industry_sector, COUNT(*) as count 
            FROM companies 
            WHERE industry_sector IS NOT NULL
            GROUP BY industry_sector 
            ORDER BY count DESC
        """)
        summary['companies_by_sector'] = dict(cursor.fetchall())
        
        # Date range
        cursor = self.conn.execute("""
            SELECT MIN(filing_date) as earliest, MAX(filing_date) as latest 
            FROM filings
        """)
        dates = cursor.fetchone()
        summary['date_range'] = {
            'earliest_filing': dates[0],
            'latest_filing': dates[1]
        }
        
        return summary
    
    def export_to_parquet(self, output_dir: str = "sec_data_export"):
        """Export all tables to Parquet files for analysis"""
        import os
        os.makedirs(output_dir, exist_ok=True)
        
        tables = [
            'companies', 'filings', 'financial_facts', 'documents',
            'insiders', 'insider_transactions', 'risk_factors',
            'executive_compensation'
        ]
        
        for table in tables:
            df = pd.read_sql_query(f"SELECT * FROM {table}", self.conn)
            output_path = os.path.join(output_dir, f"{table}.parquet")
            df.to_parquet(output_path, index=False)
            print(f"Exported {table} to {output_path} ({len(df)} rows)")
    
    def close(self):
        """Close database connection"""
        self.conn.close()


def run_sample_analyses():
    """Run sample analyses to answer the evaluation questions"""
    
    analyzer = SECDatabaseAnalyzer()
    
    print("\n" + "="*60)
    print("SEC DATABASE ANALYSIS RESULTS")
    print("="*60)
    
    # Generate summary
    summary = analyzer.generate_summary_report()
    print("\nDatabase Summary:")
    for key, value in summary.items():
        if isinstance(value, dict):
            print(f"\n{key}:")
            for k, v in value.items():
                print(f"  {k}: {v}")
        else:
            print(f"  {key}: {value}")
    
    # Question 1: Revenue trends
    print("\n" + "-"*40)
    print("Q1: Revenue Trends by Technology Companies")
    revenue_df = analyzer.get_revenue_trends(
        tickers=['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA']
    )
    if not revenue_df.empty:
        print(revenue_df.groupby('ticker_symbol')['revenue'].describe())
    
    # Question 2: R&D Spending
    print("\n" + "-"*40)
    print("Q2: R&D Spending Comparison")
    rd_df = analyzer.compare_rd_spending()
    if not rd_df.empty:
        print(rd_df.head(10))
    
    # Question 3: Working Capital
    print("\n" + "-"*40)
    print("Q3: Working Capital Analysis - Financial Services")
    wc_df = analyzer.analyze_working_capital('Financial Services')
    if not wc_df.empty:
        print(wc_df.head(10))
    
    # Question 7: Insider Trading
    print("\n" + "-"*40)
    print("Q7: Significant Insider Trading Activity")
    insider_df = analyzer.analyze_insider_trading(min_value=500000)
    if not insider_df.empty:
        print(insider_df.head(10))
    
    # Question 10: Competitive Advantages
    print("\n" + "-"*40)
    print("Q10: Competitive Advantages (Margins)")
    margins_df = analyzer.analyze_competitive_advantages()
    if not margins_df.empty:
        print(margins_df.head(10))
    
    analyzer.close()
    print("\n" + "="*60)
    print("Analysis complete!")


if __name__ == "__main__":
    run_sample_analyses()