import pandas as pd
import argparse
from pathlib import Path
from fpdf import FPDF
import requests
from io import StringIO
import re
import unicodedata

class PDFGenerator(FPDF):
    def __init__(self):
        super().__init__(orientation='L')
        self.set_auto_page_break(auto=True, margin=15)

def download_csv_from_url(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        df = pd.read_csv(StringIO(response.text))
        print(f"✓ Downloaded CSV with {len(df)} rows")
        return df
    except Exception as e:
        print(f"Error: {e}")
        return None

def get_columns_aw_to_bb(df):
    all_columns = df.columns.tolist()
    if len(all_columns) >= 54:
        return all_columns[48:54]
    else:
        return all_columns[-6:]

def sanitize_filename(filename):
    if pd.isna(filename) or filename == '':
        return "unnamed"
    filename = str(filename).strip()
    filename = re.sub(r'[<>:"/\\|?*;,]', '_', filename)
    filename = re.sub(r'\s+', '_', filename)
    filename = filename.strip('_')
    if len(filename) > 45:
        filename = filename[:45]
    return filename or "unnamed"

def add_signature(pdf):
    sig_path = Path("sign.jpg")
    if not sig_path.exists():
        sig_path = Path("sign.jpeg")
    if sig_path.exists():
        try:
            page_width = pdf.w
            sig_width = 80  # Increased from 40 to 80
            sig_height = 40  # Increased from 20 to 40
            x_position = page_width - sig_width - 15  # Right aligned with margin
            pdf.image(str(sig_path), x=x_position, y=pdf.get_y() + 5, w=sig_width, h=sig_height)
            pdf.ln(45)  # Increased from 25 to 45 to accommodate bigger signature
        except:
            pass

def create_pdf_for_row(row_data, selected_columns, output_filename):
    pdf = PDFGenerator()
    pdf.add_page()
    pdf.set_left_margin(15)
    pdf.set_right_margin(15)
    pdf.set_font('Arial', '', 10)
    
    for col in selected_columns:
        if col in row_data.index:
            value = row_data[col]
            if pd.isna(value) or value == '':
                continue
            value = str(value).strip()
            if not value:
                continue
            
            pdf.set_font('Arial', 'B', 10)
            pdf.set_x(15)
            pdf.cell(65, 6, f"{col}:", 0, 0, 'L')
            
            pdf.set_font('Arial', '', 10)
            clean_value = ' '.join(value.split())
            remaining_width = pdf.w - 30 - 65 - 2
            
            if pdf.get_string_width(clean_value) > remaining_width:
                pdf.ln(6)
                pdf.set_x(15 + 65 + 2)
                pdf.multi_cell(remaining_width, 6, clean_value, 0, 'L')
            else:
                pdf.cell(0, 6, clean_value, 0, 1, 'L')
            pdf.ln(2)
    
    pdf.ln(5)
    add_signature(pdf)
    pdf.output(output_filename)
    print(f"  ✓ {output_filename.name}")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--csv-url', required=True)
    parser.add_argument('--output-dir', default='pdfs')
    parser.add_argument('--start-row', type=int, default=1)
    parser.add_argument('--end-row', type=int, default=None)
    args = parser.parse_args()
    
    output_dir = Path(args.output_dir)
    output_dir.mkdir(exist_ok=True)
    
    df = download_csv_from_url(args.csv_url)
    if df is None:
        return
    
    selected_columns = get_columns_aw_to_bb(df)
    if not selected_columns:
        print("No columns selected")
        return
    
    start_idx = args.start_row - 1
    end_idx = args.end_row if args.end_row else len(df)
    
    all_columns = df.columns.tolist()
    filename_column = all_columns[51] if len(all_columns) >= 52 else None
    
    for idx in range(start_idx, end_idx):
        row_data = df.iloc[idx]
        row_num = idx + 1
        
        if filename_column and filename_column in row_data.index:
            base_name = sanitize_filename(row_data[filename_column])
        else:
            base_name = f"record_{row_num:03d}"
        
        output_filename = output_dir / f"{base_name}.pdf"
        if output_filename.exists():
            output_filename = output_dir / f"{base_name}_{row_num:03d}.pdf"
        
        try:
            create_pdf_for_row(row_data, selected_columns, output_filename)
        except Exception as e:
            print(f"  ❌ Row {row_num} failed: {e}")

if __name__ == "__main__":
    main()
