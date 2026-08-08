import fitz
import pdfplumber
import os
import re

def detect_category(text: str) -> str:
    text_lower = text.lower()
    
    # Categorization logic using keywords
    if any(kw in text_lower for kw in ['revenue', 'sales', 'product revenue']):
        return 'revenue'
    if any(kw in text_lower for kw in ['expenses', 'costs']):
        return 'expenses'
    if any(kw in text_lower for kw in ['balance sheet', 'assets', 'liabilities']):
        return 'assets_liabilities'
    if any(kw in text_lower for kw in ['cash flow']):
        return 'cash_flow'
    if any(kw in text_lower for kw in ['earnings per share', 'net income']):
        return 'earnings'
    if any(kw in text_lower for kw in ['segment']):
        return 'segments'
    if any(kw in text_lower for kw in ['headcount']):
        return 'headcount'
    if any(kw in text_lower for kw in ['executive compensation', 'stock awards', 'rsus']):
        return 'executive_comp'
    if any(kw in text_lower for kw in ['employee compensation', 'benefits']):
        return 'compensation'
    if any(kw in text_lower for kw in ['strategy', 'outlook']):
        return 'strategy'
    if any(kw in text_lower for kw in ['research and development']):
        return 'r_and_d'
    if any(kw in text_lower for kw in ['product roadmap', 'future products']):
        return 'product_roadmap'
    if any(kw in text_lower for kw in ['legal proceedings', 'litigation']):
        return 'legal'
    if any(kw in text_lower for kw in ['risk factors']):
        return 'risk_factors'
    if any(kw in text_lower for kw in ['market data', 'stock price']):
        return 'market_data'
    if any(kw in text_lower for kw in ['shareholders equity']):
        return 'shareholder_equity'
    if any(kw in text_lower for kw in ['debt', 'notes', 'financing']):
        return 'debt_financing'
    if any(kw in text_lower for kw in ['tax provisions']):
        return 'tax'
    if any(kw in text_lower for kw in ['operations']):
        return 'operations'
    
    return 'general'

def parse_pdf(file_path: str) -> list[dict]:
    filename = os.path.basename(file_path)
    
    # Extract fiscal year from filename (e.g. apple_ar_2023.pdf -> '2023')
    match = re.search(r'(20\d{2})', filename)
    fiscal_year = match.group(1) if match else "Unknown"

    chunks = []
    
    try:
        # Use pymupdf for text
        doc = fitz.open(file_path)
        
        # Use pdfplumber for tables
        with pdfplumber.open(file_path) as pdf:
            for page_num in range(len(doc)):
                page = doc[page_num]
                text = page.get_text()
                
                # Check for tables using pdfplumber
                plumber_page = pdf.pages[page_num]
                tables = plumber_page.extract_tables()
                
                # Append tables to text
                if tables:
                    for table in tables:
                        for row in table:
                            clean_row = [str(cell).replace('\n', ' ') if cell else '' for cell in row]
                            text += '\n' + ' | '.join(clean_row)
                
                # Detect section simply by first line or heuristic
                lines = text.strip().split('\n')
                section = lines[0] if lines else 'Unknown'
                if len(section) > 50:
                    section = 'Unknown'
                    
                data_category = detect_category(text)
                
                chunk_dict = {
                    'content': text,
                    'source_file': filename,
                    'page': page_num + 1,
                    'section': section,
                    'data_category': data_category,
                    'fiscal_year': fiscal_year,
                    'metadata': {
                        'has_tables': bool(tables)
                    }
                }
                chunks.append(chunk_dict)
    except Exception as e:
        print(f"Error parsing PDF {file_path}: {e}")
        
    return chunks
