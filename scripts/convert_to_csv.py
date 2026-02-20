#!/usr/bin/env python3
"""
Convert HAR/JSON files to CSV
Supports: .har, .json, .txt files
"""

import json
import csv
import os
import argparse
from pathlib import Path
import glob
import pandas as pd
from typing import Dict, List, Any

class HARtoCSVConverter:
    def __init__(self, input_path: str, output_path: str = "output"):
        self.input_path = input_path
        self.output_path = output_path
        self.output_dir = Path(output_path)
        self.output_dir.mkdir(exist_ok=True)
    
    def load_json_file(self, file_path: Path) -> Dict:
        """Load and parse JSON file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON from {file_path}: {e}")
            return {}
    
    def extract_har_data(self, har_data: Dict) -> List[Dict]:
        """Extract relevant data from HAR file"""
        entries = []
        
        try:
            if 'log' in har_data and 'entries' in har_data['log']:
                for entry in har_data['log']['entries']:
                    row = {
                        'url': entry.get('request', {}).get('url', ''),
                        'method': entry.get('request', {}).get('method', ''),
                        'status': entry.get('response', {}).get('status', ''),
                        'status_text': entry.get('response', {}).get('statusText', ''),
                        'time': entry.get('time', ''),
                        'started_date_time': entry.get('startedDateTime', ''),
                        'request_headers_size': entry.get('request', {}).get('headersSize', ''),
                        'response_headers_size': entry.get('response', {}).get('headersSize', ''),
                        'response_body_size': entry.get('response', {}).get('bodySize', ''),
                        'content_type': entry.get('response', {}).get('content', {}).get('mimeType', ''),
                        'server_ip': entry.get('serverIPAddress', ''),
                        'connection': entry.get('connection', ''),
                    }
                    entries.append(row)
        except Exception as e:
            print(f"Error extracting HAR data: {e}")
        
        return entries
    
    def extract_json_data(self, json_data: Any) -> List[Dict]:
        """Extract data from generic JSON file"""
        entries = []
        
        try:
            if isinstance(json_data, list):
                # If it's a list, each item becomes a row
                for item in json_data:
                    if isinstance(item, dict):
                        entries.append(item)
                    else:
                        entries.append({'value': item})
            elif isinstance(json_data, dict):
                # If it's a dict, flatten it
                entries.append(self.flatten_dict(json_data))
        except Exception as e:
            print(f"Error extracting JSON data: {e}")
        
        return entries
    
    def flatten_dict(self, d: Dict, parent_key: str = '', sep: str = '_') -> Dict:
        """Flatten nested dictionary"""
        items = []
        for k, v in d.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            if isinstance(v, dict):
                items.extend(self.flatten_dict(v, new_key, sep=sep).items())
            elif isinstance(v, list):
                # Convert lists to string
                items.append((new_key, json.dumps(v)))
            else:
                items.append((new_key, v))
        return dict(items)
    
    def save_to_csv(self, data: List[Dict], output_filename: str):
        """Save data to CSV file"""
        if not data:
            print(f"No data to save for {output_filename}")
            return
        
        output_file = self.output_dir / f"{output_filename}.csv"
        
        try:
            # Get all unique keys
            fieldnames = set()
            for row in data:
                fieldnames.update(row.keys())
            fieldnames = sorted(list(fieldnames))
            
            with open(output_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(data)
            
            print(f"✓ Saved {len(data)} rows to {output_file}")
            
        except Exception as e:
            print(f"Error saving CSV for {output_filename}: {e}")
    
    def convert_file(self, file_path: Path):
        """Convert a single file to CSV"""
        print(f"\nProcessing: {file_path}")
        
        # Load the file
        data = self.load_json_file(file_path)
        if not data:
            return
        
        # Extract data based on file type
        if file_path.suffix.lower() == '.har':
            entries = self.extract_har_data(data)
        else:  # .json, .txt, etc.
            entries = self.extract_json_data(data)
        
        # Save to CSV
        if entries:
            output_name = file_path.stem
            self.save_to_csv(entries, output_name)
        else:
            print(f"  No entries found in {file_path}")
    
    def convert_all(self):
        """Convert all supported files in input path"""
        input_path = Path(self.input_path)
        
        if input_path.is_file():
            # Single file
            self.convert_file(input_path)
        else:
            # Directory - find all supported files
            patterns = ['*.har', '*.json', '*.txt']
            for pattern in patterns:
                for file_path in input_path.glob(pattern):
                    self.convert_file(file_path)

def download_from_gdrive(file_id: str, output_path: str):
    """Download file from Google Drive by file ID"""
    import gdown
    
    url = f"https://drive.google.com/uc?id={file_id}"
    output = output_path
    
    try:
        gdown.download(url, output, quiet=False)
        return True
    except Exception as e:
        print(f"Error downloading from Google Drive: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description='Convert HAR/JSON files to CSV')
    parser.add_argument('--input', '-i', help='Input file or directory path')
    parser.add_argument('--output', '-o', default='output', help='Output directory path')
    parser.add_argument('--gdrive-id', help='Google Drive file ID to download')
    parser.add_argument('--gdrive-url', help='Google Drive sharing URL')
    
    args = parser.parse_args()
    
    # Handle Google Drive download
    if args.gdrive_id or args.gdrive_url:
        import tempfile
        temp_dir = tempfile.mkdtemp()
        
        if args.gdrive_id:
            file_id = args.gdrive_id
        else:
            # Extract file ID from URL
            import re
            match = re.search(r'/d/([a-zA-Z0-9_-]+)', args.gdrive_url)
            if match:
                file_id = match.group(1)
            else:
                print("Could not extract file ID from URL")
                return
        
        temp_file = os.path.join(temp_dir, "downloaded_file")
        print(f"Downloading from Google Drive...")
        
        if download_from_gdrive(file_id, temp_file):
            converter = HARtoCSVConverter(temp_file, args.output)
            converter.convert_all()
    else:
        # Use local file/directory
        if not args.input:
            print("Please provide input file/directory or Google Drive ID")
            return
        
        converter = HARtoCSVConverter(args.input, args.output)
        converter.convert_all()
    
    print("\n✅ Conversion complete!")

if __name__ == "__main__":
    main()
