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
from datetime import datetime
from datetime import timedelta

# Set up Chrome WebDriver in headless mode for GitHub Actions
chrome_options = Options()
chrome_options.add_argument("--headless=new")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--window-size=1920,1080")

driver = webdriver.Chrome(options=chrome_options)

# Google Play Store Categories
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

def extract_release_date(page_source, app_url):
    """Extract release date using the existing pattern"""
    target_string = 'dappgame_ratings"]]],["'
    start_index = page_source.find(target_string)
    
    if start_index != -1:
        # Start from the position of the target string and move 12 characters ahead
        start_index += len(target_string)
        extracted_value = page_source[start_index:start_index + 12]
        release_date = extracted_value.replace('"', '').strip()
        print(f"  Release Date extracted: {release_date}")
        return release_date
    else:
        print(f"  Target string not found for: {app_url}")
        return "N/A"

def extract_install_count(page_source):
    """Extract install count using the existing pattern"""
    target_string = '<div class="w7Iutd"><div class="wVqUob"><div class="ClM7O">'
    start_index = page_source.find(target_string)
    
    if start_index != -1:
        start_index += len(target_string)
        # Extract more characters to capture full install count
        install_text = page_source[start_index:start_index + 20]
        # Find the closing tag
        end_index = install_text.find('<')
        if end_index != -1:
            install_text = install_text[:end_index]
        return install_text.strip()
    return "N/A"

def extract_app_details(app_url, category_name):
    """Extract detailed information from app page"""
    try:
        driver.get(app_url)
        
        # Wait for content to load, utilizing WebDriverWait to ensure H1 is present
        try:
            WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.TAG_NAME, "h1"))
            )
        except:
            pass
        
        time.sleep(1) # Small buffer
        
        page_source = driver.page_source
        soup = BeautifulSoup(page_source, 'html.parser')
        
        # --- Extract App Name ---
        app_name = "N/A"
        # 1. Try standard H1 with itemprop
        app_name_tag = soup.find('h1', {'itemprop': 'name'})
        if app_name_tag:
            app_name = app_name_tag.text.strip()
        
        # 2. Try class Fd93Bb
        if app_name == "N/A":
            app_name_tag = soup.find('h1', {'class': 'Fd93Bb'})
            if app_name_tag:
                 app_name = app_name_tag.text.strip()
        
        # 3. Try <title> tag fallback
        if app_name == "N/A":
            title_tag = soup.find('title')
            if title_tag:
                title_text = title_tag.text.strip()
                if " - Apps on Google Play" in title_text:
                    app_name = title_text.replace(" - Apps on Google Play", "")
                else:
                    app_name = title_text

        # --- Extract Install Count ---
        install_count = "N/A"
        # 1. Search for the class 'ClM7O' which often contains the stats values (Rating, Downloads, Size etc.)
        # We look for one containing '+'
        stats_values = soup.find_all('div', {'class': 'ClM7O'})
        for val in stats_values:
            text = val.text.strip()
            if '+' in text:
                install_count = text
                break
        
        # 2. Fallback to existing string extraction method if soup failed
        if install_count == "N/A":
            install_count = extract_install_count(page_source)

        
        # Extract developer name
        developer_tag = soup.find('div', {'class': 'Vbfug auoIOc'})
        if not developer_tag:
            developer_tag = soup.find('a', {'class': 'Si6A0c Gwdmqd'})
        developer = developer_tag.text.strip() if developer_tag else "N/A"
        
        # Extract logo URL
        logo_tag = soup.find('img', {'class': 'T75of arM4bb', 'itemprop': 'image'})
        if not logo_tag:
            logo_tag = soup.find('img', {'itemprop': 'image'})
        logo_url = logo_tag['src'] if logo_tag and 'src' in logo_tag.attrs else "N/A"
        
        # Extract rating
        rating_tag = soup.find('div', {'class': 'jILTFe'})
        rating = rating_tag.text.strip() if rating_tag else "N/A"
        
        # Extract review count
        review_count_tag = soup.find('div', {'class': 'g1rdde'})
        review_count = review_count_tag.text.strip() if review_count_tag else "N/A"
        
        # Fix: If rating is N/A or review count looks like Downloads/Installs, set to N/A
        if rating == "N/A" or "Download" in review_count or "Install" in review_count:
            review_count = "N/A"
        
        # Extract release date
        release_date = extract_release_date(page_source, app_url)
        
        # --- Filter by release date: only keep if within last 3 months ---
        def is_within_last_3_months(date_str):
            try:
                # Example format: Feb 11, 2025
                parsed_date = datetime.strptime(date_str, "%b %d, %Y")
                now = datetime.now()
                # Calculate the difference in months
                months_diff = (now.year - parsed_date.year) * 12 + (now.month - parsed_date.month)
                # If the app was released in the current month, months_diff == 0
                # If released in the last 3 months (0, 1, 2), keep it
                return 0 <= months_diff < 3
            except Exception as e:
                print(f"  [Date Filter] Could not parse release date '{date_str}': {e}")
                return False

        if release_date == "N/A" or not is_within_last_3_months(release_date):
            print(f"  [Date Filter] Skipping app (release date: {release_date})")
            return None
        # Debug print
        print(f"  App: {app_name}, Installs: {install_count}, Date: {release_date}")
        
        return {
            'niche': category_name,
            'app_name': app_name,
            'logo_url': logo_url,
            'install_count': install_count,
            'release_date': release_date,
            'rating': rating,
            'review_count': review_count,
            'app_link': app_url,
            'developer': developer
        }
        
    except Exception as e:
        print(f"Error extracting details for {app_url}: {e}")
        return None

