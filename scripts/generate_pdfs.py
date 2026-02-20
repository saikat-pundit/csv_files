#!/usr/bin/env python3
"""
Generate PDFs from specific columns (AW to BB) of CSV rows
Each row becomes a separate PDF with format: COLUMN HEADER: <ROW DATA>
Filename is taken from column index 51 and shown in the middle of the page
"""

import pandas as pd
import argparse
from pathlib import Path
from fpdf import FPDF
import requests
from io import StringIO
import re

class PDFGenerator(FPDF):
    def __init__(self):
        super().__init__()
        self.set_auto_page_break(auto=True, margin=15)
    
    def header(self):
        # Removed the header text completely
        pass
    
    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')

def download_csv_from_url(url):
    """Download CSV from URL"""
    try:
        response = requests.get(url)
        response.raise_for_status()
        
        # Read CSV data
        csv_data = StringIO(response.text)
        df = pd.read_csv(csv_data)
        print(f"✓ Downloaded CSV with {len(df)} rows and {len(df.columns)} columns")
        return df
    except Exception as e:
        print(f"Error downloading CSV: {e}")
        return None

def get_columns_aw_to_bb(df):
    """Get columns AW to BB (positions 49-54 in 1-based indexing)"""
    all_columns = df.columns.tolist()
    
    # Columns AW to BB are positions 49-54 in 1-based indexing
    # In 0-based indexing: 48-53
    if len(all_columns) >= 54:
        selected_columns = all_columns[48:54]  # AW(48) to BB(53) in 0-based
        print(f"✓ Selected columns AW to BB: {selected_columns}")
        return selected_columns
    else:
        print(f"Warning: CSV has only {len(all_columns)} columns, cannot select AW to BB")
        # Return last 6 columns as fallback
        start_idx = max(0, len(all_columns) - 6)
        selected_columns = all_columns[start_idx:]
        print(f"  Using last {len(selected_columns)} columns instead: {selected_columns}")
        return selected_columns

def sanitize_filename(filename):
    """Remove invalid characters from filename"""
    # Remove or replace characters that are invalid in filenames
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    # Limit length
    if len(filename) > 50:
        filename = filename[:50]
    return filename

def create_pdf_for_row(row_data, selected_columns, output_filename, title_text):
    """Create PDF for a single row with only selected columns"""
    pdf = PDFGenerator()
    pdf.add_page()
    
    # Set margins
    pdf.set_left_margin(15)
    pdf.set_right_margin(15)
    
    # Add title in the middle of the page
    pdf.set_font('Arial', 'B', 16)
    
    # Calculate width to center the text
    title_width = pdf.get_string_width(title_text)
    page_width = pdf.w - 30  # Width minus margins
    x_position = 15 + (page_width - title_width) / 2  # Center calculation
    
    pdf.set_x(x_position)
    pdf.cell(title_width, 20, title_text, 0, 1, 'L')
    pdf.ln(10)
    
    # Add selected columns data
    pdf.set_font('Arial', '', 10)
    
    for col in selected_columns:
        if col in row_data.index:
            value = row_data[col]
            
            # Handle NaN or empty values
            if pd.isna(value) or value == '':
                value = 'N/A'
            else:
                value = str(value).strip()
            
            # Skip if value is empty after stripping
            if not value or value == 'N/A':
                continue
            
            # Column name in bold with consistent width
            pdf.set_font('Arial', 'B', 10)
            
            # Calculate available width for value
            page_width = pdf.w - 30  # Subtract margins
            col_name_width = 45  # Fixed width for column names
            
            # Set X position for consistent alignment
            pdf.set_x(15)
            pdf.cell(col_name_width, 6, f"{col}:", 0, 0, 'L')
            
            # Value with wrapping for long text
            pdf.set_font('Arial', '', 10)
            
            # Get remaining width for value
            remaining_width = page_width - col_name_width - 2
            
            # Handle multi-line values
            if pdf.get_string_width(value) > remaining_width:
                # Move to next line for value
                pdf.ln(6)
                pdf.set_x(15 + col_name_width + 2)
                
                # Write multi-line text
                pdf.multi_cell(remaining_width, 6, value, 0, 'L')
            else:
                pdf.cell(0, 6, value, 0, 1, 'L')
            
            # Small space between fields
            pdf.ln(1)
    
    # Save the PDF
    pdf.output(output_filename)
    print(f"  ✓ Generated: {output_filename}")

