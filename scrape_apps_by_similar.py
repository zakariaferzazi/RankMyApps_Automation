# -*- coding: utf-8 -*-
"""
Google Play Store App Scraper (Similar Apps Method)
===================================================
1. PHASE 1: Crawl & collect app URLs starting from a SEED URL using "Similar Apps" links.
2. PHASE 2: Extract detailed data for each collected app.
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
import time
import csv
import os
import re
from datetime import datetime
from collections import deque

# ===========================
# CONFIGURATION - EDIT HERE
# ===========================
CONFIG = {
    # How many apps to extract data for (Fast process = smaller number, Long process = larger number)
    'MAX_APPS_TO_SCRAPE': 3000, 
    
    # The starting app URL to find similar apps from
    'SEED_APP_URL': 'https://play.google.com/store/apps/details?id=com.enlivion.scaleforgrams',
    
    # Output file name
    'OUTPUT_CSV': 'google_play_apps.csv',
    
    # Filter apps by release date? (Only keep apps released in last 3 months)
    'ONLY_RECENT_APPS': True,
    
    # Crawling settings
    'CRAWL_DEPTH': 10,
    'MAX_SIMILAR_APPS_PER_PAGE': 20,
    'DELAY_BETWEEN_REQUESTS': 1
}

# ===========================
# MAIN SCRAPER CLASS
# ===========================
class SimilarAppsScraper:
    def __init__(self):
        self.driver = None
        self.visited_apps = set()
        self.apps_to_visit = deque()
        self.apps_saved_count = 0
        
    def initialize_driver(self):
        """Initialize Chrome WebDriver in Headless Mode"""
        chrome_options = Options()
        # Headless mode allows it to run in the background or on GitHub Actions
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--window-size=1920,1080")
        
        self.driver = webdriver.Chrome(options=chrome_options)
        print("WebDriver initialized.")
    
    def extract_app_id_from_url(self, url):
        """Extract app package ID from Play Store URL"""
        match = re.search(r'id=([a-zA-Z0-9._]+)', url)
        return match.group(1) if match else None
    
    def get_similar_apps(self, app_url):
        """Get similar apps from an app page (Phase 1)"""
        similar_apps = []
        try:
            self.driver.get(app_url)
            time.sleep(0.5) 
            
            # Wait for basic body presence
            try:
                WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )
            except:
                pass
            
            # Scroll to load similar apps 
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight/2);")
            time.sleep(0.5)
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(0.5)
            
            # Get all links matching an app detail URL
            all_links = self.driver.find_elements(By.XPATH, "//a[contains(@href, '/store/apps/details?id=')]")
            
            for link in all_links[:CONFIG['MAX_SIMILAR_APPS_PER_PAGE']]:
                try:
                    href = link.get_attribute('href')
                    if href and '/store/apps/details?id=' in href:
                        # Clean URL
                        if '&' in href:
                            href = href.split('&')[0]
                        full_url = href if href.startswith('http') else 'https://play.google.com' + href
                        
                        app_id = self.extract_app_id_from_url(full_url)
                        if app_id and app_id not in self.visited_apps:
                            similar_apps.append(full_url)
                except:
                    pass
                    
        except Exception as e:
            print(f"Error collecting similar apps: {e}")
            
        return list(set(similar_apps))
    
    # ---------------------------------------------------------
    # DATA EXTRACTION METHODS (From scrape_categories_to_csv)
    # ---------------------------------------------------------
    def extract_release_date(self, page_source, app_url):
        target_string = 'dappgame_ratings"]]],["'
        start_index = page_source.find(target_string)
        
        if start_index != -1:
            start_index += len(target_string)
            extracted_value = page_source[start_index:start_index + 12]
            release_date = extracted_value.replace('"', '').strip()
            return release_date
        return "N/A"

    def extract_install_count(self, page_source):
        target_string = '<div class="w7Iutd"><div class="wVqUob"><div class="ClM7O">'
        start_index = page_source.find(target_string)
        
        if start_index != -1:
            start_index += len(target_string)
            install_text = page_source[start_index:start_index + 20]
            end_index = install_text.find('<')
            if end_index != -1:
                install_text = install_text[:end_index]
            return install_text.strip()
        return "N/A"

    def parse_install_count(self, install_count_str):
        """Convert install count string (e.g., '5K+', '1.2M+') to numeric value"""
        if install_count_str == "N/A":
            return 0
        
        install_count_str = install_count_str.replace('+', '').strip()
        
        try:
            if 'M' in install_count_str.upper():
                return int(float(install_count_str.upper().replace('M', '')) * 1_000_000)
            elif 'K' in install_count_str.upper():
                return int(float(install_count_str.upper().replace('K', '')) * 1_000)
            else:
                return int(float(install_count_str))
        except:
            return 0

    def extract_app_details(self, app_url):
        """Extract detailed information from the app page (Phase 2)"""
        try:
            self.driver.get(app_url)
            
            try:
                WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located((By.TAG_NAME, "h1"))
                )
            except:
                pass
            
            time.sleep(1) # Buffer to render JS elements
            
            page_source = self.driver.page_source
            soup = BeautifulSoup(page_source, 'html.parser')
            
            # --- Extract App Name ---
            app_name = "N/A"
            app_name_tag = soup.find('h1', {'itemprop': 'name'})
            if app_name_tag:
                app_name = app_name_tag.text.strip()
            if app_name == "N/A":
                app_name_tag = soup.find('h1', {'class': 'Fd93Bb'})
                if app_name_tag:
                     app_name = app_name_tag.text.strip()
            if app_name == "N/A":
                title_tag = soup.find('title')
                if title_tag:
                    title_text = title_tag.text.strip()
                    app_name = title_text.replace(" - Apps on Google Play", "") if " - Apps on Google Play" in title_text else title_text

            # --- Extract Install Count ---
            install_count = "N/A"
            stats_values = soup.find_all('div', {'class': 'ClM7O'})
            for val in stats_values:
                text = val.text.strip()
                if '+' in text:
                    install_count = text
                    break
            if install_count == "N/A":
                install_count = self.extract_install_count(page_source)

            # --- Extract Developer name ---
            developer_tag = soup.find('div', {'class': 'Vbfug auoIOc'})
            if not developer_tag:
                developer_tag = soup.find('a', {'class': 'Si6A0c Gwdmqd'})
            developer = developer_tag.text.strip() if developer_tag else "N/A"
            
            # --- Extract Logo URL ---
            logo_tag = soup.find('img', {'class': 'T75of arM4bb', 'itemprop': 'image'})
            if not logo_tag:
                logo_tag = soup.find('img', {'itemprop': 'image'})
            logo_url = logo_tag['src'] if logo_tag and 'src' in logo_tag.attrs else "N/A"
            
            # --- Extract Rating ---
            rating_tag = soup.find('div', {'class': 'jILTFe'})
            rating = rating_tag.text.strip() if rating_tag else "N/A"
            
            # --- Extract Review Count ---
            review_count_tag = soup.find('div', {'class': 'g1rdde'})
            review_count = review_count_tag.text.strip() if review_count_tag else "N/A"
            if rating == "N/A" or "Download" in review_count or "Install" in review_count:
                review_count = "N/A"
            
            # --- Extract Release Date ---
            release_date = self.extract_release_date(page_source, app_url)
            
            # --- Extract Category (Niche) ---
            category_name = "N/A"
            category_tags = soup.find_all('a', {'itemprop': 'genre'})
            if not category_tags:
                # Fallback to general category buttons
                category_tags = soup.find_all('a', href=re.compile(r'/store/apps/category/'))
            if category_tags:
                category_name = category_tags[0].text.strip()

            # --- Date Filter Logic ---
            if CONFIG['ONLY_RECENT_APPS']:
                try:
                    parsed_date = datetime.strptime(release_date, "%b %d, %Y")
                    now = datetime.now()
                    months_diff = (now.year - parsed_date.year) * 12 + (now.month - parsed_date.month)
                    if not (0 <= months_diff < 3):
                        print(f"    [Skipping] Release date '{release_date}' is outside 3 month window.")
                        return None
                except Exception as e:
                    print(f"    [Skipping] Could not verify release date: {release_date}")
                    return None

            # --- Install Count Filter (5k+ minimum) ---
            numeric_installs = self.parse_install_count(install_count)
            if numeric_installs < 5000:
                print(f"    [Skipping] Install count {install_count} is below 5k threshold.")
                return None

            return {
                'Niche': category_name,
                'App Name': app_name,
                'Logo URL': logo_url,
                'Install Count': install_count,
                'Release Date': release_date,
                'Rating': rating,
                'Review Count': review_count,
                'App Link': app_url,
                'Developer': developer
            }
            
        except Exception as e:
            print(f"Error extracting details for {app_url}: {e}")
            return None

    def save_to_csv(self, app_data):
        """Save app data to CSV file"""
        if not app_data:
            return
            
        csv_path = os.path.join(os.path.dirname(__file__), CONFIG['OUTPUT_CSV'])
        headers = [
            'Niche', 'App Name', 'Logo URL', 'Install Count', 
            'Release Date', 'Rating', 'Review Count', 'App Link', 'Developer'
        ]
        
        file_exists = os.path.exists(csv_path)
        
        try:
            with open(csv_path, 'a', newline='', encoding='utf-8-sig') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=headers)
                if not file_exists:
                    writer.writeheader()
                writer.writerow(app_data)
            
            self.apps_saved_count += 1
            print(f"    ✓ SAVED: {app_data['App Name']} ({app_data['Install Count']} installs)")
            
        except Exception as e:
            print(f"    ✗ Error saving to CSV: {e}")

    def run(self):
        """Run the two-phase scraper"""
        print("="*60)
        print("Google Play Store App Data Scraper (Similar Apps Method)")
        print(f"Max apps target: {CONFIG['MAX_APPS_TO_SCRAPE']}")
        print("="*60)
        
        self.initialize_driver()
        self.apps_to_visit.append((CONFIG['SEED_APP_URL'], 0))
        collected_app_urls = set()
        
        # Note: CSV will be appended to (not removed)
        # If this is the first script to run, it should be empty
        # If the category scraper ran first, we'll append to its data
        csv_path = os.path.join(os.path.dirname(__file__), CONFIG['OUTPUT_CSV'])
        print(f"Will append data to: {csv_path}")
            
        try:
            # ==================================
            # PHASE 1: COLLECT URLs
            # ==================================
            print("\n" + "-"*40)
            print("PHASE 1: Collecting App URLs")
            print("-"*40)
            
            while self.apps_to_visit and len(collected_app_urls) < CONFIG['MAX_APPS_TO_SCRAPE']:
                current_url, depth = self.apps_to_visit.popleft()
                app_id = self.extract_app_id_from_url(current_url)
                
                if not app_id or app_id in self.visited_apps:
                    continue
                    
                self.visited_apps.add(app_id)
                collected_app_urls.add(current_url)
                
                print(f"Found [{len(collected_app_urls)}/{CONFIG['MAX_APPS_TO_SCRAPE']}]: {app_id}")
                
                if depth < CONFIG['CRAWL_DEPTH'] and len(collected_app_urls) < CONFIG['MAX_APPS_TO_SCRAPE']:
                    similar = self.get_similar_apps(current_url)
                    for url in similar:
                        if self.extract_app_id_from_url(url) not in self.visited_apps:
                            self.apps_to_visit.append((url, depth + 1))
                            
                time.sleep(0.2)
            
            # ==================================
            # PHASE 2: EXTRACT DATA
            # ==================================
            print("\n" + "-"*40)
            print("PHASE 2: Extracting App Data")
            print("-"*40)
            
            for index, url in enumerate(list(collected_app_urls)[:CONFIG['MAX_APPS_TO_SCRAPE']], 1):
                app_id = self.extract_app_id_from_url(url)
                print(f"\nProcessing {index}/{len(collected_app_urls)}: {app_id}")
                
                app_data = self.extract_app_details(url)
                if app_data:
                    self.save_to_csv(app_data)
                    
                time.sleep(CONFIG['DELAY_BETWEEN_REQUESTS'])
                
            print("\n" + "="*60)
            print("SCRAPING COMPLETE!")
            print(f"Total apps successfully saved: {self.apps_saved_count}")
            print(f"Data saved to: {csv_path}")
            print("="*60)

        except KeyboardInterrupt:
            print("\nScraping interrupted by user!")
        except Exception as e:
            print(f"\nCritical Error: {e}")
        finally:
            if self.driver:
                self.driver.quit()
                print("WebDriver closed.")

if __name__ == "__main__":
    scraper = SimilarAppsScraper()
    scraper.run()
