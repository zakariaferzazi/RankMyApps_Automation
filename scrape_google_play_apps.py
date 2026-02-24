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
    'MAX_APPS_PER_CATEGORY': 3000,
    'MAX_APPS_TO_SCRAPE_SIMILAR': 1000, 
    'SEED_APP_URL': 'https://play.google.com/store/apps/details?id=com.enlivion.scaleforgrams',
    'OUTPUT_CSV': 'google_play_apps.csv',
    'ONLY_RECENT_APPS': True,
    'CRAWL_DEPTH': 10,
    'MAX_SIMILAR_APPS_PER_PAGE': 20,
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

    def extract_app_details(self, app_url, category_fallback="N/A", is_similar_phase=False):
        try:
            self.driver.get(app_url)
            try:
                WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located((By.TAG_NAME, "h1"))
                )
            except:
                pass
            
            time.sleep(1)
            page_source = self.driver.page_source
            soup = BeautifulSoup(page_source, 'html.parser')
            
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
            
            release_date = self.extract_release_date(page_source, app_url)
            
            category_name = "N/A"
            category_tags = soup.find_all('a', {'itemprop': 'genre'})
            if not category_tags:
                category_tags = soup.find_all('a', href=re.compile(r'/store/apps/category/'))
            if category_tags:
                category_name = category_tags[0].text.strip()
            if category_name == "N/A" and category_fallback != "N/A":
                category_name = category_fallback

            if is_similar_phase:
                install_count_numeric = self.parse_install_count(install_count)
                if install_count_numeric < 5000:
                    print(f"    [Skipping] Install count '{install_count}' is below 5K threshold.")
                    return None

            if CONFIG['ONLY_RECENT_APPS'] or not is_similar_phase:
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

    def scrape_categories(self):
        print("\n" + "="*40)
        print("PHASE 1: Scraping by Categories")
        print("="*40)
        
        for category_name, category_id in CATEGORIES.items():
            print(f"\nScraping category: {category_name}")
            category_url = f'https://play.google.com/store/apps/category/{category_id}'
            self.driver.get(category_url)
            time.sleep(3)
            
            scroll_count = 0
            while scroll_count < 10:
                last_height = self.driver.execute_script("return document.body.scrollHeight")
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(1.5)
                new_height = self.driver.execute_script("return document.body.scrollHeight")
                if new_height == last_height:
                    break
                scroll_count += 1
            
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            app_links = set()
            for link in soup.find_all('a', href=True):
                href = link['href']
                if '/store/apps/details?id=' in href:
                    full_url = 'https://play.google.com' + href if href.startswith('/') else href
                    if '&' in full_url: full_url = full_url.split('&')[0]
                    app_links.add(full_url)
                    if len(app_links) >= CONFIG['MAX_APPS_PER_CATEGORY']:
                        break
            
            for idx, app_url in enumerate(list(app_links)[:CONFIG['MAX_APPS_PER_CATEGORY']], 1):
                app_id = self.extract_app_id_from_url(app_url)
                if app_id in self.visited_app_ids:
                    continue
                
                print(f"Processing category app {idx}/{len(app_links)}: {app_url}")
                app_data = self.extract_app_details(app_url, category_fallback=category_name, is_similar_phase=False)
                if app_data:
                    self.scraped_apps[app_id] = app_data
                    print(f"  ✓ Added: {app_data['App Name']}")
                self.visited_app_ids.add(app_id)
                time.sleep(CONFIG['DELAY_BETWEEN_REQUESTS'])

    def get_similar_apps(self, app_url):
        similar_apps = []
        try:
            self.driver.get(app_url)
            time.sleep(0.5)
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight/2);")
            time.sleep(0.5)
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(0.5)
            all_links = self.driver.find_elements(By.XPATH, "//a[contains(@href, '/store/apps/details?id=')]")
            for link in all_links[:CONFIG['MAX_SIMILAR_APPS_PER_PAGE']]:
                try:
                    href = link.get_attribute('href')
                    if href and '/store/apps/details?id=' in href:
                        if '&' in href: href = href.split('&')[0]
                        full_url = href if href.startswith('http') else 'https://play.google.com' + href
                        similar_apps.append(full_url)
                except:
                    pass
        except Exception as e:
            print(f"Error collecting similar apps: {e}")
        return list(set(similar_apps))

    def scrape_similar_apps(self):
        print("\n" + "="*40)
        print("PHASE 2: Scraping Similar Apps")
        print("="*40)
        
        apps_to_visit = deque()
        apps_to_visit.append((CONFIG['SEED_APP_URL'], 0))
        collected_unprocessed_urls = set()
        
        # Step 2A: Crawl for URLs
        print("Crawling for similar app URLs...")
        while apps_to_visit and len(collected_unprocessed_urls) < CONFIG['MAX_APPS_TO_SCRAPE_SIMILAR']:
            current_url, depth = apps_to_visit.popleft()
            app_id = self.extract_app_id_from_url(current_url)
            
            if not app_id or app_id in self.visited_app_ids:
                continue
            
            collected_unprocessed_urls.add(current_url)
            print(f"Found [{len(collected_unprocessed_urls)}/{CONFIG['MAX_APPS_TO_SCRAPE_SIMILAR']}]: {app_id}")
            
            if depth < CONFIG['CRAWL_DEPTH'] and len(collected_unprocessed_urls) < CONFIG['MAX_APPS_TO_SCRAPE_SIMILAR']:
                similar = self.get_similar_apps(current_url)
                for url in similar:
                    s_id = self.extract_app_id_from_url(url)
                    if s_id and s_id not in self.visited_app_ids:
                        apps_to_visit.append((url, depth + 1))
            time.sleep(0.2)
            
        # Step 2B: Extract data for crawled apps
        print("\nExtracting data for similar apps...")
        for index, url in enumerate(list(collected_unprocessed_urls)[:CONFIG['MAX_APPS_TO_SCRAPE_SIMILAR']], 1):
            app_id = self.extract_app_id_from_url(url)
            if not app_id or app_id in self.visited_app_ids:
                continue
                
            print(f"Processing similar app {index}/{len(collected_unprocessed_urls)}: {app_id}")
            app_data = self.extract_app_details(url, is_similar_phase=True)
            if app_data:
                self.scraped_apps[app_id] = app_data
                print(f"  ✓ Added: {app_data['App Name']}")
            self.visited_app_ids.add(app_id)
            time.sleep(CONFIG['DELAY_BETWEEN_REQUESTS'])

    def save_to_csv(self):
        if not self.scraped_apps:
            print("No apps to save.")
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
            print(f"\n✓ Saved {len(apps_list)} unique apps to {csv_path}")
        except Exception as e:
            print(f"\n✗ Error saving to CSV: {e}")

    def run(self):
        self.initialize_driver()
        try:
            self.scrape_categories()
            self.scrape_similar_apps()
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
