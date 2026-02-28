# -*- coding: utf-8 -*-
"""
CSV Merger Script
================
Downloads existing google_play_apps.csv from WordPress,
merges it with newly scraped data, and removes duplicates by App Link.
"""

import requests
import csv
import os
from datetime import datetime
from pathlib import Path

class CSVMerger:
    def __init__(self, existing_csv_url, local_csv_file='google_play_apps.csv'):
        """
        Initialize the merger
        
        :param existing_csv_url: URL to download existing CSV from
        :param local_csv_file: Local scraped CSV file to merge
        """
        self.existing_csv_url = existing_csv_url
        self.local_csv_file = local_csv_file
        self.merged_file = local_csv_file
        self.existing_data = {}
        self.new_data = {}
        
    def download_existing_csv(self):
        """Download existing CSV from WordPress"""
        print("\n" + "="*70)
        print("STEP 1: Downloading existing CSV from WordPress")
        print("="*70)
        
        try:
            print(f"Downloading from: {self.existing_csv_url}")
            response = requests.get(self.existing_csv_url, timeout=30)
            response.raise_for_status()
            
            # Parse downloaded CSV
            lines = response.text.strip().split('\n')
            if not lines:
                print("✗ Downloaded file is empty")
                return False
                
            reader = csv.DictReader(lines)
            count = 0
            
            for row in reader:
                app_link = row.get('App Link', '').strip()
                if app_link:
                    self.existing_data[app_link] = row
                    count += 1
            
            print(f"✓ Downloaded {count} apps from existing file")
            return True
            
        except requests.exceptions.RequestException as e:
            print(f"✗ Error downloading CSV: {e}")
            print("  Will proceed with new data only...")
            return False
        except Exception as e:
            print(f"✗ Error parsing CSV: {e}")
            return False
    
    def load_new_data(self):
        """Load newly scraped data from local CSV"""
        print("\n" + "="*70)
        print("STEP 2: Loading newly scraped data")
        print("="*70)
        
        if not os.path.exists(self.local_csv_file):
            print(f"✗ Local file not found: {self.local_csv_file}")
            return False
        
        try:
            with open(self.local_csv_file, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                count = 0
                
                for row in reader:
                    app_link = row.get('App Link', '').strip()
                    if app_link:
                        self.new_data[app_link] = row
                        count += 1
            
            print(f"✓ Loaded {count} apps from new data")
            return True
            
        except Exception as e:
            print(f"✗ Error loading new data: {e}")
            return False
    
    def merge_data(self):
        """Merge existing and new data, deduplicating by App Link"""
        print("\n" + "="*70)
        print("STEP 3: Merging data (deduplicating by App Link)")
        print("="*70)
        
        # Start with existing data (as base)
        merged = dict(self.existing_data)
        
        # Add/update with new data
        added = 0
        updated = 0
        
        for link, data in self.new_data.items():
            if link in merged:
                updated += 1
            else:
                added += 1
            merged[link] = data
        
        print(f"✓ Existing items: {len(self.existing_data)}")
        print(f"✓ New items added: {added}")
        print(f"✓ Existing items updated: {updated}")
        print(f"✓ Total after merge: {len(merged)}")
        
        return merged
    
    def save_merged_csv(self, merged_data):
        """Save merged data to CSV"""
        print("\n" + "="*70)
        print("STEP 4: Saving merged data")
        print("="*70)
        
        if not merged_data:
            print("✗ No data to save")
            return False
        
        try:
            # Get headers from first data item
            headers = list(merged_data[list(merged_data.keys())[0]].keys())
            
            # Ensure standard order
            standard_headers = [
                'Niche', 'App Name', 'Logo URL', 'Install Count', 
                'Release Date', 'Rating', 'Review Count', 'App Link', 'Developer'
            ]
            headers = [h for h in standard_headers if h in headers]
            
            with open(self.merged_file, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.DictWriter(f, fieldnames=headers)
                writer.writeheader()
                
                # Sort by app name for consistency
                sorted_data = sorted(merged_data.values(), key=lambda x: x.get('App Name', ''))
                writer.writerows(sorted_data)
            
            print(f"✓ Merged CSV saved: {self.merged_file}")
            print(f"✓ Total records: {len(merged_data)}")
            return True
            
        except Exception as e:
            print(f"✗ Error saving CSV: {e}")
            return False
    
    def run(self):
        """Execute the merge process"""
        print("\n")
        print("╔" + "="*68 + "╗")
        print("║" + " "*15 + "CSV MERGE AND DEDUPLICATION TOOL" + " "*20 + "║")
        print("║" + " "*68 + "║")
        print("║" + f" Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}" + " "*40 + "║")
        print("╚" + "="*68 + "╝")
        
        # Step 1: Download existing
        if not self.download_existing_csv():
            print("\n⚠ Warning: Could not download existing file, will use new data only")
        
        # Step 2: Load new data
        if not self.load_new_data():
            print("\n✗ Fatal error: Could not load new data")
            return False
        
        # Step 3: Merge
        merged_data = self.merge_data()
        
        # Step 4: Save
        if not self.save_merged_csv(merged_data):
            print("\n✗ Fatal error: Could not save merged data")
            return False
        
        print("\n" + "="*70)
        print("✓ MERGE COMPLETE - File ready for FTP upload")
        print("="*70 + "\n")
        
        return True


def main():
    """Main entry point"""
    # Configuration
    EXISTING_CSV_URL = 'http://rankmyapps.com/wp-content/themes/astra-child/google_play_apps.csv'
    LOCAL_CSV_FILE = 'google_play_apps.csv'
    
    merger = CSVMerger(EXISTING_CSV_URL, LOCAL_CSV_FILE)
    success = merger.run()
    
    if success:
        print("Next step: Upload google_play_apps.csv to WordPress via FTP/SFTP")
    
    return 0 if success else 1


if __name__ == '__main__':
    exit(main())
