# -*- coding: utf-8 -*-
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
# CONFIGURATION
# ===========================
CONFIG = {
    'MAX_CATEGORY_SEEDS': 10,           # Apps to grab per category to use as seeds for Phase 2
    'MAX_APPS_TO_VISIT': 1500,          # Prevent endless crawling loops
    'TARGET_VALID_APPS': 200,           # Target valid apps to collect
    'OUTPUT_CSV': 'google_play_apps.csv',
    'ONLY_RECENT_APPS': True,
    'INSTALL_THRESHOLD': 5000,          # Filter to only low installation apps
    'MAX_SIMILAR_APPS_PER_PAGE': 10,
    'DELAY_BETWEEN_REQUESTS': 1
}

CATEGORIES = {
    "Art & Design": "ART_AND_DESIGN",
    "Auto & Vehicles": "AUTO_AND_VEHICLES",
    "Beauty": "BEAUTY",
    "Books & Reference": "BOOKS_AND_REFERENCE",
    "Business": "BUSINESS",
    "Comics": "COMICS",
    "Communication": "COMMUNICATION",
    "Dating": "DATING",
    "Education": "EDUCATION",
    "Entertainment": "ENTERTAINMENT",
    "Events": "EVENTS",
    "Finance": "FINANCE",
    "Food & Drink": "FOOD_AND_DRINK",
    "Health & Fitness": "HEALTH_AND_FITNESS",
    "House & Home": "HOUSE_AND_HOME",
    "Libraries & Demo": "LIBRARIES_AND_DEMO",
    "Lifestyle": "LIFESTYLE",
    "Maps & Navigation": "MAPS_AND_NAVIGATION",
    "Medical": "MEDICAL",
    "Music & Audio": "MUSIC_AND_AUDIO",
    "News & Magazines": "NEWS_AND_MAGAZINES",
    "Parenting": "PARENTING",
    "Personalization": "PERSONALIZATION",
    "Photography": "PHOTOGRAPHY",
    "Productivity": "PRODUCTIVITY",
    "Shopping": "SHOPPING",
    "Social": "SOCIAL",
    "Sports": "SPORTS",
    "Tools": "TOOLS",
    "Travel & Local": "TRAVEL_AND_LOCAL",
    "Video Players & Editors": "VIDEO_PLAYERS",
    "Weather": "WEATHER",
    "Games": "GAME",
}

