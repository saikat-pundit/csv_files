#!/usr/bin/env python3
"""
Generate PDFs from specific columns (AW to BB) of CSV rows
Each row becomes a separate PDF with format: COLUMN HEADER: <ROW DATA>
Filename is taken from column AZ (index 51) - header/title is removed (kept blank)
"""

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
    """Remove invalid characters from filename for all operating systems"""
    if pd.isna(filename) or filename == '':
        return "unnamed"
    
    # Convert to string and strip
    filename = str(filename).strip()
    
    # Replace invalid characters with underscore
    # Invalid chars: < > : " / \ | ? * and control characters
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    
    # Remove or replace other problematic characters
    filename = filename.replace(';', '_')  # Replace semicolons
    filename = filename.replace(',', '_')  # Replace commas
    filename = filename.replace('\n', '_')  # Replace newlines
    filename = filename.replace('\r', '_')  # Replace carriage returns
    filename = filename.replace('\t', '_')  # Replace tabs
    
    # Remove leading/trailing spaces and dots
    filename = filename.strip('. ')
    
    # Normalize unicode characters
    filename = unicodedata.normalize('NFKD', filename).encode('ASCII', 'ignore').decode('ASCII')
    
    # Replace multiple underscores with single underscore
    filename = re.sub(r'_+', '_', filename)
    
    # Limit length to 50 characters (leaving room for extension)
    if len(filename) > 45:
        filename = filename[:45]
    
    # Ensure filename is not empty after sanitization
    if not filename or filename.isspace():
        filename = "unnamed"
    
    return filename

def create_pdf_for_row(row_data, selected_columns, output_filename):
    """Create PDF for a single row with only selected columns - NO HEADER/TITLE"""
    pdf = PDFGenerator()
    pdf.add_page()
    
    # Set margins
    pdf.set_left_margin(15)
    pdf.set_right_margin(15)
    
    # NO TITLE/HEADER - removed completely
    # Start directly with column data
    
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
            
            # Clean value for display (remove excessive whitespace)
            clean_value = ' '.join(value.split())
            
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
            if pdf.get_string_width(clean_value) > remaining_width:
                # Move to next line for value
                pdf.ln(6)
                pdf.set_x(15 + col_name_width + 2)
                
                # Write multi-line text
                pdf.multi_cell(remaining_width, 6, clean_value, 0, 'L')
            else:
                pdf.cell(0, 6, clean_value, 0, 1, 'L')
            
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
    
    # Get AZ column (index 51 in 1-based, 50 in 0-based) for FILENAME ONLY
    all_columns = df.columns.tolist()
    if len(all_columns) >= 52:  # Need at least 52 columns for AZ (51 in 1-based)
        filename_column = all_columns[51]  # AZ column (0-based index 50)
        print(f"📝 Using AZ column '{filename_column}' for filename ONLY (no header/title)")
    else:
        filename_column = None
        print(f"⚠️  CSV has only {len(all_columns)} columns, AZ column (51) not found. Using row number.")
    
    # Generate PDFs for each row in range
    generated_files = []
    failed_files = []
    
    for idx in range(start_idx, end_idx):
        row_data = df.iloc[idx]
        row_num = idx + 1
        
        # Get filename from AZ column (column 51) - NOT used as header/title
        if filename_column and filename_column in row_data.index:
            filename_value = row_data[filename_column]
            if pd.isna(filename_value) or filename_value == '':
                base_name = f"record_{row_num:03d}"
            else:
                base_name = sanitize_filename(filename_value)
        else:
            base_name = f"record_{row_num:03d}"
        
        # Ensure unique filename by adding row number if needed
        output_filename = output_dir / f"{base_name}.pdf"
        
        # If file exists, add row number to make it unique
        if output_filename.exists():
            output_filename = output_dir / f"{base_name}_{row_num:03d}.pdf"
        
        try:
            # Pass only row_data, selected_columns, and output_filename - NO title parameter
            create_pdf_for_row(row_data, selected_columns, output_filename)
            generated_files.append(output_filename)
        except Exception as e:
            print(f"  ❌ Failed to generate PDF for row {row_num}: {e}")
            failed_files.append(row_num)
    
    print("-" * 50)
    print(f"\n✅ Successfully generated {len(generated_files)} PDFs in '{args.output_dir}/'")
    
    if failed_files:
        print(f"❌ Failed to generate PDFs for rows: {failed_files}")
    
    # Create a summary file
    summary_file = output_dir / "summary.txt"
    with open(summary_file, 'w') as f:
        f.write(f"PDF Generation Summary (Columns AW to BB)\n")
        f.write(f"{'='*50}\n")
        f.write(f"CSV Source: {args.csv_url}\n")
        f.write(f"Rows processed: {args.start_row} to {end_idx}\n")
        f.write(f"Columns included: {', '.join(selected_columns)}\n")
        if filename_column:
            f.write(f"Filename from AZ column: {filename_column}\n")
        f.write(f"Total PDFs: {len(generated_files)}\n")
        if failed_files:
            f.write(f"Failed rows: {failed_files}\n")
        f.write(f"\nGenerated files:\n")
        for pdf in generated_files:
            f.write(f"  - {pdf.name}\n")
    
    print(f"📋 Summary saved to: {summary_file}")

if __name__ == "__main__":
    main()
