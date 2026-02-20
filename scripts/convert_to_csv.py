#!/usr/bin/env python3
"""
Convert HAR/JSON files to CSV
Supports: .har, .json, .txt files
Specifically extracts elector data from HAR file responses
"""

import json
import csv
import os
import argparse
from pathlib import Path
from typing import Dict, List, Any

class HARtoCSVConverter:
    def __init__(self, input_path: str, output_path: str = "CSV"):
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
    
    def extract_elector_data(self, json_data: Dict) -> List[Dict]:
        """Extract elector data from the specific JSON structure"""
        entries = []
        
        try:
            # Check if this is the elector data response structure
            if isinstance(json_data, dict):
                # If it has payload with electorDetailDto
                if 'payload' in json_data and 'electorDetailDto' in json_data['payload']:
                    electors = json_data['payload']['electorDetailDto']
                    for elector in electors:
                        if isinstance(elector, dict):
                            # Flatten the elector dictionary
                            flat_elector = self.flatten_dict(elector)
                            entries.append(flat_elector)
                
                # If it's directly an array of electors
                elif 'electorDetailDto' in json_data:
                    electors = json_data['electorDetailDto']
                    for elector in electors:
                        if isinstance(elector, dict):
                            flat_elector = self.flatten_dict(elector)
                            entries.append(flat_elector)
                
                # If it's a list of entries from HAR
                elif 'log' in json_data and 'entries' in json_data['log']:
                    for entry in json_data['log']['entries']:
                        # Check response content
                        response = entry.get('response', {})
                        content = response.get('content', {})
                        text = content.get('text', '')
                        
                        if text:
                            try:
                                # Parse the response text as JSON
                                response_data = json.loads(text)
                                # Extract elector data from this response
                                elector_entries = self.extract_elector_data(response_data)
                                entries.extend(elector_entries)
                            except:
                                # Not JSON or invalid, skip
                                pass
        except Exception as e:
            print(f"Error extracting elector data: {e}")
        
        return entries
    
    def extract_generic_data(self, json_data: Any) -> List[Dict]:
        """Extract data from generic JSON file"""
        entries = []
        
        try:
            if isinstance(json_data, list):
                for item in json_data:
                    if isinstance(item, dict):
                        entries.append(self.flatten_dict(item))
                    else:
                        entries.append({'value': item})
            elif isinstance(json_data, dict):
                entries.append(self.flatten_dict(json_data))
        except Exception as e:
            print(f"Error extracting generic data: {e}")
        
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
            print(f"  Fields: {len(fieldnames)} columns")
            
        except Exception as e:
            print(f"Error saving CSV for {output_filename}: {e}")
    
    def convert_file(self, file_path: Path, custom_filename: str = None):
        """Convert a single file to CSV"""
        print(f"\nProcessing: {file_path}")
        
        # Load the file
        data = self.load_json_file(file_path)
        if not data:
            return
        
        # Extract data - try elector data first, then fall back to generic
        entries = self.extract_elector_data(data)
        
        if not entries:
            # If no elector data found, try generic extraction
            print("  No elector data found, trying generic extraction...")
            if file_path.suffix.lower() == '.har':
                # For HAR files, try to extract from entries
                for entry in data.get('log', {}).get('entries', []):
                    response = entry.get('response', {})
                    content = response.get('content', {})
                    text = content.get('text', '')
                    if text:
                        try:
                            response_data = json.loads(text)
                            elector_entries = self.extract_elector_data(response_data)
                            if elector_entries:
                                entries.extend(elector_entries)
                        except:
                            pass
            
            if not entries:
                # Last resort: generic extraction
                if file_path.suffix.lower() == '.har':
                    entries = self.extract_generic_data(data)
                else:
                    entries = self.extract_generic_data(data)
        
        # Save to CSV
        if entries:
            if custom_filename:
                output_name = custom_filename
            else:
                output_name = file_path.stem
            self.save_to_csv(entries, output_name)
            
            # Print sample of first row
            if entries:
                print(f"\n  Sample data (first row keys):")
                sample_keys = list(entries[0].keys())[:10]  # Show first 10 keys
                print(f"  {', '.join(sample_keys)}...")
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
    parser.add_argument('--output', '-o', default='CSV', help='Output directory path')
    parser.add_argument('--filename', '-f', help='Output filename (without extension)')
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
            if args.filename:
                # Convert and save with specific filename
                data = converter.load_json_file(Path(temp_file))
                entries = converter.extract_elector_data(data)
                if not entries:
                    # Try HAR structure
                    if Path(temp_file).suffix.lower() == '.har':
                        for entry in data.get('log', {}).get('entries', []):
                            response = entry.get('response', {})
                            content = response.get('content', {})
                            text = content.get('text', '')
                            if text:
                                try:
                                    response_data = json.loads(text)
                                    elector_entries = converter.extract_elector_data(response_data)
                                    if elector_entries:
                                        entries.extend(elector_entries)
                                except:
                                    pass
                converter.save_to_csv(entries, args.filename)
            else:
                converter.convert_all()
    else:
        # Use local file/directory
        if not args.input:
            print("Please provide input file/directory or Google Drive ID")
            return
        
        converter = HARtoCSVConverter(args.input, args.output)
        if args.filename and Path(args.input).is_file():
            # Single file with custom name
            data = converter.load_json_file(Path(args.input))
            entries = converter.extract_elector_data(data)
            if not entries and Path(args.input).suffix.lower() == '.har':
                # Try HAR structure
                for entry in data.get('log', {}).get('entries', []):
                    response = entry.get('response', {})
                    content = response.get('content', {})
                    text = content.get('text', '')
                    if text:
                        try:
                            response_data = json.loads(text)
                            elector_entries = converter.extract_elector_data(response_data)
                            if elector_entries:
                                entries.extend(elector_entries)
                        except:
                            pass
            converter.save_to_csv(entries, args.filename)
        else:
            converter.convert_all()
    
    print("\n✅ Conversion complete!")

if __name__ == "__main__":
    main()