class GooglePlayScraper:
    def __init__(self):
        self.driver = None
        self.scraped_apps = {}  # Store extracted data using app_id as key
        self.visited_app_ids = set()
        self.category_seeds = set()
        
    def initialize_driver(self):
        chrome_options = Options()
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--window-size=1920,1080")
        
        self.driver = webdriver.Chrome(options=chrome_options)
        print("WebDriver initialized.")
        
    def extract_app_id_from_url(self, url):
        match = re.search(r'id=([a-zA-Z0-9._]+)', url)
        return match.group(1) if match else None

    def extract_release_date(self, page_source):
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
    
    def parse_install_count(self, install_str):
        if install_str == "N/A":
            return 0
        install_str = install_str.replace('+', '').strip().upper()
        try:
            if 'M' in install_str:
                return float(install_str.replace('M', '')) * 1_000_000
            elif 'K' in install_str:
                return float(install_str.replace('K', '')) * 1_000
            else:
                return float(install_str)
        except:
            return 0

    def scrape_categories_for_seeds(self):
        print("\n" + "="*40)
        print("PHASE 1: Scraping Categories for Seeds")
        print("="*40)
        print("Extracting a few initial apps from all categories to use as starting points.")
        
        for category_name, category_id in CATEGORIES.items():
            print(f"Fetching seeds from: {category_name}...", end=" ")
            category_url = f'https://play.google.com/store/apps/category/{category_id}'
            
            try:
                self.driver.get(category_url)
                time.sleep(2)
                
                # A couple of quick scrolls
                for _ in range(2):
                    self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    time.sleep(1)
                
                soup = BeautifulSoup(self.driver.page_source, 'html.parser')
                app_links = set()
                
                for link in soup.find_all('a', href=True):
                    href = link['href']
                    if '/store/apps/details?id=' in href:
                        full_url = 'https://play.google.com' + href if href.startswith('/') else href
                        if '&' in full_url: full_url = full_url.split('&')[0]
                        app_links.add(full_url)
                        if len(app_links) >= CONFIG['MAX_CATEGORY_SEEDS']:
                            break
                            
                for url in app_links:
                    self.category_seeds.add(url)
                print(f"Found {len(app_links)} app(s).")
                
            except Exception as e:
                print(f"Error: {e}")
                
            time.sleep(CONFIG['DELAY_BETWEEN_REQUESTS'])
            
        print(f"\nPhase 1 Complete. Collected {len(self.category_seeds)} total category seeds.")

    def parse_and_validate_app_details(self, soup, page_source, app_url):
        try:
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

            install_count = "N/A"
            stats_values = soup.find_all('div', {'class': 'ClM7O'})
            for val in stats_values:
                text = val.text.strip()
                if '+' in text:
                    install_count = text
                    break
            if install_count == "N/A":
                install_count = self.extract_install_count(page_source)

            developer_tag = soup.find('div', {'class': 'Vbfug auoIOc'})
            if not developer_tag:
                developer_tag = soup.find('a', {'class': 'Si6A0c Gwdmqd'})
            developer = developer_tag.text.strip() if developer_tag else "N/A"
            
            logo_tag = soup.find('img', {'class': 'T75of arM4bb', 'itemprop': 'image'})
            if not logo_tag:
                logo_tag = soup.find('img', {'itemprop': 'image'})
            logo_url = logo_tag['src'] if logo_tag and 'src' in logo_tag.attrs else "N/A"
            
            rating_tag = soup.find('div', {'class': 'jILTFe'})
            rating = rating_tag.text.strip() if rating_tag else "N/A"
            
            review_count_tag = soup.find('div', {'class': 'g1rdde'})
            review_count = review_count_tag.text.strip() if review_count_tag else "N/A"
            if rating == "N/A" or "Download" in review_count or "Install" in review_count:
                review_count = "N/A"
            
            release_date = self.extract_release_date(page_source)
            
            category_name = "N/A"
            category_tags = soup.find_all('a', {'itemprop': 'genre'})
            if not category_tags:
                category_tags = soup.find_all('a', href=re.compile(r'/store/apps/category/'))
            if category_tags:
                category_name = category_tags[0].text.strip()

            install_count_numeric = self.parse_install_count(install_count)
            if install_count_numeric > CONFIG['INSTALL_THRESHOLD']:
                print(f"    [Skipping] Install count '{install_count}' is above {CONFIG['INSTALL_THRESHOLD']} threshold.")
                return None

            if CONFIG['ONLY_RECENT_APPS']:
                try:
                    parsed_date = datetime.strptime(release_date, "%b %d, %Y")
                    now = datetime.now()
                    months_diff = (now.year - parsed_date.year) * 12 + (now.month - parsed_date.month)
                    if not (0 <= months_diff <= 3):
                        print(f"    [Skipping] Release date '{release_date}' is outside 3 month window.")
                        return None
                except Exception as e:
                    print(f"    [Skipping] Could not verify release date: {release_date}")
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
            print(f"    [Error] Failed parsing details: {e}")
            return None

    def crawl_similar_apps(self):
        print("\n" + "="*40)
        print("PHASE 2: Crawling Similar Apps for Valid Results")
        print("="*40)
        
        apps_to_visit = deque(list(self.category_seeds))
        visited_urls_count = 0
        
        while apps_to_visit and visited_urls_count < CONFIG['MAX_APPS_TO_VISIT']:
            if len(self.scraped_apps) >= CONFIG['TARGET_VALID_APPS']:
                print(f"\nTarget of {CONFIG['TARGET_VALID_APPS']} valid apps reached!")
                break
                
            current_url = apps_to_visit.popleft()
            app_id = self.extract_app_id_from_url(current_url)
            
            if not app_id or app_id in self.visited_app_ids:
                continue
                
            self.visited_app_ids.add(app_id)
            visited_urls_count += 1
            
            print(f"\nVisiting [{visited_urls_count}/{CONFIG['MAX_APPS_TO_VISIT']}] | Valid: {len(self.scraped_apps)}/{CONFIG['TARGET_VALID_APPS']} | Queue: {len(apps_to_visit)}")
            print(f"  -> {app_id}")
            
            try:
                self.driver.get(current_url)
                
                # Wait for title to ensure page loaded
                try:
                    WebDriverWait(self.driver, 4).until(
                        EC.presence_of_element_located((By.TAG_NAME, "h1"))
                    )
                except:
                    pass
                
                # Scroll a bit to render Similar apps section
                time.sleep(0.5)
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight/3);")
                time.sleep(0.5)
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight*2/3);")
                time.sleep(1.0)
                
                page_source = self.driver.page_source
                soup = BeautifulSoup(page_source, 'html.parser')
                
                # Extract related apps directly from the same DOM to add to queue
                similar_links = []
                for link in soup.find_all('a', href=True):
                    href = link['href']
                    if '/store/apps/details?id=' in href and app_id not in href:
                        full_url = 'https://play.google.com' + href if href.startswith('/') else href
                        if '&' in full_url: full_url = full_url.split('&')[0]
                        
                        s_id = self.extract_app_id_from_url(full_url)
                        if s_id and s_id not in self.visited_app_ids and full_url not in similar_links:
                            similar_links.append(full_url)
                            if len(similar_links) >= CONFIG['MAX_SIMILAR_APPS_PER_PAGE']:
                                break
                                
                if similar_links:
                    apps_to_visit.extend(similar_links)
                    print(f"    [+] Queued {len(similar_links)} similar apps.")
                
                # Process the currently visited app to see if it matches our desired criteria
                app_data = self.parse_and_validate_app_details(soup, page_source, current_url)
                if app_data:
                    self.scraped_apps[app_id] = app_data
                    print(f"    ✓ [VALID ADDED] {app_data['App Name']} (Installs: {app_data['Install Count']}, Released: {app_data['Release Date']})")
                    
            except Exception as e:
                print(f"    ✗ Error fetching {app_id}: {e}")
                
            time.sleep(CONFIG['DELAY_BETWEEN_REQUESTS'])

    def save_to_csv(self):
        if not self.scraped_apps:
            print("\nNo valid apps found to save.")
            return
            
        csv_path = os.path.join(os.path.dirname(__file__), CONFIG['OUTPUT_CSV'])
        headers = [
            'Niche', 'App Name', 'Logo URL', 'Install Count', 
            'Release Date', 'Rating', 'Review Count', 'App Link', 'Developer'
        ]
        
        apps_list = list(self.scraped_apps.values())
        
        try:
            with open(csv_path, 'w', newline='', encoding='utf-8-sig') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=headers)
                writer.writeheader()
                for app in apps_list:
                    writer.writerow(app)
            print(f"\n✓ Saved {len(apps_list)} unique matching apps to {csv_path}")
        except Exception as e:
            print(f"\n✗ Error saving to CSV: {e}")

    def run(self):
        self.initialize_driver()
        try:
            self.scrape_categories_for_seeds()
            self.crawl_similar_apps()
            self.save_to_csv()
        except KeyboardInterrupt:
            print("\nScraping interrupted by user!")
            self.save_to_csv()
        finally:
            if self.driver:
                self.driver.quit()

if __name__ == "__main__":
    scraper = GooglePlayScraper()
    scraper.run()