def scrape_category(category_name, category_id, max_apps=100, csv_filename='google_play_apps.csv', is_first_category=False):
    """Scrape apps from a specific category"""
    print(f"\n{'='*60}")
    print(f"Scraping category: {category_name}")
    print(f"{'='*60}")
    
    apps_saved_count = 0
    
    # Navigate to category page
    category_url = f'https://play.google.com/store/apps/category/{category_id}'
    driver.get(category_url)
    time.sleep(3)
    
    # Scroll to load more apps
    print("Scrolling to load apps...")
    scroll_count = 0
    max_scrolls = 20  # Limit scrolls to prevent infinite loop
    
    while scroll_count < max_scrolls:
        last_height = driver.execute_script("return document.body.scrollHeight")
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)
        new_height = driver.execute_script("return document.body.scrollHeight")
        
        if new_height == last_height:
            break
        scroll_count += 1
    
    # Get page source and parse
    page_source = driver.page_source
    soup = BeautifulSoup(page_source, 'html.parser')
    
    # Find all app links
    app_links = set()
    all_links = soup.find_all('a', href=True)
    
    for link in all_links:
        href = link['href']
        if '/store/apps/details?id=' in href:
            full_url = 'https://play.google.com' + href if href.startswith('/') else href
            # Clean URL (remove extra parameters)
            if '&' in full_url:
                full_url = full_url.split('&')[0]
            app_links.add(full_url)
            
            if len(app_links) >= max_apps:
                break
    
    print(f"Found {len(app_links)} app links in {category_name}")
    
    # Extract details for each app and save immediately
    for idx, app_url in enumerate(list(app_links)[:max_apps], 1):
        print(f"Processing app {idx}/{min(len(app_links), max_apps)}: {app_url}")
        
        app_data = extract_app_details(app_url, category_name)
        
        if app_data:
            # Save each app immediately
            save_to_csv([app_data], csv_filename, append=(not is_first_category or idx > 1))
            apps_saved_count += 1
            print(f"  ✓ {app_data['app_name']} - {app_data['install_count']} installs - {app_data['release_date']}")
        
        # Small delay to avoid rate limiting
        time.sleep(1)
    
    return apps_saved_count

def save_to_csv(apps_data, filename='google_play_apps.csv', append=False):
    """Save collected data to CSV file"""
    if not apps_data:
        print("No data to save!")
        return
    
    csv_path = os.path.join(os.path.dirname(__file__), filename)
    
    # Define CSV headers
    headers = [
        'Niche',
        'App Name',
        'Logo URL',
        'Install Count',
        'Release Date',
        'Rating',
        'Review Count',
        'App Link',
        'Developer'
    ]
    
    try:
        # Check if file exists to determine if we need to write headers
        file_exists = os.path.exists(csv_path)
        mode = 'a' if append and file_exists else 'w'
        
        with open(csv_path, mode, newline='', encoding='utf-8-sig') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=[
                'niche', 'app_name', 'logo_url', 'install_count', 
                'release_date', 'rating', 'review_count', 'app_link', 'developer'
            ])
            
            # Write header only if file is new or we're overwriting
            if not file_exists or not append:
                csvfile.write(','.join(headers) + '\n')
            
            # Write data
            for app in apps_data:
                writer.writerow(app)
        
        print(f"  ✓ Saved {len(apps_data)} apps to: {csv_path}")
        
    except Exception as e:
        print(f"  ✗ Error saving to CSV: {e}")

def main():
    """Main function to orchestrate scraping"""
    print("="*60)
    print("Google Play Store Category Scraper")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    
    total_apps_scraped = 0
    csv_filename = 'google_play_apps.csv'
    
    # Remove existing CSV file to start fresh
    csv_path = os.path.join(os.path.dirname(__file__), csv_filename)
    if os.path.exists(csv_path):
        os.remove(csv_path)
        print(f"Removed existing file: {csv_filename}\n")
    
    try:
        # Scrape each category
        for idx, (category_name, category_id) in enumerate(CATEGORIES.items(), 1):
            try:
                apps_count = scrape_category(category_name, category_id, max_apps=100, 
                                            csv_filename=csv_filename, is_first_category=(idx == 1))
                
                total_apps_scraped += apps_count
                if apps_count > 0:
                    print(f"✓ Collected {apps_count} apps from {category_name}")
                    print(f"  📊 Total apps saved so far: {total_apps_scraped}\n")
                else:
                    print(f"✗ No apps collected from {category_name}\n")
                    
            except Exception as e:
                print(f"✗ Error scraping {category_name}: {e}\n")
                continue
        
        # Final summary
        print(f"\n{'='*60}")
        print(f"✓ SCRAPING COMPLETE!")
        print(f"✓ Total apps scraped: {total_apps_scraped}")
        print(f"✓ Data saved to: {csv_path}")
        print(f"{'='*60}")
        
    except KeyboardInterrupt:
        print("\n\nScraping interrupted by user!")
        print(f"Partial data already saved to: {csv_path}")
        print(f"Total apps saved: {total_apps_scraped}")
    
    finally:
        # Close the browser
        driver.quit()
        print("\nBrowser closed.")
        print(f"Finished at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    main()
