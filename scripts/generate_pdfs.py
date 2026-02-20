#!/usr/bin/env python3
"""
Generate PDFs from CSV rows
Each row becomes a separate PDF with format: COLUMN HEADER: <ROW DATA>
"""

import pandas as pd
import argparse
from pathlib import Path
from fpdf import FPDF
import requests
from io import StringIO
import os

class PDFGenerator(FPDF):
    def __init__(self):
        super().__init__()
        self.set_auto_page_break(auto=True, margin=15)
    
    def header(self):
        self.set_font('Arial', 'B', 12)
        self.cell(0, 10, 'Row Data Export', 0, 1, 'C')
        self.ln(10)
    
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

def create_pdf_for_row(row_data, headers, output_filename):
    """Create PDF for a single row"""
    pdf = PDFGenerator()
    pdf.add_page()
    
    # Set font for content
    pdf.set_font('Arial', '', 11)
    
    # Add row number as title
    row_num = row_data.name + 1  # +1 because index starts at 0
    pdf.set_font('Arial', 'B', 14)
    pdf.cell(0, 10, f"Record #{row_num}", 0, 1, 'L')
    pdf.ln(5)
    
    # Add each column as COLUMN HEADER: value
    pdf.set_font('Arial', '', 11)
    
    for header in headers:
        value = row_data[header]
        
        # Handle NaN or empty values
        if pd.isna(value) or value == '':
            value = 'N/A'
        else:
            value = str(value)
        
        # Format the line
        line = f"{header}: {value}"
        
        # Check if line is too long and needs wrapping
        if pdf.get_string_width(line) > 180:  # Page width minus margins
            # Write header part
            pdf.set_font('Arial', 'B', 11)
            pdf.cell(0, 8, f"{header}:", 0, 1, 'L')
            
            # Write value part (wrapped)
            pdf.set_font('Arial', '', 11)
            pdf.multi_cell(0, 8, value)
            pdf.ln(2)
        else:
            # Write full line
            pdf.set_font('Arial', 'B', 11)
            pdf.cell(50, 8, f"{header}:", 0, 0, 'L')
            pdf.set_font('Arial', '', 11)
            pdf.cell(0, 8, value, 0, 1, 'L')
    
    # Save the PDF
    pdf.output(output_filename)
    print(f"  ✓ Generated: {output_filename}")

def main():
    parser = argparse.ArgumentParser(description='Generate PDFs from CSV rows')
    parser.add_argument('--csv-url', required=True, help='URL of the CSV file')
    parser.add_argument('--output-dir', default='pdfs', help='Output directory for PDFs')
    parser.add_argument('--start-row', type=int, default=48, help='Starting row number (1-based)')
    parser.add_argument('--end-row', type=int, default=53, help='Ending row number (1-based)')
    
    args = parser.parse_args()
    
    # Create output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(exist_ok=True)
    
    print(f"📥 Downloading CSV from: {args.csv_url}")
    
    # Download and read CSV
    df = download_csv_from_url(args.csv_url)
    if df is None:
        return
    
    # Adjust for 1-based indexing in arguments
    start_idx = args.start_row - 1
    end_idx = args.end_row
    
    # Validate row range
    if start_idx < 0 or end_idx > len(df):
        print(f"Error: Row range {args.start_row}-{args.end_row} is invalid. CSV has {len(df)} rows (1-{len(df)})")
        return
    
    print(f"\n📄 Generating PDFs for rows {args.start_row} to {args.end_row}")
    print(f"Total rows to process: {end_idx - start_idx}")
    print("-" * 50)
    
    # Get headers
    headers = df.columns.tolist()
    
    # Generate PDFs for each row in range
    generated_files = []
    for idx in range(start_idx, end_idx):
        row_data = df.iloc[idx]
        row_num = idx + 1
        output_filename = output_dir / f"row_{row_num:03d}.pdf"
        
        create_pdf_for_row(row_data, headers, output_filename)
        generated_files.append(output_filename)
    
    print("-" * 50)
    print(f"\n✅ Successfully generated {len(generated_files)} PDFs in '{args.output_dir}/'")
    
    # Create a summary file
    summary_file = output_dir / "summary.txt"
    with open(summary_file, 'w') as f:
        f.write(f"PDF Generation Summary\n")
        f.write(f"{'='*40}\n")
        f.write(f"CSV Source: {args.csv_url}\n")
        f.write(f"Rows processed: {args.start_row} to {args.end_row}\n")
        f.write(f"Total PDFs: {len(generated_files)}\n")
        f.write(f"\nGenerated files:\n")
        for pdf in generated_files:
            f.write(f"  - {pdf.name}\n")
    
    print(f"📋 Summary saved to: {summary_file}")

if __name__ == "__main__":
    main()
