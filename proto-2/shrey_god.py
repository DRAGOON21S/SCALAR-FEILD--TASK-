import os
from datetime import datetime
from typing import Dict, List, Optional, Any
import hashlib
from pymongo import MongoClient
from bson import ObjectId
from edgar import Company, Filing, get_filings
import re
import time




class SECFilingsPipeline:
    """Pipeline for ingesting SEC filings into MongoDB with structured segments."""
    
    def __init__(self, mongo_uri: str = "mongodb://localhost:27017/", db_name: str = "sec_filings_db"):
        """Initialize MongoDB connection and collections."""
        self.client = MongoClient(mongo_uri)
        self.db = self.client[db_name]
        
        # Initialize collections
        self.documents = self.db['documents']
        self.chunks = self.db['chunks']
        self.financial_metrics = self.db['financial_metrics']
        self.relationships = self.db['relationships']
        
        # Test MongoDB connection
        try:
            self.client.admin.command('ping')
            print(f"✓ Connected to MongoDB database: {db_name}")
        except Exception as e:
            print(f"✗ MongoDB connection failed: {e}")
            raise
        
        # Create indexes for better query performance
        self._create_indexes()
    
    def _create_indexes(self):
        """Create indexes for optimal query performance."""
        # Documents collection indexes
        self.documents.create_index([("company_info.ticker", 1)])
        self.documents.create_index([("filing_metadata.form_type", 1)])
        self.documents.create_index([("filing_metadata.fiscal_year", -1)])
        
        # Chunks collection indexes
        self.chunks.create_index([("document_id", 1)])
        self.chunks.create_index([("hierarchy.item", 1)])
        self.chunks.create_index([("embedding", 1)])  # For vector search
        
        # Financial metrics indexes
        self.financial_metrics.create_index([("document_id", 1)])
        self.financial_metrics.create_index([("metric_info.metric_name", 1)])
        
        # Relationships indexes
        self.relationships.create_index([("document_id", 1)])
        self.relationships.create_index([("parent_id", 1), ("child_id", 1)])
    
    def generate_document_id(self, ticker: str, form_type: str, fiscal_year: int) -> str:
        """Generate unique document ID."""
        return f"{ticker}_{form_type.replace('-', '')}_{fiscal_year}"
    
    def generate_chunk_id(self, doc_id: str, part: str, item: str, section: str, index: int) -> str:
        """Generate unique chunk ID."""
        section_clean = re.sub(r'[^A-Za-z0-9]', '_', section)[:20]
        return f"{doc_id}_P{part}_I{item}_{section_clean}_{index:03d}"
    
    def process_company(self, ticker: str, form_type: str = "10-K", years: List[int] = None):
        """Process all filings for a company."""
        print(f"\n{'='*60}")
        print(f"Processing {ticker} {form_type} filings...")
        print(f"{'='*60}")
        
        if years is None:
            years = [2024, 2023]  # Default to last 2 years
        
        try:
            # Get company information
            company = Company(ticker)
            
            # Get filings
            filings = company.get_filings(form=form_type)
            
            for year in years:
                year_filings = [f for f in filings 
                               if f.filing_date and f.filing_date.year == year]
                
                if year_filings:
                    filing = year_filings[0]  # Get the first filing for the year
                    print(f"\nProcessing {ticker} {form_type} for {year}")
                    print(f"Filing date: {filing.filing_date}")
                    print(f"Accession: {filing.accession_no}")
                    
                    self.process_filing(filing, company, year)
                    time.sleep(1)  # Rate limiting
                else:
                    print(f"No {form_type} filing found for {ticker} in {year}")
                    
        except Exception as e:
            print(f"Error processing {ticker}: {str(e)}")
    
    def process_filing(self, filing: Filing, company: Company, fiscal_year: int):
        """Process a single filing and store in MongoDB."""
        ticker = company.tickers[0] if company.tickers else "UNKNOWN"
        
        # Generate document ID
        doc_id = self.generate_document_id(ticker, filing.form, fiscal_year)
        
        # Check if document already exists
        if self.documents.find_one({"_id": doc_id}):
            print(f"Document {doc_id} already exists, skipping...")
            return
        
        # Create document metadata
        document = {
            "_id": doc_id,
            "company_info": {
                "ticker": ticker,
                "name": company.name,
                "cik": str(company.cik).zfill(10),
                "sector": company.industry or "Technology"
            },
            "filing_metadata": {
                "form_type": filing.form,
                "fiscal_year": fiscal_year,
                "period_end": filing.period_of_report or f"{fiscal_year}-12-31",
                "filing_date": str(filing.filing_date) if filing.filing_date else None,
                "url": filing.filing_url,
                "accession_no": filing.accession_no,
                "file_size": 0,  # Would need to fetch actual size
                "page_count": 0   # Would need to parse actual pages
            },
            "processing_metadata": {
                "processed_date": datetime.utcnow(),
                "chunk_count": 0,
                "status": "processing",
                "version": "1.0"
            },
            "document_structure": {
                "parts": [],
                "items": [],
                "total_sections": 0
            }
        }
        
        # Process sections and create chunks
        chunks_created = self.process_sections(filing, doc_id, ticker)
        
        # Process XBRL data if available
        financial_metrics = self.process_xbrl_data(filing, doc_id)
        
        # Update document with final counts
        document["processing_metadata"]["chunk_count"] = chunks_created
        document["processing_metadata"]["status"] = "completed"
        document["document_structure"]["total_sections"] = chunks_created
        
        # Insert document with error handling
        try:
            result = self.documents.insert_one(document)
            print(f"✓ Created document: {doc_id}")
            print(f"  - Document ID: {result.inserted_id}")
            print(f"  - Chunks created: {chunks_created}")
            print(f"  - Financial metrics: {len(financial_metrics)}")
        except Exception as e:
            print(f"✗ Error inserting document {doc_id}: {str(e)}")
            return
    
    def process_sections(self, filing: Filing, doc_id: str, ticker: str) -> int:
        """Process filing sections and create chunks."""
        chunks_created = 0
        
        # Map of section patterns to items
        item_patterns = {
            "1": ["business", "overview", "description of business"],
            "1A": ["risk factors"],
            "1B": ["unresolved staff comments"],
            "1C": ["cybersecurity"],
            "2": ["properties"],
            "3": ["legal proceedings"],
            "4": ["mine safety"],
            "5": ["market for registrant"],
            "6": ["reserved", "selected financial"],
            "7": ["management discussion", "md&a"],
            "7A": ["quantitative and qualitative"],
            "8": ["financial statements"],
            "9": ["changes in and disagreements"],
            "9A": ["controls and procedures"],
            "9B": ["other information"],
            "9C": ["disclosure regarding"],
            "10": ["directors", "executive officers"],
            "11": ["executive compensation"],
            "12": ["security ownership"],
            "13": ["certain relationships"],
            "14": ["principal accountant"],
            "15": ["exhibits", "financial statement"]
        }
        
        try:
            # Get all sections
            sections = filing.sections()
            
            if not sections:
                print(f"  ⚠ No sections found for {doc_id}")
                return 0
            
            print(f"  Found {len(sections)} total sections")
            print(f"  Section names (first 10): {list(sections)[:10]}")
            
            matched_sections = 0
            for section_name in sections:
                # Determine if this is an item section
                item_num = None
                section_lower = section_name.lower()
                
                for item, patterns in item_patterns.items():
                    if any(pattern in section_lower for pattern in patterns):
                        item_num = item
                        break
                
                # Skip non-item sections
                if not item_num:
                    print(f"  - Skipped: '{section_name[:50]}' (no pattern match)")
                    continue
                else:
                    print(f"  + Matched: '{section_name[:50]}' -> Item {item_num}")
                    matched_sections += 1
                
                try:
                    # Get section text
                    print(f"    Getting text for section: {section_name}")
                    section_text = filing.search(section_name)
                    print(f"    Search returned: {len(section_text) if section_text else 0} results")
                    
                    if section_text and len(section_text) > 0:
                        text_content = " ".join(section_text[:5])  # Limit to first 5 matches
                        print(f"    Text content length: {len(text_content)} characters")
                        
                        if len(text_content.strip()) < 50:  # Skip very short sections
                            print(f"    Skipping - content too short ({len(text_content)} chars)")
                            continue
                        
                        # Determine part (I or II based on item number)
                        part = "I" if item_num in ["1", "1A", "1B", "1C", "2", "3", "4", "5", "6"] else "II"
                        
                        # Create chunk
                        chunk = {
                            "_id": ObjectId(),
                            "chunk_id": self.generate_chunk_id(doc_id, part, item_num, section_name, chunks_created),
                            "document_id": doc_id,
                            
                            # Hierarchical Structure
                            "hierarchy": {
                                "part": part,
                                "item": item_num,
                                "section_name": section_name,
                                "subsection": None,
                                "level": 1,
                                "parent_chunk_id": None,
                                "child_chunk_ids": []
                            },
                            
                            # Content
                            "content": {
                                "title": section_name,
                                "text": text_content[:5000],  # Limit text length
                                "text_clean": re.sub(r'[^a-zA-Z0-9\s]', '', text_content.lower())[:5000],
                                "token_count": len(text_content.split()),
                                "word_count": len(text_content.split())
                            },
                            
                            # Vector embedding (placeholder - would need actual embedding model)
                            "embedding": [0.0] * 384,  # Placeholder for 384-dim embedding
                            
                            # Classification & Metadata
                            "chunk_type": self.classify_chunk_type(item_num),
                            "content_category": self.get_content_category(item_num),
                            "topics": self.extract_topics(text_content[:5000]),
                            "entities": self.extract_entities(text_content[:5000], ticker),
                            
                            # Source Information
                            "source": {
                                "page_numbers": [],
                                "start_position": 0,
                                "end_position": len(text_content),
                                "contains_tables": self.contains_tables(text_content[:5000]),
                                "contains_figures": False
                            },
                            
                            # Search Optimization
                            "search_keywords": self.extract_keywords(text_content[:5000]),
                            "semantic_tags": [f"item_{item_num}", f"part_{part}", section_name.lower()],
                            
                            # Timestamps
                            "created_at": datetime.utcnow(),
                            "updated_at": datetime.utcnow()
                        }
                        
                        try:
                            chunk_result = self.chunks.insert_one(chunk)
                            chunks_created += 1
                            print(f"  ✓ Item {item_num}: {section_name[:50]} (ID: {chunk_result.inserted_id})")
                        except Exception as chunk_error:
                            print(f"  ✗ Error inserting chunk for Item {item_num}: {str(chunk_error)}")
                            continue
                    else:
                        print(f"    No text content found for section: {section_name}")
                        
                except Exception as e:
                    print(f"  ⚠ Error processing section '{section_name}': {str(e)}")
                    continue
            
            print(f"  Total sections matched: {matched_sections}, chunks created: {chunks_created}")
                    
                    
        except Exception as e:
            print(f"  ✗ Error getting sections: {str(e)}")
        
        return chunks_created
    
    def process_xbrl_data(self, filing: Filing, doc_id: str) -> List[Dict]:
        """Process XBRL data and store financial metrics."""
        metrics_created = []
        
        print(f"  Processing XBRL data for {doc_id}...")
        
        try:
            # Get XBRL data
            print(f"  Getting XBRL object...")
            xbrl = filing.xbrl()
            
            if not xbrl:
                print(f"  ⚠ No XBRL data available")
                return metrics_created
            
            print(f"  ✓ XBRL data available")
            
            # Get financial statements
            print(f"  Getting financials...")
            try:
                financials = xbrl.get_facts()  # Try XBRL facts first
                print(f"  ✓ XBRL facts available: {len(financials) if financials else 0} facts")
                
                if financials and len(financials) > 0:
                    # Create sample financial metrics from XBRL facts
                    self.create_sample_financial_metrics(financials, doc_id, metrics_created)
                else:
                    print(f"  - No XBRL facts found")
                    
            except AttributeError:
                # Fallback: try direct financials access
                print(f"  Trying direct financials access...")
                try:
                    financials = filing.financials
                    if financials:
                        print(f"  ✓ Direct financials available")
                        
                        # Process income statement
                        if hasattr(financials, 'income_statement'):
                            print(f"  Processing income statement...")
                            self.process_financial_statement(
                                financials.income_statement,
                                doc_id,
                                "income_statement",
                                metrics_created
                            )
                        else:
                            print(f"  - No income statement found")
                        
                        # Process balance sheet
                        if hasattr(financials, 'balance_sheet'):
                            print(f"  Processing balance sheet...")
                            self.process_financial_statement(
                                financials.balance_sheet,
                                doc_id,
                                "balance_sheet",
                                metrics_created
                            )
                        else:
                            print(f"  - No balance sheet found")
                        
                        # Process cash flow
                        if hasattr(financials, 'cash_flow'):
                            print(f"  Processing cash flow...")
                            self.process_financial_statement(
                                financials.cash_flow,
                                doc_id,
                                "cash_flow",
                                metrics_created
                            )
                        else:
                            print(f"  - No cash flow found")
                    else:
                        print(f"  ⚠ No direct financials available")
                except Exception as financials_error:
                    print(f"  ⚠ Direct financials access failed: {str(financials_error)}")
                    # Create placeholder metrics
                    self.create_placeholder_metrics(doc_id, metrics_created)
                    
        except Exception as e:
            print(f"  ⚠ Error processing XBRL: {str(e)}")
        
        print(f"  XBRL processing complete. Metrics created: {len(metrics_created)}")
        return metrics_created
    
    def process_financial_statement(self, statement, doc_id: str, statement_type: str, metrics_list: List):
        """Process a financial statement and extract metrics."""
        if not statement:
            return
        
        try:
            # Common metrics to extract
            metric_mappings = {
                "income_statement": {
                    "Revenue": "revenue",
                    "Net Income": "net_income",
                    "Operating Income": "operating_income",
                    "Gross Profit": "gross_profit"
                },
                "balance_sheet": {
                    "Total Assets": "total_assets",
                    "Total Liabilities": "total_liabilities",
                    "Total Equity": "shareholders_equity",
                    "Current Assets": "current_assets"
                },
                "cash_flow": {
                    "Operating Cash Flow": "operating_cash_flow",
                    "Investing Cash Flow": "investing_cash_flow",
                    "Financing Cash Flow": "financing_cash_flow"
                }
            }
            
            mappings = metric_mappings.get(statement_type, {})
            
            for display_name, metric_key in mappings.items():
                try:
                    # Try to get metric value from statement
                    value = statement.iloc[0] if hasattr(statement, 'iloc') else None
                    
                    if value is not None:
                        metric = {
                            "_id": ObjectId(),
                            "document_id": doc_id,
                            "source_chunk_id": f"{doc_id}_XBRL_{statement_type}",
                            
                            "metric_info": {
                                "metric_name": metric_key,
                                "metric_type": statement_type.replace("_", " "),
                                "category": statement_type,
                                "subcategory": display_name
                            },
                            
                            "time_series": [{
                                "period": "annual",
                                "period_type": "annual",
                                "value": float(value) if isinstance(value, (int, float)) else 0,
                                "currency": "USD",
                                "unit": "millions"
                            }],
                            
                            "calculated_metrics": {},
                            "segment_breakdown": {},
                            "geographic_breakdown": {},
                            
                            "created_at": datetime.utcnow()
                        }
                        
                        try:
                            metric_result = self.financial_metrics.insert_one(metric)
                            metrics_list.append(metric)
                            print(f"    ✓ Metric {metric_key}: {float(value) if isinstance(value, (int, float)) else 0}")
                        except Exception as metric_error:
                            print(f"    ✗ Error inserting metric {metric_key}: {str(metric_error)}")
                            continue
                        
                except Exception as e:
                    continue
                    
        except Exception as e:
            print(f"    ⚠ Error processing {statement_type}: {str(e)}")
    
    def create_sample_financial_metrics(self, facts, doc_id: str, metrics_list: List):
        """Create sample financial metrics from XBRL facts."""
        try:
            # Look for common financial metrics in XBRL facts
            common_metrics = {
                'revenues': 'revenue',
                'netincome': 'net_income', 
                'totalassets': 'total_assets',
                'operatingincome': 'operating_income'
            }
            
            facts_created = 0
            for fact_key, metric_name in common_metrics.items():
                # Search for facts containing the key
                matching_facts = [f for f in facts if fact_key.lower() in str(f).lower()]
                
                if matching_facts:
                    # Use the first matching fact
                    fact = matching_facts[0]
                    
                    metric = {
                        "_id": ObjectId(),
                        "document_id": doc_id,
                        "source_chunk_id": f"{doc_id}_XBRL_{metric_name}",
                        
                        "metric_info": {
                            "metric_name": metric_name,
                            "metric_type": "xbrl_fact",
                            "category": "financial",
                            "subcategory": fact_key
                        },
                        
                        "time_series": [{
                            "period": "annual",
                            "period_type": "annual", 
                            "value": 0,  # Placeholder - would need proper parsing
                            "currency": "USD",
                            "unit": "dollars"
                        }],
                        
                        "calculated_metrics": {},
                        "segment_breakdown": {},
                        "geographic_breakdown": {},
                        
                        "created_at": datetime.utcnow()
                    }
                    
                    try:
                        metric_result = self.financial_metrics.insert_one(metric)
                        metrics_list.append(metric)
                        facts_created += 1
                        print(f"    ✓ XBRL Metric {metric_name}: created from fact")
                    except Exception as metric_error:
                        print(f"    ✗ Error inserting XBRL metric {metric_name}: {str(metric_error)}")
                        continue
            
            print(f"    Created {facts_created} metrics from XBRL facts")
                        
        except Exception as e:
            print(f"    ⚠ Error creating sample metrics: {str(e)}")
    
    def create_placeholder_metrics(self, doc_id: str, metrics_list: List):
        """Create placeholder financial metrics when XBRL is unavailable."""
        try:
            placeholder_metrics = [
                ("revenue", "Placeholder Revenue"),
                ("net_income", "Placeholder Net Income"),
                ("total_assets", "Placeholder Total Assets")
            ]
            
            for metric_key, metric_name in placeholder_metrics:
                metric = {
                    "_id": ObjectId(),
                    "document_id": doc_id,
                    "source_chunk_id": f"{doc_id}_PLACEHOLDER_{metric_key}",
                    
                    "metric_info": {
                        "metric_name": metric_key,
                        "metric_type": "placeholder",
                        "category": "financial",
                        "subcategory": "estimated"
                    },
                    
                    "time_series": [{
                        "period": "annual",
                        "period_type": "annual",
                        "value": 0,
                        "currency": "USD", 
                        "unit": "placeholder"
                    }],
                    
                    "calculated_metrics": {},
                    "segment_breakdown": {},
                    "geographic_breakdown": {},
                    
                    "created_at": datetime.utcnow()
                }
                
                try:
                    metric_result = self.financial_metrics.insert_one(metric)
                    metrics_list.append(metric)
                    print(f"    ✓ Placeholder Metric {metric_key}: created")
                except Exception as metric_error:
                    print(f"    ✗ Error inserting placeholder metric {metric_key}: {str(metric_error)}")
                    continue
                    
        except Exception as e:
            print(f"    ⚠ Error creating placeholder metrics: {str(e)}")
    
    def classify_chunk_type(self, item_num: str) -> str:
        """Classify chunk type based on item number."""
        type_mapping = {
            "1": "narrative",
            "1A": "risk_factor",
            "1B": "narrative",
            "1C": "risk_factor",
            "2": "narrative",
            "3": "narrative",
            "7": "narrative",
            "7A": "risk_factor",
            "8": "financial",
            "15": "list"
        }
        return type_mapping.get(item_num, "narrative")
    
    def get_content_category(self, item_num: str) -> str:
        """Get content category based on item number."""
        category_mapping = {
            "1": "business_description",
            "1A": "risk_factors",
            "1B": "staff_comments",
            "1C": "cybersecurity",
            "2": "properties",
            "3": "legal_proceedings",
            "7": "mda",
            "7A": "market_risk",
            "8": "financial_statements",
            "15": "exhibits"
        }
        return category_mapping.get(item_num, "other")
    
    def extract_topics(self, text: str) -> List[str]:
        """Extract topics from text (simplified)."""
        topics = []
        topic_keywords = {
            "products": ["product", "service", "offering"],
            "competition": ["competitor", "competition", "market share"],
            "technology": ["technology", "innovation", "research"],
            "regulation": ["regulation", "compliance", "government"],
            "financial": ["revenue", "profit", "income", "expense"],
            "risk": ["risk", "uncertainty", "threat"],
            "strategy": ["strategy", "plan", "objective", "goal"]
        }
        
        text_lower = text.lower()
        for topic, keywords in topic_keywords.items():
            if any(keyword in text_lower for keyword in keywords):
                topics.append(topic)
        
        return topics[:5]  # Limit to 5 topics
    
    def extract_entities(self, text: str, ticker: str) -> List[str]:
        """Extract entities from text (simplified)."""
        entities = [ticker]
        
        # Common tech company names
        tech_companies = ["Apple", "Microsoft", "Google", "Amazon", "Meta", "Tesla", "NVIDIA"]
        for company in tech_companies:
            if company in text and company != ticker:
                entities.append(company)
        
        # Common products for AAPL and MSFT
        if ticker == "AAPL":
            products = ["iPhone", "iPad", "Mac", "Apple Watch", "AirPods", "Services"]
            for product in products:
                if product in text:
                    entities.append(product)
        elif ticker == "MSFT":
            products = ["Windows", "Office", "Azure", "Xbox", "Surface", "LinkedIn"]
            for product in products:
                if product in text:
                    entities.append(product)
        
        return list(set(entities))[:10]  # Unique entities, limit to 10
    
    def extract_keywords(self, text: str) -> List[str]:
        """Extract keywords from text (simplified)."""
        # Simple keyword extraction based on frequency
        words = re.findall(r'\b[a-z]+\b', text.lower())
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
                     'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were'}
        words = [w for w in words if w not in stop_words and len(w) > 3]
        
        # Count frequency
        word_freq = {}
        for word in words:
            word_freq[word] = word_freq.get(word, 0) + 1
        
        # Get top keywords
        keywords = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
        return [k[0] for k in keywords[:10]]
    
    def contains_tables(self, text: str) -> bool:
        """Check if text contains tables (simplified)."""
        table_indicators = ['<table', '|', '\t\t', '$', '%', 'Total', 'Year Ended']
        return any(indicator in text for indicator in table_indicators)
    
    def create_relationships(self, doc_id: str):
        """Create relationships between chunks."""
        # Get all chunks for this document
        chunks = list(self.chunks.find({"document_id": doc_id}))
        
        # Create hierarchy relationships
        for chunk in chunks:
            # Create relationship document
            relationship = {
                "_id": ObjectId(),
                "document_id": doc_id,
                "relationship_type": "chunk_hierarchy",
                "parent_id": chunk["hierarchy"]["parent_chunk_id"],
                "child_id": chunk["chunk_id"],
                "relationship_strength": 1.0,
                "context": "item_section"
            }
            
            if chunk["hierarchy"]["parent_chunk_id"]:
                self.relationships.insert_one(relationship)
    
    def get_statistics(self):
        """Get database statistics."""
        stats = {
            "total_documents": self.documents.count_documents({}),
            "total_chunks": self.chunks.count_documents({}),
            "total_financial_metrics": self.financial_metrics.count_documents({}),
            "total_relationships": self.relationships.count_documents({}),
            "documents_by_ticker": list(self.documents.aggregate([
                {"$group": {"_id": "$company_info.ticker", "count": {"$sum": 1}}}
            ])),
            "chunks_by_type": list(self.chunks.aggregate([
                {"$group": {"_id": "$chunk_type", "count": {"$sum": 1}}}
            ]))
        }
        return stats
    
    def verify_data_insertion(self):
        """Verify that data was properly inserted into MongoDB."""
        print("\n" + "="*50)
        print("VERIFYING DATA INSERTION")
        print("="*50)
        
        try:
            # Check collections exist
            collections = self.db.list_collection_names()
            expected_collections = ['documents', 'chunks', 'financial_metrics', 'relationships']
            
            print(f"Available collections: {collections}")
            
            for col_name in expected_collections:
                if col_name in collections:
                    count = self.db[col_name].count_documents({})
                    print(f"✓ {col_name}: {count} records")
                    
                    # Show sample document
                    if count > 0:
                        sample = self.db[col_name].find_one()
                        if sample:
                            print(f"  Sample ID: {sample.get('_id', 'No ID')}")
                else:
                    print(f"✗ {col_name}: Collection not found")
            
            # Test queries
            print(f"\nTesting Queries:")
            
            # Test document query
            apple_docs = list(self.documents.find({"company_info.ticker": "AAPL"}))
            print(f"✓ Apple documents: {len(apple_docs)}")
            
            # Test chunk query
            chunks_with_text = list(self.chunks.find({"content.text": {"$exists": True, "$ne": ""}}))
            print(f"✓ Chunks with text content: {len(chunks_with_text)}")
            
            # Test financial metrics query
            financial_records = list(self.financial_metrics.find({}))
            print(f"✓ Financial metrics: {len(financial_records)}")
            
            return True
            
        except Exception as e:
            print(f"✗ Verification failed: {str(e)}")
            return False