def main():
    parser = argparse.ArgumentParser(description='Generate PDFs from CSV rows (columns AW to BB)')
    parser.add_argument('--csv-url', required=True, help='URL of the CSV file')
    parser.add_argument('--output-dir', default='pdfs', help='Output directory for PDFs')
    parser.add_argument('--start-row', type=int, default=1, help='Starting row number (1-based)')
    parser.add_argument('--end-row', type=int, default=None, help='Ending row number (1-based)')
    
    args = parser.parse_args()
    
    # Create output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(exist_ok=True)
    
    print(f"📥 Downloading CSV from: {args.csv_url}")
    
    # Download and read CSV
    df = download_csv_from_url(args.csv_url)
    if df is None:
        return
    
    # Get columns AW to BB
    selected_columns = get_columns_aw_to_bb(df)
    
    if not selected_columns:
        print("Error: No columns selected for PDF generation")
        return
    
    # Determine row range
    start_idx = args.start_row - 1
    end_idx = args.end_row if args.end_row else len(df)
    
    # Validate row range
    if start_idx < 0 or end_idx > len(df):
        print(f"Error: Row range {args.start_row}-{end_idx} is invalid. CSV has {len(df)} rows (1-{len(df)})")
        return
    
    print(f"\n📄 Generating PDFs for rows {args.start_row} to {end_idx}")
    print(f"Total rows to process: {end_idx - start_idx}")
    print(f"Columns included: {', '.join(selected_columns)}")
    print("-" * 50)
    
    # Get column at index 51 for filename and title (0-based index 50)
    all_columns = df.columns.tolist()
    if len(all_columns) >= 51:
        title_column = all_columns[50]  # Column index 51 (0-based 50)
        print(f"📝 Using column '{title_column}' (index 51) for filename and title")
    else:
        title_column = None
        print("⚠️  CSV has less than 51 columns, using row number for filename and title")
    
    # Generate PDFs for each row in range
    generated_files = []
    for idx in range(start_idx, end_idx):
        row_data = df.iloc[idx]
        row_num = idx + 1
        
        # Get title and filename from column index 51
        if title_column and title_column in row_data.index:
            title_text = str(row_data[title_column])
            if pd.isna(title_text) or title_text == '':
                title_text = f"Record_{row_num:03d}"
                base_name = f"record_{row_num:03d}"
            else:
                base_name = sanitize_filename(title_text)
        else:
            title_text = f"Record_{row_num:03d}"
            base_name = f"record_{row_num:03d}"
        
        output_filename = output_dir / f"{base_name}.pdf"
        
        create_pdf_for_row(row_data, selected_columns, output_filename, title_text)
        generated_files.append(output_filename)
    
    print("-" * 50)
    print(f"\n✅ Successfully generated {len(generated_files)} PDFs in '{args.output_dir}/'")
    
    # Create a summary file
    summary_file = output_dir / "summary.txt"
    with open(summary_file, 'w') as f:
        f.write(f"PDF Generation Summary (Columns AW to BB)\n")
        f.write(f"{'='*50}\n")
        f.write(f"CSV Source: {args.csv_url}\n")
        f.write(f"Rows processed: {args.start_row} to {end_idx}\n")
        f.write(f"Columns included: {', '.join(selected_columns)}\n")
        if title_column:
            f.write(f"Title from column: {title_column} (index 51)\n")
        f.write(f"Total PDFs: {len(generated_files)}\n")
        f.write(f"\nGenerated files:\n")
        for pdf in generated_files:
            f.write(f"  - {pdf.name}\n")
    
    print(f"📋 Summary saved to: {summary_file}")

if __name__ == "__main__":
    main()
