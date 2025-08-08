"""
Debug the actual PyArrow data structure
"""

from edgar import Company, set_identity

# Set identity
set_identity("shreybansal1165@gmail.com")

def debug_data_structure():
    """Debug the actual data structure in the filings"""
    
    try:
        company = Company('AAPL')
        filings = company.get_filings(form='10-K')
        
        print(f"Found {len(filings)} filings")
        
        # Get the raw data
        data = filings.data
        print(f"Data type: {type(data)}")
        print(f"Data schema: {data.schema}")
        print(f"Column names: {data.column_names}")
        
        # Convert to pandas for easier debugging
        df = data.to_pandas()
        print(f"DataFrame columns: {list(df.columns)}")
        print(f"DataFrame shape: {df.shape}")
        
        # Show sample data
        print("\nSample data:")
        for col in df.columns:
            print(f"{col}: {df[col].iloc[0] if len(df) > 0 else 'N/A'}")
        
        # Test our safe get value method
        print(f"\n" + "="*50)
        print("Testing safe value extraction:")
        
        for i in range(min(3, len(df))):
            print(f"\nFiling {i}:")
            
            # Test each column
            for col in df.columns:
                try:
                    if hasattr(data[col], 'to_pylist'):
                        values = data[col].to_pylist()
                        value = values[i] if i < len(values) else None
                        print(f"  {col}: {value}")
                    else:
                        print(f"  {col}: No to_pylist method")
                except Exception as e:
                    print(f"  {col}: Error - {e}")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_data_structure()