def main():
    """Main execution function."""
    # Initialize pipeline
    from edgar import set_identity

# Use your name and email
# set_identity("John Doe john.doe@company.com")

# Or just your email
    set_identity("shreybansal1165@gmail.com")
    pipeline = SECFilingsPipeline()
    
    print("\n" + "="*60)
    print("SEC Filings MongoDB Ingestion Pipeline")
    print("="*60)
    
    # Process AAPL and MSFT 10-K filings
    tickers = ["AAPL", "MSFT"]
    years = [2024, 2023]  # Process last 2 years
    
    for ticker in tickers:
        pipeline.process_company(ticker, "10-K", years)
        time.sleep(2)  # Rate limiting between companies
    
    # Print statistics
    print("\n" + "="*60)
    print("Pipeline Statistics")
    print("="*60)
    
    stats = pipeline.get_statistics()
    print(f"\nDatabase Summary:")
    print(f"  Total Documents: {stats['total_documents']}")
    print(f"  Total Chunks: {stats['total_chunks']}")
    print(f"  Total Financial Metrics: {stats['total_financial_metrics']}")
    print(f"  Total Relationships: {stats['total_relationships']}")
    
    print(f"\nDocuments by Ticker:")
    for item in stats['documents_by_ticker']:
        print(f"  {item['_id']}: {item['count']} documents")
    
    print(f"\nChunks by Type:")
    for item in stats['chunks_by_type']:
        print(f"  {item['_id']}: {item['count']} chunks")
    
    # Verify data insertion
    pipeline.verify_data_insertion()
    
    print("\n✅ Pipeline completed successfully!")


if __name__ == "__main__":
    main()