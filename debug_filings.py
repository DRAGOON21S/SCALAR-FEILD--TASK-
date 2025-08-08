"""
Debug script to understand what filings are available
"""

from edgar import Company, set_identity
import pandas as pd

# Set identity
set_identity("shreybansal1165@gmail.com")

def debug_filings():
    """Debug what filings are actually available"""
    
    try:
        # Test with Apple
        company = Company('AAPL')
        print(f"Company: {company.name}")
        print(f"CIK: {company.cik}")
        
        # Get ALL filings without filtering
        print("\nGetting all filings...")
        all_filings = company.get_filings()
        print(f"Total filings found: {len(all_filings)}")
        
        # Check what forms are available
        if len(all_filings) > 0:
            # Get the data as pandas DataFrame for easier analysis
            df = all_filings.data.to_pandas()
            print(f"\nDataFrame shape: {df.shape}")
            print(f"Columns: {list(df.columns)}")
            
            # Show form types
            print(f"\nForm types available:")
            form_counts = df['form'].value_counts()
            print(form_counts.head(10))
            
            # Show recent filings
            print(f"\nRecent 10 filings:")
            recent = df.head(10)[['form', 'filing_date', 'accession_number']]
            for idx, row in recent.iterrows():
                print(f"  {row['form']} - {row['filing_date']} - {row['accession_number']}")
            
            # Specifically look for 10-K filings
            tenk_filings = df[df['form'] == '10-K']
            print(f"\n10-K filings found: {len(tenk_filings)}")
            
            if len(tenk_filings) > 0:
                print("Recent 10-K filings:")
                for idx, row in tenk_filings.head(5).iterrows():
                    print(f"  {row['form']} - {row['filing_date']} - {row['accession_number']}")
            
            # Try alternative form names
            alt_forms = ['10-K/A', '10-K405', '10KSB']
            for form in alt_forms:
                alt_filings = df[df['form'] == form]
                if len(alt_filings) > 0:
                    print(f"\n{form} filings found: {len(alt_filings)}")
        
        # Test with specific form filtering
        print(f"\n" + "="*50)
        print("Testing specific form filtering...")
        
        try:
            tenk_direct = company.get_filings(form='10-K')
            print(f"Direct 10-K query result: {len(tenk_direct)} filings")
            
            if len(tenk_direct) > 0:
                df_tenk = tenk_direct.data.to_pandas()
                print("Sample 10-K filings:")
                for idx, row in df_tenk.head(3).iterrows():
                    print(f"  {row['form']} - {row['filing_date']} - {row['accession_number']}")
        
        except Exception as e:
            print(f"Error with direct 10-K query: {e}")
        
        # Test with date filtering
        print(f"\n" + "="*50)
        print("Testing date filtering...")
        
        try:
            recent_filings = company.get_filings(filing_date="2020-01-01:2024-12-31")
            print(f"Recent filings (2020-2024): {len(recent_filings)}")
            
            if len(recent_filings) > 0:
                df_recent = recent_filings.data.to_pandas()
                form_counts_recent = df_recent['form'].value_counts()
                print("Form types in recent filings:")
                print(form_counts_recent.head(10))
                
        except Exception as e:
            print(f"Error with date filtering: {e}")
            
    except Exception as e:
        print(f"Error in debug: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_filings()
