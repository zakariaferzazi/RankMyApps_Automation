import requests
import csv
import time
from datetime import datetime, timedelta

# ===========================
# CONFIGURATION - EDIT HERE
# ===========================
CONFIG = {
    # Filter apps by release date (True = filter, False = include all apps)
    'FILTER_BY_RELEASE_DATE': False,
    
    # How many days back too include (only used if FILTER_BY_RELEASE_DATE = True)
    # Example: 90 = last 90 days, 180 = last 6 months, 365 = last year
    'DAYS_THRESHOLD': 90,
}

# App Store category IDs for RSS feeds
CATEGORIES = {
    'games': 6014,
    'business': 6000,
    'weather': 6001,
    'utilities': 6002,
    'travel': 6003,
    'sports': 6004,
    'social-networking': 6005,
    'reference': 6006,
    'productivity': 6007,
    'photo-video': 6008,
    'news': 6009,
    'navigation': 6010,
    'music': 6011,
    'lifestyle': 6012,
    'health-fitness': 6013,
    'finance': 6015,
    'entertainment': 6016,
    'education': 6017,
    'books': 6018,
    'medical': 6020,
    'catalogs': 6022,
    'food-drink': 6023,
    'shopping': 6024
}

# Countries to search (using correct iTunes store country codes)
COUNTRIES = ['us', 'gb', 'ca', 'fr', 'de', 'ie', 'nl', 'no', 'ch']

