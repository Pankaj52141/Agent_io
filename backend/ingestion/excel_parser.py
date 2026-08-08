import xlrd
import os
import re

def detect_category(name: str, content: str) -> str:
    combined = (name + " " + content).lower()
    
    if any(kw in combined for kw in ['revenue', 'income', 'sales']):
        return 'revenue'
    if any(kw in combined for kw in ['balance sheet', 'assets', 'liabilities']):
        return 'assets_liabilities'
    if any(kw in combined for kw in ['cash flow']):
        return 'cash_flow'
    if any(kw in combined for kw in ['earnings per share', 'net income']):
        return 'earnings'
    return 'general'

def parse_excel(file_path: str) -> list[dict]:
    filename = os.path.basename(file_path)
    
    match = re.search(r'(20\d{2})', filename)
    fiscal_year = match.group(1) if match else "Unknown"
    
    fiscal_quarter = "Unknown"
    filename_lower = filename.lower()
    if 'feb' in filename_lower:
        fiscal_quarter = 'Q1'
    elif 'may' in filename_lower:
        fiscal_quarter = 'Q2'
    elif 'aug' in filename_lower:
        fiscal_quarter = 'Q3'
    elif 'nov' in filename_lower or 'oct' in filename_lower:
        fiscal_quarter = 'Q4'

    chunks = []
    
    try:
        wb = xlrd.open_workbook(file_path)
        for sheet in wb.sheets():
            sheet_name = sheet.name
            
            content_lines = []
            for rowx in range(sheet.nrows):
                row_values = sheet.row_values(rowx)
                clean_row = [str(val).replace('\n', ' ').strip() for val in row_values]
                content_lines.append(' | '.join(clean_row))
                
            content = '\n'.join(content_lines)
            data_category = detect_category(sheet_name, content)
            
            chunk_dict = {
                'content': content,
                'source_file': filename,
                'page_or_sheet': sheet_name,
                'section': sheet_name,
                'data_category': data_category,
                'fiscal_year': fiscal_year,
                'fiscal_quarter': fiscal_quarter,
                'metadata': {
                    'num_rows': sheet.nrows,
                    'num_cols': sheet.ncols
                }
            }
            chunks.append(chunk_dict)
    except Exception as e:
        print(f"Error parsing Excel {file_path}: {e}")
        
    return chunks
