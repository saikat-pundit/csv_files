import pandas as pd
import argparse, re
from pathlib import Path
from fpdf import FPDF

def fix_text(text):
    """Robustly fix corrupted text and convert to FPDF-safe ASCII"""
    if pd.isna(text) or text == '': return ""
    text = str(text).strip()
    
    # 1. Fix Mojibake (Double-encoding: CP1252 -> UTF-8)
    try: text = text.encode('cp1252').decode('utf-8')
    except: pass
    
    # 2. Convert standard Unicode punctuation to basic ASCII
    replacements = {"‘":"'", "’":"'", "“":'"', "”":'"', "–":"-", "—":"-", "…":"...", "•":"-", "\u2011":"-"}
    for k, v in replacements.items(): text = text.replace(k, v)
    
    # 3. Strip remaining unsupported characters to prevent FPDF crash
    return text.encode('latin-1', 'ignore').decode('latin-1')

class PDFGen(FPDF):
    def __init__(self):
        super().__init__(orientation='L')
        self.set_auto_page_break(auto=True, margin=15)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--csv-url', required=True)
    parser.add_argument('--output-dir', default='pdfs')
    parser.add_argument('--start-row', type=int, default=1)
    parser.add_argument('--end-row', type=int, default=None)
    args = parser.parse_args()

    out_dir = Path(args.output_dir)
    out_dir.mkdir(exist_ok=True)

    # LET PANDAS HANDLE THE DOWNLOAD - Forces correct UTF-8 encoding natively
    try:
        df = pd.read_csv(args.csv_url, encoding='utf-8')
        print(f"✓ Downloaded CSV with {len(df)} rows")
    except Exception as e:
        return print(f"❌ Failed to download/read CSV: {e}")

    cols = df.columns.tolist()
    sel_cols = cols[48:55] if len(cols) >= 55 else cols[-6:]
    if not sel_cols: return print("No columns selected")

    fname_col = cols[51] if len(cols) >= 52 else None
    end_idx = args.end_row or len(df)

    for idx in range(args.start_row - 1, end_idx):
        row = df.iloc[idx]
        r_num = idx + 1
        
        # Determine Filename
        base_name = "unnamed"
        if fname_col and pd.notna(row.get(fname_col)):
            base_name = re.sub(r'[<>:"/\\|?*;\s,]+', '_', str(row[fname_col]).strip())[:45].strip('_')
        
        out_path = out_dir / f"{base_name or 'unnamed'}.pdf"
        if out_path.exists(): out_path = out_dir / f"{base_name}_{r_num:03d}.pdf"

        try:
            pdf = PDFGen()
            pdf.add_page()
            pdf.set_font('Arial', 'B', 18)
            pdf.cell(0, 15, "HEARING ORDER", 0, 1, 'C')
            pdf.ln(5)

            # Add Row Data
            for col in sel_cols:
                val = fix_text(row.get(col))
                if not val: continue
                
                pdf.set_font('Arial', 'B', 10)
                pdf.set_x(15)
                pdf.cell(65, 6, f"{col}:", 0, 0, 'L')
                
                pdf.set_font('Arial', '', 10)
                val = ' '.join(val.split())
                rem_w = pdf.w - 97 # Page width - margins and label width
                
                if pdf.get_string_width(val) > rem_w:
                    pdf.ln(6)
                    pdf.set_x(82)
                    pdf.multi_cell(rem_w, 6, val, 0, 'L')
                else:
                    pdf.cell(0, 6, val, 0, 1, 'L')
                pdf.ln(2)

            # Add Signature
            pdf.ln(5)
            sig = Path("sign.jpg") if Path("sign.jpg").exists() else Path("sign.jpeg")
            if sig.exists():
                try: pdf.image(str(sig), x=pdf.w - 95, y=pdf.get_y() + 5, w=80, h=40)
                except: pass

            pdf.output(out_path)
            print(f"  ✓ {out_path.name}")
        except Exception as e:
            print(f"  ❌ Row {r_num} failed: {e}")

if __name__ == "__main__":
    main()