class AppStoreSearcher:
    def __init__(self, days_threshold=None):
        """
        Initialize the App Store searcher
        
        :param days_threshold: Only fetch apps released within this many days (overrides CONFIG if provided)
        """
        self.rss_url_template = "https://itunes.apple.com/{country}/rss/topfreeapplications/limit=200/genre={genre_id}/json"
        self.lookup_url = "https://itunes.apple.com/lookup"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36',
            'Accept': 'application/json',
        }
        self.filter_by_date = CONFIG['FILTER_BY_RELEASE_DATE']
        self.days_threshold = days_threshold if days_threshold is not None else CONFIG['DAYS_THRESHOLD']
        self.cutoff_date = datetime.now() - timedelta(days=self.days_threshold)
        self.all_apps = {}  # Use dict to avoid duplicates (key: app_id)
    
    def estimate_install_count(self, review_count):
        """
        Estimate install count based on review count
        
        :param review_count: Number of reviews
        :return: Estimated install count range as string
        """
        if review_count <= 10:
            return "500 – 1,2K"
        elif review_count <= 50:
            return "1,2K – 6K"
        elif review_count <= 200:
            return "6K – 24K"
        elif review_count <= 1000:
            return "24K – 120K"
        elif review_count <= 5000:
            return "120K – 600K"
        elif review_count <= 20000:
            return "600K – 2,4M"
        elif review_count <= 100000:
            return "2,4M – 12M"
        else:
            return "12M+"
        
    def search_by_category(self, category_id, country='us', limit=200):
        """
        Search for apps by category using RSS feeds
        
        :param category_id: Category ID to search
        :param country: Two-letter country code
        :param limit: Maximum number of results (max 200)
        :return: List of app IDs
        """
        # RSS feeds support up to 200
        url = self.rss_url_template.format(country=country, genre_id=category_id)
        url = url.replace('limit=200', f'limit={limit}')
        
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            
            data = response.json()
            
            # Extract app IDs from RSS feed
            app_ids = []
            if 'feed' in data and 'entry' in data['feed']:
                for entry in data['feed']['entry']:
                    app_id = entry.get('id', {}).get('attributes', {}).get('im:id')
                    if app_id:
                        app_ids.append(int(app_id))
            
            return app_ids
        
        except requests.RequestException as e:
            print(f"Error searching category {category_id} in {country}: {e}")
            return []
        except (KeyError, ValueError) as e:
            print(f"Error parsing response for category {category_id} in {country}: {e}")
            return []
    
    def get_app_metadata(self, app_id):
        """
        Retrieve detailed metadata for a specific app
        
        :param app_id: App ID to fetch
        :return: Dictionary with app metadata or None
        """
        try:
            url = f'{self.lookup_url}?id={app_id}'
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            
            app_data = response.json()
            
            if app_data['resultCount'] == 0:
                print(f"No app found with ID {app_id}")
                return None
            
            app_info = app_data['results'][0]
            
            # Parse release date
            release_date_str = app_info.get('releaseDate', '')
            if not release_date_str:
                return None
                
            release_date = datetime.strptime(
                release_date_str,
                "%Y-%m-%dT%H:%M:%SZ"
            )
            
            # Check if app was released within the threshold (OPTIONAL)
            if self.filter_by_date and release_date < self.cutoff_date:
                return None
            
            # Calculate days since release for filtering and display
            days_since_release = (datetime.now() - release_date).days
            
            # Get review count for install estimation
            review_count = app_info.get('userRatingCount', 0)
            
            # Format rating (e.g. 4.7)
            rating_val = app_info.get('averageUserRating', 0)
            formatted_rating = round(float(rating_val), 1) if rating_val else 0
            
            # Format review count (e.g. 122k)
            if review_count >= 1000000:
                formatted_review_count = f"{review_count/1000000:.1f}M".replace(".0M", "M")
            elif review_count >= 1000:
                formatted_review_count = f"{review_count/1000:.0f}k"
            else:
                formatted_review_count = str(review_count)
            
            # Prepare metadata dictionary (simplified fields only)
            metadata = {
                'Niche': app_info.get('primaryGenreName', ''),
                'App Name': app_info.get('trackName', ''),
                'Logo URL': app_info.get('artworkUrl512', app_info.get('artworkUrl100', '')),
                'Install Count': self.estimate_install_count(review_count),
                'Release Date': release_date.strftime('%B %d, %Y'),
                'Rating': formatted_rating,
                'Review Count': formatted_review_count,
                'App Link': app_info.get('trackViewUrl', ''),
                'Developer': app_info.get('artistName', ''),
            }
            
            print(f"✓ App {app_id}: {metadata['App Name']} - Released {days_since_release} days ago")
            return metadata
        
        except Exception as e:
            print(f"Error fetching metadata for app {app_id}: {e}")
            return None
    
    def search_all_categories(self, categories=None, countries=None, output_file='app_store_apps.csv'):
        """
        Search apps across multiple categories and countries and save immediately
        
        :param categories: List of category names (uses all if None)
        :param countries: List of country codes (uses default if None)
        :param output_file: Filename to save results to incrementally
        """
        if categories is None:
            categories = list(CATEGORIES.keys())
        if countries is None:
            countries = COUNTRIES
        
        # Collect all unique app IDs first
        print(f"\n{'='*70}")
        print(f"PHASE 1: Searching for apps in {len(categories)} categories across {len(countries)} countries")
        print(f"{'='*70}\n")
        
        app_ids_set = set()
        
        for category_name in categories:
            if category_name not in CATEGORIES:
                print(f"⚠ Warning: Unknown category '{category_name}', skipping...")
                continue
                
            category_id = CATEGORIES[category_name]
            # Display category name in a readable format
            display_name = category_name.replace('-', ' ').title()
            print(f"\n📂 Searching category: {display_name} (ID: {category_id})")
            
            for country in countries:
                print(f"  → Country: {country.upper()}", end=' ')
                app_ids = self.search_by_category(category_id, country)
                new_ids = len(set(app_ids) - app_ids_set)
                app_ids_set.update(app_ids)
                print(f"({len(app_ids)} found, {new_ids} new)")
                time.sleep(0.5)  # Rate limiting
        
        print(f"\n{'='*70}")
        print(f"PHASE 2: Fetching metadata for {len(app_ids_set)} unique apps")
        print(f"Filtering for apps released within the last {self.days_threshold} days")
        print(f"Saving results immediately to {output_file}")
        print(f"{'='*70}\n")
        
        # Define fields and write header (use keys from get_app_metadata to ensure consistency)
        fieldnames = ['Niche', 'App Name', 'Logo URL', 'Install Count', 'Release Date', 'Rating', 'Review Count', 'App Link', 'Developer']
        
        # Initialize file with headers
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
        
        # Fetch metadata for each unique app ID
        for i, app_id in enumerate(app_ids_set, 1):
            print(f"[{i}/{len(app_ids_set)}] ", end='')
            metadata = self.get_app_metadata(app_id)
            
            if metadata:
                self.all_apps[app_id] = metadata
                # Save immediately to CSV
                try:
                    with open(output_file, 'a', newline='', encoding='utf-8') as f:
                        writer = csv.DictWriter(f, fieldnames=fieldnames)
                        writer.writerow(metadata)
                except Exception as e:
                    print(f"Error saving app {app_id} to CSV: {e}")
            
            time.sleep(0.3)  # Rate limiting
        
        print(f"\n{'='*70}")
        print(f"✓ Found {len(self.all_apps)} apps released within the last {self.days_threshold} days")
        print(f"✓ All items saved to {output_file}")
        print(f"{'='*70}\n")
    
    def save_to_csv(self, filename='app_store_apps.csv'):
        """
        Save app details to CSV
        
        :param filename: Output CSV filename
        """
        if not self.all_apps:
            print("No apps to save.")
            return
        
        apps_list = list(self.all_apps.values())
        
        # Sort by app name alphabetically
        apps_list.sort(key=lambda x: x['App Name'])
        
        keys = apps_list[0].keys()
        
        with open(filename, 'w', newline='', encoding='utf-8') as file:
            dict_writer = csv.DictWriter(file, keys)
            dict_writer.writeheader()
            dict_writer.writerows(apps_list)
        
        print(f"✓ Saved {len(apps_list)} apps to {filename}")
        
        # Print summary statistics
        print(f"\n{'='*70}")
        print("SUMMARY")
        print(f"{'='*70}")
        print(f"Total apps found: {len(apps_list)}")
        print(f"Date range: Last {self.days_threshold} days")
        print(f"{'='*70}\n")


def main():
    # Initialize searcher (90 days threshold)
    searcher = AppStoreSearcher(days_threshold=90)
    
    # Select categories to search (you can customize this list)
    categories_to_search = [
        'utilities',
        'productivity',
        'lifestyle',
        'entertainment',
        'photo-video',
        'health-fitness',
        'social-networking',
        'games',
        'music',
        'food-drink'
    ]
    
    # Or search all categories:
    # searcher.search_all_categories()
    
    # Search selected categories across all countries
    searcher.search_all_categories(
        categories=categories_to_search,
        countries=COUNTRIES,
        output_file='app_store_apps.csv'
    )
    
    # Sort results at the end
    searcher.save_to_csv('app_store_apps.csv')


if __name__ == '__main__':
    main()
